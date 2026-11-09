# feasibility bookkeeping ONLY: does the split-only (OMP_s) path ever face an empty restricted candidate set? never computes MSE / reads quality.
import os, sys, json, time
for v in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[v]='1'
sys.path.insert(0,'src')
import numpy as np
import as_core as C, as_gen as G
COND=dict(G.COND); out=[]
lo,hi=int(sys.argv[1]),int(sys.argv[2]); rule=sys.argv[3] if len(sys.argv)>3 else 'OMP'
orig=C.mask_for; st={}
def mf(cands,only):
    m=orig(cands,only); st['step']=st.get('step',-1)+1
    if only=='s' and m.sum()==0: st['empty']=st['step']
    return m
C.mask_for=mf
for img in range(lo,hi+1):
    for cond in ('C1','C2','C3','C4'):
        for ns in (9001,9002):
            sb,sn=COND[cond]; op=C.Op(sb); y=G.noisy_obs(op,G.clean_image(img),sn,ns,img)
            st.clear(); t0=time.time()
            th,L,_=C.initial_state(op,y,sn,6.0,30)
            nclamp=sum(1 for k in range(th.shape[0]) if min(abs(th[k,3]-C.LMIN),abs(th[k,3]-C.LMAX),abs(th[k,5]-C.LMIN),abs(th[k,5]-C.LMAX))<1e-9)
            try:
                C.run_path(y,op,sn,rule,only='s',seed=img); status='ok'; step=None
            except ValueError as e:
                status='empty'; step=st.get('empty')
            out.append(dict(img=img,cond=cond,ns=ns,k0_clamped=int(nclamp),status=status,empty_step=step,wall=round(time.time()-t0,1)))
            print(out[-1],flush=True)
json.dump(out,open('feas_%s_%d_%d.json'%(rule,lo,hi),'w'))
