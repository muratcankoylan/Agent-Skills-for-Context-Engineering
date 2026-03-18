# Motifs Structurels des Textes Artificiels

## Biais de Triade (structuration ternaire)

### Signal

Les LLM ont une forte tendance à structurer le contenu par groupes de trois : "trois raisons", "trois bénéfices clés", "trois étapes". Ce motif est rare dans l'écriture humaine spontanée.

### Détection

- Énumération explicite : "premièrement / deuxièmement / troisièmement".
- Triades annoncées : "il y a trois raisons pour lesquelles...", "voici trois étapes clés...".
- Listes à puces de exactement 3 items (récurrentes).

### Remédiation

- Variez le nombre : utilisez 2, 4, 5 ou 7 points selon le contenu réel.
- Supprimez l'annonce du chiffre si elle est arbitraire.
- Fusionnez les points redondants, développez ceux qui sont substantiels.

## Motif "Sandwich"

### Signal

Structure : ouverture vague → contenu → conclusion moralisatrice. Typique des LLM qui "cadrent" chaque argument.

### Détection

- Ouverture par une platitude : "dans le monde d'aujourd'hui...", "à l'ère de l'IA...".
- Conclusion par une exhortation vide : "il est essentiel de...", "en conclusion...", "pour l'avenir...".

### Remédiation

- Supprimez la première phrase si elle contient zéro information.
- Remplacez la conclusion moralisatrice par une implication concrète ou une étape suivante.
- Commencez directement par le fait ou l'argument.

## Énumération Symétrique

### Signal

Listes où les items ont des nombres de mots presque identiques (± 5 mots). Les humains produisent des items de longueur variable.

### Remédiation

- Développez les items importants, condensez les secondaires.
- Convertissez en prose si la liste n'aide pas la lecture.

## Le Pivot "Cependant" (Performative Balance)

### Signal

Les LLM structurent souvent les arguments par "X est vrai. Cependant, Y." où le "cependant" introduit un contre-point faible ou artificiel pour paraître équilibré.

### Remédiation

- Si le contre-point est réel, gardez-le mais étayez-le par des preuves.
- S'il est purement formel, supprimez cette structure de faux équilibre.

## Structure d'Argument Crédible (Modèle de référence)

Un argument humain crédible suit ce schéma :

1. **Thèse** : Idée centrale énoncée précisément.
2. **Mécanisme** : Le "comment" ou le "pourquoi" — causalité explicite.
3. **Preuve** : Exemple concret, donnée, cas réel.
4. **Limite** : Contre-argument, exception, condition de validité.
5. **Implication** : Conséquence pratique — pas une morale abstraite.
