"""
Nonce Policy for GeoPhase RFC6979 Signing

This document specifies how RFC6979 deterministic nonce generation integrates
with the GeoPhase covenant architecture.
"""

# RFC6979 Nonce Policy

## Executive Summary

RFC6979 provides **deterministic ECDSA nonce generation** without introducing
randomness vulnerabilities or weak signatures. In GeoPhase:

- **Nonce source**: RFC6979 (HMAC-SHA256 based, deterministic)
- **Domain separation**: Optional `extra` parameter (e.g., Snake/Tetris/Zeta commitment)
- **Signature form**: Low-S normalization (canonical, Bitcoin/Ethereum compatible)
- **Determinism guarantee**: same (privkey, message, extra) → same signature

**Key invariant**: The nonce is **never entropy**; it is deterministic.  
Per-event uniqueness requires nonce *in the message* (or associated data), not in RNG.

---

## 1. Why RFC6979?

### The Problem
Traditional ECDSA requires a random nonce $k$ for each signature. If the RNG fails
(or if $k$ is reused), the private key is trivially leaked.

### RFC6979 Solution
Generate $k$ deterministically from:
- Private key $d$
- Message hash $H(m)$  
- Optional domain bytes (for separation)

**Result**: Same message and key always produce the same signature (deterministic),
yet nonce reuse cannot happen across *different messages*.

### GeoPhase Use Case
This fits perfectly with the covenant architecture:
- Determinism enables reproducible, auditable signing
- No "entropy failures" to worry about
- Signatures are canonical (low-S normalized)
- Domain separation via `extra` binds commitment metadata without changing k generation

---

## 2. Implementation: rfc6979.py

### Core Function

```python
def rfc6979_generate_k_secp256k1(
    priv_int: int, 
    hash_bytes: bytes, 
    extra: bytes = b""
) -> int:
    """Generate RFC6979 deterministic nonce k for secp256k1."""
```

**Inputs:**
- `priv_int`: Private key in [1, q-1]
- `hash_bytes`: Message hash (e.g., SHA256(msg)), raw bytes
- `extra`: Domain separation bytes (optional, hashed internally)

**Output:**
- `k`: Nonce in [1, q-1], deterministic and rejection-free

