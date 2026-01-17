# Security Anchors (Immutable Policies)

**Version**: v0.2.0  
**Date**: 2024  
**Status**: 🔐 LOCKED (Non-Negotiable)

---

## RFC6979 Nonce Policy (Immutable)

This policy is **version-locked** and forms a security anchor for all future development. Deviations require security review and RFC amendment.

### Core Properties (MUST NOT CHANGE)

#### ✅ Deterministic ECDSA

```
Property: Same (priv_int, msg, extra) → identical signature always
Method: RFC 6979 deterministic nonce generation via HMAC-SHA256
Enforced: Function sign_with_rfc6979(priv_int, msg, extra=b"")
Rationale: Reproducible attestation, audit trails, deterministic state binding
```

**Non-Negotiable**: Cannot add entropy injection or randomization to nonce generation. If randomness needed, use separate random k function.

#### ✅ Rejection Sampling (No Modulo Bias)

```
Property: Nonce k always in valid range [1, q-1] (secp256k1 order)
Method: Rejection sampling per RFC 6979 section 3.2 (reject k outside range)
NOT Method: Modulo reduction (k % q) which introduces subtle bias
Enforced: Function rfc6979_generate_k_secp256k1() loops until valid k
Rationale: Prevents nonce distribution bias exploitable by sophisticated attacks
```

**Non-Negotiable**: Cannot use modulo reduction or shortcut rejection loop. RFC 6979 section 3.2 algorithm must be followed exactly.

#### ✅ Low-S Normalization Enforced

```
Property: All signatures have canonical form where s ≤ n/2
Method: _low_s(r, s, n) normalizes: if s > n//2: s = n - s
Applied: Automatically in sign_with_rfc6979() before DER encoding
Standard: BIP 62 (Bitcoin), EIP 2 (Ethereum)
Rationale: Prevents signature malleability (two valid sigs for same input)
```

**Non-Negotiable**: Cannot skip low-S normalization or make it optional. Must apply before returning signature.

#### ✅ No External Entropy Sources

```
Property: No CSPRNG, random.SystemRandom, os.urandom, or hardware RNG
In nonce generation: Deterministic HMAC chain only
In domain separation: Extra bytes hashed but NOT used as entropy
Enforced: HAS_ECDSA guards verify ecdsa lib (not ecdsa randomness)
Rationale: Enables reproducible signing for deterministic protocols
```

**Non-Negotiable**: Cannot add any randomness to nonce path. If per-event uniqueness needed, include nonce in message or use different signing function.

#### ✅ Domain Separation via Extra Parameter

```
Property: Optional `extra` parameter influences nonce but adds no entropy
Method: Hashed internally as part of HMAC stream (RFC 6979 step 3.2a)
Example: extra=b"SNAKE_V1" → different nonce than extra=b"TETRIS_V1"
Format: User provides bytes; hashed, not interpreted as entropy
Rationale: Protocol versioning, commitment binding, state root binding
```

**Non-Negotiable**: Extra is for domain separation ONLY. Cannot be used as entropy injection or bypassed for "simplified signing."

---

## DER Encoding (Immutable)

```
Standard: SEQUENCE { INTEGER r, INTEGER s }
Format: [0x30][length][r_encoding][s_encoding]
Integer encoding: [0x02][length][value] with leading 0x00 if high bit set
Rationale: Bitcoin/Ethereum standard format
```

**Non-Negotiable**: Cannot use raw (r, s) tuples or custom serialization. Must be valid DER.

---

## Public Key Derivation (Immutable)

```
Curve: secp256k1 (Bitcoin/Ethereum standard)
Format: Uncompressed 65-byte format (0x04 + x + y)
Range: Private key in [1, q-1] where q = 2^256 - 2^32 - 977
Derived: pubkey_from_privkey(priv_int) → bytes
```

**Non-Negotiable**: Cannot change curve, format, or range validation. Must reject priv = 0 or priv ≥ q.

---

## Import Safety (Immutable)

```
Requirement: ecdsa >= 0.18 (for secp256k1 support)
Handling: HAS_ECDSA flag gracefully handles missing library
Behavior: Module loads successfully; functions raise ImportError if called
Error message: Clear guidance to "pip install ecdsa>=0.18"
Rationale: Prevents silent failures; package ships with crypto module ready
```

**Non-Negotiable**: Cannot crash on import. Must degrade gracefully with helpful error at function call time.

---

## Type Hints (Immutable)

```
Requirement: 100% type coverage on all public functions
Functions: rfc6979_generate_k_secp256k1, sign_with_rfc6979, verify_signature, pubkey_from_privkey
Format: Function annotations (priv_int: int) -> bytes
Rationale: Type safety, IDE support, documentation
```

**Non-Negotiable**: Cannot remove type hints. Must add for any new public functions.

