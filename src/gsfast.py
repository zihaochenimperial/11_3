"""Fast numpy implementation of the F0 additive Gaussian-sum pipeline (same maths as src/gsfit.py; analytic gradients, hand-written Adam).
MUST NOT import src.synth or src.reference_eval. float64 throughout; no clipping."""
from __future__ import annotations
import time
import numpy as np
from numpy.random import SeedSequence
from scipy.ndimage import gaussian_filter
from src.f0_config import F0Config
from src.omega import omega_rng
from src.gskernel import loss_and_grad_tiled

_GRID = {}


def _grid(H, W):
    k = (H, W)
    if k not in _GRID:
        gx = (np.arange(W, dtype=np.float64) + 0.5) / W
        gy = (np.arange(H, dtype=np.float64) + 0.5) / H
        X, Y = np.meshgrid(gx, gy, indexing='xy')
        _GRID[k] = (X.reshape(-1).copy(), Y.reshape(-1).copy())
    return _GRID[k]


def render_np(xy, logscale, rot, val, H, W):
    X, Y = _grid(H, W)
    dx = (X[None, :] - xy[:, 0:1]) * W
    dy = (Y[None, :] - xy[:, 1:2]) * H
    c = np.cos(rot)[:, None]; s = np.sin(rot)[:, None]
    u = c * dx + s * dy; v = -s * dx + c * dy
    uu = u / np.exp(logscale[:, 0:1]); vv = v / np.exp(logscale[:, 1:2])
    E = np.exp(-0.5 * (uu * uu + vv * vv))
    return (val @ E).reshape(H, W)


def loss_and_grad(xy, logscale, rot, val, y_flat, H, W):
    """loss = mean((f-y)^2); returns (loss, f_flat, grads dict) with analytic gradients."""
    N = H * W
    X, Y = _grid(H, W)
    dx = (X[None, :] - xy[:, 0:1]) * W
    dy = (Y[None, :] - xy[:, 1:2]) * H
    c = np.cos(rot)[:, None]; s = np.sin(rot)[:, None]
    sx = np.exp(logscale[:, 0:1]); sy = np.exp(logscale[:, 1:2])
    uu = (c * dx + s * dy) / sx
    vv = (-s * dx + c * dy) / sy
    E = np.exp(-0.5 * (uu * uu + vv * vv))
    f = val @ E
    r = f - y_flat
    loss = float(np.mean(r * r))
    g = (2.0 / N) * r
    gval = E @ g
    Pq = (-0.5 * val)[:, None] * g[None, :] * E          # dL/dq
    SU = np.einsum('kn,kn->k', Pq, uu); SV = np.einsum('kn,kn->k', Pq, vv)
    A = np.einsum('kn,kn->k', Pq * uu, uu); Bq = np.einsum('kn,kn->k', Pq * vv, vv); Cx = np.einsum('kn,kn->k', Pq * uu, vv)
    sxv = sx[:, 0]; syv = sy[:, 0]; cv = c[:, 0]; sv = s[:, 0]
    sum_a = 2.0 * SU / sxv; sum_b = 2.0 * SV / syv           # sum_n dL/du, dL/dv
    gxy = np.stack([-W * (cv * sum_a - sv * sum_b), -H * (sv * sum_a + cv * sum_b)], axis=1)
    gls = np.stack([-2.0 * A, -2.0 * Bq], axis=1)
    grot = 2.0 * Cx * (syv / sxv - sxv / syv)
    return loss, f, dict(xy=gxy, logscale=gls, rot=grot, val=gval)


class Adam:
    """numpy replica of torch.optim.Adam (lr per group, betas (0.9,0.999), eps 1e-8, no weight decay, no amsgrad)."""
    def __init__(self, params, lrs):
        self.p = params; self.lr = lrs; self.t = 0
        self.m = {k: np.zeros_like(v) for k, v in params.items()}; self.v = {k: np.zeros_like(v) for k, v in params.items()}

    def step(self, grads):
        self.t += 1; b1, b2, eps = 0.9, 0.999, 1e-8
        bc1 = 1 - b1 ** self.t; bc2 = 1 - b2 ** self.t
        for k, p in self.p.items():
            g = grads[k]; m = self.m[k]; v = self.v[k]
            m *= b1; m += (1 - b1) * g
            v *= b2; v += (1 - b2) * g * g
            denom = np.sqrt(v) / np.sqrt(bc2) + eps
            p -= (self.lr[k] / bc1) * (m / denom)


