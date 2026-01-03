#!/usr/bin/env python3
"""
Verify CLI (correct key): Read commitments + carrier, verify + recover message.

Authenticated decryption via ChaCha20-Poly1305: any tampering → REJECT.
ECC decoding placeholder (TODO: T4).
"""

import sys
import json
import base64
import hashlib
import zlib
from geophase.codec import decrypt

# Master key for public test (must match encode)
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
    H_t = bytes.fromhex(req["H_t"])
    A_t = bytes.fromhex(req["A_t"])
    carrier = base64.b64decode(req["carrier_b64"])
    compressed_struct = base64.b64decode(req["compressed_struct_b64"])
    
    # Extract message length (default 256 for backward compatibility)
    msg_len = int(req.get("msg_len", 256))

    try:
        D = zlib.decompress(compressed_struct)
    except Exception:
        print(json.dumps({"status": "REJECT"}, separators=(",", ":")))
        return

    H_prev = H(b"GENESIS" + t.to_bytes(4, "big"))
    g_t = H(D)

    A_chk = H(H_prev + g_t + canon(public_header))

    # Extract ciphertext from carrier
    # Format: nonce (12) || ct || tag (16)
    # Total AEAD output length = plaintext_len + 16 (for tag)
    # For variable msg_len: AEAD ct = nonce + (plaintext + tag)
    ct = carrier[:msg_len + 28]  # 12 (nonce) + msg_len + 16 (tag)

    # Authenticated decryption: any tampering → exception → REJECT
    associated_data = canon({
        "t": t,
        "public_header": public_header,
        "H_prev": H_prev.hex(),
    })

    try:
        msg = decrypt(MASTER_KEY, t, ct, associated_data)
    except Exception:
        # Decryption failed (bad MAC or corrupt ciphertext)
        print(json.dumps({"status": "REJECT"}, separators=(",", ":")))
        return

    H_chk = H(H_prev + H(ct) + g_t)

    if A_chk != A_t or H_chk != H_t:
        out = {"status": "REJECT"}
    else:
        out = {"status": "ACCEPT", "message_out_b64": base64.b64encode(msg).decode()}

    json.dump(out, sys.stdout, separators=(",", ":"))
    print()


if __name__ == "__main__":
    main()
