"""
Tests for PolicyGrant EIP-712 signature verification.

These tests verify:
- Valid signature acceptance
- Expired grant rejection
- Domain mismatch detection
- Rights validation
- Nonce uniqueness
"""

import time

import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak

from geophase.eth.policy_grant import PolicyGrant, Rights, Mode
from geophase.eth.eip712_policy_grant import PolicyGrantVerifier


def k32(s: str) -> str:
    """Helper to create keccak256 hash as 0x-prefixed hex."""
    return "0x" + keccak(text=s).hex()


@pytest.fixture
def verifier():
    """Create a PolicyGrantVerifier with standard test parameters."""
    return PolicyGrantVerifier(
        name="GeoPhase",
        version="0.1.1",
        chain_id=8453,
        verifying_contract="0x0000000000000000000000000000000000000000",
        clock_skew_sec=0,
    )


def sign(verifier: PolicyGrantVerifier, grant: PolicyGrant, priv: str) -> tuple[str, str]:
    """
    Sign a PolicyGrant with a private key.

    Args:
        verifier: PolicyGrantVerifier to use for domain parameters
        grant: PolicyGrant to sign
        priv: Private key as 0x-prefixed hex string

    Returns:
        Tuple of (signature_hex, signer_address_lowercase)
    """
    acct = Account.from_key(priv)
    msg = encode_typed_data(full_message=verifier.typed_data(grant))
    return acct.sign_message(msg).signature.hex(), acct.address.lower()


def test_valid_signature(verifier):
    """Test that a valid signature is accepted."""
    priv = "0x" + "11" * 32
    now = int(time.time())
    g = PolicyGrant(
        commit="0x" + "22" * 32,
        policy_id=k32("P"),
        mode=0,
        rights=int(Rights.FRAME),
        exp=now + 60,
        nonce="0x" + "33" * 32,
        engine_version=1,
    )
    sig, addr = sign(verifier, g, priv)
    out = verifier.verify(g, sig, expected_signer=addr, now=now)
    assert out.signer == addr
    assert out.grant == g


def test_expired_rejected(verifier):
    """Test that expired grants are rejected."""
    priv = "0x" + "11" * 32
    now = int(time.time())
    g = PolicyGrant(
        commit="0x" + "22" * 32,
        policy_id=k32("P"),
        mode=0,
        rights=int(Rights.FRAME),
        exp=now - 1,
        nonce="0x" + "33" * 32,
        engine_version=1,
    )
    sig, addr = sign(verifier, g, priv)
    with pytest.raises(PermissionError, match="grant expired"):
        verifier.verify(g, sig, expected_signer=addr, now=now)


def test_domain_mismatch_rejected():
    """Test that signature from different domain is rejected."""
    v1 = PolicyGrantVerifier(
        name="GeoPhase",
        version="0.1.1",
        chain_id=8453,
        verifying_contract="0x0000000000000000000000000000000000000000",
    )
    v2 = PolicyGrantVerifier(
        name="GeoPhase",
        version="0.1.2",  # changed domain => must fail
        chain_id=8453,
        verifying_contract="0x0000000000000000000000000000000000000000",
    )
    priv = "0x" + "11" * 32
    now = int(time.time())
    g = PolicyGrant(
        commit="0x" + "22" * 32,
        policy_id=k32("P"),
        mode=0,
        rights=int(Rights.FRAME),
        exp=now + 60,
        nonce="0x" + "33" * 32,
        engine_version=1,
    )
    sig, addr = sign(v1, g, priv)
    with pytest.raises(PermissionError):
        v2.verify(g, sig, expected_signer=addr, now=now)


def test_signer_mismatch_rejected(verifier):
    """Test that signature from wrong signer is rejected."""
    priv1 = "0x" + "11" * 32
    priv2 = "0x" + "22" * 32
    addr2 = Account.from_key(priv2).address.lower()
    now = int(time.time())
    g = PolicyGrant(
        commit="0x" + "33" * 32,
        policy_id=k32("P"),
        mode=0,
        rights=int(Rights.FRAME),
        exp=now + 60,
        nonce="0x" + "44" * 32,
        engine_version=1,
    )
    sig, _ = sign(verifier, g, priv1)
    with pytest.raises(PermissionError, match="signer mismatch"):
        verifier.verify(g, sig, expected_signer=addr2, now=now)


