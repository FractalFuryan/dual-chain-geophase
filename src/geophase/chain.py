"""
chain.py: Commitment hash chain (H_t, A_t, and chain validation).

Implements:
  - H_prev: previous commitment hash (chaining)
  - g_t = H(D): structured state digest
  - A_t = H(H_prev || g_t || public_header): availability witness
  - H_t = H(H_prev || H(ct) || g_t): binding hash
"""

import hashlib
from typing import Optional, Dict, Any


def hash_sha256(data: bytes) -> bytes:
    """SHA-256 hash."""
    return hashlib.sha256(data).digest()


def commit_state_digest(structured_state: Dict[str, Any]) -> bytes:
    """
    Compute g_t = H(canonical(structured_state)).
    
    Args:
        structured_state: Dictionary of structured state.
    
    Returns:
        State digest bytes.
    """
    from .util import canonical_json
    return hash_sha256(canonical_json(structured_state))


def compute_availability_witness(
    H_prev: bytes, g_t: bytes, public_header: Dict[str, Any]
) -> bytes:
    """
    Compute A_t = H(H_prev || g_t || canonical(public_header)).
    
    Args:
        H_prev: Previous commitment hash.
        g_t: State digest.
        public_header: Public header dictionary.
    
    Returns:
        Availability witness bytes.
    """
    from .util import canonical_json
    data = H_prev + g_t + canonical_json(public_header)
    return hash_sha256(data)


def compute_binding_hash(H_prev: bytes, ct_hash: bytes, g_t: bytes) -> bytes:
    """
    Compute H_t = H(H_prev || H(ct) || g_t).
    
    Args:
        H_prev: Previous commitment hash.
        ct_hash: Hash of ciphertext H(ct).
        g_t: State digest.
    
    Returns:
        Binding hash bytes.
    """
    data = H_prev + ct_hash + g_t
    return hash_sha256(data)


def verify_commitment(
    H_t: bytes,
    A_t: bytes,
    H_prev: bytes,
    g_t: bytes,
    ct_hash: bytes,
    public_header: Dict[str, Any],
) -> bool:
    """
    Verify commitment chain: A_t and H_t correct?
    
    Args:
        H_t: Claimed binding hash.
        A_t: Claimed availability witness.
        H_prev: Previous commitment hash.
        g_t: State digest.
        ct_hash: Hash of ciphertext.
        public_header: Public header.
    
    Returns:
        True if commitments are valid.
    """
    A_t_chk = compute_availability_witness(H_prev, g_t, public_header)
    H_t_chk = compute_binding_hash(H_prev, ct_hash, g_t)
    return A_t == A_t_chk and H_t == H_t_chk
