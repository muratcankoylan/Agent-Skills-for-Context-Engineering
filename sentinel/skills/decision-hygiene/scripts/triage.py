
import argparse
import json
import os

def calculate_triage(stakes: int, complexity: int, time_pressure: int,
                     expertise: int, reversibility: int,
                     group: bool = False, advocacy_mode: bool = False,
                     novelty: int = 1, commitment_horizon: int = 1):
    """
    Deterministic triage scoring - v8.1

    New dimensions vs v8.0:
    - group: collective decision? Activates group-facilitator, adds social biases
    - advocacy_mode: pitching rather than evaluating? Changes bias pre-selection
    - novelty: how unprecedented (1-5) Reduces confidence in base rates
    - commitment_horizon: duration of commitment (1=days, 5=years+) Activates temporal-auditor

    Fixed: Emergency override no longer bypasses structure entirely.
    High time pressure now routes to RAPID_STRUCTURE, not QUICK_CHECK.
    Cognitive research is clear: time pressure INCREASES bias activity.
    Less structure under pressure is the wrong response.
    """

    for val in [stakes, complexity, time_pressure, expertise, reversibility]:
        if not (1 <= val <= 5):
            return {"error": "All scores must be between 1 and 5"}
    for val in [novelty, commitment_horizon]:
        if not (1 <= val <= 5):
            return {"error": "novelty and commitment_horizon must be between 1 and 5"}

    expertise_score = (6 - expertise)

    total = (stakes * 3) + (complexity * 2) + (time_pressure * 1) + \
            (expertise_score * 1.5) + (reversibility * 2)

    group_addition = 8 if group else 0
    advocacy_addition = 5 if advocacy_mode else 0
    novelty_addition = (novelty - 1) * 1.5
    horizon_addition = (commitment_horizon - 1) * 2

    max_possible = 74.5
    total_with_modifiers = total + group_addition + advocacy_addition + novelty_addition + horizon_addition
    normalized = (total_with_modifiers / max_possible) * 100

    # FIXED emergency override - high time pressure = RAPID_STRUCTURE not QUICK_CHECK
    if time_pressure >= 5:
        protocol = "RAPID_STRUCTURE"
    elif normalized >= 78:
        protocol = "FULL_MAP"
    elif normalized >= 60:
        protocol = "STANDARD_MAP"
    elif normalized >= 40:
        protocol = "LITE_PROTOCOL"
    elif normalized >= 20:
        protocol = "QUICK_CHECK"
    else:
        protocol = "NO_PROTOCOL"

    agent_flags = {
        "activate_group_facilitator": group,
        "activate_temporal_auditor": commitment_horizon >= 3 or protocol in ["FULL_MAP", "STANDARD_MAP"],
        "activate_scope_checker": protocol in ["FULL_MAP", "STANDARD_MAP"],
        "reduce_reality_checker_confidence": novelty >= 4,
        "advocacy_mode_warning": advocacy_mode,
    }

    additional_bias_categories = []
    if group:
        additional_bias_categories.append("social_group")
    if advocacy_mode:
        additional_bias_categories.append("motivated_reasoning")
    if novelty >= 4:
        additional_bias_categories.append("novelty_risk")
    if commitment_horizon >= 4:
        additional_bias_categories.append("temporal")

    bias_category_ids = {
        "social_group": [15, 66, 71, 87, 89],
        "motivated_reasoning": [12, 13, 28, 95],
        "novelty_risk": [65, 3, 68, 83],
        "temporal": [52, 61, 98, 67]
    }

    additional_bias_ids = []
    for cat in additional_bias_categories:
        additional_bias_ids.extend(bias_category_ids.get(cat, []))

    notes = []
    if protocol == "RAPID_STRUCTURE":
        notes.append("Time pressure detected. RAPID_STRUCTURE: 3-dim MAP + 3-mode pre-mortem. High pressure = maximum bias risk.")
    if group:
        notes.append("Group decision. Run /sentinel-group for collective protocol.")
    if advocacy_mode:
        notes.append("Advocacy mode active. Motivated reasoning risk elevated. Analysis will challenge your framing.")

    return {
        "raw_score": round(total_with_modifiers, 1),
        "normalized_score": round(normalized, 1),
        "recommended_protocol": protocol,
        "scores": {
            "stakes": stakes,
            "complexity": complexity,
            "time_pressure": time_pressure,
            "expertise_match": expertise,
            "reversibility": reversibility,
            "group": group,
            "advocacy_mode": advocacy_mode,
            "novelty": novelty,
            "commitment_horizon": commitment_horizon
        },
        "agent_flags": agent_flags,
        "additional_bias_ids": list(set(additional_bias_ids)),
        "protocol_note": " | ".join(notes) if notes else None
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentinel v8.1 Triage")
    parser.add_argument("--stakes", type=int, required=True)
    parser.add_argument("--complexity", type=int, required=True)
    parser.add_argument("--time", type=int, required=True)
    parser.add_argument("--expertise", type=int, required=True)
    parser.add_argument("--reversibility", type=int, required=True)
    parser.add_argument("--group", type=str, default="false")
    parser.add_argument("--advocacy", type=str, default="false")
    parser.add_argument("--novelty", type=int, default=1)
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--plugin-root", type=str, default="")

    args = parser.parse_args()

    result = calculate_triage(
        stakes=args.stakes,
        complexity=args.complexity,
        time_pressure=args.time,
        expertise=args.expertise,
        reversibility=args.reversibility,
        group=args.group.lower() == "true",
        advocacy_mode=args.advocacy.lower() == "true",
        novelty=args.novelty,
        commitment_horizon=args.horizon
    )

    if args.plugin_root:
        profile_path = os.path.join(args.plugin_root, "data", "bias-profile.json")
        if os.path.exists(profile_path):
            try:
                with open(profile_path, 'r') as f:
                    profile = json.load(f)
                result["personal_profile_active"] = True
                result["personal_bias_overrides"] = profile.get("triage_overrides", {})
                result["personal_recurring_biases"] = profile.get("recurring_biases", [])
            except Exception:
                result["personal_profile_active"] = False
        else:
            result["personal_profile_active"] = False

    print(json.dumps(result))
