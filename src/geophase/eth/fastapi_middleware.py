"""
FastAPI middleware for GeoPhase ↔ Ethereum integration.

Provides:
- Pre-generation revocation gate
- Fail-closed safety modes
- Health endpoint
"""

from fastapi import HTTPException
from typing import Callable, Optional

from .chain_check import ChainClient, ChainConfig
from .geocommit import compute_geo_commit, GeoCommitParams
from .metrics import Metrics
from .settings import Settings


def build_geocommit_gate(settings: Settings, metrics: Optional[Metrics] = None) -> Callable:
    """
    Build fail-closed revocation gate.
    
    Args:
        settings: Settings with strict enforcement flags
        metrics: Optional metrics instance
    
    Returns:
        Callable gate function
    """
    metrics = metrics or Metrics()
    
    # Initialize chain client
    config = ChainConfig(
        rpc_url=settings.BASE_RPC_URL,
        attestation_registry=settings.ATTESTATION_REGISTRY_ADDR,
        revocation_registry=settings.REVOCATION_REGISTRY_ADDR,
        chain_id=settings.CHAIN_ID,
    )
    
    chain_client = ChainClient(config, metrics)
    
    # Verify bytecode if enabled
    if settings.BYTECODE_LOCK_ENABLED:
        chain_client.bytecode_lock(
            attest_codehash=settings.ATTESTATION_BYTECODE_HASH,
            revoke_codehash=settings.REVOCATION_BYTECODE_HASH,
        )
    
    # Fail-closed health check
    if settings.STRICT_CHAIN and not chain_client.ping():
        raise RuntimeError("FAIL_CLOSED: Chain unreachable and STRICT_CHAIN=True")
    
    def gate(params: GeoCommitParams) -> dict:
        """
        Pre-generation revocation check.
        
        Args:
            params: GeoCommitParams with seed_commit, hashes, policy, version
        
        Returns:
            dict with {"allowed": bool, "geoCommit": str, "reason": str}
        
        Raises:
            HTTPException: On strict enforcement violations
        """
        # Compute geoCommit
        geo_commit = compute_geo_commit(params)
        
        # Check revocation
        try:
            is_revoked = chain_client.is_revoked(geo_commit)
        except Exception as e:
            metrics.inc("gate_revocation_check_failed_total")
            if settings.STRICT_REVOCATION:
                # Fail closed: block on error
                raise HTTPException(
                    status_code=503,
                    detail="Revocation check failed and STRICT_REVOCATION=True"
                )
            else:
                # Fail open: allow on error (degraded mode)
                is_revoked = False
        
        if is_revoked:
            metrics.inc("gate_blocked_revoked_total")
            return {
                "allowed": False,
                "geoCommit": geo_commit.hex(),
                "reason": "REVOKED",
            }
        
        metrics.inc("gate_allowed_total")
        return {
            "allowed": True,
            "geoCommit": geo_commit.hex(),
            "reason": "OK",
        }
    
    return gate


def build_health_endpoint(chain_client: ChainClient, metrics: Metrics) -> Callable:
    """
    Build health check endpoint.
    
    Args:
        chain_client: ChainClient instance
        metrics: Metrics instance
    
    Returns:
        Callable health function
    """
    def health() -> dict:
        """
        Health check endpoint.
        
        Returns:
            dict with {"healthy": bool, "rpc": bool, "metrics": dict}
        """
        rpc_ok = chain_client.ping()
        
        return {
            "healthy": rpc_ok,
            "rpc": rpc_ok,
            "metrics": metrics.snapshot(),
        }
    
    return health


# Example FastAPI integration
"""
from fastapi import FastAPI
from geophase.eth.fastapi_middleware import build_geocommit_gate, build_health_endpoint
from geophase.eth.settings import Settings
from geophase.eth.metrics import Metrics
from geophase.eth.chain_check import ChainClient, ChainConfig
from pydantic import BaseModel

# Initialize
settings = Settings.load()
metrics = Metrics()
gate = build_geocommit_gate(settings, metrics)

# Build health endpoint
config = ChainConfig(
    rpc_url=settings.base_rpc_url,
    attestation_registry=settings.attestation_registry_addr,
    revocation_registry=settings.revocation_registry_addr,
    chain_id=settings.chain_id,
)
chain_client = ChainClient(config, metrics)
health_fn = build_health_endpoint(chain_client, metrics)

app = FastAPI()

class GenerateRequest(BaseModel):
    output_hash: str  # 64-char hex
    chain_id: int
    version: int

@app.post("/generate")
async def generate(req: GenerateRequest):
    # Pre-generation gate
    result = gate(
        bytes.fromhex(req.output_hash),
        req.chain_id,
        req.version,
    )
    
    if not result["allowed"]:
        raise HTTPException(status_code=403, detail=result["reason"])
    
    # Proceed with generation
    # ...
    
    return {
        "geoCommit": result["geoCommit"],
        "status": "generated",
    }

@app.get("/health")
async def health_check():
    return health_fn()
"""
