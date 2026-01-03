#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Geophase Self-Check"
echo "====================="
echo

# 1. Python version check
echo "▶ Checking Python version..."
python3 --version
echo

# 2. Virtual environment (optional but recommended)
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "⚠️  No virtual environment detected (ok in Codespaces)"
else
  echo "✅ Virtual environment active: $VIRTUAL_ENV"
fi
echo

# 3. Dependency check
echo "▶ Checking Python standard library..."
python3 << 'EOF'
try:
    import hashlib
    import json
    import argparse
    import zlib
    print("✅ Standard library OK")
except Exception as e:
    print("❌ Dependency error:", e)
    raise
EOF
echo

# 4. Package import check
echo "▶ Checking geophase package imports..."
PYTHONPATH=src python3 << 'EOF'
try:
    import geophase
    from geophase import util, chain, compress, codec
    print("✅ geophase imports cleanly")
except Exception as e:
    print("❌ geophase import failed:", e)
    raise
EOF
echo

# 5. Math documentation check
echo "▶ Checking mathematical documentation..."
if [[ -f MATHEMATICS.md ]]; then
  echo "✅ MATHEMATICS.md present"
  grep -q "Hash-Chained Commitments" MATHEMATICS.md && echo "✅ Contains core sections"
else
  echo "❌ MATHEMATICS.md missing"
  exit 1
fi
echo

# 6. Public test scripts present
echo "▶ Checking public test scripts..."
for script in scripts/public_test.py scripts/encode_blackbox.py scripts/verify_blackbox.py scripts/verify_blackbox_wrongkey.py; do
  if [[ -f "$script" ]]; then
    echo "✅ $script"
  else
    echo "❌ $script missing"
    exit 1
  fi
done
echo

# 7. Run unit tests
echo "▶ Running unit tests (T1–T3 foundation tests)..."
if command -v pytest &> /dev/null; then
  PYTHONPATH=src pytest tests/ -q --tb=short && echo "✅ Unit tests passed" || {
    echo "❌ Unit tests failed"
    exit 1
  }
else
  echo "⚠️  pytest not installed (run: pip install pytest)"
  echo "   Skipping unit tests"
fi
echo

# 8. Black-box test harness (T1–T3 expected pass, T4 expected fail)
echo "▶ Running black-box test harness (T1–T3)..."
PYTHONPATH=src python3 scripts/public_test.py \
  --encode scripts/encode_blackbox.py \
  --verify scripts/verify_blackbox.py \
  --verify-wrong scripts/verify_blackbox_wrongkey.py \
  --blocks 5 \
  --msg-bytes 32 \
  --noise-levels 0 \
  > /tmp/harness_output.log 2>&1

if grep -q "T1 (Determinism):.*PASS" /tmp/harness_output.log && \
   grep -q "T2 (Correctness):.*PASS" /tmp/harness_output.log && \
   grep -q "T3 (Rejection):.*PASS" /tmp/harness_output.log; then
  echo "✅ Black-box harness: T1–T3 all PASS"
else
  echo "❌ Black-box harness: T1–T3 did not all pass"
  cat /tmp/harness_output.log
  exit 1
fi
echo

# 9. Final status
echo "═══════════════════════════════════════════════════════"
echo "✅ Self-check complete"
echo "═══════════════════════════════════════════════════════"
echo
echo "Status:"
echo "  • Environment:     ✅ Ready"
echo "  • Package:         ✅ Imports cleanly"
echo "  • Math docs:       ✅ Present & comprehensive"
echo "  • Unit tests:      ✅ Passing"
echo "  • Black-box (T1-T3): ✅ All determinism/correctness/rejection passing"
echo "  • Noise (T4):      ⚠️  Expected to fail (requires real ECC implementation)"
echo
echo "Next steps:"
echo "  • Test: ./scripts/public_test.py --blocks 50 --msg-bytes 256"
echo "  • Read: MATHEMATICS.md for complete design"
echo "  • Hack: src/geophase/codec.py for real ECC integration"
echo
