# ECC Tuning Guide

## Reed–Solomon Over Bytes: Configuration & Measurement

This document explains how to tune Reed–Solomon (RS) error correction strength for different noise channels, and how to measure T4 (noise robustness) behavior.

---

## 1. NSYM (Redundancy Bytes) Tuning Matrix

| NSYM | Correctable Errors | Overhead | Storage Impact | Expected T4 Behavior |
|-----:|-------------------:|----------:|----------------:|:-----|
|  32  |       16 bytes     |   +32 B  |    1024 → 1056 | Pass low noise (≤8), mixed at 16, fail at 32+ |
|  **64**  |       **32 bytes**     |  **+64 B** |   **1024 → 1088** | **Baseline**: Pass ≤32, mixed at 48, fail at 64+ |
|  96  |       48 bytes     |   +96 B  |    1024 → 1120 | Pass most at 32–48, mixed at 64 |
|  128 |       64 bytes     |  +128 B  |    1024 → 1152 | Strong at 48+, diminishing returns |

### Key Principles

1. **Reed–Solomon can correct up to NSYM/2 symbol (byte) errors**
   - NSYM = 64 → corrects ≤32 byte errors
   - NSYM = 128 → corrects ≤64 byte errors

2. **Interleaving helps when noise is distributed** (not bursty)
   - Our deterministic permutation spreads errors across the codeword
   - Improves acceptance rate under white/random noise

3. **Authenticity is unchanged**
   - AEAD gate (Poly1305) always catches corruption
   - ECC only affects **acceptance rate under noise**, not security

4. **Overhead is linear in NSYM**
   - Small cost for strong robustness
   - NSYM=64 adds 6.25% to codeword size
   - NSYM=128 adds 12.5% (still reasonable for unreliable channels)

---

## 2. How to Measure T4 Behavior (Black-Box Harness)

### One-Shot Sweep Across NSYM Values

```bash
# Run T4 test suite with default NSYM=64
PYTHONPATH=src python -m pytest tests/test_ecc_blackbox.py::TestECCBlackBox::test_t4_noise_robustness -v -s

# Expect: ACCEPT for noise levels 0, 8, 16, 24, 32, 48, 64, 96
```

### Systematic Tuning Procedure

1. **Create a tuning script** (run once per NSYM value):

```bash
#!/bin/bash
# scripts/tune_ecc.sh

for NSYM in 32 64 96 128; do
  echo "Testing NSYM=$NSYM..."
  
  # Modify src/geophase/codec.py:
  # NSYM = $NSYM
  sed -i "s/NSYM = [0-9]*/NSYM = $NSYM/" src/geophase/codec.py
  
  # Run T4 test
  PYTHONPATH=src python -m pytest tests/test_ecc_blackbox.py::TestECCBlackBox::test_t4_noise_robustness \
    -v -s 2>&1 | tee "results/t4_nsym${NSYM}.txt"
  
  # Extract ACCEPT rate at each noise level
  grep "ACCEPT\|REJECT" "results/t4_nsym${NSYM}.txt" | sort | uniq -c
done

# Revert
sed -i "s/NSYM = [0-9]*/NSYM = 64/" src/geophase/codec.py
```

2. **Analyze results**:
   - Tabulate ACCEPT rate (%) vs noise level for each NSYM
   - Plot curves: x=noise_level, y=accept_rate%, with lines for each NSYM
   - Verify monotonic rightward shift (higher NSYM → better robustness)

### GitHub Actions Matrix (Automated)

Add to `.github/workflows/ci.yml`:

```yaml
strategy:
  matrix:
    nsym: [32, 64, 96, 128]
    
steps:
  - name: Tune ECC (NSYM=${{ matrix.nsym }})
    run: |
      sed -i "s/NSYM = [0-9]*/NSYM = ${{ matrix.nsym }}/" src/geophase/codec.py
      PYTHONPATH=src python -m pytest tests/test_ecc_blackbox.py::TestECCBlackBox::test_t4_noise_robustness -v
  
  - name: Upload T4 Results
    uses: actions/upload-artifact@v3
    with:
      name: t4-results-nsym${{ matrix.nsym }}
      path: results/
```

---

## 3. Production Recommended Tuning

