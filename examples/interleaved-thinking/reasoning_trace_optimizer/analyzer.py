"""
TraceAnalyzer: Analyzes reasoning traces to detect patterns and issues.

Uses M2.1's own interleaved thinking to analyze agent reasoning traces,
detecting patterns like context degradation, tool confusion, and instruction drift.
"""

import json
import os
from typing import Any

import anthropic

from reasoning_trace_optimizer.models import (
    AnalysisResult,
    Pattern,
    PatternType,
    ReasoningTrace,
    Severity,
)


ANALYSIS_SYSTEM_PROMPT = """You are an expert AI agent debugger specializing in analyzing reasoning traces.

Your task is to analyze an agent's interleaved thinking trace and identify:
1. **Patterns of failure** - detect specific failure modes with evidence
2. **Quality scores** - rate the agent's reasoning on multiple dimensions
3. **Actionable recommendations** - specific improvements for prompts/instructions

## Pattern Definitions

Detect these patterns with specific evidence from thinking blocks:

- **context_degradation**: Agent loses or forgets information from earlier in the conversation
  - Look for: Repeated questions, contradicting earlier statements, missing key details
- **tool_confusion**: Agent misunderstands what a tool does or how to use it
  - Look for: Wrong tool selection, incorrect parameters, misinterpreting results
- **instruction_drift**: Agent gradually deviates from original instructions/persona
  - Look for: Changing behavior, ignoring constraints, different tone over time
- **hallucination**: Agent generates information not supported by context or tools
  - Look for: Made-up facts, fabricated tool results, unsourced claims
- **incomplete_reasoning**: Agent reaches conclusions without thorough analysis
  - Look for: Skipped steps, missing validation, superficial exploration
- **tool_misuse**: Agent uses tools incorrectly or inefficiently
  - Look for: Redundant calls, wrong parameters, unused results
- **goal_abandonment**: Agent stops pursuing the original objective
  - Look for: Topic drift, giving up, switching goals without reason
- **circular_reasoning**: Agent repeats similar actions without progress
  - Look for: Same queries repeated, looping behavior, no new information
- **premature_conclusion**: Agent concludes before completing the task
  - Look for: Early stops, incomplete answers, skipped requirements
- **missing_validation**: Agent doesn't verify results or assumptions
  - Look for: No cross-checking, accepting first result, no error handling

## Analysis Focus

You have access to the FULL reasoning trace including all thinking blocks between tool calls.
This gives you unique insight into HOW the agent reasons, not just what it outputs.

For each thinking block, examine:
- What is the agent's current understanding?
- How does it interpret tool results?
- What alternatives does it consider?
- Does it maintain awareness of the original goal?

Provide your analysis in the specified JSON format with concrete evidence."""


ANALYSIS_PROMPT_TEMPLATE = """Analyze the following agent reasoning trace:

## Task
{task}

## System Prompt Given to Agent
{system_prompt}

## Reasoning Trace
{trace}

## Tool Calls Made
{tool_calls}

## Final Outcome
Success: {success}
Final Response: {final_response}
Error (if any): {error}

---

Provide your analysis as JSON with this exact structure:
```json
{{
    "patterns": [
        {{
            "type": "<one of: context_degradation, tool_confusion, instruction_drift, hallucination, incomplete_reasoning, tool_misuse, goal_abandonment, circular_reasoning, premature_conclusion, missing_validation>",
            "severity": "<one of: low, medium, high, critical>",
            "description": "<what the pattern is>",
            "evidence": ["<excerpt from thinking>", "<another excerpt>"],
            "turn_indices": [0, 2],
            "suggestion": "<how to fix this>",
            "confidence": 0.85
        }}
    ],
    "scores": {{
        "reasoning_clarity": 75,
        "goal_adherence": 80,
        "tool_usage_quality": 60,
        "error_recovery": 50,
        "overall": 66
    }},
    "strengths": ["<strength 1>", "<strength 2>"],
    "weaknesses": ["<weakness 1>", "<weakness 2>"],
    "recommendations": [
        "<specific actionable recommendation>",
        "<another recommendation>"
    ]
}}
```

Think carefully about each aspect before providing your analysis."""


