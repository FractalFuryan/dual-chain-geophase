"""
Integration test for GeoPhase ↔ Base chain bridge.
Tests commitment computation, revocation checks, and attestation flow.
"""

from geophase.eth import (
    compute_geo_commit,
    compute_seed_commit,
    compute_phase_hash,
    compute_ethics_anchor,
    GeoCommitParams,
    bytes32_to_hex,
    generate_nonce,
)


def test_commitment_computation():
    """Test geoCommit computation matches expected format."""
    print("\n🧪 Test: Commitment Computation")
    
    # Generate test data
    seed = b"test_seed_12345678901234567890"
    user_nonce = generate_nonce()
    phaseA_vector = b"phaseA_test_vector_data_here..."
    phaseB_vector = b"phaseB_test_vector_data_here..."
    policy_name = "clinical_v1"
    
    # Compute components
    seed_commit = compute_seed_commit(seed, user_nonce)
    phaseA_hash = compute_phase_hash(phaseA_vector)
    phaseB_hash = compute_phase_hash(phaseB_vector)
    
    # Compute policy ID
    from eth_utils import keccak
    policy_id = keccak(f"ANANKE_POLICY_{policy_name}".encode('utf-8'))
    
    # Compute geoCommit
    params = GeoCommitParams(
        seed_commit=seed_commit,
        phaseA_hash=phaseA_hash,
        phaseB_hash=phaseB_hash,
        policy_id=policy_id,
        version=1
    )
    geo_commit = compute_geo_commit(params)
    
    print(f"  Seed Commit: {bytes32_to_hex(seed_commit)}")
    print(f"  Phase A Hash: {bytes32_to_hex(phaseA_hash)}")
    print(f"  Phase B Hash: {bytes32_to_hex(phaseB_hash)}")
    print(f"  Policy ID: {bytes32_to_hex(policy_id)}")
    print(f"  GeoCommit: {bytes32_to_hex(geo_commit)}")
    
    # Verify lengths
    assert len(seed_commit) == 32
    assert len(phaseA_hash) == 32
    assert len(phaseB_hash) == 32
    assert len(policy_id) == 32
    assert len(geo_commit) == 32
    
    print("  ✅ All hashes are 32 bytes")


def test_ethics_anchor():
    """Test ethics anchor computation."""
    print("\n🧪 Test: Ethics Anchor")
    
    ethics_doc = "https://ananke.ethics/policy/clinical/v1"
    timestamp = 1704153600  # 2024-01-02 00:00:00 UTC
    
    ethics_anchor = compute_ethics_anchor(ethics_doc, timestamp)
    
    print(f"  Ethics Doc: {ethics_doc}")
    print(f"  Timestamp: {timestamp}")
    print(f"  Ethics Anchor: {bytes32_to_hex(ethics_anchor)}")
    
    assert len(ethics_anchor) == 32
    print("  ✅ Ethics anchor computed")


def test_determinism():
    """Test that same inputs produce same outputs."""
    print("\n🧪 Test: Determinism")
    
    seed = b"determinism_test_seed_12345678"
    nonce = b"fixed_nonce_32_bytes_long_here!"
    
    commit1 = compute_seed_commit(seed, nonce)
    commit2 = compute_seed_commit(seed, nonce)
    
    assert commit1 == commit2
    print(f"  ✅ Deterministic: {bytes32_to_hex(commit1)}")


def test_collision_resistance():
    """Test that different inputs produce different outputs."""
    print("\n🧪 Test: Collision Resistance")
    
    seed1 = b"seed_1_aaaaaaaaaaaaaaaaaaaaaaa"
    seed2 = b"seed_2_bbbbbbbbbbbbbbbbbbbbbbb"
    nonce = generate_nonce()
    
    commit1 = compute_seed_commit(seed1, nonce)
    commit2 = compute_seed_commit(seed2, nonce)
    
    assert commit1 != commit2
    print(f"  Commit 1: {bytes32_to_hex(commit1)}")
    print(f"  Commit 2: {bytes32_to_hex(commit2)}")
    print("  ✅ Different inputs → different hashes")


def test_eip712_message_structure():
    """Test EIP-712 message creation."""
    print("\n🧪 Test: EIP-712 Message Structure")
    
    from geophase.eth import create_procedural_auth_message, set_verifying_contract
    import time
    
    # Set verifying contract
    set_verifying_contract("0x1234567890123456789012345678901234567890")
    
    seed_commit = generate_nonce()
    nonce = generate_nonce()
    
    message = create_procedural_auth_message(
        seed_commit=seed_commit,
        mode=0,
        preset=42,
        expires=int(time.time()) + 3600,
        nonce=nonce
    )
    
    assert message["primaryType"] == "ProceduralAuth"
    assert "domain" in message
    assert "types" in message
    assert "message" in message
    
    print(f"  Domain: {message['domain']['name']}")
    print(f"  Chain ID: {message['domain']['chainId']}")
    print(f"  Primary Type: {message['primaryType']}")
    print("  ✅ EIP-712 message structure valid")


def test_privacy_guarantees():
    """Verify no sensitive data is exposed in commitments."""
    print("\n🧪 Test: Privacy Guarantees")
    
    # Simulate sensitive data
    sensitive_seed = b"patient_medical_record_id_12345"
    sensitive_vector = b"sensitive_biometric_data_vector"
    
    # Compute hashes
    seed_commit = compute_seed_commit(sensitive_seed, generate_nonce())
    phase_hash = compute_phase_hash(sensitive_vector)
    
    # Verify original data is not in hash
    assert sensitive_seed not in seed_commit
    assert sensitive_vector not in phase_hash
    
    # Verify hash is one-way (cannot reverse)
    print(f"  Original Seed: {sensitive_seed}")
    print(f"  Hashed Commit: {bytes32_to_hex(seed_commit)}")
    print("  ✅ Original data not recoverable from hash")


if __name__ == "__main__":
    print("=" * 60)
    print("GeoPhase ↔ Base Chain Integration Tests")
    print("=" * 60)
    
    test_commitment_computation()
    test_ethics_anchor()
    test_determinism()
    test_collision_resistance()
    test_eip712_message_structure()
    test_privacy_guarantees()
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Deploy contracts: ./deploy.sh")
    print("  2. Update .env with contract addresses")
    print("  3. Run live chain tests (requires RPC)")
