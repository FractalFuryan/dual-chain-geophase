"""
Immutable event ledger for GeoPhase capability lifecycle.

This ledger stores cryptographic events (destruction, state transitions)
in an append-only, immutable log. Events are stored as JSON lines.

Design:
- Append-only (no updates, no deletes)
- JSON Lines format (.jsonl)
- Atomic writes
- Fast lookup by asset_id
- No identity tracking
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, Optional, List
from datetime import datetime

from .destruction_event import CapabilityDestructionEvent


class LedgerQuery:
    """Query interface for ledger events."""
    
    def __init__(self, events: List[CapabilityDestructionEvent]) -> None:
        self.events = events
    
    def by_asset(self, asset_id: str) -> List[CapabilityDestructionEvent]:
        """Get all events for a specific asset."""
        return [e for e in self.events if e.asset_id == asset_id]
    
    def is_destroyed(self, asset_id: str) -> bool:
        """Check if an asset has been destroyed."""
        return any(
            e.asset_id == asset_id and e.event_type == "capability_destruction"
            for e in self.events
        )
    
    def get_destruction_event(self, asset_id: str) -> Optional[CapabilityDestructionEvent]:
        """Get the destruction event for an asset (if it exists)."""
        for e in self.events:
            if e.asset_id == asset_id and e.event_type == "capability_destruction":
                return e
        return None


class Ledger:
    """
    Immutable event ledger for GeoPhase.
    
    Stores capability destruction events in an append-only log.
    Once an event is added, it cannot be modified or deleted.
    
    Storage format: JSON Lines (.jsonl)
    - One event per line
    - Atomic appends
    - Human-readable for audit
    """
    
    def __init__(self, ledger_path: str | Path) -> None:
        """
        Initialize ledger.
        
        Args:
            ledger_path: Path to .jsonl ledger file
        """
        self.ledger_path = Path(ledger_path)
        
        # Create parent directory if needed
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create ledger file if it doesn't exist
        if not self.ledger_path.exists():
            self.ledger_path.touch()
    
    def add_event(self, event: CapabilityDestructionEvent) -> None:
        """
        Add an event to the ledger.
        
        This is an append-only operation. Events cannot be modified
        or deleted once added.
        
        Args:
            event: CapabilityDestructionEvent to add
        """
        # Serialize event to JSON
        event_json = event.model_dump_json()
        
        # Atomic append
        with self.ledger_path.open("a") as f:
            f.write(event_json + "\n")
            f.flush()
    
    def iter_events(self) -> Iterator[CapabilityDestructionEvent]:
        """
        Iterate over all events in the ledger.
        
        Yields:
            CapabilityDestructionEvent instances
        """
        if not self.ledger_path.exists():
            return
        
        with self.ledger_path.open("r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    yield CapabilityDestructionEvent.model_validate(data)
                except Exception as e:
                    # Log but don't fail - corrupted entries are skipped
                    print(f"Warning: Skipping corrupted ledger entry: {e}")
                    continue
    
    def query(self) -> LedgerQuery:
        """
        Create a query interface for the ledger.
        
        Returns:
            LedgerQuery with all events loaded into memory
        """
        events = list(self.iter_events())
        return LedgerQuery(events)
    
    def has_event(self, asset_id: str, event_type: str) -> bool:
        """
        Check if an event exists for an asset.
        
        Args:
            asset_id: Asset identifier
            event_type: Event type to check
        
        Returns:
            True if event exists
        """
        for event in self.iter_events():
            if event.asset_id == asset_id and event.event_type == event_type:
                return True
        return False
    
    def is_destroyed(self, asset_id: str) -> bool:
        """
        Check if an asset has been destroyed.
        
        Args:
            asset_id: Asset identifier
        
        Returns:
            True if destruction event exists
        """
        return self.has_event(asset_id, "capability_destruction")
    
    def count_events(self) -> int:
        """
        Count total events in the ledger.
        
        Returns:
            Number of events
        """
        count = 0
        for _ in self.iter_events():
            count += 1
        return count
    
    def get_destruction_proof(self, asset_id: str) -> Optional[str]:
        """
        Get the destruction proof hash for an asset.
        
        Args:
            asset_id: Asset identifier
        
        Returns:
            Proof hash if destroyed, None otherwise
        """
        for event in self.iter_events():
            if (
                event.asset_id == asset_id
                and event.event_type == "capability_destruction"
            ):
                return event.proof_hash
        return None
