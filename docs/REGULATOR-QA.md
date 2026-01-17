# Regulator Q&A — GeoPhase / Ananke System

**Last Updated:** January 16, 2026  
**Version:** 1.0  
**Audience:** Regulators, auditors, policy makers, compliance officers

---

## Purpose

This document addresses common regulatory questions about the GeoPhase system's architecture, privacy guarantees, ethical constraints, and verifiability.

All statements below are **enforceable by construction**, not policy promises.

---

## Q1. Why are parts of the system proprietary?

**Answer:**

The system separates **verifiable ethical guarantees** from **implementation-specific execution logic**.

All components required to verify:

- Ethical constraints
- Privacy guarantees  
- Revocation enforcement
- Non-personalization
- Non-likeness generation
- Fail-closed safety behavior

are **fully documented and auditable**.

Implementation details that do not affect these guarantees (e.g., internal math constants, performance optimizations, execution strategies) are proprietary to prevent:

- Unsafe reimplementation
- Malicious cloning  
- Trade secret theft
- Regulatory arbitrage through copying

This is **standard practice** in cryptographic and safety-critical systems (see: TLS implementations, HSM firmware, medical device software).

---

## Q2. How can regulators verify compliance if internals are closed?

**Answer:**

Compliance is enforced **by construction**, not by trust.

### Regulators Can Verify

**On-Chain (Base L2 Blockchain):**
- Cryptographic commitments (immutable, timestamped)
- Ethics anchor references (immutable policy identifiers)
- Revocation status (user-controlled, irreversible)
- Zero storage of personal data (verifiable via contract code)

**API Layer (Open Source):**
- Fail-closed behavior (code inspection + test harnesses)
- Bytecode integrity verification (contract hash validation)
- Deterministic commit computation (`PREFIX_V1` standard)
- Revocation gate enforcement (pre-generation blocking)

**System Architecture:**
- No ML training (no model updates, no gradients)
- No memory (stateless execution, ephemeral outputs)
- No behavioral profiling (no engagement metrics)
- No identity convergence (geometric constraints, not anatomical)

### What Cannot Be Overridden

No internal algorithm can bypass:

1. **Contract-level revocation** (enforced on-chain before generation)
2. **Ethics anchor immutability** (policy IDs are write-once)
3. **Commitment-only storage** (contracts reject media, names, identifiers)
4. **Fail-closed defaults** (RPC unreachable = generation blocked)
5. **Bytecode lock** (deployed contracts must match expected hash)

These properties are enforced at:
- Smart contract level (Solidity, deployed to Base L2)
- API gate level (Python middleware, open source)
- CI level (automated test suite, 19/19 passing)
- Runtime assertions (fail-fast on constraint violations)

---

## Q3. Does the system store or process personal data?

**Answer:**

**No.**

The system **never** stores:

- ❌ Biometric data
- ❌ Likeness data (photos, videos, 3D scans)
- ❌ Images or videos (input or output)
- ❌ Behavioral profiles
- ❌ Engagement metrics (time spent, preferences, click patterns)
- ❌ Identity information (names, addresses, identifiers)

### What IS Stored (On-Chain Only)

✅ **Cryptographic commitments** (keccak256 hashes, 32 bytes each)  
✅ **Policy identifiers** (ethics anchor references, 32 bytes each)  
✅ **Timestamps** (block numbers, automatically set by blockchain)  
✅ **Revocation bits** (boolean flags, user-controlled)

**All on-chain data is commitment-only.** No media, no metadata, no reversibility.

---

## Q4. Can the system generate content resembling a specific person?

**Answer:**

**No.**

The system explicitly forbids:

- ❌ Identity convergence (cannot refine toward an individual)
- ❌ Likeness reconstruction (cannot recreate faces, bodies, voices)
- ❌ Biometric mapping (no facial landmarks, no proportions, no anatomy)
- ❌ Pose or gesture inference (no skeletal models, no motion capture)

### Enforcement Mechanism

**User inputs** may only influence **procedural variation tokens**, which:

- Select abstract parameter spaces (geometry, not anatomy)
- Do NOT encode identity, proportions, or resemblance
- Cannot be iteratively refined toward a target individual
- Operate in high-dimensional noise spaces with no convergence guarantee

**Architectural constraints:**

- No reference images allowed (input rejection)
- No "likeness tuning" APIs (not exposed)
- No similarity scoring (no comparison metrics)
- No anatomical priors (no skeleton, no facial models)

---

## Q5. Why allow probabilistic human-like interpretations at all?

**Answer:**

Incidental perceptual interpretations can arise in **any** sufficiently expressive abstract system (cloud shapes, Rorschach tests, pareidolia).

The system prevents harm not by **banning interpretation**, but by enforcing:

### Structural Safeguards

✅ **Probabilistic distance** - No two seeds converge  
✅ **No repeatability** - Cannot regenerate toward individuals  
✅ **No refinement paths** - No "closer to X" optimization  
✅ **Geometric basis** - Abstract math, not anatomical models  

This approach is **more robust** than post-hoc filtering because:

1. It eliminates the convergence path itself (not just the final output)
2. It avoids introducing anatomical models (which create attack surfaces)
3. It prevents "adversarial prompt injection" (no target matching allowed)

**Analogy:** A kaleidoscope may produce patterns that resemble faces, but it structurally cannot be refined to match a specific person's face.

---

## Q6. Can users revoke participation?

**Answer:**

**Yes. Revocation is:**

