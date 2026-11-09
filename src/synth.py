"""Synthetic clean images and additive Gaussian noise for F0.

This is the only module that produces clean images.
"""

from __future__ import annotations

import numpy as np
from numpy.random import Generator, PCG64

from src.f0_config import F0Config


def _coordinate_grid(H: int, W: int) -> tuple[np.ndarray, np.ndarray]:
    """Normalized pixel-center coordinate grids.

    Returns X, Y each of shape (H, W) with X increasing across columns
    and Y increasing down rows.
    """
    gx = (np.arange(W, dtype=np.float64) + 0.5) / W
    gy = (np.arange(H, dtype=np.float64) + 0.5) / H
    return np.meshgrid(gx, gy, indexing="xy")


def make_clean(name: str, gen_seed: int, cfg: F0Config) -> np.ndarray:
    """Generate a deterministic 64x64 clean image in [0, 1]."""
    rng = Generator(PCG64(gen_seed))
    H, W = cfg.H, cfg.W
    X, Y = _coordinate_grid(H, W)

    # TE* images reuse the generators for D1..D3 with a caller-supplied seed.
    base_name = {"TE1": "D1", "TE2": "D2", "TE3": "D3"}.get(name, name)

    if base_name == "D1":
        img = _make_d1(X, Y, rng)
    elif base_name == "D2":
        img = _make_d2(X, Y, rng)
    elif base_name == "D3":
        img = _make_d3(X, Y, rng)
    else:
        raise ValueError(f"Unknown clean image name: {name!r}")

    return np.asarray(img, dtype=np.float64)


def _make_d1(X: np.ndarray, Y: np.ndarray, rng: Generator) -> np.ndarray:
    """Smooth blobs plus a soft edge."""
    img = np.zeros_like(X)
    n_blobs = 6
    for _ in range(n_blobs):
        cx, cy = rng.random(2)
        sx, sy = 0.05 + 0.10 * rng.random(2)
        theta = rng.random() * 2.0 * np.pi
        amp = 0.3 + 0.4 * rng.random()
        cos_t, sin_t = np.cos(theta), np.sin(theta)
        dx, dy = X - cx, Y - cy
        u = cos_t * dx + sin_t * dy
        v = -sin_t * dx + cos_t * dy
        img += amp * np.exp(-0.5 * ((u / sx) ** 2 + (v / sy) ** 2))

    # Soft edge via sigmoid
    edge_angle = rng.random() * 2.0 * np.pi
    edge_pos = 0.3 + 0.4 * rng.random()
    edge_width = 0.03 + 0.05 * rng.random()
    edge_val = rng.random()
    normal = np.cos(edge_angle) * X + np.sin(edge_angle) * Y
    img += edge_val / (1.0 + np.exp((normal - edge_pos) / edge_width))

    mn, mx = img.min(), img.max()
    return (img - mn) / (mx - mn + 1e-12)


def _make_d2(X: np.ndarray, Y: np.ndarray, rng: Generator) -> np.ndarray:
    """Multi-scale random Gaussian blob texture."""
    img = np.zeros_like(X)
    n_blobs = 80
    for _ in range(n_blobs):
        cx, cy = rng.random(2)
        scale = 0.005 + 0.030 * rng.random()
        amp = 0.05 + 0.15 * rng.random()
        sign = 1.0 if rng.random() > 0.5 else -1.0
        dx, dy = X - cx, Y - cy
        img += sign * amp * np.exp(-0.5 * ((dx / scale) ** 2 + (dy / scale) ** 2))
    return np.clip(img, 0.0, 1.0)


def _make_d3(X: np.ndarray, Y: np.ndarray, rng: Generator) -> np.ndarray:
    """Piecewise constant regions plus thin line segments."""
    img = np.zeros_like(X)

    n_rect = 5
    for _ in range(n_rect):
        x0, x1 = np.sort(rng.random(2))
        y0, y1 = np.sort(rng.random(2))
        val = rng.random()
        mask = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1)
        img[mask] = val

    n_lines = 6
    for _ in range(n_lines):
        x0, y0 = rng.random(2)
        x1, y1 = rng.random(2)
        thickness = 0.005 + 0.015 * rng.random()
        val = rng.random()
        dx_seg, dy_seg = x1 - x0, y1 - y0
        len2 = dx_seg * dx_seg + dy_seg * dy_seg
        if len2 < 1e-12:
            continue
        t = np.clip(((X - x0) * dx_seg + (Y - y0) * dy_seg) / len2, 0.0, 1.0)
        proj_x = x0 + t * dx_seg
        proj_y = y0 + t * dy_seg
        dist = np.sqrt((X - proj_x) ** 2 + (Y - proj_y) ** 2)
        img[dist < thickness] = val

    return np.clip(img, 0.0, 1.0)


def add_noise(x: np.ndarray, sigma: float, seed: int) -> np.ndarray:
    """Additive white Gaussian noise; no clipping."""
    rng = Generator(PCG64(seed))
    return np.asarray(x, dtype=np.float64) + rng.normal(0.0, sigma, size=x.shape)
