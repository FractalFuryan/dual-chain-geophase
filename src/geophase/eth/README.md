# GeoPhase EIP-712 PolicyGrant Layer

**Drop-in capability token authentication for GeoPhase with wallet-native signatures and on-chain revocation.**

## Overview

This module provides:

✅ **Wallet-native signatures** (secp256k1 via EIP-712)  
✅ **Base L2 on-chain revocation** (fail-closed)  
✅ **Modes + rights bitflags + expiry**  
✅ **Procedural seed-family tokens** (NOT likeness/identity)  
✅ **No user identifiers** and **no analytics storage**

## Architecture

```
┌─────────────────┐
│  Client Wallet  │
│   (secp256k1)   │
└────────┬────────┘
         │ EIP-712 signature
         ▼
┌─────────────────────┐
│  PolicyGrant Token  │  ◄── capability token (not identity)
│  - commit           │
│  - policy_id        │
│  - mode/rights      │
│  - expiry           │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   FastAPI Gate      │  ◄── fail-closed verification
│  - verify signature │
│  - check expiry     │
│  - check revocation │ ──► Base L2
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   GeoPhase API      │
│   (authenticated)   │
└─────────────────────┘
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start example API server

```bash
uvicorn geophase.eth.example_api:app --reload
```

### 3. Sign and send a grant

```bash
python scripts/sign_policy_grant.py
```

### 4. Test with curl

```bash
# Get verifier metadata
curl http://localhost:8000/.well-known/geophase-verifier.json

# Make authenticated request (headers from sign_policy_grant.py output)
curl -X POST http://localhost:8000/v1/generate \
  -H "X-Policy-Grant: {...}" \
  -H "X-Policy-Signature: 0x..." \
  -H "X-Policy-Signer: 0x..."
```

## Core Components

### PolicyGrant Model

Capability token representing permission to generate under a specific policy:

```python
from geophase.eth.policy_grant import PolicyGrant, Rights, Mode

grant = PolicyGrant(
    commit="0x" + "22" * 32,           # geo_commit hash
    policy_id="0x...",                  # keccak256("POLICY_NAME")
    mode=int(Mode.STANDARD),            # STANDARD or CLINICAL
    rights=int(Rights.FRAME),           # bitflags: FRAME, VIDEO, MP4, STREAM
    exp=int(time.time()) + 3600,        # unix timestamp
    nonce="0x" + os.urandom(32).hex(),  # anti-replay
    engine_version=1,
)
```

**CRITICAL BOUNDARY**: `seed_family_id` is a *procedural selection token*, NOT identity/likeness. No biometric inputs, no resemblance targets.

### EIP-712 Verifier

Verifies wallet signatures over typed structured data:

```python
from geophase.eth.eip712_policy_grant import PolicyGrantVerifier

verifier = PolicyGrantVerifier(
    name="GeoPhase",
    version="0.1.1",
    chain_id=8453,  # Base mainnet
    verifying_contract="0x...",
)

verified = verifier.verify(grant, signature_hex, expected_signer=address)
# Returns: VerifiedGrant(signer=address, grant=grant)
```

### FastAPI Gate (Fail-Closed)

Dependency that enforces authorization with on-chain revocation checks:

```python
from geophase.eth.fastapi_gate import build_gate_dependency, GateConfig
from geophase.eth.policy_grant import Rights

gate = build_gate_dependency(
    verifier=verifier,
    chain=chain_client,  # implements is_revoked(commit_hex) -> bool
    cfg=GateConfig(strict_chain=True, strict_revocation=True),
    required_rights=int(Rights.FRAME),
)

@app.post("/generate")
def generate(grant: VerifiedGrant = Depends(gate)):
    # Only reaches here if:
    # - signature valid
    # - not expired
    # - not revoked on-chain
    # - has FRAME rights
    return {"ok": True}
```

### Well-Known Metadata Endpoint

Discovery endpoint for clients to get signing parameters:

```python
from geophase.eth.well_known import VerifierMetadata, as_json

@app.get("/.well-known/geophase-verifier.json")
def well_known():
    meta = VerifierMetadata(
        eip712_name="GeoPhase",
        eip712_version="0.1.1",
        chain_id=8453,
        verifying_contract="0x...",
        attestation_registry="0x...",
        revocation_registry="0x...",
        bytecode_lock_hash="0x...",
        ethics_anchor="65b14d584f5a5fd070fe985eeb86e14cb3ce56a4fc41fd9e987f2259fe1f15c1",
        policy_ids=["0x..."],
    )
    return as_json(meta)
```

## Rights Bitflags

```python
from geophase.eth.policy_grant import Rights

Rights.FRAME   = 1 << 0  # 1  - single frame generation
Rights.VIDEO   = 1 << 1  # 2  - video generation
Rights.MP4     = 1 << 2  # 4  - MP4 export
Rights.STREAM  = 1 << 3  # 8  - streaming

