// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../contracts/AnankeAttestationRegistry.sol";
import "../contracts/AnankeRevocationRegistry.sol";

/// @notice Deploy Ananke contracts to Base
contract DeployScript is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        
        vm.startBroadcast(deployerPrivateKey);

        // Deploy Attestation Registry
        AnankeAttestationRegistry attestationRegistry = new AnankeAttestationRegistry();
        console.log("AnankeAttestationRegistry deployed at:", address(attestationRegistry));

        // Deploy Revocation Registry
        AnankeRevocationRegistry revocationRegistry = new AnankeRevocationRegistry();
        console.log("AnankeRevocationRegistry deployed at:", address(revocationRegistry));

        vm.stopBroadcast();

        // Log deployment info for integration
        console.log("\n=== DEPLOYMENT COMPLETE ===");
        console.log("Network: Base");
        console.log("Attestation Registry:", address(attestationRegistry));
        console.log("Revocation Registry:", address(revocationRegistry));
        console.log("\nAdd to .env:");
        console.log("ATTESTATION_REGISTRY_ADDR=%s", address(attestationRegistry));
        console.log("REVOCATION_REGISTRY_ADDR=%s", address(revocationRegistry));
    }
}
