#!/usr/bin/env python3
"""AntiSlop-FR — Scoring d'authenticité multi-signaux pour le français."""

import re
import statistics
from typing import NamedTuple

# ── Lexiques ──────────────────────────────────────────────────────────

CORPORATE_TIER1 = [
    "dans un monde en constante évolution", "à l'ère du numérique", "à l'ère de l'ia",
    "il est crucial de", "il est essentiel de", "il est primordial de",
    "il est important de noter que", "il convient de souligner que",
    "révolutionnaire", "change la donne", "à la pointe", "état de l'art",
    "nouvelle génération", "synergie", "synergies", "synergique",
    "approche holistique", "vision holistique", "changement de paradigme", "paradigme",
    "leadership éclairé", "leader d'opinion", "disruptif", "disruption",
    "écosystème", "scalable", "scalabilité", "transformation digitale",
    "proposition de valeur", "valeur ajoutée", "meilleur de sa catégorie", "classe mondiale",
    "faire bouger les lignes", "fruits à portée de main", "boucler la boucle",
    "passer au niveau supérieur", "plongée profonde", "en fin de compte",
    "libérer de la valeur", "libérer le potentiel", "alignement des parties prenantes",
    "compétence clé", "cœur de métier", "mission critique",
]

CORPORATE_TIER2 = [
    "optimiser", "optimisation", "tirer parti", "exploiter",
    "impactant", "autonomiser", "empowerment", "rationaliser", "rationalisé",
    "innovant", "innovation", "robuste", "solution robuste",
    "fluide", "de manière fluide", "exploitable", "insights exploitables",
    "stimuler la croissance", "générer des résultats", "favoriser", "fostering",
    "naviguer", "résilient", "résilience",
    "durable", "durabilité", "inclusif", "inclusivité",
    "stratégique", "feuille de route", "engagement",
]

CORPORATE_TIER3 = [
    "utiliser", "faciliter", "s'efforcer de", "améliorer", "amélioration",
    "complet", "exhaustif", "en termes de", "en ce qui concerne", "concernant",
    "à l'avenir", "désormais", "du fait que",
]

FILLER_CONNECTORS = [
    "de plus", "en outre", "par ailleurs", "de surcroît",
    "il va sans dire que", "inutile de préciser que",
    "il est à noter que", "il est intéressant de mentionner que",
    "en fait", "à vrai dire", "ceci étant dit",
]

LLM_OPENINGS = [
    "dans le monde d'aujourd'hui", "à une époque où",
    "il est indéniable que", "on ne peut nier que",
    "alors que nous naviguons", "le paysage de", "évolue constamment",
    "est devenu de plus en plus important", "ces dernières années",
]

LLM_CLOSINGS = [
    "en conclusion, il est essentiel", "seul le temps nous le dira",
    "l'avenir reste à voir", "il est clair que",
    "continuera à", "alors que nous avançons",
    "au bout du compte", "mérite une attention soutenue",
    "balle est dans le camp de",
]

AI_HEDGING = [
    "il est important de considérer", "bien qu'il y ait de nombreux facteurs",
    "c'est une question complexe", "il existe plusieurs perspectives",
    "cela dépend de divers facteurs", "les avis peuvent diverger",
]

SYCOPHANTIC_OPENERS = [
    "excellente question", "point très intéressant",
    "point pertinent", "absolument !",
]

CAUSAL_MARKERS = re.compile(
    r"\b(parce que|car|puisque|donc|ainsi|par conséquent|"
    r"en conséquence|du fait de|en raison de|grâce à|causé par|mène à|"
    r"ce qui signifie|ce qui implique|de sorte que|étant donné que|"
    r"pour cette raison|cela provoque|cela entraîne)\b", re.IGNORECASE
)

# ── Utilitaires ─────────────────────────────────────────────────────────

def split_sentences(text: str) -> list[str]:
    """Découpe le texte en phrases en gérant les abréviations françaises."""
    protected = text
    for abbr in ["M.", "Mme", "Mlle", "Dr", "Prof.", "Cie", "St.", "Blvd.", 
                 "Janv.", "Févr.", "Avr.", "Juin", "Juil.", "Août", "Sept.", 
                 "Oct.", "Nov.", "Déc.", "ex.", "éd.", "vol."]:
        protected = protected.replace(abbr, abbr.replace(".", "§"))
    # Gestion des élisions (l', d', etc.) pour le comptage de mots plus tard si besoin
    sentences = re.split(r'(?<=[.!?…])\s+', protected.strip())
    return [s.replace("§", ".").strip() for s in sentences if len(s.strip()) > 3]


