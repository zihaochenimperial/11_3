import sys, os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
sys.path.insert(0,'/home/claude/geo/src'); sys.path.insert(0,'/tmp')
import numpy as np, geo_core as GC
from bench2_make import make
N=32
P, th0, x = make(102,'C2',16)
for rc in (1e-8,1e-6,1e-4,1e-3,1e-2):
    r = GC.solve('GEO',P,th0,dict(kappa0=1e-3,f=3,rcond=rc),max_iter=200); print('rc',rc,'F',round(r['F'],2),'it',len(r['traj'])-1,r['stop'],'rej',r['rej'])
r = GC.solve('GEO',P,th0,dict(kappa0=1e-3,f=3,rcond=1e-8),max_iter=200)
th=r['theta']; F,xx,rr=P.F_of(th); K=16; p=96; m=P.m; sn,a=P.sn,P.a
xr,Jimg=GC.render_jac(th,N); AJ=P.op.apply_stack(Jimg).reshape(p,m).T; Jm=Jimg.reshape(p,m).T
U,s,Vt=np.linalg.svd(Jm,full_matrices=False); print('s',s[0],s[-1],'cond',s[0]/s[-1]); print(np.round(s[-8:]/s[0],10))
rho=int(np.sum(s>1e-8*s[0])); Ur=U[:,:rho]; sr=s[:rho]; Vr=Vt[:rho].T
B=(AJ@Vr/sr)/sn; G=B.T@B; lam,Q=np.linalg.eigh(G); rhs=B.T@(rr.ravel()/sn)-a*(Ur.T@xx.ravel()); rq=Q.T@rhs
print('theta at stall (rows w,mx,my,l11,l21,l22):'); print(np.round(th,2))
for kap in (1e-3,1e-1,1,10,1e2,1e3,1e4):
    z=Q@(rq/(lam+a+kap*P.LamA)); d=Vr@(z/sr); th2raw=th+d.reshape(th.shape); th2=GC.clamp(th2raw,N); dc=(th2-th).ravel(); jv=Jm@dc
    F2,x2,r2=P.F_of(th2); Aj=AJ@dc; pred=float(Aj@rr.ravel())/sn**2-a*float(jv@xx.ravel())-0.5*(float(Aj@Aj)/sn**2+a*float(jv@jv)); act=F-F2
    print(f"kap={kap:g} |d|={np.linalg.norm(d):.2e} nclamp={int(np.sum(np.abs(th2raw-th2)>0))} pred={pred:.3e} act={act:.3e} guard={np.linalg.norm((x2-xx).ravel()-jv)/max(np.linalg.norm(jv),1e-300):.2f}")
