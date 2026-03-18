---
name: para-organizer
description: Organisez vos fichiers selon la méthode PARA (Building a Second Brain). Catégorisation intelligente en Projets, Domaines (Areas), Ressources et Archives avec flux de travail "Inbox". Se déclenche sur "organiser mes fichiers", "nettoyer mon bureau", "méthode PARA", "second brain". Crée des dossiers PARA numérotés (0-Inbox, 1-Projets, 2-Domaines, 3-Ressources, 4-Archives), renomme les fichiers mal nommés et maintient des journaux d'audit complets.
bundle: identity-tools
triggers:
  - "organiser mes fichiers"
  - "methode PARA"
  - "organise my files"
tools:
  standalone: [filesystem]
  supercharged: []
version: 1.0.0
---

# Organisateur de Fichiers (Méthode PARA)

Organise les fichiers en utilisant la méthodologie PARA tirée de "Building a Second Brain" de Tiago Forte. Catégorisation intelligente avec flux de travail pour la boîte de réception et pistes d'audit complètes.

## Catégories PARA

| # | Catégorie | Contient | Durée de vie |
|:--|:----------|:---------|:-------------|
| 0 | Inbox | Nouveaux fichiers en attente | Temporaire |
| 1 | Projets | Travail actif avec échéances | Court terme |
| 2 | Domaines | Responsabilités continues | Long terme |
| 3 | Ressources | Matériel de référence | Permanent |
| 4 | Archives | Éléments inactifs ou terminés | Préservé |

## Flux de Travail (5 Phases)

```
Phase 1 : Découverte  → Scanner, compter, évaluer les noms de fichiers
Phase 2 : Analyse     → Lire les fichiers mal nommés, proposer des renommages
Phase 3 : Préparation → Créer la structure PARA, obtenir l'approbation
Phase 4 : Exécution   → Renommer et déplacer les fichiers (avec journalisation)
Phase 5 : Finalisation → Résumé, invitation à la revue de l'Inbox
```

**Approbation requise avant** tout renommage ou déplacement. Ne jamais supprimer sans confirmation explicite.

## Démarrage Rapide

1. Créez un dossier `_ORG/` dans le répertoire cible.
2. Initialisez les fichiers de suivi depuis `references/templates.md`.
3. Personnalisez `references/config.md` selon vos besoins.
4. Exécutez les phases avec points de contrôle utilisateur.

## Fichiers de Référence

- `references/config.md` — Structure PARA personnalisable et mots-clés de détection
- `references/templates.md` — Modèles vierges pour `_PLAN.md`, `_LOG.md`, `_MANIFEST.md`
- `references/full-guide.md` — Structure des dossiers, convention de nommage, codes PARA, règles d'analyse de contenu, journalisation, reprise de session
