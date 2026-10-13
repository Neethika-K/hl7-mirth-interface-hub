#!/usr/bin/env python3
"""Generate synthetic HL7 v2.5 ADT and ORU^R01 messages, plus deliberately
malformed messages, for use as Mirth Connect channel test data.

Standard library only. Fully fake/synthetic patient data - not real PHI.
"""

import os
import random
import string

random.seed(42)  # reproducible output across runs

SEG_SEP = "\r"
FIELD_SEP = "|"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALID_DIR = os.path.join(BASE_DIR, "sample-messages", "valid")
MALFORMED_DIR = os.path.join(BASE_DIR, "sample-messages", "malformed")

FIRST_NAMES = [
    "JAMES", "MARY", "ROBERT", "PATRICIA", "JOHN", "JENNIFER", "MICHAEL",
    "LINDA", "WILLIAM", "ELIZABETH", "DAVID", "BARBARA", "RICHARD", "SUSAN",
    "JOSEPH", "JESSICA", "THOMAS", "SARAH", "CHARLES", "KAREN",
]
LAST_NAMES = [
    "SMITH", "JOHNSON", "WILLIAMS", "BROWN", "JONES", "GARCIA", "MILLER",
    "DAVIS", "RODRIGUEZ", "MARTINEZ", "HERNANDEZ", "LOPEZ", "GONZALEZ",
    "WILSON", "ANDERSON", "THOMAS", "TAYLOR", "MOORE", "JACKSON", "MARTIN",
]
STREETS = [
    "100 MAIN ST", "200 OAK AVE", "300 ELM ST", "400 MAPLE DR",
    "500 CEDAR LN", "600 PINE ST", "700 BIRCH RD", "800 WALNUT AVE",
]
CITIES = [
    ("FAKETOWN", "NY", "10001"), ("SAMPLEVILLE", "CA", "90001"),
    ("TESTBURG", "TX", "73301"), ("DEMOPOLIS", "IL", "60601"),
    ("MOCKHAVEN", "OH", "43001"), ("SYNTHCITY", "FL", "33101"),
]
ATTENDING_DOCS = [
    ("ADAMS", "LISA"), ("BAKER", "MARK"), ("CARTER", "NINA"),
    ("DIAZ", "OMAR"), ("EVANS", "RUTH"), ("FOSTER", "TOM"),
]
FACILITIES = ["FAKEHOSP", "FAKEHOSP"]
SENDING_APP = "SYNTH_REG"
SENDING_FAC = "FAKEHOSP"
RECEIVING_APP = "MIRTH"
RECEIVING_FAC = "FAKEHOSP"

LOINC_PANEL = [
    ("2345-7", "Glucose", "mg/dL", "70-99", (60, 220)),
    ("718-7", "Hemoglobin", "g/dL", "12.0-16.0", (8, 18)),
    ("2160-0", "Creatinine", "mg/dL", "0.6-1.3", (4, 20)),  # x/10 applied below
    ("6690-2", "Leukocytes", "10*3/uL", "4.5-11.0", (20, 180)),  # x/10 applied below
]


def next_control_id(counter):
    return "MSG{:05d}".format(counter)


def rand_mrn(counter):
    return "MRN{:06d}".format(100000 + counter)


def rand_acct(counter):
    return "ACC{:06d}".format(200000 + counter)


def rand_date(start_year=1940, end_year=2005):
    year = random.randint(start_year, end_year)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return "{:04d}{:02d}{:02d}".format(year, month, day)


def rand_datetime(year=2026):
    month = random.randint(1, 10)
    day = random.randint(1, 28)
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return "{:04d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(
        year, month, day, hour, minute, second
    )


def make_patient(counter):
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    gender = random.choice(["M", "F"])
    dob = rand_date()
    street = random.choice(STREETS)
    city, state, zip_code = random.choice(CITIES)
    phone = "555{:07d}".format(random.randint(1000000, 9999999))
    ssn = "{:03d}-{:02d}-{:04d}".format(
        random.randint(100, 899), random.randint(10, 99), random.randint(1000, 9999)
    )
    return {
        "mrn": rand_mrn(counter),
        "acct": rand_acct(counter),
        "first": first,
        "last": last,
        "middle": random.choice(string.ascii_uppercase),
        "gender": gender,
        "dob": dob,
        "street": street,
        "city": city,
        "state": state,
        "zip": zip_code,
        "phone": phone,
        "ssn": ssn,
    }


def build_msh(message_type, control_id, timestamp):
    return FIELD_SEP.join([
        "MSH",
        "^~\\&",
        SENDING_APP,
        SENDING_FAC,
        RECEIVING_APP,
        RECEIVING_FAC,
        timestamp,
        "",
        message_type,
        control_id,
        "P",
        "2.5",
    ])


def build_evn(event_type, timestamp):
    return FIELD_SEP.join(["EVN", event_type, timestamp])


