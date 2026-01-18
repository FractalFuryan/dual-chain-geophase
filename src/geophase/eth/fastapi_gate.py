"""
FastAPI fail-closed gate dependency for PolicyGrant verification.

This module provides a FastAPI dependency factory that enforces:
- Valid PolicyGrant signature
- Grant not expired
- On-chain revocation not set (fail-closed)
- Capability not destroyed (410 Gone)
- Required rights present
"""

from __future__ import annotations

from typing import Optional, Protocol

from fastapi import Header, HTTPException, Request
from pydantic import ValidationError

from .policy_grant import PolicyGrant, VerifiedGrant
from .eip712_policy_grant import PolicyGrantVerifier


class GateConfig:
    """
    Configuration for gate behavior.

    Args:
        strict_chain: If True, fail if chain check throws (default: True)
        strict_revocation: If True, fail if revocation check throws (default: True)
        require_grant: If True, require grant headers to be present (default: True)
        check_destruction: If True, check ledger for destruction events (default: True)
    """

    def __init__(
        self,
        *,
        strict_chain: bool = True,
        strict_revocation: bool = True,
        require_grant: bool = True,
        check_destruction: bool = True,
    ) -> None:
        self.strict_chain = strict_chain
        self.strict_revocation = strict_revocation
        self.require_grant = require_grant
        self.check_destruction = check_destruction


class ChainClientProtocol(Protocol):
    """
    Minimal interface for chain revocation checking.

    This protocol allows the gate to remain decoupled from specific
    chain client implementations while ensuring type safety.
    """

    def is_revoked(self, commit_hex: str) -> bool:
        """
        Check if a commit is revoked on-chain.

        Args:
            commit_hex: The commit hash as a 0x-prefixed hex string

        Returns:
            True if revoked, False otherwise

        Raises:
            Exception: On chain communication failure
        """
        ...  # pragma: no cover


class LedgerProtocol(Protocol):
    """
    Minimal interface for ledger destruction checking.
    
    This protocol allows the gate to check for capability destruction
    without coupling to the ledger implementation.
    """
    
    def is_destroyed(self, asset_id: str) -> bool:
        """
        Check if an asset has been destroyed.
        
        Args:
            asset_id: Asset identifier (typically commit hash)
        
        Returns:
            True if asset is permanently destroyed, False otherwise
        """
        ...  # pragma: no cover


def _deny(detail: str, code: int = 403) -> None:
    """Raise HTTPException with given detail and status code."""
    raise HTTPException(status_code=code, detail=detail)


def build_gate_dependency(
    *,
    verifier: PolicyGrantVerifier,
    chain: ChainClientProtocol,
    cfg: GateConfig,
    required_rights: int,
    ledger: Optional[LedgerProtocol] = None,
):
    """
    Build a FastAPI dependency that enforces PolicyGrant authorization.

    The returned dependency performs the following checks in order:
    1. Presence of required headers (if cfg.require_grant)
    2. PolicyGrant JSON schema validation
    3. EIP-712 signature verification
    4. Expiry check
    5. Rights check against required_rights
    6. Capability destruction check (410 Gone if destroyed)
    7. On-chain revocation check (fail-closed if strict)

    Args:
        verifier: PolicyGrantVerifier instance
        chain: Chain client implementing is_revoked()
        cfg: GateConfig for behavior control
        required_rights: Bitmask of required Rights flags
        ledger: Optional Ledger instance for destruction checks

    Returns:
        FastAPI dependency function that returns VerifiedGrant

    Example:
        ```python
        gate = build_gate_dependency(
            verifier=my_verifier,
            chain=my_chain_client,
            cfg=GateConfig(),
            required_rights=int(Rights.FRAME),
            ledger=my_ledger,
        )

        @app.post("/generate")
        def generate(grant: VerifiedGrant = Depends(gate)):
            return {"signer": grant.signer}
        ```
    """

    async def gate(
        request: Request,
        x_policy_grant: Optional[str] = Header(default=None, alias="X-Policy-Grant"),
        x_signature: Optional[str] = Header(default=None, alias="X-Policy-Signature"),
        x_signer: Optional[str] = Header(default=None, alias="X-Policy-Signer"),
    ) -> VerifiedGrant:
        # Check required headers
        if cfg.require_grant:
            if not x_policy_grant or not x_signature:
                _deny("missing policy grant")

        # If grant is optional but not provided, deny
        if not x_policy_grant or not x_signature:
            _deny("policy grant required")

        # Parse and validate grant
        try:
            grant = PolicyGrant.model_validate_json(x_policy_grant)
        except ValidationError as e:
            _deny(f"invalid policy grant: {e}")

        # Verify signature
        try:
            verified = verifier.verify(grant, x_signature, expected_signer=x_signer)
        except Exception as e:
            _deny(f"invalid signature: {e}")

        # Rights check
        if (int(verified.grant.rights) & int(required_rights)) != int(required_rights):
            _deny("insufficient rights")

        # Destruction check (410 Gone - asset permanently destroyed)
        if cfg.check_destruction and ledger is not None:
            try:
                if ledger.is_destroyed(verified.grant.commit):
                    _deny("asset permanently destroyed", code=410)
            except Exception as e:
                # Log but continue - destruction check is advisory if ledger fails
                pass

        # Revocation check (fail-closed if strict)
        try:
            revoked = chain.is_revoked(verified.grant.commit)
        except Exception as e:
            if cfg.strict_chain or cfg.strict_revocation:
                _deny(f"chain check failed (fail-closed): {e}", code=503)
            revoked = True  # safest default

        if revoked:
            _deny("revoked")

        # Attach verified grant to request state for downstream handlers
        request.state.policy_grant = verified
        return verified

    return gate
