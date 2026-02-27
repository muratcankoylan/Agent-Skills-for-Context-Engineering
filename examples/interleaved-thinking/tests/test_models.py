"""Tests for data models."""

from datetime import datetime

from reasoning_trace_optimizer.models import (
    AnalysisResult,
    LoopResult,
    OptimizationResult,
    Pattern,
    PatternType,
    PromptDiff,
    ReasoningTrace,
    Severity,
    ThinkingBlock,
    ToolCall,
)


def test_thinking_block_creation():
    """Test ThinkingBlock creation with defaults."""
    block = ThinkingBlock(
        content="This is a test thinking block.",
        turn_index=0,
    )
    assert block.content == "This is a test thinking block."
    assert block.turn_index == 0
    assert block.token_count == 0
    assert isinstance(block.timestamp, datetime)


def test_tool_call_creation():
    """Test ToolCall creation."""
    tc = ToolCall(
        id="call_123",
        name="get_weather",
        input={"location": "San Francisco"},
        turn_index=1,
    )
    assert tc.id == "call_123"
    assert tc.name == "get_weather"
    assert tc.input["location"] == "San Francisco"
    assert tc.success is None


def test_reasoning_trace_creation():
    """Test ReasoningTrace creation and methods."""
    trace = ReasoningTrace(
        session_id="test-session",
        task="Test task",
        system_prompt="Test prompt",
    )

    # Add thinking block
    block = ThinkingBlock(content="Thinking...", turn_index=0)
    trace.thinking_blocks.append(block)

    # Add tool call
    tc = ToolCall(
        id="call_1",
        name="test_tool",
        input={},
        turn_index=0,
    )
    trace.tool_calls.append(tc)

    # Test methods
    assert trace.get_thinking_at_turn(0) == block
    assert trace.get_thinking_at_turn(1) is None
    assert len(trace.get_tool_calls_at_turn(0)) == 1
    assert len(trace.get_tool_calls_at_turn(1)) == 0


def test_pattern_creation():
    """Test Pattern creation."""
    pattern = Pattern(
        type=PatternType.CONTEXT_DEGRADATION,
        severity=Severity.HIGH,
        description="Model lost track of goal",
        evidence=["Evidence 1", "Evidence 2"],
        turn_indices=[2, 3],
        suggestion="Add explicit reminders",
        confidence=0.85,
    )
    assert pattern.type == PatternType.CONTEXT_DEGRADATION
    assert pattern.severity == Severity.HIGH
    assert pattern.confidence == 0.85


def test_analysis_result_creation():
    """Test AnalysisResult creation."""
    result = AnalysisResult(trace_id="test-trace")
    assert result.overall_score == 0.0
    assert len(result.patterns) == 0
    assert len(result.recommendations) == 0


def test_optimization_result_creation():
    """Test OptimizationResult creation."""
    result = OptimizationResult(
        original_prompt="Original",
        optimized_prompt="Optimized",
    )
    result.diffs.append(PromptDiff(
        section="instructions",
        original="Original text",
        optimized="Improved text",
        reason="Better clarity",
    ))
    assert len(result.diffs) == 1
    assert result.diffs[0].section == "instructions"


def test_loop_result_creation():
    """Test LoopResult creation."""
    result = LoopResult(task="Test task")
    assert result.total_iterations == 0
    assert result.converged is False
    assert result.improvement_percentage == 0.0


def test_pattern_types():
    """Test all PatternType values exist."""
    expected_types = [
        "context_degradation",
        "tool_confusion",
        "instruction_drift",
        "hallucination",
        "incomplete_reasoning",
        "tool_misuse",
        "goal_abandonment",
        "circular_reasoning",
        "premature_conclusion",
        "missing_validation",
    ]
    for type_name in expected_types:
        assert PatternType(type_name) is not None


def test_severity_levels():
    """Test all Severity levels exist."""
    assert Severity.LOW.value == "low"
    assert Severity.MEDIUM.value == "medium"
    assert Severity.HIGH.value == "high"
    assert Severity.CRITICAL.value == "critical"
