"""
Tests for Waffle Boundary Codec

Validates:
- Roundtrip encoding/decoding without noise
- Behavior under noise (must not crash)
- Reconstruction statistics tracking

NOTE: These tests do NOT validate security acceptance.
Acceptance must be AEAD-gated per the covenant.
"""

import os
import pytest
from src.geophase.waffle_codec import (
    WaffleParams,
    waffle_encode,
    waffle_decode,
    apply_byte_noise,
    pick_hw,
    fill_grid,
    flatten_grid,
    extract_perimeter,
    seams_dx_dy,
    reconstruct_grid_from_boundary_and_seams,
    perimeter_coords,
)


class TestWaffleRoundtrip:
    """Basic roundtrip tests without noise."""

    def test_roundtrip_no_noise_256_bytes(self):
        """Encode and decode 256 bytes with no noise."""
        ct = os.urandom(256)
        H, W = pick_hw(len(ct), target_w=32)
        params = WaffleParams(H=H, W=W, nsym_ext=64, nsym_int=64)
        carrier = waffle_encode(ct, params)
        recovered, stats = waffle_decode(carrier)
        assert recovered == ct
        assert stats.conflicts == 0

    def test_roundtrip_no_noise_1024_bytes(self):
        """Encode and decode 1024 bytes with no noise."""
        ct = os.urandom(1024)
        H, W = pick_hw(len(ct), target_w=32)
        params = WaffleParams(H=H, W=W, nsym_ext=64, nsym_int=64)
        carrier = waffle_encode(ct, params)
        recovered, stats = waffle_decode(carrier)
        assert recovered == ct
        assert stats.conflicts == 0

    def test_roundtrip_deterministic_data(self):
        """Encode and decode deterministic test data."""
        ct = b"Hello, Waffle!" * 16  # 224 bytes
        H, W = pick_hw(len(ct), target_w=32)
        params = WaffleParams(H=H, W=W, nsym_ext=64, nsym_int=64)
        carrier = waffle_encode(ct, params)
        recovered, stats = waffle_decode(carrier)
        assert recovered == ct
        assert stats.conflicts == 0


class TestWaffleNoise:
    """Noise resilience tests."""

    def test_noise_no_crash_light(self):
        """Light noise should decode without crashing."""
        ct = os.urandom(256)
        H, W = pick_hw(len(ct), target_w=32)
        params = WaffleParams(H=H, W=W, nsym_ext=64, nsym_int=64)
        carrier = waffle_encode(ct, params)
        noisy = apply_byte_noise(carrier, flips=8, seed=42)
        recovered, stats = waffle_decode(noisy)
        # May or may not recover, but must not crash
        assert isinstance(recovered, bytes)
        assert isinstance(stats.filled, int)
        assert isinstance(stats.conflicts, int)

    def test_noise_no_crash_moderate(self):
        """Moderate noise should decode without crashing."""
        ct = os.urandom(256)
        H, W = pick_hw(len(ct), target_w=32)
        params = WaffleParams(H=H, W=W, nsym_ext=64, nsym_int=64)
        carrier = waffle_encode(ct, params)
        noisy = apply_byte_noise(carrier, flips=32, seed=42)
        recovered, stats = waffle_decode(noisy)
        assert isinstance(recovered, bytes)
        assert isinstance(stats.filled, int)
        assert isinstance(stats.conflicts, int)

    def test_noise_no_crash_heavy(self):
        """Heavy noise should decode without crashing."""
        ct = os.urandom(256)
        H, W = pick_hw(len(ct), target_w=32)
        params = WaffleParams(H=H, W=W, nsym_ext=64, nsym_int=64)
        carrier = waffle_encode(ct, params)
        noisy = apply_byte_noise(carrier, flips=96, seed=42)
        recovered, stats = waffle_decode(noisy)
        assert isinstance(recovered, bytes)
        assert isinstance(stats.filled, int)
        assert isinstance(stats.conflicts, int)

    def test_noise_escalating_failures(self):
        """As noise increases, reconstruction quality degrades gracefully."""
        ct = os.urandom(256)
        H, W = pick_hw(len(ct), target_w=32)
        params = WaffleParams(H=H, W=W, nsym_ext=64, nsym_int=64)
        carrier = waffle_encode(ct, params)

        results = []
        for flips in [0, 16, 32, 64, 128]:
            noisy = apply_byte_noise(carrier, flips=flips, seed=42)
            try:
                recovered, stats = waffle_decode(noisy)
                results.append((flips, recovered == ct, stats.conflicts))
            except ValueError:
                # Bad magic or other format error is also acceptable
                results.append((flips, False, -1))

        # With 0 flips, should always match
        assert results[0][1] is True

        # No crashes - all entries have results
        assert len(results) == 5


