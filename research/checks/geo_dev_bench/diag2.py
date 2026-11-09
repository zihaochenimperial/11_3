import sys, os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
sys.path.insert(0,'/home/claude/geo/src'); sys.path.insert(0,'/tmp')
import numpy as np, geo_core as GC, geo_gen as GG
from bench2_make import make
N=32
P, th0, x = make(101,'C1',36)
cfg=dict(kappa0=1e-3,f=3,rcond=1e-8)
# run GEO until stop, then capture state
import types
r = GC.solve('GEO',P,th0,cfg,max_iter=200)
th=r['theta']; print('stop',r['stop'],'it',len(r['traj'])-1,'F',r['F'],'kappa',r['kappa'])
F,xx,rr = P.F_of(th); K=36; p=216; m=P.m; sn,a=P.sn,P.a
xr,Jimg = GC.render_jac(th,N); AJ = P.op.apply_stack(Jimg).reshape(p,m).T; Jm=Jimg.reshape(p,m).T
U,s,Vt=np.linalg.svd(Jm,full_matrices=False)
print('s range',s[0],s[-1], 'n>1e-8',np.sum(s>1e-8*s[0]),'n>1e-4',np.sum(s>1e-4*s[0]),'n>1e-2',np.sum(s>1e-2*s[0]))
for rc in (1e-8,1e-4,1e-2):
    rho=int(np.sum(s>rc*s[0])); Ur=U[:,:rho]; sr=s[:rho]; Vr=Vt[:rho].T
    B=(AJ@Vr/sr)/sn; G=B.T@B; lam,Q=np.linalg.eigh(G); rhs=B.T@(rr.ravel()/sn)-a*(Ur.T@xx.ravel()); rq=Q.T@rhs
    for kap in (1e-3,1e-1,1,1e2,1e4):
        zq=rq/(lam+a+kap*P.LamA); z=Q@zq; d=Vr@(z/sr)
        th2raw=th+d.reshape(th.shape); th2=GC.clamp(th2raw,N); dc=(th2-th).ravel(); jv=Jm@dc
        F2,x2,r2=P.F_of(th2); Aj=AJ@dc
        pred=float(Aj@rr.ravel())/sn**2-a*float(jv@xx.ravel())-0.5*(float(Aj@Aj)/sn**2+a*float(jv@jv)); act=F-F2
        gr=np.linalg.norm((x2-xx).ravel()-jv)/max(np.linalg.norm(jv),1e-300)
        print(f"rc={rc:g} kap={kap:g} |d|={np.linalg.norm(d):.2e} clampfrac={np.mean(np.abs(th2raw-th2)>0):.2f} pred={pred:.3e} act={act:.3e} ratio={act/pred if pred>0 else -1:.3f} guard={gr:.2f}")
print('---- consistency at rc=1e-8, kap=1e4')
rc=1e-8; rho=int(np.sum(s>rc*s[0])); Ur=U[:,:rho]; sr=s[:rho]; Vr=Vt[:rho].T
B=(AJ@Vr/sr)/sn; G=B.T@B; lam,Q=np.linalg.eigh(G); rhs=B.T@(rr.ravel()/sn)-a*(Ur.T@xx.ravel()); rq=Q.T@rhs
print('lam range',lam.min(),lam.max(),'a',a,'LamA',P.LamA)
kap=1e4; zq=rq/(lam+a+kap*P.LamA); z=Q@zq; d=Vr@(z/sr)
jv=Jm@d; print('|jv - Ur z|/|jv|', np.linalg.norm(jv-Ur@z)/np.linalg.norm(jv))
Aj=AJ@d; print('|Aj - A Ur z|', np.linalg.norm(Aj-(AJ@Vr/sr)@z)/np.linalg.norm(Aj))
print('z.rhs',z@rhs,' pred_z', z@rhs-0.5*z@((G+a*np.eye(rho))@z)*1.0)
g_d=float(Aj@rr.ravel())/sn**2-a*float(jv@xx.ravel()); print('g_d',g_d,'  q',float(Aj@Aj)/sn**2+a*float(jv@jv))
# true directional derivative
for eps in (1e-1,1e-2,1e-3):
    Fe=P.F_of(GC.clamp(th+eps*d.reshape(th.shape),N))[0]; print(eps,'dF/eps',(Fe-F)/eps, ' model -g_d', -g_d)
# Jacobian check: FD of the render along d
eps=1e-5; xd=(GC.render(th+eps*d.reshape(th.shape),N)-GC.render(th-eps*d.reshape(th.shape),N))/(2*eps)
print('J d vs FD', np.linalg.norm(jv-xd.ravel())/np.linalg.norm(xd))
# which params carry the step
dd=d.reshape(th.shape); print('max |d| by param type', np.abs(dd).max(0)); k=np.argmax(np.abs(dd).max(1)); print('worst gaussian',k,th[k], dd[k])
print('theta ranges', th.min(0), th.max(0))
print('---- active-set test at the stall point')
lo=np.array([-4,-4,GC.LMIN,-12,GC.LMIN]); # order for cols 1,2,3,4,5
LO=np.array([-np.inf,-4,-4,GC.LMIN,-12,GC.LMIN]); HI=np.array([np.inf,N+4,N+4,GC.LMAX,12,GC.LMAX])
g_full = -(AJ.T@(rr.ravel()/sn**2)) + a*(Jm.T@xx.ravel())          # gradient of F wrt theta (p,)
thv=th.ravel(); lov=np.tile(LO,K); hiv=np.tile(HI,K)
act = ((np.abs(thv-lov)<1e-9)&(g_full>0)) | ((np.abs(thv-hiv)<1e-9)&(g_full<0))
print('n at bound',int(np.sum((np.abs(thv-lov)<1e-9)|(np.abs(thv-hiv)<1e-9))),'n active (blocked)',int(act.sum()), np.where(act)[0])
fr=~act
Jf=Jm[:,fr]; AJf=AJ[:,fr]
Uf,sf,Vtf=np.linalg.svd(Jf,full_matrices=False)
for rc in (1e-8,):
    rho=int(np.sum(sf>rc*sf[0])); Ur=Uf[:,:rho]; sr=sf[:rho]; Vr=Vtf[:rho].T
    B=(AJf@Vr/sr)/sn; G=B.T@B; lam,Q=np.linalg.eigh(G); rhs=B.T@(rr.ravel()/sn)-a*(Ur.T@xx.ravel()); rq=Q.T@rhs
    for kap in (1e-3,1e-2,1e-1,1,10,100):
        zq=rq/(lam+a+kap*P.LamA); z=Q@zq; dfree=Vr@(z/sr); d=np.zeros(p); d[fr]=dfree
        th2raw=th+d.reshape(th.shape); th2=GC.clamp(th2raw,N); dc=(th2-th).ravel(); jv=Jm@dc
        F2,x2,r2=P.F_of(th2); Aj=AJ@dc
        pred=float(Aj@rr.ravel())/sn**2-a*float(jv@xx.ravel())-0.5*(float(Aj@Aj)/sn**2+a*float(jv@jv)); act_=F-F2
        gr=np.linalg.norm((x2-xx).ravel()-jv)/max(np.linalg.norm(jv),1e-300)
        print(f"rc={rc:g} kap={kap:g} rho={rho} |d|={np.linalg.norm(d):.2e} nclamped={int(np.sum(np.abs(th2raw-th2)>0))} pred={pred:.3e} act={act_:.3e} ratio={act_/pred if pred>0 else -1:.3f} guard={gr:.2f}")
