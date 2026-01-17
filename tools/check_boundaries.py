#!/usr/bin/env python3
"""
Boundary Gate: CI gate to prevent bleed-through between math, interpretations, and engineering.

This script checks that boundary documents exist and contain required assertions about what
is and isn't claimed. Runs on every PR and push to main.
"""

from __future__ import annotations

import sys
from pathlib import Path

REQUIRED_FILES = [
    "docs/SCALAR_WAZE_BOUNDARY.md",
    "docs/NON_CLAIMS.md",
    "docs/CLAIMS_REGISTER.md",
]

# Phrases we require to exist (to prevent "bleed-through" and document drift)
REQUIRED_SNIPPETS = {
    "docs/SCALAR_WAZE_BOUNDARY.md": [
        "Mathematical Substrate Notice",
        "We do not modify, extend, or claim ownership",
        "Scalar Waze stops at",
        "Explicit Exclusions",
        "NOT a physical theory",
    ],
    "docs/NON_CLAIMS.md": [
        "This work does not claim",
        "proof or disproof of the Riemann Hypothesis",
        "physical realization of the zeta function",
    ],
    "docs/CLAIMS_REGISTER.md": [
        "Grounded (Mathematics)",
        "Interpretive / Constraint-Layer",
        "Engineering (GeoPhase / Cryptography)",
        "independent",  # Check for independence phrase
    ],
}


def fail(msg: str) -> int:
    """Print error and return failure code."""
    print(f"❌ boundary gate: {msg}")
    return 1


def main() -> int:
    """Check that boundary documents exist and contain required assertions."""
    repo = Path(__file__).resolve().parents[1]

    # Check all required files exist
    missing = [p for p in REQUIRED_FILES if not (repo / p).exists()]
    if missing:
        return fail(f"missing required boundary docs: {missing}")

    # Check each file contains required snippets
    for rel, snippets in REQUIRED_SNIPPETS.items():
        doc_path = repo / rel
        try:
            text = doc_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return fail(f"failed to read {rel!r}: {e}")

        for s in snippets:
            if s not in text:
                return fail(
                    f"missing required assertion in {rel!r}: {s!r}\n"
                    f"(boundary check prevents math/interpretation/engineering bleed-through)"
                )

    print("✅ boundary gate: OK")
    print("   - All boundary documents present")
    print("   - All required assertions found")
    print("   - Math/interpretation/engineering separation maintained")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
