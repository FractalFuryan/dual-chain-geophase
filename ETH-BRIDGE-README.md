# GeoPhase ↔ Base Bridge

**Status:** ✅ Shipped v0.1  
**Chain:** Base (L2)  
**Attestation:** Optional (commitment-only)  
**Revocation:** Always enforced

---

## Quick Start

### 1. Install Dependencies

```bash
pip install web3 eth-account eth-utils
```

### 2. Deploy Contracts (Base Mainnet)

```bash
# Set environment variables
cp .env.example .env
# Edit .env with your PRIVATE_KEY and BASE_RPC_URL

# Deploy (requires Foundry)
./deploy.sh
```

### 3. Python Integration

```python
from geophase.eth import (
    ChainClient,
    load_config_from_env,
    compute_geo_commit,
    GeoCommitParams,
    compute_seed_commit,
    compute_phase_hash,
)

# Initialize chain client
config = load_config_from_env()
client = ChainClient(config)

# Compute geoCommit
seed_commit = compute_seed_commit(seed, user_nonce)
phaseA_hash = compute_phase_hash(phaseA_vector_bytes)
phaseB_hash = compute_phase_hash(phaseB_vector_bytes)

params = GeoCommitParams(
    seed_commit=seed_commit,
    phaseA_hash=phaseA_hash,
    phaseB_hash=phaseB_hash,
    policy_id=policy_id,
    version=1
)
geo_commit = compute_geo_commit(params)

# Check revocation (before generation)
if client.is_revoked(geo_commit):
    raise Exception("GeoCommit revoked")

# Generate (your existing logic)
result = your_generation_function(params)

# Optional: Attest on-chain
client.attest(geo_commit, ethics_anchor, policy_id, version)
```

### 4. FastAPI Middleware

```python
from fastapi import FastAPI
from geophase.eth.fastapi_middleware import GeoPhaseChainMiddleware

app = FastAPI()

# Add middleware
middleware = GeoPhaseChainMiddleware(
    enabled=True,
    enforce_revocation=True,
    enable_attestation=False,  # Optional
)
app.middleware("http")(middleware)
```

---

## What's Included

### Contracts (`/contracts`)
- `AnankeAttestationRegistry.sol` - Write-once provenance
- `AnankeRevocationRegistry.sol` - User-controlled opt-out

### Python SDK (`/src/geophase/eth`)
- `geocommit.py` - Commitment computation
- `eip712_verify.py` - Signature verification
- `chain_check.py` - On-chain reads/writes
- `fastapi_middleware.py` - Pre-generation gate

### Documentation (`/docs/eth`)
- `GEO-COMMIT-SPEC.md` - Commitment format
- `EIP712-PROCEDURAL-AUTH.md` - Signature spec
- `THREAT-MODEL-ETH.md` - Security analysis

---

## Privacy Guarantees

### ❌ Never On-Chain
- Raw seeds
- Phase vectors
- Generated media
- User identifiers
- Biometric data

### ✅ Only On-Chain
- Cryptographic hashes (keccak256, sha256)
- Policy identifiers
- Version numbers
- Timestamps
- Revocation bits

---

## Deployment

### Base Mainnet
```bash
# Deploy
forge script script/Deploy.s.sol:DeployScript \
    --rpc-url $BASE_RPC_URL \
    --broadcast \
    --verify \
    -vvvv

# Outputs:
# AnankeAttestationRegistry: 0x...
# AnankeRevocationRegistry: 0x...
```

Update your `.env`:
```bash
ATTESTATION_REGISTRY_ADDR=0x...
REVOCATION_REGISTRY_ADDR=0x...
```

---

## Gas Costs (Base L2)

| Operation | Gas | ~Cost |
|-----------|-----|-------|
| Attest | 100k | $0.10 |
| Revoke | 50k | $0.05 |
| Check (read) | 0 | Free |

---

## EIP-712 Procedural Auth

### Client-Side (MetaMask)

```javascript
const signature = await signer._signTypedData(
  {
    name: "AnankeGeoPhase",
    version: "1",
    chainId: 8453,
    verifyingContract: "0xYourRegistryAddr"
  },
  {
    ProceduralAuth: [
      { name: "seedCommit", type: "bytes32" },
      { name: "mode", type: "uint8" },
      { name: "preset", type: "uint16" },
      { name: "expires", type: "uint64" },
      { name: "nonce", type: "bytes32" }
    ]
  },
  {
    seedCommit: "0x...",
    mode: 0,
    preset: 42,
    expires: Math.floor(Date.now()/1000) + 3600,
    nonce: "0x..."
  }
);
```

### Server-Side (Python)

```python
from geophase.eth import verify_procedural_auth

if verify_procedural_auth(message, signature, user_addr):
    # Authorized
    proceed_with_generation()
```

---

## Security

- **Write-once attestations** (no overwrites)
- **Always check revocation** (pre-generation gate)
- **Short signature TTL** (1 hour recommended)
- **No upgradability** (simple, auditable contracts)
- **Server-side wallet** (user doesn't pay gas)

See [THREAT-MODEL-ETH.md](docs/eth/THREAT-MODEL-ETH.md) for full analysis.

---

## Testing

```bash
# Unit tests (Python)
pytest tests/test_geocommit.py

# Contract tests (Foundry)
forge test

# Integration test
python scripts/test_chain_integration.py
```

---

## Roadmap

### v0.1 (Current)
- ✅ Attestation + Revocation contracts
- ✅ Python SDK
- ✅ FastAPI middleware
- ✅ Documentation

### v0.2 (Next)
- [ ] Seed Rights NFT (regeneration rights)
- [ ] Zero-knowledge proofs (privacy-preserving verification)
- [ ] Multi-sig governance (DAO)

### v0.3 (Future)
- [ ] Cross-chain bridge (Polygon, Arbitrum)
- [ ] Decentralized storage (IPFS/Arweave)
- [ ] Privacy pools (anonymity sets)

---

## Support

- **Docs:** [/docs/eth](docs/eth/)
- **Issues:** GitHub Issues
- **Contact:** FractalFuryan

---

**License:** MIT  
**Maintained by:** FractalFuryan  
**Built with:** ⚙️⛓️⭕️🛑
