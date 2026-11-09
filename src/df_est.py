"""Degrees-of-freedom estimators and MC divergence for F0."""

from __future__ import annotations

from typing import Callable

import numpy as np
import torch
from scipy.integrate import quad
from scipy.stats import norm

from src import gsfit


def oracle_df(F: np.ndarray, E: np.ndarray, sigma: float) -> float:
    """Oracle covariance df.

    F, E have shape (M, N).  F[m, i] = f_i^m, E[m, i] = e_i^m.
    Returns (1/(M sigma^2)) sum_i sum_m (F[m,i] - mean_m F[:,i]) E[m,i].
    """
    F64 = np.asarray(F, dtype=np.float64)
    E64 = np.asarray(E, dtype=np.float64)
    M = F64.shape[0]
    Fbar = F64.mean(axis=0, keepdims=True)
    cov_term = float(np.sum((F64 - Fbar) * E64))
    return cov_term / (M * sigma * sigma)


def bootstrap_se(F: np.ndarray, E: np.ndarray, sigma: float, B: int, seed: int) -> float:
    """Bootstrap standard error of oracle_df over the M axis."""
    F64 = np.asarray(F, dtype=np.float64)
    E64 = np.asarray(E, dtype=np.float64)
    M = F64.shape[0]
    rng = np.random.default_rng(seed)
    estimates = np.empty(B, dtype=np.float64)
    for b in range(B):
        idx = rng.integers(0, M, size=M)
        estimates[b] = oracle_df(F64[idx], E64[idx], sigma)
    return float(estimates.std(ddof=1))


def fd_divergence(
    g_fn: Callable[[np.ndarray], np.ndarray],
    y: np.ndarray,
    base: np.ndarray,
    eps_f: float,
    b: np.ndarray,
) -> float:
    """Forward finite-difference divergence: sum(b * (g(y+eps_f*b) - base))/eps_f."""
    y64 = np.asarray(y, dtype=np.float64)
    b64 = np.asarray(b, dtype=np.float64)
    f_yp = np.asarray(g_fn(y64 + eps_f * b64), dtype=np.float64)
    return float(np.sum(b64 * (f_yp - base)) / eps_f)


def anti_df(f_plus: np.ndarray, f_minus: np.ndarray, e: np.ndarray, sigma: float) -> float:
    """Antithetic divergence estimator.

    f_plus = f(x + e), f_minus = f(x - e).  Returns
    sum((f_plus - f_minus) * e) / (2 sigma^2).
    """
    diff = np.asarray(f_plus - f_minus, dtype=np.float64).ravel()
    e64 = np.asarray(e, dtype=np.float64).ravel()
    return float(np.sum(diff * e64) / (2.0 * sigma * sigma))


def gn_trace(
    theta: np.ndarray,
    K: int,
    H: int,
    W: int,
    damping: float = 1e-6,
) -> tuple[float, int]:
    """Gauss-Newton hat-matrix trace and numerical rank at theta.

    trace = tr( J (J^T J + lam I)^-1 J^T ) with
    lam = damping * tr(J^T J) / dim.
    """
    theta_t = torch.as_tensor(theta, dtype=torch.float64, device="cpu")
    theta_t.requires_grad_(True)

    def flat_render(th: torch.Tensor) -> torch.Tensor:
        return gsfit.render_flat(th, K, H, W).reshape(-1)

    J = torch.func.jacrev(flat_render)(theta_t)  # (H*W, 6K)
    JtJ = J.T @ J
    dim = JtJ.shape[0]
    lam = damping * torch.trace(JtJ) / dim
    inv = torch.linalg.inv(JtJ + lam * torch.eye(dim, device=J.device, dtype=J.dtype))
    trace_val = float(torch.trace(JtJ @ inv).item())

    s = torch.linalg.svdvals(J)
    s_max = s.max().item()
    rank = int((s / s_max > 1e-6).sum().item())
    return trace_val, rank


def bootstrap_slope(
    log2S: np.ndarray,
    values: np.ndarray,
    B: int,
    seed: int,
) -> tuple[float, float]:
    """Bootstrap slope of values vs log2S.

    Returns (slope, one-sided 95% CI lower bound).
    """
    x = np.asarray(log2S, dtype=np.float64)
    y = np.asarray(values, dtype=np.float64)
    n = x.shape[0]
    slope0 = float(np.polyfit(x, y, 1)[0])

    rng = np.random.default_rng(seed)
    slopes = np.empty(B, dtype=np.float64)
    for b in range(B):
        idx = rng.integers(0, n, size=n)
        slopes[b] = np.polyfit(x[idx], y[idx], 1)[0]
    ci_low = float(np.percentile(slopes, 5.0))
    return slope0, ci_low


# ---------------------------------------------------------------------------
# 1-D hard-threshold toy helpers for unit tests.
# ---------------------------------------------------------------------------


def hard_threshold(y: np.ndarray, lam: float) -> np.ndarray:
    """f(y) = y if |y| > lam, else 0."""
    y_arr = np.asarray(y, dtype=np.float64)
    return np.where(np.abs(y_arr) > lam, y_arr, 0.0)


def hard_threshold_df(mu: float, sigma: float, lam: float) -> float:
    """(1/sigma^2) Cov(f(y), y) for y ~ N(mu, sigma^2), f = hard_threshold."""

    def f_integrand(y: float) -> float:
        if abs(y) > lam:
            return y * norm.pdf(y, loc=mu, scale=sigma)
        return 0.0

    def fy_integrand(y: float) -> float:
        if abs(y) > lam:
            return y * y * norm.pdf(y, loc=mu, scale=sigma)
        return 0.0

    Ef, _ = quad(f_integrand, -np.inf, np.inf, limit=200)
    Efy, _ = quad(fy_integrand, -np.inf, np.inf, limit=200)
    cov = Efy - Ef * mu
    return float(cov / (sigma * sigma))
