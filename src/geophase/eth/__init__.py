"""
GeoPhase Ethereum layer: EIP-712 PolicyGrant capability tokens.

This module provides wallet-native authentication with:
- EIP-712 typed data signatures (secp256k1)
- On-chain revocation checks (fail-closed)
- Mode & rights-based authorization
- No user identifiers or analytics storage
"""

from .policy_grant import Mode, Rights, PolicyGrant, VerifiedGrant
from .eip712_policy_grant import PolicyGrantVerifier, EIP712_TYPES
from .well_known import VerifierMetadata, as_json
from .fastapi_gate import GateConfig, ChainClientProtocol, build_gate_dependency

__all__ = [
    "Mode",
    "Rights",
    "PolicyGrant",
    "VerifiedGrant",
    "PolicyGrantVerifier",
    "EIP712_TYPES",
    "VerifierMetadata",
    "as_json",
    "GateConfig",
    "ChainClientProtocol",
    "build_gate_dependency",
]
