"""
compress.py: Structured compression codec.

Implements compression of structured state (not ciphertext).
Placeholder for 3–6–9 hierarchical compression; currently uses zlib-9.

TODO: Implement custom 3–6–9 codec for structured deltas.
"""

import zlib
from typing import Dict, Any


def compress_structured_state(structured_state: Dict[str, Any], level: int = 9) -> bytes:
    """
    Compress structured state using canonical JSON + zlib.
    
    Args:
        structured_state: Dictionary of structured state.
        level: zlib compression level (0–9).
    
    Returns:
        Compressed bytes.
    
    TODO: Swap zlib for custom 3–6–9 codec.
    """
    from .util import canonical_json
    canonical = canonical_json(structured_state)
    return zlib.compress(canonical, level=level)


def decompress_structured_state(compressed: bytes) -> Dict[str, Any]:
    """
    Decompress structured state.
    
    Args:
        compressed: Compressed bytes.
    
    Returns:
        Decompressed structured state dictionary.
    
    Raises:
        ValueError: If decompression fails.
    """
    import json
    try:
        canonical = zlib.decompress(compressed)
        return json.loads(canonical.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Decompression failed: {e}")


def estimate_compression_ratio(original_size: int, compressed_size: int) -> float:
    """
    Estimate compression ratio.
    
    Args:
        original_size: Original bytes.
        compressed_size: Compressed bytes.
    
    Returns:
        Compression ratio (0–1, lower is better).
    """
    if original_size == 0:
        return 0.0
    return compressed_size / original_size
