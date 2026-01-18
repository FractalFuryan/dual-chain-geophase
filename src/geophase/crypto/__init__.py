"""
geophase.crypto: Cryptographic primitives and utilities.

Modules:
  - rfc6979: Deterministic ECDSA nonce generation (RFC6979) for secp256k1
"""

from geophase.crypto.rfc6979 import (
    rfc6979_generate_k_secp256k1,
    sign_with_rfc6979,
    verify_signature,
    pubkey_from_privkey,
    CURVE_ORDER,
)

__all__ = [
    "rfc6979_generate_k_secp256k1",
    "sign_with_rfc6979",
    "verify_signature",
    "pubkey_from_privkey",
    "CURVE_ORDER",
]
