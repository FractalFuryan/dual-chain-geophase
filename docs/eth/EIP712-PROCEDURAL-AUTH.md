# EIP-712 Procedural Authorization

**Protocol:** GeoPhase Procedural Auth v1  
**Chain:** Base (8453)  
**Purpose:** User authorization for procedural preset selection (non-likeness)

---

## 1. Overview

This spec defines an **EIP-712 typed signature** for authorizing procedural generation parameters. It is **NOT** for likeness consent—only for preset/mode selection in a privacy-safe manner.

### What This Authorizes:
- ✅ Procedural preset selection ("vibe selector")
- ✅ Mode selection (standard/clinical/research)
- ✅ Seed commitment usage

### What This Does NOT Authorize:
- ❌ Likeness capture or storage
- ❌ User data collection
- ❌ Media distribution rights
- ❌ Biometric processing

---

## 2. EIP-712 Domain

```json
{
  "name": "AnankeGeoPhase",
  "version": "1",
  "chainId": 8453,
  "verifyingContract": "0x<AttestationRegistryAddress>"
}
```

**Notes:**
- `chainId`: 8453 (Base mainnet)
- `verifyingContract`: Address of attestation registry or service contract

---

## 3. Message Structure

### TypedData Definition

```json
{
  "types": {
    "EIP712Domain": [
      {"name": "name", "type": "string"},
      {"name": "version", "type": "string"},
      {"name": "chainId", "type": "uint256"},
      {"name": "verifyingContract", "type": "address"}
    ],
    "ProceduralAuth": [
      {"name": "seedCommit", "type": "bytes32"},
      {"name": "mode", "type": "uint8"},
      {"name": "preset", "type": "uint16"},
      {"name": "expires", "type": "uint64"},
      {"name": "nonce", "type": "bytes32"}
    ]
  },
  "primaryType": "ProceduralAuth",
  "domain": { ... },
  "message": {
    "seedCommit": "0x1234...",
    "mode": 0,
    "preset": 42,
    "expires": 1704153600,
    "nonce": "0xabcd..."
  }
}
```

### Message Fields

| Field | Type | Description |
|-------|------|-------------|
| `seedCommit` | bytes32 | Seed commitment (sha256) |
| `mode` | uint8 | Generation mode (0=standard, 1=clinical, 2=research) |
| `preset` | uint16 | Procedural preset selector (0-65535) |
| `expires` | uint64 | Unix timestamp (signature expiration) |
| `nonce` | bytes32 | Anti-replay nonce (random) |

---

## 4. Signing (Client-Side)

### Example: MetaMask / ethers.js

```javascript
const domain = {
  name: "AnankeGeoPhase",
  version: "1",
  chainId: 8453,
  verifyingContract: "0xYourAttestationRegistry"
};

const types = {
  ProceduralAuth: [
    { name: "seedCommit", type: "bytes32" },
    { name: "mode", type: "uint8" },
    { name: "preset", type: "uint16" },
    { name: "expires", type: "uint64" },
    { name: "nonce", type: "bytes32" }
  ]
};

const message = {
  seedCommit: "0x1234567890abcdef...",
  mode: 0,
  preset: 42,
  expires: Math.floor(Date.now() / 1000) + 3600, // 1 hour
  nonce: "0xrandomNonce..."
};

const signature = await signer._signTypedData(domain, types, message);
```

### Example: Python (off-chain signing)

```python
from eth_account import Account
from eth_account.messages import encode_typed_data

domain = {
    "name": "AnankeGeoPhase",
    "version": "1",
    "chainId": 8453,
    "verifyingContract": "0xYourAddress"
}

types = {
    "EIP712Domain": [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
        {"name": "chainId", "type": "uint256"},
        {"name": "verifyingContract", "type": "address"}
    ],
    "ProceduralAuth": [
        {"name": "seedCommit", "type": "bytes32"},
        {"name": "mode", "type": "uint8"},
        {"name": "preset", "type": "uint16"},
        {"name": "expires", "type": "uint64"},
        {"name": "nonce", "type": "bytes32"}
    ]
}

message = {
    "seedCommit": "0x1234...",
    "mode": 0,
    "preset": 42,
    "expires": 1704153600,
    "nonce": "0xabcd..."
}

typed_data = {
    "domain": domain,
    "types": types,
    "primaryType": "ProceduralAuth",
    "message": message
}

signable = encode_typed_data(full_message=typed_data)
signed = Account.sign_message(signable, private_key="0x...")
signature = signed.signature.hex()
```

