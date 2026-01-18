# EIP-712 PolicyGrant Authentication Layer

**Version:** 0.1.1  
**Status:** Implementation Complete  
**Date:** January 18, 2026

## Summary

A complete EIP-712 capability token authentication system for GeoPhase that provides:

- **Wallet-native signatures** using secp256k1 and EIP-712 typed structured data
- **On-chain revocation** checking via Base L2 (fail-closed)
- **Rights-based authorization** with bitflags (FRAME, VIDEO, MP4, STREAM)
- **Mode selection** (STANDARD, CLINICAL)
- **Zero user tracking** - no identifiers, no analytics, no biometrics
- **Procedural seed-family tokens** - NOT likeness/identity capture

## Key Design Principles

### 1. Fail-Closed Security

The system denies access when:
- Signature is invalid
- Grant has expired
- Insufficient rights
- Commit is revoked on-chain
- Chain communication fails (when `strict_chain=True`)

### 2. Privacy-First

- **No user identifiers stored** anywhere
- **No biometric data** in PolicyGrant
- **No analytics or tracking**
- `seed_family_id` is purely procedural (e.g., "synthwave-vibe"), not likeness-based

### 3. Capability Token Model

PolicyGrant is a **capability token**, not an identity token:
- Grants specific rights (FRAME, VIDEO, etc.)
- Tied to a specific `geo_commit` (content hash)
- Bound to a specific policy (`policy_id`)
- Time-limited (`exp` timestamp)
- Replay-protected (`nonce`)

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Client Application                       │
│  - Generates geo_commit (GeoPhase dual-phase computation)    │
│  - Creates PolicyGrant with desired rights                   │
│  - Signs with wallet (EIP-712)                              │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        │ HTTP Headers:
                        │   X-Policy-Grant: {grant JSON}
                        │   X-Policy-Signature: 0x...
                        │   X-Policy-Signer: 0x...
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI Gate (Verifier)                   │
│  1. Parse PolicyGrant JSON                                   │
│  2. Verify EIP-712 signature                                 │
│  3. Check expiry (with clock skew tolerance)                 │
│  4. Verify rights match requirements                         │
│  5. Check on-chain revocation status ───────────────────────┐│
└───────────────────────┬──────────────────────────────────────┘│
                        │                                        │
                        │ Authorized VerifiedGrant               │
                        │                                        │
                        ▼                                        │
┌──────────────────────────────────────────────────────────────┐│
│                    GeoPhase API Endpoint                      ││
│  - /v1/generate (requires FRAME)                             ││
│  - /v1/generate/video (requires VIDEO)                       ││
│  - /v1/stream (requires STREAM)                              ││
└──────────────────────────────────────────────────────────────┘│
                                                                 │
                        ┌────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│              Base L2 Revocation Registry                      │
│  - Smart contract with is_revoked(commit) -> bool           │
│  - Immutable on-chain state                                  │
│  - Fail-closed on chain communication failure                │
└──────────────────────────────────────────────────────────────┘
```

## Components

### 1. PolicyGrant Model

**File:** [src/geophase/eth/policy_grant.py](../src/geophase/eth/policy_grant.py)

Core data structure representing a capability token:

```python
class PolicyGrant(BaseModel):
    commit: str                    # 0x... bytes32 hex of geo_commit
    policy_id: str                 # 0x... bytes32 hex (keccak256 of policy name)
    mode: int                      # Mode.STANDARD or Mode.CLINICAL
    rights: int                    # Bitflags: FRAME | VIDEO | MP4 | STREAM
    exp: int                       # Unix timestamp expiry
    nonce: str                     # 0x... bytes32 hex anti-replay token
    engine_version: int            # Protocol version (currently 1)
    seed_family_id: Optional[str]  # Procedural seed (NOT likeness)
```

**Rights Bitflags:**
- `FRAME = 1 << 0` (1) - Single frame generation
- `VIDEO = 1 << 1` (2) - Video generation
- `MP4 = 1 << 2` (4) - MP4 export
- `STREAM = 1 << 3` (8) - Streaming

**Modes:**
- `STANDARD = 0` - Normal generation
- `CLINICAL = 1` - Clinical/research use

### 2. EIP-712 Verifier

**File:** [src/geophase/eth/eip712_policy_grant.py](../src/geophase/eth/eip712_policy_grant.py)

Verifies EIP-712 signatures using standard Ethereum cryptography:

```python
verifier = PolicyGrantVerifier(
    name="GeoPhase",              # EIP-712 domain name
    version="0.1.1",              # EIP-712 domain version
    chain_id=8453,                # Base mainnet
    verifying_contract="0x...",   # Verifying contract address
    clock_skew_sec=30,            # Allowed clock skew for expiry
)

