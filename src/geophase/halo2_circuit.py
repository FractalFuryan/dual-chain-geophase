"""
halo2_circuit.py: Multi-step teleport proof in Halo2.

Proves a chain of scalar transformations using deterministic mixing:
  k_0 → k_1 → ... → k_m with Q_i = k_i * G

Constraints:
  1. Limb decomposition: k_i as 16×16-bit limbs
  2. U16 matrix multiply (mod 2^16 per limb)
  3. XOR with deterministic ancilla
  4. Optional redshift scaling
  5. Recomposition to next scalar
  6. EC mul: Q_i = k_i * G
  7. Final: Q_m = Q_target

Circuit Size:
  - Per step: ~800–1500 rows (dominated by ECC mul)
  - m steps: O(m) scaling
  - Typical (m=8): ~7–12k rows
  - With column overhead: 14–16k row setup

Design:
  - No "floor(|...|)" or undefined operations
  - Limb-first mixing (valid in field)
  - Deterministic ancilla (reproducible)
  - Selector bits for local vs teleport branches
  - Range constraints on all limbs/intermediate values
"""

from __future__ import annotations

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class LimbDecomposition:
    """16×16-bit limb representation of a scalar."""

    limbs: List[int]  # 16 limbs, each 16-bit
    scalar: int  # Reconstructed scalar

    def __post_init__(self):
        """Validate limbs are 16-bit."""
        if len(self.limbs) != 16:
            raise ValueError(f"Expected 16 limbs, got {len(self.limbs)}")
        for i, limb in enumerate(self.limbs):
            if not (0 <= limb < (1 << 16)):
                raise ValueError(f"Limb {i} out of 16-bit range: {limb}")

    @classmethod
    def from_scalar(cls, k: int, max_val: int = None) -> LimbDecomposition:
        """
        Decompose a scalar into 16 limbs (16-bit each).

        Args:
            k: Scalar value.
            max_val: Optional modulus check.

        Returns:
            LimbDecomposition with limbs and scalar.
        """
        limbs = []
        val = k
        for _ in range(16):
            limbs.append(val & 0xFFFF)
            val >>= 16

        if val != 0 and max_val is None:
            raise ValueError(f"Scalar {k} does not fit in 16×16-bit limbs")

        if max_val is not None:
            k_check = k % max_val
            recomp = cls(limbs, k_check)
        else:
            recomp = cls(limbs, k)

        return recomp

    def recompose(self) -> int:
        """Reconstruct scalar from limbs."""
        result = 0
        for i, limb in enumerate(self.limbs):
            result += limb << (16 * i)
        return result

    def recompose_mod(self, mod: int) -> int:
        """Reconstruct scalar from limbs mod m."""
        return self.recompose() % mod


@dataclass
class U16Matrix:
    """4×16 matrix for U16 mixing (in Z_2^16 ring, limb-wise)."""

    rows: List[List[int]]  # 16×16 matrix of coefficients

    def __post_init__(self):
        """Validate matrix shape."""
        if len(self.rows) != 16:
            raise ValueError(f"Expected 16 rows, got {len(self.rows)}")
        for i, row in enumerate(self.rows):
            if len(row) != 16:
                raise ValueError(f"Row {i}: expected 16 cols, got {len(row)}")

    @classmethod
    def identity(cls) -> U16Matrix:
        """16×16 identity matrix."""
        rows = [[0] * 16 for _ in range(16)]
        for i in range(16):
            rows[i][i] = 1
        return cls(rows)

    def multiply_limbs_mod(self, limbs: List[int], mod: int = 1 << 16) -> List[int]:
        """
        Multiply matrix by limb vector (mod 2^16 per limb).

        Args:
            limbs: 16-element limb vector.
            mod: Modulus per limb (default 2^16).

        Returns:
            Output limbs after matrix multiply.
        """
        if len(limbs) != 16:
            raise ValueError(f"Expected 16 limbs, got {len(limbs)}")

        result = []
        for row in self.rows:
            acc = sum(row[j] * limbs[j] for j in range(16))
            result.append(acc % mod)

        return result