class ScoreBreakdown(NamedTuple):
    slop_score: float
    authenticity_score: float
    burstiness_variance: float
    corporate_count: int
    filler_count: int
    factual_density: float
    causal_density: float
    details: dict


def count_matches(text: str, terms: list[str]) -> tuple[int, list[str]]:
    low = text.lower()
    found = [t for t in terms if t in low]
    count = sum(low.count(t) for t in found)
    return count, found


def authenticity_score(text: str) -> ScoreBreakdown:
    sentences = split_sentences(text)
    word_count = len(text.split())
    if word_count == 0:
        return ScoreBreakdown(100, 0, 0.0, 0, 0, 0.0, 0.0, {})

    # ── 1. Burstiness (0-20 points) ──
    if len(sentences) >= 3:
        lengths = [len(s.split()) for s in sentences]
        var = statistics.variance(lengths)
        mean_len = statistics.mean(lengths)
        cv = (statistics.stdev(lengths) / mean_len) if mean_len > 0 else 0
        short_ratio = sum(1 for l in lengths if l < 6) / len(lengths)
    else:
        var, cv, short_ratio = 0.0, 0.0, 0.0

    if var >= 25: burst_pts = 20
    elif var >= 15: burst_pts = 14
    elif var >= 10: burst_pts = 8
    else: burst_pts = 0
    if short_ratio >= 0.12: burst_pts = min(20, burst_pts + 3)

    # ── 2. Densité factuelle (0-20 points) ──
    numbers = re.findall(r'\b\d[\d\s,.]*\d\b|\b\d+\b', text)
    proper_nouns = re.findall(r'\b[A-Z][a-z]{2,}(?:\s[A-Z][a-z]+)*', text)
    fact_raw = len(numbers) * 2 + len(proper_nouns) * 1
    fact_density = fact_raw / max(1, word_count / 100)
    factual_pts = min(20, round(fact_density * 4))

    # ── 3. Raisonnement causal (0-15 points) ──
    causal_matches = CAUSAL_MARKERS.findall(text)
    causal_density = len(causal_matches) / max(1, word_count / 100)
    causal_pts = min(15, round(causal_density * 5))

    # ── 4. Anti-corporate (0-25 points) ──
    t1_count, t1_found = count_matches(text, CORPORATE_TIER1)
    t2_count, t2_found = count_matches(text, CORPORATE_TIER2)
    t3_count, t3_found = count_matches(text, CORPORATE_TIER3)
    filler_count, filler_found = count_matches(text, FILLER_CONNECTORS)
    opening_count, _ = count_matches(text, LLM_OPENINGS)
    closing_count, _ = count_matches(text, LLM_CLOSINGS)
    hedging_count, hedging_found = count_matches(text, AI_HEDGING)
    syco_count, _ = count_matches(text, SYCOPHANTIC_OPENERS)

    corp_penalty = (t1_count * 4 + t2_count * 2 + t3_count * 1 +
                    filler_count * 1.5 + opening_count * 3 + closing_count * 3 +
                    hedging_count * 2 + syco_count * 3)
    corporate_pts = max(0, 25 - round(corp_penalty))

    # ── 5. Typographie (0-20 points) ──
    typo_pts = 20
    # Ponctuation double sans espace insécable (ex: "mot?")
    if re.search(r'[^\s\u00A0][?!:;]', text): typo_pts -= 5
    # Guillemets anglais au lieu de français
    if '"' in text: typo_pts -= 3
    # Majuscules mid-phrase suspectes
    mid_caps = re.findall(r'(?<=[a-z]\s)[A-Z][a-z]+(?!\.|,)', text)
    if len(mid_caps) > 5: typo_pts -= 5
    
    typo_pts = max(0, typo_pts)

    total = burst_pts + factual_pts + causal_pts + corporate_pts + typo_pts
    auth = max(0, min(100, total))
    slop = 100 - auth

    details = {
        "burst_pts": burst_pts, "factual_pts": factual_pts, "causal_pts": causal_pts,
        "corporate_pts": corporate_pts, "typo_pts": typo_pts,
        "corporate_tier1_found": t1_found, "corporate_tier2_found": t2_found,
        "corporate_tier3_found": t3_found, "filler_found": filler_found,
        "ai_hedging_found": hedging_found,
    }

    return ScoreBreakdown(
        slop_score=round(slop, 1), authenticity_score=round(auth, 1),
        burstiness_variance=round(var, 2), corporate_count=t1_count+t2_count+t3_count,
        filler_count=filler_count, factual_density=round(fact_density, 2),
        causal_density=round(causal_density, 2), details=details
    )

def severity(slop_score: float) -> str:
    if slop_score < 25: return "low"
    if slop_score < 50: return "medium"
    return "high"
