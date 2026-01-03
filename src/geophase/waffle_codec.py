#!/usr/bin/env python3
"""
Waffle Boundary Codec (EXPERIMENTAL, TRANSPORT-ONLY)

This module implements a 2D boundary/seam redundancy scheme
for transporting AEAD ciphertext through noisy channels.

Security invariant:
- This codec NEVER authorizes acceptance.
- All reconstructed bytes MUST pass AEAD verification upstream.
- Failure to reconstruct MUST result in rejection.

Intended use:
- Optional transport layer under GeoPhase Chain.

Goal:
- Treat bytes as a 2D "waffle" grid.
- Encode BOTH:
  (1) external boundary (perimeter) and
  (2) internal boundaries (seam XOR constraints)
  using Reed–Solomon (RS) ECC.
- Decode by RS-correcting the boundary + seams, then reconstructing the grid
  from XOR constraints (anchored by a known boundary cell).

Security posture:
- This is NOT encryption.
- Use it ONLY to transport AEAD ciphertext more robustly.
- Acceptance must still be AEAD-gated (your covenant).

Dependencies:
  pip install reedsolo

Notes:
- Seam constraints (Dx, Dy) + one anchored cell are sufficient to reconstruct
  the entire grid (in the noiseless case).
- RS corrects errors in the boundary and seam streams before reconstruction.

Author: repo-safe prototype
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from collections import deque
import os
import struct
import random

from reedsolo import RSCodec, ReedSolomonError


# -------------------------
# Helpers: perimeter + seams
# -------------------------

def pick_hw(nbytes: int, target_w: int = 32) -> Tuple[int, int]:
    """Choose H,W such that H*W >= nbytes, with W close to target_w."""
    W = max(4, target_w)
    H = (nbytes + W - 1) // W
    return H, W


def fill_grid(data: bytes, H: int, W: int, pad_byte: int = 0) -> List[List[int]]:
    """Fill HxW grid row-major with data bytes, padding with pad_byte."""
    X = [[pad_byte for _ in range(W)] for _ in range(H)]
    k = 0
    for i in range(H):
        for j in range(W):
            if k < len(data):
                X[i][j] = data[k]
                k += 1
    return X


def flatten_grid(X: List[List[int]]) -> bytes:
    """Flatten grid row-major."""
    H = len(X)
    W = len(X[0]) if H else 0
    out = bytearray(H * W)
    k = 0
    for i in range(H):
        for j in range(W):
            out[k] = X[i][j] & 0xFF
            k += 1
    return bytes(out)


def perimeter_coords(H: int, W: int) -> List[Tuple[int, int]]:
    """
    Fixed perimeter order:
      top row (0,0..W-1),
      right col (1..H-2, W-1),
      bottom row (H-1, W-1..0),
      left col (H-2..1, 0)
    """
    if H <= 0 or W <= 0:
        return []
    coords = []
    # top
    for j in range(W):
        coords.append((0, j))
    # right
    for i in range(1, H - 1):
        coords.append((i, W - 1))
    # bottom
    if H > 1:
        for j in range(W - 1, -1, -1):
            coords.append((H - 1, j))
    # left
    for i in range(H - 2, 0, -1):
        coords.append((i, 0))
    return coords


def extract_perimeter(X: List[List[int]]) -> bytes:
    H, W = len(X), len(X[0])
    coords = perimeter_coords(H, W)
    return bytes(X[i][j] & 0xFF for (i, j) in coords)


def write_perimeter(X: List[List[int]], p: bytes) -> None:
    H, W = len(X), len(X[0])
    coords = perimeter_coords(H, W)
    if len(p) != len(coords):
        raise ValueError("Perimeter length mismatch")
    for k, (i, j) in enumerate(coords):
        X[i][j] = p[k]


def seams_dx_dy(X: List[List[int]]) -> Tuple[bytes, bytes]:
    """
    Internal boundary XOR constraints:
      Dx[i,j] = X[i,j] XOR X[i,j+1] for j=0..W-2, i=0..H-1  (H*(W-1) bytes)
      Dy[i,j] = X[i,j] XOR X[i+1,j] for i=0..H-2, j=0..W-1  ((H-1)*W bytes)
    Packed in row-major.
    """
    H, W = len(X), len(X[0])
    dx = bytearray(H * (W - 1))
    dy = bytearray((H - 1) * W)

    k = 0
    for i in range(H):
        for j in range(W - 1):
            dx[k] = (X[i][j] ^ X[i][j + 1]) & 0xFF
            k += 1

    k = 0
    for i in range(H - 1):
        for j in range(W):
            dy[k] = (X[i][j] ^ X[i + 1][j]) & 0xFF
            k += 1

    return bytes(dx), bytes(dy)


def unpack_dx_dy(dx: bytes, dy: bytes, H: int, W: int) -> Tuple[List[List[int]], List[List[int]]]:
    """
    Unpack dx into Hx(W-1) and dy into (H-1)xW matrices (integers 0..255).
    """
    if len(dx) != H * (W - 1):
        raise ValueError("Dx length mismatch")
    if len(dy) != (H - 1) * W:
        raise ValueError("Dy length mismatch")

    DX = [[0 for _ in range(W - 1)] for _ in range(H)]
    DY = [[0 for _ in range(W)] for _ in range(H - 1)]

    k = 0
    for i in range(H):
        for j in range(W - 1):
            DX[i][j] = dx[k]
            k += 1

    k = 0
    for i in range(H - 1):
        for j in range(W):
            DY[i][j] = dy[k]
            k += 1

    return DX, DY


# -------------------------
# Reconstruction from seams
# -------------------------

@dataclass
class ReconStats:
    filled: int
    conflicts: int


def reconstruct_grid_from_boundary_and_seams(
    H: int,
    W: int,
    perimeter: bytes,
    dx: bytes,
    dy: bytes,
    anchor: Tuple[int, int] = (0, 0),
) -> Tuple[List[List[int]], ReconStats]:
    """
    Reconstruct all X[i,j] from:
      - perimeter values (gives multiple anchors, including anchor cell)
      - seam XOR constraints Dx, Dy

    Method:
      - Seed known cells from perimeter into X (partial).
      - BFS-propagate using XOR constraints:
          X[i,j+1] = X[i,j] XOR Dx[i,j]
          X[i+1,j] = X[i,j] XOR Dy[i,j]
      - Count conflicts if we derive a value that disagrees with an already known value.

    NOTE:
      If perimeter/seams are wrong (noise beyond ECC correction), conflicts rise.
    """
    X: List[List[Optional[int]]] = [[None for _ in range(W)] for _ in range(H)]
    # seed perimeter
    coords = perimeter_coords(H, W)
    if len(perimeter) != len(coords):
        raise ValueError("Perimeter length mismatch")
    for k, (i, j) in enumerate(coords):
        X[i][j] = perimeter[k]

    DX, DY = unpack_dx_dy(dx, dy, H, W)

    # Ensure anchor exists and is known; if not, pick first known perimeter cell.
    ai, aj = anchor
    if not (0 <= ai < H and 0 <= aj < W) or X[ai][aj] is None:
        if coords:
            ai, aj = coords[0]
        if X[ai][aj] is None:
            # No anchor available -> cannot solve.
            return [[0 for _ in range(W)] for _ in range(H)], ReconStats(filled=0, conflicts=0)

    q = deque()
    q.append((ai, aj))
    seen = set([(ai, aj)])
    conflicts = 0

    def set_cell(i: int, j: int, val: int) -> None:
        nonlocal conflicts
        cur = X[i][j]
        if cur is None:
            X[i][j] = val & 0xFF
        elif cur != (val & 0xFF):
            conflicts += 1  # inconsistency detected

    while q:
        i, j = q.popleft()
        v = X[i][j]
        if v is None:
            continue

        # right neighbor
        if j < W - 1:
            val = v ^ DX[i][j]
            set_cell(i, j + 1, val)
            if (i, j + 1) not in seen:
                seen.add((i, j + 1))
                q.append((i, j + 1))

        # left neighbor
        if j > 0:
            val = v ^ DX[i][j - 1]  # since DX[i][j-1] = X[i,j-1] XOR X[i,j]
            set_cell(i, j - 1, val)
            if (i, j - 1) not in seen:
                seen.add((i, j - 1))
                q.append((i, j - 1))

        # down neighbor
        if i < H - 1:
            val = v ^ DY[i][j]
            set_cell(i + 1, j, val)
            if (i + 1, j) not in seen:
                seen.add((i + 1, j))
                q.append((i + 1, j))

        # up neighbor
        if i > 0:
            val = v ^ DY[i - 1][j]  # DY[i-1][j] = X[i-1,j] XOR X[i,j]
            set_cell(i - 1, j, val)
            if (i - 1, j) not in seen:
                seen.add((i - 1, j))
                q.append((i - 1, j))

    # finalize: replace None with 0
    out = [[(X[i][j] if X[i][j] is not None else 0) for j in range(W)] for i in range(H)]
    filled = sum(1 for i in range(H) for j in range(W) if X[i][j] is not None)
    return out, ReconStats(filled=filled, conflicts=conflicts)


# -------------------------
# Waffle Codec (RS on ext + int)
# -------------------------

@dataclass
class WaffleParams:
    H: int
    W: int
    nsym_ext: int = 64
    nsym_int: int = 64


def rs_encode(data: bytes, nsym: int) -> bytes:
    return bytes(RSCodec(nsym).encode(data))


def rs_decode(codeword: bytes, nsym: int) -> bytes:
    try:
        decoded = RSCodec(nsym).decode(codeword)
        if isinstance(decoded, tuple):
            return bytes(decoded[0])
        return bytes(decoded)
    except ReedSolomonError:
        return b""


def waffle_encode(ciphertext: bytes, params: WaffleParams) -> bytes:
    """
    Build grid from ciphertext, then:
      ext = RS(perimeter)
      int = RS(dx || dy)
    Carrier framing:
      magic(4) | H(2) | W(2) | nsym_ext(2) | nsym_int(2) | ct_len(4)
      ext_len(4) | int_len(4) | ext | intl | padding

    Padding is optional; keep deterministic if you want T1 reproducibility (caller-controlled).
    """
    H, W = params.H, params.W
    X = fill_grid(ciphertext, H, W, pad_byte=0)

    p = extract_perimeter(X)
    dx, dy = seams_dx_dy(X)

    ext = rs_encode(p, params.nsym_ext)
    intl = rs_encode(dx + dy, params.nsym_int)

    header = struct.pack(
        ">4sHHHHIII",
        b"WFL1",
        H,
        W,
        params.nsym_ext,
        params.nsym_int,
        len(ciphertext),
        len(ext),
        len(intl),
    )
    return header + ext + intl


def waffle_decode(carrier: bytes) -> Tuple[bytes, ReconStats]:
    """
    Decode carrier -> reconstruct grid -> return reconstructed ciphertext (ct_len bytes).
    """
    if len(carrier) < 4:
        raise ValueError("Carrier too short")

    magic = carrier[:4]
    if magic != b"WFL1":
        raise ValueError("Bad magic")

    if len(carrier) < struct.calcsize(">4sHHHHIII"):
        raise ValueError("Carrier header truncated")

    magic, H, W, nsym_ext, nsym_int, ct_len, ext_len, int_len = struct.unpack(
        ">4sHHHHIII", carrier[:struct.calcsize(">4sHHHHIII")]
    )

    offset = struct.calcsize(">4sHHHHIII")
    ext_cw = carrier[offset: offset + ext_len]
    offset += ext_len
    int_cw = carrier[offset: offset + int_len]
    offset += int_len

    p = rs_decode(ext_cw, nsym_ext)
    seams = rs_decode(int_cw, nsym_int)

    # If RS failed hard, we cannot reconstruct reliably.
    expected_p_len = len(perimeter_coords(H, W))
    expected_seams_len = H * (W - 1) + (H - 1) * W

    if len(p) != expected_p_len or len(seams) != expected_seams_len:
        # Return empty with stats showing failure.
        return b"", ReconStats(filled=0, conflicts=0)

    dx = seams[: H * (W - 1)]
    dy = seams[H * (W - 1):]

    Xhat, stats = reconstruct_grid_from_boundary_and_seams(H, W, p, dx, dy, anchor=(0, 0))
    raw = flatten_grid(Xhat)
    return raw[:ct_len], stats


# -------------------------
# Noise test harness
# -------------------------

def apply_byte_noise(data: bytes, flips: int, seed: int = 0) -> bytes:
    """
    Flip 'flips' random bytes by XORing with random nonzero masks.
    """
    r = random.Random(seed)
    if flips <= 0:
        return data
    b = bytearray(data)
    n = len(b)
    for _ in range(flips):
        idx = r.randrange(n)
        mask = r.randrange(1, 256)
        b[idx] ^= mask
    return bytes(b)


def demo():
    # Simulate "ciphertext" (in real use, this would be AEAD ciphertext bytes)
    ct = os.urandom(256)

    H, W = pick_hw(len(ct), target_w=32)
    params = WaffleParams(H=H, W=W, nsym_ext=64, nsym_int=64)
    carrier = waffle_encode(ct, params)

    print(f"HxW = {H}x{W} ({H*W} cells)")
    print(f"carrier bytes = {len(carrier)}")

    for flips in [0, 8, 16, 32, 64, 96, 128]:
        noisy = apply_byte_noise(carrier, flips=flips, seed=42)
        try:
            recovered, stats = waffle_decode(noisy)
            ok = (recovered == ct)
            print(f"noise flips={flips:3d} -> ok={ok} | filled={stats.filled} conflicts={stats.conflicts}")
        except ValueError as e:
            print(f"noise flips={flips:3d} -> error={str(e)}")


if __name__ == "__main__":
    demo()