verified = verifier.verify(grant, signature_hex, expected_signer="0x...")
# Returns: VerifiedGrant(signer="0x...", grant=PolicyGrant(...))
```

### 3. FastAPI Gate

**File:** [src/geophase/eth/fastapi_gate.py](../src/geophase/eth/fastapi_gate.py)

Dependency factory for fail-closed authorization:

```python
gate = build_gate_dependency(
    verifier=verifier,
    chain=chain_client,           # Implements is_revoked(commit) -> bool
    cfg=GateConfig(
        strict_chain=True,         # Fail if chain unreachable
        strict_revocation=True,    # Fail if revocation check fails
        require_grant=True,        # Require grant headers
    ),
    required_rights=int(Rights.FRAME),
)

@app.post("/generate")
def generate(grant: VerifiedGrant = Depends(gate)):
    # Only reachable if all checks pass
    return {"ok": True, "signer": grant.signer}
```

### 4. Well-Known Discovery

**File:** [src/geophase/eth/well_known.py](../src/geophase/eth/well_known.py)

Metadata endpoint for client discovery:

```python
@app.get("/.well-known/geophase-verifier.json")
def well_known():
    return {
        "eip712_name": "GeoPhase",
        "eip712_version": "0.1.1",
        "chain_id": 8453,
        "verifying_contract": "0x...",
        "attestation_registry": "0x...",
        "revocation_registry": "0x...",
        "bytecode_lock_hash": "0x...",
        "ethics_anchor": "65b14d584f5a5fd070fe985eeb86e14cb3ce56a4fc41fd9e987f2259fe1f15c1",
        "policy_ids": ["0x..."]
    }
```

## Usage Examples

### Server-Side (API)

See [src/geophase/eth/example_api.py](../src/geophase/eth/example_api.py)

### Client-Side (Signing)

See [scripts/sign_policy_grant.py](../scripts/sign_policy_grant.py)

```python
from eth_account import Account
from geophase.eth.policy_grant import PolicyGrant, Rights
from geophase.eth.eip712_policy_grant import PolicyGrantVerifier

# Create grant
grant = PolicyGrant(
    commit="0x" + "22" * 32,
    policy_id=keccak256("ANANKE_POLICY_V1_STANDARD"),
    mode=0,
    rights=int(Rights.FRAME),
    exp=int(time.time()) + 3600,
    nonce="0x" + os.urandom(32).hex(),
    engine_version=1,
)

# Sign with wallet
verifier = PolicyGrantVerifier(...)
acct = Account.from_key(private_key)
msg = encode_typed_data(full_message=verifier.typed_data(grant))
signature = acct.sign_message(msg).signature.hex()

# Send to API
headers = {
    "X-Policy-Grant": grant.model_dump_json(),
    "X-Policy-Signature": signature,
    "X-Policy-Signer": acct.address,
}
```

## Testing

All tests pass (12/12):

```bash
$ pytest tests/test_policy_grant.py -v
================================================= test session starts =================================================
tests/test_policy_grant.py::test_valid_signature PASSED                                                         [  8%]
tests/test_policy_grant.py::test_expired_rejected PASSED                                                        [ 16%]
tests/test_policy_grant.py::test_domain_mismatch_rejected PASSED                                                [ 25%]
tests/test_policy_grant.py::test_signer_mismatch_rejected PASSED                                                [ 33%]
tests/test_policy_grant.py::test_rights_bitflags PASSED                                                         [ 41%]
tests/test_policy_grant.py::test_mode_values PASSED                                                             [ 50%]
tests/test_policy_grant.py::test_invalid_bytes32_rejected PASSED                                                [ 58%]
tests/test_policy_grant.py::test_invalid_mode_rejected PASSED                                                   [ 66%]
tests/test_policy_grant.py::test_invalid_rights_rejected PASSED                                                 [ 75%]
tests/test_policy_grant.py::test_to_eip712_message PASSED                                                       [ 83%]
tests/test_policy_grant.py::test_clock_skew PASSED                                                              [ 91%]
tests/test_policy_grant.py::test_recover_signer PASSED                                                          [100%]
================================================= 12 passed in 0.66s ==================================================
```

## Security Considerations

### 1. No Identity/Likeness Coupling

- `seed_family_id` is **procedural only** (e.g., "retro-80s", "noir-style")
- **NEVER** couple to biometric data or resemblance targets
- **NEVER** create "make me" as identity - only as procedural seed selection

### 2. Fail-Closed Defaults

- Invalid signature → DENY (403)
- Expired grant → DENY (403)
- Insufficient rights → DENY (403)
- Revoked on-chain → DENY (403)
- Chain unreachable + strict mode → DENY (503)

### 3. Replay Protection

- Each grant has unique `nonce`
- Grants expire after `exp`
- Recommend short validity periods (1-2 hours)

### 4. On-Chain Revocation

- Immutable revocation registry on Base L2
- Client-side cannot bypass
- Server checks before processing
- Fail-closed on chain communication failure

## Production Deployment

### Prerequisites

1. **Deploy Revocation Registry** to Base L2
2. **Configure verifying contract** address
3. **Set up Base L2 RPC** endpoint
4. **Generate bytecode lock hash** for contract verification
5. **Document policy IDs** (keccak256 of policy strings)

### Environment Configuration

```bash
export GEOPHASE_VERIFIER_NAME="GeoPhase"
export GEOPHASE_VERIFIER_VERSION="0.1.1"
export GEOPHASE_CHAIN_ID=8453  # Base mainnet
export GEOPHASE_VERIFYING_CONTRACT="0x..."
export GEOPHASE_REVOCATION_REGISTRY="0x..."
export GEOPHASE_ATTESTATION_REGISTRY="0x..."
export GEOPHASE_BYTECODE_LOCK_HASH="0x..."
```

### Chain Client Implementation

Replace stub with actual Base L2 client:

```python
from web3 import Web3

