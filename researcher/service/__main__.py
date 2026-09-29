"""Portable CLI; foreground service owns its scheduling without desktop tasks."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time

from .contracts import ServiceError, load_config
from .environment import read_config_file
from .store import Store
from .workflow import Workflow, admit_due, make_manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "init",
            "demo",
            "status",
            "inspect",
            "pause",
            "resume",
            "enqueue",
            "tick",
            "work",
            "serve",
            "api",
            "backup",
            "configure",
            "preflight",
        ],
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Explicit private literal env file; no ambient fallback",
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--schedule")
    parser.add_argument("--job-id")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--token-env", default="RESEARCH_OPERATOR_TOKEN")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        root = args.repo.resolve()
        if args.command in {"configure", "preflight"}:
            from .environment import read_env_file
            from .retrieval_setup import build_config, preflight, write_config

            if args.env_file is None:
                raise ServiceError("ENV_FILE_REQUIRED")
            if (
                args.live
                or args.state is not None
                or (args.command == "configure" and args.config is not None)
                or (args.command == "preflight" and args.output is not None)
            ):
                raise ServiceError("INVALID_SETUP_ARGUMENTS")
            values = read_env_file(args.env_file)
            supplied = None
            if args.config is not None:
                supplied = load_config(read_config_file(args.config))
            result = preflight(values, supplied)
            if args.command == "configure":
                if args.output is None:
                    raise ServiceError("OUTPUT_REQUIRED")
                if result["local_ready"]:
                    write_config(args.output, build_config(values))
                    result["config_written"] = True
                else:
                    result["config_written"] = False
            print(json.dumps(result, sort_keys=True))
            return 0 if result["local_ready"] else 1
        if args.state is None:
            raise ServiceError("STATE_REQUIRED")
        directory = args.state.absolute()
        if args.command == "demo":
            if args.env_file is not None:
                raise ServiceError("DEMO_CANNOT_LOAD_CREDENTIALS")
            from .demo import run_demo

            result = run_demo(root, directory)
            print(json.dumps(result, sort_keys=True))
            return 1 if any("error" in row for row in result["results"]) else 0
        if args.config is None:
            raise ServiceError("CONFIG_REQUIRED")
        config = load_config(read_config_file(args.config))
        credential = None
        if args.env_file is not None:
            from .environment import credential_reader, read_env_file
            from .retrieval_setup import configured_credential_names

            credential = credential_reader(
                read_env_file(args.env_file),
                configured_credential_names(config, args.command, args.token_env),
            )
        store = Store(directory, config, initialize=args.command == "init")
        workflow = Workflow(
            store,
            root,
            live=args.live,
            **({"credential": credential} if credential is not None else {}),
        )
        if args.command in {"init", "status"}:
            result = store.status()
        elif args.command == "inspect":
            if not args.job_id:
                raise ServiceError("JOB_ID_REQUIRED")
            result = store.inspect(args.job_id)
        elif args.command in {"pause", "resume"}:
            store.pause(args.command == "pause")
            result = store.status()
        elif args.command == "enqueue":
            schedules = [s for s in config["schedules"] if s["id"] == args.schedule]
            if len(schedules) != 1 or not args.job_id:
                raise ServiceError("SCHEDULE_AND_JOB_REQUIRED")
            result = {
                "admitted": store.enqueue(
                    args.job_id, make_manifest(root, config, schedules[0])
                )
            }
        elif args.command == "tick":
            result = {"admitted": admit_due(store, root)}
        elif args.command == "work":
            result = {"results": workflow.drain(config["limits"]["max_runs_per_tick"])}
        elif args.command == "backup":
            if not args.output:
                raise ServiceError("OUTPUT_REQUIRED")
            store.backup(args.output)
            result = {
                "inspection_backup": True,
                "contains_artifact_closure": False,
                "safe_for_live_restore": False,
            }
        elif args.command == "api":
            from .api import serve_api

            token = (
                credential(args.token_env)
                if credential is not None
                else os.environ.get(args.token_env, "")
            )
            serve_api(store, root, args.host, args.port, token)
            return 0
        else:
            if not args.live:
                raise ServiceError("LIVE_EXECUTION_REQUIRES_OPT_IN")
            if not 5 <= args.interval <= 3600:
                raise ServiceError("INVALID_POLL_INTERVAL")
            stopped = threading.Event()
            for sig in (signal.SIGINT, signal.SIGTERM):
                signal.signal(sig, lambda *_: stopped.set())
            while not stopped.is_set():
                try:
                    admitted = admit_due(store, root)
                    results = workflow.drain(config["limits"]["max_runs_per_tick"])
                    print(
                        json.dumps(
                            {
                                "event": "service_cycle",
                                "at": int(time.time()),
                                "admitted": admitted,
                                "results": [
                                    {"job": r["job"], "error": r.get("error")}
                                    for r in results
                                ],
                            }
                        ),
                        flush=True,
                    )
                except ServiceError as exc:
                    print(
                        json.dumps({"event": "service_blocked", "code": exc.code}),
                        flush=True,
                    )
                stopped.wait(args.interval)
            return 0
        print(json.dumps(result, sort_keys=True))
        if args.command == "work" and any("error" in row for row in result["results"]):
            return 1
        return 0
    except (ServiceError, OSError, ValueError) as exc:
        code = exc.code if isinstance(exc, ServiceError) else "COMMAND_FAILED"
        print(json.dumps({"error": code}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
