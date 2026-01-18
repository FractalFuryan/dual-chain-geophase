"""
Tests for capability destruction and ledger integration.

Verifies:
- Destruction event creation and validation
- Secure key shredding
- Ledger append-only behavior
- Gate enforcement of destroyed capabilities
"""

import os
import tempfile
from pathlib import Path

import pytest

from geophase.ledger import (
    CapabilityDestructionEvent,
    DestructionMethod,
    Ledger,
)
from geophase.storage import DestructionManager


def test_destruction_event_creation():
    """Test creating a destruction event with proof."""
    event = CapabilityDestructionEvent.create(
        asset_id="test-asset-123",
        method=DestructionMethod.KEY_SHRED,
        material_hash="0x" + "ab" * 32,
        pre_state_commitment="0x" + "cd" * 32,
    )
    
    assert event.asset_id == "test-asset-123"
    assert event.method == DestructionMethod.KEY_SHRED
    assert event.event_type == "capability_destruction"
    assert event.post_state == "DESTROYED"
    assert event.proof_hash is not None
    assert len(event.proof_hash) == 64  # SHA256 hex


def test_destruction_event_proof_verification():
    """Test that proof hash can be verified."""
    material_hash = "0x" + "ab" * 32
    
    event = CapabilityDestructionEvent.create(
        asset_id="test-asset-123",
        method=DestructionMethod.KEY_SHRED,
        material_hash=material_hash,
        pre_state_commitment="0x" + "cd" * 32,
    )
    
    # Correct material hash should verify
    assert event.verify_proof(material_hash)
    
    # Wrong material hash should fail
    assert not event.verify_proof("0x" + "ff" * 32)


def test_destruction_event_is_irreversible():
    """Test that destruction is always marked as irreversible."""
    event = CapabilityDestructionEvent.create(
        asset_id="test-asset-123",
        method=DestructionMethod.FULL_PURGE,
        material_hash="0x" + "ab" * 32,
        pre_state_commitment="0x" + "cd" * 32,
    )
    
    assert event.is_irreversible()


def test_destruction_manager_shred_key():
    """Test secure key shredding."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test key file
        key_path = Path(tmpdir) / "test-asset.key"
        original_key = b"this is a secret key material"
        key_path.write_bytes(original_key)
        
        # Shred it
        manager = DestructionManager(tmpdir)
        key_hash = manager.shred_key("test-asset")
        
        # Verify hash is correct
        import hashlib
        expected_hash = hashlib.sha256(original_key).hexdigest()
        assert key_hash == expected_hash
        
        # Verify file no longer exists
        assert not key_path.exists()


def test_destruction_manager_key_not_found():
    """Test that shredding non-existent key raises error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = DestructionManager(tmpdir)
        
        with pytest.raises(FileNotFoundError, match="Key not found"):
            manager.shred_key("nonexistent")


def test_destruction_manager_delete_payload():
    """Test payload deletion."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test payload file
        payload_path = Path(tmpdir) / "test-asset.bin"
        original_payload = b"encrypted payload data here"
        payload_path.write_bytes(original_payload)
        
        # Delete it
        manager = DestructionManager(tmpdir)
        payload_hash = manager.delete_payload("test-asset")
        
        # Verify hash is correct
        import hashlib
        expected_hash = hashlib.sha256(original_payload).hexdigest()
        assert payload_hash == expected_hash
        
        # Verify file no longer exists
        assert not payload_path.exists()


def test_destruction_manager_delete_missing_payload():
    """Test that deleting non-existent payload returns None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = DestructionManager(tmpdir)
        result = manager.delete_payload("nonexistent")
        assert result is None


def test_destruction_manager_destroy_capability_full():
    """Test full capability destruction (key + payload)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        key_path = Path(tmpdir) / "test-asset.key"
        payload_path = Path(tmpdir) / "test-asset.bin"
        key_path.write_bytes(b"secret key")
        payload_path.write_bytes(b"encrypted data")
        
        # Destroy
        manager = DestructionManager(tmpdir)
        result = manager.destroy_capability("test-asset")
        
        # Verify results
        assert result.asset_id == "test-asset"
        assert result.key_destroyed
        assert result.key_hash is not None
        assert result.payload_destroyed
        assert result.payload_hash is not None
        assert result.material_hash is not None  # Combined hash
        
        # Verify files gone
        assert not key_path.exists()
        assert not payload_path.exists()


def test_destruction_manager_destroy_key_only():
    """Test destroying key only (no payload)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create only key file
        key_path = Path(tmpdir) / "test-asset.key"
        key_path.write_bytes(b"secret key")
        
        # Destroy key only
        manager = DestructionManager(tmpdir)
        result = manager.destroy_capability("test-asset", delete_payload=False)
        
        assert result.key_destroyed
        assert result.key_hash is not None
        assert not result.payload_destroyed
        assert result.payload_hash is None


