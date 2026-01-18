"""
GeoPhase Storage: Secure material management and destruction.

Handles cryptographic key material and asset storage with secure deletion.
"""

from .destruction import DestructionManager, DestructionResult

__all__ = [
    "DestructionManager",
    "DestructionResult",
]
