"""
Example 1: Basic Trace Capture

Demonstrates capturing reasoning traces from M2.1 for a simple task.
This shows how interleaved thinking provides visibility into agent decisions.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from reasoning_trace_optimizer import TraceCapture
from reasoning_trace_optimizer.capture import format_trace_for_display

# Load environment variables from the project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def main():
    """Run a simple task and capture the reasoning trace."""

    # Initialize capture with M2.1
    capture = TraceCapture(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        base_url="https://api.minimax.io/anthropic",
        model="MiniMax-M2.1",
    )

    # Define a simple task
    task = "Explain what interleaved thinking is and why it matters for AI agents."
    system_prompt = "You are an AI researcher explaining concepts clearly."

    print("=" * 60)
    print("BASIC TRACE CAPTURE EXAMPLE")
    print("=" * 60)
    print(f"\nTask: {task}")
    print(f"System Prompt: {system_prompt}")
    print("\nCapturing reasoning trace...\n")

    # Capture the trace
    trace = capture.run(
        task=task,
        system_prompt=system_prompt,
        max_turns=5,
    )

    # Display the trace
    print(format_trace_for_display(trace))

    # Summary statistics
    print("\n" + "=" * 60)
    print("TRACE STATISTICS")
    print("=" * 60)
    print(f"Session ID: {trace.session_id}")
    print(f"Model: {trace.model}")
    print(f"Success: {trace.success}")
    print(f"Total Turns: {trace.total_turns}")
    print(f"Thinking Blocks: {len(trace.thinking_blocks)}")
    print(f"Tool Calls: {len(trace.tool_calls)}")
    print(f"Total Tokens: {trace.total_tokens}")

    # Show each thinking block summary
    if trace.thinking_blocks:
        print("\n" + "=" * 60)
        print("THINKING BLOCK SUMMARIES")
        print("=" * 60)
        for i, thinking in enumerate(trace.thinking_blocks):
            print(f"\n[Turn {thinking.turn_index}] ({len(thinking.content)} chars)")
            # Show first 200 chars
            preview = thinking.content[:200].replace("\n", " ")
            print(f"  Preview: {preview}...")


if __name__ == "__main__":
    main()
