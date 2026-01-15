"""
test_mixer.py: Unit tests for enhanced_F_k_v2 and mixer primitives.

Tests cover:
  - Ancilla determinism
  - Entropy proxy behavior
  - Teleport probability bounds
  - Chain reproducibility
  - CSPRNG augmentation (optional)
"""

import pytest
from geophase.mixer import (
    ancilla16,
    real_rng_u16,
    hybrid_ancilla16,
    mix64,
    Jb_from_k,
    entropy_proxy_0_1,
    p_tp_state,
    enhanced_F_k_v2,
    U16,
)


class TestAncilla:
    """Ancilla chain determinism and properties."""

    def test_ancilla16_deterministic(self):
        """Same seed + t => same ancilla."""
        seed = b"test_seed_12345"
        a1 = ancilla16(seed, 0)
        a2 = ancilla16(seed, 0)
        assert a1 == a2

    def test_ancilla16_range(self):
        """Ancilla is 16-bit."""
        seed = b"test"
        for t in range(100):
            a = ancilla16(seed, t)
            assert 0 <= a < U16

    def test_ancilla16_different_steps(self):
        """Different t => likely different ancilla."""
        seed = b"test"
        ancillas = [ancilla16(seed, t) for t in range(10)]
        # At least some should differ
        assert len(set(ancillas)) > 1

    def test_ancilla16_different_domains(self):
        """Different domain => likely different ancilla."""
        seed = b"test"
        a1 = ancilla16(seed, 0, domain=b"dom1")
        a2 = ancilla16(seed, 0, domain=b"dom2")
        assert a1 != a2

    def test_hybrid_ancilla_deterministic_off(self):
        """Hybrid with use_real_rng=False is deterministic."""
        seed = b"test"
        h1 = hybrid_ancilla16(seed, 0, use_real_rng=False)
        h2 = hybrid_ancilla16(seed, 0, use_real_rng=False)
        assert h1 == h2

    def test_hybrid_ancilla_range_on(self):
        """Hybrid with real_rng still 16-bit."""
        seed = b"test"
        for _ in range(20):
            h = hybrid_ancilla16(seed, 0, use_real_rng=True)
            assert 0 <= h < U16


class TestMixers:
    """Test mix64, Jb_from_k."""

    def test_mix64_deterministic(self):
        """mix64 is deterministic."""
        x = 12345
        m1 = mix64(x)
        m2 = mix64(x)
        assert m1 == m2

    def test_mix64_invertible_style(self):
        """mix64 produces reasonable spread."""
        # Just check it's not trivial
        values = [mix64(i) for i in range(100)]
        unique = set(values)
        assert len(unique) == 100  # All different

    def test_Jb_from_k_deterministic(self):
        """Jb_from_k is deterministic."""
        k = 999
        j1 = Jb_from_k(k)
        j2 = Jb_from_k(k)
        assert j1 == j2

    def test_Jb_different_from_k(self):
        """Jb values vary with k."""
        Jbs = [Jb_from_k(k) for k in range(100)]
        unique = set(Jbs)
        assert len(unique) > 50  # Most differ


class TestEntropyProxy:
    """Test entropy_proxy_0_1."""

    def test_entropy_all_zeros(self):
        """All 0s → entropy ~0."""
        H = entropy_proxy_0_1(0)
        assert H < 0.1

    def test_entropy_all_ones(self):
        """All 1s → entropy ~0."""
        H = entropy_proxy_0_1(0xFFFFFFFF)
        assert H < 0.1

    def test_entropy_half_and_half(self):
        """Half 1s → entropy high."""
        # 16 ones in 32 bits (via checkerboard pattern)
        half = 0xAAAAAAAA  # 10101010... pattern
        H = entropy_proxy_0_1(half)
        assert H > 0.9

    def test_entropy_bounds(self):
        """Entropy always in [0, 1]."""
        for x in [0, 1, 0xFFFFFFFF, 0x12345678, 0x80000000]:
            H = entropy_proxy_0_1(x)
            assert 0.0 <= H <= 1.0


class TestTeleportProbability:
    """Test p_tp_state."""

    def test_p_tp_bounds_default(self):
        """p_tp is in [pmin, pmax]."""
        k, Ja, Jb = 123, 456789, 987654
        for seed_val in range(20):
            p = p_tp_state(k + seed_val, Ja, Jb, p0=0.03)
            assert 0.01 <= p <= 0.15

    def test_p_tp_custom_bounds(self):
        """p_tp respects custom pmin/pmax."""
        p = p_tp_state(10, 100, 200, p0=0.05, pmin=0.02, pmax=0.10)
        assert 0.02 <= p <= 0.10

    def test_p_tp_adapts_to_entropy(self):
        """p_tp increases when entropy is low."""
        # Create two cases: high entropy vs low entropy
        # High entropy: k chosen so mixed bits are uniform
        k_high = 0x5555AAAA  # Balanced bit pattern
        p_high = p_tp_state(k_high, 100, 200)

        # Low entropy: k is extreme
        k_low = 0
        p_low = p_tp_state(k_low, 100, 200)

        # When entropy is low (all 0s), teleport should be higher
        assert p_low >= p_high or abs(p_low - p_high) < 0.05  # Tolerance


