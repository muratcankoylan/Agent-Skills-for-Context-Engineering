# Architecture de Carrousel : Cadrage pour une Rétention Élevée

Les carrousels LinkedIn (diapositives PDF) sont le format le plus puissant pour le "Dwell Time". Ils forcent l'utilisateur à cliquer 5 à 10 fois, signalant un intérêt extrême à l'algorithme. Ce plan fournit l'architecture technique pour des carrousels qui ne se contentent pas d'être beaux — ils convertissent.

---

## 🏛 1. L'Architecture Diapositive par Diapositive

Un carrousel de Grade A+ doit suivre ce "Flux de Rétention" :

| Slide #   | Nom              | Objectif                                                     |
| :-------- | :--------------- | :----------------------------------------------------------- |
| **01**    | La Couverture    | L'Accroche. Texte large, fort contraste, haute curiosité.    |
| **02**    | Les Enjeux       | Le "Pourquoi". Que se passe-t-il si le lecteur ignore ceci ? |
| **03**    | Le Guide         | L' "Intro". Qui vous êtes et quel est le framework.          |
| **04-07** | Le Cœur          | La Valeur. 1 point/pépite par slide. Max 30 mots.            |
| **08**    | Le Récapitulatif | Le résumé "Aha !" de tout ce qu'ils viennent de lire.        |
| **09**    | Le Résultat      | La "Preuve". Une étude de cas ou une métrique.               |
| **10**    | Le CTA           | L' "Appel". Une seule direction claire.                      |

---

## 🧬 2. Règles de Conception Technique (Pour Non-Designers)

### La Règle de la "Zone de Sécurité" :

Gardez tout le texte dans les 60 % centraux de la diapositive. Évitez les bords où l'interface de LinkedIn (flèches, nombre de slides) couvrira votre contenu.

### La Loi du "Contraste" :

Utilisez des combinaisons à fort contraste.

- **Mode Sombre** : Fond noir + Texte blanc/jaune.
- **Mode Marque** : Fond de couleur profonde + Texte blanc.
- **Règle** : Ne jamais utiliser de gris clair sur blanc ou de bleu foncé sur noir.

### Le Plafond du "Nombre de Mots" :

Ne dépassez jamais 40 mots par diapositive. S'il y a plus de 40 mots, cela devrait être une publication textuelle, pas un carrousel.

---

## 🧬 3. Modèles de Carrousel (Frameworks)

### Modèle A : La "Décomposition Étape par Étape"

- **Slide 1** : Comment j'ai résolu [Douleur] en [Temps court].
- **Slide 2** : L'ancienne façon vs Le Protocole Solo.
- **Slide 3** : Phase 1 : [Nom de l'action].
- **Slide 4** : Phase 2 : [Nom de l'action].
- **Slide 5** : La "Seule Chose" que les gens oublient à ce stade.
- **Slide 6** : Phase 3 : [Nom de l'action].
- **Slide 7** : Liste de contrôle du résultat final.
- **Slide 8** : Pourquoi ça marche (La logique technique).
- **Slide 9** : Vous voulez la liste ?
- **Slide 10** : Commentez [MOT-CLÉ] ci-dessous.

### Modèle B : L' "Analyse Visuelle" (Critique)

- **Slide 1** : Analyse de l'[Actif] de [Leader de l'industrie].
- **Slide 2** : Ce qu'ils ont bien fait (Signal vert).
- **Slide 3** : La seule erreur qui leur coûte [Somme].
- **Slide 4** : L'état "Avant" (Capture d'écran).
- **Slide 5** : L'état "Après" (Votre refonte).
- **Slide 6-8** : Les 3 principes de la correction.
- **Slide 9** : Résumé de la leçon.
- **Slide 10** : Vous voulez une analyse de votre site ? Lien dans la bio.

---

## 🧪 4. Protocoles d'"Ingénierie de Rétention"

Comment les faire défiler jusqu'à la Slide 10 :

- **La Slide "Cliffhanger"** : Terminez une diapositive par "Mais ce n'était pas assez..." ou "Puis j'ai réalisé..." pour forcer le balayage.
- **Le Design "Peek-a-Boo"** : Ayez un élément (comme une ligne ou une flèche) qui commence sur la Slide 4 et se termine sur la Slide 5. L'œil suit naturellement le mouvement.
- **La "Barre de Progression"** : Incluez un petit indicateur visuel en bas (bulles ou ligne) montrant au lecteur le chemin parcouru.

---

## ⚒ 5. Optimisation Technique du PDF

- **Format** : Utilisez toujours **1:1 (Carré)** ou **4:5 (Portrait)**. Jamais 16:9.
- **Type de fichier** : Exportez en "PDF Standard".
- **Limite de pages** : Visez 7 à 12 diapositives. Moins de 5 semble léger ; plus de 15 provoque un abandon.
- **Accessibilité** : Assurez-vous que le texte de votre Slide 1 est le même que votre Accroche de post afin que Google et LinkedIn puissent indexer le contenu pour la recherche.

---

## 🧪 6. Le Pont "Carrousel-Texte"

Un carrousel n'est rien sans une légende (caption) forte.

### Le Protocole :

1.  **Titre** : Résumez le carrousel.
2.  **Accroche** : Utilisez une formule de `hook-library.fr.md`.
3.  **Instruction** : "Balayez pour voir le framework complet."
4.  **Récapitulatif** : 3 à 5 puces sur ce qui se trouve à l'intérieur.
5.  **CTA** : Renforcez le CTA de la Slide 10.

---

## 📈 7. Indicateurs de Performance

- **Taux de Balayage (STR)** : Combien de personnes arrivent à la Slide 10 ? (Objectif : >50 %).
- **Taux d'Enregistrement** : Les carrousels sont le format le plus "Enregistré". (Objectif : 1 enregistrement pour 200 vues).
- **Taux de Partage** : Les carrousels à haute valeur sont partagés dans le "Fil". (Objectif : 1 partage pour 500 vues).

---

## 📂 Ressources Connexes

- [La Bibliothèque d'Accroches LinkedIn](./hook-library.fr.md)
- [Guide de Formatage LinkedIn](./formatting-guide.fr.md)
- [Stitch Asset Bridge (Figma-to-LinkedIn)](../stitch-asset-bridge/SKILL.fr.md)

---

> [!TIP]
> Utilisez la commande `/solo:build design` si vous avez un MCP Figma connecté. Je peux extraire vos cadres de conception et vous aider à les structurer automatiquement dans cette architecture PDF.
