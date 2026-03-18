#!/usr/bin/env python3
"""AntiSlop-FR — Pipeline principal : audit + remédiation + rapport."""

import sys
import os
import json

# Configuration des imports locaux
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from antislop_score import authenticity_score, severity

def main():
    if sys.stdout.encoding != 'UTF-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    text = sys.stdin.read().strip()
    if not text:
        print("Erreur : aucun texte fourni.", file=sys.stderr)
        sys.exit(1)

    word_count = len(text.split())

    # ── Audit ─────────────────────────────────────────────────────────
    score = authenticity_score(text)
    sev = severity(score.slop_score)

    report = {
        "version": "5.0-FR",
        "word_count": word_count,
        "slop_score": score.slop_score,
        "authenticity_score": score.authenticity_score,
        "severity": sev,
        "dimensions": {
            "rythme": score.details.get("burst_pts", 0),
            "densite_factuelle": score.details.get("factual_pts", 0),
            "raisonnement_causal": score.details.get("causal_pts", 0),
            "anti_corporate": score.details.get("corporate_pts", 0),
            "typographie": score.details.get("typo_pts", 0),
        },
        "variance_rythme": score.burstiness_variance,
        "corporate_trouves": (score.details.get("corporate_tier1_found", []) +
                              score.details.get("corporate_tier2_found", []) +
                              score.details.get("corporate_tier3_found", [])),
    }

    # ── Sortie Markdown ───────────────────────────────────────────────
    print("### Rapport AntiSlop-FR v5.0\n")
    print(f"**Score de Slop :** {score.slop_score}/100 | "
          f"**Sévérité :** {sev} | "
          f"**Mots :** {word_count}")
    print()

    print("#### Analyse par Dimensions")
    dims = report["dimensions"]
    print(f"- Rythme (burstiness) : {dims['rythme']}/20 (variance = {score.burstiness_variance})")
    print(f"- Densité factuelle : {dims['densite_factuelle']}/20")
    print(f"- Raisonnement causal : {dims['raisonnement_causal']}/15")
    print(f"- Anti-langue de bois : {dims['anti_corporate']}/25")
    print(f"- Typographie : {dims['typographie']}/20")
    print()

    print("<details><summary>JSON de diagnostic brut</summary>\n")
    print("```json")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("```")
    print("</details>\n")

if __name__ == "__main__":
    main()
