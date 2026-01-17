# GeoPhase ↔ Base: Quick Reference

**One-page cheat sheet for developers**

---

## 🚀 Installation (30 seconds)

```bash
# 1. Clone/navigate to repo
cd dual-chain-geophase

# 2. Install Python deps
pip install -r requirements.txt

# 3. Copy env template
cp .env.example .env

# 4. Edit .env (add your keys)
nano .env
```

---

## ⚙️ Configuration

### .env File
```bash
BASE_RPC_URL=https://mainnet.base.org
CHAIN_ID=8453
ATTESTATION_REGISTRY_ADDR=0x...  # After deployment
REVOCATION_REGISTRY_ADDR=0x...   # After deployment
PRIVATE_KEY=0x...                # Optional (for writes)
```

---

## 📝 Contract Deployment

```bash
# Install Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Deploy to Base
./deploy.sh

# Copy addresses to .env
# ATTESTATION_REGISTRY_ADDR=0x...
# REVOCATION_REGISTRY_ADDR=0x...
```

---

## 🐍 Python Usage

### Compute GeoCommit
```python
from geophase.eth import *

# Compute hashes
seed_commit = compute_seed_commit(seed, user_nonce)
phaseA_hash = compute_phase_hash(phaseA_vector)
phaseB_hash = compute_phase_hash(phaseB_vector)

# Build params
params = GeoCommitParams(
    seed_commit=seed_commit,
    phaseA_hash=phaseA_hash,
    phaseB_hash=phaseB_hash,
    policy_id=policy_id,
    version=1
)

# Compute geoCommit
geo_commit = compute_geo_commit(params)
```

### Check Revocation
```python
from geophase.eth import ChainClient, load_config_from_env

client = ChainClient(load_config_from_env())

if client.is_revoked(geo_commit):
    print("❌ Revoked")
else:
    print("✅ Not revoked")
```

### Attest On-Chain
```python
tx_hash = client.attest(
    geo_commit=geo_commit,
    ethics_anchor=ethics_anchor,
    policy_id=policy_id,
    version=1
)
print(f"Attested: {tx_hash}")
```

---

## 🔐 EIP-712 Signatures

### Client-Side (JavaScript)
```javascript
const signature = await signer._signTypedData(
  {
    name: "AnankeGeoPhase",
    version: "1",
    chainId: 8453,
    verifyingContract: "0x..."
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
  message
);
```

### Server-Side (Python)
```python
from geophase.eth import verify_procedural_auth

if verify_procedural_auth(message, signature, user_addr):
    # ✅ Authorized
    proceed()
```

---

## 🌐 FastAPI Integration

### Middleware (Auto-Check)
```python
from fastapi import FastAPI
from geophase.eth.fastapi_middleware import GeoPhaseChainMiddleware

app = FastAPI()

middleware = GeoPhaseChainMiddleware(
    enabled=True,
    enforce_revocation=True
)
app.middleware("http")(middleware)
```

### Manual Check (Endpoint)
```python
@app.post("/generate")
async def generate(params: Params):
    # Compute geoCommit
    geo_commit = compute_geo_commit(params)
    
    # Check revocation
    if client.is_revoked(geo_commit):
        raise HTTPException(403, "Revoked")
    
    # Generate
    return generate_output(params)
```

---

## 🧪 Testing

### Off-Chain Tests
```bash
python scripts/test_chain_integration.py
```

### On-Chain Tests (requires deployed contracts)
```bash
python -c "
from geophase.eth import ChainClient, load_config_from_env
client = ChainClient(load_config_from_env())
print('Revocation check:', client.is_revoked(b'\x00' * 32))
"
```

### Example Server
```bash
python scripts/example_server.py
# Visit http://localhost:8000/docs
```

---

## 📊 Gas Costs (Base L2)

| Operation | Gas | ~Cost |
|-----------|-----|-------|
| Attest | 100k | $0.10 |
| Revoke | 50k | $0.05 |
| Check (read) | 0 | Free |

---

## 🔑 Key Functions

### Commitment Computation
```python
compute_geo_commit(params)      # Main commitment
compute_seed_commit(seed, nonce) # Seed hash
compute_phase_hash(vector)       # Phase hash
compute_ethics_anchor(doc, ts)   # Ethics hash
```

### Chain Operations
```python
client.is_revoked(geo_commit)    # Check revocation (read)
client.get_attestation(geo_commit) # Get attestation (read)
client.attest(...)               # Write attestation (write)
```

### Utilities
```python
bytes32_to_hex(b)  # bytes → 0x...
hex_to_bytes32(h)  # 0x... → bytes
generate_nonce()   # Random 32 bytes
```

---

## 📚 Documentation Quick Links

| Doc | Purpose |
|-----|---------|
| [ETH-BRIDGE-README.md](../ETH-BRIDGE-README.md) | Overview |
| [GEO-COMMIT-SPEC.md](../docs/eth/GEO-COMMIT-SPEC.md) | Commitment format |
| [EIP712-PROCEDURAL-AUTH.md](../docs/eth/EIP712-PROCEDURAL-AUTH.md) | Signatures |
| [THREAT-MODEL-ETH.md](../docs/eth/THREAT-MODEL-ETH.md) | Security |
| [DEPLOYMENT.md](../docs/eth/DEPLOYMENT.md) | Deployment |

---

## ⚠️ Common Pitfalls

### ❌ Storing raw seeds on-chain
```python
# WRONG
contract.store(seed)  # Never do this!

# RIGHT
seed_commit = compute_seed_commit(seed, nonce)
contract.store(seed_commit)  # Store hash only
```

### ❌ Not checking revocation
```python
# WRONG
def generate(params):
    return generate_output(params)  # Missing check!

# RIGHT
def generate(params):
    if client.is_revoked(geo_commit):
        raise Exception("Revoked")
    return generate_output(params)
```

### ❌ Expired signatures
```python
# WRONG
expires = time.time() + 86400  # 24 hours (too long!)

# RIGHT
expires = time.time() + 3600  # 1 hour (safe)
```

---

## 🆘 Troubleshooting

### "Cannot connect to RPC"
→ Check `BASE_RPC_URL` in `.env`  
→ Try public RPC: `https://mainnet.base.org`

### "Contract not deployed"
→ Run `./deploy.sh`  
→ Update `ATTESTATION_REGISTRY_ADDR` in `.env`

### "Insufficient funds"
→ Deployer wallet needs ETH  
→ Bridge from mainnet: https://bridge.base.org

### "Signature verification failed"
→ Check `chainId` (8453 for Base)  
→ Check `verifyingContract` address  
→ Check message `expires` timestamp

---

## 📞 Support

- **Docs:** `/docs/eth/`
- **Issues:** GitHub Issues
- **Contact:** FractalFuryan

---

**Built with:** ⚙️⛓️⭕️🛑  
**License:** MIT
