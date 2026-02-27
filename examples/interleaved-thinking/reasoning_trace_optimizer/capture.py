"""
TraceCapture: Wraps M2.1 API to capture interleaved thinking traces.

This module provides the core functionality for executing agent tasks
through MiniMax M2.1 while capturing all reasoning traces for analysis.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Callable

import anthropic

from reasoning_trace_optimizer.models import (
    ReasoningTrace,
    ThinkingBlock,
    ToolCall,
)


class TraceCapture:
    """
    Captures reasoning traces from MiniMax M2.1's interleaved thinking.

    This class wraps the Anthropic SDK configured for M2.1 and captures
    all thinking blocks, tool calls, and responses during agent execution.

    Example:
        ```python
        capture = TraceCapture()
        trace = capture.run(
            task="What's the weather in San Francisco?",
            tools=[weather_tool],
            tool_executor=execute_tool
        )
        print(f"Captured {len(trace.thinking_blocks)} thinking blocks")
        ```
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.minimax.io/anthropic",
        model: str = "MiniMax-M2.1",
    ):
        """
        Initialize TraceCapture with M2.1 configuration.

        Args:
            api_key: MiniMax API key (defaults to ANTHROPIC_API_KEY env var)
            base_url: API base URL (international or China endpoint)
            model: Model to use (MiniMax-M2.1, MiniMax-M2.1-lightning, MiniMax-M2)
        """
        self.model = model
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
            base_url=base_url,
        )

    def run(
        self,
        task: str,
        system_prompt: str = "You are a helpful assistant.",
        tools: list[dict[str, Any]] | None = None,
        tool_executor: Callable[[str, dict], str] | None = None,
        max_turns: int = 10,
        max_tokens: int = 4096,
    ) -> ReasoningTrace:
        """
        Execute a task and capture the full reasoning trace.

        Args:
            task: The user task/query to execute
            system_prompt: System prompt for the agent
            tools: List of tool definitions in Anthropic format
            tool_executor: Function to execute tool calls (name, input) -> result
            max_turns: Maximum conversation turns before stopping
            max_tokens: Maximum tokens per response

        Returns:
            ReasoningTrace containing all thinking blocks, tool calls, and responses
        """
        trace = ReasoningTrace(
            session_id=str(uuid.uuid4()),
            task=task,
            system_prompt=system_prompt,
            model=self.model,
            started_at=datetime.now(),
        )

        messages = [{"role": "user", "content": task}]
        turn = 0

        try:
            while turn < max_turns:
                # Build request parameters
                params = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                    "messages": messages,
                }
                if tools:
                    params["tools"] = tools

                # Make API call
                response = self.client.messages.create(**params)

                # Process response content blocks
                thinking_blocks, text_blocks, tool_use_blocks = self._process_response(
                    response, turn, trace
                )

                # If no tool calls, we're done
                if not tool_use_blocks:
                    trace.final_response = (
                        text_blocks[0].text if text_blocks else None
                    )
                    trace.success = True
                    break

                # Append assistant response to history (CRITICAL for M2.1)
                messages.append({"role": "assistant", "content": response.content})

                # Execute tools and collect results
                tool_results = []
                for tool_block in tool_use_blocks:
                    result = self._execute_tool(
                        tool_block, tool_executor, turn, trace
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "content": result,
                        }
                    )

                # Add tool results to messages
                messages.append({"role": "user", "content": tool_results})

                turn += 1
                trace.total_turns = turn

            # Check if we hit max turns without completion
            if turn >= max_turns and not trace.success:
                trace.success = False
                trace.error = f"Reached maximum turns ({max_turns}) without completion"

        except Exception as e:
            trace.success = False
            trace.error = str(e)

        trace.completed_at = datetime.now()
        return trace

    def _process_response(
        self,
        response: anthropic.types.Message,
        turn: int,
        trace: ReasoningTrace,
    ) -> tuple[list, list, list]:
        """Process response content blocks and update trace."""
        thinking_blocks = []
        text_blocks = []
        tool_use_blocks = []

        for block in response.content:
            if block.type == "thinking":
                thinking = ThinkingBlock(
                    content=block.thinking,
                    turn_index=turn,
                    signature=getattr(block, "signature", None),
                )
                trace.thinking_blocks.append(thinking)
                thinking_blocks.append(block)

            elif block.type == "text":
                text_blocks.append(block)

            elif block.type == "tool_use":
                tool_use_blocks.append(block)

        # Update token count
        trace.total_tokens += response.usage.input_tokens + response.usage.output_tokens

        return thinking_blocks, text_blocks, tool_use_blocks

    def _execute_tool(
        self,
        tool_block: Any,
        executor: Callable[[str, dict], str] | None,
        turn: int,
        trace: ReasoningTrace,
    ) -> str:
        """Execute a tool call and record it in the trace."""
        tool_call = ToolCall(
            id=tool_block.id,
            name=tool_block.name,
            input=tool_block.input,
            turn_index=turn,
        )

        try:
            if executor:
                result = executor(tool_block.name, tool_block.input)
            else:
                result = f"[Mock result for {tool_block.name}]"

            tool_call.result = result
            tool_call.success = True

        except Exception as e:
            result = f"Error: {str(e)}"
            tool_call.result = result
            tool_call.success = False
            tool_call.error = str(e)

        trace.tool_calls.append(tool_call)

        # Link thinking to tool call
        if trace.thinking_blocks:
            last_thinking = trace.thinking_blocks[-1]
            if last_thinking.turn_index == turn:
                last_thinking.following_action = f"tool_use:{tool_block.name}"

        return result

    def run_streaming(
        self,
        task: str,
        system_prompt: str = "You are a helpful assistant.",
        tools: list[dict[str, Any]] | None = None,
        tool_executor: Callable[[str, dict], str] | None = None,
        max_turns: int = 10,
        max_tokens: int = 4096,
        on_thinking: Callable[[str], None] | None = None,
        on_text: Callable[[str], None] | None = None,
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> ReasoningTrace:
        """
        Execute a task with streaming output and capture reasoning trace.

        Similar to run() but streams thinking and text content in real-time
        via callback functions.

        Note: For multi-turn tool interactions, the non-streaming run() method
        is recommended as it provides more reliable trace capture. Use this
        method when you need real-time display of thinking/text content.

        Args:
            task: The user task/query to execute
            system_prompt: System prompt for the agent
            tools: List of tool definitions
            tool_executor: Function to execute tool calls
            max_turns: Maximum conversation turns
            max_tokens: Maximum tokens per response
            on_thinking: Callback for thinking content chunks
            on_text: Callback for text content chunks
            on_tool_call: Callback when tool is called (name, input)
            on_error: Callback when an error occurs (error message)

        Returns:
            ReasoningTrace containing the full captured trace
        """
        trace = ReasoningTrace(
            session_id=str(uuid.uuid4()),
            task=task,
            system_prompt=system_prompt,
            model=self.model,
            started_at=datetime.now(),
        )

        messages = [{"role": "user", "content": task}]
        turn = 0

        try:
            while turn < max_turns:
                params = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                    "messages": messages,
                    "stream": True,
                }
                if tools:
                    params["tools"] = tools

                # Collect streamed content
                thinking_buffer = ""
                text_buffer = ""
                tool_use_blocks = []
                current_content = []

                with self.client.messages.stream(**params) as stream:
                    for event in stream:
                        if event.type == "content_block_start":
                            if hasattr(event, "content_block"):
                                current_content.append(event.content_block)

                        elif event.type == "content_block_delta":
                            if hasattr(event, "delta"):
                                if event.delta.type == "thinking_delta":
                                    chunk = event.delta.thinking
                                    thinking_buffer += chunk
                                    if on_thinking:
                                        on_thinking(chunk)

                                elif event.delta.type == "text_delta":
                                    chunk = event.delta.text
                                    text_buffer += chunk
                                    if on_text:
                                        on_text(chunk)

                    # Get final message for tool_use blocks
                    final_message = stream.get_final_message()
                    for block in final_message.content:
                        if block.type == "tool_use":
                            tool_use_blocks.append(block)
                            if on_tool_call:
                                on_tool_call(block.name, block.input)

                # Record thinking block
                if thinking_buffer:
                    trace.thinking_blocks.append(
                        ThinkingBlock(
                            content=thinking_buffer,
                            turn_index=turn,
                        )
                    )

                # Update tokens
                trace.total_tokens += (
                    final_message.usage.input_tokens + final_message.usage.output_tokens
                )

                # If no tool calls, we're done
                if not tool_use_blocks:
                    trace.final_response = text_buffer or None
                    trace.success = True
                    break

                # Append to history
                messages.append({"role": "assistant", "content": final_message.content})

                # Execute tools
                tool_results = []
                for tool_block in tool_use_blocks:
                    result = self._execute_tool(tool_block, tool_executor, turn, trace)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "content": result,
                        }
                    )

                messages.append({"role": "user", "content": tool_results})
                turn += 1
                trace.total_turns = turn

            if turn >= max_turns and not trace.success:
                trace.success = False
                trace.error = f"Reached maximum turns ({max_turns})"

        except Exception as e:
            trace.success = False
            trace.error = str(e)
            if on_error:
                on_error(str(e))

        trace.completed_at = datetime.now()
        return trace


