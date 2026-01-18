"""
PolicyGrant capability token model.

CRITICAL BOUNDARY:
- seed_family_id is a procedural selection token (e.g., "my-vibe"), NOT identity/likeness
- No biometric inputs, no resemblance targets
- "Make it like me" = procedural seed-family token, not likeness
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class Mode(IntEnum):
    """Generation mode enumeration."""
    STANDARD = 0
    CLINICAL = 1


class Rights(IntEnum):
    """Rights bitflags for capability authorization."""
    # bitflags
    FRAME = 1 << 0
    VIDEO = 1 << 1
    MP4 = 1 << 2
    STREAM = 1 << 3
    # extend safely; never tie to realism tiers or engagement


def _is_hex_bytes32(s: str) -> bool:
    """Validate that a string is a 0x-prefixed 32-byte hex value."""
    if not isinstance(s, str):
        return False
    if not s.startswith("0x") or len(s) != 66:
        return False
    try:
        int(s[2:], 16)
        return True
    except ValueError:
        return False


class PolicyGrant(BaseModel):
    """
    Capability token: permission to generate for a specific geo_commit under a policy.

    IMPORTANT BOUNDARY:
    - seed_family_id is a *procedural selection token* (e.g., "my-vibe"), not identity/likeness.
    - No biometric inputs, no resemblance targets.
    """
    commit: str = Field(..., description="bytes32 hex (0x...) of geo_commit")
    policy_id: str = Field(..., description="bytes32 hex of policy identifier (keccak256 of policy string)")
    mode: int = Field(default=int(Mode.STANDARD))
    rights: int = Field(default=int(Rights.FRAME))
    exp: int = Field(..., description="unix seconds expiry")
    nonce: str = Field(..., description="bytes32 hex anti-replay / domain separation")
    engine_version: int = Field(default=1, description="protocol/engine version")
    seed_family_id: Optional[str] = Field(
        default=None,
        description="Optional procedural seed-family label (NOT identity/likeness)."
    )

    @field_validator("commit", "policy_id", "nonce")
    @classmethod
    def _validate_bytes32(cls, v: str) -> str:
        if not _is_hex_bytes32(v):
            raise ValueError("must be 0x + 32-byte hex (66 chars)")
        return v.lower()

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, v: int) -> int:
        if v not in (int(Mode.STANDARD), int(Mode.CLINICAL)):
            raise ValueError("invalid mode")
        return v

    @field_validator("rights")
    @classmethod
    def _validate_rights(cls, v: int) -> int:
        if v < 0 or v > (1 << 31):
            raise ValueError("invalid rights bitmask")
        return v

    def to_eip712_message(self) -> Dict[str, Any]:
        """
        Convert to EIP-712 typed message.
        
        Only include fields that are part of the typed message.
        seed_family_id is NOT included in signature by default to avoid creating identity-like coupling.
        """
        return {
            "commit": self.commit,
            "policy_id": self.policy_id,
            "mode": int(self.mode),
            "rights": int(self.rights),
            "exp": int(self.exp),
            "nonce": self.nonce,
            "engine_version": int(self.engine_version),
        }


@dataclass(frozen=True)
class VerifiedGrant:
    """A verified PolicyGrant with recovered signer address."""
    signer: str  # 0x... recovered address
    grant: PolicyGrant
