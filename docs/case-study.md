# Case Study: HL7 v2 Interface Hub in Mirth Connect (ADT and ORU)

## Summary

I built two HL7 v2.5 interfaces in Mirth Connect 4.5.2 (open-source release) that mimic the core work of an HL7 integration analyst. A simulated registration system sends admit, discharge, and update messages (ADT), and a simulated lab system sends results (ORU). Mirth receives each message over MLLP, validates it, extracts the fields, and loads clean records into a SQLite database. Anything invalid is rejected with an error acknowledgment and logged to an exceptions table so someone can investigate it.

All data is synthetic, including the identifiers and SSN-format values. No real patient data was used.

## Why this project

Hospitals run many systems that cannot talk to each other directly, and most of them exchange HL7 v2 messages through an interface engine. The analyst's job is to define what each interface accepts, map the fields, test it before go-live, and support it when messages fail. I wanted a project that covers that whole lifecycle, not only the building.

## How it works

| Stage | ADT_Inbound (port 6661) | ORU_Inbound (port 6662) |
|---|---|---|
| Listen | MLLP listener, ACK returned to sender | MLLP listener, ACK returned to sender |
| Validate | Required segments (MSH, PID, PV1), message type, control ID, patient ID and name, valid dates (MSH-7, PID-7, PV1-44) | Required segments (MSH, PID, OBR, OBX), message type must be ORU^R01, control ID, patient fields, valid dates, and every OBX must have a test code and result value |
| Transform | Pulls patient and visit fields into channel variables | Pulls patient and order fields, then loops over every OBX and builds one result per line |
| Load | Upserts the patient by MRN, inserts one encounter row | Upserts the patient by MRN, inserts one `lab_results` row per OBX |
| On failure | Rejects with `AR` and writes a row to `exceptions_log` | Same |

Full detail is in `docs/interface-specification.md`, and the flow is drawn in `docs/data-flow.md`.

## Results

- 36 valid messages (18 ADT: 6 A01, 6 A03, 6 A08; 18 ORU) were all accepted (`AA`).
- 5 deliberately broken messages were all rejected (`AR`) and logged: missing PID, missing PV1, truncated header, invalid dates, and a lab result with no value.
- Final database: 36 patients, 18 encounters, 58 lab results (matching the 58 OBX segments in the source files), 5 exception rows. The SSN is never stored.
- Evidence is in `screenshots/` and the test cases are in `docs/test-plan.md`.

## Defects found during testing

1. **Admit time in the wrong field.** My generated ADT messages put the admit time in PV1-45, but the HL7 v2.5 standard puts it in PV1-44. I fixed the sample data instead of changing the channel to match the mistake.
2. **Lab segment fields one position early.** The same kind of error appeared in OBR and OBX, which I also fixed in the generator.
3. **Validation was too shallow.** My first filter only checked that segments existed, so a message with a truncated header and a message with a birth date of `13/45/2026` both got through and wrote bad rows. I extended the filter to check required fields and date validity and to log each failure under its own category.
4. **Wrong writer in a cloned channel.** I cloned the ADT channel to make the lab channel and it still contained the ADT database writer, so the first lab message created a half-empty encounter. The acknowledgment still said `AA` because the ACK is built before the destination runs, so I traced it through the Message Browser and fixed the writer.

## Design decisions

- **Reject and log, never silently drop.** The sender gets `AR`, and the failure is stored with its category and the raw message.
- **Minimum necessary.** The SSN is in the source messages but is deliberately not mapped to the database.
- **Fix the data, not the standard.** When the samples disagreed with HL7 v2.5, I corrected the samples.

## Known limitations

- Re-sending a message creates duplicate encounter and lab rows. Only patients are protected by an upsert on MRN.
- Discharge (A03) and update (A08) messages insert new encounter rows instead of updating an existing one.
- Lab rows have no `encounter_id`, because the lab patients were never admitted through the ADT channel.
- Not tested: a zero-byte message (my sender script skips empty files), and a destination failure (`AE`). Because the ACK is generated before the destination runs, a database failure would not change the ACK. I have not yet proven that with a deliberate failure.
- Open-source Mirth Connect 4.5.2 on a single machine, with no TLS, monitoring, or alerting.

## What I would add for production

Deduplication on message control ID, encounter updates keyed on the account number, alerting on the exceptions table, TLS on the listeners, and a message-retention policy.

## Skills demonstrated

HL7 v2.x message structure (MSH, PID, PV1, OBR, OBX), Mirth Connect channel design (filters, transformers, JavaScript writers), repeating-segment handling, ACK/NACK semantics, field mapping, validation and exception handling, SQL, test planning, and interface documentation.

## Next

Project 2 converts these HL7 v2 records to FHIR R4 resources and adds a troubleshooting runbook for common interface failures.
