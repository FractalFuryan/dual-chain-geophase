"""
mixer.py: Enhanced hybrid chaotic state mixer (v2).

Implements a non-autonomous, nonlinear modular map with entropy-gated
nonlocal transitions, designed for structured unpredictability while
preventing phase trapping.

Key Features:
  - Deterministic ancilla chain (seed + t → 16-bit token)
  - Dual-phase drift (orthogonal J_a and J_b mixers)
  - Stateless teleport probability (entropy-gated)
  - Optional CSPRNG augmentation for irreversibility
  - Audit-friendly, reproducible, no learning/profiling

Classification:
  A hybrid chaotic state mixer with entropy-salted nonlocal coupling.
  Not a PRNG, cipher, or optimizer—a pure mixing primitive.

Security Properties:
  - Bounded divergence (mod n confinement)
  - Lyapunov growth locally, no unbounded blow-up
  - Escape from phase traps via teleport
  - Stateless (no history, no profiling)
"""

from __future__ import annotations

import hashlib
import os
from typing import Callable, Optional, Tuple

U16 = 1 << 16  # 2^16


def _sha256(b: bytes) -> bytes:
    """SHA-256 hash primitive."""
    return hashlib.sha256(b).digest()


def ancilla16(seed: bytes, t: int, domain: bytes = b"anc") -> int:
    """
    Deterministic 16-bit ancilla derived from seed + t.

    Replaces random.getrandbits(16) for reproducibility.
    Used to gate teleport routing and mixing decisions.

    Args:
        seed: Base seed (typically 32 bytes).
        t: Step counter (0-indexed).
        domain: Domain separator to prevent collision across use cases.

    Returns:
        16-bit integer [0, 65535].

    Example:
        >>> a = ancilla16(b"test_seed", 0)
        >>> isinstance(a, int) and 0 <= a < 65536
        True
    """
    h = _sha256(seed + domain + t.to_bytes(8, "big"))
    return int.from_bytes(h[:2], "big")


def real_rng_u16() -> int:
    """
    Cryptographically secure 16-bit entropy from OS CSPRNG.

    Uses os.urandom() backed by the OS cryptographic random source.
    Used only when irreversibility is prioritized over reproducibility.

    Returns:
        16-bit integer [0, 65535].

    Note:
        This should be toggled via environment or explicit flag,
        not called unconditionally, to preserve auditability.
    """
    return int.from_bytes(os.urandom(2), "big")


def hybrid_ancilla16(
    seed: bytes,
    t: int,
    *,
    use_real_rng: bool = False,
    domain: bytes = b"anc",
) -> int:
    """
    Hybrid ancilla: deterministic ⊕ optional CSPRNG.

    Combines deterministic and cryptographic entropy for routing,
    preserving reproducibility by default while allowing irreversibility
    when explicitly enabled.

    Args:
        seed: Base seed.
        t: Step counter.
        use_real_rng: If True, XOR with OS CSPRNG. Default False (deterministic).
        domain: Domain separator.

    Returns:
        16-bit integer [0, 65535].

    Design:
        - Default (use_real_rng=False): fully deterministic, reproducible
        - With use_real_rng=True: deterministic ⊕ real entropy
        - XOR preserves uniform distribution and does not bias either source
    """
    det = ancilla16(seed, t, domain)
    if not use_real_rng:
        return det
    return det ^ real_rng_u16()


