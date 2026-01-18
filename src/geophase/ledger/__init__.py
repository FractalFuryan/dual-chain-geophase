"""
GeoPhase Ledger: Immutable event recording for capability lifecycle.

This module provides cryptographic event logging for irreversible operations:
- Capability destruction (key shredding)
- State transitions
- Audit trail without identity tracking
"""

from .destruction_event import CapabilityDestructionEvent, DestructionMethod
from .ledger import Ledger, LedgerQuery

__all__ = [
    "CapabilityDestructionEvent",
    "DestructionMethod",
    "Ledger",
    "LedgerQuery",
]
