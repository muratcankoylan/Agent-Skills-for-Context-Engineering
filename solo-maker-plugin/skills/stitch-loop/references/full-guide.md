# Protocole : La Boucle de Construction (The Build Loop)

Exploitez la puissance de l'autonomie en utilisant le système de passage de relais pour construire des sites complexes.

## 1. Le Système du "Bâton" (Baton System)

Le fichier `next-prompt.md` sert de relais entre deux itérations de l'IA. Il contient :

- Le nom de la page cible (dans le Frontmatter YAML).
- Le prompt optimisé (via `stitch-enhance-prompt`).
- Les tokens de design (via `DESIGN.md`).

## 2. Étapes d'Exécution

1. **Découverte** : Identifier le `projectId` dans `stitch.json`.
2. **Génération** : Utiliser `generate_screen_from_text`.
3. **Récupération** : Télécharger le code HTML et l'image PNG.
4. **Déploiement** : Placer dans `site/public/` et corriger les chemins relatifs.
5. **Documentation** : Marquer la page comme [x] dans la sitemap de `SITE.md`.

## 3. Maintenir la Boucle en Vie

À chaque fin d'itération, vous **devez** mettre à jour `next-prompt.md`. Si la roadmap dans `SITE.md` est vide, proposez une amélioration ou une nouvelle page pertinente pour la vision du produit.

## 4. Structure de Référence du Projet

```
project/
├── next-prompt.md      # Le bâton - tâche actuelle
├── stitch.json         # Persistance de l'ID projet
├── DESIGN.md           # Charte graphique (source de vérité)
├── SITE.md             # Vision, sitemap et roadmap
└── site/public/        # Pages finales servies
```

## 5. Pourquoi ce mode ?

Il permet de s'affranchir des limites de contexte d'une seule session en découpant le travail de construction en bloc atomiques, tout en conservant une cohérence visuelle et narrative grâce aux fichiers de métadonnées partagés.
