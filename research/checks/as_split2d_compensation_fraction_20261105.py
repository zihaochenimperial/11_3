"""AS-phase pre-contract self-check (NOT an experiment; NOT evidence; not the frozen S0/S1/S2 code).
2-D, numpy only. For a moment-preserving symmetric split (children Sigma'=Sigma-d^2 e e^T, amplitude a/2, at m+-d e) and a
non-moment-preserving split (children keep Sigma), measure:
  (1) scaling of ||q|| with d; (2) fraction of A q explained by the parent's own 6 Jacobian columns (BLOCK-like) vs all columns (JOINT-like);
  (3) the independent part ||P_perp A q|| scaling. Config: K overlapping anisotropic Gaussians on 32x32, known Gaussian blur.
Purpose: does JOINT compensation differ from BLOCK compensation for splits (if not, the 'joint' ingredient has little room for splits)?"""
import numpy as np, json
N = 32
uy, ux = np.meshgrid(np.arange(N)+0.5, np.arange(N)+0.5, indexing='ij')
U = np.stack([ux.ravel(), uy.ravel()], 1)
def L_from(l11, l21, l22): return np.array([[np.exp(l11), 0], [l21, np.exp(l22)]])
def g_img(a, m, Sigma):
    d = U - m; Si = np.linalg.inv(Sigma)
    return a*np.exp(-0.5*np.einsum('ni,ij,nj->n', d, Si, d))
def theta_to(th):
    a, mx, my, l11, l21, l22 = th; L = L_from(l11, l21, l22); return a, np.array([mx, my]), L@L.T
def render_k(th): a, m, S = theta_to(th); return g_img(a, m, S)
def jac_k(th, h=1e-6):
    J = np.zeros((N*N, 6))
    for j in range(6):
        d = np.zeros(6); d[j] = h; J[:, j] = (render_k(th+d)-render_k(th-d))/(2*h)
    return J
def blur_matrix(sb):
    r = max(1, int(np.ceil(3*sb))); k = np.exp(-0.5*(np.arange(-r, r+1)/sb)**2); k /= k.sum()
    B = np.zeros((N, N))
    for i in range(N):
        for t, w in zip(range(-r, r+1), k):
            j = i+t
            if j < 0: j = -j-1
            if j >= N: j = 2*N-1-j
            B[i, j] += w
    return np.kron(B, B)
def run(K, spacing, sb, seed=0):
    rng = np.random.default_rng(seed)
    ths = []
    cx, cy = N/2, N/2
    for k in range(K):
        ang = 2*np.pi*k/K
        m = np.array([cx+spacing*np.cos(ang)*(K>1), cy+spacing*np.sin(ang)*(K>1)])
        s1, s2 = rng.uniform(2.5, 4.5), rng.uniform(1.5, 3.0); phi = rng.uniform(0, np.pi)
        R = np.array([[np.cos(phi), -np.sin(phi)], [np.sin(phi), np.cos(phi)]]); S = R@np.diag([s1**2, s2**2])@R.T
        Lc = np.linalg.cholesky(S)
        ths.append(np.array([rng.uniform(0.6, 1.0), m[0], m[1], np.log(Lc[0, 0]), Lc[1, 0], np.log(Lc[1, 1])]))
    A = np.eye(N*N) if sb is None else blur_matrix(sb)
    Jall = np.concatenate([jac_k(t) for t in ths], 1); AJ = A@Jall
    pinv = np.linalg.pinv(AJ, rcond=1e-10); Pall = AJ@pinv
    th0 = ths[0]; a, m, S = theta_to(th0)
    w, V = np.linalg.eigh(S); e = V[:, 1]; se = np.sqrt(w[1])        # major axis
    AJ0 = A@jac_k(th0); P0 = AJ0@np.linalg.pinv(AJ0, rcond=1e-10)
    out = []
    for mp in ('mass_corrected', True, False):
        rows = []
        for alpha in (0.7, 0.35, 0.175, 0.0875):
            d = alpha*se
            Sc = S - d*d*np.outer(e, e) if mp else S
            ac = (a/2)*np.sqrt(np.linalg.det(S)/np.linalg.det(Sc)) if mp == 'mass_corrected' else a/2
            q = g_img(ac, m+d*e, Sc) + g_img(ac, m-d*e, Sc) - g_img(a, m, S)
            Aq = A@q; nq = np.linalg.norm(Aq)
            rows.append(dict(alpha=alpha, normAq=float(nq),
                             frac_parent=float(np.linalg.norm(P0@Aq)**2/nq**2),
                             frac_joint=float(np.linalg.norm(Pall@Aq)**2/nq**2),
                             indep_parent=float(np.linalg.norm(Aq-P0@Aq)), indep_joint=float(np.linalg.norm(Aq-Pall@Aq))))
        for r0, r1 in zip(rows[:-1], rows[1:]):
            r0['exp_normAq'] = float(np.log(r0['normAq']/r1['normAq'])/np.log(2))
            r0['exp_indep_joint'] = float(np.log(r0['indep_joint']/r1['indep_joint'])/np.log(2)) if r1['indep_joint'] > 1e-14 else None
        out.append(dict(moment_preserving=mp, rows=rows))
    return out
res = {}
for sb in (None, 1.0, 2.0, 3.0):
    for K, sp in ((6, 5.0), (6, 9.0)):
        res[f"blur={sb},K={K},spacing={sp}"] = run(K, sp, sb)
for k_, v in res.items():
    print(k_)
    for o in v:
        r = o['rows'][0]; r3 = o['rows'][-2]
        print("  moment_preserving=%s alpha=0.7: |Aq|=%.3e frac_parent=%.4f frac_joint=%.4f | alpha=0.175: frac_parent=%.4f frac_joint=%.4f exp|Aq|=%s exp_indep_joint=%s" % (
            o['moment_preserving'], r['normAq'], r['frac_parent'], r['frac_joint'], r3['frac_parent'], r3['frac_joint'],
            None if r3.get('exp_normAq') is None else round(r3['exp_normAq'], 2), None if r3.get('exp_indep_joint') is None else round(r3['exp_indep_joint'], 2)))
json.dump(res, open("research/checks/as_split2d_compensation_fraction_20261105.json", "w"), indent=1)
