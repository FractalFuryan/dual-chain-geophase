// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Public revocation bit. No metadata. No reasons. Just revoked/not.
///         Use geoCommit or tokenIdCommit as the key.
contract AnankeRevocationRegistry {
    event Revoked(bytes32 indexed key, address revoker, uint64 timestamp);

    mapping(bytes32 => bool) public revoked;

    function revoke(bytes32 key) external {
        require(key != bytes32(0), "key=0");
        require(!revoked[key], "already revoked");
        revoked[key] = true;
        emit Revoked(key, msg.sender, uint64(block.timestamp));
    }

    function isRevoked(bytes32 key) external view returns (bool) {
        return revoked[key];
    }
}
