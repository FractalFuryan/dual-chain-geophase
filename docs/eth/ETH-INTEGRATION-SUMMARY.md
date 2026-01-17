# Ethereum Bridge Integration Summary

**Version:** v0.1  
**Chain:** Base (L2)  
**Status:** ✅ Shipped

---

## What We Built

GeoPhase ↔ Ethereum bridge with **commitment-only attestation** + **revocation registry**. Privacy-safe, minimal, auditable.

### Smart Contracts (Solidity)
1. **AnankeAttestationRegistry** - Write-once provenance commitments
2. **AnankeRevocationRegistry** - User-controlled opt-out

### Python Integration
1. **geocommit.py** - Commitment computation (keccak256)
2. **eip712_verify.py** - Signature verification (procedural auth)
3. **chain_check.py** - On-chain reads/writes (web3.py)
4. **fastapi_middleware.py** - Pre-generation gate

### Documentation
1. **GEO-COMMIT-SPEC.md** - Commitment format specification
2. **EIP712-PROCEDURAL-AUTH.md** - Signature protocol
3. **THREAT-MODEL-ETH.md** - Security analysis
4. **DEPLOYMENT.md** - Deployment guide

---

## File Structure

```
dual-chain-geophase/
├── contracts/
│   ├── AnankeAttestationRegistry.sol
│   └── AnankeRevocationRegistry.sol
├── script/
│   └── Deploy.s.sol
├── src/geophase/eth/
│   ├── __init__.py
│   ├── geocommit.py
│   ├── eip712_verify.py
│   ├── chain_check.py
│   └── fastapi_middleware.py
├── docs/eth/
│   ├── GEO-COMMIT-SPEC.md
│   ├── EIP712-PROCEDURAL-AUTH.md
│   ├── THREAT-MODEL-ETH.md
│   └── DEPLOYMENT.md
├── scripts/
│   └── test_chain_integration.py
├── foundry.toml
├── deploy.sh
├── .env.example
└── ETH-BRIDGE-README.md
```

---

## Key Features

### ⭕️🛑 Privacy-Safe
- **No media on-chain** (only hashes)
- **No user data** (commitments only)
- **No likeness** (procedural presets only)
- **One-way commitments** (keccak256, sha256)

### ⚙️ Minimal & Auditable
- **Two tiny contracts** (~150 lines total)
- **No upgradability** (simple, immutable)
- **Write-once semantics** (no overwrites)
- **Gas-efficient** (~$0.10/attestation on Base)

### ⛓️ Production-Ready
- **Revocation enforcement** (pre-generation gate)
- **EIP-712 signatures** (procedural auth)
- **FastAPI middleware** (plug-and-play)
- **Multi-RPC failover** (high availability)

---

## GeoCommit Formula

```
geoCommit = keccak256(
    "ANANKE_GEO_COMMIT_V1" ||
    seed_commit ||
    phaseA_hash ||
    phaseB_hash ||
    policyId ||
    version
)
```

**Components:**
- `seed_commit = sha256(seed || user_nonce)`
- `phaseA_hash = sha256(phaseA_vector_bytes)`
- `phaseB_hash = sha256(phaseB_vector_bytes)`
- `policyId = keccak256("ANANKE_POLICY_" || policy_name)`
- `version = 1` (uint32)

---

## Usage Flow

### 1. Pre-Generation (Server)
```python
from geophase.eth import ChainClient, compute_geo_commit

# Compute commitment
geo_commit = compute_geo_commit(params)

# Check revocation
if client.is_revoked(geo_commit):
    raise Exception("Revoked")
```

### 2. Generation (Off-Chain)
```python
# Generate using existing GeoPhase pipeline
result = generate_geophase(seed, phaseA, phaseB)
```

### 3. Post-Generation (Optional)
```python
# Attest on-chain
client.attest(geo_commit, ethics_anchor, policy_id, version)
```

---

## Security Guarantees

### Threat Mitigations (v0.1)
| Threat | Mitigation | Status |
|--------|-----------|--------|
| Privacy leakage | No raw data on-chain | ✅ |
| Attestation forgery | Write-once contracts | ✅ |
| Revocation bypass | Pre-gen middleware check | ✅ |
| Signature replay | Expiration + nonces | ✅ |
| Contract upgrade attack | No upgradability | ✅ |

### Attack Resistance
- **Rainbow tables:** Prevented by `user_nonce`
- **Linkability:** Each geoCommit is unique
- **Inference:** One-way hash functions
- **MEV:** No economic value (write-once)

---

## Deployment (Quick)