**Algorithm** (RFC 6979 section 3.2):
1. Set `V := 0x01...01` (32 bytes for SHA256)
2. Set `K := 0x00...00` (32 bytes)
3. Update K, V using HMAC-SHA256 with privkey + message hash + extra
4. Generate candidate k from HMAC stream
5. If k not in [1, q-1], regenerate (reject, don't reduce modulo)

### Signing

```python
def sign_with_rfc6979(
    priv_int: int, 
    msg: bytes, 
    extra: bytes = b""
) -> bytes:
    """DER-encoded ECDSA signature with RFC6979 + low-S normalization."""
```

**Steps:**
1. Hash message: `z := SHA256(msg)`
2. Generate k: `k := rfc6979_generate_k_secp256k1(priv_int, z, extra)`
3. Compute (r, s) using ECDSA with k
4. Normalize s to low-S form (s ≤ n/2)
5. Encode as DER SEQUENCE

**Determinism guarantee**: same (priv_int, msg, extra) → same (r, s) → same DER signature

### Verification

```python
def verify_signature(pub_bytes: bytes, msg: bytes, sig_der: bytes) -> bool:
    """Verify DER ECDSA signature over secp256k1."""
```

**Notes:**
- Works with any valid signature (accepts both low-S and high-S forms)
- Safe on untrusted input
- Returns False on any verification failure

---

## 3. Domain Separation via `extra`

The `extra` parameter enables **commitment binding** without adding entropy.

### Use Case: Snake/Tetris/Zeta Commitment

```python
from geophase.crypto.rfc6979 import sign_with_rfc6979

# Build commitment from game state
commitment_hash = sha256(b"SNAKE|1.0|state_blob").digest()

# Sign message with commitment metadata as domain separation
extra = b"ZETA_COMMITMENT_V1|" + commitment_hash
signature = sign_with_rfc6979(priv_int, msg, extra=extra)
```

**Effect:**
- Same message + privkey + *different extra* → different signature
- Different message + privkey + same extra → different signature
- Same message + privkey + same extra → **identical** signature (deterministic)

**Security model:**
- `extra` is **not entropy**; it is commitment metadata
- It prevents signature reuse across protocol versions or domains
- Externally auditable: commit `extra` publicly before signing

### Example: Versioned Commitments

```python
# Version 1
extra_v1 = b"GRAIL_PROTOCOL_V1"
sig_v1 = sign_with_rfc6979(priv_int, msg, extra=extra_v1)

# Version 2 (different signing domain)
extra_v2 = b"GRAIL_PROTOCOL_V2"
sig_v2 = sign_with_rfc6979(priv_int, msg, extra=extra_v2)

# sig_v1 != sig_v2 (even for identical msg + priv_int)
```

---

## 4. Low-S Normalization

ECDSA signatures (r, s) have a valid "mirror" form (r, n-s). To prevent 
signature malleability and ensure compatibility:

```python
def _low_s(r: int, s: int, n: int) -> Tuple[int, int]:
    """Normalize s to low form (s ≤ n/2)."""
    if s > n // 2:
        s = n - s
    return r, s
```

**Effect:**
- Canonical form (s ≤ n/2)
- Compatible with Bitcoin, Ethereum, and standards-compliant verifiers
- Prevents "signature malleability" attacks

**Status in `sign_with_rfc6979`**: Applied automatically after signing

---

## 5. Determinism and Reproducibility

### Guarantee 1: Same Inputs → Same Signature

```python
sig1 = sign_with_rfc6979(priv_int, msg, extra)
sig2 = sign_with_rfc6979(priv_int, msg, extra)
assert sig1 == sig2  # Always true
```

### Guarantee 2: No RNG Involved

RFC6979 uses HMAC, not random sources. HMAC is deterministic.

### Guarantee 3: Different Messages → Different Signatures (Probabilistic)

```python
sig_m1 = sign_with_rfc6979(priv_int, b"message 1", extra)
sig_m2 = sign_with_rfc6979(priv_int, b"message 2", extra)
# sig_m1 != sig_m2 (with overwhelming probability)
```

### Guarantee 4: Same Message, Different Extra → Different Signatures

```python
sig_a = sign_with_rfc6979(priv_int, msg, extra=b"A")
sig_b = sign_with_rfc6979(priv_int, msg, extra=b"B")
assert sig_a != sig_b
```

---

## 6. Usage Patterns

### Pattern 1: Deterministic Attestation

```python
from geophase.crypto.rfc6979 import sign_with_rfc6979, verify_signature

# Signer
priv_int = 12345  # From key management
msg = b"Grail commitment: state_blob_v1"
attestation = sign_with_rfc6979(priv_int, msg)

# Verifier (given pubkey from signer)
pub_bytes = pubkey_from_privkey(priv_int)
is_valid = verify_signature(pub_bytes, msg, attestation)
assert is_valid
```

### Pattern 2: Domain-Separated Signing

```python
# Scenario: Multiple protocol versions must have different signatures
commitment = sha256(b"game_state_v2").digest()
extra = b"PROTOCOL_V2|" + commitment

sig_v2 = sign_with_rfc6979(priv_int, msg, extra=extra)
# Signature v2 is distinct from signatures under other extra values
```

### Pattern 3: Reproducible Test Signing

```python
# Test: verify determinism
msg = b"test_message"
sig1 = sign_with_rfc6979(test_priv_int, msg)
sig2 = sign_with_rfc6979(test_priv_int, msg)
assert sig1 == sig2, "RFC6979 failed: nondeterministic signature"
```

---

## 7. What RFC6979 Does NOT Provide

### ❌ Per-Event Uniqueness

If you sign the same message twice with RFC6979, you get the same signature.  
**Solution**: Include a nonce or timestamp *in the message* (not in RNG).

```python
# Wrong: still gets same signature
sig1 = sign_with_rfc6979(priv_int, b"buy 100 shares")
sig2 = sign_with_rfc6979(priv_int, b"buy 100 shares")
# sig1 == sig2

# Right: include nonce in message
import time
sig1 = sign_with_rfc6979(priv_int, b"buy 100 shares|nonce_A")
sig2 = sign_with_rfc6979(priv_int, b"buy 100 shares|nonce_B")
# sig1 != sig2
```

### ❌ Cryptographic Randomness

RFC6979 is deterministic. If you need randomness (e.g., for sampling or commitment
schemes), use `os.urandom()` or a proper CSPRNG.

```python
import os
# RFC6979 for signing
sig = sign_with_rfc6979(priv_int, msg)

# os.urandom for independent randomness
random_nonce = os.urandom(32)
```

### ❌ Zero-Knowledge

Signatures are public and verifiable. If you need privacy, use ZK proofs.

---

## 8. Security Considerations

### Threat Model

**Assumption**: Private key is kept secret.

**Nonce reuse scenarios**:
- ✅ Safe: same message + privkey signed twice → same k (deterministic, secure)
- ❌ Unsafe (prevented by RFC6979): RNG failure → nonce reuse across messages
- ❌ Unsafe (prevent in application): sign same message with different keys without isolation

### Audit Checklist

- [ ] Private keys are never logged or transmitted
- [ ] Message hashes (or messages) are recorded for reproducibility
- [ ] Extra values are committed before signing
- [ ] Signatures are verified immediately after generation (sanity check)
- [ ] Low-S normalization is enforced (already done in `sign_with_rfc6979`)

### Known Limitations

1. **Hash algorithm**: Currently uses SHA256 (standard). Changing requires RFC6979 reparameterization.
2. **Curve**: Limited to secp256k1. Adding other curves requires separate implementations.
3. **Key generation**: RFC6979 is for nonce generation only. Use a proper KDF (e.g., BIP32) for key derivation.

---

## 9. Testing

### Unit Tests

See `tests/test_rfc6979_vectors.py`:

- **Determinism**: Same inputs → same signature
- **Domain separation**: Different `extra` → different signature
- **Verification**: Valid signatures verify, invalid ones reject
- **Low-S**: All signatures have s ≤ n/2
- **Test vectors**: Known RFC6979 test cases from reference implementations

### Integration Tests

- [ ] Sign a commitment with extra parameter
- [ ] Verify signature correctness
- [ ] Confirm reproducibility across sessions
- [ ] Cross-validate with external ecdsa library

---

## 10. References

- **RFC 6979**: https://tools.ietf.org/html/rfc6979
- **secp256k1**: https://en.wikipedia.org/wiki/Secp256k1
- **ecdsa library**: https://github.com/tlsfuzzer/python-ecdsa
- **Bitcoin low-S**: https://github.com/bitcoin/bips/blob/master/bip-0062.md
- **Ethereum signature**: https://eips.ethereum.org/EIPS/eip-2

---

**Version**: 1.0  
**Date**: 2026-01-17  
**Maintainer**: GeoPhase Contributors