class BaseChainClient(ChainClientProtocol):
    def __init__(self, rpc_url: str, registry_addr: str, abi: list):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.registry = self.w3.eth.contract(address=registry_addr, abi=abi)
    
    def is_revoked(self, commit_hex: str) -> bool:
        return self.registry.functions.isRevoked(commit_hex).call()
```

## Integration with GeoPhase

### 1. Generation Flow

```python
# Client generates geo_commit using dual-phase GeoPhase
geo_commit = geophase_dual_phase(lat, lon, salt)

# Create PolicyGrant for that specific commit
grant = PolicyGrant(
    commit=geo_commit,
    policy_id=keccak256("ANANKE_POLICY_V1_STANDARD"),
    ...
)

# Sign and send to API
```

### 2. Server Verification

```python
@app.post("/v1/generate")
def generate(grant: VerifiedGrant = Depends(gate_frame)):
    # Verify geo_commit matches expected format
    assert len(grant.grant.commit) == 66
    assert grant.grant.commit.startswith("0x")
    
    # Use commit for generation parameters
    # (commit is not user identity - it's a content hash)
    result = generate_frame(commit=grant.grant.commit)
    
    return result
```

### 3. Revocation Scenarios

- User requests content takedown → Revoke on-chain
- Policy violation detected → Revoke on-chain
- Covenant breach → Revoke on-chain

## Files Created

```
src/geophase/eth/
├── __init__.py                  # Module exports
├── policy_grant.py              # PolicyGrant model (118 lines)
├── eip712_policy_grant.py       # EIP-712 verifier (130 lines)
├── well_known.py                # Discovery metadata (45 lines)
├── fastapi_gate.py              # Fail-closed gate (145 lines)
├── example_api.py               # Example FastAPI app (172 lines)
└── README.md                    # Detailed documentation (349 lines)

scripts/
└── sign_policy_grant.py         # Client signing example (195 lines)

tests/
└── test_policy_grant.py         # Comprehensive tests (268 lines)

docs/
└── EIP712_POLICY_GRANT.md       # This file
```

## Next Steps

To integrate with your existing chain client:

1. **Provide your `chain_client.py`** with `is_revoked()` implementation
2. **Configure contract addresses** for Base L2
3. **Test against Base testnet** first
4. **Deploy to Base mainnet** with bytecode verification
5. **Update example_api.py** with production config

## References

- [EIP-712: Typed structured data hashing and signing](https://eips.ethereum.org/EIPS/eip-712)
- [Base L2 Documentation](https://docs.base.org/)
- [ANANKE Ethics Policy](./SECURITY.md)
- [GeoPhase Dual-Phase Computation](./DUAL_GEO_PHASE.md)

## Ethics Anchor

Hash: `65b14d584f5a5fd070fe985eeb86e14cb3ce56a4fc41fd9e987f2259fe1f15c1`

This implementation upholds the ANANKE covenant:
- No likeness capture
- No user tracking
- Fail-closed security
- Revocable grants
- Transparent verification
