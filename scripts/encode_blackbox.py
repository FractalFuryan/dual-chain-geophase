#!/usr/bin/env python3
"""
Encode CLI: Read structured state + message, output carrier + commitments.

Payload confidentiality and integrity provided by ChaCha20-Poly1305.
Robustness to channel noise delegated to ECC (TODO: T4).
"""

import sys
import json
import base64
import hashlib
import zlib
from geophase.codec import encrypt

# Master key for public test (safe, no secrets)
MASTER_KEY = b"PUBLIC_TEST_MASTER_KEY_256_BITS!"


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

    # --- ChaCha20-Poly1305 authenticated encryption ---
    # AD includes all public data to prevent tampering
    associated_data = canon({
        "t": t,
        "public_header": public_header,
        "H_prev": H_prev.hex(),
    })
    # Use deterministic nonce for test harness (T1 reproducibility)
    ct = encrypt(MASTER_KEY, t, msg, associated_data, deterministic=True)

    H_t = H(H_prev + H(ct) + g_t)

    # --- carrier: ciphertext padded with random bytes (ECC comes in T4) ---
    # Ciphertext format: nonce (12) || ct || tag (16)
    # Carrier extends to 1024 bytes for robustness testing
    carrier = ct + (b"\x00" * (1024 - len(ct)))  # Zero-pad for now; ECC will replace

    out = {
        "H_t": H_t.hex(),
        "A_t": A_t.hex(),
        "carrier_b64": base64.b64encode(carrier).decode(),
        "compressed_struct_b64": base64.b64encode(compressed_struct).decode(),
    }
    json.dump(out, sys.stdout, separators=(",", ":"))
    print()


if __name__ == "__main__":
    main()
