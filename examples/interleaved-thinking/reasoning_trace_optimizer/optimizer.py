"""
PromptOptimizer: Generates improved prompts based on trace analysis.

Uses M2.1 to synthesize analysis results into concrete prompt improvements,
with full reasoning transparency via interleaved thinking.
"""

import json
import os
from typing import Any

import anthropic

from reasoning_trace_optimizer.models import (
    AnalysisResult,
    OptimizationResult,
    PromptDiff,
    ReasoningTrace,
)


OPTIMIZER_SYSTEM_PROMPT = """You are an expert prompt engineer specializing in AI agent optimization.

Your task is to improve agent prompts based on reasoning trace analysis.
You have access to:
1. The original prompt that was used
2. Analysis of how the agent reasoned (its thinking trace)
3. Detected patterns and issues
4. Specific recommendations

Your goal is to create an IMPROVED prompt that:
- Addresses identified weaknesses
- Maintains existing strengths
- Prevents detected failure patterns
- Improves clarity and specificity

When optimizing, consider:
- Adding explicit guardrails for common failure modes
- Clarifying ambiguous instructions
- Adding examples for complex behaviors
- Restructuring for better context positioning
- Adding validation steps where missing

Provide the optimized prompt with clear explanations of changes."""


OPTIMIZATION_PROMPT_TEMPLATE = """Optimize the following agent prompt based on trace analysis:

## Original Task
{task}

## Original System Prompt
```
{original_prompt}
```

## Analysis Results

### Overall Score: {overall_score}/100

### Detected Patterns
{patterns}

### Weaknesses
{weaknesses}

### Recommendations
{recommendations}

### Analyzer's Reasoning
{analyzer_thinking}

---

Provide your optimization as JSON:
```json
{{
    "optimized_prompt": "<the full improved prompt>",
    "diffs": [
        {{
            "section": "<which part changed, e.g., 'instructions', 'guardrails', 'examples'>",
            "original": "<original text or 'N/A' if new>",
            "optimized": "<new/changed text>",
            "reason": "<why this change helps>"
        }}
    ],
    "key_changes": [
        "<summary of major change 1>",
        "<summary of major change 2>"
    ],
    "predicted_improvement": 15,
    "confidence": 0.75
}}
```

Think carefully about what changes will have the biggest impact on agent performance."""


