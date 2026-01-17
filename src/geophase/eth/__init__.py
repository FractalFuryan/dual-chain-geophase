"""Ethereum bridge for GeoPhase commitments (Base L2)."""

from .geocommit import (
    GeoCommitParams,
    compute_geo_commit,
    compute_seed_commit,
    compute_phase_hash,
    compute_ethics_anchor,
    bytes32_to_hex,
    hex_to_bytes32,
)

from .eip712_verify import (
    ProceduralAuthMessage,
    create_procedural_auth_message,
    verify_procedural_auth,
    set_verifying_contract,
    generate_nonce,
)

from .chain_check import (
    ChainConfig,
    ChainClient,
    load_config_from_env,
)

__all__ = [
    # Commitment utils
    "GeoCommitParams",
    "compute_geo_commit",
    "compute_seed_commit",
    "compute_phase_hash",
    "compute_ethics_anchor",
    "bytes32_to_hex",
    "hex_to_bytes32",
    
    # EIP-712
    "ProceduralAuthMessage",
    "create_procedural_auth_message",
    "verify_procedural_auth",
    "set_verifying_contract",
    "generate_nonce",
    
    # Chain interaction
    "ChainConfig",
    "ChainClient",
    "load_config_from_env",
]
