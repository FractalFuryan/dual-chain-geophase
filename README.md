# Dual-Chain GeoPhase (Public Test Repo)

**Security Covenant:** ✅ AEAD-Gated Acceptance (ECC never authorizes)

This repository provides a **public, black-box verification harness** for a dual-chain authenticated design:
- **Above chain:** commitments (H_t, A_t) + structured-state digesting
- **Below chain:** noise-tolerant carrier transport of AEAD ciphertext (via ECC)
- **Compression:** applied only to structured deltas (never ciphertext)

## What this repo is
- A **testable** public audit harness
- A reference CLI interface for ENCODE / VERIFY
- A reference implementation of compression and commitment logic

## What this repo is not
- A disclosure of private schedules/keys
- A claim of a new cryptographic primitive
- A claim of "post-quantum" unless backed by chosen primitives

## Quickstart

```bash
# Set up environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run black-box test harness
python scripts/public_test.py \
  --encode scripts/encode_blackbox.py \
  --verify scripts/verify_blackbox.py \
  --verify-wrong scripts/verify_blackbox_wrongkey.py \
  --blocks 50 --msg-bytes 256 --noise-levels 0,1,2,4,8,16,32
```

## Self-Check (Automated Verification)

To verify the repo is in good shape, run:

```bash
./self_check.sh
```

This checks:
- Python environment
- Package imports
- Mathematical documentation
- Unit tests (11 tests)
- Black-box test harness (T1–T3)
- Known limitations (T4 requires real ECC)

**Perfect for GitHub Codespaces:**
```bash
# In Codespaces terminal:
./self_check.sh
```

## Security Model

**Confidentiality and integrity** reduce to **standard AEAD** (placeholder: plaintext transport in harness; real build uses authenticated encryption).

**Robustness** is achieved via **error-correcting codes** and black-box verified under noise.

## Structure

```
dual-chain-geophase/
├─ README.md                           # This file
├─ LICENSE                             # MIT License
├─ SECURITY.md                         # Security policy & reporting
├─ .gitignore                          # Git exclusions
├─ pyproject.toml                      # Python project config
├─ requirements.txt                    # Dependencies
├─ scripts/
│  ├─ public_test.py                   # Black-box test harness
│  ├─ encode_blackbox.py               # Encode CLI (structured state → carrier)
│  ├─ verify_blackbox.py               # Verify CLI (correct key)
│  └─ verify_blackbox_wrongkey.py      # Verify CLI (wrong key, always rejects)
├─ src/geophase/
│  ├─ __init__.py                      # Package init
│  ├─ codec.py                         # ECC + carrier (placeholder)
│  ├─ chain.py                         # H_t, A_t, commitment logic
│  ├─ compress.py                      # 3–6–9 structured compression
│  └─ util.py                          # Canonical JSON, b64 helpers
└─ tests/
   └─ test_smoke.py                    # Smoke tests
```

## Test Harness (T1–T4)

The `public_test.py` harness runs:

1. **T1 (Determinism):** Encode same input twice → identical output
2. **T2 (Correctness):** Verify with correct key → ACCEPT + message recovery
3. **T3 (Rejection):** Verify with wrong key → REJECT
4. **T4 (Noise Robustness):** Carrier with noise → still verifies (ECC-dependent)

Run with:
```bash
python scripts/public_test.py --blocks 10 --msg-bytes 32 --noise-levels 0,1,2
```

## Architecture

### Above Chain (Commitments)
- **D** = canonical JSON of structured state
- **g_t** = H(D) — digest of current state
- **H_prev** — hash of previous commitment (chained)
- **A_t** = H(H_prev ∥ g_t ∥ public_header) — availability witness
- **H_t** = H(H_prev ∥ H(ct) ∥ g_t) — binding hash

### Below Chain (Carrier)
- **ct** = AEAD(key, nonce, msg) — authenticated encryption (placeholder: msg)
- **carrier** = ECC_encode(ct) ∥ padding — error-correcting code transport

### Compression
- Applied **only** to structured state (D), never to ciphertext
- Uses zlib-9 (placeholder; swap for custom 3–6–9 codec)

## Mathematical Foundations

For detailed mathematical treatment, see [MATHEMATICS.md](MATHEMATICS.md).

**Key invariant:** Secrecy ⊥ Structure

All components use standard, conservative cryptographic primitives:
- Hash chains (SHA-256, BLAKE2)
- Authenticated encryption (AES-GCM, ChaCha20-Poly1305)
- Error-correcting codes (Reed-Solomon, LDPC)
- Channel interleaving (standard information theory)

## Next Steps: Real Implementation

To pass T4 (noise robustness) and production-readiness:

1. **Implement real AEAD** (AES-GCM, ChaCha20-Poly1305)
2. **Add Reed-Solomon or similar ECC** in `src/geophase/codec.py`
3. **Interleave carrier** for burst-noise robustness
4. **Remove plaintext ciphertext from meta** (toy mode only)
5. **Formal security review** of commitment chain

## Testing

Run smoke tests:
```bash
python -m pytest tests/ -v
```

## License

MIT. See [LICENSE](LICENSE).

## Security & Disclosure

See [SECURITY.md](SECURITY.md).
