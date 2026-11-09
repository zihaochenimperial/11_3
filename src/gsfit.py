"""Gaussian splatting fitting pipeline for F0.

MUST NOT import src.synth or src.reference_eval.
"""

from __future__ import annotations

import time
from typing import List

import numpy as np
import torch
from numpy.random import SeedSequence
from scipy.ndimage import gaussian_filter

from src.f0_config import F0Config
from src.omega import omega_rng


def _pixel_centers(H: int, W: int, device: torch.device | str) -> tuple[torch.Tensor, torch.Tensor]:
    """Normalized pixel-center grids X, Y of shape (H, W)."""
    grid_x = (torch.arange(W, dtype=torch.float64, device=device) + 0.5) / W
    grid_y = (torch.arange(H, dtype=torch.float64, device=device) + 0.5) / H
    return torch.meshgrid(grid_x, grid_y, indexing="xy")


def render(
    xy: torch.Tensor,
    logscale: torch.Tensor,
    rot: torch.Tensor,
    val: torch.Tensor,
    H: int,
    W: int,
) -> torch.Tensor:
    """Render K anisotropic Gaussians additively in pixel units.

    For each pixel p (in normalised coordinates) and Gaussian k,
    the offset in pixels is ``(p - centre_k) * (W, H)``.  This is
    rotated by ``-rot_k`` to obtain ``(u, v)``.  The exponent is
    ``-0.5 * ((u / sx)**2 + (v / sy)**2)`` with ``sx, sy = exp(logscale)``.
    The output is the sum over all Gaussians of ``val_k * exp(-0.5 q_k)``.

    No top-k selection, no normalisation, no clamping.
    """
    K = xy.shape[0]
    X, Y = _pixel_centers(H, W, device=xy.device)

    # Pixel-unit offsets, shape (H, W, K).
    dx_px = (X.unsqueeze(-1) - xy[:, 0].view(1, 1, K)) * W
    dy_px = (Y.unsqueeze(-1) - xy[:, 1].view(1, 1, K)) * H

    # Rotate by -rot: [u; v] = [cos  sin; -sin  cos] * [dx; dy].
    c = torch.cos(rot)
    s = torch.sin(rot)
    u = c * dx_px + s * dy_px
    v = -s * dx_px + c * dy_px

    sx = torch.exp(logscale[:, 0])
    sy = torch.exp(logscale[:, 1])
    q = (u / sx) ** 2 + (v / sy) ** 2

    w = torch.exp(-0.5 * q)  # (H, W, K)
    f = (w * val).sum(dim=-1)  # (H, W)
    return f


def render_flat(theta: torch.Tensor, K: int, H: int, W: int) -> torch.Tensor:
    """Render from a flat parameter vector.

    Layout: xy(2K), logscale(2K), rot(K), val(K).
    """
    xy = theta[: 2 * K].reshape(K, 2)
    logscale = theta[2 * K : 4 * K].reshape(K, 2)
    rot = theta[4 * K : 5 * K]
    val = theta[5 * K : 6 * K]
    return render(xy, logscale, rot, val, H, W)


def pack(aux: dict) -> torch.Tensor:
    """Pack auxiliary parameter dict into a flat torch vector."""
    parts = [
        torch.as_tensor(aux["xy"], dtype=torch.float64).reshape(-1),
        torch.as_tensor(aux["logscale"], dtype=torch.float64).reshape(-1),
        torch.as_tensor(aux["rot"], dtype=torch.float64).reshape(-1),
        torch.as_tensor(aux["val"], dtype=torch.float64).reshape(-1),
    ]
    return torch.cat(parts)


def _create_adam(
    xy: torch.Tensor,
    logscale: torch.Tensor,
    rot: torch.Tensor,
    val: torch.Tensor,
    cfg: F0Config,
) -> torch.optim.Adam:
    return torch.optim.Adam(
        [
            {"params": [xy], "lr": cfg.lr_xy},
            {"params": [logscale], "lr": cfg.lr_logscale},
            {"params": [rot], "lr": cfg.lr_rot},
            {"params": [val], "lr": cfg.lr_val},
        ]
    )


