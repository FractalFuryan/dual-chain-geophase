"""
Test fail-closed safety modes.
"""

import pytest
from unittest.mock import Mock, patch
from geophase.eth.settings import Settings
from geophase.eth.geocommit import GeoCommitParams
from geophase.eth.fastapi_middleware import build_geocommit_gate


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    return Settings(
        BASE_RPC_URL="http://localhost:8545",
        ATTESTATION_REGISTRY_ADDR="0x1111111111111111111111111111111111111111",
        REVOCATION_REGISTRY_ADDR="0x2222222222222222222222222222222222222222",
        CHAIN_ID=8453,
        STRICT_CHAIN=True,
        STRICT_REVOCATION=True,
        BYTECODE_LOCK_ENABLED=False,
        ATTESTATION_BYTECODE_HASH=None,
        REVOCATION_BYTECODE_HASH=None,
    )


@pytest.fixture
def sample_params():
    """Create sample GeoCommitParams."""
    return GeoCommitParams(
        seed_commit=b"\x00" * 32,
        phaseA_hash=b"\x01" * 32,
        phaseB_hash=b"\x02" * 32,
        policy_id=b"\x03" * 32,
        version=1,
    )

def test_fail_closed_chain_unreachable(mock_settings):
    """Test fail-closed behavior when chain is unreachable."""
    with patch("geophase.eth.fastapi_middleware.ChainClient") as MockClient:
        # Mock unreachable chain
        mock_client = Mock()
        mock_client.ping.return_value = False
        MockClient.return_value = mock_client
        
        # Should raise on init
        with pytest.raises(RuntimeError, match="FAIL_CLOSED: Chain unreachable"):
            build_geocommit_gate(mock_settings)


def test_fail_open_chain_unreachable(mock_settings):
    """Test fail-open allows degraded mode when strict_chain=False."""
    # Create new settings with STRICT_CHAIN=False
    settings = Settings(
        BASE_RPC_URL=mock_settings.BASE_RPC_URL,
        ATTESTATION_REGISTRY_ADDR=mock_settings.ATTESTATION_REGISTRY_ADDR,
        REVOCATION_REGISTRY_ADDR=mock_settings.REVOCATION_REGISTRY_ADDR,
        CHAIN_ID=mock_settings.CHAIN_ID,
        STRICT_CHAIN=False,
        STRICT_REVOCATION=mock_settings.STRICT_REVOCATION,
        BYTECODE_LOCK_ENABLED=mock_settings.BYTECODE_LOCK_ENABLED,
        ATTESTATION_BYTECODE_HASH=mock_settings.ATTESTATION_BYTECODE_HASH,
        REVOCATION_BYTECODE_HASH=mock_settings.REVOCATION_BYTECODE_HASH,
    )
    
    with patch("geophase.eth.fastapi_middleware.ChainClient") as MockClient:
        # Mock unreachable chain
        mock_client = Mock()
        mock_client.ping.return_value = False
        MockClient.return_value = mock_client
        
        # Should not raise
        gate = build_geocommit_gate(settings)
        assert gate is not None


def test_fail_closed_revocation_check_error(mock_settings, sample_params):
    """Test fail-closed blocks on revocation check errors."""
    with patch("geophase.eth.fastapi_middleware.ChainClient") as MockClient:
        # Mock client with failing revocation check
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.bytecode_lock = Mock()
        mock_client.is_revoked.side_effect = Exception("RPC error")
        MockClient.return_value = mock_client
        
        gate = build_geocommit_gate(mock_settings)
        
        # Should raise HTTPException
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as excinfo:
            gate(sample_params)
        
        assert excinfo.value.status_code == 503
        assert "STRICT_REVOCATION=True" in excinfo.value.detail


def test_fail_open_revocation_check_error(mock_settings, sample_params):
    """Test fail-open allows on revocation check errors when strict_revocation=False."""
    # Create new settings with STRICT_REVOCATION=False
    settings = Settings(
        BASE_RPC_URL=mock_settings.BASE_RPC_URL,
        ATTESTATION_REGISTRY_ADDR=mock_settings.ATTESTATION_REGISTRY_ADDR,
        REVOCATION_REGISTRY_ADDR=mock_settings.REVOCATION_REGISTRY_ADDR,
        CHAIN_ID=mock_settings.CHAIN_ID,
        STRICT_CHAIN=mock_settings.STRICT_CHAIN,
        STRICT_REVOCATION=False,
        BYTECODE_LOCK_ENABLED=mock_settings.BYTECODE_LOCK_ENABLED,
        ATTESTATION_BYTECODE_HASH=mock_settings.ATTESTATION_BYTECODE_HASH,
        REVOCATION_BYTECODE_HASH=mock_settings.REVOCATION_BYTECODE_HASH,
    )
    
    with patch("geophase.eth.fastapi_middleware.ChainClient") as MockClient:
        # Mock client with failing revocation check
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.bytecode_lock = Mock()
        mock_client.is_revoked.side_effect = Exception("RPC error")
        MockClient.return_value = mock_client
        
        gate = build_geocommit_gate(settings)
        
        # Should allow (degraded mode)
        result = gate(sample_params)
        assert result["allowed"] is True


def test_revoked_commit_blocked(mock_settings, sample_params):
    """Test revoked commits are blocked."""
    with patch("geophase.eth.fastapi_middleware.ChainClient") as MockClient:
        # Mock client with revoked commit
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.bytecode_lock = Mock()
        mock_client.is_revoked.return_value = True
        MockClient.return_value = mock_client
        
        gate = build_geocommit_gate(mock_settings)
        
        result = gate(sample_params)
        
        assert result["allowed"] is False
        assert result["reason"] == "REVOKED"


def test_healthy_path(mock_settings, sample_params):
    """Test healthy path allows generation."""
    with patch("geophase.eth.fastapi_middleware.ChainClient") as MockClient:
        # Mock healthy client
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.bytecode_lock = Mock()
        mock_client.is_revoked.return_value = False
        MockClient.return_value = mock_client
        
        gate = build_geocommit_gate(mock_settings)
        
        result = gate(sample_params)
        
        assert result["allowed"] is True
        assert result["reason"] == "OK"
        assert "geoCommit" in result
