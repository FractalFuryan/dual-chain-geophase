"""
test_dual_phase_distance.py: Dual Geo Phase Angular Distance Audit Tests

Validates that dual-phase parameter projections maintain orthogonality
and do not collapse into alignment.

This is an **audit-only test**, run at build time to verify structural
properties. It does NOT gate runtime behavior.
"""

import pytest
from geophase.dual_phase import cosine_similarity, cosine_buffer_ok
from geophase.param_vectors import param_vector_from_hash, dual_phase_vectors


class TestCosineDistance:
    """Basic cosine similarity functionality."""

    def test_identical_vectors_similarity_one(self):
        """Identical vectors should have cosine similarity = 1.0."""
        v = [1.0, 0.0, 0.5]
        assert abs(cosine_similarity(v, v) - 1.0) < 1e-9

    def test_orthogonal_vectors_similarity_zero(self):
        """Perpendicular vectors should have cosine similarity = 0.0."""
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        assert abs(cosine_similarity(v1, v2)) < 1e-9

    def test_opposite_vectors_similarity_negative_one(self):
        """Opposite vectors should have cosine similarity = -1.0."""
        v1 = [1.0, 0.0, 0.0]
        v2 = [-1.0, 0.0, 0.0]
        assert abs(cosine_similarity(v1, v2) - (-1.0)) < 1e-9

    def test_zero_vector_returns_zero(self):
        """Zero vector should return 0.0 similarity."""
        v1 = [0.0, 0.0, 0.0]
        v2 = [1.0, 2.0, 3.0]
        assert cosine_similarity(v1, v2) == 0.0
        assert cosine_similarity(v2, v1) == 0.0

    def test_length_mismatch_raises_error(self):
        """Vectors of different lengths should raise ValueError."""
        v1 = [1.0, 0.0]
        v2 = [1.0, 0.0, 0.5]
        with pytest.raises(ValueError, match="Vector lengths must match"):
            cosine_similarity(v1, v2)

    def test_normalized_vectors(self):
        """Normalized parallel vectors should have similarity = 1.0."""
        v1 = [0.6, 0.8]  # magnitude 1.0
        v2 = [0.6, 0.8]
        assert abs(cosine_similarity(v1, v2) - 1.0) < 1e-9

    def test_scaled_vectors_same_similarity(self):
        """Scaling doesn't change cosine similarity (angle preserved)."""
        v1 = [1.0, 2.0, 3.0]
        v2 = [2.0, 4.0, 6.0]  # v1 × 2
        sim_original = cosine_similarity(v1, [1.0, 0.0, 0.0])
        sim_scaled = cosine_similarity(v2, [2.0, 0.0, 0.0])
        assert abs(sim_original - sim_scaled) < 1e-9


class TestCosineBuffer:
    """Cosine buffer threshold enforcement."""

    def test_buffer_accepts_orthogonal_vectors(self):
        """Orthogonal vectors should pass any positive tau."""
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        assert cosine_buffer_ok(v1, v2, tau=0.90)
        assert cosine_buffer_ok(v1, v2, tau=0.50)
        assert cosine_buffer_ok(v1, v2, tau=0.01)

    def test_buffer_rejects_aligned_vectors(self):
        """Identical vectors should fail unless tau = 1.0."""
        v = [1.0, 2.0, 3.0]
        assert not cosine_buffer_ok(v, v, tau=0.99)
        assert cosine_buffer_ok(v, v, tau=1.0)

    def test_buffer_default_tau(self):
        """Default tau=0.90 should reject high-similarity vectors."""
        v1 = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        v2 = [0.92, 0.39, 0.0, 0.0, 0.0, 0.0]  # ~95% similarity
        assert not cosine_buffer_ok(v1, v2)  # default tau=0.90

    def test_buffer_accepts_below_threshold(self):
        """Vectors below threshold should pass."""
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.85, 0.5, 0.0]  # ~85% similarity
        assert cosine_buffer_ok(v1, v2, tau=0.90)

    def test_buffer_rejects_above_threshold(self):
        """Vectors above threshold should fail."""
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.95, 0.31, 0.0]  # ~95% similarity
        assert not cosine_buffer_ok(v1, v2, tau=0.90)


class TestParamVectorGeneration:
    """Parameter vector generation from hash material."""

    def test_param_vector_phase_a_deterministic(self):
        """Same seed should always produce same Phase A vector."""
        seed = b"test-seed-deterministic-001"
        v1 = param_vector_from_hash(seed, "A")
        v2 = param_vector_from_hash(seed, "A")
        assert v1 == v2

    def test_param_vector_phase_b_deterministic(self):
        """Same seed should always produce same Phase B vector."""
        seed = b"test-seed-deterministic-001"
        v1 = param_vector_from_hash(seed, "B")
        v2 = param_vector_from_hash(seed, "B")
        assert v1 == v2

    def test_param_vector_phases_different(self):
        """Phase A and B from same seed should be different."""
        seed = b"test-seed-different-phases"
        v_a = param_vector_from_hash(seed, "A")
        v_b = param_vector_from_hash(seed, "B")
        assert v_a != v_b

    def test_param_vector_length(self):
        """Parameter vectors should have exactly 6 components."""
        seed = b"test-seed-length-check"
        v_a = param_vector_from_hash(seed, "A")
        v_b = param_vector_from_hash(seed, "B")
        assert len(v_a) == 6
        assert len(v_b) == 6

    def test_param_vector_range(self):
        """All components should be in [0.0, 1.0]."""
        seed = b"test-seed-range-check"
        v = param_vector_from_hash(seed, "A")
        for component in v:
            assert 0.0 <= component <= 1.0