def mix64(x: int) -> int:
    """
    Fast reversible-style integer mixer (SplitMix64-inspired).

    Deterministic mixing without secrets, designed to spread bits
    across a 64-bit value for preliminary diversification.

    Args:
        x: 64-bit input integer.

    Returns:
        64-bit mixed output.

    Note:
        Not cryptographic, but useful for turning raw state into
        pseudo-random-looking values efficiently.
    """
    x = (x + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9 & 0xFFFFFFFFFFFFFFFF
    x = (x ^ (x >> 27)) * 0x94D049BB133111EB & 0xFFFFFFFFFFFFFFFF
    return x ^ (x >> 31)


def Jb_from_k(k: int) -> int:
    """
    Orthogonal drift source derived from k.

    Provides a second independent mixer to reduce resonance trapping
    and increase mixing diversity. Not anatomy, similarity, or learning—
    just deterministic mixing.

    Args:
        k: Current scalar/state value.

    Returns:
        Derived J_b value (similar magnitude to J_a inputs).
    """
    return mix64(k ^ 0xD1B54A32D192ED03)


def entropy_proxy_0_1(x32: int) -> float:
    """
    Stateless local entropy proxy (bit-balance measure).

    Returns a value in [0, 1] based on how close the bit count
    is to uniformity. Peak entropy at 0.5 (half 1s).

    Used to gate teleport probability adaptively without maintaining
    history or state.

    Args:
        x32: 32-bit value to analyze.

    Returns:
        Float in [0, 1], where 1.0 = maximum entropy-like measure.

    Formula:
        H = 4 * p * (1 - p), where p = population_count / 32
    """
    pop = (x32 & 0xFFFFFFFF).bit_count() / 32.0  # [0, 1]
    return 4.0 * pop * (1.0 - pop)  # [0, 1], peak at 0.5


def p_tp_state(
    k: int,
    Ja: int,
    Jb: int,
    p0: float = 0.03,
    beta: float = 0.06,
    pmin: float = 0.01,
    pmax: float = 0.15,
) -> float:
    """
    Stateless teleport probability based on local mixing quality.

    Increases teleport chance when local mixed bits look "too structured"
    (low entropy), encouraging phase exploration. Bounds prevent extremes.

    Args:
        k: Current scalar.
        Ja: Primary drift value.
        Jb: Secondary drift value.
        p0: Base teleport probability (default 0.03, 3%).
        beta: Sensitivity to entropy deficit (default 0.06).
        pmin: Minimum allowed p_tp (default 0.01).
        pmax: Maximum allowed p_tp (default 0.15).

    Returns:
        Float in [pmin, pmax] representing P(teleport).

    Design:
        p_tp = p0 + beta * (1 - H(mixed_bits))
        where H is entropy proxy.
        Clipped to [pmin, pmax] for stability.
    """
    # Derive a 32-bit "mixed" value from inputs
    x = ((Ja ^ (Jb >> 1)) ^ (k * 0x9E3779B1)) & 0xFFFFFFFF
    H = entropy_proxy_0_1(x)  # Higher = healthier (more uniform) mixing

    # Base + sensitivity to entropy deficit
    p = p0 + beta * (1.0 - H)

    # Clamp to safe bounds
    if p < pmin:
        return pmin
    if p > pmax:
        return pmax
    return p


def enhanced_F_k_v2(
    k: int,
    t: int,
    seed: bytes,
    *,
    dk: int,
    alpha: int,
    gamma: int,
    c: int,
    n: int,
    r: int,
    redshift: Callable[[int], int],
    J: Callable[[int], int],
    sign: Callable[[int], int],
    teleport_share: Callable[[int, int, int, Optional[object], int, int], Tuple[Optional[object], int]],
    k_anc: Optional[int] = None,
    G: Optional[object] = None,
    alpha2: Optional[int] = None,
    p0: float = 0.03,
    use_real_rng: bool = False,
) -> int:
    """
    Enhanced hybrid chaotic state mixer (v2).

    Implements:
      - Deterministic ancilla chain (seed + t → routing entropy)
      - Dual-phase drift (J_a + J_b orthogonal mixers)
      - Stateless teleport probability (entropy-gated)
      - Optional CSPRNG augmentation (reproducible by default)

    Args:
        k: Current scalar state.
        t: Step counter (for deterministic ancilla).
        seed: Base seed (32+ bytes).
        dk: Offset constant.
        alpha: Primary drift scale.
        gamma: Cubic drift scale.
        c: Constant term.
        n: Modulus (confinement).
        r: Radius or context parameter (used by redshift).
        redshift: Function r → z (integer scaling factor).
        J: Function k → Ja (primary drift).
        sign: Function x → ±1 (sign function).
        teleport_share: Function (k, k_anc, anc, G, n, U16) → (G', k_new).
        k_anc: Optional ancilla scalar (for teleport_share).
        G: Optional group element (for teleport_share).
        alpha2: Secondary drift scale (default = alpha).
        p0: Base teleport probability (default 0.03).
        use_real_rng: If True, augment ancilla with OS CSPRNG (default False).

    Returns:
        Next scalar k_{t+1} = (next_base ± teleport) mod n.

    Design principles:
        - Bounded: confinement by mod n
        - Stateless: no history, no profiling
        - Auditable: all operations deterministic (when use_real_rng=False)
        - Hybrid: combines local drift + nonlocal jumps
        - Entropy-aware: adapts teleport to mixing quality

    No learning, optimization, or personalization.
    """
    if alpha2 is None:
        alpha2 = alpha  # Default: same scale for second drift

    z = redshift(r)  # Integer-compatible redshift factor

    # Primary drift source (nonlinear, cubed)
    Ja = J(k)
    delta_j = int(Ja * alpha * (1 + z) * sign(Ja)) >> 32
    delta_j4 = int((Ja * Ja * Ja) * gamma * (1 + z)) >> 32

    # Secondary drift source (orthogonal)
    Jb = Jb_from_k(k)
    delta_b = int(Jb * alpha2 * (1 + z)) >> 32

    # Deterministic ancilla (or hybrid if use_real_rng)
    anc = hybrid_ancilla16(seed, t, use_real_rng=use_real_rng)

    # Base step: local deterministic transition
    k_new = (k + dk + delta_j + delta_b + delta_j4 + c) % n

    # Stateless teleport probability from local entropy proxy
    p_tp = p_tp_state(k, Ja, Jb, p0=p0)

    # Deterministic "coin flip" from ancilla (no random call)
    do_tp = (anc / (U16 - 1)) < p_tp

    # Apply teleport if selected and resources available
    if do_tp and k_anc is not None and G is not None:
        _, k_new = teleport_share(k, k_anc, anc, G, n, U16)

    return k_new


__all__ = [
    "ancilla16",
    "real_rng_u16",
    "hybrid_ancilla16",
    "mix64",
    "Jb_from_k",
    "entropy_proxy_0_1",
    "p_tp_state",
    "enhanced_F_k_v2",
    "U16",
]
