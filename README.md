# HL7 ADT/ORU Interface Hub (Mirth Connect)

Two HL7 v2.5 interfaces built in Mirth Connect 4.5.2 that mimic the core work of an HL7 integration analyst. Simulated registration and lab systems send ADT (admit, discharge, update) and ORU (lab result) messages over MLLP. Mirth validates each message, extracts the fields, and loads clean records into SQLite. Invalid messages are rejected with an error acknowledgment and logged to an exceptions table.

**All data is synthetic**, including names, MRNs, and SSN-format values. No real patient data was used.

## What's in this repo

| Path | Contents |
|---|---|
| `channels/ADT_Inbound.xml` | Exported Mirth channel for ADT messages (port 6661) |
| `channels/ORU_Inbound.xml` | Exported Mirth channel for lab results (port 6662) |
| `docs/interface-specification.md` | Interface spec: transport, field mappings, validation rules, limitations |
| `docs/test-plan.md` | Test cases with results, defects found during testing |
| `docs/data-flow.md` | Data flow diagram (Mermaid, renders on GitHub) |
| `docs/case-study.md` | One-page write-up of the project |
| `sql/schema.sql` | SQLite schema: `patients`, `encounters`, `lab_results`, `exceptions_log` |
| `scripts/generate_hl7.py` | Generates the synthetic sample messages |
| `scripts/send_mllp.py` | Sends HL7 files to Mirth over MLLP and prints the ACK |
| `sample-messages/valid/` | 18 ADT and 18 ORU messages |
| `sample-messages/malformed/` | 6 deliberately broken messages, each described in its README |
| `screenshots/` | Mirth dashboard, message browser, and test evidence |

## How it works

| | ADT_Inbound | ORU_Inbound |
|---|---|---|
| Port | 6661 | 6662 |
| Accepts | ADT^A01, A03, A08 | ORU^R01 |
| Validates | Required segments, header fields, patient fields, dates | Required segments, header fields, patient fields, dates, every OBX has a code and a value |
| Loads | Patient (upsert by MRN) + one encounter row | Patient (upsert by MRN) + one `lab_results` row per OBX |
| On failure | `AR` acknowledgment + row in `exceptions_log` | Same |

## Results

- 36 valid messages accepted (`AA`); 5 broken messages rejected (`AR`) and logged.
- Database after the full run: 36 patients, 18 encounters, 58 lab results (matching the 58 OBX segments in the source files), 5 exception rows. The SSN is never stored.
- See `docs/test-plan.md` for every test case and the defects found and fixed along the way.

## Run it yourself

You need Java 17, Python 3, `sqlite3`, and Mirth Connect 4.5.2 (not included in this repo).

1. Download Mirth Connect 4.5.2 from the NextGen releases and start the server (`./mcserver`). Open the Mirth Connect Administrator and log in.
2. Create the database: `sqlite3 sql/mirth.db < sql/schema.sql`
3. In the Administrator, click **Channels**, then **Import Channel**, and import both XML files from `channels/`.
4. **Edit the database path.** The exported channels use the placeholder `/path/to/MIRTH-PROJECT/sql/mirth.db`. Replace it with your real path in three places in each channel: the source filter (exception logging), and the destination writer (its URL field and its script).
5. Deploy both channels.
6. Send messages: `python3 scripts/send_mllp.py sample-messages/valid/ADT_A01_003.hl7` (the sender picks port 6661 or 6662 from the message type).
7. Check the results: `sqlite3 -header -column sql/mirth.db "SELECT * FROM patients LIMIT 5;"`

The sample messages are already included. Regenerating them with `scripts/generate_hl7.py` is optional.

## Known limitations

- Re-sending a message creates duplicate encounter and lab rows (only patients are upserted).
- A03 and A08 messages insert new encounter rows instead of updating an existing one.
- Lab rows have no `encounter_id`.
- Not tested: a zero-byte message, and a database failure at the destination.
- Single machine, no TLS, monitoring, or
cat > README.md <<'EOF'
# HL7 ADT/ORU Interface Hub (Mirth Connect)

