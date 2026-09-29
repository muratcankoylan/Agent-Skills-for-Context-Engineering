"""Reproduce the local tracing microbenchmark and real-process crash check.

Run from the repository root with its existing virtual environment:
  .venv/bin/python -B /path/to/tracing-overhead-repro-20260929.py

This standalone experiment imports the local implementation being measured.
It performs no provider or network calls, reads no credentials, changes no
repository files, and removes its private temporary journals on exit. Only
aggregate measurements and environment/version identifiers are printed.

Method: one fresh journal; five batches of 100 completed, unannotated, unnested
workflow.effect no-op spans; alternate baseline-first and tracing-first order;
no warmup; exclude journal setup from timings; measure complete context-manager
entry/body/exit using perf_counter_ns. p95 uses nearest rank. Baseline timings
near clock resolution are not suitable for slowdown-ratio claims. This is not
a production throughput or power-loss durability experiment.
"""

import hashlib
import json
import math
import os
from pathlib import Path
import platform
import signal
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time


def statistics_for(values):
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "median_ns": statistics.median(ordered),
        "p95_nearest_rank_ns": ordered[math.ceil(.95 * len(ordered)) - 1],
        "min_ns": ordered[0],
        "max_ns": ordered[-1],
    }


def run():
    # Deliberately use the operator-selected checkout, not installed packages.
    sys.path.insert(0, str(Path.cwd()))
    from researcher.service.tracing import TraceJournal, Tracer

    source = Path("researcher/service/tracing.py")
    source_before = hashlib.sha256(source.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="trace-overhead-") as temporary:
        state = Path(temporary).resolve()
        state.chmod(0o700)
        journal = TraceJournal(state / "telemetry")
        tracer = Tracer(journal)
        batches, all_baseline, all_traced = [], [], []

        def measure(traced):
            samples = []
            started = time.perf_counter_ns()
            if traced:
                for _ in range(100):
                    tick = time.perf_counter_ns()
                    with tracer.span("workflow.effect"):
                        pass
                    samples.append(time.perf_counter_ns() - tick)
            else:
                for _ in range(100):
                    tick = time.perf_counter_ns()
                    pass
                    samples.append(time.perf_counter_ns() - tick)
            return samples, time.perf_counter_ns() - started

        for index in range(5):
            if index % 2:
                traced, traced_total = measure(True)
                baseline, baseline_total = measure(False)
            else:
                baseline, baseline_total = measure(False)
                traced, traced_total = measure(True)
            all_baseline.extend(baseline)
            all_traced.extend(traced)
            batches.append({
                "batch": index + 1,
                "baseline_first": not bool(index % 2),
                "baseline": statistics_for(baseline),
                "traced": statistics_for(traced),
                "baseline_batch_wall_ns": baseline_total,
                "traced_batch_wall_ns": traced_total,
                "batch_wall_difference_ns": traced_total - baseline_total,
            })
        status = journal.status()
        assert status["spans"] == 500 and status["unfinished_spans"] == 0
        assert tracer.health()["write_failures"] == 0
        with journal.connect() as database:
            sqlite_settings = {
                "journal_mode": database.execute("PRAGMA journal_mode").fetchone()[0],
                "synchronous": database.execute("PRAGMA synchronous").fetchone()[0],
                "page_size": database.execute("PRAGMA page_size").fetchone()[0],
                "page_count": database.execute("PRAGMA page_count").fetchone()[0],
            }
        measurement = {
            "batches": batches,
            "all_baseline": statistics_for(all_baseline),
            "all_traced": statistics_for(all_traced),
            "db_bytes": journal.path.stat().st_size,
            "directory_bytes": sum(path.stat().st_size for path in journal.directory.iterdir() if path.is_file()),
            "status": status,
            "health": tracer.health(),
            "sqlite": sqlite_settings,
        }

    minimal_env = {
        "PATH": os.defpath,
        "PYTHONPATH": str(Path.cwd()),
        "PYTHONUTF8": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    child_code = '''import os
import sys
from pathlib import Path
from researcher.service.tracing import TraceJournal, Tracer
journal = TraceJournal(Path(sys.argv[1]) / "telemetry")
tracer = Tracer(journal)
with tracer.span("workflow.effect"):
    pass
with tracer.span("workflow.effect"):
    os._exit(73)
'''
    with tempfile.TemporaryDirectory(prefix="trace-crash-") as temporary:
        state = Path(temporary).resolve()
        state.chmod(0o700)
        child = subprocess.run(
            [sys.executable, "-B", "-c", child_code, str(state)],
            env=minimal_env, capture_output=True, timeout=3,
        )
        assert child.returncode == 73, "unexpected-child-exit"
        assert child.stdout == b"" and child.stderr == b""
        reopened = TraceJournal(state / "telemetry")
        status = reopened.status()
        rows = reopened.rows()
        assert [row["status"] for row in rows] == ["ok", "running"]
        assert rows[1]["end_ns"] is None and rows[1]["duration_ns"] is None
        assert status["spans"] == 2 and status["unfinished_spans"] == 1 and status["pending_export"] == 1
        preview_run = subprocess.run(
            [sys.executable, "-B", "-m", "researcher.service.trace_cli", "preview", "--state", str(state)],
            env=minimal_env, capture_output=True, timeout=3,
        )
        assert preview_run.returncode == 0 and preview_run.stderr == b""
        preview = json.loads(preview_run.stdout)
        preview_spans = preview["payload"]["resourceSpans"][0]["scopeSpans"][0]["spans"]
        assert preview["span_count"] == 1 and len(preview_spans) == 1
        assert preview_spans[0]["spanId"] == rows[0]["span_id"]
        assert preview_spans[0]["spanId"] != rows[1]["span_id"]
        crash = {
            "child_exit_code": child.returncode,
            "child_output_bytes": 0,
            "reopened_status": status,
            "stored_statuses": [row["status"] for row in rows],
            "unfinished_end_and_duration_null": True,
            "cli_preview_span_count": preview["span_count"],
            "cli_preview_excludes_unfinished": True,
        }
    source_after = hashlib.sha256(source.read_bytes()).hexdigest()
    assert source_before == source_after, "measured-source-changed"
    return {
        "schema": "local-tracing-measurement/v1",
        "source_sha256": source_after,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "sqlite_version": sqlite3.sqlite_version,
            "perf_counter_resolution_seconds": time.get_clock_info("perf_counter").resolution,
        },
        "method": {
            "batches": 5,
            "spans_per_batch": 100,
            "journal_setup_excluded": True,
            "fsync_policy": "sqlite synchronous FULL",
            "warmup_spans": 0,
            "p95_method": "nearest_rank",
            "operation": "workflow.effect",
            "payload": "empty no-op, no annotations, no nesting",
            "providers": False,
            "network": False,
            "individual_samples_retained": False,
        },
        "measurement": measurement,
        "crash": crash,
    }


def timeout(_signum, _frame):
    raise TimeoutError("LOCAL_EXPERIMENT_DEADLINE")


if __name__ == "__main__":
    # POSIX-only like the measured fcntl-backed journal. Fail boundedly rather
    # than turning a local diagnostic into a long-running workload.
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(9)
    try:
        result = run()
    finally:
        signal.alarm(0)
    print(json.dumps(result, sort_keys=True))