def _run(params, lrs, y_flat, H, W, n):
    opt = Adam(params, lrs)
    for _ in range(n):
        loss, _f, gr = loss_and_grad_tiled(params['xy'], params['logscale'], params['rot'], params['val'], y_flat, H, W, tile=512, want_f=False)
        if not np.isfinite(loss): raise RuntimeError('Non-finite loss encountered: %r' % loss)
        opt.step(gr)
        for p in params.values():
            if not np.isfinite(p).all(): raise RuntimeError('Non-finite parameters after optimizer step')


def _lrs(cfg):
    return dict(xy=cfg.lr_xy, logscale=cfg.lr_logscale, rot=cfg.lr_rot, val=cfg.lr_val)


def _birth_round(y, f_cur, cfg, omega, r, S, forced_idx):
    H, W = cfg.H, cfg.W; N = H * W
    perm = omega_rng(omega, 1 + r).permutation(N); cand = perm[: int(S)]
    sm = gaussian_filter(y - f_cur, sigma=cfg.smooth_sigma_px, mode='reflect')
    if forced_idx is not None:
        chosen = np.asarray(forced_idx, dtype=np.int64)
    else:
        order = np.argsort(-np.abs(sm.ravel()[cand]), kind='stable'); chosen = np.sort(cand[order[: cfg.births_per_round]])
    rows = chosen // W; cols = chosen % W
    new = dict(xy=np.stack([(cols + 0.5) / W, (rows + 0.5) / H], axis=-1), logscale=np.full((len(chosen), 2), np.log(cfg.birth_scale_px)),
               rot=np.zeros(len(chosen)), val=f_cur.ravel()[chosen] + sm.ravel()[chosen])
    return chosen, cand, new


def _init(omega, K, cfg):
    rng = omega_rng(omega, 0); xy = rng.random((K, 2)); val = 0.5 + 0.05 * rng.standard_normal(K)
    return dict(xy=xy.astype(np.float64), logscale=np.full((K, 2), np.log(cfg.init_scale_px)), rot=np.zeros(K), val=val.astype(np.float64))


def fit_pipeline(y, omega, S, cfg, forced_idx=None):
    t0 = time.perf_counter(); H, W = cfg.H, cfg.W; y = np.asarray(y, dtype=np.float64); yf = y.reshape(-1); lrs = _lrs(cfg)
    P = _init(omega, cfg.K0, cfg); init_xy = P['xy'].copy(); init_val = P['val'].copy()
    births, cands = [], []
    _run(P, lrs, yf, H, W, cfg.steps_per_stage)
    for r in range(cfg.birth_rounds):
        f_cur = render_np(P['xy'], P['logscale'], P['rot'], P['val'], H, W)
        chosen, cand, new = _birth_round(y, f_cur, cfg, omega, r, S, None if forced_idx is None else forced_idx[r])
        births.append(chosen.copy()); cands.append(cand.copy())
        P = {k: np.concatenate([P[k], new[k]], axis=0) for k in P}
        _run(P, lrs, yf, H, W, cfg.steps_per_stage)
    f = render_np(P['xy'], P['logscale'], P['rot'], P['val'], H, W)
    if not np.isfinite(f).all(): raise RuntimeError('Non-finite final render output')
    aux = dict(birth_idx=births, cand_idx=cands, init_xy=init_xy, init_val=init_val, xy=P['xy'].copy(), logscale=P['logscale'].copy(), rot=P['rot'].copy(), val=P['val'].copy(), wall_s=time.perf_counter() - t0)
    return f, aux


def fit_no_birth(y, omega, cfg):
    H, W = cfg.H, cfg.W; yf = np.asarray(y, dtype=np.float64).reshape(-1); K = cfg.K0 + cfg.birth_rounds * cfg.births_per_round
    P = _init(omega, K, cfg); _run(P, _lrs(cfg), yf, H, W, (cfg.birth_rounds + 1) * cfg.steps_per_stage)
    f = render_np(P['xy'], P['logscale'], P['rot'], P['val'], H, W)
    if not np.isfinite(f).all(): raise RuntimeError('Non-finite final render output')
    return f