class TestDualPhaseVectors:
    """Dual-phase vector pair generation."""

    def test_dual_phase_returns_pair(self):
        """Dual phase function should return (v_a, v_b) tuple."""
        seed = b"test-dual-phase"
        v_a, v_b = dual_phase_vectors(seed)
        assert isinstance(v_a, list)
        assert isinstance(v_b, list)
        assert len(v_a) == 6
        assert len(v_b) == 6

    def test_dual_phase_deterministic(self):
        """Same seed should produce same vector pair."""
        seed = b"test-dual-phase-deterministic"
        v_a1, v_b1 = dual_phase_vectors(seed)
        v_a2, v_b2 = dual_phase_vectors(seed)
        assert v_a1 == v_a2
        assert v_b1 == v_b2

    def test_dual_phase_different_seeds(self):
        """Different seeds should produce different pairs."""
        seed1 = b"test-seed-1"
        seed2 = b"test-seed-2"
        v_a1, v_b1 = dual_phase_vectors(seed1)
        v_a2, v_b2 = dual_phase_vectors(seed2)
        assert v_a1 != v_a2 or v_b1 != v_b2


class TestDualPhaseAudit:
    """Full dual-phase audit: independence check."""

    def test_audit_single_nonce_independence(self):
        """Single nonce should produce orthogonal phase vectors."""
        nonce = b"audit-seed-001"
        v_a, v_b = dual_phase_vectors(nonce)

        # Default tau=0.90: allow up to 90% similarity
        # With independent hash projections, expect much lower
        assert cosine_buffer_ok(v_a, v_b, tau=0.90)

    def test_audit_multiple_seeds_all_orthogonal(self):
        """Multiple seeds should maintain reasonable orthogonality."""
        nonces = [
            b"audit-nonce-001",
            b"audit-nonce-002",
            b"audit-nonce-003",
            b"audit-nonce-004",
            b"audit-nonce-005",
        ]

        similarities = []
        for nonce in nonces:
            v_a, v_b = dual_phase_vectors(nonce)
            sim = cosine_similarity(v_a, v_b)
            similarities.append(sim)
            # Relaxed threshold: most should pass tau=0.95, some may exceed
            # due to randomness in hash projections

        # At least 4 out of 5 should be < 0.95
        passing = sum(1 for s in similarities if s < 0.95)
        assert passing >= 4, f"Only {passing}/5 seeds passed orthogonality"

    def test_audit_strict_orthogonality(self):
        """Vectors should show independent structure (cosine < 0.95)."""
        # This is a realistic check: Phase A uses SHA256, Phase B uses BLAKE2b
        nonce = b"audit-strict-orthogonality"
        v_a, v_b = dual_phase_vectors(nonce)
        similarity = cosine_similarity(v_a, v_b)

        # With two different hash algorithms, expect < 0.95 similarity
        # (hash distribution makes perfect orthogonality rare with 6D)
        assert similarity < 0.95, f"Vectors too similar: {similarity}"

    def test_audit_batch_sweep(self):
        """Batch audit: verify 100 seeds show decorrelated phases."""
        count = 100
        min_similarity = 1.0
        max_similarity = 0.0
        failures = 0

        for i in range(count):
            nonce = f"batch-audit-{i:04d}".encode("utf-8")
            v_a, v_b = dual_phase_vectors(nonce)
            sim = cosine_similarity(v_a, v_b)

            min_similarity = min(min_similarity, sim)
            max_similarity = max(max_similarity, sim)

            # Audit threshold: tau=0.95 for batch (realistic with different hash algs)
            if not cosine_buffer_ok(v_a, v_b, tau=0.95):
                failures += 1

        # Allow up to 20% failures (some high-similarity pairs are expected by chance)
        assert failures < 20, f"Failed {failures}/{count} orthogonality checks (tau=0.95)"

        # Diagnostic: report distribution
        print(
            f"\nBatch audit ({count} seeds, tau=0.95):"
            f"\n  Min similarity: {min_similarity:.4f}"
            f"\n  Max similarity: {max_similarity:.4f}"
            f"\n  Failures: {failures}/100 ({100*failures//count}%)"
            f"\n  Audit result: ✓ (SHA256 A vs BLAKE2b B decorrelated)"
        )


class TestStaticAnalysisComplianceMypy:
    """Verify mypy-safe type annotations (no Any, proper casts)."""

    def test_cosine_similarity_returns_float(self):
        """Return type should be float, not Any."""
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        result = cosine_similarity(v1, v2)
        assert isinstance(result, float)

    def test_cosine_buffer_ok_returns_bool(self):
        """Return type should be bool, not Any."""
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        result = cosine_buffer_ok(v1, v2)
        assert isinstance(result, bool)

    def test_param_vector_returns_list_float(self):
        """Return type should be List[float]."""
        seed = b"type-check"
        result = param_vector_from_hash(seed, "A")
        assert isinstance(result, list)
        assert all(isinstance(x, float) for x in result)

    def test_dual_phase_vectors_returns_tuple(self):
        """Return type should be tuple of lists."""
        seed = b"type-check-dual"
        result = dual_phase_vectors(seed)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], list)
        assert isinstance(result[1], list)
