"""
SkillGenerator: Converts optimization insights into shareable Agent Skills.

Transforms the learnings from optimization loops into reusable skills
following the Agent Skills template format.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic

from reasoning_trace_optimizer.models import (
    AnalysisResult,
    LoopResult,
    Pattern,
    PatternType,
)


SKILL_TEMPLATE = '''---
name: {skill_name}
description: "{description}"
---

# {title}

{intro}

## When to Activate

{activation}

## Core Concepts

{concepts}

## Patterns to Avoid

{anti_patterns}

## Recommended Practices

{practices}

## Guidelines

{guidelines}

## Examples

{examples}

---

## Skill Metadata

**Generated**: {date}
**Source**: Reasoning Trace Optimizer
**Optimization Iterations**: {iterations}
**Score Improvement**: {initial_score:.1f} → {final_score:.1f} (+{improvement:.1f}%)
'''


GENERATOR_SYSTEM_PROMPT = """You are an expert at converting agent optimization insights into reusable skills.

Your task is to analyze optimization results and generate a shareable Agent Skill that
captures the learnings so other developers can benefit.

The skill should:
1. Describe WHEN to use these learnings (activation triggers)
2. Explain the PATTERNS to avoid (anti-patterns found)
3. Provide CONCRETE practices that improved performance
4. Give VERIFIABLE guidelines (things that can be checked)
5. Include EXAMPLES showing before/after improvements

