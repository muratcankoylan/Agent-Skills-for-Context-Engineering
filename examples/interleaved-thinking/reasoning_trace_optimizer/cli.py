"""
CLI interface for Reasoning Trace Optimizer.

Provides command-line access to the optimization tools.
"""

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console

from reasoning_trace_optimizer.analyzer import TraceAnalyzer, format_analysis_report
from reasoning_trace_optimizer.capture import TraceCapture, format_trace_for_display
from reasoning_trace_optimizer.loop import OptimizationLoop, LoopConfig
from reasoning_trace_optimizer.skill_generator import SkillGenerator


console = Console()


def cmd_capture(args: argparse.Namespace) -> None:
    """Run a task and capture reasoning trace."""
    capture = TraceCapture(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
    )

    console.print(f"[cyan]Capturing trace for task: {args.task}[/cyan]")

    trace = capture.run(
        task=args.task,
        system_prompt=args.system_prompt or "You are a helpful assistant.",
        max_turns=args.max_turns,
    )

    # Output trace
    output = format_trace_for_display(trace)
    if args.output:
        Path(args.output).write_text(output)
        console.print(f"[green]Trace saved to: {args.output}[/green]")
    else:
        console.print(output)


def cmd_analyze(args: argparse.Namespace) -> None:
    """Analyze a captured reasoning trace."""
    # For now, run capture + analyze together
    # In future, could load trace from file

    capture = TraceCapture(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
    )
    analyzer = TraceAnalyzer(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
    )

    console.print(f"[cyan]Capturing and analyzing: {args.task}[/cyan]")

    trace = capture.run(
        task=args.task,
        system_prompt=args.system_prompt or "You are a helpful assistant.",
    )

    analysis = analyzer.analyze(trace)

    # Output analysis
    output = format_analysis_report(analysis)
    if args.output:
        Path(args.output).write_text(output)
        console.print(f"[green]Analysis saved to: {args.output}[/green]")
    else:
        console.print(output)


def cmd_optimize(args: argparse.Namespace) -> None:
    """Run full optimization loop."""
    config = LoopConfig(
        max_iterations=args.max_iterations,
        convergence_threshold=args.convergence_threshold,
        min_score_threshold=args.min_score,
        save_artifacts=True,
        artifacts_dir=args.artifacts_dir,
        verbose=True,
    )

    loop = OptimizationLoop(
        config=config,
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
    )

    console.print(f"[cyan]Starting optimization for: {args.task}[/cyan]")

    result = loop.run(
        task=args.task,
        initial_prompt=args.system_prompt or "You are a helpful assistant.",
    )

    # Output final prompt
    if args.output:
        Path(args.output).write_text(result.final_prompt)
        console.print(f"[green]Optimized prompt saved to: {args.output}[/green]")

    # Generate skill if requested
    if args.generate_skill:
        generator = SkillGenerator(
            api_key=args.api_key,
            base_url=args.base_url,
            model=args.model,
        )
        skill_path = generator.generate(
            result=result,
            skill_name=args.skill_name or "optimized-agent",
            output_dir=args.skills_dir,
        )
        console.print(f"[green]Generated skill at: {skill_path}[/green]")


def cmd_generate_skill(args: argparse.Namespace) -> None:
    """Generate a skill from optimization artifacts."""
    # Load summary from artifacts
    artifacts_dir = Path(args.artifacts_dir)
    summary_path = artifacts_dir / "summary.json"

    if not summary_path.exists():
        console.print("[red]Error: No optimization summary found. Run optimize first.[/red]")
        sys.exit(1)

    with open(summary_path) as f:
        summary = json.load(f)

    # Create minimal loop result from summary
    from reasoning_trace_optimizer.models import LoopResult, LoopIteration, ReasoningTrace, AnalysisResult

    # Load final prompt
    final_prompt_path = artifacts_dir / "final_prompt.txt"
    final_prompt = final_prompt_path.read_text() if final_prompt_path.exists() else ""

    result = LoopResult(
        task=summary.get("task", "Unknown task"),
        final_prompt=final_prompt,
        total_iterations=summary.get("total_iterations", 0),
        initial_score=summary.get("initial_score", 0),
        final_score=summary.get("final_score", 0),
        improvement_percentage=summary.get("improvement_percentage", 0),
        converged=summary.get("converged", False),
    )

    generator = SkillGenerator(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
    )

    skill_path = generator.generate(
        result=result,
        skill_name=args.skill_name,
        output_dir=args.output_dir,
    )

    console.print(f"[green]Generated skill at: {skill_path}[/green]")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="rto",
        description="Reasoning Trace Optimizer - Debug and optimize AI agents using M2.1's interleaved thinking",
    )

    # Global arguments
    parser.add_argument(
        "--api-key",
        help="MiniMax API key (or set ANTHROPIC_API_KEY env var)",
    )
    parser.add_argument(
        "--base-url",
        default="https://api.minimax.io/anthropic",
        help="API base URL",
    )
    parser.add_argument(
        "--model",
        default="MiniMax-M2.1",
        choices=["MiniMax-M2.1", "MiniMax-M2.1-lightning", "MiniMax-M2"],
        help="Model to use",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Capture command
    capture_parser = subparsers.add_parser(
        "capture",
        help="Capture reasoning trace for a task",
    )
    capture_parser.add_argument("task", help="Task to execute")
    capture_parser.add_argument("--system-prompt", "-s", help="System prompt")
    capture_parser.add_argument("--max-turns", type=int, default=10)
    capture_parser.add_argument("--output", "-o", help="Output file path")
    capture_parser.set_defaults(func=cmd_capture)

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Capture and analyze reasoning trace",
    )
    analyze_parser.add_argument("task", help="Task to analyze")
    analyze_parser.add_argument("--system-prompt", "-s", help="System prompt")
    analyze_parser.add_argument("--output", "-o", help="Output file path")
    analyze_parser.set_defaults(func=cmd_analyze)

    # Optimize command
    optimize_parser = subparsers.add_parser(
        "optimize",
        help="Run full optimization loop",
    )
    optimize_parser.add_argument("task", help="Task to optimize for")
    optimize_parser.add_argument("--system-prompt", "-s", help="Initial system prompt")
    optimize_parser.add_argument("--max-iterations", type=int, default=5)
    optimize_parser.add_argument("--convergence-threshold", type=float, default=5.0)
    optimize_parser.add_argument("--min-score", type=float, default=80.0)
    optimize_parser.add_argument(
        "--artifacts-dir",
        default="./optimization_artifacts",
        help="Directory for artifacts",
    )
    optimize_parser.add_argument("--output", "-o", help="Output file for final prompt")
    optimize_parser.add_argument(
        "--generate-skill",
        action="store_true",
        help="Generate Agent Skill from results",
    )
    optimize_parser.add_argument("--skill-name", help="Name for generated skill")
    optimize_parser.add_argument(
        "--skills-dir",
        default="./generated_skills",
        help="Directory for generated skills",
    )
    optimize_parser.set_defaults(func=cmd_optimize)

    # Generate skill command
    skill_parser = subparsers.add_parser(
        "generate-skill",
        help="Generate skill from optimization artifacts",
    )
    skill_parser.add_argument("skill_name", help="Name for the skill")
    skill_parser.add_argument(
        "--artifacts-dir",
        default="./optimization_artifacts",
        help="Directory with optimization artifacts",
    )
    skill_parser.add_argument(
        "--output-dir",
        default="./generated_skills",
        help="Output directory for skill",
    )
    skill_parser.set_defaults(func=cmd_generate_skill)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
