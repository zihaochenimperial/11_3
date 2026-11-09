"""F0 unit-test gate."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import torch

from src import df_est, gsfit, synth
from src.f0_config import F0Config


# ---------------------------------------------------------------------------
# 1. Static leakage: gsfit must not import synth or reference_eval.
# ---------------------------------------------------------------------------


def test_static_leakage():
    src_path = Path(__file__).parent.parent / "src" / "gsfit.py"
    tree = ast.parse(src_path.read_text(encoding="utf-8"))
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module
            if mod:
                imported_modules.add(mod)
    assert "synth" not in imported_modules
    assert "reference_eval" not in imported_modules
    assert "src.synth" not in imported_modules
    assert "src.reference_eval" not in imported_modules


# ---------------------------------------------------------------------------
# 2. Determinism: same y, omega, S -> bitwise-identical output.
# ---------------------------------------------------------------------------


def test_determinism():
    torch.set_num_threads(1)
    cfg = F0Config(steps_per_stage=5)
    x = synth.make_clean("D1", 12345, cfg)
    y = synth.add_noise(x, cfg.sigma0, 999)
    f1, aux1 = gsfit.fit_pipeline(y, omega=42, S=16, cfg=cfg)
    f2, aux2 = gsfit.fit_pipeline(y, omega=42, S=16, cfg=cfg)
    assert np.array_equal(f1, f2)
    assert np.array_equal(aux1["xy"], aux2["xy"])
    assert np.array_equal(aux1["logscale"], aux2["logscale"])
    assert np.array_equal(aux1["rot"], aux2["rot"])
    assert np.array_equal(aux1["val"], aux2["val"])


# ---------------------------------------------------------------------------
# 3. Search independence: S == b uses only omega; S > b can depend on y.
# ---------------------------------------------------------------------------


def test_birth_search_independence():
    torch.set_num_threads(1)
    cfg = F0Config(steps_per_stage=5)
    x1 = synth.make_clean("D1", 111, cfg)
    x2 = synth.make_clean("D2", 222, cfg)
    y1 = synth.add_noise(x1, cfg.sigma0, 333)
    y2 = synth.add_noise(x2, cfg.sigma0, 444)
    omega = 55

    _, aux1 = gsfit.fit_pipeline(y1, omega=omega, S=cfg.births_per_round, cfg=cfg)
    _, aux2 = gsfit.fit_pipeline(y2, omega=omega, S=cfg.births_per_round, cfg=cfg)
    for a, b in zip(aux1["birth_idx"], aux2["birth_idx"]):
        assert np.array_equal(a, b)

    _, aux3 = gsfit.fit_pipeline(y1, omega=omega, S=256, cfg=cfg)
    _, aux4 = gsfit.fit_pipeline(y2, omega=omega, S=256, cfg=cfg)
    differs = any(
        not np.array_equal(a, b)
        for a, b in zip(aux3["birth_idx"], aux4["birth_idx"])
    )
    assert differs, "S > births_per_round unexpectedly produced identical birth indices"


# ---------------------------------------------------------------------------
# 4. Renderer analytic gradient vs finite differences.
# ---------------------------------------------------------------------------


def test_renderer_gradient_fd():
    torch.set_num_threads(1)
    H, W, K, topk = 8, 8, 4, 2
    rng = torch.Generator(device="cpu")
    rng.manual_seed(7)

    xy = torch.rand(K, 2, generator=rng, dtype=torch.float64)
    logscale = torch.randn(K, 2, generator=rng, dtype=torch.float64) * 0.5 + np.log(2.0)
    rot = torch.randn(K, generator=rng, dtype=torch.float64) * 0.3
    val = torch.randn(K, generator=rng, dtype=torch.float64) * 0.2 + 0.5

    def flat_render(params: torch.Tensor) -> torch.Tensor:
        return gsfit.render_flat(params, K, H, W, topk).reshape(-1)

    theta = torch.cat([xy.reshape(-1), logscale.reshape(-1), rot.reshape(-1), val.reshape(-1)])

    J_auto = torch.func.jacrev(flat_render)(theta)

    eps = 1e-6
    J_fd = torch.zeros_like(J_auto)
    for i in range(theta.numel()):
        theta_plus = theta.clone()
        theta_plus[i] += eps
        theta_minus = theta.clone()
        theta_minus[i] -= eps
        J_fd[:, i] = (flat_render(theta_plus) - flat_render(theta_minus)) / (2.0 * eps)

    denom = torch.norm(J_auto) + 1e-12
    rel_err = torch.norm(J_auto - J_fd) / denom
    assert rel_err < 1e-4


# ---------------------------------------------------------------------------
# 5. Hard-threshold toy: covariance df and MC-divergence identity.
# ---------------------------------------------------------------------------


def test_hard_threshold_toy():
    sigma = 1.0
    lam = 1.0
    n = 400_000

    for mu in (0.0, 0.7):
        # Direct covariance df at noise level sigma.
        rng = np.random.default_rng(2024 + int(mu * 100))
        y = rng.normal(mu, sigma, size=n)
        f_y = df_est.hard_threshold(y, lam)
        cov_mc = np.mean(f_y * y) - np.mean(f_y) * mu
        df_mc = cov_mc / (sigma ** 2)
        df_theory = df_est.hard_threshold_df(mu, sigma, lam)
        se_df = np.sqrt(np.var(f_y * (y - mu), ddof=1) / n) / (sigma ** 2)
        assert np.abs(df_mc - df_theory) <= 4.0 * se_df

        for eps in (0.1, 0.5, 1.0):
            rng = np.random.default_rng(2024 + int(mu * 100) + int(eps * 1000))
            y = rng.normal(mu, sigma, size=n)
            b = rng.normal(0.0, 1.0, size=n)
            div_samples = b * (
                df_est.hard_threshold(y + eps * b, lam) - df_est.hard_threshold(y, lam)
            ) / eps
            div_mean = float(np.mean(div_samples))
            sigma_p = np.sqrt(sigma ** 2 + eps ** 2)
            df_at_sp = df_est.hard_threshold_df(mu, sigma_p, lam)
            se_div = np.std(div_samples, ddof=1) / np.sqrt(n)
            assert np.abs(div_mean - df_at_sp) <= 4.0 * se_div


# ---------------------------------------------------------------------------
# 6. GN trace equals rank on a linear toy renderer.
# ---------------------------------------------------------------------------


def test_gn_trace_linear_toy():
    H, W, K, topk = 10, 10, 8, 4
    N = H * W
    D = 6 * K
    r = 5

    rng = torch.Generator(device="cpu")
    rng.manual_seed(123)
    base = torch.randn(N, D, generator=rng, dtype=torch.float32)
    U, s, Vh = torch.linalg.svd(base, full_matrices=False)
    s[:] = 0.0
    s[:r] = 1.0
    A = (U * s) @ Vh

    orig_render_flat = gsfit.render_flat

    def linear_render_flat(theta, K_arg, H_arg, W_arg, topk_arg):
        return (A @ theta).reshape(H_arg, W_arg)

    gsfit.render_flat = linear_render_flat
    try:
        theta = torch.randn(D, dtype=torch.float32)
        trace, rank = df_est.gn_trace(theta, K, H, W, topk, damping=1e-6)
        assert abs(trace - r) < 1e-3
        assert rank == r
    finally:
        gsfit.render_flat = orig_render_flat
