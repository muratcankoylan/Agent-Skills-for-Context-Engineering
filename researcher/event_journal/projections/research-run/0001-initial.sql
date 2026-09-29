CREATE TABLE projector_control (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    projector_name TEXT NOT NULL,
    projector_version TEXT NOT NULL,
    last_sequence INTEGER NOT NULL CHECK (last_sequence >= 0),
    source_hash TEXT,
    state_digest TEXT NOT NULL,
    updated_at TEXT NOT NULL
) STRICT;

CREATE TABLE research_run_projections (
    subject_id TEXT PRIMARY KEY,
    subject_version INTEGER NOT NULL CHECK (subject_version > 0),
    current_state TEXT NOT NULL,
    close_status TEXT,
    last_occurred_at TEXT NOT NULL,
    classification TEXT NOT NULL,
    last_sequence INTEGER NOT NULL CHECK (last_sequence > 0),
    last_event_id TEXT NOT NULL
) STRICT;

CREATE TABLE projection_quarantines (
    subject_kind TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    first_sequence INTEGER NOT NULL CHECK (first_sequence > 0),
    event_id TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (subject_kind, subject_id)
) STRICT;
