"""
covenant.py: ECC–AEAD Covenant Enforcement Gate

This module enforces the non-negotiable security invariant:
  ACCEPT ⟺ AEAD_verify(K, ciphertext, AD) = true

ECC is strictly a transport-layer repair mechanism. It may output:
  - corrected ciphertext
  - uncorrected ciphertext
  - arbitrary garbage

Only AEAD verification authorizes acceptance.
No acceptance path may bypass this gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class VerifyResult:
    """Immutable result of AEAD-gated verification."""

    status: str  # "ACCEPT" | "REJECT"
    plaintext: Optional[bytes] = None


def verify_gate(
    carrier: bytes,
    ad: bytes,
    ecc_decode: Callable[[bytes], bytes],
    aead_decrypt: Callable[[bytes, bytes], bytes],
) -> VerifyResult:
    """
    ECC–AEAD Covenant Gate (Single Source of Truth for Acceptance)

    This is the ONLY function that may produce ACCEPT results.

    Flow:
      1. ECC decoding (transport repair, best-effort)
      2. AEAD decryption & verification (sole authority)

    Args:
        carrier: Received carrier bytes (possibly corrupted by noise).
        ad: Associated data for AEAD verification (public headers).
        ecc_decode: Callable that repairs carrier noise. May return garbage.
        aead_decrypt: Callable that decrypts & verifies. Throws on MAC failure.

    Returns:
        VerifyResult with status="ACCEPT" and plaintext,
        or status="REJECT" with plaintext=None.

    Security Invariant (Covenant):
        ACCEPT ⟹ AEAD verification succeeded
        AEAD failure ⟹ REJECT (no exceptions)
    """
    # Step 1: ECC attempts best-effort repair
    candidate_ct = ecc_decode(carrier)

    # Step 2: AEAD is the sole acceptance gate
    try:
        plaintext = aead_decrypt(candidate_ct, ad)
    except Exception:
        # MAC verification failed → REJECT (no questions asked)
        return VerifyResult(status="REJECT", plaintext=None)

    # AEAD succeeded → ACCEPT
    return VerifyResult(status="ACCEPT", plaintext=plaintext)
