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

## 9. Enhanced Hybrid Chaotic State Mixer (v2)

### Overview

The mixer implements a **non-autonomous, nonlinear modular map with entropy-gated nonlocal transitions**. It serves as a structured, unpredictable state transition function designed to:

- Maintain bounded chaos (mod $n$ confinement)
- Escape phase traps via randomized teleportation
- Preserve auditability and reproducibility
- Resist statistical bias without external randomness

### Formal Definition

Let $k_t \in \mathbb{Z}_n$ be the scalar state at step $t$.

The transition is:
$$k_{t+1} = \begin{cases}
(k_t + \Delta_{\text{local}}(k_t, t) + c) \bmod n & \text{if } b_t = 0 \\
\text{teleport\_share}(k_t, s_t, \mathcal{G}) \bmod n & \text{if } b_t = 1
\end{cases}$$

where:

- **Local drift:**
$$\Delta_{\text{local}}(k_t, t) := \Delta_j + \Delta_b + \Delta_{j4}$$

  - $\Delta_j := \alpha \cdot J(k_t) \cdot (1+z_r) \cdot \text{sign}(J(k_t))$ (primary nonlinear drift)
  - $\Delta_b := \alpha_2 \cdot J_b(k_t) \cdot (1+z_r)$ (secondary orthogonal drift)
  - $\Delta_{j4} := \gamma \cdot J(k_t)^3 \cdot (1+z_r)$ (cubic amplification)

- **Redshift modulation:**
$$z_r := \text{redshift}(r) \quad \text{(context-dependent scaling)}$$

- **Teleport selector:**
$$b_t := \begin{cases}
1 & \text{if } \text{ancilla}_{16}(t) / U16 < p_{\text{tp}}(k_t) \\
0 & \text{otherwise}
\end{cases}$$
where $U16 := 2^{16} = 65536$.

- **Teleport probability (entropy-gated):**
$$p_{\text{tp}}(k_t) := \min\left(\max(p_0 + \beta(1 - H(k_t)), p_{\min}), p_{\max}\right)$$

  where $H(k_t) \in [0,1]$ is a stateless entropy proxy based on bit balance:
  $$H(k_t) := 4 p (1-p), \quad p := \frac{\text{popcount}(k_t \bmod 2^{32})}{32}$$

### Key Properties

#### 1. **Boundedness**
Since all operations are congruent modulo $n$, divergence is strictly confined:
$$k_t \in [0, n) \quad \forall t$$

#### 2. **Local Chaos (Lyapunov Growth)**
The polynomial drift terms $\Delta_j + \Delta_{j4}$ induce:
- Nonlinear, state-dependent step sizes
- Local bit spread via XOR and mixing gates
- Positive Lyapunov exponent in local dynamics (locally)

However, modular confinement prevents unbounded explosion.

#### 3. **Nonlocal Escape (Teleportation)**
The selector bit $b_t$ enables occasional long-range jumps, guaranteeing:
- Escape from periodic cycles and resonance traps
- Global ergodicity (with probability 1 over infinite chains)
- No stationary distribution (system is non-autonomous)

#### 4. **Statestateless Routing**
Teleport selection depends only on:
- Current scalar $k_t$
- Deterministic ancilla $\text{ancilla}_{16}(t) := \text{SHA256}(\text{seed} \| t)[0:2]$
- No memory, no profiling, no learning

This makes the system **fully auditable and reproducible** when CSPRNG is disabled.

#### 5. **Entropy Adaptation (Without State)**
The entropy proxy $H(k_t)$ is derived deterministically from bit counts, not history. When local bits appear "too uniform" (high $H$), teleport probability *decreases*; when they appear "too biased" (low $H$), it *increases*. This provides **self-regulating diversity** without maintaining explicit state.

### Implementation Details

#### Deterministic Ancilla
$$\text{ancilla}_{16}(t) := \text{int.from\_bytes}(\text{SHA256}(\text{seed} \| t \| \text{"anc"})[0:2], \text{big})$$

This produces a 16-bit token reproducible for any $(t, \text{seed})$ pair.

#### Hybrid Mode (Optional CSPRNG)
To add cryptographic unpredictability while preserving reproducibility:
$$\text{ancilla}_{16}^{\text{hybrid}}(t) := \text{ancilla}_{16}(t) \oplus \text{os.urandom}(2)$$
(conditional on an explicit flag; default is deterministic mode)

#### Drift Functions
- **Primary:** $J(k) := \text{SHA256}(k)[0:8]$ (or curve-dependent parameter)
- **Secondary:** $J_b(k) := \text{mix64}(k \oplus \text{const})$ (orthogonal to $J$)

Both are stateless and deterministic.

### Why Not a PRNG?

The mixer is **not** suitable as a standalone pseudorandom number generator:

- No proven statistical uniformity over all output bits
- Output is correlated with input (intentionally)
- No backtracking resistance guarantees
- Designed for *state mixing*, not randomness generation

It is, however, suitable for:
- Nonlinear state transitions in iterative protocols
- Mixing scalars in scalar-based hash chains
- Preventing convergence in parametric searches
- Carrier mixing in teleport-based EC protocols

### Auditability and Security

#### No Learning
The transition function has **no adjustable parameters** (beyond fixed constants) and **no feedback mechanisms**. Each step is deterministic in isolation.

#### No Optimization Objective
There is no fitness function, loss term, or objective to optimize. The system does not converge to any goal state.

#### Reproducibility
For reproducible audits: set `use_real_rng=False`. The entire transition sequence is deterministic under seed and step index.

#### Irreversibility
For forward unpredictability: set `use_real_rng=True` to augment ancilla with OS CSPRNG. This maintains determinism in local drift but randomizes teleport routing.

### Complexity

Per step (scalar mod $n$):
- Limb decomposition (U16): ~16 operations
- Matrix multiply (U16): ~256 field operations
- Ancilla generation: 1 SHA256 hash
- Entropy proxy: ~32 bit operations
- Teleport decision: 1 comparison

**Total:** $O(1)$ per step, negligible in most contexts.

In ZK circuits (Halo2):
- Limb decomposition: ~16 rows (range checks)
- U16 mix: ~32 rows (field arithmetic)
- XOR lookup: ~1 row (lookup table)
- Recomposition: ~16 rows (field arithmetic)
- EC mul: ~800–1200 rows (dominant)
- **Per-step total:** ~900–1500 rows

For $m$ steps: $O(m \cdot 900)$ rows; e.g., $m=8 \Rightarrow 7200$ rows.

---

## References

- Goldreich, O. (2001). *Foundations of Cryptography*.
- Forney, G. D. (1966). *Concatenated Codes*.
- Shannon, C. E. (1948). *A Mathematical Theory of Communication*.
- Sprott, J. C. (2003). *Chaos and Time-Series Analysis*. (reference for chaotic maps)

---

## Appendix: Harmonic Interpretation (Scalar Waze)

An optional interpretive framework exploring harmonic ratios, discrete symmetry,
and curvature modulation is provided in:

- [docs/APPENDIX_SCALAR_WAZE_UNIFIED.md](docs/APPENDIX_SCALAR_WAZE_UNIFIED.md)

This appendix is **not normative** and does not participate in any security,
verification, or acceptance logic.

---

For more details on integration with the test harness, see [README.md](README.md).
