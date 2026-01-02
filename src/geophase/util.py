"""
util.py: Utility functions for canonical JSON, base64, and hashing.
"""

import json
import base64
import hashlib
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
