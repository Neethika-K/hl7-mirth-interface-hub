-- Schema for the Mirth Connect HL7 interface portfolio project.
-- Target: SQLite (built via `sqlite3 mirth.db < schema.sql`)

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS exceptions_log;
DROP TABLE IF EXISTS lab_results;
DROP TABLE IF EXISTS encounters;
DROP TABLE IF EXISTS patients;

CREATE TABLE patients (
    patient_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    mrn             TEXT NOT NULL UNIQUE,
    last_name       TEXT NOT NULL,
    first_name      TEXT NOT NULL,
    middle_name     TEXT,
    date_of_birth   TEXT,              -- YYYYMMDD
    gender          TEXT,              -- M/F/U
    address_street  TEXT,
    address_city    TEXT,
    address_state   TEXT,
    address_zip     TEXT,
    phone           TEXT,
    ssn             TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE encounters (
    encounter_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL REFERENCES patients(patient_id),
    account_number  TEXT,
    message_control_id TEXT,
    event_type      TEXT,              -- A01, A03, A08, ...
    patient_class   TEXT,              -- I, O, E, ...
    location        TEXT,
    attending_doctor TEXT,
    admit_datetime  TEXT,              -- YYYYMMDDHHMMSS
    discharge_datetime TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lab_results (
    lab_result_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL REFERENCES patients(patient_id),
    encounter_id    INTEGER REFERENCES encounters(encounter_id),
    order_number    TEXT,
    result_number   TEXT,
    loinc_code      TEXT NOT NULL,
    loinc_name      TEXT,
    value           TEXT,
    units           TEXT,
    reference_range TEXT,
    abnormal_flag   TEXT,              -- N, H, L, A, ...
    result_status   TEXT,              -- F, P, C, ...
    observed_at     TEXT,              -- YYYYMMDDHHMMSS
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE exceptions_log (
    exception_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    source_filename  TEXT,
    message_control_id TEXT,
    message_type    TEXT,
    error_category  TEXT,              -- e.g. MISSING_SEGMENT, BAD_DATE, PARSE_ERROR
    error_detail    TEXT,
    raw_message     TEXT,
    occurred_at     TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_encounters_patient_id ON encounters(patient_id);
CREATE INDEX idx_lab_results_patient_id ON lab_results(patient_id);
CREATE INDEX idx_lab_results_encounter_id ON lab_results(encounter_id);
CREATE INDEX idx_lab_results_loinc_code ON lab_results(loinc_code);
