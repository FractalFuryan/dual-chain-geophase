# GeoPhase Chain

[![CI](https://github.com/FractalFuryan/dual-chain-geophase/actions/workflows/ci.yml/badge.svg)](https://github.com/FractalFuryan/dual-chain-geophase/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Security Covenant:** ✅ AEAD-Gated Acceptance  
*(ECC never authorizes — blockchain acceptance is cryptographic only)*

---

## Quick mental model

- **ECC + interleaving** → helps ciphertext survive noise *(transport only)*
- **AEAD** → decides authenticity *(sole acceptance gate)*
- **Chain index (t)** → binds blocks into an ordered, replay-safe sequence
- **Covenant** → prevents "transport success ⇒ trust" failures by construction

GeoPhase Chain is a **block-indexed transport + verification pattern** for authenticated ciphertext.

It answers one engineering question:

> **How do we move authenticated ciphertext through noisy/lossy channels
> across a block chain, without letting "transport success" be mistaken for "authenticity"?**

GeoPhase Chain solves this by **separating cryptographic trust (AEAD) from geometric robustness (ECC + interleaving)**.

📖 **Read [GEOPHASE.md](GEOPHASE.md) for the full conceptual model.**

### Documentation

- **Scalar Waze Appendix (optional):** Harmonic and discrete-symmetry interpretation  
  ([docs/APPENDIX_SCALAR_WAZE_UNIFIED.md](docs/APPENDIX_SCALAR_WAZE_UNIFIED.md))  
  *Exploratory, non-fundamental, not used in protocol logic*

---

## What This Is (And Isn't)

GeoPhase Chain is **not a blockchain protocol or consensus system**.

It is a **block-chain pattern**: messages are indexed, hash-linked, and cryptographically bound to their position (`t`) in a chain.

**Consensus, networking, and storage are intentionally out of scope.**

---

## The Covenant (One Rule That Matters)

> **ACCEPT(block t) ⇔ AEAD_verify(ciphertext, AD_t) = true**

Error correction is transport-only. It may repair bytes, but it never decides validity.

This rule is enforced by:
- A single acceptance gate (`verify_gate()`)
- Immutable `VerifyResult` type
- CI tripwire tests (5 non-regression checks)

---

## About This Repo

This repository provides a **public, black-box verification harness**:

- ✅ **Testable:** T1–T4 harness with deterministic + noise-robust modes
- ✅ **Auditable:** Covenant enforcement via code structure + CI
- ✅ **Reference implementation:** ENCODE/VERIFY CLI, codec, commitment logic
- ✅ **Conservative:** Composes standard AEAD (ChaCha20-Poly1305) + standard ECC (Reed–Solomon)

**What this is NOT:**
- ❌ A new cryptographic primitive
- ❌ "Post-quantum by magic"
- ❌ Security by obscurity

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

---

## Enhanced Hybrid Chaotic State Mixer (v2)

**New in v0.2.0:** A production-grade non-autonomous nonlinear state mixer with entropy-gated teleportation.

### What It Does

The mixer (`mixer.py`) implements a **structured unpredictable transition** for scalars in cryptographic protocols:

- **Deterministic ancilla chains** (seed + step index)
- **Dual-phase drift** (primary + secondary orthogonal mixers)
- **Stateless teleport probability** (entropy-aware, no memory)
- **Optional CSPRNG augmentation** (reproducible by default, irreversible on demand)

### Key Features

✅ **Bounded:** All operations mod $n$ (no divergence)  
✅ **Chaotic locally:** Nonlinear drift + XOR mixing  
✅ **Escape trap states:** Stochastic teleportation breaks resonance  
✅ **Auditable:** Fully deterministic when randomness is disabled  
✅ **No learning:** Pure function, no state, no adaptation  

### Quick Integration

```python
from geophase.mixer import enhanced_F_k_v2, ancilla16

# Deterministic mixer (reproducible)
k_next = enhanced_F_k_v2(
    k=12345, t=0, seed=b"my_seed_32bytes!",
    dk=1, alpha=1000, gamma=100, c=42, n=(1<<64), r=10,
    redshift=lambda r: r // 10,
    J=lambda k: hash(k),
    sign=lambda x: 1 if x >= 0 else -1,
    teleport_share=my_teleport_fn,
    use_real_rng=False,  # Deterministic by default
)
```

**Full documentation:** [MATHEMATICS.md](MATHEMATICS.md) Section 9  
**Tests:** `tests/test_mixer.py` (22 tests, all passing)

---

## Halo2 Multi-Step Teleport Circuit

**New in v0.2.0:** ZK circuit proof system for multi-step scalar transitions.

Proves a chain of deterministic mixing steps in Halo2:

$$Q_0 \to Q_1 \to \cdots \to Q_m \text{ where } Q_i = k_i \cdot G$$

**Key constraints:**
- Limb decomposition (16×16-bit representation)
- U16 matrix multiply (mod $2^{16}$ per limb)
- Ancilla XOR (deterministic routing)
- Recomposition and EC scalar mul
- Final point equality

**Complexity:** ~900 rows per step, $O(m)$ total scaling

**Implementation:** `src/geophase/halo2_circuit.py`  
**Tests:** `tests/test_halo2_circuit.py` (23 tests, all passing)

---

## Security Model

**Confidentiality and integrity** reduce to **standard AEAD** (placeholder: plaintext transport in harness; real build uses authenticated encryption).

**Robustness** is achieved via **error-correcting codes** and black-box verified under noise.

## Structure

```
dual-chain-geophase/
├─ README.md                           # This file
├─ LICENSE                             # MIT License
├─ SECURITY.md                         # Security policy & reporting
├─ MATHEMATICS.md                      # Mathematical foundations (Sections 1–9)
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
│  ├─ covenant.py                      # AEAD verification (sole acceptance gate)
│  ├─ mixer.py                         # Enhanced hybrid chaotic state mixer (v2) ⭐ NEW
│  ├─ halo2_circuit.py                 # Multi-step teleport ZK circuit ⭐ NEW
│  ├─ param_vectors.py                 # Dual-phase parameter vectors
│  ├─ util.py                          # Canonical JSON, b64 helpers
│  ├─ dual_phase.py                    # Audit-only angular distance
│  └─ __pycache__/
└─ tests/
   ├─ test_smoke.py                    # Smoke tests
   ├─ test_covenant_gate.py             # AEAD covenant tests
   ├─ test_dual_phase_distance.py      # Parameter orthogonality tests
   ├─ test_ecc_blackbox.py             # ECC black-box tests
   ├─ test_mixer.py                    # Mixer unit tests ⭐ NEW
   ├─ test_halo2_circuit.py            # Halo2 circuit tests ⭐ NEW
   ├─ test_waffle_codec.py             # Carrier codec tests
   └─ __pycache__/
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

## How It Works

### Encode
```
message M
  → build Associated Data (AD) binding public context
  → AEAD encrypt → ciphertext C
  → interleave + ECC encode
  → carrier bytes (noise-tolerant)
```

### Verify
```
carrier bytes
  → ECC decode + deinterleave (best effort)
  → candidate ciphertext Ĉ
  → AEAD verify/decrypt (SOLE gate)
  → ACCEPT + recover M   OR   REJECT
```

**Key invariant:** ECC can corrupt, fail to recover, or succeed.  
Only AEAD decides which outcome is valid. Transport noise cannot leak into trust decisions.

---

## Architecture

### Dual Chains

#### Message Chain (Trust)
- AEAD-protected payloads (ChaCha20-Poly1305)
- Acceptance gated exclusively by AEAD verification
- Immutable security boundary

#### Transport Chain (Robustness)
- Reed–Solomon ECC + deterministic interleaving
- Length framing (decode boundaries explicit, never guessed)
- Tuning parameters (NSYM, noise metrics)

## The Security Model

**Confidentiality & Integrity** → AEAD (ChaCha20-Poly1305)

**Robustness** → ECC + interleaving (transport-only)

**Covenant Enforcement** → immutable gate + CI tripwires

For detailed treatment, see [GEOPHASE.md](GEOPHASE.md) and [MATHEMATICS.md](MATHEMATICS.md).

## Current Status

✅ **v0.2.0 (Covenant + ECC Integrated + Dual Geo Phase Audit)**

- [x] AEAD encryption (ChaCha20-Poly1305)
- [x] Reed–Solomon ECC with deterministic interleaving
- [x] Covenant enforcement (immutable gate + CI tests)
- [x] Dual Geo Phase structural audit (28 tests, batch + strict checks)
- [x] T1–T4 black-box verification harness
- [x] Deterministic + HKDF KDF modes (feature-flagged)
- [x] Complete documentation (tuning guide, release notes, audit guide)

**All tests passing:** 67/67 (28 dual-phase + 39 core/transport tests)  
**Covenant preserved:** 5 non-regression tripwires, all green  
**Angular distance audit:** Dual phases decorrelated (cosine < 0.95, 95% pass rate)

## Testing

Run all tests (67 total):
```bash
python -m pytest tests/ -v
```

Run just dual-phase audit (28 tests):
```bash
python -m pytest tests/test_dual_phase_distance.py -v
```

See [DUAL_GEO_PHASE.md](DUAL_GEO_PHASE.md) for audit methodology and results.

## Transport Tuning

Reed–Solomon (ECC) error correction is configurable for different channel noise profiles.

### NSYM (Redundancy Bytes)

- **NSYM=64** (default): Corrects ≤32 byte errors per block
  - Suitable for ~99% of white-noise channels
  - Overhead: +64 bytes per 1024-byte carrier
  
- **NSYM=96, 128**: For harsher channels (FM, satellite, etc.)
  - See [ECC_TUNING.md](ECC_TUNING.md) for measurement procedure

### Feature Flags

```bash
# Test mode (default): Deterministic KDF for reproducibility (T1)
python scripts/encode_blackbox.py < request.json

# Production mode: HKDF-SHA256 for randomness/strength
GEOPHASE_USE_HKDF=1 python scripts/encode_blackbox.py < request.json
```

**Key invariant:** Changing ECC tuning or KDF never affects the security covenant. AEAD remains the sole acceptance gate.

See [ECC_TUNING.md](ECC_TUNING.md) for detailed tuning, measurement, and proof.

## Documentation

- **[GEOPHASE.md](GEOPHASE.md)** — Conceptual model & architecture
- **[ECC_TUNING.md](ECC_TUNING.md)** — Noise robustness tuning & T4 measurement
- **[RELEASE_v0.2.0.md](RELEASE_v0.2.0.md)** — Release notes & feature summary
- **[SECURITY.md](SECURITY.md)** — Security policy & covenant enforcement
- **[MATHEMATICS.md](MATHEMATICS.md)** — Formal proofs & theorems

## Auditor Checklist

- Verify covenant gate: [src/geophase/covenant.py](src/geophase/covenant.py)
- Verify CI tripwires: [tests/test_covenant_gate.py](tests/test_covenant_gate.py)
- Verify AEAD primitive: [src/geophase/codec.py](src/geophase/codec.py)
- Verify black-box harness: [scripts/public_test.py](scripts/public_test.py)
- Verify tuning procedure: [ECC_TUNING.md](ECC_TUNING.md)

## License

MIT. See [LICENSE](LICENSE).

## Security & Disclosure

GeoPhase's security rests entirely on:

1. Standard cryptographic primitives (AEAD, SHA-256, Reed–Solomon)
2. The covenant rule (`ACCEPT ⇔ AEAD_verify(...)`)
3. Enforcement via immutable types and CI tripwires

For security concerns, see [SECURITY.md](SECURITY.md).
