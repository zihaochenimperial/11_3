import sys, time, os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
sys.path.insert(0,'/home/claude/geo/src')
import numpy as np, geo_core as GC, geo_gen as GG
N=32
def make(i, cond, K, lam=1e-3, base=9101):
    sb, sn = GG.COND[cond]; op = GC.Op(N, sb); x = GG.clean_image_geo(i); y = GG.noisy_obs_geo(op, x, sn, base, i)
    P = GC.Prob(N, sb, y, sn, lam/sn**2); return P, GC.grid_init(P, K), x
P, th0, x = make(101, 'C1', 36)
print('F0', P.F_of(th0)[0])
for name, cfg in [('GEO',dict(kappa0=1e-3,f=3,rcond=1e-8)),('GEO',dict(kappa0=1e-3,f=3,rcond=1e-6)),('GEO',dict(kappa0=1e-3,f=3,rcond=1e-4)),('GEO',dict(kappa0=1e-3,f=3,rcond=1e-3)),('GEO',dict(kappa0=1e-3,f=3,rcond=1e-2)),
                  ('BJ',dict(kappa0=1e-3,f=3,rcond=1e-8)),('BJ',dict(kappa0=1e-3,f=3,rcond=1e-2)),('LMD',dict(kappa0=1e-3,f=3))]:
    t=time.perf_counter(); r=GC.solve(name,P,th0,cfg,max_iter=200); dt=time.perf_counter()-t
    it=len(r['traj'])-1
    print(f"{name:5s} rcond={cfg.get('rcond','-')}: F={r['F']:.2f} it={it} stop={r['stop']} A={r['cnt']['A']} W={r['cnt']['W']:.2e} rej={r['rej']} clamp={r['clamp_rate']:.2f} t={dt:.1f}s  ({dt/max(it,1)*1e3:.0f} ms/it)", flush=True)
