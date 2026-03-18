# Organization Templates

Initialize these files in the `_ORG/` folder before starting.

---

## \_PLAN.md Template

```markdown
# Downloads Organization Plan

**Created on**: [TIMESTAMP]
**Last updated**: [TIMESTAMP]
**Status**: ⬜ Not started

---

## Overview

**Target folder**: ~/Downloads
**Total files found**: [waiting for scan]

---

## Phase 1: Discovery and Inventory

| Task                          | Status | Start | End | Notes |
| :---------------------------- | :----- | :---- | :-- | :---- |
| 1.1 List all files            | ⬜     | -     | -   |       |
| 1.2 Count by extension        | ⬜     | -     | -   |       |
| 1.3 Identify date range       | ⬜     | -     | -   |       |
| 1.4 Flag large files (>100MB) | ⬜     | -     | -   |       |
| 1.5 Flag sensitive files      | ⬜     | -     | -   |       |
| 1.6 Evaluate naming quality   | ⬜     | -     | -   |       |

---

## Phase 2: Content Analysis

| Task                          | Status | Start | End | Notes         |
| :---------------------------- | :----- | :---- | :-- | :------------ |
| 2.1 Analyze documents         | ⬜     | -     | -   |               |
| 2.2 Analyze images            | ⬜     | -     | -   |               |
| 2.3 Analyze spreadsheets      | ⬜     | -     | -   |               |
| 2.4 Generate proposed renames | ⬜     | -     | -   |               |
| 2.5 Present for approval      | ⬜     | -     | -   | ⚠️ CHECKPOINT |

---

## Phase 3: Preparation

| Task                        | Status | Start | End | Notes       |
| :-------------------------- | :----- | :---- | :-- | :---------- |
| 3.1 Create folder structure | ⬜     | -     | -   |             |
| 3.2 Approval checkpoint     | ⬜     | -     | -   | ⚠️ REQUIRED |

---

## Phase 4: Execution

| Task                       | Status | Start | End | Notes |
| :------------------------- | :----- | :---- | :-- | :---- |
| 4.1 Rename approved files  | ⬜     | -     | -   |       |
| 4.2 Move HIGH confidence   | ⬜     | -     | -   |       |
| 4.3 Move MEDIUM confidence | ⬜     | -     | -   |       |
| 4.4 Move LOW → \_REVISE    | ⬜     | -     | -   |       |
| 4.5 Handle duplicates      | ⬜     | -     | -   |       |
| 4.6 Handle large files     | ⬜     | -     | -   |       |

---

## Phase 5: Finalization

| Task                  | Status | Start | End | Notes |
| :-------------------- | :----- | :---- | :-- | :---- |
| 5.1 Generate summary  | ⬜     | -     | -   |       |
| 5.2 Finalize manifest | ⬜     | -     | -   |       |

---

## Final Summary

| Metric                | Count |
| :-------------------- | :---- |
| Total files processed | -     |
| Files renamed         | -     |
| Files moved           | -     |
| Files in \_REVISE     | -     |
| Errors                | -     |
```

---

## \_LOG.md Template

```markdown
# Organization Log

**Session started on**: [TIMESTAMP]
**Target folder**: ~/Downloads

---

## Session Log

### [TIMESTAMP] - SESSION

**Action**: Organization session started
**Target**: ~/Downloads
**Next**: Start Phase 1 (Discovery)

---

<!-- Add entries as you go -->

---

## Error Summary

| Timestamp | File | Error | Resolution |
| :-------- | :--- | :---- | :--------- |
| (none)    | -    | -     | -          |

---

## Notes and Observations

- [Noticed patterns]
- [Suggestions for future]
```

---

## \_MANIFEST.md Template

```markdown
# Organization Manifest

**Session**: [TIMESTAMP]
**Plan**: `_PLAN.md`
**Log**: `_LOG.md`

---

## Pre-Organization Inventory

| Extension | Count |
| :-------- | :---- |
| .pdf      | -     |
| .docx     | -     |
| .jpg/.png | -     |
| Other     | -     |

---

## Content Analysis Results

| #   | Original Name | Found Content | Proposed Name | Confidence | Approved |
| :-- | :------------ | :------------ | :------------ | :--------- | :------- |
| 1   |               |               |               |            | ⬜       |

---

## File Operations

### Renames

| #   | Timestamp | Original | New Name | Status |
| :-- | :-------- | :------- | :------- | :----- |
| 1   |           |          |          | ⬜     |

### Moves

| #   | Timestamp | File Name | From | To  | Status |
| :-- | :-------- | :-------- | :--- | :-- | :----- |
| 1   |           |           |      |     | ⬜     |

---

## Statistics

| Metric        | Count |
| :------------ | :---- |
| Files renamed | -     |
| Files moved   | -     |
| Errors        | -     |

---

## Rollback Information

To undo: Refer to the rename and move tables above.
```
