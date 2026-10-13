# Test Plan — Mirth Connect ADT/ORU Interfaces

Scope: functional validation of `ADT_Inbound` (port 6661) and `ORU_Inbound` (port 6662) against the
sample messages in `sample-messages/valid/` and `sample-messages/malformed/`. Test execution itself
was performed outside this session (recorded results below, dated 2026-10-13); this document
reports those results and independently re-verifies the database-level claims with read-only SQLite
queries against `sql/mirth.db` (`sqlite3 -readonly ...`). No messages were sent to Mirth as part of
producing this document. The valid ADT set is 18 messages total: 6 ADT^A01, 6 ADT^A03, and 6
ADT^A08, matching `generate_adt_messages()` in `scripts/generate_hl7.py`
(`types = (["A01"] * 6) + (["A03"] * 6) + (["A08"] * 6)`) and the live database
(`SELECT event_type, COUNT(*) FROM encounters GROUP BY event_type` → A01=6, A03=6, A08=6).

## 1. Test Case Results

| ID | Scenario | Input file(s) | Port | Expected result | Actual result (2026-10-13) | Pass/Fail |
|---|---|---|---|---|---|---|
| TC-01 | Valid ADT admit (A01) | `ADT_A01_001.hl7` … `ADT_A01_018.hl7` (6 files) | 6661 | Filter passes; ACK `AA`; 1 `patients` row upserted + 1 `encounters` row per message | ACK `AA` on all 6; 6 `encounters` rows with `event_type='A01'` | PASS |
| TC-02 | Valid ADT discharge (A03) | `ADT_A03_004.hl7`, `006`, `008`, `009`, `012`, `016` (6 files) | 6661 | Filter passes; ACK `AA`; 1 `encounters` row per message | ACK `AA` on all 6; 6 `encounters` rows with `event_type='A03'` | PASS |
| TC-03 | Valid ADT update (A08) | `ADT_A08_001.hl7`, `002`, `007`, `010`, `014`, `015` (6 files) | 6661 | Filter passes; ACK `AA`; 1 `encounters` row per message | ACK `AA` on all 6; 6 `encounters` rows with `event_type='A08'` | PASS |
| TC-04 | Valid lab results (ORU^R01) | `ORU_R01_001.hl7` … `ORU_R01_018.hl7` (18 files) | 6662 | Filter passes; ACK `AA`; 1 `patients` row upserted + one `lab_results` row per OBX | ACK `AA` on all 18; 58 total `lab_results` rows across the 18 messages | PASS |
| TC-05 | Missing PID segment | `01_missing_pid.hl7` | 6661 | Filter rejects; ACK `AR`; `exceptions_log` row, category `MISSING_SEGMENT` (PID); no `patients`/`encounters` rows written | ACK `AR`; 1 `exceptions_log` row, `error_category='MISSING_SEGMENT'`, detail "Missing required segment: PID" | PASS |
| TC-06 | Broken MSH (missing MSH-9, MSH-10) | `02_broken_msh.hl7` | 6661 (type undetectable, falls back to default port in `send_mllp.py`) | Filter rejects; ACK `AR`; `exceptions_log` row, category `MISSING_FIELD` (MSH-9 and MSH-10) | ACK `AR`; 1 `exceptions_log` row, `error_category='MISSING_FIELD'`, detail covers both MSH-9 and MSH-10; `message_control_id` and `message_type` columns blank (expected — MSH was unreadable) | PASS |
| TC-07 | Bad date formats | `03_bad_date_format.hl7` | 6661 | Filter rejects; ACK `AR`; `exceptions_log` row, category `BAD_DATE`, covering MSH-7, PID-7, and PV1-44 | ACK `AR`; 1 `exceptions_log` row, `error_category='BAD_DATE'`, detail lists MSH-7, PID-7, and PV1-44 all as invalid | PASS |
| TC-08 | Missing OBX value | `04_missing_obx_value.hl7` | 6662 | Filter rejects; ACK `AR`; `exceptions_log` row, category `MISSING_FIELD` (OBX-5) | ACK `AR`; 1 `exceptions_log` row, `error_category='MISSING_FIELD'`, detail "OBX #1: result value (OBX-5) is missing" | PASS |
| TC-09 | Missing PV1 segment | `05_missing_pv1.hl7` | 6661 | Filter rejects; ACK `AR`; `exceptions_log` row, category `MISSING_SEGMENT` (PV1) | ACK `AR`; 1 `exceptions_log` row, `error_category='MISSING_SEGMENT'`, detail "Missing required segment: PV1" | PASS |
| TC-10 | Zero-byte / empty message | `06_empty_message.hl7` | n/a | **Untested.** `scripts/send_mllp.py` skips any file whose content is empty/whitespace-only before opening a socket, so this file was never actually sent to Mirth | Message was skipped by the sender script (confirmed: file is 0 bytes on disk); no ACK, no `exceptions_log` row, Mirth's behavior on a genuinely empty MLLP payload remains unobserved | NOT RUN — see Limitations |
| TC-11 | Re-send of an already-processed message (duplicate detection) | `ADT_A01_003.hl7` (MSG00003), sent twice on 2026-10-12 | 6661 | Ambiguous/undocumented behavior — no explicit dedup requirement exists in the filter or destination query | ACK `AA` on both sends (filter has no dedup logic). Sending `MSG00003` a second time created a second `encounters` row instead of being recognized as a repeat. Observed with: `SELECT message_control_id, COUNT(*) FROM encounters GROUP BY message_control_id HAVING COUNT(*) > 1;` → `MSG00003 \| 2`. | FAIL — duplicate row confirms the limitation described in §3 |

