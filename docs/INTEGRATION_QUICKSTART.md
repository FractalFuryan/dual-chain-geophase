# PolicyGrant Integration Quick Start

**Get running in 5 minutes** ⚡

## 1. Install Dependencies

```bash
cd /workspaces/dual-chain-geophase
pip install -e .
```

Dependencies added to [requirements.txt](../requirements.txt):
- `fastapi>=0.109.0`
- `pydantic>=2.0.0`
- `web3>=6.15.0`
- `eth-account>=0.11.0`
- `eth-utils>=2.3.0`
- `uvicorn>=0.27.0`

## 2. Test the Implementation

```bash
# Run all tests (should see 12 passed)
pytest tests/test_policy_grant.py -v

# Test the signing script
python scripts/sign_policy_grant.py
```

## 3. Start Example API Server

```bash
# Terminal 1: Start server
uvicorn geophase.eth.example_api:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Check health
curl http://localhost:8000/health

# Check well-known endpoint
curl http://localhost:8000/.well-known/geophase-verifier.json
```

## 4. Make Authenticated Request

```bash
# Generate signed grant
python scripts/sign_policy_grant.py > /tmp/grant_output.txt

# Extract headers from output and test
# (Or use the curl commands printed by the script)
```

## 5. Replace Chain Client Stub

Edit [src/geophase/eth/example_api.py](../src/geophase/eth/example_api.py):

```python
# REPLACE THIS:
class ChainClientStub(ChainClientProtocol):
    def is_revoked(self, commit_hex: str) -> bool:
        return False  # stub

# WITH YOUR ACTUAL IMPLEMENTATION:
from web3 import Web3

class BaseChainClient(ChainClientProtocol):
    def __init__(self, rpc_url: str, registry_addr: str, registry_abi: list):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.registry = self.w3.eth.contract(
            address=registry_addr,
            abi=registry_abi
        )
    
    def is_revoked(self, commit_hex: str) -> bool:
        try:
            return self.registry.functions.isRevoked(commit_hex).call()
        except Exception as e:
            # Fail closed on chain errors
            raise Exception(f"Chain query failed: {e}")

# Update instantiation:
chain = BaseChainClient(
    rpc_url=os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
    registry_addr=os.getenv("REVOCATION_REGISTRY", "0x..."),
    registry_abi=REVOCATION_ABI,  # Load from JSON
)
```

## 6. Configure for Production

Create `.env` file:

```bash
# EIP-712 Domain
GEOPHASE_VERIFIER_NAME=GeoPhase
GEOPHASE_VERIFIER_VERSION=0.1.1
GEOPHASE_CHAIN_ID=8453  # Base mainnet (or 84532 for testnet)

# Contract Addresses (REPLACE WITH YOUR DEPLOYED CONTRACTS)
GEOPHASE_VERIFYING_CONTRACT=0x0000000000000000000000000000000000000000
GEOPHASE_ATTESTATION_REGISTRY=0x0000000000000000000000000000000000000000
GEOPHASE_REVOCATION_REGISTRY=0x0000000000000000000000000000000000000000

# Base L2 RPC
BASE_RPC_URL=https://mainnet.base.org

# Security
GEOPHASE_BYTECODE_LOCK_HASH=0x...
```

Load in your app:

```python
from dotenv import load_dotenv
load_dotenv()
```

## 7. Deploy to Base L2

### Revocation Registry Contract (Solidity)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract RevocationRegistry {
    mapping(bytes32 => bool) public isRevoked;
    address public owner;
    
    event Revoked(bytes32 indexed commit, uint256 timestamp);
    
    constructor() {
        owner = msg.sender;
    }
    
    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }
    
    function revoke(bytes32 commit) external onlyOwner {
        require(!isRevoked[commit], "already revoked");
        isRevoked[commit] = true;
        emit Revoked(commit, block.timestamp);
    }
    
    function batchRevoke(bytes32[] calldata commits) external onlyOwner {
        for (uint256 i = 0; i < commits.length; i++) {
            if (!isRevoked[commits[i]]) {
                isRevoked[commits[i]] = true;
                emit Revoked(commits[i], block.timestamp);
            }
        }
    }
}
```

Deploy:

```bash
# Using Foundry
forge create --rpc-url $BASE_RPC_URL \
    --private-key $DEPLOYER_KEY \
    --etherscan-api-key $BASESCAN_API_KEY \
    --verify \
    src/RevocationRegistry.sol:RevocationRegistry