def build_pid(p):
    name = "{}^{}^{}".format(p["last"], p["first"], p["middle"])
    address = "{}^^{}^{}^{}".format(p["street"], p["city"], p["state"], p["zip"])
    return FIELD_SEP.join([
        "PID",
        "1",
        "",
        "{}^^^FAKEHOSP^MR".format(p["mrn"]),
        "",
        name,
        "",
        p["dob"],
        p["gender"],
        "",
        "",
        address,
        "",
        p["phone"],
        "",
        "",
        "",
        "",
        p["acct"],
        p["ssn"],
    ])


def build_pv1(p, patient_class, timestamp, discharge_ts=None):
    doc_last, doc_first = random.choice(ATTENDING_DOCS)
    attending = "{}^{}^{}".format(
        "DOC{:03d}".format(random.randint(1, 50)), doc_last, doc_first
    )
    # PV1-1..3, three blanks (PV1-4..6), attending (PV1-7), blanks for
    # PV1-8..43, then admit date/time (PV1-44) and, for discharges,
    # discharge date/time (PV1-45) -- matching HL7 v2.5 field numbering.
    fields = [
        "PV1",
        "1",
        patient_class,
        "FAKEUNIT^{}^A".format(random.randint(100, 499)),
        "",
        "",
        "",
        attending,
    ] + [""] * 36 + [timestamp]
    if discharge_ts:
        fields.append(discharge_ts)
    return FIELD_SEP.join(fields)


def build_adt(msg_type, counter):
    """msg_type is one of 'A01', 'A03', 'A08'."""
    p = make_patient(counter)
    ts = rand_datetime()
    control_id = next_control_id(counter)
    segments = [
        build_msh("ADT^{}".format(msg_type), control_id, ts),
        build_evn(msg_type, ts),
        build_pid(p),
    ]
    if msg_type == "A01":  # admit
        segments.append(build_pv1(p, "I", ts))
    elif msg_type == "A03":  # discharge
        discharge_ts = rand_datetime()
        segments.append(build_pv1(p, "I", ts, discharge_ts=discharge_ts))
    elif msg_type == "A08":  # update
        segments.append(build_pv1(p, random.choice(["I", "O"]), ts))
    return SEG_SEP.join(segments) + SEG_SEP


def build_obx(seq, loinc):
    code, name, units, ref_range, value_range = loinc
    raw = random.randint(*value_range)
    if code in ("2160-0", "6690-2"):
        value = "{:.1f}".format(raw / 10.0)
    else:
        value = str(raw)
    return FIELD_SEP.join([
        "OBX",
        str(seq),
        "NM",
        "{}^{}^LN".format(code, name),
        "",
        value,
        units,
        ref_range,
        "N",
        "",
        "",
        "F",
    ])


def build_oru(counter):
    p = make_patient(counter)
    ts = rand_datetime()
    control_id = next_control_id(counter)
    doc_last, doc_first = random.choice(ATTENDING_DOCS)
    ordering_doc = "{}^{}^{}".format(
        "DOC{:03d}".format(random.randint(1, 50)), doc_last, doc_first
    )
    segments = [
        build_msh("ORU^R01", control_id, ts),
        build_pid(p),
        build_pv1(p, "O", ts),
        FIELD_SEP.join([
            "OBR", "1", "ORD{:06d}^LAB".format(counter), "RES{:06d}^LAB".format(counter),
            "CBC^COMPLETE BLOOD COUNT PANEL^L", "", ts, ts, "", "", "", "", "", "", "", "",
            ordering_doc, "", "", "", "", "", "", "", "", "F",
        ]),
    ]
    num_obx = random.randint(2, 4)
    chosen = random.sample(LOINC_PANEL, num_obx)
    for i, loinc in enumerate(chosen, start=1):
        segments.append(build_obx(i, loinc))
    return SEG_SEP.join(segments) + SEG_SEP


def write_message(directory, filename, content):
    path = os.path.join(directory, filename)
    with open(path, "w", newline="") as f:
        f.write(content)
    return path


def generate_adt_messages():
    types = (["A01"] * 6) + (["A03"] * 6) + (["A08"] * 6)
    random.shuffle(types)
    for i, msg_type in enumerate(types, start=1):
        content = build_adt(msg_type, i)
        filename = "ADT_{}_{:03d}.hl7".format(msg_type, i)
        write_message(VALID_DIR, filename, content)
    print("Wrote 18 ADT messages to {}".format(VALID_DIR))


def generate_oru_messages():
    for i in range(1, 19):
        content = build_oru(1000 + i)
        filename = "ORU_R01_{:03d}.hl7".format(i)
        write_message(VALID_DIR, filename, content)
    print("Wrote 18 ORU^R01 messages to {}".format(VALID_DIR))


