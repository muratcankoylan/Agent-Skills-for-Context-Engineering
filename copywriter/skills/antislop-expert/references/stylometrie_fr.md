# Stylométrie et Burstiness — Détection de Textes Artificiels

## Principe

La stylométrie mesure les invariants d'un style d'écriture. Un humain produit un texte au rythme irrégulier ("bursty"), tandis qu'un LLM a tendance à lisser la longueur des phrases autour d'une moyenne.

## Burstiness (variance de longueur de phrase)

### Calcul

```
variance = Σ(longueur_phrase_i - moyenne)² / (n - 1)
```

### Interprétation

| Variance | Diagnostic                                         |
| :------- | :------------------------------------------------- |
| < 10     | Signal LLM fort : rythme trop régulier             |
| 10–20    | Zone grise : peut être un texte technique ou édité |
| > 20     | Rythme humain naturel                              |
| > 40     | Rythme très varié (oral, littéraire)               |

### Ratios complémentaires

- **Phrases courtes** (< 6 mots) : un texte humain en contient typiquement 10–20 %. Les LLM descendent rarement sous les 8 %.
- **Phrases longues** (> 30 mots) : les humains en produisent occasionnellement ; les LLM soit les évitent, soit en produisent à fréquence constante.
- **Écart-type normalisé** (CV = σ/μ) : CV > 0,5 est typique de l'écriture humaine, < 0,3 est suspect.

## Autres signaux stylométriques

### Diversité lexicale (TTR)

Type-Token Ratio = mots uniques / total de mots. Un TTR bas sur un texte court (< 500 mots) est suspect.

### Distribution de Zipf

Les textes humains suivent imparfaitement la loi de Zipf. Les LLM la suivent trop parfaitement (distribution trop lisse).

### Entropie lexicale

Mesure l'imprévisibilité du vocabulaire. Une entropie anormalement basse (vocabulaire très prévisible) est un signal LLM.

## Limites

Aucun signal n'est suffisant à lui seul. Une détection fiable nécessite un diagnostic multi-signaux combinant burstiness, lexique, structure et typographie.
