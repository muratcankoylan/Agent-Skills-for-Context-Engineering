# Guide : Documenter un Système de Design pour Stitch (DESIGN.md)

Le fichier `DESIGN.md` est crucial pour que Stitch comprenne l'identité visuelle de votre application et génère de nouveaux écrans cohérents.

## 1. Structure du Fichier DESIGN.md

Un bon document de design doit contenir :

- **Atmosphère & Vibe** : Décrivez le sentiment (ex: "Épuré", "Utilitaire", "Ludique").
- **Palette de Couleurs** : Pour chaque couleur, donnez un nom descriptif, le code Hex et son rôle (ex: "Bleu Nuit Sourd (#1e293b) - Couleur de fond").
- **Typographie** : Familles de polices, graisses utilisées pour les titres vs le corps.
- **Géométrie & Formes** : Traduisez les classes Tailwind en descriptions physiques (ex: `rounded-lg` -> "Coins subtilement arrondis").
- **Élévation & Profondeur** : Type d'ombres (ex: "Ombres portées douces et diffuses").

## 2. Traduction Sémantique (Table de Correspondance)

| Classe Tailwind | Description Sémantique (pour Stitch) |
| :-------------- | :----------------------------------- |
| `rounded-full`  | Forme en pilule (Pill-shaped)        |
| `rounded-lg`    | Arêtes douces et arrondies           |
| `rounded-none`  | Angles vifs et droits                |
| `shadow-xl`     | Ombre portée profonde et contrastée  |

## 3. Section de Génération (REQUIRED)

À la fin de votre `DESIGN.md`, incluez toujours ce bloc résumé pour Stitch :

```markdown
**DESIGN SYSTEM (REQUIRED):**

- Plateforme : [Web/Mobile]
- Thème : [Clair/Sombre]
- Fond : [Couleur] (#hex)
- Accent : [Couleur] (#hex)
- Boutons : [Forme], [Couleur]
- Cartes : [Arrondi], [Ombre]
```

## 4. Pourquoi c'est important ?

Stitch ne "voit" pas le code comme un humain. Il a besoin d'une description visuelle riche. En documentant votre design en langage naturel, vous permettez à l'IA de maintenir une cohérence parfaite même sur des centaines d'écrans.
