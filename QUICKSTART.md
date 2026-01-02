# Quick Start

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run Tests

### Black-Box Test Harness (T1–T3)
```bash
python scripts/public_test.py \
  --encode scripts/encode_blackbox.py \
  --verify scripts/verify_blackbox.py \
  --verify-wrong scripts/verify_blackbox_wrongkey.py \
  --blocks 50 --msg-bytes 256
```

**Expected output:** T1, T2, T3 = **PASS** ✓

### With Noise Levels (T4)
```bash
python scripts/public_test.py \
  --encode scripts/encode_blackbox.py \
  --verify scripts/verify_blackbox.py \
  --verify-wrong scripts/verify_blackbox_wrongkey.py \
  --blocks 10 --msg-bytes 32 --noise-levels 0,1,2,4,8
```

**Expected output:** T1–T3 = **PASS** ✓, T4 = **FAIL** (expected—no real ECC)

### Smoke Tests
```bash
PYTHONPATH=src python -m pytest tests/ -v
```

**Expected output:** 11 tests = **PASS** ✓

## Test Results

| Test | Status | Notes |
|------|--------|-------|
| **T1** (Determinism) | ✓ PASS | Encode same input → identical output |
| **T2** (Correctness) | ✓ PASS | Verify correct key → ACCEPT + recover message |
| **T3** (Rejection) | ✓ PASS | Verify wrong key → REJECT |
| **T4** (Noise) | ✗ FAIL | Requires real ECC in carrier (placeholder only) |

## Next Steps

To make T4 pass, implement:

1. **Real ECC** (Reed-Solomon or similar) in `src/geophase/codec.py`
2. **AEAD** (AES-GCM or ChaCha20-Poly1305)
3. **Interleaver** for burst-noise robustness
4. Update `scripts/encode_blackbox.py` and `scripts/verify_blackbox.py` to use real codec

See [README.md](README.md) for architecture details.