class PromptOptimizer:
    """
    Optimizes agent prompts based on reasoning trace analysis.

    Uses M2.1's interleaved thinking to generate thoughtful improvements
    with full transparency into the optimization reasoning.

    Example:
        ```python
        optimizer = PromptOptimizer()
        result = optimizer.optimize(
            original_prompt=system_prompt,
            analysis=analysis_result,
            trace=reasoning_trace
        )

        print(f"Predicted improvement: {result.predicted_improvement}%")
        print(f"New prompt:\\n{result.optimized_prompt}")
        ```
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.minimax.io/anthropic",
        model: str = "MiniMax-M2.1",
    ):
        """
        Initialize PromptOptimizer with M2.1 configuration.

        Args:
            api_key: MiniMax API key
            base_url: API endpoint
            model: Model for optimization
        """
        self.model = model
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
            base_url=base_url,
        )

    def optimize(
        self,
        original_prompt: str,
        analysis: AnalysisResult,
        trace: ReasoningTrace | None = None,
        max_tokens: int = 8192,
    ) -> OptimizationResult:
        """
        Generate an optimized prompt based on analysis.

        Args:
            original_prompt: The original system prompt to improve
            analysis: Analysis results from TraceAnalyzer
            trace: Optional original trace for additional context
            max_tokens: Maximum tokens for response

        Returns:
            OptimizationResult with new prompt and change details
        """
        # Format analysis for prompt
        patterns_text = self._format_patterns(analysis)
        weaknesses_text = "\n".join(f"- {w}" for w in analysis.weaknesses)
        recommendations_text = "\n".join(f"- {r}" for r in analysis.recommendations)

        prompt = OPTIMIZATION_PROMPT_TEMPLATE.format(
            task=trace.task if trace else "Unknown task",
            original_prompt=original_prompt,
            overall_score=analysis.overall_score,
            patterns=patterns_text,
            weaknesses=weaknesses_text or "None identified",
            recommendations=recommendations_text or "None provided",
            analyzer_thinking=analysis.analyzer_thinking[:2000] if analysis.analyzer_thinking else "Not available",
        )

        # Call M2.1 for optimization
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=OPTIMIZER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract thinking and response
        optimizer_thinking = ""
        optimization_text = ""

        for block in response.content:
            if block.type == "thinking":
                optimizer_thinking = block.thinking
            elif block.type == "text":
                optimization_text = block.text

        # Parse the response
        result = self._parse_optimization_response(optimization_text, original_prompt)
        result.optimizer_thinking = optimizer_thinking

        return result

    def optimize_iterative(
        self,
        original_prompt: str,
        analyses: list[AnalysisResult],
        traces: list[ReasoningTrace],
    ) -> OptimizationResult:
        """
        Optimize based on multiple analysis iterations.

        Synthesizes patterns across multiple runs for more robust improvements.

        Args:
            original_prompt: The original system prompt
            analyses: List of analysis results from multiple runs
            traces: Corresponding reasoning traces

        Returns:
            OptimizationResult incorporating learnings from all iterations
        """
        # Aggregate patterns across all analyses
        all_patterns = []
        all_weaknesses = []
        all_recommendations = []
        avg_score = 0

        for analysis in analyses:
            all_patterns.extend(analysis.patterns)
            all_weaknesses.extend(analysis.weaknesses)
            all_recommendations.extend(analysis.recommendations)
            avg_score += analysis.overall_score

        avg_score /= len(analyses) if analyses else 1

        # Create aggregated analysis
        aggregated = AnalysisResult(
            trace_id="aggregated",
            patterns=all_patterns,
            overall_score=avg_score,
            weaknesses=list(set(all_weaknesses)),  # Deduplicate
            recommendations=list(set(all_recommendations)),
        )

        # Optimize based on aggregated analysis
        return self.optimize(
            original_prompt=original_prompt,
            analysis=aggregated,
            trace=traces[0] if traces else None,
        )

    def suggest_tool_improvements(
        self,
        tools: list[dict[str, Any]],
        analysis: AnalysisResult,
        trace: ReasoningTrace,
    ) -> dict[str, str]:
        """
        Suggest improvements for tool definitions based on analysis.

        Args:
            tools: Original tool definitions
            analysis: Analysis results
            trace: Original reasoning trace

        Returns:
            Dict mapping tool names to suggested description improvements
        """
        tool_issues = [
            p for p in analysis.patterns
            if p.type.value in ("tool_confusion", "tool_misuse")
        ]

        if not tool_issues:
            return {}

        prompt = f"""Based on these tool usage issues:

{self._format_patterns_for_tools(tool_issues)}

And the original tool definitions:
{json.dumps(tools, indent=2)}

