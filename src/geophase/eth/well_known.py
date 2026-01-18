"""
Well-known metadata endpoint for GeoPhase verifier configuration.

Provides a standard /.well-known/geophase-verifier.json endpoint
for clients to discover EIP-712 domain parameters and registry addresses.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import List


@dataclass(frozen=True)
class VerifierMetadata:
    """
    Metadata for GeoPhase EIP-712 verifier discovery.

    This structure is served at /.well-known/geophase-verifier.json
    to allow clients to discover the correct domain parameters,
    registry addresses, and policy identifiers.
    """
    eip712_name: str
    eip712_version: str
    chain_id: int
    verifying_contract: str
    attestation_registry: str
    revocation_registry: str
    bytecode_lock_hash: str  # optional but recommended for trust anchoring
    ethics_anchor: str  # hash of ethics policy document
    policy_ids: List[str]  # list of bytes32 hex policy identifiers


def as_json(meta: VerifierMetadata) -> dict:
    """
    Convert VerifierMetadata to JSON-serializable dictionary.

    Args:
        meta: VerifierMetadata instance

    Returns:
        Dictionary suitable for JSON serialization
    """
    return asdict(meta)