## 2. Database Totals — Verified by Read-Only Query

Run against `sql/mirth.db` with `sqlite3 -readonly` (no write access used):

| Check | Query | Recorded claim | Verified result | Match? |
|---|---|---|---|---|
| Patient count | `SELECT COUNT(*) FROM patients;` | 36 | 36 | Yes |
| Encounter count | `SELECT COUNT(*) FROM encounters;` | 18 | 18 | Yes |
| Encounters by event type | `SELECT event_type, COUNT(*) FROM encounters GROUP BY event_type;` | 6 A01, 6 A03, 6 A08 (18 total) | A01=6, A03=6, A08=6 | Yes |
| Lab result count | `SELECT COUNT(*) FROM lab_results;` | 58 | 58 | Yes |
| Lab results by LOINC code | `SELECT loinc_code, loinc_name, COUNT(*) FROM lab_results GROUP BY loinc_code;` | 2160-0 ×15, 2345-7 ×12, 6690-2 ×14, 718-7 ×17 | 2160-0 (Creatinine) ×15, 2345-7 (Glucose) ×12, 6690-2 (Leukocytes) ×14, 718-7 (Hemoglobin) ×17 | Yes |
| Lab results with empty value | `SELECT COUNT(*) FROM lab_results WHERE value IS NULL OR value = '';` | 0 | 0 | Yes |
| Exceptions logged | `SELECT COUNT(*) FROM exceptions_log;` | 5 | 5 | Yes |
| Exceptions by category | `SELECT error_category, COUNT(*) FROM exceptions_log GROUP BY error_category;` | BAD_DATE ×1, MISSING_FIELD ×2, MISSING_SEGMENT ×2 | BAD_DATE ×1, MISSING_FIELD ×2, MISSING_SEGMENT ×2 | Yes |

### SSN check

Recorded claim: "SSN is deliberately not stored (minimum necessary)."

```sql
SELECT COUNT(*) FROM patients WHERE ssn IS NOT NULL AND ssn != '';
```

Result: **0** of 36 patients have a non-blank `ssn`, even though every generated HL7 message does
include a synthetic SSN in PID-19 (confirmed in `scripts/generate_hl7.py`'s `build_pid`, and
visible in the raw sample files, e.g. `463-36-5374` in `ADT_A01_003.hl7`). This confirms the claim:
neither channel's transformer extracts PID-19, and neither destination INSERT writes to the
`patients.ssn` column, even though the column exists in `sql/schema.sql`.

### Lab result `encounter_id`

```sql
SELECT COUNT(*) FROM lab_results WHERE encounter_id IS NULL;
```

Result: **58 of 58** — every `lab_results` row has a `NULL` `encounter_id`, consistent with the
claim that lab patients are not admitted through the ADT channel and the ORU destination query
never populates that column.

