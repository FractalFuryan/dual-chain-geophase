# Claims Register

## Grounded (Mathematics)

- We use the classical Gaussian explicit formula as a fixed mathematical substrate.
- No new number-theoretic claims are made.
- The explicit formula remains unchanged: standard references are Titchmarsh, Ivic, Montgomery-Vaughan.
- Zero spectrum and prime contributions are defined per classical analytic number theory.

## Interpretive / Constraint-Layer (Speculative, Optional)

- We propose an optional stability constraint: off-critical spectral mass is treated as instability under bandwidth refinement.
- This is a tool for exploring interpretations of the explicit formula, not a mathematical theorem.
- The constraint layer does NOT modify the underlying mathematics.
- Users may choose to apply this interpretive frame or ignore it entirely.

## Engineering (GeoPhase / Cryptography)

- Cryptographic mechanisms (RFC6979 deterministic ECDSA nonces, commitments, attestations) are **independent** of the interpretive layer.
- All crypto code relies on well-established standards: RFC 6979, BIP 62, secp256k1 (Bitcoin/Ethereum).
- Security properties of crypto are NOT affected by interpretive claims about zeta zeros.

## Immutable Security Anchors

- See [SECURITY-ANCHORS.md](../SECURITY-ANCHORS.md) for cryptographic security properties that cannot change.
- RFC6979 nonce generation is deterministic, rejection-sampled, low-S normalized, and entropy-free.
- These properties are version-locked and require formal RFC + security review to change.

---

## Boundary Enforcement

This register is checked by automated CI gate ([tools/check_boundaries.py](../tools/check_boundaries.py)) on every pull request and push to main.

No code shall blend mathematical substrate, interpretive claims, or engineering standards without explicit labeling.

---

## Cross-References

- [SCALAR_WAZE_BOUNDARY.md](SCALAR_WAZE_BOUNDARY.md) - Mathematical substrate boundary
- [NON_CLAIMS.md](NON_CLAIMS.md) - Hard boundary on what is NOT claimed
- [../SECURITY-ANCHORS.md](../SECURITY-ANCHORS.md) - Immutable cryptographic security properties
