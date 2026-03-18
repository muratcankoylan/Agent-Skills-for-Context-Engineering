
import math
import argparse
import json
import statistics
from typing import List, Dict, Any, Union

def simple_divergence(scores: List[float], scale_min: float, scale_max: float) -> Dict[str, Any]:
    """Algorithm 1: Normalized standard deviation for ratings."""
    n = len(scores)
    if n < 2:
         return {"error": "Need at least 2 scores"}
         
    mean = sum(scores) / n
    variance = sum((s - mean) ** 2 for s in scores) / n
    std_dev = math.sqrt(variance)
    
    scale_range = scale_max - scale_min
    if scale_range == 0:
        divergence = 0.0
    else:
        divergence = std_dev / (scale_range / 2)

    interpretation = (
        "VERY_LOW" if divergence < 0.15 else
        "LOW" if divergence < 0.30 else
        "MODERATE" if divergence < 0.50 else
        "HIGH" if divergence < 0.70 else
        "VERY_HIGH"
    )

    return {
        "mean": round(mean, 2),
        "std_dev": round(std_dev, 2),
        "divergence_score": round(divergence, 3),
        "interpretation": interpretation
    }

def coefficient_of_variation(estimates: List[float]) -> Dict[str, Any]:
    """Algorithm 2: CV for estimates with units."""
    n = len(estimates)
    if n < 2:
        return {"error": "Need at least 2 estimates"}
        
    mean = sum(estimates) / n
    if mean == 0:
        return {"error": "Mean is 0, cannot calculate CV"}
        
    stdev = statistics.stdev(estimates)
    cv = (stdev / mean) * 100
    
    interpretation = (
        "VERY_LOW" if cv < 10 else
        "LOW" if cv < 20 else
        "MODERATE" if cv < 40 else
        "HIGH" if cv < 70 else
        "VERY_HIGH"
    )
    
    return {
        "mean": round(mean, 2),
        "std_dev": round(stdev, 2),
        "cv_percent": round(cv, 1),
        "interpretation": interpretation
    }

def range_based_noise(assessments: List[float]) -> Dict[str, Any]:
    """Algorithm 3: Quick range ratio."""
    if not assessments:
        return {"error": "No assessments"}
        
    min_val = min(assessments)
    max_val = max(assessments)
    
    # Avoid division by zero
    if min_val == 0:
        ratio = float('inf') if max_val > 0 else 1.0
    else:
        ratio = max_val / min_val
        
    return {
        "min": min_val,
        "max": max_val,
        "ratio": round(ratio, 2)
    }

def pairwise_agreement(rankings: List[List[str]]) -> Dict[str, Any]:
    """Algorithm 4: Agreement percentage for rankings (simplified)."""
    # This is a complex metric, simplifying for "Top 1 match"
    if not rankings:
        return {"error": "No rankings"}
        
    n_voters = len(rankings)
    first_choices = [r[0] for r in rankings if r]
    
    if not first_choices:
        return {"agreement": 0.0}
        
    # Find most common first choice
    from collections import Counter
    counts = Counter(first_choices)
    top_choice, count = counts.most_common(1)[0]
    
    agreement = (count / n_voters) * 100
    
    return {
        "top_choice_agreement_pct": round(agreement, 1),
        "consensus_winner": top_choice
    }

def quartile_spread(assessments: List[float]) -> Dict[str, Any]:
    """Algorithm 5: IQR-based noise score."""
    if len(assessments) < 4:
        return {"error": "Need at least 4 for quartiles"}
        
    sorted_vals = sorted(assessments)
    q1 = statistics.quantiles(sorted_vals, n=4)[0]
    q3 = statistics.quantiles(sorted_vals, n=4)[2]
    iqr = q3 - q1
    
    return {
        "q1": q1,
        "q3": q3,
        "iqr": iqr
    }

def calculate_noise(inputs):
    """Dispatch based on input type"""
    alg = inputs.get("algorithm", "divergence")
    data = inputs.get("data", [])
    
    if alg == "divergence":
        return simple_divergence(data, inputs.get("min", 1), inputs.get("max", 10))
    elif alg == "cv":
        return coefficient_of_variation(data)
    elif alg == "range":
        return range_based_noise(data)
    elif alg == "ranking":
        return pairwise_agreement(data)
    elif alg == "iqr":
        return quartile_spread(data)
    else:
        return {"error": f"Unknown algorithm {alg}"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, help="JSON input string")
    args = parser.parse_args()
    
    try:
        inputs = json.loads(args.json)
        result = calculate_noise(inputs)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
