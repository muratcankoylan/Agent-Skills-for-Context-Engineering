#!/usr/bin/env python3
"""Run the repository's deterministic validation gates in one command.

This is the local/operator equivalent of the CI floor. It intentionally uses the
current Python interpreter for repository Python scripts, so helper tools such as
`skills-ref` should be installed into that environment with:

    python3 -m pip install -r requirements-dev.txt
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

COMPILE_TARGETS = [
    "researcher/scripts/skill_frontmatter.py",
    "researcher/scripts/tests/test_skill_frontmatter.py",
    "researcher/scripts/tests/test_validate_all.py",
    "researcher/scripts/tests/test_validation_paths.py",
    "researcher/scripts/validate_platform_compat.py",
    "researcher/scripts/validate_repo.py",
    "researcher/scripts/validate_run.py",
    "researcher/scripts/research_loop.py",
    "researcher/scripts/novelty_check.py",
    "researcher/scripts/compare_skill_revisions.py",
    "researcher/scripts/check_activation_cases.py",
    "researcher/scripts/run_benchmarks.py",
    "researcher/scripts/skill_health.py",
    "researcher/scripts/loop_common.py",
    "researcher/scripts/loop_discover.py",
    "researcher/scripts/loop_step.py",
    "researcher/scripts/loop_daily.py",
    "researcher/scripts/loop_status.py",
    "researcher/scripts/validate_all.py",
]


@dataclass(frozen=True)
class Step:
    name: str
    command: list[str]


def build_steps() -> list[Step]:
    python = sys.executable
    return [
        Step("compile researcher scripts", [python, "-m", "py_compile", *COMPILE_TARGETS]),
        Step(
            "researcher unit tests",
            [python, "-m", "unittest", "discover", "-s", "researcher/scripts/tests", "-p", "test_*.py"],
        ),
        Step(
            "platform compatibility",
            [python, "researcher/scripts/validate_platform_compat.py", "--require-reference-validator"],
        ),
        Step("repository validation", [python, "researcher/scripts/validate_repo.py", "--strict"]),
        Step(
            "skill health",
            [python, "researcher/scripts/skill_health.py", "--strict", "--no-history"],
        ),
        Step("activation cases", [python, "researcher/scripts/check_activation_cases.py"]),
        Step("adversarial benchmarks", [python, "researcher/scripts/run_benchmarks.py"]),
    ]


def format_command(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def run_step(step: Step) -> int:
    print(f"\n== {step.name} ==", flush=True)
    print(format_command(step.command), flush=True)
    completed = subprocess.run(step.command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        print(f"FAILED {step.name}: exit {completed.returncode}", file=sys.stderr, flush=True)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic repository validation gates")
    parser.add_argument("--list", action="store_true", help="print the gate commands without running them")
    args = parser.parse_args()

    steps = build_steps()
    if args.list:
        for step in steps:
            print(f"{step.name}: {format_command(step.command)}")
        return 0

    for step in steps:
        return_code = run_step(step)
        if return_code != 0:
            return return_code

    print("\nALL_REPOSITORY_GATES_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
