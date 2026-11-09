"""Cache-blocked (pixel-tiled) analytic loss+gradient for the F0 additive Gaussian-sum renderer. numpy only, float64, no clipping.
Same maths as gsfast.loss_and_grad (which was verified against torch autograd); all per-tile quantities are tile-local sums, so tiling changes only
the floating-point summation order (~1e-16 relative), not the model. MUST NOT import src.synth or src.reference_eval."""
from __future__ import annotations
import numpy as np

_TILES = {}


def _tiles(H, W, tile):
    k = (H, W, tile)
    if k not in _TILES:
        gx = (np.arange(W, dtype=np.float64) + 0.5) / W
        gy = (np.arange(H, dtype=np.float64) + 0.5) / H
        X, Y = np.meshgrid(gx, gy, indexing='xy')
        px = (X.reshape(-1) * W).copy(); py = (Y.reshape(-1) * H).copy()
        N = H * W
        _TILES[k] = [(a, min(a + tile, N), px[a:min(a + tile, N)].copy(), py[a:min(a + tile, N)].copy()) for a in range(0, N, tile)]
    return _TILES[k]


def loss_and_grad_tiled(xy, logscale, rot, val, y_flat, H, W, tile=512, want_f=True):
    """loss = mean((f-y)^2); returns (loss, f_flat or None, grads dict)."""
    N = H * W; K = val.shape[0]
    c = np.cos(rot); s = np.sin(rot); sx = np.exp(logscale[:, 0]); sy = np.exp(logscale[:, 1])
    x0 = xy[:, 0] * W; y0 = xy[:, 1] * H
    a = (c / sx)[:, None]; b = (s / sx)[:, None]; c0 = (-(c * x0 + s * y0) / sx)[:, None]      # uu = a*px + b*py + c0
    d = (-s / sy)[:, None]; e = (c / sy)[:, None]; f0 = ((s * x0 - c * y0) / sy)[:, None]       # vv = d*px + e*py + f0
    f = np.empty(N) if want_f else None
    loss = 0.0; gval = np.zeros(K); SU = np.zeros(K); SV = np.zeros(K); A = np.zeros(K); Bq = np.zeros(K); Cx = np.zeros(K)
    for lo, hi, px, py in _tiles(H, W, tile):
        uu = a * px + b * py + c0
        vv = d * px + e * py + f0
        E = uu * uu; E += vv * vv; E *= -0.5; np.exp(E, out=E)
        ft = val @ E
        r = ft - y_flat[lo:hi]
        if want_f: f[lo:hi] = ft
        loss += float(r @ r)
        g = (2.0 / N) * r
        gval += E @ g
        E *= g                                    # EG
        Gu = E * uu; Gv = E * vv
        SU += Gu.sum(axis=1); SV += Gv.sum(axis=1)
        A += np.einsum('kt,kt->k', Gu, uu); Cx += np.einsum('kt,kt->k', Gu, vv); Bq += np.einsum('kt,kt->k', Gv, vv)
    loss /= N
    h = -0.5 * val                                 # Pq = h * EG
    SU *= h; SV *= h; A *= h; Bq *= h; Cx *= h
    sum_a = 2.0 * SU / sx; sum_b = 2.0 * SV / sy
    gxy = np.stack([-W * (c * sum_a - s * sum_b), -H * (s * sum_a + c * sum_b)], axis=1)
    gls = np.stack([-2.0 * A, -2.0 * Bq], axis=1)
    grot = 2.0 * Cx * (sy / sx - sx / sy)
    return loss, f, dict(xy=gxy, logscale=gls, rot=grot, val=gval)
