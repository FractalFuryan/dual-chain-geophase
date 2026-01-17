"""
Test canonical geoCommit computation with PREFIX_V1.
"""

import pytest
from geophase.eth.geocommit import (
    compute_geo_commit,
    GeoCommitParams,
    PREFIX_V1,
    GEO_COMMIT_VERSION,
)


def test_prefix_v1_constant():
    """Test PREFIX_V1 constant is correctly defined."""
    assert PREFIX_V1 == b"ANANKE_GEO_COMMIT_V1"
    assert len(PREFIX_V1) == 20


def test_geo_commit_version():
    """Test GEO_COMMIT_VERSION constant."""
    assert GEO_COMMIT_VERSION == 1


def test_compute_geo_commit_valid():
    """Test compute_geo_commit with valid inputs."""
    params = GeoCommitParams(
        seed_commit=b"\x00" * 32,
        phaseA_hash=b"\x01" * 32,
        phaseB_hash=b"\x02" * 32,
        policy_id=b"\x03" * 32,
        version=1,
    )
    
    geo_commit = compute_geo_commit(params)
    
    # Should be 32 bytes
    assert len(geo_commit) == 32
    assert isinstance(geo_commit, bytes)


def test_compute_geo_commit_invalid_hash_length():
    """Test compute_geo_commit rejects invalid hash length."""
    with pytest.raises(ValueError, match="seed_commit must be 32 bytes"):
        params = GeoCommitParams(
            seed_commit=b"\x00" * 31,
            phaseA_hash=b"\x01" * 32,
            phaseB_hash=b"\x02" * 32,
            policy_id=b"\x03" * 32,
            version=1,
        )
        compute_geo_commit(params)


def test_compute_geo_commit_invalid_version():
    """Test compute_geo_commit rejects invalid version."""
    with pytest.raises(ValueError, match="version must be uint32"):
        params = GeoCommitParams(
            seed_commit=b"\x00" * 32,
            phaseA_hash=b"\x01" * 32,
            phaseB_hash=b"\x02" * 32,
            policy_id=b"\x03" * 32,
            version=-1,
        )
        compute_geo_commit(params)


def test_compute_geo_commit_deterministic():
    """Test compute_geo_commit is deterministic."""
    params = GeoCommitParams(
        seed_commit=b"\xaa" * 32,
        phaseA_hash=b"\xbb" * 32,
        phaseB_hash=b"\xcc" * 32,
        policy_id=b"\xdd" * 32,
        version=1,
    )
    
    commit1 = compute_geo_commit(params)
    commit2 = compute_geo_commit(params)
    
    assert commit1 == commit2


def test_compute_geo_commit_different_inputs():
    """Test compute_geo_commit produces different outputs for different inputs."""
    params1 = GeoCommitParams(
        seed_commit=b"\x00" * 32,
        phaseA_hash=b"\x01" * 32,
        phaseB_hash=b"\x02" * 32,
        policy_id=b"\x03" * 32,
        version=1,
    )
    
    params2 = GeoCommitParams(
        seed_commit=b"\xff" * 32,
        phaseA_hash=b"\x01" * 32,
        phaseB_hash=b"\x02" * 32,
        policy_id=b"\x03" * 32,
        version=1,
    )
    
    commit1 = compute_geo_commit(params1)
    commit2 = compute_geo_commit(params2)
    
    assert commit1 != commit2


def test_compute_geo_commit_version_sensitivity():
    """Test compute_geo_commit changes with version."""
    params_v1 = GeoCommitParams(
        seed_commit=b"\xaa" * 32,
        phaseA_hash=b"\xbb" * 32,
        phaseB_hash=b"\xcc" * 32,
        policy_id=b"\xdd" * 32,
        version=1,
    )
    
    params_v2 = GeoCommitParams(
        seed_commit=b"\xaa" * 32,
        phaseA_hash=b"\xbb" * 32,
        phaseB_hash=b"\xcc" * 32,
        policy_id=b"\xdd" * 32,
        version=2,
    )
    
    commit_v1 = compute_geo_commit(params_v1)
    commit_v2 = compute_geo_commit(params_v2)
    
    assert commit_v1 != commit_v2
