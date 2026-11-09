"""Gaussian splatting fitting pipeline for F0.

MUST NOT import src.synth or src.reference_eval.
"""

from __future__ import annotations

import time
from typing import List

import numpy as np
import torch
from scipy.ndimage import gaussian_filter

from src.f0_config import F0Config


def _pixel_centers(H: int, W: int, device: torch.device | str) -> tuple[torch.Tensor, torch.Tensor]:
    """Normalized pixel-center grids X, Y of shape (H, W)."""
    grid_x = (torch.arange(W, dtype=torch.float32, device=device) + 0.5) / W
    grid_y = (torch.arange(H, dtype=torch.float32, device=device) + 0.5) / H
    return torch.meshgrid(grid_x, grid_y, indexing="xy")


def _covariance_inv(logscale: torch.Tensor, rot: torch.Tensor, H: int, W: int) -> torch.Tensor:
    """Compute Sigma^-1 in normalized coordinates for each Gaussian.

    logscale: (K, 2), log std in pixels along the two rotated axes.
    rot:      (K,), rotation angle in radians.
    Returns   (K, 2, 2).
    """
    std_px = torch.exp(logscale)
    wh = torch.tensor([W, H], dtype=std_px.dtype, device=std_px.device).unsqueeze(0)
    std_norm = std_px / wh
    inv_var = 1.0 / (std_norm * std_norm + 1e-12)

    c = torch.cos(rot)
    s = torch.sin(rot)
    a = c * c * inv_var[:, 0] + s * s * inv_var[:, 1]
    b = c * s * (inv_var[:, 0] - inv_var[:, 1])
    d = s * s * inv_var[:, 0] + c * c * inv_var[:, 1]

    row0 = torch.stack([a, b], dim=-1)
    row1 = torch.stack([b, d], dim=-1)
    return torch.stack([row0, row1], dim=-2)


def render(
    xy: torch.Tensor,
    logscale: torch.Tensor,
    rot: torch.Tensor,
    val: torch.Tensor,
    H: int,
    W: int,
    topk: int,
) -> torch.Tensor:
    """Render K anisotropic Gaussians with top-k normalization per pixel.

    xy:        (K, 2), normalized [0, 1] coordinates as (x, y).
    logscale:  (K, 2), log std in pixels along rotated axes.
    rot:       (K,), rotation in radians.
    val:       (K,), gray values.
    Returns    (H, W) float32 render.
    """
    K = xy.shape[0]
    X, Y = _pixel_centers(H, W, device=xy.device)

    # d: (H, W, K, 2)
    d = torch.stack(
        [X.unsqueeze(-1) - xy[:, 0].view(1, 1, K),
         Y.unsqueeze(-1) - xy[:, 1].view(1, 1, K)],
        dim=-1,
    )
    Sigma_inv = _covariance_inv(logscale, rot, H, W)  # (K, 2, 2)

    # mahalanobis: d^T Sigma^-1 d, shape (H, W, K)
    d_col = d.unsqueeze(-1)  # (H, W, K, 2, 1)
    m = torch.matmul(Sigma_inv.unsqueeze(0).unsqueeze(0), d_col)
    mahal = (d_col * m).sum(dim=(-2, -1))

    w = torch.exp(-0.5 * mahal)
    k = min(topk, K)
    topk_w, topk_idx = torch.topk(w, k, dim=-1, largest=True, sorted=True)
    topk_val = val[topk_idx]  # (H, W, k)
    denom = topk_w.sum(dim=-1) + 1e-8
    return (topk_w * topk_val).sum(dim=-1) / denom


def render_flat(theta: torch.Tensor, K: int, H: int, W: int, topk: int) -> torch.Tensor:
    """Render from a flat parameter vector.

    Layout: xy(2K), logscale(2K), rot(K), val(K).
    """
    xy = theta[: 2 * K].reshape(K, 2)
    logscale = theta[2 * K : 4 * K].reshape(K, 2)
    rot = theta[4 * K : 5 * K]
    val = theta[5 * K : 6 * K]
    return render(xy, logscale, rot, val, H, W, topk)


