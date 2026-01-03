# Documentation Index

Quick navigation to GeoPhase Chain documentation by topic and audience.

## Starting Here

- **[README.md](README.md)** — Overview, quickstart, auditor checklist
- **[GEOPHASE.md](GEOPHASE.md)** — Conceptual model, covenant, threat model

## For Auditors & Reviewers

1. **[SECURITY.md](SECURITY.md)** — Covenant rule, non-claims, disclosure policy
2. **[MATHEMATICS.md](MATHEMATICS.md)** — Formal theorem, proof sketch, acceptance gate definition
3. **[GEOPHASE.md](GEOPHASE.md#threat-model-scope)** — Threat model & assumptions
4. **[src/geophase/covenant.py](src/geophase/covenant.py)** — Acceptance gate implementation
5. **[tests/test_covenant_gate.py](tests/test_covenant_gate.py)** — CI non-regression tripwires

## For Implementers & Integrators

- **[QUICKSTART.md](QUICKSTART.md)** — Setup, encode/verify, first test
- **[ECC_TUNING.md](ECC_TUNING.md)** — NSYM tuning matrix, measurement procedure, T4
- **[README.md#transport-tuning](README.md#transport-tuning)** — Feature flags (HKDF, NSYM)

## For Deployers & Operators

- **[INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md)** — Deployment checklist, version timeline
- **[RELEASE_v0.2.0.md](RELEASE_v0.2.0.md)** — What's new, performance, backwards compatibility
- **[ECC_TUNING.md#monitoring-and-operations](ECC_TUNING.md#monitoring-and-operations)** — Production monitoring

## Complete File Index

| File | Purpose | Audience |
|------|---------|----------|
| README.md | Overview + quickstart | Everyone |
| GEOPHASE.md | Concept + covenant | Architects, auditors |
| SECURITY.md | Security model + disclosure | Auditors |
| MATHEMATICS.md | Formal foundations | Auditors, cryptographers |
| ECC_TUNING.md | Noise robustness + T4 | Implementers, operators |
| QUICKSTART.md | Setup guide | Developers |
| RELEASE_v0.2.0.md | Release notes + blog | Product teams |
| INTEGRATION_SUMMARY.md | Status + deployment | Operators |
| DOCS_INDEX.md | This file | Navigation |

## Key Concepts at a Glance

### The Covenant
```
ACCEPT ⇔ AEAD_verify(ciphertext, AD) = true
```
Enforced by immutable types + CI tripwires. See [SECURITY.md](SECURITY.md).

### Architecture
- **Message chain:** AEAD-encrypted payloads (trust)
- **Transport chain:** ECC + interleaving (robustness)
- Chains linked by hashes, not authority

See [GEOPHASE.md](GEOPHASE.md#architecture-dual-chains).

### Tests (T1–T4)
- **T1:** Determinism (reproducibility)
- **T2:** Correctness (clean carrier works)
- **T3:** Rejection (tampering caught)
- **T4:** Noise robustness (ACCEPT rates across noise levels)

See [ECC_TUNING.md](ECC_TUNING.md#the-t4-measurement-procedure).

## Quick Links

- **GitHub:** https://github.com/FractalFuryan/dual-chain-geophase
- **Test Status:** [![CI](https://github.com/FractalFuryan/dual-chain-geophase/actions/workflows/ci.yml/badge.svg)](https://github.com/FractalFuryan/dual-chain-geophase/actions/workflows/ci.yml)
- **License:** MIT
