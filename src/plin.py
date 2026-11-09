"""Positive-control linear model for F0 (P-lin).

May import src.omega but must not import src.synth or src.reference_eval.
"""

from __future__ import annotations

import numpy as np
from numpy.random import SeedSequence

from src.f0_config import F0Config
from src.omega import omega_rng


def plin_atoms(cfg: F0Config) -> np.ndarray:
    """Return the P-lin dictionary A (N x 1024), columns L2-normalised.

    Atom index a = s_idx*256 + gy*16 + gx for scale plin_scales_px[s_idx]
    and normalised grid centre ((gx+0.5)/16, (gy+0.5)/16).
    """
    H, W = cfg.H, cfg.W
    N = H * W
    G = cfg.plin_grid
    scales = cfg.plin_scales_px
    n_atoms = len(scales) * G * G
    A = np.empty((N, n_atoms), dtype=np.float64)

    rows = (np.arange(H, dtype=np.float64).reshape(-1, 1) + 0.5)
    cols = (np.arange(W, dtype=np.float64).reshape(1, -1) + 0.5)
    # Pixel centre arrays, shape (H, W).
    px_y = np.broadcast_to(rows, (H, W))
    px_x = np.broadcast_to(cols, (H, W))
    px_y = px_y.ravel()
    px_x = px_x.ravel()

    for s_idx, scale_px in enumerate(scales):
        for gy in range(G):
            cy = (gy + 0.5) / G * H
            for gx in range(G):
                cx = (gx + 0.5) / G * W
                a = s_idx * G * G + gy * G + gx
                dist2 = (px_x - cx) ** 2 + (px_y - cy) ** 2
                atom = np.exp(-0.5 * dist2 / (scale_px * scale_px))
                norm = np.linalg.norm(atom)
                if norm == 0:
                    raise RuntimeError("Zero-norm P-lin atom")
                A[:, a] = atom / norm
    return A


def _ls_fit(A: np.ndarray, idx: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Least-squares fit of A[:, idx] to y (N-vector), returning N-vector."""
    B = A[:, idx]
    coef, *_ = np.linalg.lstsq(B, y.ravel(), rcond=None)
    fit = B @ coef
    return fit.reshape(y.shape)


def _ls_fit_cols(A: np.ndarray, idx: np.ndarray, Ycols: np.ndarray) -> np.ndarray:
    """Least-squares fit of A[:, idx] to each column of Ycols."""
    B = A[:, idx]
    coef, *_ = np.linalg.lstsq(B, Ycols, rcond=None)
    return B @ coef


def plin_pipeline(
    y: np.ndarray,
    omega: SeedSequence,
    S: int,
    cfg: F0Config,
) -> tuple[np.ndarray, dict]:
    """Forward-stepwise linear regression over the P-lin dictionary.

    Returns the fitted image f and an aux dict with key ``support``,
    a list of chosen atom-index arrays per round.
    """
    A = plin_atoms(cfg)
    resid = y.astype(np.float64, copy=True)
    selected: list[int] = []
    support_history: list[np.ndarray] = []

    n_atoms = A.shape[1]

    for r in range(cfg.plin_rounds):
        rng = omega_rng(omega, 1 + r)
        perm = rng.permutation(n_atoms)

        # First S atoms of perm that are not yet selected.
        selected_set = set(selected)
        cand = []
        for a in perm:
            if a not in selected_set:
                cand.append(a)
            if len(cand) >= S:
                break
        cand = np.asarray(cand, dtype=np.int64)

        scores = np.abs(A[:, cand].T @ resid.ravel())
        order = np.argsort(-scores, kind="stable")
        chosen = np.sort(cand[order[: cfg.births_per_round]])

        support_history.append(chosen.copy())
        selected = list(np.concatenate([np.asarray(selected, dtype=np.int64), chosen]))

        f_cur = _ls_fit(A, np.asarray(selected, dtype=np.int64), y)
        resid = y - f_cur

    return f_cur, {"support": support_history}


def plin_frozen(y: np.ndarray, support: list[np.ndarray], cfg: F0Config) -> np.ndarray:
    """Re-fit on the concatenated support in the same order as plin_pipeline."""
    A = plin_atoms(cfg)
    if not support:
        return np.zeros_like(y, dtype=np.float64)
    full_support = np.concatenate(support)
    return _ls_fit(A, full_support, y)


def plin_frozen_cols(Ycols: np.ndarray, support: list[np.ndarray], cfg: F0Config) -> np.ndarray:
    """Batched least-squares refit on the concatenated support."""
    A = plin_atoms(cfg)
    if not support:
        return np.zeros_like(Ycols, dtype=np.float64)
    full_support = np.concatenate(support)
    return _ls_fit_cols(A, full_support, Ycols)


def plin_rank(support: list[np.ndarray], cfg: F0Config) -> int:
    """Numerical rank of A[:, support] (SVD, rtol 1e-10)."""
    A = plin_atoms(cfg)
    full_support = np.concatenate(support)
    B = A[:, full_support]
    s = np.linalg.svd(B, compute_uv=False)
    if s.size == 0:
        return 0
    threshold = 1e-10 * s.max()
    return int(np.sum(s > threshold))
