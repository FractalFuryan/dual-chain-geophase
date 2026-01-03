# GeoPhase

GeoPhase is a **transport + verification pattern** for authenticated ciphertext.

It is **not** a new cryptographic primitive.

## The Problem

> **How do we move authenticated ciphertext through noisy or lossy channels,
> without letting "transport success" be mistaken for "authenticity"?**

GeoPhase solves this by separating:

- **Truth** (cryptographic authorization via AEAD)
- **Survivability** (geometric/transport robustness via ECC + interleaving)

This separation prevents a class of real-world failures where error correction or noise handling accidentally becomes a trust decision.

## The Core Covenant

> **ACCEPT ⇔ AEAD_verify(ciphertext, AD) = true**

Everything else in the system exists to help ciphertext *arrive intact* — never to help it *be believed*.

This covenant is enforced by:

- A single acceptance gate (`verify_gate()` in `src/geophase/covenant.py`)
- Immutable `VerifyResult` type (no fallible intermediate states)
- CI tripwire tests (5 non-regression checks, run on every commit)

Breaking the covenant is structurally difficult by design.

## Why "GeoPhase"?

- **Geo** → transport geometry: interleaving, error correction, noise distribution, channel shape
- **Phase** → deterministic, step-indexed evolution
  - each block advances the system one phase forward
  - bound to block index `t` and prior state hash

No quantum assumptions. No mystical claims.

"Geometry" here is engineering geometry: *data moving through noise*.

## Threat Model (Scope)

Assume an adversary can:

- Corrupt carrier bytes (bounded noise / bit corruption)
- Replay old carriers
- Reorder blocks
- Observe ciphertexts

Assume an adversary cannot:

- Break the AEAD primitive (ChaCha20-Poly1305)
- Recover secret keys from the implementation environment
- Control the entropy source (for random-nonce mode)

**Security claims in this repo:**

- Authenticity / integrity reduce to AEAD verification
- Noise robustness reduces to ECC correction radius + interleaving
- Transport layer never influences acceptance decisions

## Architecture (Dual Chain)

GeoPhase uses two logically separate chains:

### 1) Message Chain (Trust)

- AEAD-protected payloads (ChaCha20-Poly1305)
- Acceptance gated exclusively by AEAD verification
- Cryptographic boundary is immutable by covenant

### 2) Transport/State Chain (Robustness)

- ECC (Reed–Solomon) and interleaving strategy
- Length framing (decode boundaries are explicit, never guessed)
- Tuning parameters (e.g., NSYM) and optional noise receipts

The chains may be linked by hashes, **but never by authority**.

## Dataflow

### ENCODE

```
message M
  → build Associated Data (AD) binding public context
  → AEAD encrypt → ciphertext C
  → interleave + ECC encode (Reed–Solomon)
  → carrier bytes (noise-tolerant transport)
```

### VERIFY

```
carrier bytes
  → ECC decode + deinterleave (best effort, may fail)
  → candidate ciphertext Ĉ
  → AEAD verify/decrypt (SOLE acceptance gate)
  → ACCEPT + recover M   OR   REJECT
```

Key point: ECC can output corrected ciphertext, uncorrected ciphertext, or garbage.  
**Only AEAD decides which is valid.**

## What GeoPhase Is NOT

To be explicit:

- ❌ Not a new cipher
- ❌ Not a new MAC
- ❌ Not compression of ciphertext
- ❌ Not "post-quantum by magic"
- ❌ Not security by obscurity

GeoPhase **composes audited primitives** with explicit boundaries.

## Why This Is Safe

ECC can corrupt, fail to recover, or succeed unpredictably.

GeoPhase remains safe because:

1. Only AEAD can authorize acceptance
2. This rule is enforced by code structure
3. Violations are caught by CI tripwire tests
4. The acceptance gate is immutable and type-safe

Transport noise **cannot leak into the trust decision**.

## Where GeoPhase Fits

GeoPhase is useful for channels that are imperfect:

- Unreliable networks (packet loss, corruption)
- Lossy storage (flash, magnetic media with bit flips)
- Noisy physical links (RF, optical, spacecraft telemetry)
- Distributed systems with variable channel quality

The cryptographic core remains intentionally conservative (auditable, standard).  
The transport layer is tunable without touching crypto.

## Testability & Honesty

GeoPhase was designed to be **black-box testable from day one**.

That's why the repo includes:

- T1 (Determinism): same input → same output
- T2 (Correctness): clean carrier → ACCEPT + message recovery
- T3 (Rejection): AEAD catches tampering
- T4 (Noise Robustness): ACCEPT rate across noise levels

If GeoPhase fails, it fails *loudly* and *provably*.

See [ECC_TUNING.md](ECC_TUNING.md) for the T4 measurement procedure and covenant-preservation proof.

## Executive Summary

> **GeoPhase** is a covenant-first transport pattern for authenticated data.
> It separates cryptographic trust from geometric robustness, ensuring that
> error correction and noise handling can never authorize acceptance. By
> enforcing AEAD-gated verification and treating ECC as transport-only,
> GeoPhase enables tunable noise resilience, deterministic testing, and
> public auditability without introducing new cryptographic assumptions.

## Quick Links

- [README.md](README.md) — How to use GeoPhase
- [ECC_TUNING.md](ECC_TUNING.md) — Noise robustness tuning and T4 procedure
- [SECURITY.md](SECURITY.md) — Security model and covenant enforcement
- [MATHEMATICS.md](MATHEMATICS.md) — Formal treatment and proofs
