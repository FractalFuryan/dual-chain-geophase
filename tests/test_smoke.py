"""
test_smoke.py: Smoke tests for geophase package.

Tests basic functionality of util, chain, and compress modules.
"""

import pytest
import json
from geophase import util, chain, compress


class TestUtil:
    """Tests for util module."""

    def test_canonical_json(self):
        """Test canonical JSON serialization."""
        obj = {"z": 1, "a": 2, "m": 3}
        canonical = util.canonical_json(obj)
        # Should be sorted and minimal
        assert canonical == b'{"a":2,"m":3,"z":1}'

    def test_b64_roundtrip(self):
        """Test base64 encode/decode roundtrip."""
        original = b"Hello, World!"
        encoded = util.b64_encode(original)
        decoded = util.b64_decode(encoded)
        assert decoded == original

    def test_hash_sha256(self):
        """Test SHA-256 hashing."""
        data = b"test data"
        digest = util.hash_sha256(data)
        assert len(digest) == 32  # SHA-256 is 32 bytes

    def test_hex_roundtrip(self):
        """Test hex encode/decode roundtrip."""
        original = b"0x1234"
        encoded = util.hex_encode(original)
        decoded = util.hex_decode(encoded)
        assert decoded == original


class TestChain:
    """Tests for chain module."""

    def test_state_digest(self):
        """Test state digest computation."""
        state = {"t": 0, "counter": 42}
        digest = chain.commit_state_digest(state)
        assert len(digest) == 32  # SHA-256

    def test_availability_witness(self):
        """Test availability witness computation."""
        H_prev = b"\x00" * 32
        g_t = b"\x01" * 32
        public_header = {"version": 1}
        A_t = chain.compute_availability_witness(H_prev, g_t, public_header)
        assert len(A_t) == 32

    def test_binding_hash(self):
        """Test binding hash computation."""
        H_prev = b"\x00" * 32
        ct_hash = b"\x02" * 32
        g_t = b"\x01" * 32
        H_t = chain.compute_binding_hash(H_prev, ct_hash, g_t)
        assert len(H_t) == 32

    def test_verify_commitment(self):
        """Test commitment verification."""
        H_prev = b"\x00" * 32
        public_header = {"version": 1}
        state = {"t": 0}
        ct_hash = b"\x02" * 32

        g_t = chain.commit_state_digest(state)
        A_t = chain.compute_availability_witness(H_prev, g_t, public_header)
        H_t = chain.compute_binding_hash(H_prev, ct_hash, g_t)

        # Should verify successfully
        assert chain.verify_commitment(H_t, A_t, H_prev, g_t, ct_hash, public_header)

        # Should fail with wrong H_t
        wrong_H_t = b"\x99" * 32
        assert not chain.verify_commitment(wrong_H_t, A_t, H_prev, g_t, ct_hash, public_header)


class TestCompress:
    """Tests for compress module."""

    def test_compress_decompress_roundtrip(self):
        """Test compression/decompression roundtrip."""
        original_state = {"t": 0, "counter": 42, "data": "hello world"}
        compressed = compress.compress_structured_state(original_state)
        decompressed = compress.decompress_structured_state(compressed)
        assert decompressed == original_state

    def test_compression_ratio(self):
        """Test compression ratio calculation."""
        original = 1000
        compressed = 750
        ratio = compress.estimate_compression_ratio(original, compressed)
        assert ratio == 0.75

    def test_compression_ratio_zero_original(self):
        """Test compression ratio with zero original size."""
        ratio = compress.estimate_compression_ratio(0, 100)
        assert ratio == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
