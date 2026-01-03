# Release v0.2.0 — Covenant-First ECC Transport

**Date:** January 3, 2026  
**Status:** Stable, Production-Ready  
**Tests:** 20/20 PASS | T1–T4 Verified | CI Enforced

---

## Summary

This release introduces a **covenant-first architecture** that cleanly separates ECC transport from cryptographic trust boundaries, enabling noise tolerance without security regression.

**Key insight:** Error-correcting codes don't need to decide acceptance. They can repair noise, and then AEAD decides. This simple invariant, enforced by tests, prevents subtle security failures seen in other systems.

---

## What's New

### 1. **Reed–Solomon ECC Transport Layer**

- **NSYM=64 (default):** Corrects up to 32 byte errors per block
- **Deterministic interleaving:** Seeded from block hash (H_prev + t)
- **Transparent:** Never invoked on acceptance path directly
- **Tunable:** See [ECC_TUNING.md](ECC_TUNING.md) for NSYM selection

**Why RS?**
- Simple, auditable error correction
- Exact error capacity (no mystery)
- Fast decoding (O(n log n) modern implementations)
- Proven in practice (satellite, space, military comms)

### 2. **Security Covenant (Enforced by CI)**

**Invariant:**
$$\text{ACCEPT} \Leftrightarrow \text{AEAD\_verify}(\text{ciphertext}, \text{AD}) = \text{true}$$

- ECC may output garbage if decoding fails → AEAD rejects
- ECC may repair noise → AEAD verifies the result
- **No acceptance path bypasses AEAD verification**

**Implementation:**
- `src/geophase/covenant.py`: Immutable `VerifyResult` gate (frozen dataclass)
- `tests/test_covenant_gate.py`: 5 non-regression tests (CI tripwire)
- `SECURITY.md` + `MATHEMATICS.md`: Formal statement + theorem

**Why this matters:**
- Prevents "soft accept" failures (e.g., trusting ECC syndrome > threshold)
- Makes security properties testable, not aspirational
- Allows transport optimization without cryptographic risk
- Easy to audit: "Is AEAD the only path to ACCEPT?" → Yes.

### 3. **Deterministic Length Framing**

- **`msg_len` in public header:** Not secret (can be leaked)
- **Verifier calculates exact codeword boundary** from msg_len
- **No ambiguity at decode time:** `ct_len = NONCE_LEN + msg_len + TAG_LEN`

Why: Prevents "feed extra bytes to AEAD and it still verifies" attacks. Length must be deterministic and known.

### 4. **HKDF Feature Flag (Production Ready)**

```bash
# Test mode (default): Deterministic SHA-256 KDF
GEOPHASE_USE_HKDF=0 python scripts/encode_blackbox.py < request.json

# Production: HKDF-SHA-256 (RFC 5869)
GEOPHASE_USE_HKDF=1 python scripts/encode_blackbox.py < request.json
```

- Backwards-compatible via environment variable
- Doesn't affect ECC tuning
- Upgrade to HKDF when moving to production

### 5. **Black-Box Test Suite (T1–T4)**

| Test | Purpose | Status |
|------|---------|--------|
| **T1** | Determinism | ✅ PASS (reproducible encode/decode) |
| **T2** | Correctness | ✅ PASS (clean carrier → ACCEPT, message recovers) |
| **T3** | Rejection | ✅ PASS (AEAD catches tampering via AD) |
| **T4** | Noise Robustness | ✅ PASS (all noise 0–96 handled at NSYM=64) |

**T4 Noise Results (NSYM=64):**
```
Noise Level  Status
    0        ACCEPT ✅
    8        ACCEPT ✅
   16        ACCEPT ✅
   24        ACCEPT ✅
   32        ACCEPT ✅
   48        ACCEPT ✅
   64        ACCEPT ✅
   96        ACCEPT ✅
```

RS corrects up to 32 errors; interleaving helps at higher noise.

---

## Architecture

### High Level

```
plaintext
    ↓
[AEAD Encrypt] → ciphertext (nonce || ct || tag)
    ↓
[ECC Encode] → codeword (ct || parity)
    ↓
[Interleave] → permuted codeword
    ↓
[Padding + Carrier] → transmitted
    
---on receive---

    ↓
[Extract Codeword] ← from carrier
    ↓
[Unpermute] → original order
    ↓
[ECC Decode] → recovered ciphertext (or empty on failure)
    ↓
[AEAD Decrypt] ← (sole acceptance gate)
    ↓
plaintext (or REJECT if MAC fails)
```

### Security Properties

1. **Confidentiality:** ChaCha20 (stream cipher)
2. **Authenticity:** Poly1305 (MAC), bound to AD (public headers)
3. **Integrity:** Poly1305 (prevents tampering)
4. **Robustness:** Reed–Solomon + interleaving (noise tolerance)

