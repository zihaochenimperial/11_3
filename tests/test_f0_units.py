"""F0 unit-test gate."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import torch
from numpy.random import SeedSequence

from src import df_est, gsfit, plin, synth
from src.f0_config import F0Config
from src.omega import omega_rng


# ---------------------------------------------------------------------------
# 1. Static leakage: gsfit and plin must not import synth or reference_eval.
# ---------------------------------------------------------------------------


def _module_imports(name: str) -> set[str]:
    src_path = Path(__file__).parent.parent / "src" / f"{name}.py"
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
                # `from src import synth` has module 'src' and alias 'synth': record both forms
                for alias in node.names:
                    imported_modules.add(alias.name)
                    imported_modules.add(mod + "." + alias.name)
    return imported_modules


def test_static_leakage_detector_can_fail():
    """Sonnet patch (audit finding): the AST scan must flag all import spellings, otherwise the leakage test cannot fail."""
    for snippet in ("from src import synth", "import src.synth", "from src.synth import make_clean", "from src import reference_eval"):
        tree = ast.parse(snippet)
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module); found |= {a.name for a in node.names}; found |= {node.module + "." + a.name for a in node.names}
        assert found & {"synth", "src.synth", "reference_eval", "src.reference_eval"}, snippet


def test_static_leakage():
    for name in ("gsfit", "plin"):
        mods = _module_imports(name)
        assert "synth" not in mods
        assert "reference_eval" not in mods
        assert "src.synth" not in mods
        assert "src.reference_eval" not in mods


# ---------------------------------------------------------------------------
# 2. Determinism: same y, omega, S -> bitwise-identical output.
# ---------------------------------------------------------------------------


def test_determinism():
    torch.set_num_threads(1)
    cfg = F0Config(steps_per_stage=5)
    x = synth.make_clean("D1", 12345, cfg)
    y = synth.add_noise(x, cfg.sigma0, 999)
    omega = SeedSequence(entropy=42)

    f1, aux1 = gsfit.fit_pipeline(y, omega=omega, S=16, cfg=cfg)
    f2, aux2 = gsfit.fit_pipeline(y, omega=omega, S=16, cfg=cfg)
    assert np.array_equal(f1, f2)
    assert np.array_equal(aux1["xy"], aux2["xy"])
    assert np.array_equal(aux1["logscale"], aux2["logscale"])
    assert np.array_equal(aux1["rot"], aux2["rot"])
    assert np.array_equal(aux1["val"], aux2["val"])

    f_forced, aux_forced = gsfit.fit_pipeline(
        y, omega=omega, S=16, cfg=cfg, forced_idx=aux1["birth_idx"]
    )
    assert np.array_equal(f1, f_forced)

    f_nb1 = gsfit.fit_no_birth(y, omega=omega, cfg=cfg)
    f_nb2 = gsfit.fit_no_birth(y, omega=omega, cfg=cfg)
    assert np.array_equal(f_nb1, f_nb2)


# ---------------------------------------------------------------------------
# 3. S == b uses only omega; nested candidates across S.
# ---------------------------------------------------------------------------


def test_birth_search_independence():
    torch.set_num_threads(1)
    cfg = F0Config(steps_per_stage=5)
    x1 = synth.make_clean("D1", 111, cfg)
    x2 = synth.make_clean("D2", 222, cfg)
    y1 = synth.add_noise(x1, cfg.sigma0, 333)
    y2 = synth.add_noise(x2, cfg.sigma0, 444)
    omega = SeedSequence(entropy=55)

    _, aux1 = gsfit.fit_pipeline(y1, omega=omega, S=cfg.births_per_round, cfg=cfg)
    _, aux2 = gsfit.fit_pipeline(y2, omega=omega, S=cfg.births_per_round, cfg=cfg)
    for a, b in zip(aux1["birth_idx"], aux2["birth_idx"]):
        assert np.array_equal(a, b)

    _, aux3 = gsfit.fit_pipeline(y1, omega=omega, S=64, cfg=cfg)
    _, aux4 = gsfit.fit_pipeline(y2, omega=omega, S=64, cfg=cfg)
    differs = any(
        not np.array_equal(a, b)
        for a, b in zip(aux3["birth_idx"], aux4["birth_idx"])
    )
    assert differs, "S > births_per_round unexpectedly produced identical birth indices"

    # Nested candidates: S1's prefix equals S1's full candidate array.
    _, aux_s8 = gsfit.fit_pipeline(y1, omega=omega, S=8, cfg=cfg)
    for r in range(cfg.birth_rounds):
        assert np.array_equal(aux_s8["cand_idx"][r], aux3["cand_idx"][r][:8])


# ---------------------------------------------------------------------------
# 4. Forced-index replay is bitwise identical for S in {8, 64}.
# ---------------------------------------------------------------------------


def test_forced_idx_replay():
    torch.set_num_threads(1)
    cfg = F0Config(steps_per_stage=5)
    x = synth.make_clean("D1", 777, cfg)
    y = synth.add_noise(x, cfg.sigma0, 888)
    omega = SeedSequence(entropy=99)

    for S in (8, 64):
        f, aux = gsfit.fit_pipeline(y, omega=omega, S=S, cfg=cfg)
        f_forced, aux_forced = gsfit.fit_pipeline(
            y, omega=omega, S=S, cfg=cfg, forced_idx=aux["birth_idx"]
        )
        assert np.array_equal(f, f_forced)
        for a, b in zip(aux["birth_idx"], aux_forced["birth_idx"]):
            assert np.array_equal(a, b)


# ---------------------------------------------------------------------------
# 5. Omega/S independence and birth order.
# ---------------------------------------------------------------------------


def test_omega_s_independence():
    torch.set_num_threads(1)
    cfg = F0Config(steps_per_stage=5)
    x = synth.make_clean("D1", 321, cfg)
    y = synth.add_noise(x, cfg.sigma0, 654)
    omega = SeedSequence(entropy=123)

    _, aux8 = gsfit.fit_pipeline(y, omega=omega, S=8, cfg=cfg)
    _, aux64 = gsfit.fit_pipeline(y, omega=omega, S=64, cfg=cfg)

    assert np.array_equal(aux8["init_xy"], aux64["init_xy"])
    assert np.array_equal(aux8["init_val"], aux64["init_val"])

    for aux in (aux8, aux64):
        for arr in aux["birth_idx"]:
            assert np.all(np.diff(arr) >= 0)


# ---------------------------------------------------------------------------
# 6. Renderer analytic gradient vs finite differences (float64).
# ---------------------------------------------------------------------------


def test_renderer_gradient_fd():
    torch.set_num_threads(1)
    H, W, K = 8, 8, 4
    rng = torch.Generator(device="cpu")
    rng.manual_seed(7)

    xy = torch.rand(K, 2, generator=rng, dtype=torch.float64)
    logscale = torch.randn(K, 2, generator=rng, dtype=torch.float64) * 0.5 + np.log(2.0)
    rot = torch.randn(K, generator=rng, dtype=torch.float64) * 0.3
    val = torch.randn(K, generator=rng, dtype=torch.float64) * 0.2 + 0.5

    def flat_render(params: torch.Tensor) -> torch.Tensor:
        return gsfit.render_flat(params, K, H, W).reshape(-1)

    theta = torch.cat([xy.reshape(-1), logscale.reshape(-1), rot.reshape(-1), val.reshape(-1)])

    J_auto = torch.func.jacrev(flat_render)(theta)

    eps = 1e-7
    J_fd = torch.zeros_like(J_auto)
    for i in range(theta.numel()):
        theta_plus = theta.clone()
        theta_plus[i] += eps
        theta_minus = theta.clone()
        theta_minus[i] -= eps
        J_fd[:, i] = (flat_render(theta_plus) - flat_render(theta_minus)) / (2.0 * eps)

    denom = torch.norm(J_auto) + 1e-12
    rel_err = torch.norm(J_auto - J_fd) / denom
    assert rel_err < 1e-6


# ---------------------------------------------------------------------------
# 7. Hard-threshold toy: covariance df and MC-divergence identity.
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
# 8. GN trace equals rank on a linear toy renderer.
# ---------------------------------------------------------------------------


def test_gn_trace_linear_toy():
    H, W, K = 10, 10, 8
    N = H * W
    D = 6 * K
    r = 5

    rng = torch.Generator(device="cpu")
    rng.manual_seed(123)
    base = torch.randn(N, D, generator=rng, dtype=torch.float64)
    U, s, Vh = torch.linalg.svd(base, full_matrices=False)
    s[:] = 0.0
    s[:r] = 1.0
    A = (U * s) @ Vh

    orig_render_flat = gsfit.render_flat

    def linear_render_flat(theta, K_arg, H_arg, W_arg):
        return (A @ theta).reshape(H_arg, W_arg)

    gsfit.render_flat = linear_render_flat
    try:
        theta = torch.randn(D, dtype=torch.float64)
        trace, rank = df_est.gn_trace(theta, K, H, W, damping=1e-6)
        assert abs(trace - r) < 1e-3
        assert rank == r
    finally:
        gsfit.render_flat = orig_render_flat


# ---------------------------------------------------------------------------
# 9. P-lin: frozen reproduces pipeline, rank, exact coordinate FD.
# ---------------------------------------------------------------------------


def test_plin_frozen_and_rank():
    cfg = F0Config()
    x = synth.make_clean("D1", 111, cfg)
    y = synth.add_noise(x, cfg.sigma0, 222)
    omega = SeedSequence(entropy=333)
    S = 64

    f_pipe, aux = plin.plin_pipeline(y, omega=omega, S=S, cfg=cfg)
    f_frozen = plin.plin_frozen(y, support=aux["support"], cfg=cfg)
    assert np.array_equal(f_pipe, f_frozen)

    rank = plin.plin_rank(aux["support"], cfg=cfg)
    assert rank == 24


def test_plin_exact_coordinate_fd():
    cfg = F0Config()
    x = synth.make_clean("D1", 444, cfg)
    y = synth.add_noise(x, cfg.sigma0, 555)
    omega = SeedSequence(entropy=666)
    S = 256

    _, aux = plin.plin_pipeline(y, omega=omega, S=S, cfg=cfg)
    support = aux["support"]
    rank = plin.plin_rank(support, cfg=cfg)

    N = cfg.H * cfg.W
    eps_f = cfg.eps_frozen_rel * cfg.sigma0
    y_vec = y.ravel()
    Ycols = y_vec[:, None] + eps_f * np.eye(N, dtype=np.float64)
    g_pert = plin.plin_frozen_cols(Ycols, support=support, cfg=cfg)
    g_y = plin.plin_frozen(y, support=support, cfg=cfg).ravel()
    trace_fd = float(np.sum((np.diag(g_pert) - g_y)) / eps_f)
    rel_err = abs(trace_fd - rank) / max(rank, 1.0)
    assert rel_err <= 1e-6


# ---------------------------------------------------------------------------
# 10. Antithetic estimator is unbiased on a linear map.
# ---------------------------------------------------------------------------


def test_antithetic_linear_toy():
    n = 4000
    sigma = 0.08
    N = 64
    rng = np.random.default_rng(2024)
    Hmat = rng.standard_normal((N, N))

    estimates = np.empty(n, dtype=np.float64)
    for i in range(n):
        e = rng.normal(0.0, sigma, size=N)
        x = rng.standard_normal(N)  # arbitrary x, cancels in antithetic form
        f_plus = Hmat @ (x + e)
        f_minus = Hmat @ (x - e)
        estimates[i] = df_est.anti_df(f_plus, f_minus, e, sigma)

    mean_est = float(np.mean(estimates))
    se = float(np.std(estimates, ddof=1) / np.sqrt(n))
    trace_h = float(np.trace(Hmat))
    assert np.abs(mean_est - trace_h) <= 4.0 * se
