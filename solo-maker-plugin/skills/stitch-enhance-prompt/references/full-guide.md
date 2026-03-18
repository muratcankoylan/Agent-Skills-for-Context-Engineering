# Guide : Ingénierie de Prompt pour Stitch

Ce guide détaille les techniques pour transformer une idée brute en une interface professionnelle générée par l'IA.

## 1. Le Pipeline d'Amélioration

Pour optimiser un prompt, suivez ces 4 étapes :

### A. Préciser la Plateforme & l'Environnement

Ne dites pas "ma page", dites "Web, Desktop-first" ou "Mobile App, iOS-style".

### B. Enrichir avec des Mots-Clés UI/UX

| Terme Vague    | Terme Optimisé (pour Stitch)                       |
| :------------- | :------------------------------------------------- |
| "menu en haut" | "navigation bar with logo and menu items"          |
| "bouton"       | "primary call-to-action button"                    |
| "liste"        | "card grid layout with thumbnails"                 |
| "formulaire"   | "form with labeled input fields and submit button" |

### C. Définir l'Atmosphère

Utilisez des adjectifs sensoriels : "Airy", "Playful", "Corporate", "High-contrast dark theme", "Glassmorphism elements".

### D. Structurer par Sections

Stitch comprend mieux quand le contenu est organisé hiérarchiquement :

1. **Header** : [Description]
2. **Hero Section** : [Description]
3. **Features Grid** : [Description]
4. **Footer** : [Description]

## 2. Intégration du Design System

Si un fichier `DESIGN.md` existe, extrayez le bloc "DESIGN SYSTEM (REQUIRED)" et placez-le au début de votre prompt. Cela garantit que chaque écran généré partagera les mêmes couleurs (Hex) et rayons de bordure.

## 3. Exemple de Transformation

**Avant :** "Fais moi une page de login bleue."
**Après :**
"Une page de connexion épurée et professionnelle dans un style minimaliste.
**DESIGN SYSTEM (REQUIRED):**

- Thème : Clair, professionnel
- Fond : Blanc (#ffffff)
- Accent : Bleu Royal (#2563eb)
  **Structure :**

1. Carte centrée avec logo en haut.
2. Champs de saisie email et mot de passe avec labels gris.
3. Bouton d'action principal bleu pleine largeur.
4. Lien 'Mot de passe oublié' subtil."
