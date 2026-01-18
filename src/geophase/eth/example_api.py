"""
Example FastAPI application using PolicyGrant authentication.

This demonstrates how to:
- Configure the EIP-712 verifier
- Set up fail-closed gates with on-chain revocation
- Expose the .well-known discovery endpoint
- Protect routes with different rights requirements
"""

import os
from fastapi import FastAPI, Depends

from geophase.eth.eip712_policy_grant import PolicyGrantVerifier
from geophase.eth.fastapi_gate import build_gate_dependency, GateConfig, ChainClientProtocol
from geophase.eth.policy_grant import Rights, VerifiedGrant
from geophase.eth.well_known import VerifierMetadata, as_json


# ===== Configuration (load from environment in production) =====

VERIFIER_NAME = os.getenv("GEOPHASE_VERIFIER_NAME", "GeoPhase")
VERIFIER_VERSION = os.getenv("GEOPHASE_VERIFIER_VERSION", "0.1.1")
CHAIN_ID = int(os.getenv("GEOPHASE_CHAIN_ID", "8453"))  # Base mainnet
VERIFYING_CONTRACT = os.getenv(
    "GEOPHASE_VERIFYING_CONTRACT",
    "0x0000000000000000000000000000000000000000"  # REPLACE with your actual contract
)
ATTESTATION_REGISTRY = os.getenv("GEOPHASE_ATTESTATION_REGISTRY", "0x0000000000000000000000000000000000000000")
REVOCATION_REGISTRY = os.getenv("GEOPHASE_REVOCATION_REGISTRY", "0x0000000000000000000000000000000000000000")
BYTECODE_LOCK_HASH = os.getenv("GEOPHASE_BYTECODE_LOCK_HASH", "0x" + "00" * 32)
ETHICS_ANCHOR = "65b14d584f5a5fd070fe985eeb86e14cb3ce56a4fc41fd9e987f2259fe1f15c1"  # ANANKE ethics hash


# ===== Chain Client Stub (replace with your actual implementation) =====

class ChainClientStub(ChainClientProtocol):
    """
    Stub implementation of chain client.
    
    REPLACE THIS with your actual chain client that checks on-chain revocation.
    """
    
    def is_revoked(self, commit_hex: str) -> bool:
        """
        Check if a commit is revoked on-chain.
        
        In production, this should query your Base L2 revocation registry contract.
        """
        # TODO: Implement actual on-chain check
        # Example:
        # contract = web3.eth.contract(address=REVOCATION_REGISTRY, abi=REVOCATION_ABI)
        # return contract.functions.isRevoked(commit_hex).call()
        return False


# ===== FastAPI Application =====

app = FastAPI(
    title="GeoPhase API",
    description="EIP-712 PolicyGrant authenticated API",
    version=VERIFIER_VERSION,
)

# Initialize verifier
verifier = PolicyGrantVerifier(
    name=VERIFIER_NAME,
    version=VERIFIER_VERSION,
    chain_id=CHAIN_ID,
    verifying_contract=VERIFYING_CONTRACT,
)

# Initialize chain client
chain = ChainClientStub()

# Gate configuration (fail-closed by default)
cfg = GateConfig(
    strict_chain=True,
    strict_revocation=True,
    require_grant=True,
)

# Build gates for different rights levels
gate_frame = build_gate_dependency(
    verifier=verifier,
    chain=chain,
    cfg=cfg,
    required_rights=int(Rights.FRAME),
)

gate_video = build_gate_dependency(
    verifier=verifier,
    chain=chain,
    cfg=cfg,
    required_rights=int(Rights.VIDEO),
)

gate_stream = build_gate_dependency(
    verifier=verifier,
    chain=chain,
    cfg=cfg,
    required_rights=int(Rights.STREAM),
)


# ===== Routes =====

@app.get("/.well-known/geophase-verifier.json")
def well_known():
    """
    Discovery endpoint for EIP-712 domain parameters and registry addresses.
    
    Clients should query this to get the correct signing parameters.
    """
    meta = VerifierMetadata(
        eip712_name=VERIFIER_NAME,
        eip712_version=VERIFIER_VERSION,
        chain_id=CHAIN_ID,
        verifying_contract=VERIFYING_CONTRACT,
        attestation_registry=ATTESTATION_REGISTRY,
        revocation_registry=REVOCATION_REGISTRY,
        bytecode_lock_hash=BYTECODE_LOCK_HASH,
        ethics_anchor=ETHICS_ANCHOR,
        policy_ids=[
            # Add your policy IDs here (keccak256 of policy strings)
            # Example: "0x" + keccak(text="ANANKE_POLICY_V1_STANDARD").hex()
        ],
    )
    return as_json(meta)


@app.get("/health")
def health():
    """Health check endpoint (no authentication required)."""
    return {"status": "ok", "version": VERIFIER_VERSION}


@app.post("/v1/generate")
def generate(grant: VerifiedGrant = Depends(gate_frame)):
    """
    Generate a single frame.
    
    Requires PolicyGrant with FRAME rights.
    
    Headers:
        X-Policy-Grant: JSON-encoded PolicyGrant
        X-Policy-Signature: Hex-encoded EIP-712 signature
        X-Policy-Signer: (Optional) Expected signer address
    """
    return {
        "ok": True,
        "kind": "frame",
        "signer": grant.signer,
        "commit": grant.grant.commit,
        "mode": grant.grant.mode,
    }


@app.post("/v1/generate/video")
def generate_video(grant: VerifiedGrant = Depends(gate_video)):
    """
    Generate a video.
    
    Requires PolicyGrant with VIDEO rights.
    """
    return {
        "ok": True,
        "kind": "video",
        "signer": grant.signer,
        "commit": grant.grant.commit,
        "mode": grant.grant.mode,
    }


@app.post("/v1/stream")
def stream(grant: VerifiedGrant = Depends(gate_stream)):
    """
    Start a stream.
    
    Requires PolicyGrant with STREAM rights.
    """
    return {
        "ok": True,
        "kind": "stream",
        "signer": grant.signer,
        "commit": grant.grant.commit,
        "mode": grant.grant.mode,
    }


# ===== Run with: uvicorn example_api:app --reload =====

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