---

## Documentation (Immutable)

```
Requirement: Comprehensive docstrings on all functions
Content: Purpose, parameters, returns, raises, design notes, examples
Minimum: 500 chars per function docstring
Location: RFC6979-NONCE-POLICY.md documents design rationale
Rationale: Auditable, maintainable, understood by future developers
```

**Non-Negotiable**: Cannot remove docstrings or reduce documentation. Must expand when adding features.

---

## Test Coverage (Immutable)

```
Baseline: 28 tests minimum (current coverage)
Classes: 7 test classes (K generation, determinism, verification, domain sep, normalization, pubkey, integration)
Scope: All major functions, error paths, edge cases
Location: tests/test_rfc6979_vectors.py
Rationale: Catch regressions, verify correctness
```

**Non-Negotiable**: Cannot reduce test count. New changes must add tests, not remove them.

---

## Security Checklist (Immutable Reference)

This checklist applies to any changes to RFC6979 code:

- [ ] RFC 6979 section 3.2 algorithm unchanged
- [ ] Nonce rejection sampling loop intact (no shortcuts)
- [ ] Low-S normalization applied to all signatures
- [ ] Extra parameter affects nonce only (no entropy)
- [ ] All functions have HAS_ECDSA guard
- [ ] Type hints on all functions
- [ ] Docstrings present and up-to-date
- [ ] Tests pass (28+ tests minimum)
- [ ] No new entropy sources added
- [ ] DER encoding follows standard
- [ ] Error messages helpful
- [ ] Backward compatible (or documented breaking change)

---

## What Can Change (With Caution)

**Allowed**: Performance optimizations that don't change output
**Allowed**: Better error messages or documentation
**Allowed**: New helper functions (if properly guarded)
**Allowed**: Bug fixes (with test regression suite)
**Allowed**: Dependencies upgrades (if compatible)

**Requires RFC**: Adding new signing modes
**Requires RFC**: Changing domain separation mechanism
**Requires RFC**: Supporting new curves
**Requires RFC**: Removing low-S normalization
**Requires RFC**: Adding entropy to nonce generation

---

## What CANNOT Change (Locked)

❌ **Cannot** use modulo reduction for nonce (must reject)  
❌ **Cannot** skip low-S normalization (must enforce)  
❌ **Cannot** add entropy to deterministic nonce path  
❌ **Cannot** change curve from secp256k1  
❌ **Cannot** remove type hints  
❌ **Cannot** reduce test coverage  
❌ **Cannot** make import crash on missing ecdsa  
❌ **Cannot** use non-DER signature format  

---

## Amendment Process

To change this anchor:

1. **Create RFC** (Request for Comment) document
2. **Security Review** - Independent cryptography review
3. **Impact Analysis** - How does this affect existing deployments?
4. **Version Bump** - Major version increase (v1.0.0 → v2.0.0)
5. **Migration Path** - How do users migrate safely?
6. **Documentation** - Update SECURITY-ANCHORS.md with rationale for change

**Example**: If wanting to support BLS signatures, this requires a NEW function (not modification to sign_with_rfc6979).

---

## Verification

To verify this anchor is maintained:

```bash
# 1. Check module loads
python -c "from geophase.crypto import rfc6979; print('✅ Loads')"

# 2. Verify nonce rejection
python -c "from geophase.crypto.rfc6979 import rfc6979_generate_k_secp256k1; \
k = rfc6979_generate_k_secp256k1(123, b'\\x00'*32); \
assert 1 <= k < 2**256 - 2**32 - 977, 'Nonce out of range!'"

# 3. Check low-S in signatures
pip install ecdsa>=0.18 && python -c "from geophase import sign_with_rfc6979, pubkey_from_privkey, verify_signature; \
priv = 0x123...; pub = pubkey_from_privkey(priv); \
sig = sign_with_rfc6979(priv, b'test'); \
assert verify_signature(pub, b'test', sig), 'Sig verify failed!'"

# 4. Run test suite
pytest tests/test_rfc6979_vectors.py -v
# Expect: 28 passed
```

---

## Related Documents

- [RFC6979-NONCE-POLICY.md](docs/RFC6979-NONCE-POLICY.md) - Design rationale
- [RFC6979_README.md](RFC6979_README.md) - Usage guide
- [RFC6979_DELIVERY.md](RFC6979_DELIVERY.md) - Implementation summary

---

## Version History

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| v0.2.0 | 2024 | 🔐 LOCKED | Initial RFC6979 implementation, all anchors frozen |

---

**This document is a covenant with future maintainers. These properties must not be violated without explicit security review and RFC amendment.**

🔐 **Last Updated**: January 17, 2024  
🔐 **Locked By**: RFC6979 v0.2.0 implementation  
🔐 **Status**: Active & Enforced
