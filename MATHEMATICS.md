# Mathematical Foundations

This project deliberately builds on **well-established mathematics**. No new hardness assumptions are introduced. All novelty lies in *composition, separation of concerns, and verifiability*.

## 1. Hash-Chained Commitments

Each block links to the previous via cryptographic hashes:

$$H_t = H(H_{t-1} \parallel H(\text{payload}_t) \parallel H(\text{state}_t))$$

This ensures:

- Append-only structure
- Tamper evidence
- Order integrity

> Any secure hash function (e.g., SHA-256, BLAKE2) satisfies the requirements.

---

## 2. Authenticated Encryption (AEAD)

Confidential payloads are protected using standard AEAD:

$$\text{ct}_t = \text{AEAD}_{K_t}(M_t; \text{AD}_t)$$

Where:

- $M_t$ is the plaintext message
- $\text{AD}_t$ binds public commitments into authentication
- $K_t$ is derived via a standard KDF

Security reduces to the chosen AEAD primitive (e.g., AES-GCM, ChaCha20-Poly1305).

---

## 3. Error-Correcting Codes (ECC)

To tolerate bounded corruption in the carrier, ciphertexts are encoded:

$$W_t = \text{ECC\_encode}(\text{ct}_t)$$

Decoding succeeds provided noise remains within the code's correction radius:

$$\text{ECC\_decode}(W_t + \eta) = \text{ct}_t \quad \text{if } |\eta| \leq \tau$$

This is a **classical channel-coding model**; robustness comes from redundancy, not entropy violations.

---

## 4. Interleaving (Burst Error Mitigation)

Before ECC encoding, symbols may be permuted via an interleaver:

$$\pi : \{1,\dots,n\} \rightarrow \{1,\dots,n\}$$

This converts localized (burst) corruption into approximately independent errors, improving ECC performance.

---

## 5. Structured State & Compression

Structured state ($D_t$) is *separate* from encrypted payloads and may be compressed safely:

$$\Delta D_t = D_t - D_{t-1}$$

Compression applies **only** to $\Delta D_t$, never to ciphertext:

$$\text{comp}(\Delta D_t) \quad \text{with} \quad H(\Delta D_t) < |\Delta D_t|$$

This respects Shannon's source coding theorem.

---

## 6. Dual-Chain Separation (Core Invariant)

The system enforces a strict separation:

$$\boxed{\text{Secrecy} \perp \text{Structure}}$$

- **Secrecy** → AEAD + keys
- **Structure** → hashes, compression, public verification

No component depends on hidden mathematical assumptions.

---

## 7. Noise Accountability (Optional Extension)

An internal noise margin ($B_t \in [0,1]$) may be tracked and committed:

$$\text{NoiseReceipt}_t = H(B_t \parallel H_t)$$

This provides **public evidence of channel stress** without revealing carrier internals.

---

## Design Philosophy: Why This Math

- **Conservative primitives** → easy to audit
- **Explicit assumptions** → no hidden security claims
- **Black-box verifiable behavior** → trust via testing, not obscurity

All mathematical components are individually standard; their **composition** is what enables dual-chain auditability with noise-tolerant transport.

---

## Security Model Summary

| Component | Assumption | Strength | Notes |
|-----------|-----------|----------|-------|
| Hash chain | Collision resistance | $2^{-128}$ | SHA-256, BLAKE2 |
| AEAD | IND-CCA2 | $2^{-128}$ | AES-GCM, ChaCha20-Poly1305 |
| ECC | Random error model | Channel-dependent | Reed-Solomon, LDPC, Turbo |
| Interleaving | Symbol independence | Deterministic | No entropy cost |
| Compression | Source structure | Lossless only | Shannon coding bound |

None of these are novel. The **novelty is in composition and verification methodology**.

---

## 8. The ECC–AEAD Covenant (Acceptance Theorem)

Define the acceptance predicate:

$$\mathrm{Acc}(\tilde{w}, AD) := \begin{cases}
1 & \text{if } \mathrm{AEAD\_verify}_K(\mathrm{ECC\_dec}(\tilde{w}), AD)=\text{true}\\
0 & \text{otherwise}
\end{cases}$$

### Theorem (Authorization Isolation)
For any adversarial corruption process $\eta$, the system accepts **only** ciphertexts that pass AEAD verification under the bound key $K$ and associated data $AD$. ECC decoding success does not imply authenticity.

### Consequence
Transport coding choices (Reed–Solomon, LDPC, Turbo, interleaving) may change the *acceptance rate under noise* but cannot weaken authenticity unless they bypass AEAD.

### Proof Sketch
- ECC decoding outputs $\hat{c}$, which may be:
  - The correct ciphertext (with high probability if noise is within the code distance)
  - The uncorrected, noisy ciphertext
  - Garbage (if noise exceeds the code distance)
- AEAD verification checks $\mathrm{AEAD\_verify}_K(\hat{c}, AD)$.
- This predicate is **deterministic** and **unforgeable** (by Poly1305 security).
- No combination of ECC output can produce acceptance without a valid MAC.
- QED.

---

## References

- Goldreich, O. (2001). *Foundations of Cryptography*.
- Forney, G. D. (1966). *Concatenated Codes*.
- Shannon, C. E. (1948). *A Mathematical Theory of Communication*.

---

For more details on integration with the test harness, see [README.md](README.md).