def test_destruction_manager_verify_destroyed():
    """Test verifying that an asset is destroyed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create and destroy
        key_path = Path(tmpdir) / "test-asset.key"
        key_path.write_bytes(b"secret")
        
        manager = DestructionManager(tmpdir)
        assert not manager.verify_destroyed("test-asset")
        
        manager.shred_key("test-asset")
        assert manager.verify_destroyed("test-asset")


def test_ledger_add_event():
    """Test adding an event to the ledger."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"
        ledger = Ledger(ledger_path)
        
        event = CapabilityDestructionEvent.create(
            asset_id="test-123",
            method=DestructionMethod.KEY_SHRED,
            material_hash="0x" + "ab" * 32,
            pre_state_commitment="0x" + "cd" * 32,
        )
        
        ledger.add_event(event)
        
        # Verify file exists and has content
        assert ledger_path.exists()
        content = ledger_path.read_text()
        assert "test-123" in content
        assert "capability_destruction" in content


def test_ledger_iter_events():
    """Test iterating over ledger events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"
        ledger = Ledger(ledger_path)
        
        # Add multiple events
        for i in range(3):
            event = CapabilityDestructionEvent.create(
                asset_id=f"asset-{i}",
                method=DestructionMethod.KEY_SHRED,
                material_hash="0x" + "ab" * 32,
                pre_state_commitment="0x" + "cd" * 32,
            )
            ledger.add_event(event)
        
        # Iterate and verify
        events = list(ledger.iter_events())
        assert len(events) == 3
        assert events[0].asset_id == "asset-0"
        assert events[1].asset_id == "asset-1"
        assert events[2].asset_id == "asset-2"


def test_ledger_is_destroyed():
    """Test checking if an asset is destroyed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"
        ledger = Ledger(ledger_path)
        
        # Not destroyed yet
        assert not ledger.is_destroyed("test-123")
        
        # Add destruction event
        event = CapabilityDestructionEvent.create(
            asset_id="test-123",
            method=DestructionMethod.KEY_SHRED,
            material_hash="0x" + "ab" * 32,
            pre_state_commitment="0x" + "cd" * 32,
        )
        ledger.add_event(event)
        
        # Now it's destroyed
        assert ledger.is_destroyed("test-123")
        
        # Other assets not affected
        assert not ledger.is_destroyed("test-456")


def test_ledger_get_destruction_proof():
    """Test retrieving destruction proof hash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"
        ledger = Ledger(ledger_path)
        
        event = CapabilityDestructionEvent.create(
            asset_id="test-123",
            method=DestructionMethod.KEY_SHRED,
            material_hash="0x" + "ab" * 32,
            pre_state_commitment="0x" + "cd" * 32,
        )
        ledger.add_event(event)
        
        proof = ledger.get_destruction_proof("test-123")
        assert proof == event.proof_hash
        assert proof is not None
        
        # Non-existent asset
        assert ledger.get_destruction_proof("nonexistent") is None


def test_ledger_count_events():
    """Test counting total events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"
        ledger = Ledger(ledger_path)
        
        assert ledger.count_events() == 0
        
        for i in range(5):
            event = CapabilityDestructionEvent.create(
                asset_id=f"asset-{i}",
                method=DestructionMethod.KEY_SHRED,
                material_hash="0x" + "ab" * 32,
                pre_state_commitment="0x" + "cd" * 32,
            )
            ledger.add_event(event)
        
        assert ledger.count_events() == 5


def test_ledger_query_by_asset():
    """Test querying events by asset."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "events.jsonl"
        ledger = Ledger(ledger_path)
        
        # Add events for different assets
        for i in range(3):
            event = CapabilityDestructionEvent.create(
                asset_id="asset-1" if i < 2 else "asset-2",
                method=DestructionMethod.KEY_SHRED,
                material_hash="0x" + "ab" * 32,
                pre_state_commitment="0x" + "cd" * 32,
            )
            ledger.add_event(event)
        
        query = ledger.query()
        
        asset1_events = query.by_asset("asset-1")
        assert len(asset1_events) == 2
        
        asset2_events = query.by_asset("asset-2")
        assert len(asset2_events) == 1


def test_full_destruction_workflow():
    """Test complete destruction workflow: destroy -> event -> ledger."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir) / "storage"
        storage_dir.mkdir()
        ledger_path = Path(tmpdir) / "ledger.jsonl"
        
        # Setup
        asset_id = "important-asset"
        key_path = storage_dir / f"{asset_id}.key"
        key_path.write_bytes(b"secret encryption key")
        
        manager = DestructionManager(storage_dir)
        ledger = Ledger(ledger_path)
        
        # Get pre-state commitment (in real system, this would be computed)
        pre_state = "0x" + "aa" * 32
        
        # Destroy capability
        result = manager.destroy_capability(asset_id)
        
        # Create and record event
        event = CapabilityDestructionEvent.create(
            asset_id=asset_id,
            method=DestructionMethod.KEY_SHRED,
            material_hash=result.material_hash,
            pre_state_commitment=pre_state,
        )
        ledger.add_event(event)
        
        # Verify complete destruction
        assert manager.verify_destroyed(asset_id)
        assert ledger.is_destroyed(asset_id)
        assert not key_path.exists()
        
        # Verify proof
        proof = ledger.get_destruction_proof(asset_id)
        assert proof is not None


def test_destruction_methods_enum():
    """Test DestructionMethod enum values."""
    assert DestructionMethod.KEY_SHRED == "key_shred"
    assert DestructionMethod.STORAGE_DELETE == "storage_delete"
    assert DestructionMethod.FULL_PURGE == "full_purge"
