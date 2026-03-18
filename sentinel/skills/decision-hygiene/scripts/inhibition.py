
import argparse
import json

def calculate_inhibition(appropriateness: float, stakes: str = "MEDIUM",
                         time_pressure: str = "NORMAL",
                         expertise: str = "SOME"):
    """Deterministic inhibition strength calculation."""
    
    if not (0.0 <= appropriateness <= 1.0):
        return {"error": "Appropriateness must be between 0.0 and 1.0"}

    base = 1.0 - appropriateness

    modifiers = {
        "stakes": {"CRITICAL": 0.2, "HIGH": 0.1, "MEDIUM": 0.0, "LOW": -0.1}.get(stakes, 0.0),
        "time": {"EMERGENCY": -0.3, "URGENT": -0.15, "NORMAL": 0.0, "STRATEGIC": 0.1}.get(time_pressure, 0.0),
        "expertise": {"EXPERT": -0.2, "ADJACENT": -0.1, "SOME": 0.0, "MODERATE": 0.0, "UNFAMILIAR": 0.1}.get(expertise, 0.0)
    }

    adjusted = max(0.0, min(1.0, base + sum(modifiers.values())))

    action = (
        "NONE" if adjusted < 0.2 else
        "FLAG" if adjusted < 0.4 else
        "PAUSE_AND_CONFIRM" if adjusted < 0.6 else
        "BLOCK_AND_REQUIRE_ALTERNATIVE" if adjusted < 0.85 else
        "REFUSE_TO_PROCEED"
    )

    return {
        "appropriateness": appropriateness,
        "base_score": round(base, 2),
        "modifiers": modifiers,
        "adjusted_score": round(adjusted, 2),
        "strength": action
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--appropriateness", type=float, required=True)
    parser.add_argument("--stakes", default="MEDIUM", choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"])
    parser.add_argument("--time", default="NORMAL", choices=["EMERGENCY", "URGENT", "NORMAL", "STRATEGIC"])
    parser.add_argument("--expertise", default="SOME", choices=["EXPERT", "ADJACENT", "SOME", "MODERATE", "UNFAMILIAR", "NONE"])
    
    args = parser.parse_args()
    
    result = calculate_inhibition(args.appropriateness, args.stakes, args.time, args.expertise)
    print(json.dumps(result))
