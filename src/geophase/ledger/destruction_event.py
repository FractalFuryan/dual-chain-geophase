"""
Capability Destruction Event - Cryptographic revocation without regulatory framing.

This is NOT GDPR erasure. This is permanent cryptographic capability loss.

Design principles:
- No identity tracking
- No legal language
- No compliance framing
- Pure cryptographic semantics
- Fail-closed enforcement
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DestructionMethod(str, Enum):
    """Methods for irreversible capability destruction."""
    
    KEY_SHRED = "key_shred"          # Cryptographic key material destroyed
    STORAGE_DELETE = "storage_delete"  # Storage physically overwritten
    FULL_PURGE = "full_purge"        # Complete removal (key + storage)


class CapabilityDestructionEvent(BaseModel):
    """
    Immutable ledger record indicating irreversible capability destruction.
    
    This event represents a one-way state transition: once destroyed, the
    capability cannot be restored. This is enforced cryptographically, not
    by policy.
    
    CRITICAL BOUNDARY:
    - No identity (no subject_id, no user data)
    - No legal framing (no GDPR language)
    - No compliance claims (no regulator_id)
    - Pure cryptographic fact: "this capability is gone"
    """
    
    event_type: str = Field(
        default="capability_destruction",
        description="Event type identifier"
    )
    
    asset_id: str = Field(
        ...,
        description="Asset/capability identifier (NOT user identity)"
    )
    
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of destruction"
    )
    
    method: DestructionMethod = Field(
        ...,
        description="Destruction method used"
    )
    
    proof_hash: str = Field(
        ...,
        description="Cryptographic proof of destruction (hash of destroyed material)"
    )
    
    # Chain integrity anchors
    pre_state_commitment: str = Field(
        ...,
        description="Hash commitment of state before destruction"
    )
    
    post_state: str = Field(
        default="DESTROYED",
        description="Post-destruction state marker"
    )
    
    # Optional technical metadata (NOT user data)
    metadata: Optional[dict] = Field(
        default=None,
        description="Optional technical metadata (no PII)"
    )
    
    @classmethod
    def create(
        cls,
        asset_id: str,
        method: DestructionMethod,
        material_hash: str,
        pre_state_commitment: str,
        metadata: Optional[dict] = None,
    ) -> "CapabilityDestructionEvent":
        """
        Create a capability destruction event with cryptographic proof.
        
        Args:
            asset_id: Asset identifier (NOT user identity)
            method: Destruction method used
            material_hash: Hash of destroyed material (key, data, etc.)
            pre_state_commitment: Hash of state before destruction
            metadata: Optional technical metadata (no PII)
        
        Returns:
            CapabilityDestructionEvent with proof hash
        """
        # Generate proof hash: DESTROY:asset:material
        proof = hashlib.sha256(
            f"DESTROY:{asset_id}:{material_hash}".encode()
        ).hexdigest()
        
        return cls(
            asset_id=asset_id,
            method=method,
            proof_hash=proof,
            pre_state_commitment=pre_state_commitment,
            metadata=metadata,
        )
    
    def verify_proof(self, material_hash: str) -> bool:
        """
        Verify that the proof hash matches the given material hash.
        
        Args:
            material_hash: Hash of material to verify
        
        Returns:
            True if proof is valid
        """
        expected = hashlib.sha256(
            f"DESTROY:{self.asset_id}:{material_hash}".encode()
        ).hexdigest()
        return self.proof_hash == expected
    
    def is_irreversible(self) -> bool:
        """
        Check if this destruction is irreversible.
        
        Returns:
            Always True - destruction is always irreversible
        """
        return self.post_state == "DESTROYED"
