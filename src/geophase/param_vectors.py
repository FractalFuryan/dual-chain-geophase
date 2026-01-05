"""
param_vectors.py: Dual-Phase Parameter Vector Generation

Generates two independent parameter vectors from the same hash material
for structural audit via cosine buffer verification.

This module is **audit-only**, enabling build-time assertions about
parameterization independence.
"""

from __future__ import annotations

from hashlib import sha256, blake2b
from typing import List


def param_vector_from_hash(hash_material: bytes, projection: str = "A") -> List[float]:
    """
    Generate a parameter vector from hash material.

    Args:
        hash_material: Seed bytes for deterministic generation.
        projection: Phase identifier ("A" for primary, "B" for secondary).
                   Different projections use different algorithms for orthogonality.

    Returns:
        Parameter vector (6 floats in [0.0, 1.0]).

    Method:
        Phase A: SHA256 direct hash
        Phase B: BLAKE2b with different context string
        This ensures strong decorrelation between phases.

    Example:
        >>> seed = b"test-seed-12345"
        >>> v_a = param_vector_from_hash(seed, "A")
        >>> v_b = param_vector_from_hash(seed, "B")
        >>> len(v_a), len(v_b)
        (6, 6)
    """
    if projection == "A":
        # Phase A: SHA256 with prefix
        tag = b"::param::A"
        h = sha256(hash_material + tag).digest()
    else:
        # Phase B: BLAKE2b with different algorithm entirely
        # This maximizes orthogonality to Phase A
        tag = b"::param::B"
        h = blake2b(hash_material + tag, digest_size=32).digest()

    # Extract 6 integers from hash (4 bytes each)
    integers = [
        int.from_bytes(h[i : i + 4], byteorder="big") for i in range(0, 24, 4)
    ]

    # Normalize to [0.0, 1.0]
    return [(i % 10000) / 10000.0 for i in integers]


def dual_phase_vectors(seed: bytes) -> tuple[List[float], List[float]]:
    """
    Generate two independent phase vectors from the same seed.

    Args:
        seed: Master seed material (e.g., from nonce, entropy source).

    Returns:
        Tuple of (phase_a_vector, phase_b_vector).
        Each is a list of 6 floats.

    Security Property:
        Phase B is derived from Phase A material + independent suffix,
        ensuring structural non-alignment.
    """
    v_a = param_vector_from_hash(seed, "A")
    v_b = param_vector_from_hash(seed, "B")
    return v_a, v_b
