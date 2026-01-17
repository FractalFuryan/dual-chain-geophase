# Proprietary Components Notice

**Effective Date:** January 16, 2026

## Purpose

This repository intentionally separates **verifiable trust code** from **proprietary execution logic**.

The system architecture ensures that ethical guarantees, privacy constraints, and revocation enforcement are fully auditable, while protecting competitive implementation details that do not affect these guarantees.

---

## Proprietary Components (NOT Open Source)

The following components are **excluded from any public license grant** and are subject to proprietary EULA terms:

### Core Implementation
- **GeoPhase internal algorithms** - Exact transforms, constants, schedules
- **Dual-phase coupling logic** - Phase A / Phase B interaction mechanisms
- **Parameter schedules and constants** - Tuning values, weights, entropy routing
- **Teleport heuristics** - Thresholds, schedules, optimization strategies
- **Cosine buffer implementations** - Specifications may be public; code is closed
- **Living Cipher runtime** - Any code under `/living-cipher` or equivalent directories

### Performance & Optimization
- **GPU / shader implementations** - CUDA, WebGL, compute shader code
- **SIMD optimizations** - Vectorized execution paths
- **Batching strategies** - Performance-critical execution patterns
- **Production wiring** - FastAPI internals beyond public API gates

### Internal Tooling
- **Circuit optimizations** - Gate layouts, lookup table encodings
- **Field decompositions** - Arithmetic circuit implementation details
- **Any "why this works well" tuning** - Trade secrets related to effectiveness

---

## Open Source Components (MIT Licensed)

The following components ARE open source and serve the purpose of **verifiable trust**:

### Trust Layer
- **Commitment formats** (`geocommit.py`, `PREFIX_V1`)
- **Ethics anchors** + invariants
- **Smart contracts** (attestation + revocation registries)
- **Public API surface** (request/response shapes only)
- **ZK specifications** (statements, constraints, security bounds)
- **Test harnesses** proving determinism and fail-closed behavior
- **Documentation** explaining *what is enforced*

### Infrastructure
- **Ethereum bridge** (Base L2 integration)
- **Bytecode lock** verification
- **Fail-closed safety modes**
- **Metrics** (non-behavioral, privacy-safe)
- **Settings** (enforcement configuration)

---

## Legal Boundaries

### Rule of Thumb

> **Open source proves *that* the system is ethical.**  
> **Proprietary code defines *how* it actually works.**

### Prohibited Activities

Without explicit written permission, the following are **prohibited**:

1. **Reverse engineering** proprietary components
2. **Extraction** of algorithms, constants, or optimization strategies
3. **Derivative works** based on proprietary execution logic
4. **Reimplementation** of GeoPhase internal math or dual-phase coupling
5. **Performance analysis** aimed at replicating proprietary optimizations

### Permitted Activities

You MAY:

1. **Audit** verifiable trust components (commitments, ethics, contracts)
2. **Verify** privacy guarantees and fail-closed behavior
3. **Test** revocation enforcement and determinism
4. **Use** public API specifications for integration
5. **Read** documentation explaining constraints and guarantees

---

## Why This Boundary Exists

### For Regulators
- All compliance-critical components are auditable
- Ethical constraints are enforced by architecture, not trust
- Privacy guarantees are verifiable without accessing internals

### For Users
- Revocation is enforceable and auditable
- No hidden data collection or personalization
- Ethics anchors provide immutable guarantees

### For the Business
- Trade secrets remain protected
- Competitive advantage is preserved
- Sustainable monetization is possible
- Prevents unsafe reimplementation

---

## Verification Without Disclosure

Regulators and auditors can verify:

- ✅ On-chain commitments (Base L2, public blockchain)
- ✅ Immutable ethics anchors
- ✅ Revocation enforcement (fail-closed by default)
- ✅ Deterministic behavior (test harnesses provided)
- ✅ Zero storage of personal data (contract-level enforcement)
- ✅ Absence of learning/memory/profiling (architectural constraint)

**None of these verifications require access to proprietary implementation details.**

---

## Contact

For licensing inquiries regarding proprietary components:

**Email:** [Insert licensing contact]  
**Entity:** [Insert legal entity name]

---

## Compliance Statement

This notice complies with:

- Trade secret protection requirements (U.S. Defend Trade Secrets Act)
- Open source license clarity (OSI guidelines)
- Dual-licensing best practices (copyleft + proprietary separation)

**Last Updated:** January 16, 2026