def test_rights_bitflags():
    """Test that rights bitflags work correctly."""
    assert int(Rights.FRAME) == 1
    assert int(Rights.VIDEO) == 2
    assert int(Rights.MP4) == 4
    assert int(Rights.STREAM) == 8

    # Combined rights
    combined = int(Rights.FRAME) | int(Rights.VIDEO)
    assert combined == 3
    assert (combined & int(Rights.FRAME)) == int(Rights.FRAME)
    assert (combined & int(Rights.VIDEO)) == int(Rights.VIDEO)
    assert (combined & int(Rights.MP4)) == 0


def test_mode_values():
    """Test that mode values are correct."""
    assert int(Mode.STANDARD) == 0
    assert int(Mode.CLINICAL) == 1


def test_invalid_bytes32_rejected():
    """Test that invalid bytes32 hex strings are rejected."""
    now = int(time.time())
    
    # Too short
    with pytest.raises(ValueError):
        PolicyGrant(
            commit="0x1234",
            policy_id=k32("P"),
            mode=0,
            rights=1,
            exp=now + 60,
            nonce="0x" + "33" * 32,
        )
    
    # Missing 0x prefix
    with pytest.raises(ValueError):
        PolicyGrant(
            commit="11" * 32,
            policy_id=k32("P"),
            mode=0,
            rights=1,
            exp=now + 60,
            nonce="0x" + "33" * 32,
        )
    
    # Invalid hex
    with pytest.raises(ValueError):
        PolicyGrant(
            commit="0x" + "ZZ" * 32,
            policy_id=k32("P"),
            mode=0,
            rights=1,
            exp=now + 60,
            nonce="0x" + "33" * 32,
        )


def test_invalid_mode_rejected():
    """Test that invalid mode values are rejected."""
    now = int(time.time())
    with pytest.raises(ValueError, match="invalid mode"):
        PolicyGrant(
            commit="0x" + "11" * 32,
            policy_id=k32("P"),
            mode=99,  # invalid
            rights=1,
            exp=now + 60,
            nonce="0x" + "33" * 32,
        )


def test_invalid_rights_rejected():
    """Test that invalid rights values are rejected."""
    now = int(time.time())
    with pytest.raises(ValueError, match="invalid rights bitmask"):
        PolicyGrant(
            commit="0x" + "11" * 32,
            policy_id=k32("P"),
            mode=0,
            rights=-1,  # negative not allowed
            exp=now + 60,
            nonce="0x" + "33" * 32,
        )


def test_to_eip712_message():
    """Test that to_eip712_message() excludes seed_family_id."""
    now = int(time.time())
    g = PolicyGrant(
        commit="0x" + "11" * 32,
        policy_id=k32("P"),
        mode=0,
        rights=1,
        exp=now + 60,
        nonce="0x" + "33" * 32,
        engine_version=1,
        seed_family_id="my-vibe",  # should NOT appear in message
    )
    msg = g.to_eip712_message()
    assert "seed_family_id" not in msg
    assert msg["commit"] == "0x" + "11" * 32
    assert msg["policy_id"] == k32("P")
    assert msg["mode"] == 0
    assert msg["rights"] == 1
    assert msg["exp"] == now + 60
    assert msg["nonce"] == "0x" + "33" * 32
    assert msg["engine_version"] == 1


def test_clock_skew():
    """Test that clock skew allows reasonable time differences."""
    verifier_with_skew = PolicyGrantVerifier(
        name="GeoPhase",
        version="0.1.1",
        chain_id=8453,
        verifying_contract="0x0000000000000000000000000000000000000000",
        clock_skew_sec=60,  # 1 minute skew allowed
    )
    priv = "0x" + "11" * 32
    now = int(time.time())
    g = PolicyGrant(
        commit="0x" + "22" * 32,
        policy_id=k32("P"),
        mode=0,
        rights=int(Rights.FRAME),
        exp=now - 30,  # expired 30 seconds ago
        nonce="0x" + "33" * 32,
        engine_version=1,
    )
    sig, addr = sign(verifier_with_skew, g, priv)
    # Should succeed because clock_skew_sec=60 allows 30 second expiry
    out = verifier_with_skew.verify(g, sig, expected_signer=addr, now=now)
    assert out.signer == addr


def test_recover_signer(verifier):
    """Test that recover_signer returns correct address."""
    priv = "0x" + "11" * 32
    acct = Account.from_key(priv)
    now = int(time.time())
    g = PolicyGrant(
        commit="0x" + "22" * 32,
        policy_id=k32("P"),
        mode=0,
        rights=int(Rights.FRAME),
        exp=now + 60,
        nonce="0x" + "33" * 32,
        engine_version=1,
    )
    sig, _ = sign(verifier, g, priv)
    recovered = verifier.recover_signer(g, sig)
    assert recovered == acct.address.lower()
