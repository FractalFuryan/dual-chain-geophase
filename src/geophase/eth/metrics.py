"""
Non-behavioral system metrics only.

NO user identifiers.
NO content metrics.
NO session tracking.

Only infrastructure health: latency, errors, success/failure counts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Metrics:
    """
    Non-behavioral system metrics only.
    
    Examples:
        - RPC latency
        - Revocation check errors
        - Chain health
    
    NOT allowed:
        - User IDs
        - Content hashes
        - Session tracking
        - Behavioral analytics
    """
    counters: Dict[str, int] = field(default_factory=dict)
    gauges: Dict[str, float] = field(default_factory=dict)

    def inc(self, name: str, by: int = 1) -> None:
        """Increment counter by value."""
        self.counters[name] = self.counters.get(name, 0) + by

    def observe(self, name: str, value: float) -> None:
        """Record gauge observation."""
        self.gauges[name] = float(value)

    def snapshot(self) -> dict:
        """Return current metrics snapshot."""
        return {"counters": dict(self.counters), "gauges": dict(self.gauges)}
