"""
On-chain attestation and revocation checks for GeoPhase commitments.
Connects to Base network via web3.py.

Includes:
- Bytecode lock verification
- Fail-closed health checks
- Non-behavioral metrics
"""

import os
import time
from typing import Optional, Tuple
from dataclasses import dataclass
from web3 import Web3
from web3.contract import Contract
from eth_typing import Address

from .metrics import Metrics
from .bytecode_lock import BytecodeLock


@dataclass
class ChainConfig:
    """Base network configuration."""
    rpc_url: str
    chain_id: int
    attestation_registry: str
    revocation_registry: str
    private_key: Optional[str] = None  # Only for attestation writes


# Contract ABIs (minimal, read-only friendly)
ATTESTATION_REGISTRY_ABI = [
    {
        "inputs": [{"name": "geoCommit", "type": "bytes32"}],
        "name": "attestations",
        "outputs": [
            {"name": "ethicsAnchor", "type": "bytes32"},
            {"name": "policyId", "type": "bytes32"},
            {"name": "version", "type": "uint32"},
            {"name": "attestor", "type": "address"},
            {"name": "timestamp", "type": "uint64"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "geoCommit", "type": "bytes32"},
            {"name": "ethicsAnchor", "type": "bytes32"},
            {"name": "policyId", "type": "bytes32"},
            {"name": "version", "type": "uint32"},
        ],
        "name": "attest",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

REVOCATION_REGISTRY_ABI = [
    {
        "inputs": [{"name": "key", "type": "bytes32"}],
        "name": "isRevoked",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "key", "type": "bytes32"}],
        "name": "revoke",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


class ChainClient:
    """
    Web3 client for Base network interactions.
    
    Features:
    - Bytecode lock verification
    - Fail-closed health checks
    - Non-behavioral metrics
    """
    
    def __init__(self, config: ChainConfig, metrics: Optional[Metrics] = None):
        self.config = config
        self.w3 = Web3(Web3.HTTPProvider(config.rpc_url, request_kwargs={"timeout": 8}))
        self.metrics = metrics or Metrics()
        
        if not self.w3.is_connected():
            raise ConnectionError(f"Cannot connect to Base RPC: {config.rpc_url}")
        
        # Initialize contracts
        self.attestation_registry = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.attestation_registry),
            abi=ATTESTATION_REGISTRY_ABI
        )
        
        self.revocation_registry = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.revocation_registry),
            abi=REVOCATION_REGISTRY_ABI
        )
    
    def bytecode_lock(self, attest_codehash: str, revoke_codehash: str) -> None:
        """
        Verify deployed bytecode matches expected hashes.
        Fails closed on mismatch.
        """
        if attest_codehash:
            BytecodeLock(
                self.w3,
                self.attestation_registry.address,
                attest_codehash
            ).verify_or_raise()
        
        if revoke_codehash:
            BytecodeLock(
                self.w3,
                self.revocation_registry.address,
                revoke_codehash
            ).verify_or_raise()
    
    def ping(self) -> bool:
        """
        Check RPC health.
        Returns True if reachable, False otherwise.
        """
        t0 = time.time()
        try:
            _ = self.w3.eth.block_number
            self.metrics.observe("rpc_latency_ms", (time.time() - t0) * 1000.0)
            return True
        except Exception as e:
            self.metrics.inc("rpc_errors_total")
            return False
    
    def is_revoked(self, geo_commit: bytes) -> bool:
        """
        Check if a geoCommit is revoked.
        
        Args:
            geo_commit: 32-byte geoCommit hash
        
        Returns:
            True if revoked, False otherwise
        
        Raises:
            Exception: On RPC failure (caller should handle fail-closed)
        """
        t0 = time.time()
        try:
            result = self.revocation_registry.functions.isRevoked(geo_commit).call()
            self.metrics.observe("revocation_read_ms", (time.time() - t0) * 1000.0)
            return bool(result)
        except Exception as e:
            self.metrics.inc("revocation_read_errors_total")
            raise
    
    def get_attestation(self, geo_commit: bytes) -> Optional[dict]:
        """
        Retrieve attestation for a geoCommit.
        
        Args:
            geo_commit: 32-byte geoCommit hash
        
        Returns:
            Attestation dict or None if not attested
        """
        try:
            result = self.attestation_registry.functions.attestations(geo_commit).call()
            ethics_anchor, policy_id, version, attestor, timestamp = result
            
            # Check if attested (timestamp != 0)
            if timestamp == 0:
                return None
            
            return {
                "ethicsAnchor": ethics_anchor,
                "policyId": policy_id,
                "version": version,
                "attestor": attestor,
                "timestamp": timestamp,
            }
        except Exception as e:
            self.metrics.inc("attestation_read_errors_total")
            return None
    
    def attest(
        self,
        geo_commit: bytes,
        ethics_anchor: bytes,
        policy_id: bytes,
        version: int,
        gas_limit: int = 200_000
    ) -> Optional[str]:
        """
        Write an attestation on-chain (requires private key).
        
        Args:
            geo_commit: 32-byte geoCommit hash
            ethics_anchor: 32-byte ethics anchor hash
            policy_id: 32-byte policy identifier
            version: uint32 version number
            gas_limit: Max gas for transaction
        
        Returns:
            Transaction hash (0x-prefixed) or None on failure
        """
        if not self.config.private_key:
            raise ValueError("Private key required for attestation writes")
        
        account = self.w3.eth.account.from_key(self.config.private_key)
        
        try:
            # Build transaction
            tx = self.attestation_registry.functions.attest(
                geo_commit,
                ethics_anchor,
                policy_id,
                version
            ).build_transaction({
                'from': account.address,
                'nonce': self.w3.eth.get_transaction_count(account.address),
                'gas': gas_limit,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.config.chain_id,
            })
            
            # Sign and send
            signed_tx = account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            print(f"Attestation submitted: {tx_hash.hex()}")
            
            # Wait for receipt (optional, comment out for async)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                print(f"Attestation confirmed in block {receipt['blockNumber']}")
                return tx_hash.hex()
            else:
                print(f"Attestation failed: {receipt}")
                return None
                
        except Exception as e:
            print(f"Attestation transaction failed: {e}")
            return None


def load_config_from_env() -> ChainConfig:
    """Load chain configuration from environment variables."""
    return ChainConfig(
        rpc_url=os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
        chain_id=int(os.getenv("CHAIN_ID", "8453")),
        attestation_registry=os.getenv("ATTESTATION_REGISTRY_ADDR", ""),
        revocation_registry=os.getenv("REVOCATION_REGISTRY_ADDR", ""),
        private_key=os.getenv("PRIVATE_KEY"),  # Optional for read-only
    )
