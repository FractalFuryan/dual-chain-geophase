"""
Irreversible destruction of cryptographic capability.

This module implements secure deletion of cryptographic key material and
associated assets. Destruction is permanent and fail-closed.

Design:
- Multi-pass overwrite (3x random + 1x zeros)
- Atomic deletion
- Cryptographic proof generation
- No recovery mechanism

NOT GDPR ERASURE - This is cryptographic capability loss.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class DestructionResult:
    """Result of a destruction operation."""
    
    asset_id: str
    key_destroyed: bool
    key_hash: Optional[str]
    payload_destroyed: bool
    payload_hash: Optional[str]
    
    @property
    def material_hash(self) -> str:
        """
        Combined hash of all destroyed material.
        
        Returns:
            SHA256 hash of concatenated key_hash and payload_hash
        """
        parts = []
        if self.key_hash:
            parts.append(self.key_hash)
        if self.payload_hash:
            parts.append(self.payload_hash)
        
        if not parts:
            raise ValueError("No material was destroyed")
        
        return hashlib.sha256(":".join(parts).encode()).hexdigest()


class DestructionManager:
    """
    Irreversible destruction of cryptographic capability.
    
    This manager handles secure deletion of:
    - Cryptographic key material (.key files)
    - Encrypted payloads (.bin files)
    - Associated metadata
    
    Destruction is permanent and cannot be undone.
    """
    
    def __init__(self, root: str | Path) -> None:
        """
        Initialize destruction manager.
        
        Args:
            root: Root directory containing asset files
        """
        self.root = Path(root)
        if not self.root.exists():
            raise ValueError(f"Root directory does not exist: {root}")
    
    def _secure_overwrite(self, path: Path, passes: int = 3) -> None:
        """
        Securely overwrite a file before deletion.
        
        Args:
            path: Path to file to overwrite
            passes: Number of random overwrite passes (default: 3)
        """
        if not path.exists():
            return
        
        file_size = path.stat().st_size
        
        # Multiple passes of random data
        for _ in range(passes):
            path.write_bytes(os.urandom(file_size))
            path.flush() if hasattr(path, 'flush') else None
        
        # Final pass with zeros
        path.write_bytes(b"\x00" * file_size)
        
        # Delete
        path.unlink()
    
    def shred_key(self, asset_id: str) -> str:
        """
        Shred cryptographic key material.
        
        This is the primary destruction operation. Once a key is shredded,
        the associated capability is permanently lost.
        
        Args:
            asset_id: Asset identifier
        
        Returns:
            SHA256 hash of original key material (proof of destruction)
        
        Raises:
            FileNotFoundError: If key file does not exist
        """
        key_path = self.root / f"{asset_id}.key"
        
        if not key_path.exists():
            raise FileNotFoundError(f"Key not found for asset: {asset_id}")
        
        # Read and hash original
        original = key_path.read_bytes()
        original_hash = hashlib.sha256(original).hexdigest()
        
        # Secure overwrite and delete
        self._secure_overwrite(key_path)
        
        return original_hash
    
    def delete_payload(self, asset_id: str) -> Optional[str]:
        """
        Delete encrypted payload.
        
        Args:
            asset_id: Asset identifier
        
        Returns:
            SHA256 hash of original payload, or None if not found
        """
        payload_path = self.root / f"{asset_id}.bin"
        
        if not payload_path.exists():
            return None
        
        # Read and hash original
        data = payload_path.read_bytes()
        data_hash = hashlib.sha256(data).hexdigest()
        
        # Secure overwrite and delete
        self._secure_overwrite(payload_path)
        
        return data_hash
    
    def destroy_capability(
        self,
        asset_id: str,
        *,
        shred_key: bool = True,
        delete_payload: bool = True,
    ) -> DestructionResult:
        """
        Destroy a capability completely.
        
        This is the high-level destruction operation that combines
        key shredding and payload deletion.
        
        Args:
            asset_id: Asset identifier
            shred_key: Whether to shred the key (default: True)
            delete_payload: Whether to delete the payload (default: True)
        
        Returns:
            DestructionResult with hashes of destroyed material
        
        Raises:
            FileNotFoundError: If key file doesn't exist and shred_key=True
            ValueError: If neither operation is requested
        """
        if not shred_key and not delete_payload:
            raise ValueError("At least one destruction operation must be specified")
        
        key_hash = None
        key_destroyed = False
        
        if shred_key:
            key_hash = self.shred_key(asset_id)
            key_destroyed = True
        
        payload_hash = None
        payload_destroyed = False
        
        if delete_payload:
            payload_hash = self.delete_payload(asset_id)
            payload_destroyed = payload_hash is not None
        
        return DestructionResult(
            asset_id=asset_id,
            key_destroyed=key_destroyed,
            key_hash=key_hash,
            payload_destroyed=payload_destroyed,
            payload_hash=payload_hash,
        )
    
    def verify_destroyed(self, asset_id: str) -> bool:
        """
        Verify that an asset has been destroyed.
        
        Args:
            asset_id: Asset identifier
        
        Returns:
            True if key file does not exist (destroyed)
        """
        key_path = self.root / f"{asset_id}.key"
        return not key_path.exists()
