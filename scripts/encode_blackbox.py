#!/usr/bin/env python3
"""
Encode CLI: Read structured state + message, output carrier + commitments.

Payload confidentiality and integrity provided by ChaCha20-Poly1305.
Transport robustness provided by Reed-Solomon ECC + interleaving.
Length framing ensures verifier knows exact ciphertext size.
"""

import sys
import json
import base64
import hashlib
import zlib
import os
from geophase.codec import encrypt, ecc_encode, NONCE_LEN, TAG_LEN, NSYM
from geophase.util import permute

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

    # --- Record message length in public header (safe, not secret) ---
    public_header_with_len = dict(public_header)
    public_header_with_len["msg_len"] = len(msg)

    # --- structured compression (placeholder: zlib on canonical json) ---
    D = canon(structured_state)
    compressed_struct = zlib.compress(D, level=9)

    # --- commitments (toy reference, NOT your real secret sauce) ---
    # NOTE: In a real build, H_{t-1} would be stored/loaded. For harness, keep deterministic per t.
    H_prev = H(b"GENESIS" + t.to_bytes(4, "big"))
    g_t = H(D)

    A_t = H(H_prev + g_t + canon(public_header_with_len))

    # --- ChaCha20-Poly1305 authenticated encryption ---
    # AD includes all public data to prevent tampering
    associated_data = canon({
        "t": t,
        "public_header": public_header_with_len,
        "H_prev": H_prev.hex(),
    })
    # Use deterministic nonce for test harness (T1 reproducibility)
    ct = encrypt(MASTER_KEY, t, msg, associated_data, deterministic=True)

    H_t = H(H_prev + H(ct) + g_t)

    # --- ECC encoding + interleaving (transport layer) ---
    # CT format: nonce (12) || ciphertext || tag (16)
    # CT length is deterministic: NONCE_LEN + len(msg) + TAG_LEN
    codeword = ecc_encode(ct)  # ct || parity (NSYM bytes)
    
    # Interleave codeword using deterministic seed from H_prev and t
    seed = H_prev + t.to_bytes(8, "big")
    codeword_interleaved = permute(codeword, seed)

    # --- carrier: interleaved codeword + deterministic padding (1024 total) ---
    # For determinism (T1), pad with SHA256 chain instead of random
    padding_seed = H(H_prev + t.to_bytes(8, "big") + len(codeword_interleaved).to_bytes(4, "big"))
    padding_len = max(0, 1024 - len(codeword_interleaved))
    padding = b""
    pad_hash = padding_seed
    while len(padding) < padding_len:
        padding += pad_hash
        pad_hash = H(pad_hash)
    carrier = codeword_interleaved + padding[:padding_len]

    out = {
        "H_t": H_t.hex(),
        "A_t": A_t.hex(),
        "msg_len": len(msg),  # Echo length so verifier knows codeword size
        "carrier_b64": base64.b64encode(carrier).decode(),
        "compressed_struct_b64": base64.b64encode(compressed_struct).decode(),
        "public_header": public_header,
    }
    print(json.dumps(out, separators=(",", ":")))


if __name__ == "__main__":
    main()
