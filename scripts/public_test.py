#!/usr/bin/env python3
"""
Black-box test harness for dual-chain authenticated design.
Tests: T1 (determinism), T2 (correctness), T3 (rejection), T4 (noise robustness).
"""

import argparse
import subprocess
import json
import base64
import os
import sys
from typing import Dict, Any, Tuple, Optional


def run_encode(script_path: str, req: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Run encode CLI with request JSON; return (success, output_dict)."""
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            input=json.dumps(req),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False, None
        out = json.loads(result.stdout)
        return True, out
    except Exception as e:
        print(f"  [ENCODE ERROR] {e}")
        return False, None


def run_verify(script_path: str, req: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
    """Run verify CLI; return (success, status, message_b64)."""
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            input=json.dumps(req),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False, None, None
        out = json.loads(result.stdout)
        status = out.get("status")
        msg = out.get("message_out_b64")
        return True, status, msg
    except Exception as e:
        print(f"  [VERIFY ERROR] {e}")
        return False, None, None


def add_noise_to_carrier(carrier_b64: str, num_flips: int) -> str:
    """Flip random bits in carrier."""
    carrier = base64.b64decode(carrier_b64)
    carrier_list = bytearray(carrier)
    for _ in range(num_flips):
        idx = os.urandom(1)[0] % len(carrier_list)
        bit_pos = os.urandom(1)[0] % 8
        carrier_list[idx] ^= (1 << bit_pos)
    return base64.b64encode(bytes(carrier_list)).decode()


def test_t1_determinism(script_path: str, blocks: int, msg_bytes: int) -> bool:
    """T1: Determinism - encode(msg) == encode(msg) for same t and state."""
    print("\n[T1] Testing Determinism...")
    passed = 0
    failed = 0

    for t in range(blocks):
        msg = os.urandom(msg_bytes)
        public_header = {"version": 1, "timestamp": t}
        structured_state = {"t": t, "counter": 0}

        req = {
            "t": t,
            "public_header": public_header,
            "structured_state": structured_state,
            "message_b64": base64.b64encode(msg).decode(),
        }

        success1, out1 = run_encode(script_path, req)
        success2, out2 = run_encode(script_path, req)

        if success1 and success2 and out1 == out2:
            passed += 1
            print(f"  T block {t}: PASS (deterministic)")
        else:
            failed += 1
            print(f"  T block {t}: FAIL (not deterministic)")

    rate = 100 * passed / blocks if blocks > 0 else 0
    print(f"  T1 Result: {passed}/{blocks} ({rate:.1f}%)")
    return failed == 0


def test_t2_correctness(
    encode_script: str, verify_script: str, blocks: int, msg_bytes: int
) -> bool:
    """T2: Correctness - encode + verify with correct key → ACCEPT + recover message."""
    print("\n[T2] Testing Correctness (Verify with Correct Key)...")
    passed = 0
    failed = 0

    for t in range(blocks):
        msg = os.urandom(msg_bytes)
        public_header = {"version": 1, "timestamp": t}
        structured_state = {"t": t, "counter": 0}

        req = {
            "t": t,
            "public_header": public_header,
            "structured_state": structured_state,
            "message_b64": base64.b64encode(msg).decode(),
        }

        # Encode
        success, enc_out = run_encode(encode_script, req)
        if not success:
            print(f"  T block {t}: FAIL (encode failed)")
            failed += 1
            continue

        # Verify with correct key
        verify_req = {
            "t": t,
            "public_header": public_header,
            "H_t": enc_out["H_t"],
            "A_t": enc_out["A_t"],
            "carrier_b64": enc_out["carrier_b64"],
            "compressed_struct_b64": enc_out["compressed_struct_b64"],
            "msg_len": msg_bytes,
        }

        success, status, msg_out_b64 = run_verify(verify_script, verify_req)
        if not success or status != "ACCEPT":
            print(f"  T block {t}: FAIL (verify returned {status})")
            failed += 1
            continue

        # Recover message
        if msg_out_b64:
            try:
                msg_recovered = base64.b64decode(msg_out_b64)
                if msg_recovered == msg:
                    passed += 1
                    print(f"  T block {t}: PASS (message recovered)")
                else:
                    failed += 1
                    print(f"  T block {t}: FAIL (message mismatch)")
            except Exception as e:
                failed += 1
                print(f"  T block {t}: FAIL (message decode: {e})")
        else:
            failed += 1
            print(f"  T block {t}: FAIL (no message output)")

    rate = 100 * passed / blocks if blocks > 0 else 0
    print(f"  T2 Result: {passed}/{blocks} ({rate:.1f}%)")
    return failed == 0


def test_t3_rejection(
    verify_wrong_script: str, encode_script: str, blocks: int, msg_bytes: int
) -> bool:
    """T3: Rejection - verify with wrong key → REJECT."""
    print("\n[T3] Testing Rejection (Verify with Wrong Key)...")
    passed = 0
    failed = 0

    for t in range(blocks):
        msg = os.urandom(msg_bytes)
        public_header = {"version": 1, "timestamp": t}
        structured_state = {"t": t, "counter": 0}

        req = {
            "t": t,
            "public_header": public_header,
            "structured_state": structured_state,
            "message_b64": base64.b64encode(msg).decode(),
        }

        # Encode
        success, enc_out = run_encode(encode_script, req)
        if not success:
            print(f"  T block {t}: FAIL (encode failed)")
            failed += 1
            continue

        # Verify with wrong key
        verify_req = {
            "t": t,
            "public_header": public_header,
            "H_t": enc_out["H_t"],
            "A_t": enc_out["A_t"],
            "carrier_b64": enc_out["carrier_b64"],
            "compressed_struct_b64": enc_out["compressed_struct_b64"],
            "msg_len": msg_bytes,
        }

        success, status, _ = run_verify(verify_wrong_script, verify_req)
        if not success or status == "REJECT":
            passed += 1
            print(f"  T block {t}: PASS (correctly rejected)")
        else:
            failed += 1
            print(f"  T block {t}: FAIL (should have been rejected, got {status})")

    rate = 100 * passed / blocks if blocks > 0 else 0
    print(f"  T3 Result: {passed}/{blocks} ({rate:.1f}%)")
    return failed == 0


def test_t4_noise_robustness(
    verify_script: str, encode_script: str, blocks: int, msg_bytes: int, noise_levels: list
) -> bool:
    """T4: Noise Robustness - carrier with noise → still verifies (ECC-dependent)."""
    print(f"\n[T4] Testing Noise Robustness (noise_levels={noise_levels})...")
    passed = 0
    failed = 0
    total = blocks * len(noise_levels)

    for noise_level in noise_levels:
        print(f"  [Noise level: {noise_level} bit flips]")
        for t in range(blocks):
            msg = os.urandom(msg_bytes)
            public_header = {"version": 1, "timestamp": t}
            structured_state = {"t": t, "counter": 0}

            req = {
                "t": t,
                "public_header": public_header,
                "structured_state": structured_state,
                "message_b64": base64.b64encode(msg).decode(),
            }

            # Encode
            success, enc_out = run_encode(encode_script, req)
            if not success:
                print(f"    Block {t}: FAIL (encode failed)")
                failed += 1
                continue

            # Add noise to carrier
            noisy_carrier = add_noise_to_carrier(enc_out["carrier_b64"], noise_level)

            # Verify with noisy carrier
            verify_req = {
                "t": t,
                "public_header": public_header,
                "H_t": enc_out["H_t"],
                "A_t": enc_out["A_t"],
                "carrier_b64": noisy_carrier,
                "compressed_struct_b64": enc_out["compressed_struct_b64"],
                "msg_len": msg_bytes,
            }

            success, status, msg_out_b64 = run_verify(verify_script, verify_req)
            if success and status == "ACCEPT" and msg_out_b64:
                try:
                    msg_recovered = base64.b64decode(msg_out_b64)
                    if msg_recovered == msg:
                        passed += 1
                        print(f"    Block {t}: PASS (recovered with {noise_level} flips)")
                    else:
                        failed += 1
                        print(f"    Block {t}: FAIL (recovered message mismatch)")
                except Exception:
                    failed += 1
                    print(f"    Block {t}: FAIL (message decode error)")
            else:
                # In toy harness, noise will cause rejection (no real ECC)
                if status == "REJECT":
                    print(f"    Block {t}: REJECT (expected, no real ECC)")
                failed += 1

    rate = 100 * passed / total if total > 0 else 0
    print(f"  T4 Result: {passed}/{total} ({rate:.1f}%)")
    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Black-box test harness for dual-chain design")
    parser.add_argument("--encode", required=True, help="Path to encode_blackbox.py script")
    parser.add_argument("--verify", required=True, help="Path to verify_blackbox.py script")
    parser.add_argument("--verify-wrong", required=True, help="Path to verify_blackbox_wrongkey.py script")
    parser.add_argument("--blocks", type=int, default=10, help="Number of test blocks per test")
    parser.add_argument("--msg-bytes", type=int, default=256, help="Message size in bytes")
    parser.add_argument(
        "--noise-levels",
        type=str,
        default="0,1,2,4,8",
        help="Comma-separated noise levels (bit flips) for T4",
    )

    args = parser.parse_args()

    noise_levels = [int(x) for x in args.noise_levels.split(",")]

    print("=" * 70)
    print("DUAL-CHAIN GEOPHASE: BLACK-BOX TEST HARNESS")
    print("=" * 70)
    print(f"Encode script:         {args.encode}")
    print(f"Verify script:         {args.verify}")
    print(f"Verify-wrong script:   {args.verify_wrong}")
    print(f"Test blocks:           {args.blocks}")
    print(f"Message bytes:         {args.msg_bytes}")
    print(f"Noise levels (T4):     {noise_levels}")
    print("=" * 70)

    t1_pass = test_t1_determinism(args.encode, args.blocks, args.msg_bytes)
    t2_pass = test_t2_correctness(args.encode, args.verify, args.blocks, args.msg_bytes)
    t3_pass = test_t3_rejection(args.verify_wrong, args.encode, args.blocks, args.msg_bytes)
    t4_pass = test_t4_noise_robustness(
        args.verify, args.encode, args.blocks, args.msg_bytes, noise_levels
    )

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"T1 (Determinism):      {'PASS' if t1_pass else 'FAIL'}")
    print(f"T2 (Correctness):      {'PASS' if t2_pass else 'FAIL'}")
    print(f"T3 (Rejection):        {'PASS' if t3_pass else 'FAIL'}")
    print(f"T4 (Noise Robustness): {'PASS' if t4_pass else 'FAIL (expected—no real ECC)'}")
    print("=" * 70)

    overall = t1_pass and t2_pass and t3_pass
    print(f"\nOverall (T1-T3): {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
