# Security Policy

This repo is intended for **public verification** and **black-box testing**.
It intentionally does not include private carrier schedules, keys, or deployment parameters.

## Reporting

If you believe you have found an issue that causes:
- false ACCEPT,
- integrity bypass,
- key misuse,
- nonce reuse vulnerabilities,

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
