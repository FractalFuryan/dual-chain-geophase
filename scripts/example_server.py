"""
Example FastAPI server with GeoPhase ↔ Base integration.
Demonstrates revocation checks and optional attestation.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import os
import time

from geophase.eth import (
    ChainClient,
    load_config_from_env,
    compute_geo_commit,
    compute_seed_commit,
    compute_phase_hash,
    GeoCommitParams,
    verify_procedural_auth,
    generate_nonce,
    bytes32_to_hex,
    hex_to_bytes32,
    set_verifying_contract,
)


# Initialize chain client
try:
    chain_config = load_config_from_env()
    chain_client = ChainClient(chain_config)
    set_verifying_contract(chain_config.attestation_registry)
    CHAIN_ENABLED = True
    print("✅ Chain client initialized (Base)")
except Exception as e:
    print(f"⚠️ Chain client disabled: {e}")
    CHAIN_ENABLED = False
    chain_client = None


app = FastAPI(
    title="GeoPhase Living Cipher API",
    description="Privacy-safe procedural generation with on-chain attestation",
    version="0.1.0"
)


# Request models
class GenerateRequest(BaseModel):
    seed: str  # hex-encoded
    user_nonce: str  # hex-encoded (32 bytes)
    phaseA_vector: str  # hex-encoded
    phaseB_vector: str  # hex-encoded
    policy_id: str  # hex-encoded (32 bytes)
    version: int = 1
    
    # Optional EIP-712 auth
    signature: Optional[str] = None
    message: Optional[dict] = None
    address: Optional[str] = None


class AttestRequest(BaseModel):
    geo_commit: str  # hex-encoded
    ethics_anchor: str  # hex-encoded
    policy_id: str  # hex-encoded
    version: int = 1


class RevokeRequest(BaseModel):
    key: str  # hex-encoded (geoCommit or other key)


# Endpoints
@app.get("/")
async def root():
    return {
        "service": "GeoPhase Living Cipher",
        "version": "0.1.0",
        "chain": "Base" if CHAIN_ENABLED else "disabled",
        "endpoints": {
            "generate": "/generate",
            "attest": "/attest",
            "revoke": "/revoke",
            "status": "/status/{geo_commit}"
        }
    }


@app.post("/generate")
async def generate(req: GenerateRequest):
    """
    Generate GeoPhase output (Living Cipher).
    
    Steps:
    1. Verify EIP-712 signature (if provided)
    2. Compute geoCommit
    3. Check revocation
    4. Generate (placeholder - wire your logic here)
    5. Optional: Attest on-chain
    """
    
    # Optional: Verify EIP-712 signature
    if req.signature and req.message and req.address:
        if not verify_procedural_auth(req.message, req.signature, req.address):
            raise HTTPException(403, "Invalid procedural authorization")
    
    # Compute geoCommit
    try:
        seed = bytes.fromhex(req.seed.replace("0x", ""))
        user_nonce = bytes.fromhex(req.user_nonce.replace("0x", ""))
        phaseA_vector = bytes.fromhex(req.phaseA_vector.replace("0x", ""))
        phaseB_vector = bytes.fromhex(req.phaseB_vector.replace("0x", ""))
        policy_id = hex_to_bytes32(req.policy_id)
    except Exception as e:
        raise HTTPException(400, f"Invalid hex encoding: {e}")
    
    seed_commit = compute_seed_commit(seed, user_nonce)
    phaseA_hash = compute_phase_hash(phaseA_vector)
    phaseB_hash = compute_phase_hash(phaseB_vector)
    
    params = GeoCommitParams(
        seed_commit=seed_commit,
        phaseA_hash=phaseA_hash,
        phaseB_hash=phaseB_hash,
        policy_id=policy_id,
        version=req.version
    )
    
    geo_commit = compute_geo_commit(params)
    
    # Check revocation (if chain enabled)
    if CHAIN_ENABLED and chain_client:
        if chain_client.is_revoked(geo_commit):
            raise HTTPException(403, "GeoCommit has been revoked")
    
    # TODO: Replace with your actual generation logic
    result = {
        "geo_commit": bytes32_to_hex(geo_commit),
        "seed_commit": bytes32_to_hex(seed_commit),
        "phaseA_hash": bytes32_to_hex(phaseA_hash),
        "phaseB_hash": bytes32_to_hex(phaseB_hash),
        "output": "[Generated output would go here]",
        "timestamp": int(time.time())
    }
    
    return result


@app.post("/attest")
async def attest(req: AttestRequest):
    """
    Attest a geoCommit on-chain (requires private key in config).
    """
    if not CHAIN_ENABLED or not chain_client:
        raise HTTPException(503, "Chain client not available")
    
    try:
        geo_commit = hex_to_bytes32(req.geo_commit)
        ethics_anchor = hex_to_bytes32(req.ethics_anchor)
        policy_id = hex_to_bytes32(req.policy_id)
    except Exception as e:
        raise HTTPException(400, f"Invalid hex encoding: {e}")
    
    # Submit attestation
    tx_hash = chain_client.attest(
        geo_commit=geo_commit,
        ethics_anchor=ethics_anchor,
        policy_id=policy_id,
        version=req.version
    )
    
    if not tx_hash:
        raise HTTPException(500, "Attestation failed")
    
    return {
        "status": "attested",
        "tx_hash": tx_hash,
        "geo_commit": req.geo_commit
    }


@app.post("/revoke")
async def revoke(req: RevokeRequest):
    """
    Revoke a geoCommit (or other key).
    Note: This is a write operation - requires gas.
    """
    if not CHAIN_ENABLED or not chain_client:
        raise HTTPException(503, "Chain client not available")
    
    # TODO: Add authorization check (only owner can revoke)
    
    raise HTTPException(501, "Revocation endpoint not implemented (use web3 directly)")


@app.get("/status/{geo_commit}")
async def status(geo_commit: str):
    """
    Check attestation and revocation status for a geoCommit.
    """
    if not CHAIN_ENABLED or not chain_client:
        raise HTTPException(503, "Chain client not available")
    
    try:
        geo_commit_bytes = hex_to_bytes32(geo_commit)
    except Exception as e:
        raise HTTPException(400, f"Invalid hex encoding: {e}")
    
    # Check revocation
    is_revoked = chain_client.is_revoked(geo_commit_bytes)
    
    # Get attestation
    attestation = chain_client.get_attestation(geo_commit_bytes)
    
    return {
        "geo_commit": geo_commit,
        "revoked": is_revoked,
        "attested": attestation is not None,
        "attestation": attestation
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    chain_status = "connected" if CHAIN_ENABLED else "disabled"
    
    if CHAIN_ENABLED and chain_client:
        try:
            # Test RPC connection
            chain_client.w3.eth.block_number
            chain_status = "connected"
        except:
            chain_status = "error"
    
    return {
        "status": "healthy",
        "chain": chain_status,
        "timestamp": int(time.time())
    }


# Error handlers
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": type(exc).__name__
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