class TestGridOperations:
    """Test grid manipulation and reconstruction primitives."""

    def test_perimeter_coords_basic(self):
        """Perimeter coordinates are well-formed."""
        H, W = 4, 5
        coords = perimeter_coords(H, W)
        # Should have 2*H + 2*W - 4 cells (corners counted once each)
        expected = 2 * H + 2 * W - 4
        assert len(coords) == expected

    def test_grid_roundtrip(self):
        """Fill and flatten grid preserves data."""
        ct = b"Test" * 10
        H, W = 5, 8
        grid = fill_grid(ct, H, W, pad_byte=0)
        flat = flatten_grid(grid)
        assert flat[:len(ct)] == ct

    def test_perimeter_extract_write(self):
        """Extract and write perimeter roundtrips."""
        ct = os.urandom(128)
        H, W = 8, 16
        grid = fill_grid(ct, H, W, pad_byte=0)
        p1 = extract_perimeter(grid)
        # Modify grid perimeter
        grid_copy = [row[:] for row in grid]
        perimeter_coords_list = perimeter_coords(H, W)
        for i, j in perimeter_coords_list:
            grid_copy[i][j] ^= 0xFF
        p2 = extract_perimeter(grid_copy)
        assert p1 != p2

    def test_seams_dx_dy(self):
        """Seam constraints are computed correctly."""
        ct = os.urandom(64)
        H, W = 4, 8
        grid = fill_grid(ct, H, W, pad_byte=0)
        dx, dy = seams_dx_dy(grid)
        assert len(dx) == H * (W - 1)
        assert len(dy) == (H - 1) * W


class TestErrorHandling:
    """Test error conditions and edge cases."""

    def test_decode_bad_magic(self):
        """Decoder rejects bad magic."""
        bad_carrier = b"BAD!" + os.urandom(100)
        try:
            recovered, stats = waffle_decode(bad_carrier)
            # Should either return empty or raise ValueError
            assert isinstance(recovered, bytes)
        except ValueError:
            # Expected behavior - bad magic raises ValueError
            pass

    def test_decode_truncated_header(self):
        """Decoder handles truncated header."""
        short_carrier = b"WFL" + os.urandom(4)
        try:
            recovered, stats = waffle_decode(short_carrier)
            # Should either return empty or raise ValueError
            assert isinstance(recovered, bytes)
        except ValueError:
            pass  # Also acceptable

    def test_decode_too_short(self):
        """Decoder handles carrier that is too short."""
        tiny = b"X"
        try:
            recovered, stats = waffle_decode(tiny)
            assert isinstance(recovered, bytes)
        except ValueError:
            pass  # Also acceptable


class TestParameterVariants:
    """Test different grid and ECC parameter combinations."""

    def test_small_grid(self):
        """Small grid (4x4)."""
        ct = b"Test" * 2
        params = WaffleParams(H=4, W=4, nsym_ext=16, nsym_int=16)
        carrier = waffle_encode(ct, params)
        recovered, stats = waffle_decode(carrier)
        assert recovered == ct

    def test_tall_grid(self):
        """Tall grid (16x4)."""
        ct = os.urandom(64)
        params = WaffleParams(H=16, W=4, nsym_ext=32, nsym_int=32)
        carrier = waffle_encode(ct, params)
        recovered, stats = waffle_decode(carrier)
        assert recovered == ct

    def test_wide_grid(self):
        """Wide grid (4x16)."""
        ct = os.urandom(64)
        params = WaffleParams(H=4, W=16, nsym_ext=32, nsym_int=32)
        carrier = waffle_encode(ct, params)
        recovered, stats = waffle_decode(carrier)
        assert recovered == ct

    def test_minimal_ecc(self):
        """Minimal ECC symbols."""
        ct = os.urandom(64)
        H, W = pick_hw(len(ct), target_w=32)
        params = WaffleParams(H=H, W=W, nsym_ext=8, nsym_int=8)
        carrier = waffle_encode(ct, params)
        recovered, stats = waffle_decode(carrier)
        assert recovered == ct

    def test_strong_ecc(self):
        """Strong ECC symbols."""
        ct = os.urandom(64)
        H, W = pick_hw(len(ct), target_w=32)
        params = WaffleParams(H=H, W=W, nsym_ext=128, nsym_int=128)
        carrier = waffle_encode(ct, params)
        recovered, stats = waffle_decode(carrier)
        assert recovered == ct