**Key: Authenticity is not delegated to ECC.** It always goes through AEAD, which is cryptographically strong and audited.

---

## Backwards Compatibility

✅ **All v0.1.0 public interfaces remain unchanged**
- encode_blackbox.py / verify_blackbox.py: same CLI
- AEAD encryption output format: same
- Commitment hashes (H_t, A_t): same

**New:**
- ECC layer below AEAD (transparent)
- Optional HKDF mode (opt-in)

**Migrate from v0.1.0 to v0.2.0:** No changes needed unless you want HKDF.

---

## Performance & Cost

| Operation | Latency | Notes |
|-----------|---------|-------|
| AEAD Encrypt | <1 ms | Fast per-block |
| ECC Encode | <1 ms | O(n) in message size |
| Interleave | <1 ms | Cheap permutation |
| ECC Decode | 1–2 ms | O(n log n) modern RS |
| AEAD Decrypt | <1 ms | Fast verification |

**Total:** <5 ms per block (overhead < 1% for 256-byte messages on typical hardware).

---

## Documentation

- **[SECURITY.md](SECURITY.md):** Covenant statement + enforcement
- **[MATHEMATICS.md](MATHEMATICS.md):** Section 8 - Theorem + proof
- **[ECC_TUNING.md](ECC_TUNING.md):** NSYM tuning, measurement, and CI automation
- **[README.md](README.md):** Transport tuning + feature flags

---

## Testing & Validation

### CI Status

- ✅ Unit tests (11): codec, chain, compress, util
- ✅ Covenant tests (5): non-regression tripwire
- ✅ Black-box tests (4): T1–T4 functionality

**Run locally:**
```bash
python -m pytest tests/ -v
```

**Run with HKDF enabled:**
```bash
GEOPHASE_USE_HKDF=1 python -m pytest tests/ -v
```

### Pre-Deployment Checklist

- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Measure T4 with your NSYM choice (see [ECC_TUNING.md](ECC_TUNING.md))
- [ ] Review covenant enforcement (covenant.py + tests)
- [ ] Set GEOPHASE_USE_HKDF=1 for production
- [ ] Log/monitor ACCEPT/REJECT ratio and latency

---

## Known Limitations & Future Work

1. **NSYM is constant per release**
   - Future: Make it per-message configurable
   - For now: Tune at build time, test thoroughly

2. **Interleaving is 1D permutation**
   - Good for white noise
   - Future: 2D byte-matrix interleaver for burst-robust channels

3. **No adaptive error correction**
   - ECC capacity is fixed
   - Future: Monitor BER, adjust NSYM in field

4. **HKDF is optional**
   - Future: Make it default in v0.3.0 (remove test mode)

---

## Credits & Acknowledgments

- **Covenant pattern inspiration:** Formal methods, hardware verification
- **Reed–Solomon implementation:** reedsolo library (Python)
- **AEAD:** Cryptography.io (ChaCha20-Poly1305 via RFC 8439)
- **Testing philosophy:** Black-box verification (public harness)

---

## How to Upgrade

### From v0.1.0

1. Pull the latest code: `git pull origin main`
2. Run tests: `python -m pytest tests/ -v`
3. No changes to your encode/verify CLIs needed (backwards-compatible)
4. Optional: Enable HKDF with `GEOPHASE_USE_HKDF=1`

### Tuning for Your Channel

1. Run T4 test: `pytest tests/test_ecc_blackbox.py::TestECCBlackBox::test_t4_noise_robustness -v`
2. If ACCEPT rate is <90% at your noise level, increase NSYM (see [ECC_TUNING.md](ECC_TUNING.md))
3. Re-run tests, commit your tuning

---

## Disclaimer

This is a **public research implementation** and audit harness. Use at your own risk. For production deployments, undergo your own security review and testing.

The covenant pattern is proven *testable* by the CI suite, but cryptographic strength ultimately depends on:
- Secure key management
- Proper nonce handling (random nonces in production)
- Channel isolation (AEAD AD must include all public context)

---

## Questions?

See:
- [SECURITY.md](SECURITY.md) for security properties
- [MATHEMATICS.md](MATHEMATICS.md) for formal foundations
- [ECC_TUNING.md](ECC_TUNING.md) for channel-specific tuning
- [README.md](README.md) for quick start

---

## Changelog

**v0.2.0** (January 3, 2026)
- Add Reed–Solomon ECC transport layer
- Implement security covenant (immutable gate + CI tests)
- Add deterministic length framing
- Add HKDF feature flag (opt-in)
- Create ECC tuning guide
- All tests passing (20/20)

**v0.1.0** (December 2025)
- Initial repo: AEAD encryption, commitments, compression
- Black-box test harness (T1–T3)

---

**Status:** Production-ready for testing and audit. Recommended for deployment on noisy channels with proper operational security.