def generate_malformed_messages():
    notes = []

    # 1. Missing PID segment
    p = make_patient(9001)
    ts = rand_datetime()
    content = SEG_SEP.join([
        build_msh("ADT^A01", "MSGBAD01", ts),
        build_evn("A01", ts),
        build_pv1(p, "I", ts),
    ]) + SEG_SEP
    write_message(MALFORMED_DIR, "01_missing_pid.hl7", content)
    notes.append(("01_missing_pid.hl7", "ADT^A01 message has no PID segment at all. "
                  "A compliant parser needs PID to identify the patient; this simulates "
                  "a registration feed dropping the segment mid-transmission."))

    # 2. Broken MSH segment (wrong encoding characters / missing fields)
    p = make_patient(9002)
    ts = rand_datetime()
    bad_msh = "MSH|^~\\&" + FIELD_SEP + SENDING_APP  # truncated, missing encoding char and fields
    content = SEG_SEP.join([
        bad_msh,
        build_pid(p),
        build_pv1(p, "I", ts),
    ]) + SEG_SEP
    write_message(MALFORMED_DIR, "02_broken_msh.hl7", content)
    notes.append(("02_broken_msh.hl7", "MSH segment is truncated: the encoding "
                  "characters field is malformed (\"^~\\&\" is cut short and the pipe "
                  "placement is wrong) and required fields (receiving app/facility, "
                  "timestamp, message type, control ID, version) are missing entirely."))

    # 3. Bad date format in PID (DOB) and MSH (timestamp)
    p = make_patient(9003)
    bad_ts = "10/06/2026 12:00pm"  # not HL7 TS format (should be YYYYMMDDHHMMSS)
    pid_bad = build_pid(p).replace(p["dob"], "13/45/2026")  # invalid month/day too
    content = SEG_SEP.join([
        build_msh("ADT^A08", "MSGBAD03", bad_ts),
        build_evn("A08", bad_ts),
        pid_bad,
        build_pv1(p, "I", bad_ts),
    ]) + SEG_SEP
    write_message(MALFORMED_DIR, "03_bad_date_format.hl7", content)
    notes.append(("03_bad_date_format.hl7", "MSH-7 (message timestamp) uses "
                  "\"10/06/2026 12:00pm\" instead of HL7 TS format YYYYMMDDHHMMSS, and "
                  "PID-7 (date of birth) uses an invalid \"13/45/2026\" (month 13, day 45 "
                  "do not exist)."))

    # 4. Missing OBX value (OBX-5 empty) in an ORU message
    p = make_patient(9004)
    ts = rand_datetime()
    doc_last, doc_first = random.choice(ATTENDING_DOCS)
    ordering_doc = "{}^{}^{}".format("DOC099", doc_last, doc_first)
    obx_no_value = FIELD_SEP.join([
        "OBX", "1", "NM", "2345-7^Glucose^LN", "", "", "mg/dL", "70-99", "N", "", "", "F",
    ])
    content = SEG_SEP.join([
        build_msh("ORU^R01", "MSGBAD04", ts),
        build_pid(p),
        build_pv1(p, "O", ts),
        FIELD_SEP.join([
            "OBR", "1", "ORD009004^LAB", "RES009004^LAB",
            "CBC^COMPLETE BLOOD COUNT PANEL^L", "", ts, ts, "", "", "", "", "", "", "", "",
            ordering_doc, "", "", "", "", "", "", "", "", "F",
        ]),
        obx_no_value,
    ]) + SEG_SEP
    write_message(MALFORMED_DIR, "04_missing_obx_value.hl7", content)
    notes.append(("04_missing_obx_value.hl7", "The single OBX segment has an empty "
                  "OBX-5 (observation value) field -- the result code, units, and "
                  "reference range are present but the actual lab value was dropped."))

    # 5. Missing PV1 segment in an ADT message
    p = make_patient(9005)
    ts = rand_datetime()
    content = SEG_SEP.join([
        build_msh("ADT^A01", "MSGBAD05", ts),
        build_evn("A01", ts),
        build_pid(p),
    ]) + SEG_SEP
    write_message(MALFORMED_DIR, "05_missing_pv1.hl7", content)
    notes.append(("05_missing_pv1.hl7", "ADT^A01 message has no PV1 segment, so there "
                  "is no patient class, location, or attending doctor -- required "
                  "visit information for an admit event is absent."))

    # 6. Empty message
    write_message(MALFORMED_DIR, "06_empty_message.hl7", "")
    notes.append(("06_empty_message.hl7", "The file is completely empty (0 bytes) -- "
                  "simulates a zero-length payload reaching the listener, e.g. from a "
                  "network glitch or an upstream system sending a keep-alive with no "
                  "actual HL7 content."))

    readme_lines = [
        "# Malformed HL7 Sample Messages",
        "",
        "These files are intentionally invalid HL7 v2.5 messages, generated for testing",
        "Mirth Connect channel error handling, filters, and the `exceptions_log` table.",
        "",
    ]
    for filename, desc in notes:
        readme_lines.append("## {}".format(filename))
        readme_lines.append("")
        readme_lines.append(desc)
        readme_lines.append("")
    readme_path = os.path.join(MALFORMED_DIR, "README.md")
    with open(readme_path, "w") as f:
        f.write("\n".join(readme_lines))

    print("Wrote 6 malformed messages and README.md to {}".format(MALFORMED_DIR))


def main():
    os.makedirs(VALID_DIR, exist_ok=True)
    os.makedirs(MALFORMED_DIR, exist_ok=True)
    generate_adt_messages()
    generate_oru_messages()
    generate_malformed_messages()


if __name__ == "__main__":
    main()
