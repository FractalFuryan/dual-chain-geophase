# Ananke Smart Contracts

**Chain:** Base (L2)  
**Solidity:** 0.8.20  
**License:** MIT

---

## Contracts

### AnankeAttestationRegistry.sol

**Purpose:** Write-once provenance commitments for GeoPhase outputs.

**Key Features:**
- ✅ Stores only cryptographic hashes (no user data)
- ✅ Write-once semantics (cannot overwrite attestations)
- ✅ Minimal storage (5 fields per attestation)
- ✅ Gas-efficient (~100k per attestation)

**Storage:**
```solidity
struct Attestation {
    bytes32 ethicsAnchor;   // Ethics policy commitment
    bytes32 policyId;       // Policy identifier
    uint32 version;         // Protocol version
    address attestor;       // Who attested
    uint64 timestamp;       // When attested
}
```

**Functions:**
- `attest(geoCommit, ethicsAnchor, policyId, version)` - Write attestation
- `attestations(geoCommit)` - Read attestation (view)

### AnankeRevocationRegistry.sol

**Purpose:** User-controlled opt-out mechanism.

**Key Features:**
- ✅ Simple revocation bit (no metadata)
- ✅ Anyone can revoke (permissionless)
- ✅ Immutable once revoked (no un-revoke)
- ✅ Gas-efficient (~50k per revocation)

**Storage:**
```solidity
mapping(bytes32 => bool) public revoked;
```

**Functions:**
- `revoke(key)` - Set revocation bit
- `isRevoked(key)` - Check revocation status (view)

---

## Security Properties

### Privacy
- ❌ No user data stored
- ❌ No media stored
- ❌ No biometric data
- ✅ Only cryptographic hashes

### Integrity
- ✅ Write-once (no overwrites)
- ✅ Immutable revocations
- ✅ Public verifiability

### Availability
- ✅ No admin keys (permissionless)
- ✅ No upgradability (simple, auditable)
- ✅ L2 gas efficiency

---

## Gas Costs (Base L2)

| Operation | Gas | Cost (~$0.01/gas) |
|-----------|-----|-------------------|
| Deploy Attestation | ~500k | ~$0.50 |
| Deploy Revocation | ~250k | ~$0.25 |
| `attest()` | ~100k | ~$0.10 |
| `revoke()` | ~50k | ~$0.05 |
| `isRevoked()` (view) | 0 | Free |

---

## Deployment

See [../docs/eth/DEPLOYMENT.md](../docs/eth/DEPLOYMENT.md)

**Quick deploy:**
```bash
./deploy.sh
```

**Manual deploy:**
```bash
forge script script/Deploy.s.sol:DeployScript \
    --rpc-url $BASE_RPC_URL \
    --broadcast \
    --verify
```

---

## Testing

### Local Tests (Foundry)
```bash
forge test
```

### Gas Reports
```bash
forge test --gas-report
```

### Coverage
```bash
forge coverage
```

---

## Verification

Contracts are automatically verified on deployment if:
- `BASESCAN_API_KEY` is set
- `--verify` flag is used

**Manual verification:**
```bash
forge verify-contract \
    --chain-id 8453 \
    --compiler-version v0.8.20 \
    <CONTRACT_ADDRESS> \
    contracts/AnankeAttestationRegistry.sol:AnankeAttestationRegistry \
    --etherscan-api-key $BASESCAN_API_KEY
```

---

## Design Rationale

### Why Write-Once?
- Simpler (no update logic)
- Safer (no overwrites)
- Auditable (immutable history)

### Why No Upgradability?
- Attack surface reduction
- Trust minimization
- Gas efficiency

### Why Permissionless Revocation?
- User sovereignty
- No centralized control
- Privacy-preserving

---

## Integration

See [../src/geophase/eth/chain_check.py](../src/geophase/eth/chain_check.py)

**Python example:**
```python
from geophase.eth import ChainClient, load_config_from_env

client = ChainClient(load_config_from_env())

# Check revocation
if client.is_revoked(geo_commit):
    raise Exception("Revoked")

# Attest
tx_hash = client.attest(
    geo_commit,
    ethics_anchor,
    policy_id,
    version=1
)
```

---

## Audit Status

**v0.1:** Not yet audited (use at own risk)

**Recommended audits:**
- [ ] Formal verification (Certora, Halmos)
- [ ] Manual review (Trail of Bits, OpenZeppelin)
- [ ] Gas optimization (0xmacro)

---

## License

MIT License - see [../LICENSE](../LICENSE)

---

## References

- [Base Network](https://base.org)
- [Foundry Book](https://book.getfoundry.sh/)
- [Solidity Docs](https://docs.soliditylang.org/)
- [OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts/)