## 3. Defects Found During Testing

| # | Defect | Status |
|---|---|---|
| a | Generated ADT sample messages originally placed the admit date/time in **PV1-45** instead of the HL7 v2.5-correct **PV1-44**. Fixed in `scripts/generate_hl7.py` (`build_pv1`); current generator writes admit time to PV1-44 and, for discharges, appends discharge time as PV1-45 — confirmed by field-counting `ADT_A01_003.hl7`'s PV1 segment (field index 44 holds the timestamp) and `ADT_A03_004.hl7`'s PV1 segment (indices 44 and 45 both populated). | Fixed |
| b | Generated ORU sample messages originally placed several OBR and OBX fields earlier than their correct HL7 v2.5 positions. Fixed in the generator; confirmed against the current `build_obr`/`build_obx` output (e.g. OBR-7 observation date/time, OBR-16 ordering provider, OBX-3 test code, OBX-5 value, OBX-6 units, OBX-7 reference range, OBX-8 abnormal flag, OBX-11 result status all land at the field indices the channel transformers read). | Fixed |
| c | The first version of each channel's filter only checked that required segments **existed**, not that required fields were populated or that dates were valid. As a result, `02_broken_msh.hl7` (missing MSH-9/MSH-10) and `03_bad_date_format.hl7` (invalid dates) were **accepted** and wrote bad rows into `patients`/`encounters`. The filter was extended to add the field-presence and date-validity checks documented in `docs/interface-specification.md` §7, with every rejection logged to `exceptions_log`. | Fixed |
| d | The cloned `ORU_Inbound` channel (cloned from `ADT_Inbound`) initially still contained the ADT channel's `patients`+`encounters` Database Writer query, which caused ORU messages to create a half-empty `encounters` row (no lab data) instead of `lab_results` rows. Fixed by replacing the destination query with the `patients`+`lab_results` query now in `channels/ORU_Inbound.xml`. | Fixed |
| e *(discovered during this review, not in the original list)* | Re-sending a previously processed ADT message (`MSG00003` on 2026-10-12) created a **duplicate `encounters` row** with no error or warning — see TC-11. This is not fixed; it is a consequence of the limitation described below (no dedup key on `encounters`/`lab_results`). | Open — tracked as a limitation, not patched |

## 4. Limitations

- **No encounter update logic.** A03 (discharge) and A08 (update) events do not locate and update
  the ADT_Inbound encounter they logically belong to; every ADT event — A01, A03, or A08 — inserts
  a brand-new `encounters` row. `encounters.discharge_datetime` is never populated by any event
  type.
- **No message-replay protection.** Only `patients` is deduplicated, via `ON CONFLICT(mrn) DO
  UPDATE`. `encounters` and `lab_results` have no uniqueness constraint tied to message control ID,
  so re-sending the same `.hl7` file creates additional rows — demonstrated by TC-11.
- **`lab_results.encounter_id` is always NULL.** Lab patients are not admitted through the ADT
  channel as part of this project's flow, so ORU_Inbound has no encounter to link a lab result to,
  and its destination query does not populate the column.
- **SSN is deliberately not stored**, per the minimum-necessary-data design choice described above
  — confirmed empty for all 36 patients despite being present in every source message.
- **All data is synthetic** (`scripts/generate_hl7.py`, fixed random seed); none of this is real
  PHI.
- **This project runs on open-source Mirth Connect 4.5.2**, not a commercial edition.
- **TC-10 (empty message) was not actually exercised against Mirth.** `scripts/send_mllp.py` skips
  zero-byte files before connecting, so there is no observed evidence of how the MLLP listener
  behaves on a truly empty payload (e.g. whether it times out, sends a NACK byte, or something
  else). TODO: this needs a dedicated manual test (e.g. a raw socket script that sends just
  `0x0B 0x1C 0x0D` with no content) before it can be documented with confidence.
- **No observed `AE` (Application Error) ACK.** All rejections in this test run were `AR` (filter
  rejections); no destination-side runtime error occurred, so this test plan has no example of the
  `AE` path described in the interface specification. TODO if destination-failure testing (e.g.
  pointing the JDBC URL at a locked or missing database file) is in scope.