Write in a clear, direct style. Focus on actionable guidance, not theory."""


def _format_list_to_markdown(items: list | str) -> str:
    """Convert a list to markdown bullet points."""
    if isinstance(items, str):
        return items
    if not items:
        return ""

    import re
    formatted = []
    for item in items:
        # Strip any existing leading bullet points/dashes to avoid duplication
        cleaned = re.sub(r'^[-*•]\s*', '', str(item).strip())
        formatted.append(f"- {cleaned}")
    return "\n".join(formatted)


def _format_numbered_list_to_markdown(items: list | str) -> str:
    """Convert a list to markdown numbered list."""
    if isinstance(items, str):
        return items
    if not items:
        return ""

    import re
    formatted = []
    for i, item in enumerate(items):
        # Strip any existing leading numbers (e.g., "1. ", "2. ") to avoid duplication
        cleaned = re.sub(r'^\d+\.\s*', '', str(item).strip())
        formatted.append(f"{i+1}. {cleaned}")
    return "\n".join(formatted)


def _format_examples_to_markdown(examples: list | str) -> str:
    """Convert example dicts to markdown format."""
    if isinstance(examples, str):
        return examples
    if not examples:
        return ""

    parts = []
    for i, ex in enumerate(examples):
        if isinstance(ex, dict):
            parts.append(f"### Example {i+1}: {ex.get('context', 'Scenario')}")
            if ex.get('before'):
                parts.append(f"\n**Before:**\n```\n{ex['before']}\n```")
            if ex.get('after'):
                parts.append(f"\n**After:**\n```\n{ex['after']}\n```")
            if ex.get('improvement'):
                parts.append(f"\n**Improvement:** {ex['improvement']}")
            parts.append("")
        else:
            parts.append(f"- {ex}")
    return "\n".join(parts)


class SkillGenerator:
    """
    Generates shareable Agent Skills from optimization results.

    Converts the learnings from optimization loops into the standard
    Agent Skills format for sharing with other developers.

    Example:
        ```python
        generator = SkillGenerator()
        skill_path = generator.generate(
            result=loop_result,
            skill_name="web-search-agent",
            output_dir="./generated_skills"
        )
        print(f"Generated skill at: {skill_path}")
        ```
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.minimax.io/anthropic",
        model: str = "MiniMax-M2.1",
    ):
        """
        Initialize SkillGenerator.

        Args:
            api_key: MiniMax API key
            base_url: API endpoint
            model: Model for skill generation
        """
        self.model = model
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
            base_url=base_url,
        )

    def generate(
        self,
        result: LoopResult,
        skill_name: str,
        output_dir: str = "./generated_skills",
        title: str | None = None,
    ) -> str:
        """
        Generate an Agent Skill from optimization results.

        Args:
            result: The optimization loop result
            skill_name: Name for the skill (lowercase-with-hyphens)
            output_dir: Directory to save the skill
            title: Optional human-readable title

        Returns:
            Path to the generated SKILL.md file
        """
        # Extract insights from all iterations
        all_patterns = self._collect_patterns(result)
        all_recommendations = self._collect_recommendations(result)
        key_changes = self._collect_key_changes(result)

        # Generate skill content using M2.1
        content = self._generate_skill_content(
            task=result.task,
            patterns=all_patterns,
            recommendations=all_recommendations,
            key_changes=key_changes,
            initial_prompt=result.iterations[0].trace.system_prompt if result.iterations else "",
            final_prompt=result.final_prompt,
        )

        # Format content - convert lists to markdown
        formatted_content = {
            "activation": _format_list_to_markdown(content.get("activation", "")),
            "concepts": _format_list_to_markdown(content.get("concepts", "")),
            "anti_patterns": _format_list_to_markdown(content.get("anti_patterns", "")),
            "practices": _format_list_to_markdown(content.get("practices", "")),
            "guidelines": _format_numbered_list_to_markdown(content.get("guidelines", "")),
            "examples": _format_examples_to_markdown(content.get("examples", "")),
        }

        # Format using template
        skill_content = SKILL_TEMPLATE.format(
            skill_name=skill_name,
            description=content.get("description", f"Optimized practices for {skill_name}"),
            title=title or content.get("title", skill_name.replace("-", " ").title()),
            intro=content.get("intro", ""),
            activation=formatted_content["activation"],
            concepts=formatted_content["concepts"],
            anti_patterns=formatted_content["anti_patterns"],
            practices=formatted_content["practices"],
            guidelines=formatted_content["guidelines"],
            examples=formatted_content["examples"],
            date=datetime.now().strftime("%Y-%m-%d"),
            iterations=result.total_iterations,
            initial_score=result.initial_score,
            final_score=result.final_score,
            improvement=result.improvement_percentage,
        )

        # Save skill
        skill_dir = Path(output_dir) / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_path = skill_dir / "SKILL.md"
        with open(skill_path, "w") as f:
            f.write(skill_content)

        # Save optimization data as reference
        self._save_references(skill_dir, result, content)

        return str(skill_path)

    def generate_from_analysis(
        self,
        analyses: list[AnalysisResult],
        skill_name: str,
        task_description: str,
        output_dir: str = "./generated_skills",
    ) -> str:
        """
        Generate a skill from multiple analysis results (without full loop).

        Useful when you have analysis data but didn't run the full optimization loop.

        Args:
            analyses: List of analysis results
            skill_name: Name for the skill
            task_description: Description of the task context
            output_dir: Output directory

        Returns:
            Path to generated skill
        """
        # Aggregate patterns and recommendations
        all_patterns = []
        all_recommendations = []

        for analysis in analyses:
            all_patterns.extend(analysis.patterns)
            all_recommendations.extend(analysis.recommendations)

        content = self._generate_skill_content(
            task=task_description,
            patterns=all_patterns,
            recommendations=list(set(all_recommendations)),
            key_changes=[],
            initial_prompt="",
            final_prompt="",
        )

        # Calculate average score
        avg_score = sum(a.overall_score for a in analyses) / len(analyses) if analyses else 0

        skill_content = SKILL_TEMPLATE.format(
            skill_name=skill_name,
            description=content.get("description", f"Learnings for {skill_name}"),
            title=content.get("title", skill_name.replace("-", " ").title()),
            intro=content.get("intro", ""),
            activation=content.get("activation", ""),
            concepts=content.get("concepts", ""),
            anti_patterns=content.get("anti_patterns", ""),
            practices=content.get("practices", ""),
            guidelines=content.get("guidelines", ""),
            examples=content.get("examples", ""),
            date=datetime.now().strftime("%Y-%m-%d"),
            iterations=len(analyses),
            initial_score=avg_score,
            final_score=avg_score,
            improvement=0,
        )

        skill_dir = Path(output_dir) / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_path = skill_dir / "SKILL.md"
        with open(skill_path, "w") as f:
            f.write(skill_content)

        return str(skill_path)

    def _collect_patterns(self, result: LoopResult) -> list[Pattern]:
        """Collect all unique patterns from iterations."""
        patterns = []
        seen = set()

        for iteration in result.iterations:
            for pattern in iteration.analysis.patterns:
                key = (pattern.type, pattern.description[:50])
                if key not in seen:
                    patterns.append(pattern)
                    seen.add(key)

        return patterns

    def _collect_recommendations(self, result: LoopResult) -> list[str]:
        """Collect all unique recommendations."""
        recommendations = []
        seen = set()

        for iteration in result.iterations:
            for rec in iteration.analysis.recommendations:
                if rec not in seen:
                    recommendations.append(rec)
                    seen.add(rec)

        return recommendations

    def _collect_key_changes(self, result: LoopResult) -> list[str]:
        """Collect all key changes from optimizations."""
        changes = []

        for iteration in result.iterations:
            if iteration.optimization:
                changes.extend(iteration.optimization.key_changes)

        return changes

    def _generate_skill_content(
        self,
        task: str,
        patterns: list[Pattern],
        recommendations: list[str],
        key_changes: list[str],
        initial_prompt: str,
        final_prompt: str,
    ) -> dict[str, str]:
        """Use M2.1 to generate skill content sections."""
        patterns_text = "\n".join(
            f"- [{p.severity.value}] {p.type.value}: {p.description}"
            for p in patterns
        )

        recommendations_text = "\n".join(f"- {r}" for r in recommendations)
        changes_text = "\n".join(f"- {c}" for c in key_changes)

        prompt = f"""Generate an Agent Skill based on these optimization insights:

## Task Context
{task}

## Patterns Detected (Anti-patterns to avoid)
{patterns_text or "No significant patterns detected"}

## Recommendations from Analysis
{recommendations_text or "No specific recommendations"}

## Key Changes That Improved Performance
{changes_text or "No recorded changes"}

## Prompt Evolution
Initial: {initial_prompt[:500] if initial_prompt else "N/A"}...
Final: {final_prompt[:500] if final_prompt else "N/A"}...

---

Generate skill content as JSON:
```json
{{
    "title": "Human-readable skill title",
    "description": "One-line description for skill discovery (what triggers this skill)",
    "intro": "2-3 sentence introduction explaining what this skill teaches",
    "activation": "Bullet points of when to activate this skill (specific keywords, task types)",
    "concepts": "Core concepts this skill covers (3-5 key ideas)",
    "anti_patterns": "Patterns to AVOID - formatted as markdown list with descriptions",
    "practices": "Recommended practices - formatted as markdown list",
    "guidelines": "Numbered verifiable guidelines (things that can be checked)",
    "examples": "1-2 concrete before/after examples showing improvement"
}}
```"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=GENERATOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse response
        for block in response.content:
            if block.type == "text":
                try:
                    text = block.text
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0]
                    return json.loads(text)
                except json.JSONDecodeError:
                    pass

        # Return defaults if parsing fails
        return {
            "title": "Generated Agent Skill",
            "description": f"Optimized practices for {task}",
            "intro": "This skill contains learnings from automated prompt optimization.",
            "activation": "- When working on similar tasks\n- When debugging agent failures",
            "concepts": "See recommendations section.",
            "anti_patterns": patterns_text or "No patterns identified.",
            "practices": recommendations_text or "No specific practices.",
            "guidelines": "1. Review the anti-patterns before implementation\n2. Apply recommended practices",
            "examples": "See optimization artifacts for detailed examples.",
        }

    def _save_references(
        self,
        skill_dir: Path,
        result: LoopResult,
        content: dict[str, str],
    ) -> None:
        """Save reference materials alongside the skill."""
        refs_dir = skill_dir / "references"
        refs_dir.mkdir(exist_ok=True)

        # Save optimization summary
        summary = {
            "task": result.task,
            "iterations": result.total_iterations,
            "initial_score": result.initial_score,
            "final_score": result.final_score,
            "improvement": result.improvement_percentage,
            "converged": result.converged,
            "generated_at": datetime.now().isoformat(),
        }
        with open(refs_dir / "optimization_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        # Save final optimized prompt
        with open(refs_dir / "optimized_prompt.txt", "w") as f:
            f.write(result.final_prompt)

        # Save all patterns found
        patterns_data = []
        for iteration in result.iterations:
            for p in iteration.analysis.patterns:
                patterns_data.append({
                    "type": p.type.value,
                    "severity": p.severity.value,
                    "description": p.description,
                    "suggestion": p.suggestion,
                    "iteration": iteration.iteration,
                })

        with open(refs_dir / "patterns_found.json", "w") as f:
            json.dump(patterns_data, f, indent=2)


def generate_skill_from_loop(
    result: LoopResult,
    skill_name: str,
    output_dir: str = "./generated_skills",
) -> str:
    """
    Quick helper to generate a skill from optimization results.

    Args:
        result: Optimization loop result
        skill_name: Name for the skill
        output_dir: Output directory

    Returns:
        Path to generated skill
    """
    generator = SkillGenerator()
    return generator.generate(result, skill_name, output_dir)
