# Capability Destruction Layer

**Cryptographic revocation without regulatory framing.**

## Overview

This module implements **irreversible capability destruction** for GeoPhase. This is NOT GDPR erasure or compliance-driven data deletion. This is pure cryptographic capability loss enforced through secure key destruction and immutable ledger recording.

### What This IS

✅ **Cryptographic destruction** - Key material is securely overwritten and removed  
✅ **Immutable ledger** - "Something was destroyed" without storing personal data  
✅ **Fail-closed enforcement** - Once destroyed → cannot be re-enabled  
✅ **Proof generation** - Cryptographic evidence without disclosure  
✅ **410 Gone semantics** - Asset permanently unavailable  

### What This is NOT

❌ **GDPR/CPRA compliance layer** (stays in DNA Vault)  
❌ **Legal "Right to Erasure"** (no regulatory framing)  
❌ **Identity tracking** (no subject IDs, no user data)  
❌ **Audit reports** (no human-readable legal documents)  
❌ **Reversible** (destruction is permanent)  

## Architecture

```
┌─────────────────────┐
│  Capability Token   │  (EIP-712 PolicyGrant)
│  commit: 0x...      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Gate Check         │  FastAPI dependency
│  - is_destroyed()?  │────► Ledger (immutable)
└──────────┬──────────┘
           │
           ├─ Not destroyed ──► Allow (200)
           └─ Destroyed ──────► Deny (410 Gone)

Destruction Flow:
┌─────────────────────┐
│ DestructionManager  │
│ - shred_key()       │  3x random + 1x zeros
│ - delete_payload()  │  Multi-pass overwrite
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ CapabilityDestruction│
│ Event.create()      │  Proof hash generation
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Ledger.add_event()  │  Append-only .jsonl
│ IRREVERSIBLE        │
└─────────────────────┘
```

## Components

### 1. CapabilityDestructionEvent

Immutable ledger record indicating permanent capability loss.

```python
from geophase.ledger import CapabilityDestructionEvent, DestructionMethod

event = CapabilityDestructionEvent.create(
    asset_id="0x1234...",  # NOT user identity
    method=DestructionMethod.KEY_SHRED,
    material_hash="0xabcd...",  # SHA256 of destroyed material
    pre_state_commitment="0xef01...",  # Hash of state before destruction
)

# Verify proof
assert event.verify_proof(material_hash)
assert event.is_irreversible()
```

**CRITICAL BOUNDARY:**
- `asset_id` is a **capability identifier** (commit hash), NOT user identity
- No PII, no biometric data, no resemblance targets
- Pure cryptographic fact: "this capability is gone"

### 2. DestructionManager

Secure deletion of cryptographic material.

```python
from geophase.storage import DestructionManager

manager = DestructionManager("/path/to/storage")

# Destroy key only (renders capability unusable)
key_hash = manager.shred_key(asset_id="0x1234...")

# Destroy payload only (data remains encrypted but inaccessible)
payload_hash = manager.delete_payload(asset_id="0x1234...")

# Full destruction (key + payload)
result = manager.destroy_capability(
    asset_id="0x1234...",
    shred_key=True,
    delete_payload=True,
)

print(result.material_hash)  # Combined proof hash
```

**Destruction Method:**
1. Read original material
2. Generate SHA256 hash (proof)
3. Overwrite 3× with random data
4. Overwrite 1× with zeros
5. Delete file

### 3. Ledger

Append-only event storage.

```python
from geophase.ledger import Ledger

ledger = Ledger("/path/to/ledger.jsonl")

# Add destruction event
ledger.add_event(event)

# Check if destroyed
if ledger.is_destroyed(asset_id):
    raise HTTPException(410, "Asset permanently destroyed")

# Get proof
proof = ledger.get_destruction_proof(asset_id)
```

**Properties:**
- Append-only (no updates, no deletes)
- JSON Lines format (.jsonl)
- Human-readable for audit
- Fast lookup by asset_id

### 4. Gate Integration

Enforce destruction in FastAPI gates.

