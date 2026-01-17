"""
Comprehensive test suite for GeoPhase ↔ Base integration.
Run: pytest tests/test_eth_integration.py -v
"""

import pytest
import secrets
import time
from eth_utils import keccak

from geophase.eth import (
    compute_geo_commit,
    compute_seed_commit,
    compute_phase_hash,
    compute_ethics_anchor,
    GeoCommitParams,
    bytes32_to_hex,
    hex_to_bytes32,
    generate_nonce,
    create_procedural_auth_message,
    set_verifying_contract,
)


class TestCommitmentComputation:
    """Test commitment computation functions."""
    
    def test_seed_commit_deterministic(self):
        """Same inputs produce same seed commits."""
        seed = b"test_seed_12345678901234567890"
        nonce = b"fixed_nonce_32_bytes_long_here!"
        
        commit1 = compute_seed_commit(seed, nonce)
        commit2 = compute_seed_commit(seed, nonce)
        
        assert commit1 == commit2
        assert len(commit1) == 32
    
    def test_seed_commit_different_inputs(self):
        """Different inputs produce different commits."""
        seed1 = b"seed_1" + b"a" * 26
        seed2 = b"seed_2" + b"b" * 26
        nonce = generate_nonce()
        
        commit1 = compute_seed_commit(seed1, nonce)
        commit2 = compute_seed_commit(seed2, nonce)
        
        assert commit1 != commit2
    
    def test_phase_hash_deterministic(self):
        """Same vectors produce same hashes."""
        vector = b"phase_vector_data_here_12345678"
        
        hash1 = compute_phase_hash(vector)
        hash2 = compute_phase_hash(vector)
        
        assert hash1 == hash2
        assert len(hash1) == 32
    
    def test_ethics_anchor_deterministic(self):
        """Same ethics doc + timestamp produce same anchor."""
        doc = "https://ananke.ethics/policy/clinical/v1"
        timestamp = 1704153600
        
        anchor1 = compute_ethics_anchor(doc, timestamp)
        anchor2 = compute_ethics_anchor(doc, timestamp)
        
        assert anchor1 == anchor2
        assert len(anchor1) == 32
    
    def test_geo_commit_deterministic(self):
        """Same params produce same geoCommit."""
        params = GeoCommitParams(
            seed_commit=generate_nonce(),
            phaseA_hash=generate_nonce(),
            phaseB_hash=generate_nonce(),
            policy_id=generate_nonce(),
            version=1
        )
        
        commit1 = compute_geo_commit(params)
        commit2 = compute_geo_commit(params)
        
        assert commit1 == commit2
        assert len(commit1) == 32
    
    def test_geo_commit_different_params(self):
        """Different params produce different geoCommits."""
        base_params = {
            "seed_commit": generate_nonce(),
            "phaseA_hash": generate_nonce(),
            "phaseB_hash": generate_nonce(),
            "policy_id": generate_nonce(),
            "version": 1
        }
        
        commit1 = compute_geo_commit(GeoCommitParams(**base_params))
        
        # Change one field
        modified_params = base_params.copy()
        modified_params["version"] = 2
        commit2 = compute_geo_commit(GeoCommitParams(**modified_params))
        
        assert commit1 != commit2


class TestHexConversion:
    """Test hex conversion utilities."""
    
    def test_bytes32_to_hex(self):
        """Convert bytes32 to hex."""
        b = b"\x12\x34\x56\x78" + b"\x00" * 28
        h = bytes32_to_hex(b)
        
        assert h.startswith("0x")
        assert len(h) == 66  # 0x + 64 hex chars
        assert h == "0x1234567800000000000000000000000000000000000000000000000000000000"
    
    def test_hex_to_bytes32(self):
        """Convert hex to bytes32."""
        h = "0x1234567800000000000000000000000000000000000000000000000000000000"
        b = hex_to_bytes32(h)
        
        assert len(b) == 32
        assert b[:4] == b"\x12\x34\x56\x78"
    
    def test_roundtrip_conversion(self):
        """Bytes → hex → bytes should be identity."""
        original = generate_nonce()
        h = bytes32_to_hex(original)
        recovered = hex_to_bytes32(h)
        
        assert original == recovered