### Conservative (Enterprise Channels, Bit Error Rate ~1e-3)
- **NSYM = 64**
- Assumes bursts ≤32 bytes with interleaving spreading
- Covers 99%+ of white noise conditions

### Aggressive (Lossy Channels, Bit Error Rate ~1e-2)
- **NSYM = 96 or 128**
- Necessary for FM, satellite, or severely degraded links
- Trade: +32–64 bytes overhead per codeword

### Ultra-Conservative (Mission-Critical, Any Channel)
- **NSYM = 128 + Larger Interleaver**
- Maximum safety margin
- Minimal performance cost for critical applications

---

## 4. Covenant Remains Invariant

**Whatever NSYM you choose, the security invariant is preserved:**

$$\text{ACCEPT} \Leftrightarrow \text{AEAD\_verify}(\text{ciphertext}, \text{AD}) = \text{true}$$

- AEAD (Poly1305) always authenticates
- ECC only helps recovery **before** AEAD check
- Increasing NSYM never weakens security
- Decreasing NSYM never skips AEAD verification

---

## 5. Testing & Validation

### CI Validation (Every Commit)
```bash
PYTHONPATH=src python -m pytest tests/ -q
```

Confirms:
- T1–T3 pass at baseline NSYM=64
- Covenant gate tests pass
- No regressions

### Pre-Deployment Validation (Before Release)
```bash
# Run T4 sweep across all recommended NSYM values
for NSYM in 32 64 96 128; do
  sed -i "s/NSYM = [0-9]*/NSYM = $NSYM/" src/geophase/codec.py
  PYTHONPATH=src python -m pytest tests/test_ecc_blackbox.py::TestECCBlackBox::test_t4_noise_robustness -q
done
git checkout src/geophase/codec.py  # Revert to baseline
```

---

## 6. Monitoring & Observability

### Metrics to Track in Production

1. **ACCEPT vs REJECT ratio** by block/channel
2. **Bit Error Rate (BER)** before/after ECC
3. **Decoding latency** (should be <1ms per block)
4. **AEAD verification success** (should be 100% for clean ACCEPT blocks)

### Log Format (Recommended)

```json
{
  "t": 12345,
  "noise_level": 18,
  "ecc_decode_status": "SUCCESS",
  "aead_verify_status": "ACCEPT",
  "latency_us": 850,
  "channel_bitmask": "0x..."
}
```

---

## 7. FAQ

**Q: Why can't we just increase NSYM to 256?**
A: RS(256) means 128 parity bytes = 12.5% overhead. Diminishing returns on top of NSYM=128, and latency becomes noticeable (RS is O(n²) in general form, though modern implementations are O(n log n)). NSYM=128 covers 99.9% of practical channels.

**Q: Does HKDF change the tuning?**
A: No. HKDF is only used in the KDF, not in ECC. ECC tuning is independent.

**Q: Can we interleave harder (e.g., 2D permutation)?**
A: Yes, and it helps. For now, we use 1D deterministic permutation. A 2D byte-matrix interleaver (like CCSDS) would improve burst handling further, but adds complexity.

**Q: What about Turbo codes or LDPC?**
A: Reed–Solomon is cleaner for our use case (small blocks, exact error correction). Turbo/LDPC are better for continuous streams. Consider for future versions if channels prove harder.

**Q: How do we know our interleaving helps?**
A: Measure T4 with/without permute(). We expect ~5–10% improvement under white noise.

---

## 8. Proof of Covenant Preservation

**Theorem:** Increasing NSYM preserves the covenant.

**Proof sketch:**
1. ECC only operates on ciphertext (before AEAD gate)
2. AEAD verification is independent of ECC output
3. ECC failure (garbage output) → AEAD MAC fails → REJECT
4. ECC success + AEAD success → ACCEPT (only valid route)
5. No acceptance path depends on NSYM choice ✓

---

## Summary

- **Default (baseline):** NSYM=64 (32-byte error correction)
- **Measurement:** T4 black-box harness (automated, reproducible)
- **Tuning:** Modify `src/geophase/codec.py`, re-run tests
- **Validation:** CI tests + ACCEPT rate curves
- **Covenant:** Invariant under all NSYM values

**Start at NSYM=64. Increase only if T4 shows unacceptable rejection under your noise profile.**
