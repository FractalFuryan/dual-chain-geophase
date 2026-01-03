# Security Policy

This repo is intended for **public verification** and **black-box testing**.
It intentionally does not include private carrier schedules, keys, or deployment parameters.

## ECC–AEAD Covenant (Non-Negotiable)

This project enforces a strict separation between **transport repair** and **cryptographic authorization**.

### Covenant Statement
**Error-correcting codes may repair transport noise, but they must never confer validity.  
Only authenticated decryption may authorize acceptance.**

### Formal Rule
Let:
- $ct = \text{AEAD}_K(\text{plaintext}, AD)$ (authenticated ciphertext)
- $w = \text{ECC\_encode}(ct)$ (ECC-encoded carrier)
- $\tilde{w} = w + \eta$ (channel noise / corruption)
- $\hat{c} = \text{ECC\_decode}(\tilde{w})$ (best-effort ECC repair)

Then:
$$\boxed{\text{ACCEPT} \iff \mathrm{AEAD\_verify}_K(\hat{c}, AD)=\text{true}}$$

### Acceptance Logic (Immutable)
Explicitly forbidden:
- ACCEPT based on ECC success, syndrome weight, plausibility, heuristics, or partial decoding.

Only **AEAD verification** may authorize acceptance.

### Rationale
ECC is a transport-layer reliability mechanism. It may output:
- corrected ciphertext,
- uncorrected ciphertext,
- or arbitrary garbage.

**AEAD verification is the sole acceptance gate.**  
Any change violating this covenant is a security defect.

### Enforcement
- Code pattern: `src/geophase/covenant.py` (centralized verify gate)
- CI test: `tests/test_covenant_gate.py` (non-regression tripwire)
- Every acceptance path must route through the covenant gate

---

## Reporting

If you believe you have found an issue that causes:
- false ACCEPT,
- integrity bypass,
- key misuse,
- nonce reuse vulnerabilities,
- **covenant violation** (ECC deciding acceptance),

please report with:
- the failing test case,
- minimal reproduction steps,
- expected vs actual behavior.

## Testing

All test harness code is designed to be:
- **deterministic** (for reproducibility)
- **independent** (no private state outside scripts)
- **transparent** (source code publicly readable)

Do not use this implementation in production without:
- Formal cryptographic review
- Integration of real AEAD and ECC implementations
- Noise-robust carrier encoding
- Covenant gate enforcement in all code paths
