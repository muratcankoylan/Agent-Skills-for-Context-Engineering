# Bonnes Pratiques de Prompting Exa

L'API Exa est un moteur de recherche neuronal conçu pour les LLM. Contrairement aux moteurs de recherche traditionnels par mots-clés, Exa comprend le sens et la sémantique. Pour obtenir les meilleurs résultats, vous devez le prompter efficacement.

## Principes Fondamentaux

1. **Formulation pour la Recherche Neuronale** :
   - **Ne posez pas de questions** : Au lieu de "Quelles sont les meilleures stratégies marketing ?", formulez votre requête comme la _réponse_ ou le _contenu_ que vous vous attendez à trouver.
   - **Pensez "Autocomplétion"** : Imaginez que vous écrivez le début d'une phrase qui se termine par le lien que vous voulez.
   - **Mauvais** : "Qui est le PDG d'Anthropic ?"
   - **Bon** : "Le PDG actuel d'Anthropic est"

2. **Utilisation de l'Autoprompt (`use_autoprompt: true`)** :
   - Exa dispose d'une fonctionnalité `autoprompt` intégrée. Elle réécrit intelligemment votre requête pour qu'elle soit plus efficace pour la recherche neuronale.
   - **Quand l'utiliser** : Généralement toujours, sauf si vous avez une chaîne de requête hautement spécifique et optimisée.

3. **Recherche par Mots-clés vs Recherche Neuronale** :
   - **Neuronal (par défaut)** : Idéal pour les sujets larges, l'exploration de concepts et la recherche de réponses à des questions complexes. Utilisé pour : "cadres stratégiques pour la croissance du SaaS".
   - **Mots-clés** : Idéal pour trouver des noms spécifiques, des identifiants, des codes d'erreur ou des citations exactes. Utilisé pour : "erreur 404 sur /api/v1/login".

## Modèles de Prompting

### Trouver des Listes et Collections

Si vous voulez une liste de ressources, promptez avec une phrase décrivant une liste.

- **Requête** : "Voici une liste des 10 meilleurs fournisseurs de logiciels CRM pour les petites entreprises :"
- **Requête** : "Les meilleures ressources pour apprendre la sémiotique dans le branding sont :"

### Trouver des Discussions et Opinions

- **Requête** : "discussion sur l'impact de l'IA sur les industries créatives site:reddit.com"
- **Requête** : "fil hacker news concernant les nouvelles fonctionnalités CSS"

### Trouver des Entreprises et Concurrents

- **Requête** : "startups B2B SaaS en forte croissance dans le secteur de la santé"
- **Requête** : "recrutement pour un poste de Head of Growth" (implique des entreprises en phase de croissance)

### Trouver des Articles Académiques ou Techniques

- **Requête** : "document de recherche PDF sur l'efficacité de l'architecture transformer"
- **Requête** : "Résumé : apprentissage par renforcement profond pour le contrôle robotique"

## Stratégies de Filtrage

La puissance d'Exa est multipliée lorsque vous combinez la recherche neuronale avec des filtres.

- **`include_domains`** : Limiter la recherche à des sources de haute qualité.
- **`exclude_domains`** : Supprimer le bruit (ex: exclure les réseaux sociaux pour du contenu long format).
- **`start_published_date`** : Essentiel pour les requêtes liées à l'actualité.

## Modèles de Recherche Spécialisés

### Contexte de Code (`get_code_context_exa`)

- **Objectif** : Trouver des exemples d'implémentation ou des bibliothèques.
- **Invite** : "Voici une implémentation Python d'un pipeline RAG utilisant LangChain :"

### Recherche de Personnes (`people_search_exa`)

- **Objectif** : Trouver des experts ou des candidats.
- **Invite** : "Le profil LinkedIn d'un ingénieur IA senior chez OpenAI spécialisé dans l'apprentissage par renforcement :"

### Recherche d'Entreprises (`company_research_exa`)

- **Objectif** : Cartographie de marché.
- **Invite** : "Liste des startups en Série B construisant des agents IA pour la legal tech :"