def format_trace_for_display(trace: ReasoningTrace) -> str:
    """Format a reasoning trace for human-readable display."""
    lines = [
        f"Session: {trace.session_id}",
        f"Task: {trace.task}",
        f"Model: {trace.model}",
        f"Status: {'Success' if trace.success else 'Failed'}",
        f"Turns: {trace.total_turns}",
        f"Tokens: {trace.total_tokens}",
        "",
        "=" * 60,
        "REASONING TRACE",
        "=" * 60,
    ]

    for i, thinking in enumerate(trace.thinking_blocks):
        lines.append(f"\n[Turn {thinking.turn_index}] Thinking:")
        lines.append("-" * 40)
        lines.append(thinking.content[:500] + "..." if len(thinking.content) > 500 else thinking.content)

        # Show tool calls at this turn
        turn_tools = trace.get_tool_calls_at_turn(thinking.turn_index)
        for tool in turn_tools:
            lines.append(f"\n  Tool: {tool.name}({json.dumps(tool.input)})")
            lines.append(f"  Result: {tool.result[:100]}..." if tool.result and len(tool.result) > 100 else f"  Result: {tool.result}")

    if trace.final_response:
        lines.append("\n" + "=" * 60)
        lines.append("FINAL RESPONSE")
        lines.append("=" * 60)
        lines.append(trace.final_response)

    if trace.error:
        lines.append("\n" + "=" * 60)
        lines.append("ERROR")
        lines.append("=" * 60)
        lines.append(trace.error)

    return "\n".join(lines)
