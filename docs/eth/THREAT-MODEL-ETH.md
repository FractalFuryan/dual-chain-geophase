# Threat Model: GeoPhase ↔ Ethereum Bridge

**Version:** 1.0  
**Chain:** Base (L2)  
**Scope:** Attestation + Revocation Registries

---

## 1. System Architecture

### Components

```
┌─────────────┐
│   Client    │  (MetaMask, wallet)
│  (EIP-712)  │
└──────┬──────┘
       │ signature
       ▼
┌─────────────────────────────────────────┐
│   Server (FastAPI)                      │
│   - Verify EIP-712                      │
│   - Compute geoCommit                   │
│   - Check revocation (read on-chain)    │
│   - Generate (off-chain)                │
│   - Optional: Attest (write on-chain)   │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│   Base L2 (Ethereum)                    │
│   - AnankeAttestationRegistry (write)   │
│   - AnankeRevocationRegistry (write)    │
└─────────────────────────────────────────┘
```

### Trust Boundaries

1. **Client → Server:** Signature-based (EIP-712)
2. **Server → Chain:** RPC calls (read/write)
3. **Chain → World:** Public ledger (immutable)

---

## 2. Assets

### What We Protect
- ✅ **Privacy:** No user data on-chain
- ✅ **Provenance:** Immutable attestations
- ✅ **Revocability:** User-controlled opt-out
- ✅ **Integrity:** Commitment binding (hash-based)

### What We Do NOT Protect
- ❌ Off-chain data (seeds, vectors, media)
- ❌ Server infrastructure security
- ❌ Wallet security (user responsibility)
- ❌ Smart contract vulnerabilities (audits required)

---

## 3. Threat Actors

| Actor | Capability | Motivation |
|-------|-----------|------------|
| **Malicious User** | Sign EIP-712, call contracts | Abuse system, spam, fraud |
| **Compromised Server** | Read DB, compute geoCommits | Data theft, unauthorized generation |
| **Contract Attacker** | Call contract functions | DoS, state manipulation |
| **MEV Bot** | Front-run transactions | Extract value, manipulate attestations |
| **State Actor** | Subpoena, chain analysis | Surveillance, de-anonymization |

---

## 4. Threat Scenarios

### 4.1 Privacy Violations

#### T1: On-Chain Inference Attack
**Threat:** Adversary infers user data from geoCommits.

- **Attack Vector:** Analyze geoCommit patterns, linkability
- **Mitigation:**
  - Use `user_nonce` in seed commits (prevents rainbow tables)
  - No cross-user correlation (each geoCommit is unique)
  - Hashes are one-way (keccak256, sha256)
- **Residual Risk:** LOW (cryptographic hardness)

#### T2: Transaction Metadata Leakage
**Threat:** Wallet address reveals user identity.

- **Attack Vector:** Link wallet to attestation transactions
- **Mitigation:**
  - Use burner wallets for attestations
  - Optional: Tornado Cash / privacy pool (future)
  - Server-side attestation (server wallet, not user)
- **Residual Risk:** MEDIUM (blockchain transparency)

#### T3: Off-Chain Data Breach
**Threat:** Server DB contains seeds/vectors.

- **Attack Vector:** SQL injection, server compromise
- **Mitigation:**
  - **Never store raw seeds/vectors** (compute hashes only)
  - Encrypt at rest (if storage is necessary)
  - Access controls, audit logs
- **Residual Risk:** HIGH (out-of-scope for chain bridge)

---

### 4.2 Integrity Attacks

#### T4: Attestation Forgery
**Threat:** Adversary creates fake attestations.

- **Attack Vector:** Call `attest()` with arbitrary geoCommit
- **Mitigation:**
  - Write-once semantics (cannot overwrite)
  - Server-controlled attestor wallet (only server can attest)
  - Optional: Multi-sig or DAO governance
- **Residual Risk:** LOW (contract enforcement)

#### T5: Revocation Bypass
**Threat:** User revokes, but generation proceeds.

- **Attack Vector:** Server ignores revocation check
- **Mitigation:**
  - **Always** check `isRevoked()` before generation
  - Circuit breaker if RPC fails (fail-safe: block generation)
  - Monitor revocation events (off-chain indexer)
- **Residual Risk:** MEDIUM (server compliance)

#### T6: Signature Replay Attack
**Threat:** Reuse EIP-712 signature for multiple generations.

- **Attack Vector:** Replay signed message
- **Mitigation:**
  - Include `nonce` in message (server tracks used nonces)
  - Include `expires` (short TTL, e.g., 1 hour)
  - Optional: Include `geoCommit` in signature (bind to specific generation)
- **Residual Risk:** LOW (if nonce tracking is implemented)

---

### 4.3 Availability Attacks

#### T7: Revocation Spam
**Threat:** Adversary revokes many geoCommits (DoS).

- **Attack Vector:** Call `revoke()` repeatedly
- **Mitigation:**
  - Gas costs (economic disincentive)
  - Rate limiting (off-chain indexer)
  - Optional: Require signature from original attestor
