import sys, time, os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
sys.path.insert(0,'/home/claude/geo/src'); sys.path.insert(0,'/tmp')
import numpy as np, geo_core as GC
from bench2_make import make
img, cond, K = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
P, th0, x = make(img, cond, K)
print('F0', P.F_of(th0)[0])
runs = [('LMD',dict(kappa0=1e-3,f=3)),('GEO',dict(kappa0=1e-3,f=3,rcond=1e-8)),('GEO',dict(kappa0=1e-3,f=3,rcond=1e-4)),('GEO',dict(kappa0=1e-3,f=3,rcond=1e-2))]
for rc in (1e-8,1e-6,1e-4,1e-3,1e-2): runs.append(('BJ',dict(kappa0=1e-3,f=3,rcond=rc)))
for rc in (1e-8,1e-4,1e-2): runs.append(('BLK',dict(kappa0=1e-3,f=3,rcond=rc)))
runs += [('LSMR',dict(kappa0=1e-3,f=3)),('PCG8P',dict(kappa0=1e-3,f=3)),('PCG8D',dict(kappa0=1e-3,f=3))]
for name,cfg in runs:
    t=time.perf_counter(); r=GC.solve(name,P,th0,cfg,max_iter=200); dt=time.perf_counter()-t; it=len(r['traj'])-1
    xs=GC.render(r['theta'],32)
    print(f"{name:5s} rc={cfg.get('rcond','-')}: F={r['F']:.2f} it={it} stop={r['stop']} A={r['cnt']['A']} W={r['cnt']['W']:.2e} rej={r['rej']} clamp={r['clamp_rate']:.2f} act={np.mean(r['act']) if r['act'] else 0:.2f} t={dt:.1f}s", flush=True)
