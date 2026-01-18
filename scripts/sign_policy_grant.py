"""
Example client-side signing script for PolicyGrant.

This demonstrates how to:
- Create a PolicyGrant capability token
- Sign it with EIP-712 using a wallet private key
- Format headers for API requests
- Make authenticated requests to the API
"""

import os
import time
import json
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak

from geophase.eth.policy_grant import PolicyGrant, Rights, Mode
from geophase.eth.eip712_policy_grant import PolicyGrantVerifier


def keccak_bytes32(s: str) -> str:
    """Helper to create keccak256 hash as 0x-prefixed hex."""
    return "0x" + keccak(text=s).hex()


def create_and_sign_grant(
    private_key: str,
    commit: str,
    policy_name: str,
    rights: int = int(Rights.FRAME),
    mode: int = int(Mode.STANDARD),
    validity_seconds: int = 3600,
) -> tuple[PolicyGrant, str, str]:
    """
    Create and sign a PolicyGrant.

    Args:
        private_key: 0x-prefixed private key hex string
        commit: 0x-prefixed bytes32 hex of geo_commit
        policy_name: Human-readable policy name (will be hashed)
        rights: Rights bitmask (default: FRAME)
        mode: Generation mode (default: STANDARD)
        validity_seconds: How long the grant is valid (default: 1 hour)

    Returns:
        Tuple of (grant, signature_hex, signer_address)
    """
    # Create account from private key
    acct = Account.from_key(private_key)
    
    # Create grant
    grant = PolicyGrant(
        commit=commit,
        policy_id=keccak_bytes32(policy_name),
        mode=mode,
        rights=rights,
        exp=int(time.time()) + validity_seconds,
        nonce="0x" + os.urandom(32).hex(),  # random nonce for replay protection
        engine_version=1,
    )
    
    # Create verifier (must match server configuration)
    verifier = PolicyGrantVerifier(
        name="GeoPhase",
        version="0.1.1",
        chain_id=8453,  # Base mainnet
        verifying_contract="0x0000000000000000000000000000000000000000",  # REPLACE
    )
    
    # Sign
    typed = verifier.typed_data(grant)
    msg = encode_typed_data(full_message=typed)
    signed = acct.sign_message(msg)
    
    return grant, signed.signature.hex(), acct.address


def format_headers(grant: PolicyGrant, signature: str, signer: str) -> dict:
    """
    Format headers for API request.

    Args:
        grant: PolicyGrant instance
        signature: Signature hex string
        signer: Signer address

    Returns:
        Dictionary of headers for HTTP request
    """
    return {
        "X-Policy-Grant": grant.model_dump_json(),
        "X-Policy-Signature": signature,
        "X-Policy-Signer": signer,
        "Content-Type": "application/json",
    }


def main():
    """Example usage."""
    
    # EXAMPLE 1: Sign a grant for frame generation
    print("=" * 60)
    print("EXAMPLE 1: Frame Generation Grant")
    print("=" * 60)
    
    # In production, load from secure key management
    private_key = os.environ.get("SIGNER_PRIVATE_KEY", "0x" + "11" * 32)
    
    # Example commit hash (in production, this comes from your GeoPhase workflow)
    commit = "0x" + "22" * 32
    
    grant, sig, addr = create_and_sign_grant(
        private_key=private_key,
        commit=commit,
        policy_name="ANANKE_POLICY_V1_STANDARD",
        rights=int(Rights.FRAME),
        mode=int(Mode.STANDARD),
        validity_seconds=3600,
    )
    
    headers = format_headers(grant, sig, addr)
    
    print(f"Signer Address: {addr}")
    print(f"Grant Expiry: {grant.exp} ({time.ctime(grant.exp)})")
    print(f"\nHeaders for API request:")
    print(json.dumps(headers, indent=2))
    print(f"\nCurl example:")
    print(f"""
curl -X POST http://localhost:8000/v1/generate \\
  -H "X-Policy-Grant: {headers['X-Policy-Grant']}" \\
  -H "X-Policy-Signature: {headers['X-Policy-Signature']}" \\
  -H "X-Policy-Signer: {headers['X-Policy-Signer']}"
""")
    
    # EXAMPLE 2: Sign a grant for video generation
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Video Generation Grant")
    print("=" * 60)
    
    grant2, sig2, addr2 = create_and_sign_grant(
        private_key=private_key,
        commit=commit,
        policy_name="ANANKE_POLICY_V1_STANDARD",
        rights=int(Rights.VIDEO),  # VIDEO rights
        mode=int(Mode.STANDARD),
        validity_seconds=7200,  # 2 hours
    )
    
    headers2 = format_headers(grant2, sig2, addr2)
    
    print(f"Signer Address: {addr2}")
    print(f"Grant Expiry: {grant2.exp} ({time.ctime(grant2.exp)})")
    print(f"\nCurl example:")
    print(f"""
curl -X POST http://localhost:8000/v1/generate/video \\
  -H "X-Policy-Grant: {headers2['X-Policy-Grant']}" \\
  -H "X-Policy-Signature: {headers2['X-Policy-Signature']}" \\
  -H "X-Policy-Signer: {headers2['X-Policy-Signer']}"
""")
    
    # EXAMPLE 3: Combined rights
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Combined Rights (FRAME + VIDEO)")
    print("=" * 60)
    
    combined_rights = int(Rights.FRAME) | int(Rights.VIDEO)
    grant3, sig3, addr3 = create_and_sign_grant(
        private_key=private_key,
        commit=commit,
        policy_name="ANANKE_POLICY_V1_STANDARD",
        rights=combined_rights,
        mode=int(Mode.STANDARD),
        validity_seconds=3600,
    )
    
    print(f"Rights bitmask: {combined_rights} (FRAME | VIDEO)")
    print(f"This grant can be used for both /v1/generate and /v1/generate/video")
    
    # EXAMPLE 4: Using requests library (if available)
    try:
        import requests
        
        print("\n" + "=" * 60)
        print("EXAMPLE 4: Making actual API request")
        print("=" * 60)
        
        # Check if API is running
        try:
            health = requests.get("http://localhost:8000/health", timeout=2)
            if health.status_code == 200:
                print("API is running!")
                
                # Make authenticated request
                response = requests.post(
                    "http://localhost:8000/v1/generate",
                    headers=headers,
                    timeout=5
                )
                
                print(f"\nResponse status: {response.status_code}")
                print(f"Response body: {response.json()}")
            else:
                print("API not running at http://localhost:8000")
        except requests.exceptions.ConnectionError:
            print("API not running. Start with: uvicorn geophase.eth.example_api:app")
            
    except ImportError:
        print("\n(Install 'requests' to test actual API calls)")


if __name__ == "__main__":
    main()
