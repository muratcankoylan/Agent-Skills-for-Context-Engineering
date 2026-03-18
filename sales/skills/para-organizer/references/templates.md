# Modèles d'Organisation

Initialisez ces fichiers dans le dossier `_ORG/` avant de commencer.

---

## Modèle \_PLAN.md

```markdown
# Plan d'Organisation des Téléchargements

**Créé le** : [HORODATAGE]
**Dernière mise à jour** : [HORODATAGE]
**Statut** : ⬜ Non démarré

---

## Vue d'ensemble

**Dossier cible** : ~/Downloads
**Total des fichiers trouvés** : [en attente de scan]

---

## Phase 1 : Découverte et Inventaire

| Tâche                                   | Statut | Début | Fin | Notes |
| :-------------------------------------- | :----- | :---- | :-- | :---- |
| 1.1 Lister tous les fichiers            | ⬜     | -     | -   |       |
| 1.2 Compter par extension               | ⬜     | -     | -   |       |
| 1.3 Identifier la plage de dates        | ⬜     | -     | -   |       |
| 1.4 Signaler les gros fichiers (>100Mo) | ⬜     | -     | -   |       |
| 1.5 Signaler les fichiers sensibles     | ⬜     | -     | -   |       |
| 1.6 Évaluer la qualité des noms         | ⬜     | -     | -   |       |

---

## Phase 2 : Analyse du Contenu

| Tâche                               | Statut | Début | Fin | Notes                |
| :---------------------------------- | :----- | :---- | :-- | :------------------- |
| 2.1 Analyser les documents          | ⬜     | -     | -   |                      |
| 2.2 Analyser les images             | ⬜     | -     | -   |                      |
| 2.3 Analyser les tableurs           | ⬜     | -     | -   |                      |
| 2.4 Générer les renommages proposés | ⬜     | -     | -   |                      |
| 2.5 Présenter pour approbation      | ⬜     | -     | -   | ⚠️ POINT DE CONTRÔLE |

---

## Phase 3 : Préparation

| Tâche                               | Statut | Début | Fin | Notes     |
| :---------------------------------- | :----- | :---- | :-- | :-------- |
| 3.1 Créer la structure de dossiers  | ⬜     | -     | -   |           |
| 3.2 Point de contrôle d'approbation | ⬜     | -     | -   | ⚠️ REQUIS |

---

## Phase 4 : Exécution

| Tâche                               | Statut | Début | Fin | Notes |
| :---------------------------------- | :----- | :---- | :-- | :---- |
| 4.1 Renommer les fichiers approuvés | ⬜     | -     | -   |       |
| 4.2 Déplacer confiance HAUTE        | ⬜     | -     | -   |       |
| 4.3 Déplacer confiance MOYENNE      | ⬜     | -     | -   |       |
| 4.4 Déplacer BASSE → \_REVISE       | ⬜     | -     | -   |       |
| 4.5 Gérer les doublons              | ⬜     | -     | -   |       |
| 4.6 Gérer les gros fichiers         | ⬜     | -     | -   |       |

---

## Phase 5 : Finalisation

| Tâche                      | Statut | Début | Fin | Notes |
| :------------------------- | :----- | :---- | :-- | :---- |
| 5.1 Générer le résumé      | ⬜     | -     | -   |       |
| 5.2 Finaliser le manifeste | ⬜     | -     | -   |       |

---

## Résumé Final

| Métrique                   | Nombre |
| :------------------------- | :----- |
| Total des fichiers traités | -      |
| Fichiers renommés          | -      |
| Fichiers déplacés          | -      |
| Fichiers dans \_REVISE     | -      |
| Erreurs                    | -      |
```

---

## Modèle \_LOG.md

```markdown
# Journal d'Organisation

**Session démarrée le** : [HORODATAGE]
**Dossier cible** : ~/Downloads

---

## Journal de Session

### [HORODATAGE] - SESSION

**Action** : Session d'organisation démarrée
**Cible** : ~/Downloads
**Suivant** : Commencer la Phase 1 (Découverte)

---

<!-- Ajoutez des entrées au fur et à mesure -->

---

## Résumé des Erreurs

| Horodatage | Fichier | Erreur | Résolution |
| :--------- | :------ | :----- | :--------- |
| (néant)    | -       | -      | -          |

---

## Notes et Observations

- [Motifs remarqués]
- [Suggestions pour l'avenir]
```

---

## Modèle \_MANIFEST.md

```markdown
# Manifeste d'Organisation

**Session** : [HORODATAGE]
**Plan** : `_PLAN.md`
**Journal** : `_LOG.md`

---

## Inventaire Pré-Organisation

| Extension | Nombre |
| :-------- | :----- |
| .pdf      | -      |
| .docx     | -      |
| .jpg/.png | -      |
| Autre     | -      |

---

## Résultats de l'Analyse du Contenu

| #   | Nom d'Origine | Contenu Trouvé | Nom Proposé | Confiance | Approuvé |
| :-- | :------------ | :------------- | :---------- | :-------- | :------- |
| 1   |               |                |             |           | ⬜       |

---

## Opérations sur les Fichiers

### Renommages

| #   | Horodatage | Origine | Nouveau Nom | Statut |
| :-- | :--------- | :------ | :---------- | :----- |
| 1   |            |         |             | ⬜     |

### Déplacements

| #   | Horodatage | Nom du Fichier | De  | Vers | Statut |
| :-- | :--------- | :------------- | :-- | :--- | :----- |
| 1   |            |                |     |      | ⬜     |

---

## Statistiques

| Métrique          | Nombre |
| :---------------- | :----- |
| Fichiers renommés | -      |
| Fichiers déplacés | -      |
| Erreurs           | -      |

---

## Informations de Retour en Arrière (Rollback)

Pour annuler : Référez-vous aux tableaux de renommages et de déplacements ci-dessus.
```