class TraceAnalyzer:
    """
    Analyzes reasoning traces using M2.1 to detect patterns and score quality.

    The analyzer uses M2.1's interleaved thinking to deeply understand
    the agent's reasoning process and identify issues that wouldn't be
    visible from outputs alone.

    Example:
        ```python
        analyzer = TraceAnalyzer()
        result = analyzer.analyze(trace)

        print(f"Overall score: {result.overall_score}")
        for pattern in result.patterns:
            print(f"Found: {pattern.type.value} ({pattern.severity.value})")
        ```
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.minimax.io/anthropic",
        model: str = "MiniMax-M2.1",
    ):
        """
        Initialize TraceAnalyzer with M2.1 configuration.

        Args:
            api_key: MiniMax API key
            base_url: API endpoint
            model: Model for analysis (M2.1 recommended for best results)
        """
        self.model = model
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
            base_url=base_url,
        )

    def analyze(
        self,
        trace: ReasoningTrace,
        max_tokens: int = 8192,
    ) -> AnalysisResult:
        """
        Analyze a reasoning trace and return detailed analysis.

        Args:
            trace: The reasoning trace to analyze
            max_tokens: Maximum tokens for analysis response

        Returns:
            AnalysisResult with patterns, scores, and recommendations
        """
        # Format trace for analysis
        trace_text = self._format_trace_for_analysis(trace)
        tool_calls_text = self._format_tool_calls(trace)

        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            task=trace.task,
            system_prompt=trace.system_prompt,
            trace=trace_text,
            tool_calls=tool_calls_text,
            success=trace.success,
            final_response=trace.final_response or "None",
            error=trace.error or "None",
        )

        # Call M2.1 for analysis
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract thinking and text from response
        analyzer_thinking = ""
        analysis_text = ""

        for block in response.content:
            if block.type == "thinking":
                analyzer_thinking = block.thinking
            elif block.type == "text":
                analysis_text = block.text

        # Parse the JSON response
        result = self._parse_analysis_response(analysis_text, trace.session_id)
        result.analyzer_thinking = analyzer_thinking
        result.analyzer_model = self.model

        return result

    def analyze_batch(
        self,
        traces: list[ReasoningTrace],
    ) -> list[AnalysisResult]:
        """Analyze multiple traces and return results."""
        return [self.analyze(trace) for trace in traces]

    def quick_score(
        self,
        trace: ReasoningTrace,
    ) -> float:
        """
        Get a quick overall score without full pattern analysis.

        Useful for optimization loops where you need fast feedback.

        Args:
            trace: The reasoning trace to score

        Returns:
            Overall score from 0-100
        """
        quick_prompt = f"""Rate this agent's performance from 0-100 based on its reasoning trace.

Task: {trace.task}
Success: {trace.success}
Turns: {trace.total_turns}

Thinking excerpts:
{self._get_thinking_excerpts(trace, max_chars=2000)}

