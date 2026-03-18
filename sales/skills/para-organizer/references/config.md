# Configuration de l'Organisation (Méthode PARA)

Personnalisez ce fichier pour votre structure de dossiers en utilisant la méthodologie PARA de "Building a Second Brain".

## Structure des Dossiers PARA

```yaml
folders:
  0-Inbox:
    - _REVISE # Fichiers nécessitant une attention manuelle
  1-Projets: # Travail actif avec échéances
    - Travail
    - Personnel
  2-Domaines: # Responsabilités continues (Areas)
    - Finances
    - Santé
    - Juridique
    - Carrière
    - Maison
  3-Ressources: # Matériel de référence par sujet
    Médias:
      - Images
      - Vidéos
      - Audio
      - Captures
    Outils:
      - Installeurs
      - Utilitaires
    Apprentissage:
      - Articles
      - Livres
      - Cours
    Modèles: []
  4-Archives: # Éléments inactifs ou terminés
    - Projets-Terminés
    - Anciens-Domaines
    - Vieilles-Ressources
```

## Codes Projets/Clients

Définissez des codes courts pour les catégories PARA :

```yaml
codes:
  # Projets (travail actif)
  PROJ: "Projet Actif"
  CLIENT: "Travail Client"

  # Domaines (responsabilités)
  FIN: "Finances"
  SANTE: "Santé"
  JUR: "Juridique"
  CARR: "Carrière"

  # Ressources (référence)
  REF: "Matériel de Référence"
  APPR: "Apprentissage"

  # Général
  GEN: "Général/Non-catégorisé"
```

## Mots-clés de Détection de Contenu

Mots-clés pour catégoriser automatiquement dans les dossiers PARA :

```yaml
detection:
  1-Projets:
    - "projet"
    - "échéance"
    - "livrable"
    - "jalon"
    - "sprint"
    - "brouillon"
    - "révision"
    - "en-cours"
    - "final"

  2-Domaines/Finances:
    - "facture"
    - "reçu"
    - "relevé"
    - "taxe"
    - "impôt"
    - "banque"
    - "paiement"
    - "dépense"
    - "budget"

  2-Domaines/Santé:
    - "médical"
    - "santé"
    - "ordonnance"
    - "assurance"
    - "docteur"
    - "dentaire"
    - "laboratoire"
    - "résultats"

  2-Domaines/Juridique:
    - "contrat"
    - "accord"
    - "nda"
    - "bail"
    - "acte"
    - "testament"
    - "tribunal"
    - "juridique"

  3-Ressources/Médias:
    extensions:
      - ".jpg"
      - ".jpeg"
      - ".png"
      - ".gif"
      - ".mp4"
      - ".mov"
      - ".mp3"
      - ".wav"
    patterns:
      - "IMG_*"
      - "DSC_*"
      - "Capture*"

  3-Ressources/Outils:
    extensions:
      - ".dmg"
      - ".exe"
      - ".pkg"
      - ".msi"
      - ".app"
    keywords:
      - "installeur"
      - "setup"
      - "mise-a-jour"

  3-Ressources/Apprentissage:
    - "guide"
    - "tutoriel"
    - "cours"
    - "ebook"
    - "syllabus"
    - "conférence"
    - "référence"
    - "documentation"
```

## Flux de Travail Inbox

Prompts pour le traitement des fichiers dans 0-Inbox :

```yaml
inbox_workflow:
  daily_review_prompt: |
    C'est l'heure de votre revue quotidienne de l'Inbox ! Traitez les fichiers dans 0-Inbox :

    Pour chaque fichier, demandez :
    - Est-ce actionnable avec une échéance ? → 1-Projets
    - Est-ce une responsabilité continue ? → 2-Domaines
    - Est-ce du matériel de référence utile ? → 3-Ressources
    - Est-ce terminé/inactif ? → 4-Archives
    - Rien de tout cela ? → Supprimez ou gardez dans l'Inbox

  weekly_review_prompt: |
    L'heure de la revue hebdomadaire ! Allons-y :
    1. Videz les éléments restants de 0-Inbox
    2. Archivez les projets terminés dans 1-Projets
    3. Revoyez 2-Domaines pour les éléments qui ne sont plus pertinents
    4. Nettoyez les doublons dans 3-Ressources
    5. Organisez 4-Archives par année/catégorie
```

## Indicateurs de Sensibilité

Signalez les fichiers contenant :

| Type         | Indicateurs                     | Emplacement PARA     | Action                |
| :----------- | :------------------------------ | :------------------- | :-------------------- |
| Financier    | IBAN, numéros de compte, impôts | 2-Domaines/Finances  | Signaler pour revue   |
| Médical      | Dossiers de santé, ordonnances  | 2-Domaines/Santé     | Signaler pour revue   |
| Juridique    | Contrats, accords               | 2-Domaines/Juridique | Signaler pour revue   |
| Identifiants | Mots de passe, clés API         | NE PAS DÉPLACER      | Alerter immédiatement |

## Paramètres de Comportement

```yaml
settings:
  require_approval_for_renames: true
  require_approval_for_moves: false # Seulement pour une confiance HAUTE
  require_approval_for_sensitive: true
  never_delete_files: true
  preserve_original_dates: true
  create_review_folder_for_uncertain: true
  skip_files_larger_than_mb: 500
  inbox_processing_enabled: true
  auto_prompt_daily_review: true
  auto_prompt_weekly_review: true
```