✅ **User-initiated** - No approval needed, no intermediaries  
✅ **On-chain** - Immutable record on Base L2 blockchain  
✅ **Enforced at generation time** - Pre-generation gate checks revocation status  
✅ **Irreversible** - Once revoked, regeneration is cryptographically blocked  
✅ **Fail-closed by default** - RPC errors block generation (no silent bypasses)

### How It Works

1. User calls `revoke(geoCommit)` on revocation registry (Base L2)
2. Transaction is mined, revocation bit set permanently
3. Next generation attempt checks `isRevoked(geoCommit)` on-chain
4. If revoked, generation is **blocked before execution** (fail-closed gate)
5. No regeneration possible for that commitment (immutable blockchain state)

**Test Coverage:** 6 fail-closed tests verify this behavior (100% passing).

---

## Q7. Is this system designed to maximize engagement or arousal?

**Answer:**

**No.**

The system explicitly forbids:

- ❌ Engagement optimization (no A/B testing, no metrics)
- ❌ Reinforcement learning (no user feedback loops)
- ❌ Escalation loops (no "intensity tuning" based on behavior)
- ❌ Personalization feedback (stateless execution, no memory)

### Additional Safeguards

✅ **Optional clinical modes** - Reduced intensity, muted palettes  
✅ **Optional harm-reduction modes** - Further constraints on output  
✅ **No analytics tracking** - No behavioral data collected  
✅ **No recommendation engine** - No "similar to this" suggestions  

**Design Philosophy:** Expressive freedom without exploitation mechanics.

---

## Q8. Why is Ethereum (Base L2) used at all?

**Answer:**

Ethereum (via Base L2) is used **solely** for:

✅ **Timestamped provenance** - When was this commitment made?  
✅ **Revocation enforcement** - Can this be regenerated?  
✅ **Public auditability** - Regulators can verify on-chain state  
✅ **Immutability** - Ethics anchors cannot be changed post-deployment  

### What Is NOT Stored On-Chain

❌ Content (no images, videos, media)  
❌ Identity data (no names, addresses, biometrics)  
❌ Behavioral data (no engagement, preferences, history)  
❌ Metadata (no tags, captions, descriptions)  

**Only cryptographic hashes** (32-byte commitments, irreversible).

### Why Base L2 Specifically?

- Low gas costs (~$0.10/attestation vs ~$50 on Ethereum L1)
- 1-2 second finality (fast revocation enforcement)
- EVM-compatible (standard Solidity contracts, widely audited)
- Backed by Coinbase (institutional-grade reliability)

---

## Q9. Can the system be audited in production?

**Answer:**

**Yes.**

### Audit Points

**Smart Contracts (Deployed on Base L2):**
- `AnankeAttestationRegistry.sol` - Provenance commitments
- `AnankeRevocationRegistry.sol` - User-controlled opt-out
- Deployed bytecode matches expected hash (bytecode lock enforced)

**API Gates (Open Source):**
- `fastapi_middleware.py` - Revocation enforcement
- `chain_check.py` - On-chain reads/writes
- `geocommit.py` - Canonical commit computation

**Test Harnesses (19/19 Passing):**
- Canonical commit validation (8 tests)
- Bytecode lock integrity (5 tests)
- Fail-closed safety (6 tests)

**Metrics (Non-Behavioral Only):**
- RPC latency (gauge)
- Revocation checks (counter)
- Gate blocks (counter)
- **NO user behavior**, **NO content metrics**

---

## Q10. What happens if the company disappears?

**Answer:**

### User Protections

✅ **Smart contracts are immutable** - Cannot be shut down or modified  
✅ **Revocation remains enforceable** - On-chain state persists forever  
✅ **No centralized data storage** - Nothing to "lose access to"  
✅ **Open source trust layer** - Can be verified independently  

### What Users Lose

❌ Access to proprietary generation engine (Living Cipher runtime)  
❌ API endpoints (if servers shut down)  
❌ Support and updates  

### What Users KEEP

✅ Revocation rights (permanent, on-chain)  
✅ Commitment provenance (immutable blockchain records)  
✅ Ability to verify ethics anchors (contracts remain deployed)  

**Bottom Line:** User agency persists independently of the company.

---

## Summary Statement

This system is designed to preserve **expressive freedom** while **structurally eliminating** the known harm vectors of traditional NSFW platforms:

| Traditional Platforms            | GeoPhase Architecture              |
| -------------------------------- | ---------------------------------- |
| ❌ Store biometric/likeness data | ✅ Zero storage (commitment-only)  |
| ❌ ML-driven personalization     | ✅ Stateless, no learning          |
| ❌ Engagement optimization       | ✅ No analytics, no feedback loops |
| ❌ Identity convergence possible | ✅ Geometric constraints prevent   |
| ❌ Revocation by policy          | ✅ Revocation by cryptography      |
| ❌ Proprietary black boxes       | ✅ Verifiable trust layer          |

**Ethical guarantees are enforced by architecture, not policy.**

---

## Contact for Regulatory Inquiries

**Technical Contact:** [Insert email]  
**Legal Contact:** [Insert email]  
**Compliance Officer:** [Insert name/email]  

**Documentation:**
- [PROPRIETARY-NOTICE.md](../PROPRIETARY-NOTICE.md) - IP boundaries
- [ETH-BRIDGE-SHIPPED.md](eth/ETH-BRIDGE-SHIPPED.md) - Ethereum integration
- [THREAT-MODEL-ETH.md](eth/THREAT-MODEL-ETH.md) - Security analysis
- [GEO-COMMIT-SPEC.md](eth/GEO-COMMIT-SPEC.md) - Commitment format

**Last Updated:** January 16, 2026
