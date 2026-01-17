"""
EIP-712 "Make it like me" procedural authorization.
Server-side signature verification (no likeness, only procedural preset selection).
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import time


@dataclass
class ProceduralAuthMessage:
    """EIP-712 message for procedural preset authorization."""
    seed_commit: bytes    # bytes32
    mode: int            # uint8 (0=standard, 1=clinical, etc.)
    preset: int          # uint16 (procedural "vibe selector")
    expires: int         # uint64 (unix timestamp)
    nonce: bytes         # bytes32 (anti-replay)


# EIP-712 Domain
DOMAIN = {
    "name": "AnankeGeoPhase",
    "version": "1",
    "chainId": 8453,  # Base mainnet
    "verifyingContract": None,  # Set at runtime from config
}

# EIP-712 Types
TYPES = {
    "EIP712Domain": [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
        {"name": "chainId", "type": "uint256"},
        {"name": "verifyingContract", "type": "address"},
    ],
    "ProceduralAuth": [
        {"name": "seedCommit", "type": "bytes32"},
        {"name": "mode", "type": "uint8"},
        {"name": "preset", "type": "uint16"},
        {"name": "expires", "type": "uint64"},
        {"name": "nonce", "type": "bytes32"},
    ],
}


def set_verifying_contract(address: str):
    """Set the verifying contract address (attestation registry or service contract)."""
    global DOMAIN
    DOMAIN["verifyingContract"] = address


def create_procedural_auth_message(
    seed_commit: bytes,
    mode: int,
    preset: int,
    expires: int,
    nonce: bytes
) -> Dict[str, Any]:
    """
    Create EIP-712 typed message for procedural authorization.
    
    Args:
        seed_commit: 32-byte seed commitment
        mode: uint8 mode selector
        preset: uint16 procedural preset selector
        expires: unix timestamp (uint64)
        nonce: 32-byte anti-replay nonce
    
    Returns:
        EIP-712 typed data dict
    """
    message = {
        "seedCommit": '0x' + seed_commit.hex(),
        "mode": mode,
        "preset": preset,
        "expires": expires,
        "nonce": '0x' + nonce.hex(),
    }
    
    return {
        "domain": DOMAIN,
        "types": TYPES,
        "primaryType": "ProceduralAuth",
        "message": message,
    }


def verify_procedural_auth(
    message: Dict[str, Any],
    signature: str,
    expected_addr: str
) -> bool:
    """
    Verify EIP-712 signature for procedural authorization.
    
    Args:
        message: Message dict (seedCommit, mode, preset, expires, nonce)
        signature: Hex-encoded signature (0x-prefixed)
        expected_addr: Expected signer address (0x-prefixed)
    
    Returns:
        True if signature is valid and not expired
    """
    from eth_account import Account
    from eth_account.messages import encode_typed_data
    
    # Check expiration
    if int(message["expires"]) < int(time.time()):
        return False
    
    # Build typed data
    typed_data = {
        "domain": DOMAIN,
        "types": TYPES,
        "primaryType": "ProceduralAuth",
        "message": message,
    }
    
    # Encode and recover signer
    try:
        signable = encode_typed_data(full_message=typed_data)
        recovered = Account.recover_message(signable, signature=signature)
        return recovered.lower() == expected_addr.lower()
    except Exception as e:
        print(f"EIP-712 verification failed: {e}")
        return False


def generate_nonce() -> bytes:
    """Generate a random 32-byte nonce for anti-replay."""
    import secrets
    return secrets.token_bytes(32)