def pack(aux: dict) -> torch.Tensor:
    """Pack auxiliary parameter dict into a flat torch vector."""
    parts = [
        torch.as_tensor(aux["xy"], dtype=torch.float32).reshape(-1),
        torch.as_tensor(aux["logscale"], dtype=torch.float32).reshape(-1),
        torch.as_tensor(aux["rot"], dtype=torch.float32).reshape(-1),
        torch.as_tensor(aux["val"], dtype=torch.float32).reshape(-1),
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


def fit_pipeline(
    y: np.ndarray,
    omega: int,
    S: int,
    cfg: F0Config,
) -> tuple[np.ndarray, dict]:
    """Fit an adaptive Gaussian mixture to a noisy image y.

    Parameters
    ----------
    y:     (H, W) noisy observation.
    omega: seed for the fitting RNG (torch.Generator on CPU).
    S:     number of birth candidates sampled per round.
    cfg:   F0Config instance.

    Returns
    -------
    f:   (H, W) float32 numpy render.
    aux: dict with keys 'xy', 'logscale', 'rot', 'val', 'birth_idx', 'wall_s'.
    """
    t0 = time.perf_counter()
    H, W = cfg.H, cfg.W
    device = torch.device("cpu")
    dtype = torch.float32
    y_t = torch.as_tensor(y, dtype=dtype, device=device)
    gen = torch.Generator(device=device)
    gen.manual_seed(int(omega))

    K = cfg.K0
    xy = torch.rand(K, 2, generator=gen, device=device, dtype=dtype)
    logscale = torch.full((K, 2), float(np.log(cfg.init_scale_px)), device=device, dtype=dtype)
    rot = torch.zeros(K, device=device, dtype=dtype)
    val = 0.5 + 0.05 * torch.randn(K, generator=gen, device=device, dtype=dtype)

    params = [xy, logscale, rot, val]
    for p in params:
        p.requires_grad_(True)
    optimizer = _create_adam(xy, logscale, rot, val, cfg)

    birth_idx_history: List[np.ndarray] = []

    def run_steps(n: int) -> None:
        for _ in range(n):
            optimizer.zero_grad()
            f = render(xy, logscale, rot, val, H, W, cfg.topk)
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

    run_steps(cfg.steps_per_stage)

    for _ in range(cfg.birth_rounds):
        with torch.no_grad():
            f_current = render(xy, logscale, rot, val, H, W, cfg.topk)
            residual = (y_t - f_current).cpu().numpy()
            smoothed_res = gaussian_filter(residual, sigma=cfg.smooth_sigma_px, mode="reflect")
            smoothed_res_t = torch.as_tensor(smoothed_res, dtype=dtype, device=device)

        N = H * W
        S_eff = min(int(S), N)
        perm = torch.randperm(N, generator=gen, device=device)
        sampled_flat = perm[:S_eff]

        scores = torch.abs(smoothed_res_t.flatten()[sampled_flat])
        bpr = cfg.births_per_round
        if S_eff <= bpr:
            chosen = sampled_flat
        else:
            _, top_local = torch.topk(scores, bpr, largest=True, sorted=True)
            chosen = sampled_flat[top_local]

        rows = chosen // W
        cols = chosen % W
        birth_idx_history.append(chosen.cpu().numpy().copy())

        # New Gaussians at pixel centers.
        new_xy = torch.stack(
            [(cols.float() + 0.5) / W, (rows.float() + 0.5) / H], dim=-1
        )
        new_logscale = torch.full(
            (len(chosen), 2), float(np.log(cfg.birth_scale_px)), device=device, dtype=dtype
        )
        new_rot = torch.zeros(len(chosen), device=device, dtype=dtype)
        new_val = f_current.flatten()[chosen] + smoothed_res_t.flatten()[chosen]

        xy = torch.cat([xy.detach(), new_xy], dim=0)
        logscale = torch.cat([logscale.detach(), new_logscale], dim=0)
        rot = torch.cat([rot.detach(), new_rot], dim=0)
        val = torch.cat([val.detach(), new_val], dim=0)

        xy.requires_grad_(True)
        logscale.requires_grad_(True)
        rot.requires_grad_(True)
        val.requires_grad_(True)
        params = [xy, logscale, rot, val]
        optimizer = _create_adam(xy, logscale, rot, val, cfg)

        run_steps(cfg.steps_per_stage)

    with torch.no_grad():
        f_final = render(xy, logscale, rot, val, H, W, cfg.topk)

    if not torch.isfinite(f_final).all():
        raise RuntimeError("Non-finite final render output")

    aux = {
        "xy": xy.detach().cpu().numpy(),
        "logscale": logscale.detach().cpu().numpy(),
        "rot": rot.detach().cpu().numpy(),
        "val": val.detach().cpu().numpy(),
        "birth_idx": birth_idx_history,
        "wall_s": time.perf_counter() - t0,
    }
    return f_final.cpu().numpy(), aux
