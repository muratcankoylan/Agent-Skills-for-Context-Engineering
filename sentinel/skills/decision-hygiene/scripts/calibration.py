
import argparse
import json
import math
from typing import List, Dict, Any

def compute_calibration(decisions: List[Dict]) -> Dict[str, Any]:
    """Compute calibration metrics from resolved decisions."""
    resolved = [d for d in decisions if d.get("resolution", {}).get("status") == "resolved"]

    if len(resolved) < 5:
        return {
            "status": "insufficient_data", 
            "n": len(resolved), 
            "minimum": 5,
            "brier_score": None
        }

    # Brier Score (lower is better, 0 = perfect)
    brier_scores = []
    for d in resolved:
        try:
            predicted = d["prediction"]["predicted_probability"]
            actual = 1.0 if d["resolution"]["actual_outcome"] == "success" else 0.0
            brier_scores.append((predicted - actual) ** 2)
        except (KeyError, TypeError):
            continue

    brier = sum(brier_scores) / len(brier_scores) if brier_scores else 0.0

    # Overconfidence Index
    # Bucket predictions by confidence level, check if calibrated
    buckets = {"high_conf": [], "med_conf": [], "low_conf": []}
    for d in resolved:
        try:
            p = d["prediction"]["predicted_probability"]
            actual = 1.0 if d["resolution"]["actual_outcome"] == "success" else 0.0
            if p >= 0.8:
                buckets["high_conf"].append(actual)
            elif p >= 0.5:
                buckets["med_conf"].append(actual)
            else:
                buckets["low_conf"].append(actual)
        except (KeyError, TypeError):
            continue

    # For each bucket, compare predicted confidence vs. actual success rate
    overconfidence = {}
    expected_range = {"high_conf": 0.8, "med_conf": 0.65, "low_conf": 0.3}
    
    for bucket_name, actuals in buckets.items():
        if actuals:
            actual_rate = sum(actuals) / len(actuals)
            overconfidence[bucket_name] = {
                "expected": expected_range[bucket_name],
                "actual": round(actual_rate, 2),
                "gap": round(expected_range[bucket_name] - actual_rate, 2),
                "n": len(actuals)
            }

    # Per-domain breakdown
    domain_scores = {}
    for d in resolved:
        domain = d.get("domain", "general")
        if domain not in domain_scores:
            domain_scores[domain] = {"brier_sum": 0, "n": 0}
            
        try:
            predicted = d["prediction"]["predicted_probability"]
            actual = 1.0 if d["resolution"]["actual_outcome"] == "success" else 0.0
            domain_scores[domain]["brier_sum"] += (predicted - actual) ** 2
            domain_scores[domain]["n"] += 1
        except (KeyError, TypeError):
            continue

    final_domain_scores = {}
    for domain, s in domain_scores.items():
        if s["n"] > 0:
            final_domain_scores[domain] = {
                "brier": round(s["brier_sum"] / s["n"], 3),
                "n": s["n"]
            }

    return {
        "status": "calibrated",
        "brier_score": round(brier, 3),
        "total_resolved": len(resolved),
        "overconfidence": overconfidence,
        "domain_breakdown": final_domain_scores
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True, help="Path to decision-ledger.json")
    
    args = parser.parse_args()
    
    try:
        with open(args.ledger, 'r') as f:
            data = json.load(f)
            decisions = data.get("decisions", [])
            
        result = compute_calibration(decisions)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
