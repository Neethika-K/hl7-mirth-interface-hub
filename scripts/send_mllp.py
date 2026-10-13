#!/usr/bin/env python3
"""Send HL7 v2.x messages to a Mirth Connect (or any MLLP) listener.

Wraps each message in standard MLLP framing:
    start block: 0x0B
    end block:   0x1C 0x0D

Accepts a single .hl7 file or a directory of .hl7 files. If --port is not
given, the port is chosen per message based on its HL7 message type
(MSH-9): ADT messages default to 6661, ORU messages default to 6662.

Standard library only.
"""

import argparse
import glob
import os
import socket
import sys

START_BLOCK = b"\x0b"
END_BLOCK = b"\x1c\x0d"

DEFAULT_PORTS = {
    "ADT": 6661,
    "ORU": 6662,
}
FALLBACK_PORT = 6661
SOCKET_TIMEOUT_SECONDS = 10


def collect_files(path):
    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, "*.hl7")))
        if not files:
            raise SystemExit("No .hl7 files found in directory: {}".format(path))
        return files
    if os.path.isfile(path):
        return [path]
    raise SystemExit("Path not found: {}".format(path))


def read_message(filepath):
    with open(filepath, "r", newline="") as f:
        content = f.read()
    # Normalize segment terminators to \r regardless of how the file was saved
    content = content.replace("\r\n", "\r").replace("\n", "\r")
    return content


def detect_message_category(message):
    """Look at MSH-9 to decide ADT vs ORU; returns None if undetermined."""
    first_segment = message.split("\r", 1)[0] if message else ""
    fields = first_segment.split("|")
    if len(fields) > 8 and fields[0] == "MSH":
        msg_type = fields[8].split("^")[0].strip().upper()
        if msg_type in DEFAULT_PORTS:
            return msg_type
    return None


def pick_port(message, explicit_port):
    if explicit_port is not None:
        return explicit_port
    category = detect_message_category(message)
    if category is None:
        return FALLBACK_PORT
    return DEFAULT_PORTS[category]


def wrap_mllp(message):
    return START_BLOCK + message.encode("utf-8") + END_BLOCK


def unwrap_mllp(data):
    payload = data
    if payload.startswith(START_BLOCK):
        payload = payload[1:]
    if payload.endswith(END_BLOCK):
        payload = payload[: -len(END_BLOCK)]
    return payload.decode("utf-8", errors="replace")


def send_message(host, port, message, timeout=SOCKET_TIMEOUT_SECONDS):
    framed = wrap_mllp(message)
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(framed)
        sock.settimeout(timeout)
        chunks = []
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
                if chunk.endswith(END_BLOCK):
                    break
        except socket.timeout:
            pass
    return unwrap_mllp(b"".join(chunks)) if chunks else ""


def main():
    parser = argparse.ArgumentParser(
        description="Send HL7 message(s) to an MLLP listener and print the ACK."
    )
    parser.add_argument("path", help="Path to a .hl7 file or a directory of .hl7 files")
    parser.add_argument("--host", default="127.0.0.1", help="Target host (default 127.0.0.1)")
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Target port. If omitted, inferred per message: ADT->6661, ORU->6662",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=SOCKET_TIMEOUT_SECONDS,
        help="Socket timeout in seconds (default 10)",
    )
    args = parser.parse_args()

    files = collect_files(args.path)
    exit_code = 0

    for filepath in files:
        message = read_message(filepath)
        if not message.strip():
            print("{}: SKIPPED (empty message)".format(os.path.basename(filepath)))
            continue
        port = pick_port(message, args.port)
        try:
            ack = send_message(args.host, port, message, timeout=args.timeout)
        except (socket.timeout, ConnectionRefusedError, OSError) as exc:
            print(
                "{}: FAILED to send to {}:{} ({})".format(
                    os.path.basename(filepath), args.host, port, exc
                )
            )
            exit_code = 1
            continue

        print("=== {} -> {}:{} ===".format(os.path.basename(filepath), args.host, port))
        if ack:
            print(ack.replace("\r", "\n"))
        else:
            print("(no ACK received before timeout)")
        print()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
