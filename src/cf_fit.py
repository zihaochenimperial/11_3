"""CF-birth utilities (new line; contract CF0, not yet frozen). Does NOT modify the frozen F0/F3 code: imports gsfast internals.
trajectory(): same maths as gsfast.fit_pipeline but runs R_max birth rounds and returns the render after every stage (snapshot R == pipeline with birth_rounds=R, bitwise).
fission_copies(): Gaussian data fission y_f = y + tau z, y_g = y - z/tau (z ~ N(0, sigma0^2) independent of the noise in y) -> independent copies.
MUST NOT import src.synth or src.reference_eval (clean image never enters fitting)."""
from __future__ import annotations
import time
import numpy as np
from src import gsfast as G


def fission_copies(y, z, tau):
    """y_f = y + tau*z (selection copy), y_g = y - z/tau (fit copy). Independent when y = x + e, e ~ N(0,s0^2 I), z ~ N(0,s0^2 I) independent of e."""
    y = np.asarray(y, dtype=np.float64); z = np.asarray(z, dtype=np.float64)
    return y + tau * z, y - z / tau


def trajectory(y, omega, S, cfg, R_max, forced_idx=None):
    """Run K0 stage + R_max birth rounds; return (snaps, births, aux). snaps[r] = flat render after stage r (r=0..R_max); births[r] = pixel indices chosen in round r.
    forced_idx: None or list of R_max index arrays (round r births forced; their init values still come from y). Seeds/streams identical to gsfast.fit_pipeline."""
    t0 = time.perf_counter(); H, W = cfg.H, cfg.W
    y = np.asarray(y, dtype=np.float64); yf = y.reshape(-1); lrs = G._lrs(cfg)
    if forced_idx is not None and len(forced_idx) < R_max:
        raise ValueError('forced_idx shorter than R_max')
    P = G._init(omega, cfg.K0, cfg)
    G._run(P, lrs, yf, H, W, cfg.steps_per_stage)
    snaps = [G.render_np(P['xy'], P['logscale'], P['rot'], P['val'], H, W).reshape(-1).copy()]
    births = []; resid_at_births = []; born_xy = []
    for r in range(int(R_max)):
        f_cur = snaps[-1].reshape(H, W)
        chosen, _cand, new = G._birth_round(y, f_cur, cfg, omega, r, S, None if forced_idx is None else forced_idx[r])
        births.append(np.asarray(chosen, dtype=np.int64).copy())
        resid_at_births.append(float(np.mean(np.abs(new['val'] - f_cur.reshape(-1)[chosen]))))   # mean |smoothed residual| of the FIT copy at the chosen pixels (report-only)
        born_xy.append(new['xy'].copy())
        P = {k: np.concatenate([P[k], new[k]], axis=0) for k in P}
        G._run(P, lrs, yf, H, W, cfg.steps_per_stage)
        snaps.append(G.render_np(P['xy'], P['logscale'], P['rot'], P['val'], H, W).reshape(-1).copy())
    for s in snaps:
        if not np.isfinite(s).all():
            raise RuntimeError('Non-finite snapshot render')
    disp = []
    for r in range(int(R_max)):                                                                   # final displacement (pixels) of each round's births from their birth positions (report-only)
        a = cfg.K0 + cfg.births_per_round * r; b = a + len(births[r])
        d = (P['xy'][a:b] - born_xy[r]) * np.array([W, H], dtype=np.float64)
        disp.append(float(np.mean(np.sqrt((d * d).sum(axis=1)))))
    return snaps, births, dict(K=[cfg.K0 + cfg.births_per_round * r for r in range(int(R_max) + 1)], wall_s=time.perf_counter() - t0, n_steps=(int(R_max) + 1) * cfg.steps_per_stage, resid_at_births=resid_at_births, birth_disp_px=disp)


def sse(a, b):
    a = np.asarray(a, dtype=np.float64).reshape(-1); b = np.asarray(b, dtype=np.float64).reshape(-1)
    return float(np.sum((a - b) ** 2))