# Or using Hardhat
npx hardhat run scripts/deploy.js --network base
```

## 8. Verify Deployment

```bash
# Check contract on BaseScan
open "https://basescan.org/address/$REVOCATION_REGISTRY"

# Verify bytecode hash matches
curl -s "https://api.basescan.org/api?module=contract&action=getabi&address=$REVOCATION_REGISTRY" \
    | jq -r '.result' \
    | sha256sum
```

## File Structure Reference

```
/workspaces/dual-chain-geophase/
│
├── src/geophase/eth/          # PolicyGrant implementation
│   ├── __init__.py            # Module exports
│   ├── policy_grant.py        # PolicyGrant model
│   ├── eip712_policy_grant.py # EIP-712 verifier
│   ├── well_known.py          # Discovery metadata
│   ├── fastapi_gate.py        # Fail-closed gate
│   ├── example_api.py         # Example FastAPI app
│   └── README.md              # Detailed docs
│
├── scripts/
│   └── sign_policy_grant.py   # Client signing example
│
├── tests/
│   └── test_policy_grant.py   # Comprehensive tests
│
└── docs/
    ├── EIP712_POLICY_GRANT.md # This architecture doc
    └── INTEGRATION_QUICKSTART.md  # This file
```

## Common Issues

### "Module not found: geophase.eth"

```bash
# Reinstall in editable mode
pip install -e .
```

### "Chain check failed"

- Verify `BASE_RPC_URL` is accessible
- Check `REVOCATION_REGISTRY` address is correct
- Ensure contract ABI matches deployed contract
- Test with `strict_chain=False` during development

### "Signature verification failed"

- Ensure `verifying_contract` matches between client and server
- Check `chain_id` is correct (8453 for Base mainnet)
- Verify EIP-712 domain `name` and `version` match
- Confirm grant hasn't expired

### "Invalid policy grant"

- Validate `commit` is 0x-prefixed 66-char hex
- Validate `policy_id` is 0x-prefixed 66-char hex
- Validate `nonce` is 0x-prefixed 66-char hex
- Check `mode` is 0 or 1
- Check `rights` is positive integer

## Monitoring

Add monitoring for:

```python
import logging
from prometheus_client import Counter, Histogram

# Metrics
grant_verifications = Counter('grant_verifications_total', 'Total grant verifications', ['status'])
grant_verification_duration = Histogram('grant_verification_duration_seconds', 'Time to verify grant')
chain_revocation_checks = Counter('chain_revocation_checks_total', 'Chain revocation checks', ['result'])

# In your gate:
with grant_verification_duration.time():
    try:
        verified = verifier.verify(grant, signature, signer)
        grant_verifications.labels(status='success').inc()
    except Exception as e:
        grant_verifications.labels(status='failed').inc()
        logging.error(f"Grant verification failed: {e}")
        raise
```

## Next Steps

Once running:

1. ✅ **Test on Base testnet** (chain_id=84532)
2. ✅ **Deploy contracts to mainnet**
3. ✅ **Update verifying_contract address**
4. ✅ **Generate bytecode lock hash**
5. ✅ **Document policy IDs**
6. ✅ **Set up monitoring**
7. ✅ **Enable HTTPS**
8. ✅ **Configure CORS**
9. ✅ **Audit by security firm**
10. ✅ **Launch** 🚀

## Support

- **Documentation**: [docs/EIP712_POLICY_GRANT.md](EIP712_POLICY_GRANT.md)
- **Module README**: [src/geophase/eth/README.md](../src/geophase/eth/README.md)
- **Tests**: [tests/test_policy_grant.py](../tests/test_policy_grant.py)
- **Example API**: [src/geophase/eth/example_api.py](../src/geophase/eth/example_api.py)
- **Example Client**: [scripts/sign_policy_grant.py](../scripts/sign_policy_grant.py)
