"""
GeoPhase: Dual-chain authenticated design package.

Modules:
  - codec:        ECC and carrier encoding/decoding
  - chain:        Commitment hash chain (H_t, A_t)
  - compress:     Structured compression (3–6–9 codec placeholder)
  - covenant:     AEAD-gated verification (sole acceptance gate)
  - util:         Utilities (canonical JSON, base64 helpers)
  - dual_phase:   Audit-only angular distance verification
  - param_vectors: Parameter vector generation for dual-phase audit
"""

__version__ = "0.2.0"
__author__ = "GeoPhase Contributors"

from geophase.covenant import VerifyResult, verify_gate
from geophase.dual_phase import cosine_similarity, cosine_buffer_ok
from geophase.param_vectors import param_vector_from_hash, dual_phase_vectors

__all__ = [
    "VerifyResult",
    "verify_gate",
    "cosine_similarity",
    "cosine_buffer_ok",
    "param_vector_from_hash",
    "dual_phase_vectors",
]
