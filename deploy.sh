#!/bin/bash
# Deploy Ananke contracts to Base mainnet

set -e

echo "🚀 Deploying Ananke contracts to Base..."

# Check env vars
if [ -z "$PRIVATE_KEY" ]; then
    echo "❌ PRIVATE_KEY not set in .env"
    exit 1
fi

if [ -z "$BASE_RPC_URL" ]; then
    echo "❌ BASE_RPC_URL not set in .env"
    exit 1
fi

# Load environment
source .env

# Deploy
forge script script/Deploy.s.sol:DeployScript \
    --rpc-url $BASE_RPC_URL \
    --broadcast \
    --verify \
    -vvvv

echo "✅ Deployment complete!"
echo "📋 Update your .env with the deployed addresses above"
