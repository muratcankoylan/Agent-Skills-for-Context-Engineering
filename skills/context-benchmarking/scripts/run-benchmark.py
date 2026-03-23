"""
Automated Context Benchmarking Pipeline
========================================
Runs a test set against an agent configuration using LLM-as-Judge scoring.
Implements the context-benchmarking skill in practice.

Usage:
    python run_benchmark.py --test-set test_cases.json --baseline baseline.json
    python run_benchmark.py --test-set test_cases.json --update-baseline

Requirements:
    pip install anthropic
    export ANTHROPIC_API_KEY=your-key
"""

import json
import time
import argparse
import os
import sys
from typing import Any

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package not installed. Run: pip install anthropic")
    sys.exit(1)


# ── Configuration ─────────────────────────────────────────────────────────────

MODEL = "claude-haiku-4-5-20251001"   # cheapest model — keeps benchmark costs low
RECALL_THRESHOLD = 0.80               # below this = regression failure
REGRESSION_TOLERANCE = 0.05           # allow up to 5% drop from baseline before failing
MAX_TOKENS = 512                      # judge responses are short structured JSON


# ── LLM Judge ─────────────────────────────────────────────────────────────────

def score_with_judge(client: anthropic.Anthropic, original: str, output: str, expected_facts: list[str]) -> dict:
    """
    Uses an LLM to score whether expected facts survived compression/retrieval.
    Returns per-fact scores and an overall recall score.
    """
    facts_formatted = "\n".join(f"- {f}" for f in expected_facts)

    prompt = f"""You are an evaluation judge. Your job is to check whether key facts from an original context are preserved in an agent's output.

Original context:
{original}

Agent output:
{output}

Expected facts that should be present:
{facts_formatted}

For each expected fact, score it 1 if clearly present in the agent output, or 0 if missing or significantly distorted.

Return ONLY valid JSON in this exact format, with no explanation:
{{"scores": [{{"fact": "<fact text>", "score": 0, "reason": "<one sentence why>"}}]}}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    result = json.loads(raw)
    scores = result["scores"]
    recall = sum(s["score"] for s in scores) / len(scores) if scores else 0.0
    return {"recall": recall, "per_fact": scores}


# ── Benchmark Runner ───────────────────────────────────────────────────────────

def run_benchmark(test_cases: list[dict], client: anthropic.Anthropic) -> dict:
    """
    Runs all test cases and returns aggregated results.
    Each test case must have: id, input, question, expected_facts
    """
    results = []
    total_latency = 0.0

    print(f"\nRunning {len(test_cases)} test cases...\n")

    for i, case in enumerate(test_cases):
        case_id = case["id"]
        context_input = case["input"]
        question = case["question"]
        expected_facts = case["expected_facts"]

        print(f"  [{i+1}/{len(test_cases)}] {case_id}...", end=" ", flush=True)

        # Simulate agent processing the context (compress, retrieve, respond)
        start = time.time()
        agent_output = call_agent(client, context_input, question)
        latency = time.time() - start
        total_latency += latency

        # Score the output with the judge
        score = score_with_judge(client, context_input, agent_output, expected_facts)

        results.append({
            "id": case_id,
            "recall": score["recall"],
            "latency_s": round(latency, 3),
            "per_fact": score["per_fact"],
            "agent_output": agent_output
        })

        status = "PASS" if score["recall"] >= RECALL_THRESHOLD else "FAIL"
        print(f"[{status}] recall={score['recall']:.2f} latency={latency:.2f}s")

    overall_recall = sum(r["recall"] for r in results) / len(results)
    avg_latency = total_latency / len(results)

    return {
        "overall_recall": round(overall_recall, 4),
        "avg_latency_s": round(avg_latency, 3),
        "passed": overall_recall >= RECALL_THRESHOLD,
        "cases": results
    }


def call_agent(client: anthropic.Anthropic, context: str, question: str) -> str:
    """
    Calls the agent with a context + question.
    In a real pipeline, replace this with your actual agent call
    (e.g., compressed context retrieval, memory system lookup, etc.)
    """
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system="You are a helpful assistant. Answer questions based only on the provided context.",
        messages=[{
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {question}"
        }]
    )
    return response.content[0].text.strip()


# ── Regression Check ───────────────────────────────────────────────────────────

def check_regression(current: dict, baseline: dict) -> tuple[bool, str]:
    """
    Compares current results against baseline.
    Returns (passed, message).
    """
    baseline_recall = baseline.get("overall_recall", 0)
    current_recall = current["overall_recall"]
    min_acceptable = baseline_recall * (1 - REGRESSION_TOLERANCE)

    if current_recall < min_acceptable:
        return False, (
            f"REGRESSION DETECTED: recall dropped from {baseline_recall:.4f} "
            f"to {current_recall:.4f} (threshold: {min_acceptable:.4f})"
        )

    improvement = current_recall - baseline_recall
    sign = "+" if improvement >= 0 else ""
    return True, f"No regression. recall={current_recall:.4f} ({sign}{improvement:.4f} vs baseline)"


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run context benchmarking pipeline")
    parser.add_argument("--test-set", required=True, help="Path to test_cases.json")
    parser.add_argument("--baseline", default="baseline.json", help="Path to baseline results file")
    parser.add_argument("--update-baseline", action="store_true", help="Save results as new baseline")
    parser.add_argument("--output", default="benchmark_results.json", help="Path to save results")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Load test cases
    with open(args.test_set) as f:
        test_cases = json.load(f)
    print(f"Loaded {len(test_cases)} test cases from {args.test_set}")

    # Run benchmark
    results = run_benchmark(test_cases, client)

    # Save results
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {args.output}")

    # Regression check
    if os.path.exists(args.baseline) and not args.update_baseline:
        with open(args.baseline) as f:
            baseline = json.load(f)
        passed, message = check_regression(results, baseline)
        print(f"\nRegression check: {message}")
        if not passed:
            sys.exit(1)
    else:
        print(f"\nNo baseline found at {args.baseline} — skipping regression check.")

    # Update baseline if requested
    if args.update_baseline:
        with open(args.baseline, "w") as f:
            json.dump({"overall_recall": results["overall_recall"], "avg_latency_s": results["avg_latency_s"]}, f, indent=2)
        print(f"Baseline updated: {args.baseline}")

    # Final summary
    print(f"\n{'='*50}")
    print(f"Overall recall : {results['overall_recall']:.4f}")
    print(f"Avg latency    : {results['avg_latency_s']:.3f}s")
    print(f"Status         : {'PASSED' if results['passed'] else 'FAILED'}")
    print(f"{'='*50}\n")

    if not results["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()