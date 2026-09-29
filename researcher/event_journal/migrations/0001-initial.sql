CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY CHECK (version > 0),
    name TEXT NOT NULL UNIQUE,
    digest TEXT NOT NULL CHECK (digest GLOB 'sha256:[0-9a-f]*' AND length(digest) = 71),
    applied_at TEXT NOT NULL
) STRICT;

CREATE TABLE journal_entries (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    idempotency_scope TEXT NOT NULL,
    idempotency_key_digest TEXT NOT NULL,
    subject_kind TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    subject_version INTEGER NOT NULL CHECK (subject_version > 0),
    event_type TEXT NOT NULL,
    classification TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    event_json BLOB NOT NULL CHECK (length(event_json) <= 65536),
    event_digest TEXT NOT NULL,
    received_at TEXT NOT NULL,
    previous_entry_hash TEXT,
    entry_hash TEXT NOT NULL UNIQUE,
    UNIQUE (idempotency_scope, idempotency_key_digest),
    UNIQUE (subject_kind, subject_id, subject_version),
    FOREIGN KEY (previous_entry_hash) REFERENCES journal_entries(entry_hash)
) STRICT;

CREATE INDEX journal_entries_subject_sequence
    ON journal_entries(subject_kind, subject_id, sequence);
CREATE INDEX journal_entries_event_type_sequence
    ON journal_entries(event_type, sequence);

CREATE TABLE journal_control (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    last_sequence INTEGER,
    last_entry_hash TEXT,
    integrity_state TEXT NOT NULL CHECK (integrity_state IN ('healthy', 'operator_halt')),
    last_verified_sequence INTEGER,
    last_verified_hash TEXT,
    last_verified_at TEXT,
    FOREIGN KEY (last_sequence) REFERENCES journal_entries(sequence),
    FOREIGN KEY (last_entry_hash) REFERENCES journal_entries(entry_hash)
) STRICT;

INSERT INTO journal_control (
    singleton,
    last_sequence,
    last_entry_hash,
    integrity_state,
    last_verified_sequence,
    last_verified_hash,
    last_verified_at
) VALUES (1, NULL, NULL, 'healthy', NULL, NULL, NULL);

CREATE TABLE subject_versions (
    subject_kind TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    last_sequence INTEGER NOT NULL,
    PRIMARY KEY (subject_kind, subject_id),
    FOREIGN KEY (last_sequence) REFERENCES journal_entries(sequence)
) STRICT;

CREATE TRIGGER journal_entries_immutable_update
BEFORE UPDATE ON journal_entries
BEGIN
    SELECT RAISE(ABORT, 'JOURNAL_ENTRY_IMMUTABLE');
END;

CREATE TRIGGER journal_entries_immutable_delete
BEFORE DELETE ON journal_entries
BEGIN
    SELECT RAISE(ABORT, 'JOURNAL_ENTRY_IMMUTABLE');
END;