```python
from geophase.eth.fastapi_gate import build_gate_dependency, GateConfig
from geophase.ledger import Ledger

ledger = Ledger("/path/to/ledger.jsonl")

gate = build_gate_dependency(
    verifier=verifier,
    chain=chain_client,
    cfg=GateConfig(check_destruction=True),
    required_rights=int(Rights.FRAME),
    ledger=ledger,  # Enable destruction checks
)

@app.post("/generate")
def generate(grant: VerifiedGrant = Depends(gate)):
    # Only reaches here if:
    # - signature valid
    # - not expired
    # - not revoked on-chain
    # - NOT DESTROYED (410)
    return {"ok": True}
```

**HTTP Status Codes:**
- `200 OK` - Capability valid
- `403 Forbidden` - Invalid signature / insufficient rights
- `410 Gone` - **Capability permanently destroyed** (new!)
- `503 Service Unavailable` - Chain check failed (fail-closed)

## Complete Workflow Example

```python
from pathlib import Path
from geophase.storage import DestructionManager
from geophase.ledger import CapabilityDestructionEvent, DestructionMethod, Ledger

# Setup
storage_dir = Path("/data/storage")
ledger_path = Path("/data/ledger.jsonl")

manager = DestructionManager(storage_dir)
ledger = Ledger(ledger_path)

asset_id = "0x" + "12" * 32  # Commit hash (NOT user ID)

# 1. Get current state commitment (before destruction)
pre_state = compute_state_commitment()  # Your implementation

# 2. Destroy capability
result = manager.destroy_capability(asset_id)

# 3. Create destruction event with proof
event = CapabilityDestructionEvent.create(
    asset_id=asset_id,
    method=DestructionMethod.FULL_PURGE,
    material_hash=result.material_hash,
    pre_state_commitment=pre_state,
    metadata={"reason": "user_request", "timestamp_ms": 1234567890},
)

# 4. Record in ledger (IRREVERSIBLE)
ledger.add_event(event)

# 5. Verify destruction
assert manager.verify_destroyed(asset_id)
assert ledger.is_destroyed(asset_id)

# 6. Future requests will fail with 410 Gone
# (enforced by gate dependency)
```

## Destruction Methods

```python
from geophase.ledger import DestructionMethod

DestructionMethod.KEY_SHRED       # Key material destroyed (primary)
DestructionMethod.STORAGE_DELETE  # Storage physically overwritten
DestructionMethod.FULL_PURGE      # Complete removal (key + storage)
```

**Recommendation:** Use `KEY_SHRED` for capability revocation. Once the key is gone, the data is cryptographically inaccessible even if storage persists.

## Security Properties

### 1. Fail-Closed

```python
# Gate checks destruction BEFORE other operations
if ledger.is_destroyed(asset_id):
    return 410  # Gone forever

# If ledger is unavailable:
try:
    destroyed = ledger.is_destroyed(asset_id)
except Exception:
    # Advisory check - continue to other checks
    # (destruction check is NOT fail-closed by default)
    pass
```

**Rationale:** Destruction is a local operation (not on-chain), so we don't want a ledger read failure to block all operations. Chain revocation is the fail-closed mechanism.

### 2. Cryptographic Proof

```python
# Proof hash = SHA256("DESTROY:asset_id:material_hash")
proof = hashlib.sha256(
    f"DESTROY:{asset_id}:{material_hash}".encode()
).hexdigest()

# Verifiable without revealing material
event.verify_proof(material_hash)  # True
```

### 3. Immutability

- Ledger is append-only (.jsonl format)
- Events cannot be modified after recording
- Deletion would break audit trail
- Destruction is permanent

### 4. No Identity Leakage

```python
# ✅ CORRECT: Asset-based
event = CapabilityDestructionEvent.create(
    asset_id="0x" + commit_hash,  # Cryptographic identifier
    method=DestructionMethod.KEY_SHRED,
    material_hash=key_hash,
    pre_state_commitment=state_hash,
)

# ❌ WRONG: User-based (do not do this!)
event = CapabilityDestructionEvent.create(
    asset_id=f"user-{user_id}",  # NO! This leaks identity
    method=DestructionMethod.KEY_SHRED,
    material_hash=key_hash,
    pre_state_commitment=state_hash,
)
```

## Testing

