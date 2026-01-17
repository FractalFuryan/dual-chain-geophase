"""
GeoPhase ↔ Ethereum commitment utilities.
Computes geoCommit hashes (privacy-safe, commitment-only).

Canonical commitment format (v1):
    geoCommit = keccak256(
        "ANANKE_GEO_COMMIT_V1" ||
        seed_commit ||
        phaseA_hash ||
        phaseB_hash ||
        policyId ||
        version_u32_be
    )
"""

import hashlib
from typing import Optional, Final
from dataclasses import dataclass


# Commit version constant (frozen)
GEO_COMMIT_VERSION: Final[int] = 1
PREFIX_V1: Final[bytes] = b"ANANKE_GEO_COMMIT_V1"


@dataclass
class GeoCommitParams:
    """Parameters for computing a GeoPhase commitment."""
    seed_commit: bytes  # sha256(seed || user_nonce)
    phaseA_hash: bytes  # sha256(phaseA_vector_bytes)
    phaseB_hash: bytes  # sha256(phaseB_vector_bytes)
    policy_id: bytes    # bytes32 policy identifier
    version: int        # protocol version (uint32)


def _validate_bytes32(b: bytes, name: str) -> bytes:
    """Validate 32-byte value."""
    if len(b) != 32:
        raise ValueError(f"{name} must be 32 bytes, got {len(b)}")
    return b


def compute_geo_commit(params: GeoCommitParams) -> bytes:
    """
    Compute the on-chain geoCommit key (canonical v1).
    
    Formula:
        geoCommit = keccak256(
            PREFIX_V1 ||
            seed_commit ||
            phaseA_hash ||
            phaseB_hash ||
            policyId ||
            version_u32_be
        )
    
    Returns:
        32-byte commitment hash (bytes32)
    
    Raises:
        ValueError: If any input is not 32 bytes or version out of range
    """
    from eth_utils import keccak
    
    # Validate all 32-byte inputs
    _validate_bytes32(params.seed_commit, "seed_commit")
    _validate_bytes32(params.phaseA_hash, "phaseA_hash")
    _validate_bytes32(params.phaseB_hash, "phaseB_hash")
    _validate_bytes32(params.policy_id, "policy_id")
    
    # Validate version range (uint32)
    if not (0 <= params.version <= 0xFFFFFFFF):
        raise ValueError(f"version must be uint32, got {params.version}")
    
    # Pack version as uint32 big-endian
    version_bytes = params.version.to_bytes(4, byteorder='big')
    
    # Concatenate all components (canonical order)
    preimage = (
        PREFIX_V1 +
        params.seed_commit +
        params.phaseA_hash +
        params.phaseB_hash +
        params.policy_id +
        version_bytes
    )
    
    # Keccak256 (Ethereum hash)
    return keccak(preimage)


def compute_seed_commit(seed: bytes, user_nonce: bytes) -> bytes:
    """
    Compute seed commitment: sha256(seed || user_nonce)
    
    Args:
        seed: Raw seed bytes
        user_nonce: User-specific nonce (32 bytes recommended)
    
    Returns:
        32-byte seed commitment
    """
    return hashlib.sha256(seed + user_nonce).digest()


def compute_phase_hash(phase_vector: bytes) -> bytes:
    """
    Compute phase vector hash: sha256(phase_vector_bytes)
    
    Args:
        phase_vector: Serialized phase vector
    
    Returns:
        32-byte phase hash
    """
    return hashlib.sha256(phase_vector).digest()


def compute_ethics_anchor(ethics_doc: str, timestamp: int) -> bytes:
    """
    Compute ethics anchor commitment.
    
    Args:
        ethics_doc: Ethics policy document (or URL/IPFS hash)
        timestamp: Unix timestamp of policy version
    
    Returns:
        32-byte ethics anchor hash
    """
    from eth_utils import keccak
    
    timestamp_bytes = timestamp.to_bytes(8, byteorder='big')
    preimage = ethics_doc.encode('utf-8') + timestamp_bytes
    return keccak(preimage)


def bytes32_to_hex(b: bytes) -> str:
    """Convert bytes32 to 0x-prefixed hex string."""
    return '0x' + b.hex()


def hex_to_bytes32(h: str) -> bytes:
    """Convert 0x-prefixed hex string to bytes32."""
    if h.startswith('0x'):
        h = h[2:]
    return bytes.fromhex(h)
