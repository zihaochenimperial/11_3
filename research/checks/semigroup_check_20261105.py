"""Analytic sanity check (NOT an experiment; no data/images, no pipeline fit).
Checks Opus round-9's claims about the Gaussian scale semigroup (to be verified by Sonnet):
 (1) g_Sigma = g_Sigma1 * g_(Sigma-Sigma1): a wide atom is a positive continuous mixture of narrower shifted atoms.
 (2) L1-normalised atoms: total mass of every positive representation of the same image is identical -> BLASSO TV penalty is constant.
     L2-normalised atoms: penalty of narrow mixture / wide atom = (|Sig_w|/|Sig_n|)^(1/4) in 2D.
 (3) Pure-noise sup of matched-filter response over (position, scale): where the argmax lands for L2 / L1 / peak normalisation.
numpy only. Seed fixed. Pure-noise only (no E41-58, no project images).
"""
import numpy as np, json, sys
rng=np.random.default_rng(20261105)
out={}

def gauss2(X,Y,mu,S):
    d=np.stack([X-mu[0],Y-mu[1]],-1)
    Si=np.linalg.inv(S)
    q=np.einsum('...i,ij,...j->...',d,Si,d)
    return np.exp(-0.5*q)/(2*np.pi*np.sqrt(np.linalg.det(S)))   # unit mass density

# ---- (1) semigroup identity, isotropic and rotated anisotropic
n=161; c=(n-1)/2
ax=np.arange(n)*1.0
X,Y=np.meshgrid(ax,ax,indexing='xy')
def rot(t): return np.array([[np.cos(t),-np.sin(t)],[np.sin(t),np.cos(t)]])
cases={'iso':(np.diag([9.,9.]),np.diag([2.25,2.25])),
       'aniso_rot':(rot(0.6)@np.diag([16.,4.])@rot(0.6).T, None)}
S=cases['aniso_rot'][0]; cases['aniso_rot']=(S,0.3*S)
res1={}
for name,(Sw,Sn) in cases.items():
    Sd=Sw-Sn
    assert np.all(np.linalg.eigvalsh(Sd)>-1e-12)
    target=gauss2(X,Y,(c,c),Sw)
    # mixture of narrow atoms on centres grid (spacing h) with weights g_{Sd}(mu'-mu) h^2
    h=0.5
    cs=np.arange(c-25,c+25+1e-9,h)
    mix=np.zeros_like(target); wsum=0.0
    Sdi=np.linalg.inv(Sd)
    for a in cs:
        for b in cs:
            d=np.array([a-c,b-c]); w=np.exp(-0.5*d@Sdi@d)/(2*np.pi*np.sqrt(np.linalg.det(Sd)))*h*h
            if w<1e-9: continue
            mix+=w*gauss2(X,Y,(a,b),Sn); wsum+=w
    res1[name]={'max_abs_err_over_peak':float(np.abs(mix-target).max()/target.max()),
                'mixture_total_weight':float(wsum),'target_sum':float(target.sum()),'mix_sum':float(mix.sum())}
out['semigroup_identity']=res1

# ---- (2) penalty comparison: single wide atom vs narrow-mixture representation of the SAME image
res2={}
for name,(Sw,Sn) in cases.items():
    wide=gauss2(X,Y,(c,c),Sw)            # mass 1
    # L1 normalised: coefficient = mass; wide atom: 1 ; mixture: sum weights (=wsum ~ 1)
    nw=np.sqrt((wide**2).sum())          # discrete L2 norm of unit-mass wide atom
    narrow=gauss2(X,Y,(c,c),Sn); nn=np.sqrt((narrow**2).sum())
    res2[name]={'L1_pen_wide':1.0,'L1_pen_mixture(=mixture weight sum)':res1[name]['mixture_total_weight'],
                'L2_pen_ratio_narrow_over_wide_numeric':float(nn/nw),
                'L2_pen_ratio_theory_(|Sw|/|Sn|)^(1/4)':float((np.linalg.det(Sw)/np.linalg.det(Sn))**0.25)}
out['penalty_normalisation']=res2

# ---- (3) pure-noise sup over (position, scale); isotropic atoms; periodic correlation via FFT
N=64; sig=1.0
scales=0.7*1.35**np.arange(10)   # sigma in pixels
def atom_fft(s,norm):
    k=np.fft.fftfreq(N)*N
    xx=np.minimum(np.arange(N),N-np.arange(N)).astype(float)
    XX,YY=np.meshgrid(xx,xx)
    g=np.exp(-(XX**2+YY**2)/(2*s*s))
    if norm=='L2': g=g/np.sqrt((g**2).sum())
    elif norm=='L1': g=g/g.sum()
    elif norm=='peak': pass
    return np.fft.fft2(g), np.sqrt((g**2).sum())
B=200
res3={}
for norm in ['L2','L1','peak']:
    F=[atom_fft(s,norm) for s in scales]
    sup=np.zeros(B); arg=np.zeros(B,int); noisesd=[f[1] for f in F]
    for b in range(B):
        w=rng.normal(0,sig,(N,N)); W=np.fft.fft2(w)
        best=-1;bi=-1
        for j,(Fj,_) in enumerate(F):
            r=np.fft.ifft2(W*np.conj(Fj)).real
            m=np.abs(r).max()
            if m>best: best=m; bi=j
        sup[b]=best; arg[b]=bi
    res3[norm]={'mean_sup':float(sup.mean()),'sd_sup':float(sup.std()),
                'argmax_scale_hist(scale idx 0..9)':np.bincount(arg,minlength=10).tolist(),
                'per_scale_noise_response_sd(=||g||2)':[float(x) for x in noisesd]}
out['pure_noise_sup']=res3
out['scales_px']=[float(s) for s in scales]
out['sqrt_2log_cells_reference']=float(np.sqrt(2*np.log(N*N*len(scales))))
print(json.dumps(out,indent=1))
json.dump(out,open('research/checks/semigroup_check_20261105.json','w'),indent=1)
