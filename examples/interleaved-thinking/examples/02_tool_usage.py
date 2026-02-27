"""
Example 2: Tool Usage with Trace Capture

Demonstrates how M2.1's interleaved thinking reasons between tool calls.
This is where interleaved thinking really shines - you can see the model
adapting to tool outputs in real-time.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

from reasoning_trace_optimizer import TraceCapture
from reasoning_trace_optimizer.capture import format_trace_for_display

# Load environment variables from the project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


# Define mock tools
TOOLS = [
    {
        "name": "get_weather",
        "description": "Get current weather for a location. Returns temperature and conditions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name, e.g., 'San Francisco, CA'",
                }
            },
            "required": ["location"],
        },
    },
    {
        "name": "get_forecast",
        "description": "Get 3-day weather forecast for a location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days (1-3)",
                    "default": 3,
                },
            },
            "required": ["location"],
        },
    },
]


# Mock tool executor
def execute_tool(name: str, input_data: dict) -> str:
    """Execute a mock tool and return results."""
    if name == "get_weather":
        location = input_data.get("location", "Unknown")
        # Simulate different weather for different cities
        if "san francisco" in location.lower():
            return json.dumps({
                "location": location,
                "temperature": "18°C",
                "conditions": "Foggy",
                "humidity": "85%",
            })
        elif "new york" in location.lower():
            return json.dumps({
                "location": location,
                "temperature": "22°C",
                "conditions": "Partly cloudy",
                "humidity": "60%",
            })
        else:
            return json.dumps({
                "location": location,
                "temperature": "20°C",
                "conditions": "Clear",
                "humidity": "50%",
            })

    elif name == "get_forecast":
        location = input_data.get("location", "Unknown")
        days = input_data.get("days", 3)
        forecast = []
        for i in range(days):
            forecast.append({
                "day": i + 1,
                "high": f"{20 + i * 2}°C",
                "low": f"{12 + i}°C",
                "conditions": ["Sunny", "Cloudy", "Rainy"][i % 3],
            })
        return json.dumps({
            "location": location,
            "forecast": forecast,
        })

    return json.dumps({"error": f"Unknown tool: {name}"})


def main():
    """Run a task with tools and observe interleaved thinking."""

    capture = TraceCapture(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        base_url="https://api.minimax.io/anthropic",
        model="MiniMax-M2.1",
    )

    task = """Compare the current weather in San Francisco and New York City.
    Then tell me which city would be better for outdoor activities this weekend."""

    system_prompt = """You are a helpful weather assistant.
    Use the available tools to get accurate weather information.
    Always provide specific data to support your recommendations."""

    print("=" * 60)
    print("TOOL USAGE WITH INTERLEAVED THINKING")
    print("=" * 60)
    print(f"\nTask: {task}")
    print(f"\nTools available: {', '.join(t['name'] for t in TOOLS)}")
    print("\nCapturing trace with tool usage...\n")

    # Capture the trace (using non-streaming for reliability)
    trace = capture.run(
        task=task,
        system_prompt=system_prompt,
        tools=TOOLS,
        tool_executor=execute_tool,
        max_turns=10,
    )

    print("\n\n" + "=" * 60)
    print("TRACE ANALYSIS")
    print("=" * 60)

    print(f"\nSuccess: {trace.success}")
    print(f"Total Turns: {trace.total_turns}")
    print(f"Thinking Blocks: {len(trace.thinking_blocks)}")
    print(f"Tool Calls: {len(trace.tool_calls)}")

    # Show how thinking evolved between tool calls
    print("\n" + "=" * 60)
    print("THINKING EVOLUTION ACROSS TOOL CALLS")
    print("=" * 60)

    for i, thinking in enumerate(trace.thinking_blocks):
        print(f"\n[Turn {thinking.turn_index}] Thinking Block {i + 1}")
        print("-" * 40)

        # Show what tool was called after this thinking
        turn_tools = trace.get_tool_calls_at_turn(thinking.turn_index)
        if turn_tools:
            print(f"Following action: Called {', '.join(t.name for t in turn_tools)}")
        else:
            print("Following action: Generated response")

        # Show key reasoning points (first 300 chars)
        print(f"\nReasoning preview:\n{thinking.content[:300]}...")

    # Show tool call results
    print("\n" + "=" * 60)
    print("TOOL CALL SUMMARY")
    print("=" * 60)

    for tc in trace.tool_calls:
        status = "✅" if tc.success else "❌"
        print(f"\n{status} {tc.name}")
        print(f"   Input: {json.dumps(tc.input)}")
        print(f"   Result: {tc.result[:100]}..." if tc.result and len(tc.result) > 100 else f"   Result: {tc.result}")

    # Final response
    if trace.final_response:
        print("\n" + "=" * 60)
        print("FINAL RESPONSE")
        print("=" * 60)
        print(trace.final_response)


if __name__ == "__main__":
    main()
