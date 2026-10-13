# Malformed HL7 Sample Messages

These files are intentionally invalid HL7 v2.5 messages, generated for testing
Mirth Connect channel error handling, filters, and the `exceptions_log` table.

## 01_missing_pid.hl7

ADT^A01 message has no PID segment at all. A compliant parser needs PID to identify the patient; this simulates a registration feed dropping the segment mid-transmission.

## 02_broken_msh.hl7

MSH segment is truncated: the encoding characters field is malformed ("^~\&" is cut short and the pipe placement is wrong) and required fields (receiving app/facility, timestamp, message type, control ID, version) are missing entirely.

## 03_bad_date_format.hl7

MSH-7 (message timestamp) uses "10/06/2026 12:00pm" instead of HL7 TS format YYYYMMDDHHMMSS, and PID-7 (date of birth) uses an invalid "13/45/2026" (month 13, day 45 do not exist).

## 04_missing_obx_value.hl7

The single OBX segment has an empty OBX-5 (observation value) field -- the result code, units, and reference range are present but the actual lab value was dropped.

## 05_missing_pv1.hl7

ADT^A01 message has no PV1 segment, so there is no patient class, location, or attending doctor -- required visit information for an admit event is absent.

## 06_empty_message.hl7

The file is completely empty (0 bytes) -- simulates a zero-length payload reaching the listener, e.g. from a network glitch or an upstream system sending a keep-alive with no actual HL7 content.