Respond with ONLY a number from 0-100."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=100,
            messages=[{"role": "user", "content": quick_prompt}],
        )

        # Extract score from response
        for block in response.content:
            if block.type == "text":
                try:
                    score = float(block.text.strip())
                    return min(100, max(0, score))
                except ValueError:
                    pass

        return 50.0  # Default middle score if parsing fails

    def _format_trace_for_analysis(self, trace: ReasoningTrace) -> str:
        """Format thinking blocks for analysis."""
        parts = []
        for i, thinking in enumerate(trace.thinking_blocks):
            parts.append(f"[Turn {thinking.turn_index}] Thinking:")
            parts.append(thinking.content)
            parts.append("")

        return "\n".join(parts)

    def _format_tool_calls(self, trace: ReasoningTrace) -> str:
        """Format tool calls for analysis."""
        if not trace.tool_calls:
            return "No tool calls made."

        parts = []
        for tc in trace.tool_calls:
            status = "Success" if tc.success else f"Failed: {tc.error}"
            parts.append(
                f"- {tc.name}({json.dumps(tc.input)}) -> {status}\n"
                f"  Result: {tc.result[:200] if tc.result else 'None'}..."
            )

        return "\n".join(parts)

    def _get_thinking_excerpts(self, trace: ReasoningTrace, max_chars: int = 2000) -> str:
        """Get excerpts from thinking blocks."""
        excerpts = []
        remaining = max_chars

        for thinking in trace.thinking_blocks:
            if remaining <= 0:
                break
            excerpt = thinking.content[:remaining]
            excerpts.append(f"[Turn {thinking.turn_index}]: {excerpt}")
            remaining -= len(excerpt) + 20

        return "\n\n".join(excerpts)

    def _parse_analysis_response(
        self,
        response_text: str,
        trace_id: str,
    ) -> AnalysisResult:
        """Parse the JSON analysis response from M2.1."""
        result = AnalysisResult(trace_id=trace_id)

        try:
            # Extract JSON from response (may have markdown code blocks)
            json_text = response_text
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0]

            data = json.loads(json_text)

            # Parse patterns
            for p in data.get("patterns", []):
                try:
                    pattern = Pattern(
                        type=PatternType(p["type"]),
                        severity=Severity(p["severity"]),
                        description=p["description"],
                        evidence=p.get("evidence", []),
                        turn_indices=p.get("turn_indices", []),
                        suggestion=p.get("suggestion", ""),
                        confidence=p.get("confidence", 0.5),
                    )
                    result.patterns.append(pattern)
                except (KeyError, ValueError):
                    continue

            # Parse scores
            scores = data.get("scores", {})
            result.reasoning_clarity = scores.get("reasoning_clarity", 0)
            result.goal_adherence = scores.get("goal_adherence", 0)
            result.tool_usage_quality = scores.get("tool_usage_quality", 0)
            result.error_recovery = scores.get("error_recovery", 0)
            result.overall_score = scores.get("overall", 0)

            # Parse feedback
            result.strengths = data.get("strengths", [])
            result.weaknesses = data.get("weaknesses", [])
            result.recommendations = data.get("recommendations", [])

        except (json.JSONDecodeError, KeyError) as e:
            # If parsing fails, try fallback extraction and set reasonable defaults
            result = self._fallback_parse_analysis(response_text, trace_id, str(e))

        # Warn if score is suspiciously low (likely parsing failure)
        if result.overall_score == 0 and not result.patterns:
            result.weaknesses.append("WARNING: Analysis may have failed - score is 0 with no patterns detected")
            # Try to extract a score from the response text as fallback
            fallback_score = self._extract_fallback_score(response_text)
            if fallback_score > 0:
                result.overall_score = fallback_score
                result.recommendations.append(f"Score extracted via fallback: {fallback_score}")

        return result

    def _fallback_parse_analysis(
        self,
        response_text: str,
        trace_id: str,
        error_msg: str,
    ) -> AnalysisResult:
        """Fallback parsing when JSON extraction fails."""
        import re

        result = AnalysisResult(trace_id=trace_id)

        # Try to extract score from text patterns like "Overall Score: 75" or "overall": 75
        score_patterns = [
            r'overall["\s:]+(\d+)',
            r'Overall Score[:\s]+(\d+)',
            r'"overall"[:\s]+(\d+)',
            r'Score[:\s]+(\d+)/100',
        ]

        for pattern in score_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                result.overall_score = min(100, max(0, int(match.group(1))))
                break

        # If still no score, use a neutral default (not 0)
        if result.overall_score == 0:
            result.overall_score = 50  # Neutral default instead of 0

        result.recommendations = [
            f"Analysis parsing failed ({error_msg}). Using fallback extraction.",
            "Consider re-running analysis if results seem inconsistent."
        ]
        result.weaknesses = ["JSON parsing failed - analysis may be incomplete"]

        return result

    def _extract_fallback_score(self, response_text: str) -> float:
        """Extract a score from response text when JSON parsing fails."""
        import re

        patterns = [
            r'overall["\s:]+(\d+)',
            r'Overall Score[:\s]+(\d+)',
            r'"overall"[:\s]+(\d+)',
            r'(\d+)/100',
            r'score[:\s]+(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                if 0 <= score <= 100:
                    return float(score)

        return 0.0


def format_analysis_report(analysis: AnalysisResult) -> str:
    """Format an analysis result as a human-readable report."""
    lines = [
        "=" * 60,
        "REASONING TRACE ANALYSIS REPORT",
        "=" * 60,
        "",
        f"Overall Score: {analysis.overall_score}/100",
        "",
        "Scores:",
        f"  - Reasoning Clarity: {analysis.reasoning_clarity}/100",
        f"  - Goal Adherence: {analysis.goal_adherence}/100",
        f"  - Tool Usage Quality: {analysis.tool_usage_quality}/100",
        f"  - Error Recovery: {analysis.error_recovery}/100",
        "",
    ]

    if analysis.patterns:
        lines.append("Detected Patterns:")
        for p in analysis.patterns:
            lines.append(f"\n  [{p.severity.value.upper()}] {p.type.value}")
            lines.append(f"    {p.description}")
            lines.append(f"    Suggestion: {p.suggestion}")

    if analysis.strengths:
        lines.append("\nStrengths:")
        for s in analysis.strengths:
            lines.append(f"  + {s}")

    if analysis.weaknesses:
        lines.append("\nWeaknesses:")
        for w in analysis.weaknesses:
            lines.append(f"  - {w}")

    if analysis.recommendations:
        lines.append("\nRecommendations:")
        for i, r in enumerate(analysis.recommendations, 1):
            lines.append(f"  {i}. {r}")

    return "\n".join(lines)
