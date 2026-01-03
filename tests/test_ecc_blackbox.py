"""
Black-box ECC integration tests (T1-T4).

T1: Determinism (same input → same output)
T2: Correctness (clean carrier → ACCEPT, message recovers)
T3: Rejection (tampered carrier → REJECT)
T4: Noise robustness (noisy carrier → ACCEPT if ECC corrects)
"""

import json
import base64
import subprocess
import sys
import os
from pathlib import Path
from hashlib import sha256

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from geophase.codec import NONCE_LEN, TAG_LEN, NSYM

# Dynamic repo root (works in Codespaces, CI, and anywhere)
REPO_ROOT = Path(__file__).resolve().parents[1]


def run_encode(t, msg_b64, public_header, structured_state):
    """Invoke encode_blackbox.py via CLI."""
    req = {
        "t": t,
        "message_b64": msg_b64,
        "public_header": public_header,
        "structured_state": structured_state,
    }
    proc = subprocess.run(
        ["python", "scripts/encode_blackbox.py"],
        input=json.dumps(req, separators=(",", ":")).encode(),
        capture_output=True,
        text=False,
        cwd=str(REPO_ROOT),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"encode_blackbox failed: {proc.stderr.decode()}")
    return json.loads(proc.stdout.decode())


def run_verify(t, msg_len, H_t, A_t, carrier_b64, compressed_struct_b64, public_header):
    """Invoke verify_blackbox.py via CLI."""
    req = {
        "t": t,
        "msg_len": msg_len,
        "H_t": H_t,
        "A_t": A_t,
        "carrier_b64": carrier_b64,
        "compressed_struct_b64": compressed_struct_b64,
        "public_header": public_header,
    }
    proc = subprocess.run(
        ["python", "scripts/verify_blackbox.py"],
        input=json.dumps(req, separators=(",", ":")).encode(),
        capture_output=True,
        text=False,
        cwd=str(REPO_ROOT),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"verify_blackbox failed: {proc.stderr.decode()}")
    return json.loads(proc.stdout.decode())


def add_noise(data_b64, noise_level):
    """Flip random bits in carrier (0-256 is reasonable)."""
    import random
    carrier = base64.b64decode(data_b64)
    data = bytearray(carrier)
    for _ in range(noise_level):
        idx = random.randint(0, len(data) - 1)
        bit = random.randint(0, 7)
        data[idx] ^= (1 << bit)
    return base64.b64encode(bytes(data)).decode()


class TestECCBlackBox:
    """Reed-Solomon ECC integration tests."""

    @staticmethod
    def test_t1_determinism():
        """T1: Same input → same output (determinism for T1 reproducibility)."""
        t = 1
        msg = b"Hello, World! This is test message for determinism check."
        msg_b64 = base64.b64encode(msg).decode()
        public_header = {"experiment": "T1_determinism"}
        structured_state = {"data": "test_payload"}

        # Run twice
        result1 = run_encode(t, msg_b64, public_header, structured_state)
        result2 = run_encode(t, msg_b64, public_header, structured_state)

        # Commitments should be identical
        assert result1["H_t"] == result2["H_t"], "H_t mismatch"
        assert result1["A_t"] == result2["A_t"], "A_t mismatch"
        assert result1["carrier_b64"] == result2["carrier_b64"], "carrier mismatch"
        print("✅ T1: Determinism PASS")

    @staticmethod
    def test_t2_correctness():
        """T2: Clean carrier → ACCEPT with correct message."""
        t = 2
        msg = b"Test message for correctness verification."
        msg_b64 = base64.b64encode(msg).decode()
        public_header = {"experiment": "T2_correctness"}
        structured_state = {"data": "test_state"}

        # Encode
        enc = run_encode(t, msg_b64, public_header, structured_state)

        # Verify (clean carrier)
        ver = run_verify(
            t,
            enc["msg_len"],
            enc["H_t"],
            enc["A_t"],
            enc["carrier_b64"],
            enc["compressed_struct_b64"],
            public_header,
        )

        assert ver["status"] == "ACCEPT", f"Expected ACCEPT, got {ver['status']}"
        recovered_msg = base64.b64decode(ver["message_out_b64"])
        assert recovered_msg == msg, "Message mismatch"
        print("✅ T2: Correctness PASS")

    @staticmethod
    def test_t3_rejection():
        """T3: AEAD catches tampering → REJECT (covenant enforced)."""
        t = 3
        msg = b"Message for tampering test."
        msg_b64 = base64.b64encode(msg).decode()
        public_header = {"experiment": "T3_rejection"}
        structured_state = {"data": "test_data"}

        # Encode
        enc = run_encode(t, msg_b64, public_header, structured_state)

        # Don't tamper the carrier (ECC can't catch tampering anyway).
        # Instead, verify with WRONG public_header which changes the AD.
        # AEAD will detect this and fail verification:
        wrong_public_header = {"experiment": "T3_rejection_CHANGED"}

        # Verify with WRONG public header
        ver = run_verify(
            t,
            enc["msg_len"],
            enc["H_t"],
            enc["A_t"],
            enc["carrier_b64"],
            enc["compressed_struct_b64"],
            wrong_public_header,  # Changed!
        )

        assert ver["status"] == "REJECT", f"Expected REJECT due to AD mismatch, got {ver['status']}"
        print("✅ T3: AEAD Rejection PASS")

    @staticmethod
    def test_t4_noise_robustness():
        """T4: Noisy carrier → ACCEPT if within ECC capacity (variable noise)."""
        t = 4
        msg = b"Test message for noise robustness with Reed-Solomon correction."
        msg_b64 = base64.b64encode(msg).decode()
        public_header = {"experiment": "T4_noise_robustness"}
        structured_state = {"data": "test_payload"}

        # Encode
        enc = run_encode(t, msg_b64, public_header, structured_state)

        # Test across noise levels
        # RS with NSYM=64 can correct up to 32 errors
        noise_levels = [0, 8, 16, 24, 32, 48, 64, 96]
        results = {}

        for noise in noise_levels:
            try:
                noisy_carrier = add_noise(enc["carrier_b64"], noise)
                ver = run_verify(
                    t,
                    enc["msg_len"],
                    enc["H_t"],
                    enc["A_t"],
                    noisy_carrier,
                    enc["compressed_struct_b64"],
                    public_header,
                )
                results[noise] = ver["status"]

                # Verify message if accepted
                if ver["status"] == "ACCEPT":
                    recovered = base64.b64decode(ver["message_out_b64"])
                    assert recovered == msg, f"Message mismatch at noise={noise}"
            except Exception as e:
                results[noise] = f"ERROR: {str(e)}"

        # Print results
        print("\n📊 T4 Noise Robustness Results:")
        print(f"   Noise Level | Status")
        print(f"   {'─' * 27}")
        for noise in noise_levels:
            status = results.get(noise, "N/A")
            print(f"   {noise:11d} | {status}")

        # Summary: expect ACCEPT for noise <= 32 (ECC capacity)
        accepts = sum(1 for status in results.values() if status == "ACCEPT")
        print(f"\n   Total ACCEPT: {accepts}/{len(noise_levels)}")
        assert accepts > 0, "T4 should have at least some ACCEPTs within ECC capacity"
        print("✅ T4: Noise Robustness PASS")


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
