# dev smoke (NOT a result): convergence/validity after K1 code changes (eps-active, alpha log, safety). 200 outer iterations, calibration mode.
import sys, time, os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
sys.path.insert(0,'/home/claude/geo/src')
import numpy as np, geo_core as GC, geo_gen as GG
N=32
def make(i, cond, K, lam=1e-3, base=9101):
    sb, sn = GG.COND[cond]; op = GC.Op(N, sb); x = GG.clean_image_geo(i); y = GG.noisy_obs_geo(op, x, sn, base, i)
    P = GC.Prob(N, sb, y, sn, lam/sn**2); return P, GC.grid_init(P, K)
cells=[(103,'C4',36),(101,'C1',36),(102,'C2',16)]
arms=[('GEO',dict(kappa0=1e-3,f=3,rcond=1e-4)),('GEO',dict(kappa0=1e-3,f=3,rcond=1e-8)),('LMD',dict(kappa0=1e-3,f=3)),('BJ',dict(kappa0=1e-3,f=3,rcond=1e-4)),('BLK',dict(kappa0=1e-3,f=3,rcond=1e-4)),('LSMR',dict(kappa0=1e-3,f=3)),('PCG8P',dict(kappa0=1e-3,f=3)),('PCG8D',dict(kappa0=1e-3,f=3))]
sel=sys.argv[1:] 
for (i,c,K) in cells:
    if sel and f'{i}_{c}_{K}' not in sel: continue
    P, th0 = make(i,c,K); print(f'cell {i}/{c}/K{K} F0={P.F_of(th0)[0]:.2f}', flush=True)
    for name,cfg in arms:
        t=time.perf_counter(); r=GC.solve(name,P,th0,cfg,max_iter=200); dt=time.perf_counter()-t
        a=np.array(r['act']) if len(r['act']) else np.zeros(1)
        print(f"  {name:5s} rc={cfg.get('rcond','-')}: F={r['F']:.2f} it={len(r['traj'])-1} stop={r['stop']} rej={r['rej']} meanI={a.mean():.2f} clampTr={r['clamp_rate']:.2f} t={dt:.0f}s", flush=True)
