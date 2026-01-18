"""
EIP-712 PolicyGrant signature verification.

Provides wallet-native signing and verification using secp256k1 signatures
over EIP-712 typed structured data.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from eth_account import Account
from eth_account.messages import encode_typed_data

from .policy_grant import PolicyGrant, VerifiedGrant


EIP712_TYPES: Dict[str, Any] = {
    "EIP712Domain": [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
        {"name": "chainId", "type": "uint256"},
        {"name": "verifyingContract", "type": "address"},
    ],
    "PolicyGrant": [
        {"name": "commit", "type": "bytes32"},
        {"name": "policy_id", "type": "bytes32"},
        {"name": "mode", "type": "uint8"},
        {"name": "rights", "type": "uint32"},
        {"name": "exp", "type": "uint64"},
        {"name": "nonce", "type": "bytes32"},
        {"name": "engine_version", "type": "uint32"},
    ],
}


class PolicyGrantVerifier:
    """
    Verifies EIP-712 signed PolicyGrant messages.

    Design:
      - wallet-native signing (secp256k1)
      - fail-closed expiry
      - does NOT store user identifiers
    """

    def __init__(
        self,
        *,
        name: str,
        version: str,
        chain_id: int,
        verifying_contract: str,
        clock_skew_sec: int = 30,
    ) -> None:
        """
        Initialize the verifier with EIP-712 domain parameters.

        Args:
            name: EIP-712 domain name (e.g., "GeoPhase")
            version: EIP-712 domain version (e.g., "0.1.1")
            chain_id: Blockchain chain ID (e.g., 8453 for Base mainnet)
            verifying_contract: Address of the verifying contract
            clock_skew_sec: Allowed clock skew in seconds for expiry checks
        """
        self.name = name
        self.version = version
        self.chain_id = int(chain_id)
        self.verifying_contract = verifying_contract
        self.clock_skew_sec = int(clock_skew_sec)

    def typed_data(self, grant: PolicyGrant) -> Dict[str, Any]:
        """
        Build EIP-712 typed data structure for a grant.

        Args:
            grant: The PolicyGrant to encode

        Returns:
            EIP-712 typed data dictionary
        """
        return {
            "types": EIP712_TYPES,
            "primaryType": "PolicyGrant",
            "domain": {
                "name": self.name,
                "version": self.version,
                "chainId": self.chain_id,
                "verifyingContract": self.verifying_contract,
            },
            "message": grant.to_eip712_message(),
        }

    def recover_signer(self, grant: PolicyGrant, signature_hex: str) -> str:
        """
        Recover the signer address from a grant signature.

        Args:
            grant: The PolicyGrant that was signed
            signature_hex: The signature as a hex string

        Returns:
            Recovered Ethereum address (lowercase)
        """
        msg = encode_typed_data(full_message=self.typed_data(grant))
        signer = Account.recover_message(msg, signature=signature_hex)
        return signer.lower()

    def verify(
        self,
        grant: PolicyGrant,
        signature_hex: str,
        expected_signer: Optional[str] = None,
        now: Optional[int] = None,
    ) -> VerifiedGrant:
        """
        Verify a PolicyGrant signature and expiry.

        Args:
            grant: The PolicyGrant to verify
            signature_hex: The signature as a hex string
            expected_signer: Optional expected signer address (lowercase)
            now: Optional current timestamp (defaults to time.time())

        Returns:
            VerifiedGrant with recovered signer

        Raises:
            PermissionError: If grant is expired or signature is invalid
        """
        # Expiry (fail closed)
        t = int(time.time() if now is None else now)
        if grant.exp < (t - self.clock_skew_sec):
            raise PermissionError("grant expired")

        signer = self.recover_signer(grant, signature_hex)

        if expected_signer is not None and signer != expected_signer.lower():
            raise PermissionError("signer mismatch")

        return VerifiedGrant(signer=signer, grant=grant)
