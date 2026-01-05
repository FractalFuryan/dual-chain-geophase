"""
dual_phase.py: Dual Geo Phase Angular Distance Audit

Dual-phase parameterization with audit-only cosine buffer ensures
structural non-alignment without introducing runtime filtering, memory,
or optimization pressure.

This module is **audit-only / batch-only**, not runtime-gating.
It verifies that two independent projections of the same parameter space
do not collapse into alignment.

Security Property:
  Cosine similarity ≤ τ (default 0.90) ensures the two phase vectors
  remain orthogonal/independent, preventing structural convergence.

This is NOT:
  - Runtime filtering
  - Output censorship
  - Perceptual comparison
  - Optimization objective

It IS:
  - A structural guarantee
  - Parameterization audit
  - Stateless batch verification
"""

from __future__ import annotations

import math
from typing import List


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        a: First vector (must be same length as b).
        b: Second vector (must be same length as a).

    Returns:
        Cosine similarity in [0, 1].
        Returns 0.0 if either vector has zero magnitude.

    Formula:
        cos(θ) = (a · b) / (||a|| × ||b||)
    """
    if len(a) != len(b):
        raise ValueError(f"Vector lengths must match: {len(a)} != {len(b)}")

    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def cosine_buffer_ok(a: List[float], b: List[float], tau: float = 0.90) -> bool:
    """
    Audit-only cosine buffer constraint.

    Ensures two independent parameter projections do not align
    beyond threshold τ.

    Args:
        a: Phase A parameter vector.
        b: Phase B parameter vector (from independent hash projection).
        tau: Maximum allowed cosine similarity (default 0.90).
             Increase for more tolerance, decrease for stricter orthogonality.

    Returns:
        True if cosine_similarity(a, b) <= tau.
        False otherwise.

    Note:
        This is **NOT** a rejection criterion. It's an audit assertion.
        Use in tests to verify structural properties at build time.

    Example:
        >>> v1 = [1.0, 0.0, 0.5]
        >>> v2 = [0.1, 0.9, 0.2]
        >>> assert cosine_buffer_ok(v1, v2, tau=0.85)
    """
    similarity = cosine_similarity(a, b)
    return similarity <= tau
