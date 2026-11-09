# TRN dev pilot, image 301 only (pre-freeze exploration, 2026-11-08 ~09:10-09:14Z).
# PROVENANCE: ad-hoc inline script (python3 - <<EOF) executed in the cloud container against the then-current
# src/trn_core.py (with block_jacobi added) and src/trn_gen.py (candidate, unfrozen). Saved here verbatim from the
# executed command text for disclosure; it was NOT run as a saved file and has no run_id. Informational, dev-only.
# Triples are iterations to ||e||_H^2 <= rho*||delta*||_H^2 for rho=(0.1,0.03,0.01); None = not reached within min(p,400).
import sys; sys.path.insert(0,'/home/claude/geo/src')
import numpy as np, time
import geo_core as GC, trn_gen as TG, trn_core as TC
def pilot(N,K,cond,img=301,t=3,kap=1e-4):
    sb,sn=TG.COND[cond]; op=GC.Op(N,sb); x=TG.clean_image_trn(img,N); y=TG.noisy_obs_trn(op,x,sn,9401,img)
    P=GC.Prob(N,sb,y,sn,1e-3/sn**2); th0=GC.grid_init(P,K)
    t0=time.time(); res=GC.solve('GEO',P,th0,dict(kappa0=1e-3,f=3,rcond=1e-4),max_iter=t+1,keep_theta=True); tg=time.time()-t0
    th=res['th_hist'][t]; I=TC.Inner(P,th,kap); t1=time.time(); D=I.dense(); td=time.time()-t1
    idx=D['idx']; Hf=D['H']; dstar=D['dstar']; ds2=D['dH2']; lam=D['lam']; e=D['energy']; order=np.argsort(-e); cs=np.cumsum(e[order])/e.sum()
    print(f'\n=== N={N} K={K} {cond} img{img} t={t}: p={I.p} free={int(I.free.sum())} cond={lam[-1]/lam[0]:.2e} r_eff95={int(np.searchsorted(cs,.95))+1} r_eff99={int(np.searchsorted(cs,.99))+1} (traj {tg:.1f}s dense {td:.1f}s) F0={res["traj"][0][1]:.4g}->{res["traj"][t][1]:.4g}')
    def track(xk):
        ee=(xk-dstar)[idx]; return dict(err=float(ee@Hf@ee)/ds2)
    rhos=(0.1,0.03,0.01)
    def run(prec,W=None,build=0.0):
        w=[build]; HW=None
        if W is not None: HW=np.stack([I.Hmv(W[:,j]) for j in range(W.shape[1])],1); w[0]+=W.shape[1]*I.wH
        o=TC.dpcg(I,I.g,prec,W=W,HW=HW,track=track,work=w,maxit=min(I.p,400))
        errs=[h['err'] for h in o['hist']]; its=[next((i for i,ev in enumerate(errs) if ev<=rho),None) for rho in rhos]
        wk=[ (w[0] - (o['iters']-it)*I.wH) if it is not None else None for it in its]   # approx work up to criterion
        return its, [None if v is None else f'{v:.2e}' for v in wk]
    wb=[0.0]; Mb=TC.block_jacobi(I,wb)
    print(' PCG-J      ',run(I.dinvJ)); print(' PCG-BJ     ',run(Mb,build=wb[0]), f'(BJ build W={wb[0]:.2e}, one H-matvec W={I.wH:.2e})')
    V=D['V']
    for k in (16,32):
        Ws=I._embed(idx,V[:,:k]); We=I._embed(idx,V[:,order[:k]])
        print(f' J + smallest-{k}',run(I.dinvJ,Ws),f' J + energy-{k}',run(I.dinvJ,We))
        print(f' BJ+ smallest-{k}',run(Mb,Ws,wb[0]),f' BJ+ energy-{k}',run(Mb,We,wb[0]))
for args in ((32,36,'C4'),(64,144,'C1'),(64,144,'C4')): pilot(*args)