```bash
# Run all destruction tests
pytest tests/test_destruction.py -v

# 18 tests covering:
# - Event creation and validation
# - Secure key shredding
# - Payload deletion  
# - Ledger append-only behavior
# - Query interface
# - Full workflow integration
```

## File Structure

```
src/geophase/
├── ledger/
│   ├── __init__.py
│   ├── destruction_event.py  # CapabilityDestructionEvent model
│   └── ledger.py              # Immutable event ledger
├── storage/
│   ├── __init__.py
│   └── destruction.py         # DestructionManager (secure deletion)
└── eth/
    └── fastapi_gate.py        # Updated with destruction check

tests/
└── test_destruction.py        # 18 comprehensive tests
```

## Production Checklist

- [ ] Set up ledger storage (persistent volume)
- [ ] Configure ledger path in environment
- [ ] Enable `check_destruction=True` in gate config
- [ ] Test 410 Gone responses
- [ ] Monitor destruction event rate
- [ ] Set up ledger backup/replication
- [ ] Document destruction request flow
- [ ] Train support on 410 vs 403 vs 503

## Monitoring

```python
from prometheus_client import Counter

destruction_events = Counter(
    'destruction_events_total',
    'Total capability destruction events',
    ['method']
)

# When destroying:
result = manager.destroy_capability(asset_id)
event = CapabilityDestructionEvent.create(...)
ledger.add_event(event)

destruction_events.labels(method=event.method).inc()
```

**Metrics to track:**
- `destruction_events_total` by method
- `gate_410_responses_total` (assets hit after destruction)
- `ledger_size_bytes` (growth over time)
- `ledger_event_count`

## Differences from DNA Vault

| DNA Vault | GeoPhase |
|-----------|----------|
| "Right to Erasure" | "Capability Destruction" |
| Data Subject | ❌ (not present) |
| Legal basis | ❌ |
| Compliance report | ❌ |
| GDPR/CPRA language | ❌ |
| Regulator ID | ❌ |
| Audit trail with PII | Audit trail WITHOUT identity |
| Reversible (legal holds) | Irreversible (cryptographic) |

**GeoPhase is protocol-grade. DNA Vault is compliance-grade.**

## FAQs

### Q: Can destruction be reversed?

**No.** Once `ledger.add_event(destruction_event)` completes, the capability is permanently lost. There is no "undo" mechanism.

### Q: What if I need to recover a destroyed capability?

**You can't.** That's the point. Destruction is irreversible. If you need recoverability, use on-chain revocation instead (which can be un-revoked by contract owner).

### Q: Do I need to destroy both key and payload?

**No.** Destroying the key is sufficient to render the capability unusable. The encrypted payload is cryptographically inaccessible without the key.

### Q: Is this GDPR compliant?

**This is not a GDPR layer.** GeoPhase does not store user identities, so GDPR does not apply. If you need GDPR compliance, see DNA Vault.

### Q: What's the difference between revocation and destruction?

- **Revocation** (on-chain): Temporary denial, can be reversed by contract owner
- **Destruction** (local ledger): Permanent cryptographic loss, cannot be reversed

Use revocation for policy violations. Use destruction for permanent capability retirement.

### Q: Can I use the same ledger for multiple assets?

**Yes.** The ledger is asset-agnostic. All destruction events go into the same append-only log. Use `ledger.query().by_asset(asset_id)` to filter.

## Next Steps

1. ✅ **Integrate with your API** - Add `ledger` parameter to gate
2. ✅ **Test 410 responses** - Verify destruction enforcement
3. ✅ **Set up monitoring** - Track destruction event rate
4. ✅ **Document for users** - Explain 410 Gone responses
5. ✅ **Production deployment** - Enable in staging first

---

## License

See [LICENSE](../../../LICENSE) file.

## Ethics Compliance

✅ **No identity capture** - asset IDs only, no user tracking  
✅ **Fail-closed enforcement** - destroyed capabilities cannot be used  
✅ **Immutable audit trail** - cryptographic proof without disclosure  
✅ **Irreversible** - once destroyed, cannot be restored  

**This is cryptographic capability revocation, not regulatory erasure.**
