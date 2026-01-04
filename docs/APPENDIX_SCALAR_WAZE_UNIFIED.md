# Appendix: Scalar-Waze Unified Framework (Public-Safe)

This appendix unifies three layers used throughout Dual-Chain GeoPhase:

1) **Math layer**: canonical synchronization / similarity primitives (no new cryptography)
2) **Discrete-symmetry layer**: clean invariants for "Structure ⟂ Secrecy"
3) **Harmonic analogy layer** (optional): intuition aid only, not a security claim

The intent is to give reviewers one place to verify that all abstractions reduce to standard, conservative components.

---

## A1. Objects & Notation

Let:
- Messages: $m \in \{0,1\}^*$
- Ciphertexts / payloads: $c$
- Keys: $k$
- Commitments / chain nodes: $h_t$
- Channel noise operator: $\mathcal{N}(\cdot)$
- Features (structure signals): $M_i \in \mathbb{R}^d$

We separate two domains:

- **Secrecy domain**: AEAD + key material  
- **Structure domain**: commitments, block ordering, channel/noise evidence, optional public metrics

Core axiom:

$$\boxed{\text{Secrecy} \perp \text{Structure}}$$

Meaning: structural artifacts must not leak key-dependent information, and correctness must not depend on hidden geometry.

---

## A2. Dual-Chain Separation (Core Invariant)

### A2.1 Commitment chain (public, tamper-evident)

A minimal hash chain:

$$h_0 = H(\texttt{domain} \parallel \texttt{genesis})$$

$$h_{t+1} = H(h_t \parallel \texttt{meta}_t \parallel \texttt{commit}(c_t))$$

Where:
- $H$ is a standard hash (e.g., SHA-256)
- $\texttt{meta}_t$ contains ordering and non-secret metadata
- $\texttt{commit}(c_t)$ is a commitment to ciphertext (or to a public tag of it), not to plaintext

This gives **append-only ordering** and **tamper evidence** without inventing a blockchain.

### A2.2 Secrecy chain (private, authenticated)

Use standard AEAD:

$$c \leftarrow \textsf{AEAD.Enc}(k, \textsf{nonce}, m, \textsf{aad})$$

$$m \leftarrow \textsf{AEAD.Dec}(k, \textsf{nonce}, c, \textsf{aad})$$

Acceptance gate:

$$\boxed{\text{ACCEPT} \iff \textsf{AEAD.Dec} \neq \bot}$$

No ECC result, no transport "success," and no geometry signal is allowed to override this.

---

## A3. Noise / Transport Layer (Robustness, Not Trust)

Define a channel noise operator $\mathcal{N}$ acting on the transmitted payload:

$$c' = \mathcal{N}(c)$$

Optional ECC encoder/decoder:

$$x = \textsf{ECC.Enc}(c),\quad x'=\mathcal{N}(x),\quad \hat{c}=\textsf{ECC.Dec}(x')$$

The system remains correct if:

$$\textsf{AEAD.Dec}(k, \textsf{nonce}, \hat{c}, \textsf{aad}) \neq \bot$$

**Important:** ECC is a *transport hardener*, never the acceptance gate.

---

## A4. Determinism vs Randomness (Audit-Safe)

To support black-box reproducibility tests, public harnesses may use deterministic placeholders.

Rule:
- **Determinism** is acceptable only for tests and non-secret scaffolding.
- **Production secrecy** must use proper randomness / nonce discipline per AEAD requirements.

In docs and code, any deterministic mode must be clearly labeled as:
- test-only,
- not a security primitive,
- not relied upon for confidentiality.

---

## A5. Cosine Similarity (Structure / Recognition Gating)

Cosine similarity is used only as a **structure-domain metric** (e.g., gating optional behaviors, classifying inputs, or documenting "recognition" in non-security contexts).

Given feature vectors $M_i, M_j \in \mathbb{R}^d$:

$$\boxed{S_{ij}=\frac{\langle M_i,M_j\rangle}{\|M_i\|\|M_j\|} \in[-1,1]}$$

Two safe uses:

### A5.1 Hard threshold gate

$$g(S_{ij}) = \mathbf{1}[S_{ij}\ge S_{\text{crit}}]$$

### A5.2 Smooth gate (differentiable)

$$g(S_{ij})=\frac{1}{1+\exp(-\beta(S_{ij}-S_{\text{crit}}))}$$

**Security constraint:** cosine similarity must not depend on secrets, keys, or decrypted content.

---

## A6. Discrete Symmetry View (Reviewer-Friendly)

We define a discrete "separation symmetry":

- **S-domain operations** act on secrets (keys, AEAD internals)
- **P-domain operations** act on public structure (hash-chain order, noise evidence)

Allowed:
- $P \to P$
- $S \to S$
- $P \to S$ only through *input transport* (ciphertext delivered for decryption)
- $S \to P$ only through *minimal authenticated outputs* (ACCEPT/REJECT and optionally public tags)

Disallowed:
- any $S \to P$ leakage path where secrets influence public structure in a way that could be distinguishable

This is the cleanest statement of:

$$\boxed{\text{Secrecy} \perp \text{Structure}}$$

---

## A7. Harmonic / "Scalar-Waze" Analogy (Non-Security)

This section is intuition only.

Think of each block transmission as a "wave packet" moving through a channel:

- **Amplitude survival** = ECC/interleaving robustness
- **Phase correctness** = AEAD authentication / correctness
- **Coherence** = consistent chain ordering and replay resistance

Analogy mapping:

- Transport can preserve shape (ECC succeeds) while still being **wrong** (AEAD rejects).  
- Therefore trust is "phase-locked" only by AEAD, never by transport.

In one line:

$$\boxed{\text{Transport success} \not\Rightarrow \text{Authenticity}}$$

That is the GeoPhase covenant.

---

## A8. Implementation Notes (Public-Safe)

- If ECC is placeholder, document it clearly (e.g., "T4 expected fail")
- Keep acceptance gate exclusively AEAD
- Keep structure chain independent of key material
- Keep cosine similarity strictly in structure domain (no secret dependence)

End of appendix.
