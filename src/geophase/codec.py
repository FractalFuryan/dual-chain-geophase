"""
codec.py: AEAD (ChaCha20-Poly1305) + Reed-Solomon ECC transport layer.

Provides:
  - ChaCha20-Poly1305 for confidentiality + integrity (AEAD is sole auth gate)
  - KDF for deterministic per-block key derivation
  - Reed-Solomon ECC for transport reliability (never decides acceptance)
  
Security Covenant:
  ACCEPT ⟺ AEAD_verify(ciphertext, AD) = true
  ECC is strictly a transport-layer repair mechanism.
"""

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from hashlib import sha256
from reedsolo import RSCodec, ReedSolomonError
import os

# Constants
KEY_LEN = 32      # 256-bit key for ChaCha20
NONCE_LEN = 12    # RFC 8439 standard nonce length
TAG_LEN = 16      # Poly1305 tag length
NSYM = 64         # Reed-Solomon redundancy bytes (corrects up to 32 byte errors)


def kdf(master_key: bytes, t: int) -> bytes:
    """
    Deterministic per-block key derivation.
    
    Args:
        master_key: Base key (256-bit).
        t: Block counter.
    
    Returns:
        Derived key for block t (SHA-256 output).
    
    Note: Public-safe placeholder. Replace with HKDF for production.
    """
    return sha256(master_key + t.to_bytes(8, "big")).digest()


def encrypt(
    master_key: bytes,
    t: int,
    plaintext: bytes,
    associated_data: bytes,
    deterministic: bool = True,
) -> bytes:
    """
    ChaCha20-Poly1305 authenticated encryption.
    
    Args:
        master_key: Base encryption key (256-bit).
        t: Block counter for KDF.
        plaintext: Message to encrypt.
        associated_data: Additional authenticated data (AD).
        deterministic: If True, derive nonce from t (for testing).
                      If False, use random nonce (production).
    
    Returns:
        nonce (12 bytes) || ciphertext || tag (16 bytes).
    
    Note: For T1 determinism, nonce is derived from t.
          For production, set deterministic=False for random nonces.
    """
    key = kdf(master_key, t)
    
    if deterministic:
        # For testing: derive nonce deterministically from t
        nonce_material = sha256(b"NONCE" + master_key + t.to_bytes(8, "big")).digest()
        nonce = nonce_material[:NONCE_LEN]
    else:
        # For production: random nonce (true misuse resistance)
        nonce = os.urandom(NONCE_LEN)
    
    aead = ChaCha20Poly1305(key)
    ct = aead.encrypt(nonce, plaintext, associated_data)
    return nonce + ct


def decrypt(
    master_key: bytes,
    t: int,
    ciphertext: bytes,
    associated_data: bytes,
) -> bytes:
    """
    ChaCha20-Poly1305 authenticated decryption.
    
    Args:
        master_key: Base encryption key (256-bit).
        t: Block counter for KDF.
        ciphertext: nonce (12 bytes) || ct || tag (16 bytes).
        associated_data: Additional authenticated data (must match encrypt).
    
    Returns:
        Plaintext if MAC is valid.
    
    Raises:
        cryptography.exceptions.InvalidTag: If MAC verification fails.
    """
    key = kdf(master_key, t)
    nonce = ciphertext[:NONCE_LEN]
    ct = ciphertext[NONCE_LEN:]
    aead = ChaCha20Poly1305(key)
    return aead.decrypt(nonce, ct, associated_data)


def ecc_encode(payload: bytes) -> bytes:
    """
    Reed-Solomon encode payload with redundancy.
    
    Args:
        payload: Bytes to encode.
    
    Returns:
        Encoded bytes: payload || parity (length = len(payload) + NSYM).
    
    Note: Encodes payload as-is. Can correct up to NSYM//2 errors.
    """
    rs = RSCodec(NSYM)
    return bytes(rs.encode(payload))


def ecc_decode(codeword: bytes) -> bytes:
    """
    Reed-Solomon decode codeword, correcting errors if possible.
    
    Args:
        codeword: Encoded bytes with ECC parity.
    
    Returns:
        Decoded message, or empty bytes if unrecoverable.
    
    Security: ECC may output garbage on decoding failure.
              AEAD gate (verify_gate) must verify the output before accepting.
    """
    rs = RSCodec(NSYM)
    try:
        # reedsolo.decode returns (msg, ecc, errata_pos)
        decoded, ecc, errata_pos = rs.decode(codeword)
        return bytes(decoded)
    except ReedSolomonError:
        # Cannot recover; return empty to force AEAD rejection
        return b""