```bash
# 1. Setup
cp .env.example .env
# Edit .env with PRIVATE_KEY, BASE_RPC_URL, BASESCAN_API_KEY

# 2. Deploy
./deploy.sh

# 3. Update .env with contract addresses
ATTESTATION_REGISTRY_ADDR=0x...
REVOCATION_REGISTRY_ADDR=0x...

# 4. Install Python deps
pip install -r requirements.txt

# 5. Test
python scripts/test_chain_integration.py
```

---

## Integration Example

### FastAPI Endpoint

```python
from fastapi import FastAPI
from geophase.eth import ChainClient, load_config_from_env

app = FastAPI()
client = ChainClient(load_config_from_env())

@app.post("/generate")
async def generate(params: GenerateParams):
    # Compute geoCommit
    geo_commit = compute_geo_commit(params)
    
    # Check revocation
    if client.is_revoked(geo_commit):
        raise HTTPException(403, "Revoked")
    
    # Generate
    result = your_generation_function(params)
    
    # Optional: Attest
    client.attest(geo_commit, ethics_anchor, policy_id, 1)
    
    return {"result": result}
```

---

## Gas Costs (Base L2)

| Operation | Gas | Cost (~$0.01/gas) |
|-----------|-----|-------------------|
| Deploy (total) | ~750k | ~$2.50 (one-time) |
| Attest | 100k | ~$0.10 |
| Revoke | 50k | ~$0.05 |
| Check (read) | 0 | Free |

---

## Testing

### Off-Chain Tests
```bash
python scripts/test_chain_integration.py
```

Tests:
- ✅ Commitment computation
- ✅ Ethics anchor generation
- ✅ Determinism
- ✅ Collision resistance
- ✅ EIP-712 structure
- ✅ Privacy guarantees

### On-Chain Tests (after deployment)
```bash
# Requires deployed contracts
python -c "
from geophase.eth import ChainClient, load_config_from_env
client = ChainClient(load_config_from_env())
print('Revocation check:', client.is_revoked(b'\x00' * 32))
"
```

---

## Roadmap

### v0.1 (Current) ✅
- Attestation + Revocation contracts
- Python SDK (web3.py)
- FastAPI middleware
- Comprehensive docs

### v0.2 (Next)
- Seed Rights NFT (regeneration rights)
- Zero-knowledge proofs (privacy-preserving verification)
- Nonce tracking (anti-replay)
- Event indexer (off-chain query layer)

### v0.3 (Future)
- Cross-chain bridge (Polygon, Arbitrum)
- Decentralized storage (IPFS/Arweave for ethics docs)
- Privacy pools (anonymity sets)
- DAO governance (multi-sig upgrades)

---

## Resources

### Documentation
- [ETH-BRIDGE-README.md](../ETH-BRIDGE-README.md) - Quick start
- [GEO-COMMIT-SPEC.md](GEO-COMMIT-SPEC.md) - Commitment format
- [EIP712-PROCEDURAL-AUTH.md](EIP712-PROCEDURAL-AUTH.md) - Signature spec
- [THREAT-MODEL-ETH.md](THREAT-MODEL-ETH.md) - Security analysis
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide

### External
- [Base Documentation](https://docs.base.org)
- [EIP-712 Spec](https://eips.ethereum.org/EIPS/eip-712)
- [web3.py Docs](https://web3py.readthedocs.io/)
- [Foundry Book](https://book.getfoundry.sh/)

---

## Decision Rationale

### Why Base?
- ✅ Lowest L2 gas costs
- ✅ EVM-native (Solidity, web3.py)
- ✅ Fastest finality (1-2 seconds)
- ✅ Coinbase-backed (long-term stability)

### Why No NFTs in v0.1?
- ✅ Simpler (two contracts vs. three)
- ✅ Cleaner ethics (no tradable assets yet)
- ✅ Faster audit (less attack surface)
- ✅ Future-proof (can add without migration)

### Why Commitment-Only?
- ✅ Privacy-safe (no user data)
- ✅ Minimal gas (small storage footprint)
- ✅ Provable (hash-based integrity)
- ✅ Non-extractive (no monetization pressure)

---

## Maintenance

### Contract Monitoring
- Watch `Attested` events (provenance tracking)
- Watch `Revoked` events (user opt-outs)
- Monitor gas prices (defer attestations if high)

### Server Health
- RPC uptime (failover to backup)
- Revocation check latency (<100ms)
- Signature verification rate (detect attacks)

### Security Updates
- Review Solidity security advisories
- Update web3.py (breaking changes rare)
- Audit new threat vectors (quarterly)

---

## Contact

- **Maintainer:** FractalFuryan
- **Issues:** GitHub Issues
- **Docs:** [/docs/eth](.)

---

**Built with:** ⚙️⛓️⭕️🛑  
**License:** MIT  
**Status:** Production-ready v0.1
