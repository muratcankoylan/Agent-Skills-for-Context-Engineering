"""
OptimizationLoop: Orchestrates the full capture → analyze → improve → re-run cycle.

This is the main entry point for automated prompt optimization,
running iterative improvements until convergence or max iterations.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from reasoning_trace_optimizer.analyzer import TraceAnalyzer, format_analysis_report
from reasoning_trace_optimizer.capture import TraceCapture, format_trace_for_display
from reasoning_trace_optimizer.models import (
    AnalysisResult,
    LoopIteration,
    LoopResult,
    OptimizationResult,
    ReasoningTrace,
)
from reasoning_trace_optimizer.optimizer import PromptOptimizer, format_optimization_report


console = Console()


@dataclass
class LoopConfig:
    """Configuration for the optimization loop."""

    max_iterations: int = 5
    convergence_threshold: float = 3.0  # Stop if improvement < this %
    min_score_threshold: float = 75.0  # Stop if score >= this (realistic for complex tasks)
    regression_threshold: float = 8.0  # Rollback if score drops by this much

    # Scoring weights
    success_weight: float = 0.4
    score_weight: float = 0.4
    error_weight: float = 0.2

    # Optimization behavior
    use_best_prompt: bool = True  # Use best performing prompt, not final
    max_prompt_growth: float = 5.0  # Max ratio of new prompt length to original

    # Output options
    save_artifacts: bool = True
    artifacts_dir: str = "./optimization_artifacts"
    verbose: bool = True


class OptimizationLoop:
    """
    Orchestrates the full optimization cycle.

    Runs iterative loops of:
    1. Execute agent with current prompt
    2. Capture reasoning trace
    3. Analyze trace for issues
    4. Generate optimized prompt
    5. Repeat until convergence

    Example:
        ```python
        loop = OptimizationLoop()
        result = loop.run(
            task="Search for Python tutorials and summarize them",
            initial_prompt="You are a helpful research assistant.",
            tools=[search_tool],
            tool_executor=execute_search
        )

        print(f"Improved from {result.initial_score} to {result.final_score}")
        print(f"Final prompt:\\n{result.final_prompt}")
        ```
    """

    def __init__(
        self,
        config: LoopConfig | None = None,
        api_key: str | None = None,
        base_url: str = "https://api.minimax.io/anthropic",
        model: str = "MiniMax-M2.1",
    ):
        """
        Initialize the optimization loop.

        Args:
            config: Loop configuration
            api_key: MiniMax API key
            base_url: API endpoint
            model: Model to use for all components
        """
        self.config = config or LoopConfig()

        # Initialize components with same configuration
        self.capture = TraceCapture(api_key=api_key, base_url=base_url, model=model)
        self.analyzer = TraceAnalyzer(api_key=api_key, base_url=base_url, model=model)
        self.optimizer = PromptOptimizer(api_key=api_key, base_url=base_url, model=model)

        # Create artifacts directory
        if self.config.save_artifacts:
            Path(self.config.artifacts_dir).mkdir(parents=True, exist_ok=True)

    def run(
        self,
        task: str,
        initial_prompt: str,
        tools: list[dict[str, Any]] | None = None,
        tool_executor: Callable[[str, dict], str] | None = None,
        on_iteration: Callable[[LoopIteration], None] | None = None,
    ) -> LoopResult:
        """
        Run the full optimization loop.

        Args:
            task: The task to optimize for
            initial_prompt: Starting system prompt
            tools: Tool definitions for the agent
            tool_executor: Function to execute tool calls
            on_iteration: Optional callback after each iteration

        Returns:
            LoopResult with all iterations and final optimized prompt
        """
        result = LoopResult(task=task, final_prompt=initial_prompt)
        current_prompt = initial_prompt

        # Track best performing iteration
        best_score = 0.0
        best_prompt = initial_prompt
        best_iteration = 0
        consecutive_regressions = 0

        if self.config.verbose:
            console.print(Panel(
                f"[bold]Starting Optimization Loop[/bold]\n\n"
                f"Task: {task}\n"
                f"Max Iterations: {self.config.max_iterations}\n"
                f"Convergence Threshold: {self.config.convergence_threshold}%",
                title="Reasoning Trace Optimizer"
            ))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=not self.config.verbose,
        ) as progress:

            for i in range(self.config.max_iterations):
                task_id = progress.add_task(f"Iteration {i + 1}/{self.config.max_iterations}", total=4)

                # Step 1: Capture trace
                progress.update(task_id, description=f"[cyan]Iteration {i + 1}: Capturing trace...")
                trace = self.capture.run(
                    task=task,
                    system_prompt=current_prompt,
                    tools=tools,
                    tool_executor=tool_executor,
                )
                progress.advance(task_id)

                # Step 2: Analyze trace
                progress.update(task_id, description=f"[cyan]Iteration {i + 1}: Analyzing trace...")
                analysis = self.analyzer.analyze(trace)
                progress.advance(task_id)

                # Calculate iteration score
                iteration_score = self._calculate_score(trace, analysis)

                # Record initial score
                if i == 0:
                    result.initial_score = iteration_score
                    best_score = iteration_score
                    best_prompt = current_prompt

                # Step 3: Check convergence
                should_continue, reason = self._check_convergence(
                    iteration=i,
                    score=iteration_score,
                    prev_score=result.iterations[-1].analysis.overall_score if result.iterations else 0,
                    best_score=best_score,
                    consecutive_regressions=consecutive_regressions,
                )

                # Step 4: Optimize if continuing
                optimization = None
                if should_continue:
                    progress.update(task_id, description=f"[cyan]Iteration {i + 1}: Optimizing prompt...")
                    optimization = self.optimizer.optimize(
                        original_prompt=current_prompt,
                        analysis=analysis,
                        trace=trace,
                    )

                    # Check for excessive prompt growth
                    new_prompt = optimization.optimized_prompt
                    if len(new_prompt) > len(initial_prompt) * self.config.max_prompt_growth:
                        if self.config.verbose:
                            console.print(f"[yellow]Warning: Prompt grew too large ({len(new_prompt)} chars), limiting growth[/yellow]")
                        # Keep the current prompt instead of the bloated one
                        new_prompt = current_prompt

                    current_prompt = new_prompt
                    progress.advance(task_id)

                # Track best performing iteration AFTER optimization
                # This ensures we capture the optimized prompt, not the input prompt
                if iteration_score > best_score:
                    best_score = iteration_score
                    # Use the optimized prompt if available, otherwise the current prompt
                    if optimization and optimization.optimized_prompt != initial_prompt:
                        best_prompt = optimization.optimized_prompt
                    else:
                        best_prompt = current_prompt
                    best_iteration = i + 1
                    consecutive_regressions = 0
                elif iteration_score < best_score - self.config.regression_threshold:
                    consecutive_regressions += 1
                    if self.config.verbose:
                        console.print(f"[yellow]Warning: Score regressed from {best_score:.1f} to {iteration_score:.1f}[/yellow]")

                # Record iteration
                iteration = LoopIteration(
                    iteration=i + 1,
                    trace=trace,
                    analysis=analysis,
                    optimization=optimization,
                    task_completed=trace.success or False,
                    error_count=len([tc for tc in trace.tool_calls if not tc.success]),
                    token_usage=trace.total_tokens,
                )
                result.iterations.append(iteration)

                # Callback
                if on_iteration:
                    on_iteration(iteration)

                # Print iteration summary
                if self.config.verbose:
                    self._print_iteration_summary(iteration)

                # Save artifacts
                if self.config.save_artifacts:
                    self._save_iteration_artifacts(iteration, i + 1)

                # Check if we should stop
                if not should_continue:
                    if self.config.verbose:
                        console.print(f"\n[green]Stopping: {reason}[/green]")
                    result.converged = True
                    break

                progress.remove_task(task_id)

        # Finalize result - use best prompt if configured
        if self.config.use_best_prompt and best_score > result.iterations[-1].analysis.overall_score:
            result.final_prompt = best_prompt
            result.final_score = best_score
            if self.config.verbose:
                console.print(f"[green]Using best prompt from iteration {best_iteration} (score: {best_score:.1f})[/green]")
        else:
            result.final_prompt = current_prompt
            result.final_score = result.iterations[-1].analysis.overall_score if result.iterations else 0

        result.total_iterations = len(result.iterations)
        result.improvement_percentage = (
            (result.final_score - result.initial_score) / max(result.initial_score, 1) * 100
        )

        # Warn if prompt was never successfully optimized
        if result.final_prompt == initial_prompt:
            if self.config.verbose:
                console.print(
                    "[yellow]Warning: Final prompt unchanged from initial. "
                    "Optimization may have failed to parse model responses.[/yellow]"
                )
            # Check if any iteration actually produced a different prompt
            any_optimized = any(
                i.optimization and i.optimization.optimized_prompt != initial_prompt
                for i in result.iterations
                if i.optimization
            )
            if not any_optimized:
                console.print(
                    "[yellow]No successful prompt optimizations were extracted. "
                    "Check artifacts for raw optimizer responses.[/yellow]"
                )

        # Print final summary
        if self.config.verbose:
            self._print_final_summary(result)

        # Save final artifacts
        if self.config.save_artifacts:
            self._save_final_artifacts(result)

        return result

    def run_single(
        self,
        task: str,
        prompt: str,
        tools: list[dict[str, Any]] | None = None,
        tool_executor: Callable[[str, dict], str] | None = None,
    ) -> tuple[ReasoningTrace, AnalysisResult]:
        """
        Run a single capture + analysis cycle (no optimization).

        Useful for debugging or when you just want analysis without
        automatic optimization.

        Returns:
            Tuple of (trace, analysis)
        """
        trace = self.capture.run(
            task=task,
            system_prompt=prompt,
            tools=tools,
            tool_executor=tool_executor,
        )
        analysis = self.analyzer.analyze(trace)
        return trace, analysis

    def _calculate_score(
        self,
        trace: ReasoningTrace,
        analysis: AnalysisResult,
    ) -> float:
        """Calculate weighted score from trace and analysis."""
        success_score = 100 if trace.success else 0
        error_penalty = len([tc for tc in trace.tool_calls if not tc.success]) * 10

        weighted = (
            success_score * self.config.success_weight
            + analysis.overall_score * self.config.score_weight
            - error_penalty * self.config.error_weight
        )

        return max(0, min(100, weighted))

    def _check_convergence(
        self,
        iteration: int,
        score: float,
        prev_score: float,
        best_score: float = 0.0,
        consecutive_regressions: int = 0,
    ) -> tuple[bool, str]:
        """Check if optimization should continue."""
        # Check score threshold
        if score >= self.config.min_score_threshold:
            return False, f"Score {score:.1f} >= threshold {self.config.min_score_threshold}"

        # Check for consecutive regressions (stop if we've regressed twice in a row)
        if consecutive_regressions >= 2:
            return False, f"Consecutive regressions detected (best was {best_score:.1f})"

        # Check improvement threshold (after first iteration)
        if iteration > 0:
            improvement = score - prev_score
            if abs(improvement) < self.config.convergence_threshold and score >= prev_score:
                return False, f"Converged (improvement {improvement:.1f}% < threshold)"

        # Check max iterations
        if iteration >= self.config.max_iterations - 1:
            return False, f"Reached max iterations ({self.config.max_iterations})"

        return True, ""

    def _print_iteration_summary(self, iteration: LoopIteration) -> None:
        """Print summary of an iteration."""
        table = Table(title=f"Iteration {iteration.iteration} Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Task Completed", "Yes" if iteration.task_completed else "No")
        table.add_row("Overall Score", f"{iteration.analysis.overall_score:.1f}/100")
        table.add_row("Patterns Found", str(len(iteration.analysis.patterns)))
        table.add_row("Tool Errors", str(iteration.error_count))
        table.add_row("Token Usage", str(iteration.token_usage))

        if iteration.optimization:
            table.add_row(
                "Predicted Improvement",
                f"{iteration.optimization.predicted_improvement}%"
            )

        console.print(table)

    def _print_final_summary(self, result: LoopResult) -> None:
        """Print final optimization summary."""
        console.print("\n")
        panel_content = (
            f"[bold]Iterations:[/bold] {result.total_iterations}\n"
            f"[bold]Converged:[/bold] {'Yes' if result.converged else 'No'}\n"
            f"[bold]Initial Score:[/bold] {result.initial_score:.1f}\n"
            f"[bold]Final Score:[/bold] {result.final_score:.1f}\n"
            f"[bold]Improvement:[/bold] {result.improvement_percentage:+.1f}%"
        )
        console.print(Panel(panel_content, title="[green]Optimization Complete[/green]"))

    def _save_iteration_artifacts(self, iteration: LoopIteration, num: int) -> None:
        """Save iteration artifacts to disk."""
        base_path = Path(self.config.artifacts_dir) / f"iteration_{num}"
        base_path.mkdir(exist_ok=True)

        # Save trace
        with open(base_path / "trace.txt", "w") as f:
            f.write(format_trace_for_display(iteration.trace))

        # Save analysis
        with open(base_path / "analysis.txt", "w") as f:
            f.write(format_analysis_report(iteration.analysis))

        # Save optimization if present
        if iteration.optimization:
            with open(base_path / "optimization.txt", "w") as f:
                f.write(format_optimization_report(iteration.optimization))

            with open(base_path / "optimized_prompt.txt", "w") as f:
                f.write(iteration.optimization.optimized_prompt)

    def _save_final_artifacts(self, result: LoopResult) -> None:
        """Save final optimization artifacts."""
        base_path = Path(self.config.artifacts_dir)

        # Save final prompt
        with open(base_path / "final_prompt.txt", "w") as f:
            f.write(result.final_prompt)

        # Save summary JSON
        summary = {
            "task": result.task,
            "total_iterations": result.total_iterations,
            "converged": result.converged,
            "initial_score": result.initial_score,
            "final_score": result.final_score,
            "improvement_percentage": result.improvement_percentage,
            "timestamp": datetime.now().isoformat(),
        }
        with open(base_path / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)


def run_quick_optimization(
    task: str,
    initial_prompt: str,
    tools: list[dict[str, Any]] | None = None,
    tool_executor: Callable[[str, dict], str] | None = None,
    max_iterations: int = 3,
) -> str:
    """
    Quick helper function for one-shot optimization.

    Returns the optimized prompt directly.
    """
    config = LoopConfig(max_iterations=max_iterations, verbose=False)
    loop = OptimizationLoop(config=config)
    result = loop.run(task, initial_prompt, tools, tool_executor)
    return result.final_prompt