@dataclass
class TeleportStep:
    """Single teleport step in the chain."""

    step_idx: int
    k_in: int  # Input scalar
    anc: int  # 16-bit ancilla (deterministic or hybrid)
    z_i: int  # Redshift scaling factor (small int or fixed-point)

    k_out: int  # Output scalar (computed)

    def __post_init__(self):
        """Validate ranges."""
        if not (0 <= self.anc < (1 << 16)):
            raise ValueError(f"Ancilla out of range: {self.anc}")
        if self.k_in < 0 or self.k_out < 0:
            raise ValueError("Scalars must be non-negative")


@dataclass
class TeleportChain:
    """Multi-step teleport chain proof."""

    m: int  # Number of steps
    modulus: int  # Scalar field modulus (typically 2^256 or Fr)
    steps: List[TeleportStep]

    def __post_init__(self):
        """Validate chain structure."""
        if len(self.steps) != self.m:
            raise ValueError(f"Expected {self.m} steps, got {len(self.steps)}")

    @classmethod
    def create(
        cls,
        k0: int,
        m: int,
        modulus: int,
        seed: bytes,
        transition_fn,
    ) -> TeleportChain:
        """
        Build a teleport chain by applying transition repeatedly.

        Args:
            k0: Initial scalar.
            m: Number of steps.
            modulus: Scalar field modulus.
            seed: Seed for deterministic ancilla.
            transition_fn: Function (k, t, seed) → (k_next, anc, z).

        Returns:
            TeleportChain with m steps.
        """
        steps = []
        k = k0
        for t in range(m):
            k_next, anc, z_i = transition_fn(k, t, seed)
            step = TeleportStep(t, k, anc, z_i, k_next)
            steps.append(step)
            k = k_next

        return cls(m, modulus, steps)

    def final_scalar(self) -> int:
        """Return final k_m."""
        if not self.steps:
            return 0
        return self.steps[-1].k_out

    def all_scalars(self) -> List[int]:
        """Return list [k_0, k_1, ..., k_m]."""
        result = [self.steps[0].k_in]
        for step in self.steps:
            result.append(step.k_out)
        return result