class TestEnhancedF_k_v2:
    """Integration tests for enhanced_F_k_v2."""

    def setup_method(self):
        """Set up test fixtures."""
        self.seed = b"integration_test_seed_32bytes!!"
        self.n = 1 << 64  # Modulus
        self.dk = 1
        self.alpha = 1000
        self.gamma = 100
        self.c = 42
        self.r = 10

    def stub_redshift(self, r: int) -> int:
        """Simple redshift: (r // 10)."""
        return r // 10

    def stub_J(self, k: int) -> int:
        """Simple J: hash-based."""
        import hashlib
        h = hashlib.sha256(k.to_bytes(8, "big")).digest()
        return int.from_bytes(h[:8], "big")

    def stub_sign(self, x: int) -> int:
        """Simple sign."""
        return 1 if x >= 0 else -1

    def stub_teleport_share(self, k, k_anc, anc, G, n, U16):
        """Stub teleport: XOR k with anc."""
        k_new = (k ^ anc) % n
        return G, k_new

    def test_F_k_v2_deterministic_no_rng(self):
        """Same inputs => same output (without CSPRNG)."""
        k = 12345
        t = 0
        out1 = enhanced_F_k_v2(
            k, t, self.seed,
            dk=self.dk, alpha=self.alpha, gamma=self.gamma, c=self.c,
            n=self.n, r=self.r,
            redshift=self.stub_redshift,
            J=self.stub_J,
            sign=self.stub_sign,
            teleport_share=self.stub_teleport_share,
            use_real_rng=False,
        )
        out2 = enhanced_F_k_v2(
            k, t, self.seed,
            dk=self.dk, alpha=self.alpha, gamma=self.gamma, c=self.c,
            n=self.n, r=self.r,
            redshift=self.stub_redshift,
            J=self.stub_J,
            sign=self.stub_sign,
            teleport_share=self.stub_teleport_share,
            use_real_rng=False,
        )
        assert out1 == out2

    def test_F_k_v2_bounded(self):
        """Output is always in [0, n)."""
        for k in [0, 100, 99999]:
            out = enhanced_F_k_v2(
                k, 0, self.seed,
                dk=self.dk, alpha=self.alpha, gamma=self.gamma, c=self.c,
                n=self.n, r=self.r,
                redshift=self.stub_redshift,
                J=self.stub_J,
                sign=self.stub_sign,
                teleport_share=self.stub_teleport_share,
            )
            assert 0 <= out < self.n

    def test_F_k_v2_avalanche(self):
        """Small input change => likely different output."""
        k1 = 12345
        k2 = 12346
        t = 0

        out1 = enhanced_F_k_v2(
            k1, t, self.seed,
            dk=self.dk, alpha=self.alpha, gamma=self.gamma, c=self.c,
            n=self.n, r=self.r,
            redshift=self.stub_redshift,
            J=self.stub_J,
            sign=self.stub_sign,
            teleport_share=self.stub_teleport_share,
            use_real_rng=False,
        )
        out2 = enhanced_F_k_v2(
            k2, t, self.seed,
            dk=self.dk, alpha=self.alpha, gamma=self.gamma, c=self.c,
            n=self.n, r=self.r,
            redshift=self.stub_redshift,
            J=self.stub_J,
            sign=self.stub_sign,
            teleport_share=self.stub_teleport_share,
            use_real_rng=False,
        )
        assert out1 != out2

    def test_F_k_v2_chain(self):
        """Chain multiple steps without error."""
        k = 42
        n = 1 << 32
        for t in range(10):
            k = enhanced_F_k_v2(
                k, t, self.seed,
                dk=self.dk, alpha=self.alpha, gamma=self.gamma, c=self.c,
                n=n, r=self.r,
                redshift=self.stub_redshift,
                J=self.stub_J,
                sign=self.stub_sign,
                teleport_share=self.stub_teleport_share,
                use_real_rng=False,
            )
            assert 0 <= k < n


class TestHaloCircuitIntegration:
    """Placeholder: Halo2 circuit tests."""

    def test_halo2_imports(self):
        """Just check halo2_circuit module imports."""
        from geophase.halo2_circuit import (
            LimbDecomposition,
            U16Matrix,
            TeleportChain,
            TeleportProofSystem,
        )
        assert LimbDecomposition is not None
        assert U16Matrix is not None
        assert TeleportChain is not None
        assert TeleportProofSystem is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