# Combine with bitwise OR
combined = int(Rights.FRAME) | int(Rights.VIDEO)  # 3
```

**NEVER** tie rights to realism tiers or engagement metrics.

## Modes

```python
from geophase.eth.policy_grant import Mode

Mode.STANDARD = 0  # standard generation
Mode.CLINICAL = 1  # clinical/research use
```

## Security Model

### Fail-Closed Design

1. **Signature verification**: If signature invalid → DENY
2. **Expiry check**: If expired → DENY
3. **Rights check**: If insufficient rights → DENY
4. **Revocation check**: 
   - If chain unreachable and `strict_chain=True` → DENY (503)
   - If commit revoked → DENY

### No User Identifiers

- PolicyGrant contains **no biometric data**
- PolicyGrant contains **no personal identifiers**
- `seed_family_id` is **procedural**, not likeness-based
- No analytics, no tracking, no user profiling

### Replay Protection

- Each grant has a unique `nonce`
- Grants expire after `exp` timestamp
- Clock skew allowed via `clock_skew_sec` parameter

## Client-Side Signing

### Python Example

```python
from eth_account import Account
from eth_account.messages import encode_typed_data

acct = Account.from_key(private_key)
msg = encode_typed_data(full_message=verifier.typed_data(grant))
signature = acct.sign_message(msg).signature.hex()
```

### JavaScript/TypeScript Example

```typescript
import { ethers } from 'ethers';

const domain = {
  name: 'GeoPhase',
  version: '0.1.1',
  chainId: 8453,
  verifyingContract: '0x...',
};

const types = {
  PolicyGrant: [
    { name: 'commit', type: 'bytes32' },
    { name: 'policy_id', type: 'bytes32' },
    { name: 'mode', type: 'uint8' },
    { name: 'rights', type: 'uint32' },
    { name: 'exp', type: 'uint64' },
    { name: 'nonce', type: 'bytes32' },
    { name: 'engine_version', type: 'uint32' },
  ],
};

const signer = new ethers.Wallet(privateKey);
const signature = await signer._signTypedData(domain, types, grant);
```

## On-Chain Integration

### Revocation Registry Interface

Your chain client must implement:

```python
class ChainClientProtocol:
    def is_revoked(self, commit_hex: str) -> bool:
        """
        Check if commit is revoked on Base L2.
        
        Returns:
            True if revoked, False otherwise
            
        Raises:
            Exception on chain communication failure
        """
```

### Example Implementation (Web3.py)

```python
from web3 import Web3

class BaseChainClient:
    def __init__(self, rpc_url: str, registry_address: str, registry_abi: list):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.registry = self.w3.eth.contract(
            address=registry_address,
            abi=registry_abi
        )
    
    def is_revoked(self, commit_hex: str) -> bool:
        return self.registry.functions.isRevoked(commit_hex).call()
```

## Testing

```bash
# Run all tests
pytest tests/test_policy_grant.py -v

# Run specific test
pytest tests/test_policy_grant.py::test_valid_signature -v
```

## Configuration

Environment variables:

```bash
# EIP-712 Domain
GEOPHASE_VERIFIER_NAME="GeoPhase"
GEOPHASE_VERIFIER_VERSION="0.1.1"
GEOPHASE_CHAIN_ID=8453  # Base mainnet

# Contract Addresses
GEOPHASE_VERIFYING_CONTRACT="0x..."
GEOPHASE_ATTESTATION_REGISTRY="0x..."
GEOPHASE_REVOCATION_REGISTRY="0x..."

# Security
GEOPHASE_BYTECODE_LOCK_HASH="0x..."
```

## Production Checklist

- [ ] Replace stub chain client with actual Base L2 integration
- [ ] Deploy revocation registry contract to Base
- [ ] Configure verifying contract address
- [ ] Set up secure key management (HSM/KMS)
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS policies
- [ ] Set up monitoring for chain availability
- [ ] Document policy IDs (keccak256 of policy strings)
- [ ] Audit bytecode lock hash
- [ ] Test fail-closed behavior under chain outage

## File Structure

```
geophase/eth/
├── __init__.py              # Module exports
├── policy_grant.py          # PolicyGrant model & validation
├── eip712_policy_grant.py   # EIP-712 verifier
├── well_known.py            # Discovery endpoint metadata
├── fastapi_gate.py          # Fail-closed gate dependency
└── example_api.py           # Example FastAPI application

scripts/
└── sign_policy_grant.py     # Client-side signing example

tests/
└── test_policy_grant.py     # Comprehensive test suite
```

## License

See [LICENSE](../../../LICENSE) file.

## Ethics Anchor

This implementation enforces the ANANKE ethics policy:
- **No likeness capture** (procedural generation only)
- **No user tracking** (no identifiers stored)
- **Fail-closed security** (deny on uncertainty)
- **Revocable grants** (on-chain control)

Ethics anchor hash: `65b14d584f5a5fd070fe985eeb86e14cb3ce56a4fc41fd9e987f2259fe1f15c1`
