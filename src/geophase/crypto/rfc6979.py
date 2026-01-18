"""
rfc6979.py: RFC6979 deterministic ECDSA nonce generation + signing.

Implements RFC 6979 (Deterministic ECDSA) for secp256k1 using HMAC-SHA256.

Key Properties:
  - Fully deterministic: same (privkey, msg_hash, extra) → same nonce
  - No bias: rejects k outside [1, q-1] rather than reducing modulo
  - Low-S normalization: signatures have canonical form (s ≤ n/2)
  - Domain separation: optional 'extra' parameter for domain binding (e.g., Snake/Tetris/Zeta)

Security Model:
  - Nonce generation follows RFC 6979 strictly (no shortcuts)
  - Extra bytes are for domain separation ONLY (not entropy)
  - Signatures are deterministic and reproducible
  - Per-event uniqueness requires nonce in the message, not in RNG

References:
  - RFC 6979: https://tools.ietf.org/html/rfc6979
  - secp256k1: https://en.wikipedia.org/wiki/Secp256k1
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Tuple

try:
    from ecdsa import SigningKey, VerifyingKey, SECP256k1
    from ecdsa.util import sigencode_der, sigdecode_der
    HAS_ECDSA = True
except ImportError:
    HAS_ECDSA = False
    SECP256k1 = None  # type: ignore


# secp256k1 curve parameters
# Lazy initialization: only computed when ecdsa is available
CURVE_ORDER = SECP256k1.order if HAS_ECDSA else 2**256 - 2**32 - 977  # secp256k1 order (q)


def _hmac_sha256(key: bytes, data: bytes) -> bytes:
    """HMAC-SHA256."""
    return hmac.new(key, data, hashlib.sha256).digest()


def _int2octets(x: int, rolen: int) -> bytes:
    """Convert integer to octets (big-endian, zero-padded to rolen)."""
    return x.to_bytes(rolen, "big")


def _bits2int(b: bytes, qlen: int) -> int:
    """
    Convert bit sequence to integer (RFC 6979, step 2e).
    If bits exceed qlen, right-shift to align.
    """
    i = int.from_bytes(b, "big")
    blen = len(b) * 8
    if blen > qlen:
        i >>= (blen - qlen)
    return i


def _bits2octets(b: bytes, q: int, qlen: int, rolen: int) -> bytes:
    """
    Convert bit sequence to octets (RFC 6979, step 3a).
    Compute z1 = bits2int(b), then z2 = z1 mod q, then int2octets(z2).
    """
    z1 = _bits2int(b, qlen)
    z2 = z1 % q
    return _int2octets(z2, rolen)


def rfc6979_generate_k_secp256k1(
    priv_int: int, hash_bytes: bytes, extra: bytes = b""
) -> int:
    """
    Generate RFC6979 deterministic nonce k for ECDSA over secp256k1.

    Args:
        priv_int: Private key (scalar in [1, q-1]).
        hash_bytes: Hash of message (e.g., SHA256(message)).
        extra: Optional domain separation bytes (hashed internally if provided).

    Returns:
        Nonce k in [1, q-1], deterministic and rejection-free.

    Raises:
        ValueError: If priv_int is out of range or ecdsa package not installed.

    Notes:
        - hash_bytes should be the result of a cryptographic hash (e.g., SHA256)
        - extra is domain separation only; it does not add entropy
        - Same (priv_int, hash_bytes, extra) always produces the same k
        - Requires 'ecdsa' package: pip install ecdsa
    """
    if not HAS_ECDSA:
        raise ImportError(
            "rfc6979 requires 'ecdsa' package. Install: pip install ecdsa"
        )
    
    if not (1 <= priv_int < CURVE_ORDER):
        raise ValueError(f"Private key out of range: {priv_int}")

    q = CURVE_ORDER
    qlen = q.bit_length()
    rolen = (qlen + 7) // 8  # round up to nearest byte
    holen = hashlib.sha256().digest_size  # 32 for SHA256

    # Step D: process private key and message hash
    bx = _int2octets(priv_int, rolen)
    bh = _bits2octets(hash_bytes, q, qlen, rolen)

    # Step E: HMAC initialization
    V = b"\x01" * holen
    K = b"\x00" * holen

    # Optional: hash extra for domain separation
    extra_h = hashlib.sha256(extra).digest() if extra else b""

    # Step D (RFC 6979 section 3.2d): Set K and V
    K = _hmac_sha256(K, V + b"\x00" + bx + bh + extra_h)
    V = _hmac_sha256(K, V)

    # Step F (RFC 6979 section 3.2f): Update K and V again
    K = _hmac_sha256(K, V + b"\x01" + bx + bh + extra_h)
    V = _hmac_sha256(K, V)

    # Step H (RFC 6979 section 3.2h): Generate candidate k
    while True:
        T = b""
        while len(T) < rolen:
            V = _hmac_sha256(K, V)
            T += V

        k = _bits2int(T, qlen)

        # Reject if k not in [1, q-1]; loop and regenerate
        if 1 <= k < q:
            return k

        # k out of range: update K and V, try again
        K = _hmac_sha256(K, V + b"\x00")
        V = _hmac_sha256(K, V)


def _low_s(r: int, s: int, n: int) -> Tuple[int, int]:
    """
    Normalize signature to low-S form (s ≤ n/2).

    This ensures canonical signatures compatible with Bitcoin/Ethereum
    and other systems that enforce low-S normalization.

    Args:
        r: Signature r component.
        s: Signature s component.
        n: Curve order.

    Returns:
        (r, s_normalized) where s_normalized ≤ n/2.
    """
    if s > n // 2:
        s = n - s
    return r, s


def _encode_der_int(x: int) -> bytes:
    """Encode an integer to DER format (tag 0x02, length, value)."""
    # Convert to big-endian bytes, omitting leading zeros
    if x == 0:
        b = b"\x00"
    else:
        b = x.to_bytes((x.bit_length() + 7) // 8, "big")

    # Add leading 0x00 if high bit is set (to indicate positive integer)
    if b[0] & 0x80:
        b = b"\x00" + b

    return b"\x02" + bytes([len(b)]) + b


def _encode_der_sequence(r: int, s: int) -> bytes:
    """Encode (r, s) as DER SEQUENCE."""
    rb = _encode_der_int(r)
    sb = _encode_der_int(s)
    seq_content = rb + sb
    return b"\x30" + bytes([len(seq_content)]) + seq_content


def sign_with_rfc6979(
    priv_int: int, msg: bytes, extra: bytes = b""
) -> bytes:
    """
    Create DER-encoded ECDSA signature with RFC6979 nonce and low-S normalization.

    Args:
        priv_int: Private key (scalar in [1, q-1]).
        msg: Message to sign (any bytes).
        extra: Optional domain separation (e.g., b"ZETA_V1|commitment_hash").

    Returns:
        DER-encoded signature bytes.

    Raises:
        ImportError: If ecdsa package is not installed.

    Design:
        1. Hash message with SHA256
        2. Generate deterministic k via RFC6979
        3. Sign with ecdsa library using the provided k
        4. Normalize s to low form
        5. Re-encode as DER SEQUENCE

    Notes:
        - Signature is deterministic: same (priv_int, msg, extra) → same signature
        - Low-S normalization ensures canonical form
        - Extra is for domain separation, not entropy
        - Requires 'ecdsa' package: pip install ecdsa
    """
    if not HAS_ECDSA:
        raise ImportError(
            "rfc6979 requires 'ecdsa' package. Install: pip install ecdsa"
        )
    # Step 1: Hash message
    z = hashlib.sha256(msg).digest()

    # Step 2: Generate deterministic k
    k = rfc6979_generate_k_secp256k1(priv_int, z, extra=extra)

    # Step 3: Sign using ecdsa library with fixed k
    sk = SigningKey.from_secret_exponent(priv_int, curve=SECP256k1)
    der_sig = sk.sign_digest(z, sigencode=sigencode_der, k=k)

    # Step 4: Decode, normalize low-S, re-encode
    r, s = sigdecode_der(der_sig, CURVE_ORDER)
    r, s = _low_s(r, s, CURVE_ORDER)
    normalized_der = _encode_der_sequence(r, s)

    return normalized_der


def verify_signature(pub_bytes: bytes, msg: bytes, sig_der: bytes) -> bool:
    """
    Verify DER-encoded ECDSA signature over secp256k1.

    Args:
        pub_bytes: Public key bytes (33-byte compressed or 65-byte uncompressed).
        msg: Original message.
        sig_der: DER-encoded signature.

    Returns:
        True if signature is valid, False otherwise.

    Raises:
        ImportError: If ecdsa package is not installed.

    Notes:
        - Does not check low-S normalization (accepts any valid s)
        - Safe to call on untrusted signatures
        - Requires 'ecdsa' package: pip install ecdsa
    """
    if not HAS_ECDSA:
        raise ImportError(
            "rfc6979 requires 'ecdsa' package. Install: pip install ecdsa"
        )
    try:
        vk = VerifyingKey.from_string(pub_bytes, curve=SECP256k1)
        z = hashlib.sha256(msg).digest()
        vk.verify_digest(sig_der, z, sigdecode=sigdecode_der)
        return True
    except Exception:
        return False


def pubkey_from_privkey(priv_int: int) -> bytes:
    """
    Derive secp256k1 public key from private key.

    Args:
        priv_int: Private key scalar in [1, q-1].

    Returns:
        Uncompressed 65-byte public key (0x04 + x + y).

    Raises:
        ImportError: If ecdsa package is not installed.
        ValueError: If private key is out of valid range.

    Notes:
        - Requires 'ecdsa' package: pip install ecdsa
    """
    if not HAS_ECDSA:
        raise ImportError(
            "rfc6979 requires 'ecdsa' package. Install: pip install ecdsa"
        )
    if not (1 <= priv_int < CURVE_ORDER):
        raise ValueError(f"Private key out of range: {priv_int}")

    sk = SigningKey.from_secret_exponent(priv_int, curve=SECP256k1)
    vk = sk.verifying_key
    return vk.to_string()  # 65 bytes uncompressed


__all__ = [
    "rfc6979_generate_k_secp256k1",
    "sign_with_rfc6979",
    "verify_signature",
    "pubkey_from_privkey",
    "CURVE_ORDER",
]
