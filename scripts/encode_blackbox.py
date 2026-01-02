#!/usr/bin/env python3
"""
Encode CLI: Read structured state + message, output carrier + commitments.
"""

import sys
import json
import base64
import hashlib
import zlib


def H(b: bytes) -> bytes:
    """SHA-256 hash."""
    return hashlib.sha256(b).digest()


def canon(obj) -> bytes:
    """Canonical JSON (sorted keys, minimal spacing)."""
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode()


def main():
    req = json.load(sys.stdin)
    t = int(req["t"])
    public_header = req["public_header"]
    structured_state = req["structured_state"]
    msg = base64.b64decode(req["message_b64"])

    # --- structured compression (placeholder: zlib on canonical json) ---
    D = canon(structured_state)
    compressed_struct = zlib.compress(D, level=9)

    # --- commitments (toy reference, NOT your real secret sauce) ---
    # NOTE: In a real build, H_{t-1} would be stored/loaded. For harness, keep deterministic per t.
    H_prev = H(b"GENESIS" + t.to_bytes(4, "big"))
    g_t = H(D)

    A_t = H(H_prev + g_t + canon(public_header))

    # ciphertext placeholder: in toy mode, ct = msg (no encryption)
    # Replace with real AEAD in production.
    ct = msg

    H_t = H(H_prev + H(ct) + g_t)

    # --- carrier placeholder: ct padded with deterministic bytes (for T1 determinism) ---
    # In real build, replace with ECC+carrier
    padding = H(b"PADDING" + t.to_bytes(4, "big"))
    # Repeat padding to make up 1024 bytes
    carrier = ct + (padding * (1024 // len(padding) + 1))[:1024]

    out = {
        "H_t": H_t.hex(),
        "A_t": A_t.hex(),
        "carrier_b64": base64.b64encode(carrier).decode(),
        "compressed_struct_b64": base64.b64encode(compressed_struct).decode(),
        "meta": {
            # Optional: include ct for Shannon-Karen if you want (safe-ish in toy mode only).
            # Remove in any real build.
            "ct_b64": base64.b64encode(ct).decode(),
        },
    }
    json.dump(out, sys.stdout, separators=(",", ":"))
    print()


if __name__ == "__main__":
    main()
