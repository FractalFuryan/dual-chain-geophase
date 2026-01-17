"""
Test bytecode lock verification.
"""

import pytest
from unittest.mock import Mock, patch
from geophase.eth.bytecode_lock import BytecodeLock, keccak_hex


def test_keccak_hex():
    """Test keccak_hex produces correct output."""
    # Known test vector
    data = b"hello"
    expected = "1c8aff950685c2ed4bc3174f3472287b56d9517b9c948127319a09a7a36deac8"
    
    assert keccak_hex(data) == expected


def test_bytecode_lock_verify_success():
    """Test BytecodeLock verification succeeds with matching bytecode."""
    # Mock Web3 instance
    mock_w3 = Mock()
    mock_w3.eth.get_code.return_value = b"\x60\x80\x60\x40"
    
    # Compute expected hash
    expected_hash = keccak_hex(b"\x60\x80\x60\x40")
    
    # Create lock
    lock = BytecodeLock(mock_w3, "0x1234567890123456789012345678901234567890", expected_hash)
    
    # Should not raise
    lock.verify_or_raise()


def test_bytecode_lock_verify_failure():
    """Test BytecodeLock verification fails with mismatched bytecode."""
    # Mock Web3 instance
    mock_w3 = Mock()
    mock_w3.eth.get_code.return_value = b"\x60\x80\x60\x40"
    
    # Wrong expected hash
    wrong_hash = "0" * 64
    
    # Create lock
    lock = BytecodeLock(mock_w3, "0x1234567890123456789012345678901234567890", wrong_hash)
    
    # Should raise
    with pytest.raises(RuntimeError, match="BYTECODE_LOCK FAIL"):
        lock.verify_or_raise()


def test_bytecode_lock_empty_bytecode():
    """Test BytecodeLock fails on empty bytecode (undeployed contract)."""
    # Mock Web3 instance
    mock_w3 = Mock()
    mock_w3.eth.get_code.return_value = b""
    
    expected_hash = keccak_hex(b"\x60\x80")
    
    # Create lock
    lock = BytecodeLock(mock_w3, "0x1234567890123456789012345678901234567890", expected_hash)
    
    # Should raise
    with pytest.raises(RuntimeError, match="BYTECODE_LOCK FAIL"):
        lock.verify_or_raise()


def test_bytecode_lock_none_expected():
    """Test BytecodeLock allows None expected_hash (skip verification)."""
    # Mock Web3 instance
    mock_w3 = Mock()
    mock_w3.eth.get_code.return_value = b"\x60\x80\x60\x40"
    
    # Create lock with None expected
    lock = BytecodeLock(mock_w3, "0x1234567890123456789012345678901234567890", None)
    
    # Should not raise (verification skipped)
    lock.verify_or_raise()
