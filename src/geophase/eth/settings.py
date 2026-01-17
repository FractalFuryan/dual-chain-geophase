"""
Fail-closed server settings.

STRICT_CHAIN=true: Refuse generation if RPC unreachable
STRICT_REVOCATION=true: Block on revocation check failure
BYTECODE_LOCK_ENABLED=true: Verify contract bytecode at boot
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _req(name: str) -> str:
    """Get required environment variable or raise."""
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def _opt(name: str, default: str) -> str:
    """Get optional environment variable with default."""
    return os.getenv(name, default)


def _opt_bool(name: str, default: bool) -> bool:
    """Parse boolean environment variable."""
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


@dataclass(frozen=True)
class Settings:
    """
    GeoPhase Ethereum bridge settings.
    
    Fail-closed by default:
    - STRICT_CHAIN: true (refuse if RPC down)
    - STRICT_REVOCATION: true (refuse if revocation check fails)
    - BYTECODE_LOCK_ENABLED: true (verify contract code at boot)
    """
    BASE_RPC_URL: str
    ATTESTATION_REGISTRY_ADDR: str
    REVOCATION_REGISTRY_ADDR: str
    CHAIN_ID: int = 8453  # Base L2

    # Fail-closed behaviors (default ON)
    STRICT_CHAIN: bool = True
    STRICT_REVOCATION: bool = True

    # Bytecode lock (recommended ON in production)
    BYTECODE_LOCK_ENABLED: bool = True
    ATTESTATION_BYTECODE_HASH: str | None = None
    REVOCATION_BYTECODE_HASH: str | None = None

    # Optional toggles
    ATTEST_ENABLED: bool = False

    @staticmethod
    def load() -> "Settings":
        """Load settings from environment variables."""
        return Settings(
            BASE_RPC_URL=_req("BASE_RPC_URL"),
            ATTESTATION_REGISTRY_ADDR=_req("ATTESTATION_REGISTRY_ADDR"),
            REVOCATION_REGISTRY_ADDR=_req("REVOCATION_REGISTRY_ADDR"),
            CHAIN_ID=int(_opt("CHAIN_ID", "8453")),
            STRICT_CHAIN=_opt_bool("STRICT_CHAIN", True),
            STRICT_REVOCATION=_opt_bool("STRICT_REVOCATION", True),
            BYTECODE_LOCK_ENABLED=_opt_bool("BYTECODE_LOCK_ENABLED", True),
            ATTESTATION_BYTECODE_HASH=_opt("ATTESTATION_BYTECODE_HASH", "") or None,
            REVOCATION_BYTECODE_HASH=_opt("REVOCATION_BYTECODE_HASH", "") or None,
            ATTEST_ENABLED=_opt_bool("ATTEST_ENABLED", False),
        )
