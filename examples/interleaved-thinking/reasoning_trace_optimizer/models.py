"""
Core data models for reasoning trace optimization.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PatternType(Enum):
    """Types of patterns detected in reasoning traces."""

    CONTEXT_DEGRADATION = "context_degradation"
    TOOL_CONFUSION = "tool_confusion"
    INSTRUCTION_DRIFT = "instruction_drift"
    HALLUCINATION = "hallucination"
    INCOMPLETE_REASONING = "incomplete_reasoning"
    TOOL_MISUSE = "tool_misuse"
    GOAL_ABANDONMENT = "goal_abandonment"
    CIRCULAR_REASONING = "circular_reasoning"
    PREMATURE_CONCLUSION = "premature_conclusion"
    MISSING_VALIDATION = "missing_validation"


class Severity(Enum):
    """Severity levels for detected patterns."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ThinkingBlock:
    """A single thinking/reasoning block from the model."""

    content: str
    turn_index: int
    timestamp: datetime = field(default_factory=datetime.now)
    token_count: int = 0
    signature: str | None = None  # M2.1 thinking signature

    # Context at time of thinking
    preceding_tool_call: str | None = None
    preceding_tool_result: str | None = None
    following_action: str | None = None  # tool_use, text, or end_turn


@dataclass
class ToolCall:
    """A tool call made by the agent."""

    id: str
    name: str
    input: dict[str, Any]
    turn_index: int
    result: str | None = None
    success: bool | None = None
    error: str | None = None


@dataclass
class ReasoningTrace:
    """Complete reasoning trace for an agent session."""

    session_id: str
    task: str
    system_prompt: str
    thinking_blocks: list[ThinkingBlock] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    final_response: str | None = None

    # Metadata
    model: str = "MiniMax-M2.1"
    total_turns: int = 0
    total_tokens: int = 0
    success: bool | None = None
    error: str | None = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def get_thinking_at_turn(self, turn: int) -> ThinkingBlock | None:
        """Get thinking block at specific turn."""
        for block in self.thinking_blocks:
            if block.turn_index == turn:
                return block
        return None

    def get_tool_calls_at_turn(self, turn: int) -> list[ToolCall]:
        """Get all tool calls at specific turn."""
        return [tc for tc in self.tool_calls if tc.turn_index == turn]


@dataclass
class Pattern:
    """A detected pattern in reasoning traces."""

    type: PatternType
    severity: Severity
    description: str
    evidence: list[str]  # Excerpts from thinking blocks
    turn_indices: list[int]
    suggestion: str
    confidence: float  # 0.0 to 1.0


@dataclass
class AnalysisResult:
    """Result of analyzing a reasoning trace."""

    trace_id: str
    patterns: list[Pattern] = field(default_factory=list)

    # Scores (0-100)
    reasoning_clarity: float = 0.0
    goal_adherence: float = 0.0
    tool_usage_quality: float = 0.0
    error_recovery: float = 0.0
    overall_score: float = 0.0

    # Feedback
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    # Analysis metadata
    analyzer_model: str = "MiniMax-M2.1"
    analyzer_thinking: str = ""  # The analyzer's own reasoning


@dataclass
class PromptDiff:
    """Difference between original and optimized prompt."""

    section: str  # e.g., "system_prompt", "tool_description", "instruction"
    original: str
    optimized: str
    reason: str


@dataclass
class OptimizationResult:
    """Result of prompt optimization."""

    original_prompt: str
    optimized_prompt: str
    diffs: list[PromptDiff] = field(default_factory=list)

    # Improvement predictions
    predicted_improvement: float = 0.0  # Percentage
    confidence: float = 0.0

    # Optimizer reasoning
    optimizer_thinking: str = ""
    key_changes: list[str] = field(default_factory=list)


@dataclass
class LoopIteration:
    """Single iteration of the optimization loop."""

    iteration: int
    trace: ReasoningTrace
    analysis: AnalysisResult
    optimization: OptimizationResult | None

    # Metrics
    task_completed: bool = False
    error_count: int = 0
    token_usage: int = 0


@dataclass
class LoopResult:
    """Result of running the full optimization loop."""

    task: str
    iterations: list[LoopIteration] = field(default_factory=list)

    # Final state
    final_prompt: str = ""
    converged: bool = False
    total_iterations: int = 0

    # Improvement metrics
    initial_score: float = 0.0
    final_score: float = 0.0
    improvement_percentage: float = 0.0

    # Generated artifacts
    generated_skill_path: str | None = None