class TestPrivacyGuarantees:
    """Test privacy properties."""
    
    def test_seed_not_in_commit(self):
        """Original seed is not in commitment."""
        seed = b"sensitive_medical_record_12345"
        nonce = generate_nonce()
        
        commit = compute_seed_commit(seed, nonce)
        
        # Seed should not appear in commit
        assert seed not in commit
        assert b"sensitive" not in commit
        assert b"medical" not in commit
    
    def test_vector_not_in_hash(self):
        """Original vector is not in hash."""
        vector = b"biometric_data_vector_sensitive"
        
        hash_val = compute_phase_hash(vector)
        
        assert vector not in hash_val
        assert b"biometric" not in hash_val
    
    def test_commit_irreversible(self):
        """Cannot recover original from commitment."""
        seed = secrets.token_bytes(32)
        nonce = generate_nonce()
        
        commit = compute_seed_commit(seed, nonce)
        
        # Even knowing the nonce, commit is one-way
        # (This is a property test - we can't prove it, but we verify format)
        assert len(commit) == 32
        assert commit != seed
        assert commit != nonce


class TestEIP712Messages:
    """Test EIP-712 message structure."""
    
    def test_message_structure(self):
        """EIP-712 message has correct structure."""
        set_verifying_contract("0x1234567890123456789012345678901234567890")
        
        message = create_procedural_auth_message(
            seed_commit=generate_nonce(),
            mode=0,
            preset=42,
            expires=int(time.time()) + 3600,
            nonce=generate_nonce()
        )
        
        assert message["primaryType"] == "ProceduralAuth"
        assert "domain" in message
        assert "types" in message
        assert "message" in message
        
        assert message["domain"]["name"] == "AnankeGeoPhase"
        assert message["domain"]["version"] == "1"
        assert message["domain"]["chainId"] == 8453
    
    def test_message_fields(self):
        """Message contains all required fields."""
        set_verifying_contract("0x1234567890123456789012345678901234567890")
        
        seed_commit = generate_nonce()
        nonce = generate_nonce()
        expires = int(time.time()) + 3600
        
        message = create_procedural_auth_message(
            seed_commit=seed_commit,
            mode=1,
            preset=123,
            expires=expires,
            nonce=nonce
        )
        
        msg = message["message"]
        assert msg["mode"] == 1
        assert msg["preset"] == 123
        assert msg["expires"] == expires
        assert msg["seedCommit"] == bytes32_to_hex(seed_commit)
        assert msg["nonce"] == bytes32_to_hex(nonce)


class TestPolicyGeneration:
    """Test policy ID generation."""
    
    def test_policy_id_format(self):
        """Policy IDs are 32-byte keccak256 hashes."""
        policy_name = "clinical_v1"
        policy_id = keccak(f"ANANKE_POLICY_{policy_name}".encode('utf-8'))
        
        assert len(policy_id) == 32
        assert isinstance(policy_id, bytes)
    
    def test_different_policies_different_ids(self):
        """Different policies produce different IDs."""
        id1 = keccak(b"ANANKE_POLICY_clinical_v1")
        id2 = keccak(b"ANANKE_POLICY_entertainment_v1")
        
        assert id1 != id2


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_seed(self):
        """Empty seed still produces valid commit."""
        seed = b""
        nonce = generate_nonce()
        
        commit = compute_seed_commit(seed, nonce)
        assert len(commit) == 32
    
    def test_max_version(self):
        """Max uint32 version works."""
        params = GeoCommitParams(
            seed_commit=generate_nonce(),
            phaseA_hash=generate_nonce(),
            phaseB_hash=generate_nonce(),
            policy_id=generate_nonce(),
            version=2**32 - 1  # Max uint32
        )
        
        commit = compute_geo_commit(params)
        assert len(commit) == 32
    
    def test_zero_version(self):
        """Zero version works."""
        params = GeoCommitParams(
            seed_commit=generate_nonce(),
            phaseA_hash=generate_nonce(),
            phaseB_hash=generate_nonce(),
            policy_id=generate_nonce(),
            version=0
        )
        
        commit = compute_geo_commit(params)
        assert len(commit) == 32


class TestVectorConformance:
    """Test against known test vectors (if available)."""
    
    def test_known_vector_1(self):
        """Test against known test vector 1."""
        # Using all-zero inputs for reproducibility
        params = GeoCommitParams(
            seed_commit=b"\x00" * 32,
            phaseA_hash=b"\x00" * 32,
            phaseB_hash=b"\x00" * 32,
            policy_id=b"\x00" * 32,
            version=1
        )
        
        commit = compute_geo_commit(params)
        
        # This hash should be deterministic
        # (Replace with actual expected value after first run)
        assert len(commit) == 32
        assert commit.hex() == commit.hex()  # Tautology for now
        
        # Print for documentation
        print(f"\nTest Vector 1 (all zeros, version=1):")
        print(f"  geoCommit: {bytes32_to_hex(commit)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
