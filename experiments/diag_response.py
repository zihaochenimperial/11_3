"""EXPLORATORY post-hoc diagnostic (NOT part of the frozen contract; not evidence for H1/H2): how does the replay-frozen fit respond to a y-perturbation of size eps?
For D1, samples m<NM, S in (8,1024): record ||g_I(y+eps*s0*b) - f(y)|| and FD = b^T(...)/(eps*s0) on an eps grid from 1e-9 to 1.0 (units of sigma0).
Uses the runner's own helpers so y/omega/b are exactly the pilot's streams. Fitters see only (y, omega, S, I, cfg)."""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_v] = '1'
import sys, json, time, argparse
from dataclasses import asdict
from pathlib import Path
from multiprocessing import Pool
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
EPS = [1e-9, 1e-7, 1e-5, 1e-4, 1e-3, 3e-3, 1e-2, 3e-2, 0.1, 0.3, 1.0]
NM = 8
IMPL = os.environ.get('DIAG_IMPL', 'fast')


def work(args):
    S, m, EPSL = args
    from experiments import f0_run as R
    if IMPL == 'torch':
        import torch
        torch.set_num_threads(1)
        from src import gsfit as G
    else:
        from src import gsfast as G
    from src.f0_config import F0Config
    cfg = F0Config(); cj = json.dumps(json.loads(json.dumps(asdict(cfg))), sort_keys=True)
    H, W = cfg.H, cfg.W; N = H * W; s0 = cfg.sigma0; ent = cfg.entropy; ii = R.IMG_IDX['D1']
    x = R.clean('D1', cj); e = s0 * R.rng_for(ent, 1, ii, m).standard_normal(N); y = x + e
    om = R.omega_for(ent, 2, ii, m)
    t0 = time.time()
    f, aux = G.fit_pipeline(y.reshape(H, W), om, S, cfg); f = np.asarray(f, dtype=np.float64).reshape(-1); bi = [np.asarray(a, dtype=np.int64) for a in aux['birth_idx']]
    b0 = R.rng_for(ent, 3, ii, m).standard_normal(N)
    rows = []
    for er in EPSL:
        gp = np.asarray(G.fit_pipeline((y + er * s0 * b0).reshape(H, W), om, S, cfg, forced_idx=bi)[0], dtype=np.float64).reshape(-1)
        d = gp - f
        rows.append(dict(eps=er, dnorm=float(np.linalg.norm(d)), dmax=float(np.max(np.abs(d))), fd=float(b0 @ d / (er * s0)), lin_rate=float(np.linalg.norm(d) / (er * s0))))
    return dict(S=S, m=m, rows=rows, wall_s=time.time() - t0)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--impl', default='fast'); ap.add_argument('--nm', type=int, default=8); ap.add_argument('--eps', default=''); ap.add_argument('--out', default='DIAG_R7_response_p2'); ap.add_argument('--S', default='1024,8')
    a = ap.parse_args(); os.environ['DIAG_IMPL'] = a.impl; IMPL = a.impl; NM = a.nm
    if a.eps: EPS = [float(v) for v in a.eps.split(',')]
    tasks = [(int(S), m, list(EPS)) for S in a.S.split(',') for m in range(NM)]
    t0 = time.time()
    with Pool(6) as pool:
        res = pool.map(work, tasks, chunksize=1)
    out = dict(impl=a.impl, eps_units='sigma0', note='exploratory post-hoc diagnostic; not a contract stage', wall_s=time.time() - t0, results=res)
    Path(ROOT, 'outputs').mkdir(exist_ok=True)
    Path(ROOT, 'outputs', a.out + '.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print('done', round(time.time() - t0), 's')