def _run_steps(
    optimizer: torch.optim.Adam,
    xy: torch.Tensor,
    logscale: torch.Tensor,
    rot: torch.Tensor,
    val: torch.Tensor,
    y_t: torch.Tensor,
    H: int,
    W: int,
    n: int,
) -> None:
    params = [xy, logscale, rot, val]
    for _ in range(n):
        optimizer.zero_grad()
        f = render(xy, logscale, rot, val, H, W)
        loss = ((f - y_t) ** 2).mean()
        if not torch.isfinite(loss):
            raise RuntimeError(f"Non-finite loss encountered: {loss.item()}")
        loss.backward()
        optimizer.step()
        for p in params:
            if not torch.isfinite(p).all():
                raise RuntimeError("Non-finite parameters after optimizer step")
        if not torch.isfinite(f).all():
            raise RuntimeError("Non-finite render output")


def _birth_round(
    y: np.ndarray,
    f_cur: np.ndarray,
    cfg: F0Config,
    omega: SeedSequence,
    r: int,
    S: int,
    forced_idx: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Choose and build one round of new Gaussians.

    Returns
    -------
    chosen : ascending int64 pixel indices
    cand : candidate permutation prefix
    new_params : dict with keys xy, logscale, rot, val (torch tensors)
    """
    H, W = cfg.H, cfg.W
    N = H * W
    rng = omega_rng(omega, 1 + r)
    perm = rng.permutation(N)
    cand = perm[: int(S)]

    residual = y - f_cur
    smoothed_res = gaussian_filter(residual, sigma=cfg.smooth_sigma_px, mode="reflect")

    if forced_idx is not None:
        chosen = np.asarray(forced_idx, dtype=np.int64)
    else:
        scores = np.abs(smoothed_res.ravel()[cand])
        order = np.argsort(-scores, kind="stable")
        bpr = cfg.births_per_round
        chosen = np.sort(cand[order[:bpr]])

    rows = chosen // W
    cols = chosen % W

    new_xy_np = np.stack([(cols + 0.5) / W, (rows + 0.5) / H], axis=-1)
    new_logscale_np = np.full((len(chosen), 2), np.log(cfg.birth_scale_px), dtype=np.float64)
    new_rot_np = np.zeros(len(chosen), dtype=np.float64)
    f_flat = f_cur.ravel()
    s_flat = smoothed_res.ravel()
    new_val_np = f_flat[chosen] + s_flat[chosen]

    device = torch.device("cpu")
    new_params = {
        "xy": torch.as_tensor(new_xy_np, dtype=torch.float64, device=device),
        "logscale": torch.as_tensor(new_logscale_np, dtype=torch.float64, device=device),
        "rot": torch.as_tensor(new_rot_np, dtype=torch.float64, device=device),
        "val": torch.as_tensor(new_val_np, dtype=torch.float64, device=device),
    }
    return chosen, cand, new_params


def fit_pipeline(
    y: np.ndarray,
    omega: SeedSequence,
    S: int,
    cfg: F0Config,
    forced_idx: list[np.ndarray] | None = None,
) -> tuple[np.ndarray, dict]:
    """Fit an adaptive Gaussian mixture to a noisy image y.

    Parameters
    ----------
    y:     (H, W) noisy observation, float64.
    omega: SeedSequence controlling init and permutation streams.
    S:     number of birth candidates sampled per round.
    cfg:   F0Config instance.
    forced_idx: optional list of birth_rounds ascending int64 arrays.
                When given, the birth topology is frozen; value
                initialisation still depends on y through the current
                render and smoothed residual.

    Returns
    -------
    f:   (H, W) float64 numpy render.
    aux: dict with parameter arrays, birth indices and timing.
    """
    t0 = time.perf_counter()
    H, W = cfg.H, cfg.W
    device = torch.device("cpu")
    y_t = torch.as_tensor(y, dtype=torch.float64, device=device)

    # Init stream j=0: xy first, then val.
    rng_init = omega_rng(omega, 0)
    K0 = cfg.K0
    xy_np = rng_init.random((K0, 2))
    val_np = 0.5 + 0.05 * rng_init.standard_normal(K0)

    xy = torch.as_tensor(xy_np, dtype=torch.float64, device=device)
    logscale = torch.full((K0, 2), np.log(cfg.init_scale_px), dtype=torch.float64, device=device)
    rot = torch.zeros(K0, dtype=torch.float64, device=device)
    val = torch.as_tensor(val_np, dtype=torch.float64, device=device)

    for p in (xy, logscale, rot, val):
        p.requires_grad_(True)
    optimizer = _create_adam(xy, logscale, rot, val, cfg)

    init_xy = xy.detach().cpu().numpy().copy()
    init_val = val.detach().cpu().numpy().copy()

    birth_idx_history: List[np.ndarray] = []
    cand_idx_history: List[np.ndarray] = []

    _run_steps(optimizer, xy, logscale, rot, val, y_t, H, W, cfg.steps_per_stage)

    for r in range(cfg.birth_rounds):
        with torch.no_grad():
            f_current = render(xy, logscale, rot, val, H, W)
        f_cur = f_current.detach().cpu().numpy()

        forced_r = forced_idx[r] if forced_idx is not None else None
        chosen, cand, new_params = _birth_round(
            y, f_cur, cfg, omega, r, S, forced_r
        )
        birth_idx_history.append(chosen.copy())
        cand_idx_history.append(cand.copy())

        xy = torch.cat([xy.detach(), new_params["xy"]], dim=0)
        logscale = torch.cat([logscale.detach(), new_params["logscale"]], dim=0)
        rot = torch.cat([rot.detach(), new_params["rot"]], dim=0)
        val = torch.cat([val.detach(), new_params["val"]], dim=0)

        for p in (xy, logscale, rot, val):
            p.requires_grad_(True)
        optimizer = _create_adam(xy, logscale, rot, val, cfg)
        _run_steps(optimizer, xy, logscale, rot, val, y_t, H, W, cfg.steps_per_stage)

    with torch.no_grad():
        f_final = render(xy, logscale, rot, val, H, W)
    if not torch.isfinite(f_final).all():
        raise RuntimeError("Non-finite final render output")

    aux = {
        "birth_idx": birth_idx_history,
        "cand_idx": cand_idx_history,
        "init_xy": init_xy,
        "init_val": init_val,
        "xy": xy.detach().cpu().numpy(),
        "logscale": logscale.detach().cpu().numpy(),
        "rot": rot.detach().cpu().numpy(),
        "val": val.detach().cpu().numpy(),
        "wall_s": time.perf_counter() - t0,
    }
    return f_final.detach().cpu().numpy(), aux


def fit_no_birth(y: np.ndarray, omega: SeedSequence, cfg: F0Config) -> np.ndarray:
    """Control N0: K=48 random init, same total steps, no births."""
    H, W = cfg.H, cfg.W
    device = torch.device("cpu")
    y_t = torch.as_tensor(y, dtype=torch.float64, device=device)

    rng_init = omega_rng(omega, 0)
    K = cfg.K0 + cfg.birth_rounds * cfg.births_per_round
    xy_np = rng_init.random((K, 2))
    val_np = 0.5 + 0.05 * rng_init.standard_normal(K)

    xy = torch.as_tensor(xy_np, dtype=torch.float64, device=device)
    logscale = torch.full((K, 2), np.log(cfg.init_scale_px), dtype=torch.float64, device=device)
    rot = torch.zeros(K, dtype=torch.float64, device=device)
    val = torch.as_tensor(val_np, dtype=torch.float64, device=device)

    for p in (xy, logscale, rot, val):
        p.requires_grad_(True)
    optimizer = _create_adam(xy, logscale, rot, val, cfg)

    total_steps = (cfg.birth_rounds + 1) * cfg.steps_per_stage
    _run_steps(optimizer, xy, logscale, rot, val, y_t, H, W, total_steps)

    with torch.no_grad():
        f_final = render(xy, logscale, rot, val, H, W)
    if not torch.isfinite(f_final).all():
        raise RuntimeError("Non-finite final render output")
    return f_final.detach().cpu().numpy()