- **Residual Risk:** MEDIUM (gas is cheap on Base)

#### T8: RPC Failure
**Threat:** Base RPC is down, blocking generation.

- **Attack Vector:** Network outage, rate limits
- **Mitigation:**
  - Use multiple RPC providers (failover)
  - Cache revocation state (short TTL)
  - Degraded mode: allow generation with logging
- **Residual Risk:** MEDIUM (third-party dependency)

#### T9: Contract Upgrade Attack
**Threat:** Malicious upgrade changes logic.

- **Attack Vector:** Owner deploys new contract logic
- **Mitigation:**
  - **No upgradability** in v1 (simple contracts, no proxies)
  - Future: Use transparent proxy with timelock
  - Governance: Multi-sig or DAO for upgrades
- **Residual Risk:** LOW (no upgrades in v1)

---

### 4.4 Economic Attacks

#### T10: MEV Front-Running
**Threat:** MEV bot front-runs attestation to claim geoCommit.

- **Attack Vector:** See pending `attest()` tx, submit with higher gas
- **Mitigation:**
  - Use Flashbots RPC (private mempool)
  - Write-once semantics (first tx wins)
  - Attestation is optional (no value at risk)
- **Residual Risk:** LOW (no economic incentive)

#### T11: Gas Price Manipulation
**Threat:** Adversary spikes gas to make attestations expensive.

- **Attack Vector:** Spam network during attestation
- **Mitigation:**
  - Attestations are optional (defer if gas is high)
  - Use EIP-1559 (predictable gas)
  - Server monitors gas prices (wait for low gas)
- **Residual Risk:** LOW (L2 gas is stable)

---

## 5. Mitigations Summary

### Implemented (v1)

| Threat | Mitigation | Status |
|--------|-----------|--------|
| T1 | User nonces, one-way hashes | ✅ Implemented |
| T4 | Write-once attestations | ✅ Contract-enforced |
| T5 | Pre-generation revocation check | ✅ Middleware |
| T6 | Expiration timestamps | ✅ EIP-712 |
| T8 | Multiple RPC providers (config) | ✅ Configurable |
| T9 | No upgradability | ✅ Simple contracts |

### Recommended (v1.1+)

| Threat | Mitigation | Priority |
|--------|-----------|----------|
| T2 | Server-side attestation wallet | HIGH |
| T3 | Never store raw seeds | CRITICAL |
| T6 | Nonce tracking (anti-replay) | MEDIUM |
| T7 | Rate limiting / gas analysis | LOW |
| T8 | Revocation state caching | MEDIUM |
| T10 | Flashbots RPC | LOW |

### Future Research

- Zero-knowledge proofs (prove geoCommit validity without revealing components)
- Privacy pools (break wallet linkability)
- Decentralized attestation (DAO-controlled)

---

## 6. Security Assumptions

### Chain-Level
- ✅ Base L2 is secure (Optimism stack)
- ✅ Keccak256 / SHA256 are collision-resistant
- ✅ ECDSA signature recovery is secure

### Server-Level
- ⚠️ Server does NOT store sensitive data
- ⚠️ Server verifies signatures correctly
- ⚠️ Server enforces revocation checks

### User-Level
- ⚠️ User protects wallet private key
- ⚠️ User understands signature scope (procedural only)

---

## 7. Incident Response

### If a geoCommit is compromised:
1. User calls `revoke(geoCommit)` on-chain
2. Server blocks future generations (automatic)
3. Existing media is **not** automatically deleted (off-chain)

### If contract is exploited:
1. Deploy new contracts (no upgrade path)
2. Migrate attestations (off-chain indexer)
3. Update server config (`ATTESTATION_REGISTRY_ADDR`)

### If server is compromised:
1. Rotate server wallet (if used for attestations)
2. Audit recent attestations (check for anomalies)
3. Notify users (if PII was exposed—should be none)

---

## 8. Audit Checklist

### Pre-Deployment
- [ ] No user data in contracts (only hashes)
- [ ] Write-once attestation logic verified
- [ ] Revocation cannot be reversed
- [ ] Gas costs are acceptable
- [ ] RPC failover configured

### Post-Deployment
- [ ] Contracts verified on Basescan
- [ ] Server middleware enforces revocation
- [ ] EIP-712 signatures verified correctly
- [ ] No secrets in environment variables (use secrets manager)

---

## 9. References

- [OWASP Smart Contract Top 10](https://owasp.org/www-project-smart-contract-top-10/)
- [ConsenSys Smart Contract Best Practices](https://consensys.github.io/smart-contract-best-practices/)
- [Base Security Docs](https://docs.base.org/security/)
- [EIP-712 Security Considerations](https://eips.ethereum.org/EIPS/eip-712#security-considerations)

---

**Maintained by:** FractalFuryan  
**Last Updated:** 2026-01-16  
**License:** MIT