Two HL7 v2.5 interfaces built in Mirth Connect 4.5.2 that mimic the core work of an HL7 integration analyst. Simulated registration and lab systems send ADT (admit, discharge, update) and ORU (lab result) messages over MLLP. Mirth validates each message, extracts the fields, and loads clean records into SQLite. Invalid messages are rejected with an error acknowledgment and logged to an exceptions table.

**All data is synthetic**, including names, MRNs, and SSN-format values. No real patient data was used.

## What's in this repo

| Path | Contents |
|---|---|
| `channels/ADT_Inbound.xml` | Exported Mirth channel for ADT messages (port 6661) |
| `channels/ORU_Inbound.xml` | Exported Mirth channel for lab results (port 6662) |
| `docs/interface-specification.md` | Interface spec: transport, field mappings, validation rules, limitations |
| `docs/test-plan.md` | Test cases with results, defects found during testing |
| `docs/data-flow.md` | Data flow diagram (Mermaid, renders on GitHub) |
| `docs/case-study.md` | One-page write-up of the project |
| `sql/schema.sql` | SQLite schema: `patients`, `encounters`, `lab_results`, `exceptions_log` |
| `scripts/generate_hl7.py` | Generates the synthetic sample messages |
| `scripts/send_mllp.py` | Sends HL7 files to Mirth over MLLP and prints the ACK |
| `sample-messages/valid/` | 18 ADT and 18 ORU messages |
| `sample-messages/malformed/` | 6 deliberately broken messages, each described in its README |
| `screenshots/` | Mirth dashboard, message browser, and test evidence |

## How it works

| | ADT_Inbound | ORU_Inbound |
|---|---|---|
| Port | 6661 | 6662 |
| Accepts | ADT^A01, A03, A08 | ORU^R01 |
| Validates | Required segments, header fields, patient fields, dates | Required segments, header fields, patient fields, dates, every OBX has a code and a value |
| Loads | Patient (upsert by MRN) + one encounter row | Patient (upsert by MRN) + one `lab_results` row per OBX |
| On failure | `AR` acknowledgment + row in `exceptions_log` | Same |

## Results

- 36 valid messages accepted (`AA`); 5 broken messages rejected (`AR`) and logged.
- Database after the full run: 36 patients, 18 encounters, 58 lab results (matching the 58 OBX segments in the source files), 5 exception rows. The SSN is never stored.
- See `docs/test-plan.md` for every test case and the defects found and fixed along the way.

## Run it yourself

You need Java 17, Python 3, `sqlite3`, and Mirth Connect 4.5.2 (not included in this repo).

1. Download Mirth Connect 4.5.2 from the NextGen releases and start the server (`./mcserver`). Open the Mirth Connect Administrator and log in.
2. Create the database: `sqlite3 sql/mirth.db < sql/schema.sql`
3. In the Administrator, click **Channels**, then **Import Channel**, and import both XML files from `channels/`.
4. **Edit the database path.** The exported channels use the placeholder `/path/to/MIRTH-PROJECT/sql/mirth.db`. Replace it with your real path in three places in each channel: the source filter (exception logging), and the destination writer (its URL field and its script).
5. Deploy both channels.
6. Send messages: `python3 scripts/send_mllp.py sample-messages/valid/ADT_A01_003.hl7` (the sender picks port 6661 or 6662 from the message type).
7. Check the results: `sqlite3 -header -column sql/mirth.db "SELECT * FROM patients LIMIT 5;"`

The sample messages are already included. Regenerating them with `scripts/generate_hl7.py` is optional.

## Known limitations

- Re-sending a message creates duplicate encounter and lab rows (only patients are upserted).
- A03 and A08 messages insert new encounter rows instead of updating an existing one.
- Lab rows have no `encounter_id`.
- Not tested: a zero-byte message, and a database failure at the destination.
- Single machine, no TLS, monitoring, or alerting.

## Tools

Mirth Connect 4.5.2, HL7 v2.5, SQLite, Python 3, JavaScript (Mirth transformers and writers).
