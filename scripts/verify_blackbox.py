#!/usr/bin/env python3
"""
Verify CLI (correct key): Read commitments + carrier, recover + verify message.

Authenticated decryption via ChaCha20-Poly1305: any tampering → REJECT.
Reed-Solomon ECC for transport robustness (never decides acceptance).
AEAD is the sole authority for acceptance (covenant enforced).
"""

import sys
import json
import base64
import hashlib
import zlib
from geophase.codec import decrypt, ecc_decode, NONCE_LEN, TAG_LEN, NSYM
from geophase.util import unpermute
from geophase.covenant import verify_gate

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
    msg_len = int(req["msg_len"])
    carrier = base64.b64decode(req["carrier_b64"])
    compressed_struct = base64.b64decode(req["compressed_struct_b64"])
    
    # Calculate codeword length from msg_len
    # CT = nonce (12) + plaintext + tag (16)
    ct_len = NONCE_LEN + msg_len + TAG_LEN
    # Codeword = CT + RS parity (NSYM bytes)
    cw_len = ct_len + NSYM

    try:
        D = zlib.decompress(compressed_struct)
    except Exception:
        print(json.dumps({"status": "REJECT"}, separators=(",", ":")))
        return

    H_prev = H(b"GENESIS" + t.to_bytes(4, "big"))
    g_t = H(D)

    # Reconstruct public_header with msg_len (as encode did)
    public_header_with_len = dict(public_header)
    public_header_with_len["msg_len"] = msg_len

    A_chk = H(H_prev + g_t + canon(public_header_with_len))

    # --- Extract and decode ECC codeword from carrier ---
    cw = carrier[:cw_len]
    
    # Reverse interleaving using same seed as encode
    seed = H_prev + t.to_bytes(8, "big")
    cw = unpermute(cw, seed)
    
    # Decode codeword (ECC corrects errors if possible)
    ct_candidate = ecc_decode(cw)

    # --- Associated data for AEAD verification ---
    associated_data = canon({
        "t": t,
        "public_header": public_header_with_len,
        "H_prev": H_prev.hex(),
    })

    # --- AEAD is the sole acceptance authority (covenant enforced) ---
    # ECC provides best-effort repair only; AEAD decides acceptance
    try:
        msg = decrypt(MASTER_KEY, t, ct_candidate, associated_data)
        aead_pass = True
    except Exception:
        aead_pass = False
        msg = b""

    # Check commitment validity only if AEAD passed
    if aead_pass:
        H_chk = H(H_prev + H(ct_candidate) + g_t)
        if A_chk != A_t or H_chk != H_t:
            out = {"status": "REJECT"}
        else:
            out = {
                "status": "ACCEPT",
                "message_out_b64": base64.b64encode(msg).decode(),
            }
    else:
        out = {"status": "REJECT"}
    print(json.dumps(out, separators=(",", ":")))


if __name__ == "__main__":
    main()