Suggest improved tool descriptions. Respond as JSON:
```json
{{
    "tool_name": "improved description that addresses the confusion"
}}
```"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        for block in response.content:
            if block.type == "text":
                try:
                    text = block.text
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0]
                    return json.loads(text)
                except json.JSONDecodeError:
                    pass

        return {}

    def _format_patterns(self, analysis: AnalysisResult) -> str:
        """Format patterns for optimization prompt."""
        if not analysis.patterns:
            return "No significant patterns detected."

        parts = []
        for p in analysis.patterns:
            parts.append(
                f"[{p.severity.value.upper()}] {p.type.value}\n"
                f"  Description: {p.description}\n"
                f"  Evidence: {', '.join(p.evidence[:2])}\n"
                f"  Suggestion: {p.suggestion}"
            )
        return "\n\n".join(parts)

    def _format_patterns_for_tools(self, patterns: list) -> str:
        """Format tool-related patterns."""
        return "\n".join(
            f"- {p.type.value}: {p.description}" for p in patterns
        )

    def _parse_optimization_response(
        self,
        response_text: str,
        original_prompt: str,
    ) -> OptimizationResult:
        """Parse the JSON optimization response with fallback extraction."""
        result = OptimizationResult(
            original_prompt=original_prompt,
            optimized_prompt=original_prompt,  # Default to original if parsing fails
        )

        try:
            json_text = response_text
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0]

            data = json.loads(json_text)

            result.optimized_prompt = data.get("optimized_prompt", original_prompt)
            result.predicted_improvement = data.get("predicted_improvement", 0)
            result.confidence = data.get("confidence", 0.5)
            result.key_changes = data.get("key_changes", [])

            # Parse diffs
            for d in data.get("diffs", []):
                diff = PromptDiff(
                    section=d.get("section", "unknown"),
                    original=d.get("original", ""),
                    optimized=d.get("optimized", ""),
                    reason=d.get("reason", ""),
                )
                result.diffs.append(diff)

        except (json.JSONDecodeError, KeyError) as e:
            # Fallback: try to extract optimized_prompt directly from response
            extracted_prompt = self._fallback_extract_prompt(response_text)
            if extracted_prompt and extracted_prompt != original_prompt:
                result.optimized_prompt = extracted_prompt
                result.key_changes = [f"JSON parsing failed ({type(e).__name__}), extracted prompt via fallback"]
                result.confidence = 0.3  # Lower confidence for fallback extraction
            else:
                result.key_changes = [f"Optimization parsing failed ({type(e).__name__}) - using original prompt"]

        return result

    def _fallback_extract_prompt(self, response_text: str) -> str | None:
        """
        Fallback method to extract optimized prompt when JSON parsing fails.

        Tries multiple strategies to find the prompt content.
        """
        import re

        # Strategy 1: Look for "optimized_prompt": "..." pattern
        match = re.search(r'"optimized_prompt"\s*:\s*"([^"]+)"', response_text, re.DOTALL)
        if match:
            # Unescape the string
            return match.group(1).replace('\\n', '\n').replace('\\"', '"')

        # Strategy 2: Look for content between specific markers
        markers = [
            ('## Optimized Prompt', '##'),
            ('**Optimized Prompt**', '**'),
            ('OPTIMIZED PROMPT:', '\n\n'),
            ('Here is the improved prompt:', '\n\n---'),
        ]

        for start_marker, end_marker in markers:
            if start_marker in response_text:
                start_idx = response_text.find(start_marker) + len(start_marker)
                remaining = response_text[start_idx:].strip()
                if end_marker in remaining:
                    end_idx = remaining.find(end_marker)
                    extracted = remaining[:end_idx].strip()
                    if len(extracted) > 50:  # Minimum length check
                        return extracted

        # Strategy 3: Look for a substantial code block that might be the prompt
        code_blocks = re.findall(r'```(?:text|markdown)?\n(.*?)```', response_text, re.DOTALL)
        for block in code_blocks:
            # Skip JSON blocks, look for prose blocks that could be prompts
            if not block.strip().startswith('{') and len(block) > 100:
                return block.strip()

        return None


def format_optimization_report(result: OptimizationResult) -> str:
    """Format an optimization result as a human-readable report."""
    lines = [
        "=" * 60,
        "PROMPT OPTIMIZATION REPORT",
        "=" * 60,
        "",
        f"Predicted Improvement: {result.predicted_improvement}%",
        f"Confidence: {result.confidence * 100:.0f}%",
        "",
    ]

    if result.key_changes:
        lines.append("Key Changes:")
        for change in result.key_changes:
            lines.append(f"  - {change}")
        lines.append("")

    if result.diffs:
        lines.append("Detailed Changes:")
        for diff in result.diffs:
            lines.append(f"\n  [{diff.section}]")
            if diff.original and diff.original != "N/A":
                lines.append(f"    Before: {diff.original[:100]}...")
            lines.append(f"    After: {diff.optimized[:100]}...")
            lines.append(f"    Reason: {diff.reason}")

    lines.extend([
        "",
        "=" * 60,
        "OPTIMIZED PROMPT",
        "=" * 60,
        result.optimized_prompt,
    ])

    return "\n".join(lines)
