import sys; sys.path.insert(0,'/home/claude/geo/src')
import numpy as np, geo_core as GC, geo_gen as GG
def make(i, cond, K, lam=1e-3, base=9101, N=32):
    sb, sn = GG.COND[cond]; op = GC.Op(N, sb); x = GG.clean_image_geo(i); y = GG.noisy_obs_geo(op, x, sn, base, i)
    P = GC.Prob(N, sb, y, sn, lam/sn**2); return P, GC.grid_init(P, K), x