class TeleportProofSystem:
    """
    Halo2 circuit skeleton for multi-step teleport proof.

    This is a logical blueprint; actual gate wiring goes in a Halo2 circuit.
    """

    def __init__(self, m: int, modulus: int):
        """
        Initialize proof system.

        Args:
            m: Number of steps (compile-time constant).
            modulus: Scalar field modulus.
        """
        self.m = m
        self.modulus = modulus
        self.u16_matrix = U16Matrix.identity()  # Or real U16 matrix
        self.domain = b"teleport_chain"

    def synthesize_constraints(self, chain: TeleportChain) -> Dict[str, Any]:
        """
        Return constraint specification for Halo2 circuit.

        This is a logical description; actual synthesis requires Halo2 gates.

        Args:
            chain: Teleport chain to prove.

        Returns:
            Dict with constraint groups:
              - limb_decomp: k_i limb consistency
              - u16_mix: matrix multiply and XOR
              - recompose: next scalar consistency
              - ec_mul: Q_i = k_i * G (stubbed)
              - chaining: k_{i+1} = computed output
              - final_check: Q_m = Q_target
        """
        constraints = {
            "limb_decomp": [],
            "u16_mix": [],
            "recompose": [],
            "ec_mul": [],
            "chaining": [],
            "final_check": [],
        }

        for step in chain.steps:
            i = step.step_idx
            k_in = step.k_in
            anc = step.anc
            z_i = step.z_i
            k_out = step.k_out

            # Limb decompose k_i
            decomp_in = LimbDecomposition.from_scalar(k_in, self.modulus)

            # U16 mix
            mixed_limbs = self.u16_matrix.multiply_limbs_mod(decomp_in.limbs)

            # XOR with ancilla (limb-wise or single limb)
            xored_limbs = [lim ^ anc for lim in mixed_limbs]

            # Optional redshift scaling on first limb
            if z_i != 0:
                scale = 1 + z_i  # Example: z_i encodes (1+z_i)
                xored_limbs[0] = (xored_limbs[0] * scale) & 0xFFFF

            # Recompose
            decomp_out = LimbDecomposition(xored_limbs, 0)
            k_next_computed = decomp_out.recompose_mod(self.modulus)

            # Constraints
            constraints["limb_decomp"].append({
                "step": i,
                "limbs": decomp_in.limbs,
                "scalar": k_in,
            })

            constraints["u16_mix"].append({
                "step": i,
                "in_limbs": decomp_in.limbs,
                "out_limbs": mixed_limbs,
            })

            constraints["recompose"].append({
                "step": i,
                "out_limbs": xored_limbs,
                "scalar": k_next_computed,
            })

            constraints["chaining"].append({
                "step": i,
                "expected": k_out,
                "computed": k_next_computed,
                "modulus": self.modulus,
            })

            constraints["ec_mul"].append({
                "step": i,
                "scalar": k_out,
                # "point": Q_i (would be from witness)
            })

        constraints["final_check"] = {
            "final_scalar": chain.final_scalar(),
            # "final_point": Q_target (public input)
        }

        return constraints

    def estimate_rows(self) -> Dict[str, int]:
        """
        Estimate row count for each constraint group.

        These are rough bounds; actual numbers depend on gate optimization.

        Returns:
            Dict with per-constraint row estimates.
        """
        return {
            "limb_decomp_per_step": 16,  # 16 range checks
            "u16_mix_per_step": 32,  # 16 outputs, with carries
            "recompose_per_step": 16,  # 16 limb checks
            "ec_mul_per_step": 800,  # Dominates: scalar mul in curve
            "chaining_per_step": 2,  # Equality checks
            "final_check": 4,  # Final EC check
            "setup_overhead": 50,  # Selectors, lookups, etc.
            "total_per_step": 900,  # Rough
            "total_m_steps": self.m * 900,
        }


def proof_system_spec(m: int = 8, modulus: int = 2**256) -> Dict[str, Any]:
    """
    Specification for Halo2 teleport proof system.

    Args:
        m: Number of steps (default 8).
        modulus: Scalar field modulus (default 2^256).

    Returns:
        Full system specification (to be implemented in Halo2).
    """
    ps = TeleportProofSystem(m, modulus)
    return {
        "name": "MultiStepTeleportChain",
        "steps": m,
        "modulus": modulus,
        "row_estimate": ps.estimate_rows(),
        "public_inputs": {
            "Q_0": "Initial point",
            "Q_target": "Final point",
            "ancilla_seeds": "m×16-bit public ancillas",
            "redshift_indices": "m×optional redshift factors",
        },
        "witnesses": {
            "scalars": "k_0, ..., k_m (each in F_r)",
            "limbs": "16×16-bit decomposition per step",
            "mixed_limbs": "Intermediate after U16 mix",
            "xored_limbs": "After ancilla XOR",
        },
        "gates": {
            "limb_range": "Each limb in [0, 2^16)",
            "u16_multiply": "Field-native matrix multiply mod 2^16",
            "xor_lookup": "Lookup table for 16-bit XOR",
            "recompose": "Consistency of scalar from limbs",
            "ec_mul": "halo2-ecc scalar mul gate (external)",
            "chaining": "k_{i+1} = computed(k_i)",
        },
        "lookups": {
            "xor_16bit": "Precomputed XOR table (2^32 entries, ~1MB)",
            "z_redshift": "Redshift function lookup (small, ~256 entries)",
        },
        "complexity_summary": {
            "rows_per_step": "~900 (ECC dominates)",
            "total_rows_m8": "~7200",
            "column_width": "8–12 columns",
            "time_estimate": "~1–2 seconds (m=8, standard hardware)",
            "proof_size": "~1–2 kB (Halo2 standard)",
        },
    }


__all__ = [
    "LimbDecomposition",
    "U16Matrix",
    "TeleportStep",
    "TeleportChain",
    "TeleportProofSystem",
    "proof_system_spec",
]