---

## 5. Verification (Server-Side)

### Python Implementation

```python
from geophase.eth import verify_procedural_auth

# Request body
message = {
    "seedCommit": "0x1234...",
    "mode": 0,
    "preset": 42,
    "expires": 1704153600,
    "nonce": "0xabcd..."
}
signature = "0x<65-byte-signature>"
expected_addr = "0x<user-wallet-address>"

# Verify
if verify_procedural_auth(message, signature, expected_addr):
    # Authorized: proceed with generation
    pass
else:
    # Reject: invalid signature or expired
    raise Exception("Invalid procedural authorization")
```

### FastAPI Middleware

```python
from fastapi import Request, HTTPException
from geophase.eth import verify_procedural_auth

async def require_procedural_auth(request: Request):
    body = await request.json()
    
    if not verify_procedural_auth(
        message=body["message"],
        signature=body["signature"],
        expected_addr=body["address"]
    ):
        raise HTTPException(403, "Invalid procedural authorization")
```

---

## 6. Security Considerations

### 6.1 Expiration
- **Always** include `expires` field
- Server **must** reject expired signatures
- Recommended TTL: 1 hour for interactive, 5 minutes for API

### 6.2 Nonce
- **Must** be random (32 bytes)
- Server **should** track used nonces (optional anti-replay)
- Use `secrets.token_bytes(32)` in Python

### 6.3 Scope Limitation
- Signature authorizes **only** procedural parameters
- Does **not** grant:
  - Data access rights
  - Likeness usage rights
  - Media distribution rights
  - Wallet fund access

### 6.4 Key Management
- User signs with **wallet private key** (MetaMask, etc.)
- Server **never** has access to user private keys
- Server **only** verifies signatures (public key recovery)

---

## 7. Mode and Preset Semantics

### Mode Values

| Value | Name | Description |
|-------|------|-------------|
| 0 | Standard | General-purpose procedural generation |
| 1 | Clinical | Medical/research-grade (strict ethics) |
| 2 | Research | Academic reproducibility mode |
| 3-255 | Reserved | Future use |

### Preset Values

Presets are **non-sensitive procedural selectors**:
- 0-999: Standard presets (e.g., "cyberpunk", "minimalist")
- 1000-1999: Clinical presets (e.g., "CT-scan-like")
- 2000-65535: Reserved/custom

**No user data is encoded in presets.**

---

## 8. Example Flow

### Client → Server Request

```json
POST /generate HTTP/1.1
Content-Type: application/json

{
  "message": {
    "seedCommit": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    "mode": 0,
    "preset": 42,
    "expires": 1704153600,
    "nonce": "0xabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcdabcd"
  },
  "signature": "0x<130-char-hex-signature>",
  "address": "0x<user-wallet-address>"
}
```

### Server Processing

1. **Verify signature** (EIP-712 recovery)
2. **Check expiration** (message.expires > now)
3. **Compute geoCommit** (from seedCommit + phaseHashes)
4. **Check revocation** (on-chain call)
5. **Generate** (procedural generation)
6. **Optional: Attest** (on-chain write)

---

## 9. Testing

### Test Vectors

```python
# Known test case
message = {
    "seedCommit": "0x" + "00" * 32,
    "mode": 0,
    "preset": 1,
    "expires": 2000000000,
    "nonce": "0x" + "ff" * 32
}

# Sign with test key: 0x1234... (DO NOT USE IN PRODUCTION)
# Expected signature: 0x...
```

### Fuzzing
- Test expired signatures (rejected)
- Test wrong signer (rejected)
- Test modified message (rejected)
- Test replay (optional: check nonce tracking)

---

## 10. References

- [EIP-712 Specification](https://eips.ethereum.org/EIPS/eip-712)
- [eth-account Documentation](https://eth-account.readthedocs.io/)
- [MetaMask Signing Guide](https://docs.metamask.io/guide/signing-data.html)

---

**Maintainer:** FractalFuryan  
**License:** MIT
