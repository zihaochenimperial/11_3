"""DESCRIPTIVE / EXPLORATORY ONLY (not confirmation, not a new experiment): re-reads the already-analysed
CF0 dev tables (outputs/CF0-dev-d1; images E21+..., dev stage) and compares fixed-R rules with RAWcv and oracle-R.
RSS-based rules (discrepancy principle, Cp) CANNOT be evaluated: per-R RSS is not stored in the unit files.
Best-fixed-R is selected IN-SAMPLE on the same dev data -> optimistic; labelled as such.
"""
import sys, json, numpy as np
sys.path.insert(0,'experiments')
import cf_analyze as C
metas,U,integ=C.load_units(['outputs/CF0-dev-d1'])
C.attach_rcv(U)
imgs=sorted(U,key=lambda s:int(s[1:])); types=np.array([C.img_type(i) for i in imgs])
def rm(name): return C.image_means(U,name)[1]
R={r:rm('RAWy_R%d'%r) for r in range(5)}
y=rm('RAWy'); cv=rm('RAWcv'); orc=rm('RAWoracleR')
def nu_vec(a): return (y-a)/y
out={'n_images':len(imgs),'note':'in-sample, descriptive, dev tables only; RSS rules not evaluable'}
def summ(v): 
    d={'pooled':float(v.mean())}
    for t in C.TYPES:
        if (types==t).any(): d[t]=float(v[types==t].mean())
    return d
out['abs_risk_mean_by_type']={n:{t:float(a[types==t].mean()) for t in C.TYPES if (types==t).any()} for n,a in [('RAWy',y)]+[('R%d'%r,R[r]) for r in range(5)]+[('RAWcv',cv),('oracleR',orc)]}
out['NU_vs_RAWy']={('fixed_R%d'%r):summ(nu_vec(R[r])) for r in range(5)}
out['NU_vs_RAWy']['RAWcv']=summ(nu_vec(cv)); out['NU_vs_RAWy']['oracleR']=summ(nu_vec(orc))
# best fixed R pooled (equal image weights, in-sample)
bp=min(range(5),key=lambda r:R[r].mean()); out['best_fixed_R_pooled']=bp
out['NU_vs_RAWy']['best_fixed_R_pooled_in_sample']=summ(nu_vec(R[bp]))
# best fixed R per type (in-sample; each type uses own best) - upper-bound-ish for a 'type-aware' fixed rule
v=np.zeros(len(imgs)); per={}
for t in C.TYPES:
    m=types==t; b=min(range(5),key=lambda r:R[r][m].mean()); per[t]=b; v[m]=nu_vec(R[b])[m]
out['best_fixed_R_by_type']=per; out['NU_vs_RAWy']['best_fixed_R_by_type_in_sample']=summ(v)
# fraction of (oracle - RAWy) gain captured
gain_or=nu_vec(orc).mean()
out['fraction_of_oracle_gain_pooled']={'RAWcv':float(nu_vec(cv).mean()/gain_or),'best_fixed_R_pooled':float(nu_vec(R[bp]).mean()/gain_or),'best_fixed_R_by_type':float(v.mean()/gain_or)}
out['Rstar_cv_hist']={'by_type':{t:np.bincount([u['Rstar'] for i in imgs if C.img_type(i)==t for u in U[i].values()],minlength=5).tolist() for t in C.TYPES}}
print(json.dumps(out,indent=1)); json.dump(out,open('research/checks/m2_fixedR_headroom_20261105.json','w'),indent=1)
