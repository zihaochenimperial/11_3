import sys, os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
sys.path.insert(0,'/home/claude/geo/src'); sys.path.insert(0,'/tmp')
import numpy as np, geo_core as GC
from bench2_make import make
P, th0, x = make(101,'C1',36)
r = GC.solve('BJ',P,th0,dict(kappa0=1e-3,f=3,rcond=1e-8),max_iter=200)
print('stop',r['stop'],'its',len(r['traj'])-1,'alphas',np.round(r['alpha'][:40],3))
print('kappa',r['kappa'])
