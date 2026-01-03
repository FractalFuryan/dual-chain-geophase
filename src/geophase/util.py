"""
util.py: Utility functions for canonical JSON, base64, hashing, and interleaving.
"""

import json
import base64
import hashlib
import random
from typing import Dict, Any


def canonical_json(obj: Dict[str, Any]) -> bytes:
    """
    Serialize object to canonical JSON (sorted keys, minimal spacing).
    
    Args:
        obj: Dictionary to serialize.
    
    Returns:
        Canonical JSON bytes (UTF-8 encoded).
    """
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")


def b64_encode(data: bytes) -> str:
    """
    Encode bytes as URL-safe base64 string.
    
    Args:
        data: Bytes to encode.
    
    Returns:
        Base64 string (without padding).
    """
    return base64.b64encode(data).decode("utf-8")


def b64_decode(s: str) -> bytes:
    """
    Decode base64 string to bytes.
    
    Args:
        s: Base64 string.
    
    Returns:
        Decoded bytes.
    
    Raises:
        ValueError: If decoding fails.
    """
    try:
        return base64.b64decode(s)
    except Exception as e:
        raise ValueError(f"Base64 decode failed: {e}")


def hash_sha256(data: bytes) -> bytes:
    """
    Compute SHA-256 hash.
    
    Args:
        data: Bytes to hash.
    
    Returns:
        SHA-256 digest (32 bytes).
    """
    return hashlib.sha256(data).digest()


def hex_encode(data: bytes) -> str:
    """
    Encode bytes as hexadecimal string.
    
    Args:
        data: Bytes to encode.
    
    Returns:
        Hex string.
    """
    return data.hex()


def hex_decode(s: str) -> bytes:
    """
    Decode hexadecimal string to bytes.
    
    Args:
        s: Hex string.
    
    Returns:
        Decoded bytes.
    
    Raises:
        ValueError: If decoding fails.
    """
    try:
        return bytes.fromhex(s)
    except ValueError as e:
        raise ValueError(f"Hex decode failed: {e}")


def permute(data: bytes, seed_material: bytes) -> bytes:
    """
    Deterministically permute bytes using seed material (for ECC interleaving).
    
    Args:
        data: Bytes to permute.
        seed_material: Seed for deterministic shuffling.
    
    Returns:
        Permuted bytes (same length as input).
    
    Note: Deterministic permutation for transport layer robustness.
          Helps RS recovery under burst noise.
    """
    n = len(data)
    if n == 0:
        return data
    
    # Seed RNG with SHA-256(seed_material)
    idx = list(range(n))
    rng = random.Random(hashlib.sha256(seed_material).digest())
    rng.shuffle(idx)
    
    # Build permuted output
    out = bytearray(n)
    for i, j in enumerate(idx):
        out[i] = data[j]
    
    return bytes(out)


def unpermute(data: bytes, seed_material: bytes) -> bytes:
    """
    Reverse a deterministic permutation (inverse of permute()).
    
    Args:
        data: Permuted bytes.
        seed_material: Same seed used in permute().
    
    Returns:
        Original bytes (before permutation).
    """
    n = len(data)
    if n == 0:
        return data
    
    # Recreate the same index mapping
    idx = list(range(n))
    rng = random.Random(hashlib.sha256(seed_material).digest())
    rng.shuffle(idx)
    
    # Reverse the permutation
    out = bytearray(n)
    for i, j in enumerate(idx):
        out[j] = data[i]
    
    return bytes(out)


def permute(data: bytes, seed_material: bytes) -> bytes:
    """
    Deterministically permute bytes using seed material (for ECC interleaving).
    
    Args:
        data: Bytes to permute.
        seed_material: Seed for deterministic shuffling.
    
    Returns:
        Permuted bytes (same length as input).
    
    Note: Deterministic permutation for transport layer robustness.
          Helps RS recovery under burst noise.
    """
    n = len(data)
    if n == 0:
        return data
    
    # Seed RNG with SHA-256(seed_material)
    idx = list(range(n))
    rng = random.Random(hashlib.sha256(seed_material).digest())
    rng.shuffle(idx)
    
    # Build permuted output
    out = bytearray(n)
    for i, j in enumerate(idx):
        out[i] = data[j]
    
    return bytes(out)


def unpermute(data: bytes, seed_material: bytes) -> bytes:
    """
    Reverse a deterministic permutation (inverse of permute()).
    
    Args:
        data: Permuted bytes.
        seed_material: Same seed used in permute().
    
    Returns:
        Original bytes (before permutation).
    """
    n = len(data)
    if n == 0:
        return data
    
    # Recreate the same index mapping
    idx = list(range(n))
    rng = random.Random(hashlib.sha256(seed_material).digest())
    rng.shuffle(idx)
    
    # Reverse the permutation
    out = bytearray(n)
    for i, j in enumerate(idx):
        out[j] = data[i]
    
    return bytes(out)
