# Data Flow — ADT_Inbound and ORU_Inbound

Both channels share the same shape: MLLP listener → source filter (validate/reject) → source
transformer (extract fields) → JDBC database writer destination → SQLite. The ACK sent back to the
sender is generated automatically from the filter's accept/reject decision
(`responseVariable = Auto-generate (After source transformer)`), but is not actually transmitted
until the whole message — including the destination write — has finished processing
(`respondAfterProcessing = true`), per `channels/ADT_Inbound.xml` and `channels/ORU_Inbound.xml`.

```mermaid
flowchart TD
    subgraph ADT["ADT_Inbound — port 6661"]
        direction TB
        A_Sender["Simulated registration system<br/>(scripts/send_mllp.py)<br/>ADT^A01 / A03 / A08"]
        A_Listener["MLLP Listener<br/>TCP Receiver :6661"]
        A_Filter{"Source Filter:<br/>Require MSH, PID, PV1<br/>+ required fields + valid dates"}
        A_Transform["Source Transformer:<br/>Extract ADT fields<br/>into channelMap"]
        A_DBWriter["Destination: Database Writer<br/>1. Upsert patients by MRN<br/>2. Insert new encounters row"]
        A_Exc[("INSERT INTO exceptions_log<br/>category + detail + raw_message")]
        A_AA(["ACK AA<br/>(Application Accept)"])
        A_AR(["ACK AR<br/>(Application Reject)"])

        A_Sender -- "MLLP: 0x0B ... 0x1C 0x0D" --> A_Listener
        A_Listener --> A_Filter
        A_Filter -- "problem found<br/>(MISSING_SEGMENT /<br/>MISSING_FIELD / BAD_DATE)" --> A_Exc
        A_Exc --> A_AR
        A_Filter -- "no problems" --> A_Transform
        A_Transform --> A_DBWriter
        A_DBWriter --> A_AA
        A_AA -. "sent after destination write completes<br/>(respondAfterProcessing=true)" .-> A_Sender
        A_AR -. "sent after exceptions_log write completes" .-> A_Sender
    end

    subgraph ORU["ORU_Inbound — port 6662"]
        direction TB
        O_Sender["Simulated lab system<br/>(scripts/send_mllp.py)<br/>ORU^R01"]
        O_Listener["MLLP Listener<br/>TCP Receiver :6662"]
        O_Filter{"Source Filter:<br/>Require MSH, PID, OBR, OBX<br/>+ required fields + valid dates<br/>+ MSH-9 must equal ORU^R01"}
        O_Transform["Source Transformer:<br/>Extract patient + OBR fields,<br/>build one result{} per OBX"]
        O_DBWriter["Destination: Database Writer<br/>1. Upsert patients by MRN<br/>2. Insert one lab_results row per OBX"]
        O_Exc[("INSERT INTO exceptions_log<br/>category + detail + raw_message")]
        O_AA(["ACK AA<br/>(Application Accept)"])
        O_AR(["ACK AR<br/>(Application Reject)"])

        O_Sender -- "MLLP: 0x0B ... 0x1C 0x0D" --> O_Listener
        O_Listener --> O_Filter
        O_Filter -- "problem found<br/>(MISSING_SEGMENT /<br/>MISSING_FIELD / BAD_DATE /<br/>WRONG_MESSAGE_TYPE)" --> O_Exc
        O_Exc --> O_AR
        O_Filter -- "no problems" --> O_Transform
        O_Transform --> O_DBWriter
        O_DBWriter --> O_AA
        O_AA -. "sent after destination write completes<br/>(respondAfterProcessing=true)" .-> O_Sender
        O_AR -. "sent after exceptions_log write completes" .-> O_Sender
    end

    DB[("SQLite: sql/mirth.db<br/>patients / encounters /<br/>lab_results / exceptions_log")]
    A_DBWriter -.-> DB
    A_Exc -.-> DB
    O_DBWriter -.-> DB
    O_Exc -.-> DB
```

## Notes on the diagram

- **Filter → `exceptions_log` branch**: both filters write the rejected-message row themselves
  (opening their own JDBC connection inside the JavaScript rule), independent of the destination
  connector. A logging failure is caught and does not change the reject decision — rejection always
  wins ("fail closed"). See `docs/interface-specification.md` §8.
- **Filter → transformer → destination path**: only runs for messages the filter accepts. The
  destination connector in both channels has its own (currently empty) filter/transformer slots —
  all accept/reject logic lives in the *source* filter, not the destination.
- **ACK timing**: because `respondAfterProcessing = true` on both source connectors, the sender
  does not get its ACK until Mirth has finished the full pipeline for that message — for an accepted
  message, that means waiting for the SQLite insert(s) to finish; for a rejected message, it means
  waiting for the `exceptions_log` insert to finish. The ACK *code* (`AA` vs `AR`) is decided purely
  by the filter step, not by whether the destination write itself succeeds — there is no observed
  path in this project that produces `AE` (see Known Limitations in
  `docs/interface-specification.md`).
- **No cross-channel linkage**: `ADT_Inbound` and `ORU_Inbound` write to the same SQLite file but
  never to each other — there is no connector or script that causes one channel's destination write
  to trigger the other. The shared `SQLite: sql/mirth.db` node above represents the common storage
  target, not a data-flow link between the two channels.
