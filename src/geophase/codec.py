"""
codec.py: AEAD (ChaCha20-Poly1305) and ECC placeholder.

Provides:
  - ChaCha20-Poly1305 for confidentiality + integrity
  - KDF for deterministic per-block key derivation
  - Placeholder for Reed-Solomon ECC (T4)
"""

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from hashlib import sha256
import os

# Constants
KEY_LEN = 32      # 256-bit key for ChaCha20
NONCE_LEN = 12    # RFC 8439 standard nonce length


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


def ecc_encode(message: bytes, redundancy: int = 32) -> bytes:
    """
    Encode message with error-correcting code.
    
    Args:
        message: Raw message bytes.
        redundancy: Number of redundancy bytes (placeholder).
    
    Returns:
        Encoded message with ECC parity.
    
    TODO: Implement Reed-Solomon or similar.
    """
    # Placeholder: return message as-is
    return message


def ecc_decode(encoded: bytes, num_errors: int = 0) -> bytes:
    """
    Decode message with error correction.
    
    Args:
        encoded: Encoded message bytes.
        num_errors: Expected number of error bytes (for statistics).
    
    Returns:
        Decoded message (or None if unrecoverable).
    
    TODO: Implement Reed-Solomon or similar.
    """
    # Placeholder: return encoded as-is
    return encoded


def carrier_embed(ciphertext: bytes, ecc_redundancy: int = 32, padding: int = 1024) -> bytes:
    """
    Embed AEAD ciphertext into noise-tolerant carrier.
    
    Args:
        ciphertext: AEAD ciphertext bytes.
        ecc_redundancy: ECC redundancy bytes.
        padding: Additional padding bytes.
    
    Returns:
        Carrier bytes (ECC-encoded + padding).
    
    TODO: Implement interleaving and real ECC.
    """
    # Placeholder: return ciphertext + padding
    import os
    return ciphertext + os.urandom(padding)


def carrier_extract(carrier: bytes, ciphertext_len: int) -> bytes:
    """
    Extract AEAD ciphertext from carrier.
    
    Args:
        carrier: Carrier bytes.
        ciphertext_len: Expected ciphertext length.
    
    Returns:
        Extracted ciphertext (or None if unrecoverable).
    
    TODO: Implement ECC decoding and validation.
    """
    # Placeholder: extract first N bytes
    return carrier[:ciphertext_len]
