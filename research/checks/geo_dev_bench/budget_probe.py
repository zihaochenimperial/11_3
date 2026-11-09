import sys, time, os, json
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
sys.path.insert(0,'/home/claude/geo/src'); sys.path.insert(0,'/tmp')
import numpy as np, geo_core as GC
from bench2_make import make
img, cond, K = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
P, th0, x = make(img, cond, K)
t=time.perf_counter(); g=GC.solve('GEO',P,th0,dict(kappa0=1e-3,f=3,rcond=1e-4),max_iter=200); tg=time.perf_counter()-t
A0=g['cnt']['A']; W0=g['cnt']['W']; print(f'GEO calib: its={len(g["traj"])-1} stop={g["stop"]} A={A0} W={W0:.3e} t={tg:.1f}s F={g["F"]:.2f}', flush=True)
Acap, Wcap = 5*A0, 5*W0
out={}
for name,cfg in [('GEO',dict(kappa0=1e-3,f=3,rcond=1e-4)),('LMD',dict(kappa0=1e-3,f=3)),('BJ',dict(kappa0=1e-3,f=3,rcond=1e-4)),('BLK',dict(kappa0=1e-3,f=3,rcond=1e-4)),('PCG8P',dict(kappa0=1e-3,f=3)),('PCG8D',dict(kappa0=1e-3,f=3)),('LSMR',dict(kappa0=1e-3,f=3))]:
    t=time.perf_counter(); r=GC.solve(name,P,th0,cfg,A_cap=Acap,W_cap=Wcap); dt=time.perf_counter()-t; tr=r['traj']
    # F at A_cap and at W_cap
    iA=max(i for i,e in enumerate(tr) if e[3]<=Acap); iW=max(i for i,e in enumerate(tr) if e[6]<=Wcap)
    print(f"{name:5s}: its={len(tr)-1} stop={r['stop']} F_end={r['F']:.3f} F@Acap={tr[iA][1]:.3f} F@Wcap={tr[iW][1]:.3f} A={r['cnt']['A']} W={r['cnt']['W']:.2e} t={dt:.1f}s", flush=True)
