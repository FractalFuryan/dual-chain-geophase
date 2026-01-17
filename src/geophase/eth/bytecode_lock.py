"""
Bytecode hash lock - Fail-closed contract integrity check.
Prevents silent redeploy/proxy swap attacks.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

from web3 import Web3


def keccak_hex(data: bytes) -> str:
    """Compute keccak256 hash and return as hex string."""
    return Web3.keccak(data).hex()


@dataclass(frozen=True)
class BytecodeLock:
    """
    Fail-closed contract integrity check.
    Compares deployed bytecode (eth_getCode) keccak hash to an expected hash.
    
    Usage:
        lock = BytecodeLock(w3, contract_addr, expected_hash)
        lock.verify_or_raise()  # Raises on mismatch
    """
    w3: Web3
    contract_address: str
    expected_codehash: str  # 0x-prefixed keccak256(code)

    def fetch_codehash(self) -> str:
        """Fetch current deployed bytecode and compute its hash."""
        code = self.w3.eth.get_code(Web3.to_checksum_address(self.contract_address))
        return keccak_hex(bytes(code))

    def verify_or_raise(self) -> None:
        """
        Verify bytecode matches expected hash.
        Raises RuntimeError on mismatch.
        """
        # Skip verification if expected_codehash is None
        if self.expected_codehash is None:
            return
        
        got = self.fetch_codehash().lower()
        exp = self.expected_codehash.lower()
        if got != exp:
            raise RuntimeError(
                f"BYTECODE_LOCK FAIL: {self.contract_address} expected={exp} got={got}"
            )
