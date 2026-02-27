"""
Reasoning Trace Optimizer

Debug and optimize AI agents by analyzing reasoning traces
using MiniMax M2.1's interleaved thinking capabilities.
"""

from reasoning_trace_optimizer.models import (
    ReasoningTrace,
    ThinkingBlock,
    ToolCall,
    Pattern,
    PatternType,
    Severity,
    AnalysisResult,
    OptimizationResult,
    PromptDiff,
    LoopIteration,
    LoopResult,
)
from reasoning_trace_optimizer.capture import TraceCapture
from reasoning_trace_optimizer.analyzer import TraceAnalyzer
from reasoning_trace_optimizer.optimizer import PromptOptimizer
from reasoning_trace_optimizer.loop import OptimizationLoop, LoopConfig
from reasoning_trace_optimizer.skill_generator import SkillGenerator

__version__ = "0.1.0"

__all__ = [
    # Models
    "ReasoningTrace",
    "ThinkingBlock",
    "ToolCall",
    "Pattern",
    "PatternType",
    "Severity",
    "AnalysisResult",
    "OptimizationResult",
    "PromptDiff",
    "LoopIteration",
    "LoopResult",
    # Capture
    "TraceCapture",
    # Analyzer
    "TraceAnalyzer",
    # Optimizer
    "PromptOptimizer",
    # Loop
    "OptimizationLoop",
    "LoopConfig",
    # Skill Generator
    "SkillGenerator",
]
