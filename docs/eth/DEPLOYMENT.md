# GeoPhase → Base Deployment Guide

**Target:** Base Mainnet (Chain ID: 8453)  
**Contracts:** Attestation + Revocation Registries

---

## Prerequisites

### 1. Install Foundry

```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

### 2. Get Base RPC

**Free RPCs:**
- Public: `https://mainnet.base.org`
- Alchemy: `https://base-mainnet.g.alchemy.com/v2/YOUR_KEY`
- QuickNode: `https://your-endpoint.base.quiknode.pro/YOUR_KEY`

### 3. Get Basescan API Key

1. Visit https://basescan.org/
2. Create account → API Keys
3. Generate new key

---

## Deployment Steps

### 1. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```bash
BASE_RPC_URL=https://mainnet.base.org
BASESCAN_API_KEY=YOUR_BASESCAN_KEY
PRIVATE_KEY=0xYOUR_DEPLOYER_PRIVATE_KEY
CHAIN_ID=8453
```

⚠️ **Security:**
- Use a fresh deployer wallet (not your main wallet)
- Fund with ~0.001 ETH for deployment gas
- Never commit `.env` to git

### 2. Install Forge Dependencies

```bash
forge install foundry-rs/forge-std
```

### 3. Test Contracts Locally

```bash
# Compile
forge build

# Run tests (if any)
forge test

# Check gas costs
forge test --gas-report
```

### 4. Deploy to Base Mainnet

```bash
./deploy.sh
```

**Expected output:**
```
🚀 Deploying Ananke contracts to Base...

AnankeAttestationRegistry deployed at: 0x1234...
AnankeRevocationRegistry deployed at: 0x5678...

=== DEPLOYMENT COMPLETE ===
Network: Base
Attestation Registry: 0x1234...
Revocation Registry: 0x5678...

Add to .env:
ATTESTATION_REGISTRY_ADDR=0x1234...
REVOCATION_REGISTRY_ADDR=0x5678...
```

### 5. Verify Contracts on Basescan

Verification happens automatically if:
- `BASESCAN_API_KEY` is set
- `--verify` flag is in deploy script

Manual verification (if needed):
```bash
forge verify-contract \
    --chain-id 8453 \
    --compiler-version v0.8.20 \
    0x1234... \
    contracts/AnankeAttestationRegistry.sol:AnankeAttestationRegistry \
    --etherscan-api-key $BASESCAN_API_KEY
```

### 6. Update Configuration

Add to `.env`:
```bash
ATTESTATION_REGISTRY_ADDR=0x1234...
REVOCATION_REGISTRY_ADDR=0x5678...
```

---

## Post-Deployment

### 1. Test On-Chain Reads

```python
from geophase.eth import ChainClient, load_config_from_env

config = load_config_from_env()
client = ChainClient(config)

# Test revocation check (should be False for random hash)
test_hash = b'\x00' * 32
is_revoked = client.is_revoked(test_hash)
print(f"Revocation check works: {is_revoked == False}")
```

### 2. Test On-Chain Write (Attestation)

```python
from geophase.eth import compute_geo_commit, GeoCommitParams, generate_nonce

# Generate test commitment
params = GeoCommitParams(
    seed_commit=generate_nonce(),
    phaseA_hash=generate_nonce(),
    phaseB_hash=generate_nonce(),
    policy_id=generate_nonce(),
    version=1
)
geo_commit = compute_geo_commit(params)

# Attest (requires PRIVATE_KEY in .env)
tx_hash = client.attest(
    geo_commit=geo_commit,
    ethics_anchor=generate_nonce(),
    policy_id=params.policy_id,
    version=1
)

print(f"Attestation tx: {tx_hash}")
```

### 3. Monitor Contracts

**Basescan URLs:**
- Attestation: `https://basescan.org/address/0x1234...`
- Revocation: `https://basescan.org/address/0x5678...`

**Track events:**
- `Attested(geoCommit, ethicsAnchor, policyId, ...)`
- `Revoked(key, revoker, timestamp)`

---

## Gas Costs

| Operation | Gas | Cost (ETH) | Cost (USD @ $3k ETH) |
|-----------|-----|------------|----------------------|
| Deploy Attestation | ~500k | 0.0005 | $1.50 |
| Deploy Revocation | ~250k | 0.00025 | $0.75 |
| First `attest()` | ~100k | 0.0001 | $0.30 |
| Subsequent `attest()` | ~50k | 0.00005 | $0.15 |
| `revoke()` | ~50k | 0.00005 | $0.15 |

**Total deployment cost:** ~$2.50 (one-time)

---

## Troubleshooting

### "Nonce too low"
- Another transaction is pending
- Wait 30 seconds and retry

### "Insufficient funds"
- Deployer wallet needs ETH
- Bridge from Ethereum mainnet: https://bridge.base.org

### "Verification failed"
- Check compiler version matches (`solc 0.8.20`)
- Ensure constructor args are correct (none in v1)
- Retry with `--force` flag

### "RPC rate limited"
- Switch to paid RPC (Alchemy/QuickNode)
- Add delays between calls

---

## Security Checklist

- [ ] Deployer wallet is fresh (not reused)
- [ ] Private key stored in secrets manager (not `.env` in prod)
- [ ] Contracts verified on Basescan
- [ ] No user data in test attestations
- [ ] Revocation check works (test script passes)
- [ ] Server config updated with contract addresses

---

## Mainnet vs. Testnet

### Base Sepolia (Testnet)
```bash
BASE_RPC_URL=https://sepolia.base.org
CHAIN_ID=84532
```

**Use testnet for:**
- Development
- Integration testing
- Gas estimation

**Use mainnet for:**
- Production
- Real user data (commitments only!)

---

## Next Steps

1. ✅ Deploy contracts
2. ✅ Verify on Basescan
3. ✅ Update `.env`
4. Install Python deps: `pip install -r requirements.txt`
5. Run integration tests: `python scripts/test_chain_integration.py`
6. Wire up FastAPI middleware
7. Test end-to-end flow (sign → generate → attest)

---

**Questions?** See [ETH-BRIDGE-README.md](ETH-BRIDGE-README.md)
