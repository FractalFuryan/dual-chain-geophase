"""
test_covenant_gate.py: Non-Regression Tests for ECC–AEAD Covenant

These tests enforce the immutable security invariant:
  ACCEPT ⟺ AEAD_verify(ciphertext, AD) = true

If these tests ever fail, it means acceptance logic has been bypassed or modified.
This is a security defect.
"""

import os
import pytest

from geophase.covenant import verify_gate


class AlwaysSucceedsECC:
    """Mock ECC that always returns something (even if wrong)."""

    def __call__(self, carrier: bytes) -> bytes:
        return carrier


class AlwaysFailsAEAD:
    """Mock AEAD that always rejects."""

    def __call__(self, ct: bytes, ad: bytes) -> bytes:
        raise ValueError("InvalidTag")


class SucceedsAEADWithADCheck:
    """Mock AEAD that checks AD and returns plaintext if match."""

    def __init__(self, expected_ad: bytes, plaintext: bytes):
        self.expected_ad = expected_ad
        self.plaintext = plaintext

    def __call__(self, ct: bytes, ad: bytes) -> bytes:
        if ad != self.expected_ad:
            raise ValueError("InvalidTag")
        return self.plaintext


class TestCovenantGate:
    """ECC–AEAD Covenant enforcement tests."""

    def test_covenant_rejects_when_aead_fails_even_if_ecc_succeeds(self):
        """
        CRITICAL: If ECC "succeeds" but AEAD fails, result must be REJECT.

        This is the core covenant: ECC success does NOT imply acceptance.
        """
        carrier = os.urandom(256)
        ad = b"some-ad"

        res = verify_gate(
            carrier=carrier,
            ad=ad,
            ecc_decode=AlwaysSucceedsECC(),
            aead_decrypt=AlwaysFailsAEAD(),
        )

        assert res.status == "REJECT", (
            "COVENANT VIOLATION: ECC success caused acceptance without AEAD"
        )
        assert res.plaintext is None

    def test_covenant_accepts_only_when_aead_succeeds(self):
        """
        CRITICAL: ACCEPT is only produced when AEAD verification succeeds.
        """
        carrier = os.urandom(256)
        ad = b"good-ad"
        pt = b"hello, covenant"

        res = verify_gate(
            carrier=carrier,
            ad=ad,
            ecc_decode=AlwaysSucceedsECC(),
            aead_decrypt=SucceedsAEADWithADCheck(expected_ad=ad, plaintext=pt),
        )

        assert res.status == "ACCEPT"
        assert res.plaintext == pt

    def test_covenant_rejects_with_wrong_ad(self):
        """
        CRITICAL: Associated data binding prevents replay and tampering.
        """
        carrier = os.urandom(256)
        ad_sent = b"good-ad"
        ad_received = b"wrong-ad"  # Attacker flipped the AD
        pt = b"hello"

        res = verify_gate(
            carrier=carrier,
            ad=ad_received,
            ecc_decode=AlwaysSucceedsECC(),
            aead_decrypt=SucceedsAEADWithADCheck(expected_ad=ad_sent, plaintext=pt),
        )

        assert res.status == "REJECT", (
            "COVENANT VIOLATION: AD tampering was not detected"
        )
        assert res.plaintext is None

    def test_covenant_never_returns_plaintext_on_reject(self):
        """
        CRITICAL: REJECT must never leak plaintext, even if ECC recovery succeeds.
        """
        carrier = os.urandom(256)
        ad = b"ad"

        res = verify_gate(
            carrier=carrier,
            ad=ad,
            ecc_decode=AlwaysSucceedsECC(),
            aead_decrypt=AlwaysFailsAEAD(),
        )

        assert res.plaintext is None, (
            "COVENANT VIOLATION: Plaintext leaked despite REJECT status"
        )

    def test_covenant_status_is_immutable(self):
        """
        CRITICAL: VerifyResult is frozen (immutable).
        This prevents accidental mutation in downstream code.
        """
        from geophase.covenant import VerifyResult

        res = VerifyResult(status="REJECT", plaintext=None)

        with pytest.raises(AttributeError):
            res.status = "ACCEPT"  # Should fail

        with pytest.raises(AttributeError):
            res.plaintext = b"hacked"  # Should fail


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
