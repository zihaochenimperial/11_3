"""AS-phase contract-free unit-scale check K-a (NOT an experiment, NOT evidence, NOT frozen S0/S1/S2 code).
Opus-gate item K-a: on a small 2-D problem with a known blur, do the candidate-selection rules
 raw (OMP-like), block-compensated, joint-compensated (OLS-like), v1 free-coefficient rules
pick the same edit, and how do they compare with the realised full-refit gain (ORACLE_y-like, full candidate set)?
Numpy only. Usage: python as_ka_decision_agreement.py SB SPACING SEED0 NSEEDS OUT.json
Design: N=32; truth = 5 anisotropic Gaussians on a ring (spacing SPACING); observation y = blur(truth)+noise(0.02);
current model = K0=3 Gaussians fitted by LM to near-stationarity; candidates = 6 mass-preserving moment splits
(3 parents x alpha in {0.5,0.8}) + 72 births (iso sigma {1.5,3.0} on a 6x6 grid). Realised gain = 1/2(|r|^2-|r_new|^2) after 14 LM
steps from the candidate-inserted model (all parameters free); births: best of two amplitude inits (raw-OMP, OLS) = rule-neutral value. VARIANT v2 of as_ka_decision_agreement_20261105.py."""
import numpy as np, json, sys, time

N = 32
uy, ux = np.meshgrid(np.arange(N) + 0.5, np.arange(N) + 0.5, indexing='ij')


def blur_mat(sb):
    if sb is None:
        return np.eye(N)
    r = max(1, int(np.ceil(3 * sb)))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sb) ** 2)
    k /= k.sum()
    B = np.zeros((N, N))
    for i in range(N):
        for t, w in zip(range(-r, r + 1), k):
            j = i + t
            if j < 0: j = -j - 1
            if j >= N: j = 2 * N - 1 - j
            B[i, j] += w
    return B


def g_img(a, mx, my, l11, l21, l22):
    L11 = np.exp(l11); L22 = np.exp(l22); L21 = l21
    S11 = L11 * L11; S12 = L11 * L21; S22 = L21 * L21 + L22 * L22
    det = S11 * S22 - S12 * S12
    dx = ux - mx; dy = uy - my
    q = (S22 * dx * dx - 2 * S12 * dx * dy + S11 * dy * dy) / det
    return a * np.exp(-0.5 * q)


def render(th):
    out = np.zeros((N, N))
    for k in range(th.shape[0]):
        out += g_img(*th[k])
    return out


def chol_params(S):
    L = np.linalg.cholesky(S)
    return np.log(L[0, 0]), L[1, 0], np.log(L[1, 1])


def sigma_of(p):
    l11, l21, l22 = p
    L = np.array([[np.exp(l11), 0], [l21, np.exp(l22)]])
    return L @ L.T


def blur_img(Bm, X):
    return Bm @ X @ Bm.T


def blur_stack(Bm, X):  # X: (n,N,N)
    return np.einsum('ij,njk,lk->nil', Bm, X, Bm, optimize=True)


def resid(Bm, y, th):
    return (y - blur_img(Bm, render(th))).ravel()


def jac(Bm, th, h=1e-5):
    K = th.shape[0]
    cols = []
    for k in range(K):
        for j in range(6):
            tp = th.copy(); tm = th.copy()
            tp[k, j] += h; tm[k, j] -= h
            cols.append((g_img(*tp[k]) - g_img(*tm[k])) / (2 * h))
    X = np.stack(cols, 0)
    return blur_stack(Bm, X).reshape(len(cols), -1).T  # (N*N, 6K)


def clamp(th):
    t = th.copy()
    t[:, 1] = np.clip(t[:, 1], -4, N + 4); t[:, 2] = np.clip(t[:, 2], -4, N + 4)
    t[:, 3] = np.clip(t[:, 3], np.log(0.6), np.log(12)); t[:, 5] = np.clip(t[:, 5], np.log(0.6), np.log(12))
    t[:, 4] = np.clip(t[:, 4], -12, 12)
    return t


def lm(Bm, y, th, steps, lam=1e-2):
    th = clamp(th.copy()); r = resid(Bm, y, th); f = r @ r
    for _ in range(steps):
        J = jac(Bm, th); H = J.T @ J; g = J.T @ r
        ok = False
        for _t in range(8):
            try:
                d = np.linalg.solve(H + lam * np.diag(np.diag(H) + 1e-9), g)
            except np.linalg.LinAlgError:
                lam *= 10; continue
            th2 = clamp(th + d.reshape(th.shape)); r2 = resid(Bm, y, th2); f2 = r2 @ r2
            if f2 < f:
                th, r, f = th2, r2, f2; lam = max(lam * 0.3, 1e-9); ok = True; break
            lam *= 5
        if not ok:
            break
    return th, r, f


def spearman(a, b):
    a = np.asarray(a); b = np.asarray(b)
    if len(a) < 3: return np.nan
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    if ra.std() == 0 or rb.std() == 0: return np.nan
    return float(np.corrcoef(ra, rb)[0, 1])


def make_truth(rng, spacing, M=5):
    th = []
    for k in range(M):
        ang = 2 * np.pi * k / M + rng.uniform(0, 0.3)
        m = np.array([N / 2 + spacing * np.cos(ang), N / 2 + spacing * np.sin(ang)])
        s1, s2 = rng.uniform(2.5, 4.5), rng.uniform(1.5, 3.0); phi = rng.uniform(0, np.pi)
        R = np.array([[np.cos(phi), -np.sin(phi)], [np.sin(phi), np.cos(phi)]]); S = R @ np.diag([s1 ** 2, s2 ** 2]) @ R.T
        cp = chol_params(S)
        th.append([rng.uniform(0.6, 1.0), m[0], m[1], cp[0], cp[1], cp[2]])
    return np.array(th)


def scenario(sb, spacing, seed, sn=0.02, K0=3):
    rng = np.random.default_rng(seed)
    Bm = blur_mat(sb)
    tr = make_truth(rng, spacing)
    y = blur_img(Bm, render(tr)) + sn * rng.standard_normal((N, N))
    # current model: K0 broad Gaussians at random positions, fit to near stationarity
    th0 = []
    for k in range(K0):
        S = np.diag([rng.uniform(3, 5) ** 2, rng.uniform(3, 5) ** 2]); cp = chol_params(S)
        th0.append([0.5, rng.uniform(8, 24), rng.uniform(8, 24), cp[0], cp[1], cp[2]])
    th, r, f = lm(Bm, y, np.array(th0), 60)
    J = jac(Bm, th); sv = np.linalg.svd(J, compute_uv=False)
    stat = float(np.linalg.norm(J.T @ r) / (sv[0] * np.linalg.norm(r)))
    pinv = np.linalg.pinv(J, rcond=1e-10); P = J @ pinv
    Pperp_r = r - P @ r
    r2 = float(r @ r)
    blocks = [np.arange(6 * k, 6 * k + 6) for k in range(K0)]
    Pb = []
    for b in blocks:
        Jb = J[:, b]; Pb.append(Jb @ np.linalg.pinv(Jb, rcond=1e-10))
    cands = []
    # splits
    for k in range(K0):
        a = th[k, 0]; S = sigma_of(th[k, 3:6]); w, V = np.linalg.eigh(S); e = V[:, 1]; se = np.sqrt(w[1])
        for alpha in (0.5, 0.8):
            d = alpha * se; Sc = S - d * d * np.outer(e, e)
            ac = (a / 2) * np.sqrt(np.linalg.det(S) / np.linalg.det(Sc)); cp = chol_params(Sc)
            m = th[k, 1:3]
            c1 = np.array([ac, *(m + d * e), *cp]); c2 = np.array([ac, *(m - d * e), *cp])
            q = g_img(*c1) + g_img(*c2) - g_img(*th[k])
            Aq = blur_img(Bm, q).ravel()
            newth = np.vstack([np.delete(th, k, 0), c1[None], c2[None]])
            cands.append(dict(type='split', k=k, alpha=alpha, v=Aq, newth=newth, parent=k))
    # births
    gx = np.arange(2.5, N, 5.0)
    for sig in (1.5, 3.0):
        for bx in gx:
            for by in gx:
                cp = chol_params(np.diag([sig ** 2, sig ** 2]))
                g1 = np.array([1.0, bx, by, cp[0], cp[1], cp[2]])
                v = blur_img(Bm, g_img(*g1)).ravel()
                c0 = float(np.clip((r @ v) / (v @ v), 0.05, 1.5))
                vp = v - P @ v; c1o = float(np.clip((r @ vp) / (vp @ vp + 1e-30), 0.05, 1.5))
                nth = np.vstack([th, np.array([c0, bx, by, cp[0], cp[1], cp[2]])[None]])
                nth2 = np.vstack([th, np.array([c1o, bx, by, cp[0], cp[1], cp[2]])[None]])
                cands.append(dict(type='birth', v=v, newth=nth, newth2=nth2, parent=None, c0=c0))
    out = []
    for c in cands:
        v = c['v']
        if c['type'] == 'split':
            Pv = P @ v; Pvp = v - Pv; Pbv = Pb[c['parent']] @ v; Pbvp = v - Pbv
            raw_free = max(r @ v, 0) ** 2 / (2 * (v @ v) + 1e-30)
            fl = float(np.linalg.norm(Pvp) / (np.linalg.norm(v) + 1e-30))
            joint_free = (r @ Pvp) ** 2 / (2 * (Pvp @ Pvp) + 1e-30)
            raw_c1 = float(r @ v - 0.5 * v @ v)
            block_c1 = float(r @ Pbvp - 0.5 * Pbvp @ Pbvp)
            joint_c1 = float(r @ Pvp - 0.5 * Pvp @ Pvp)  # r not projected: general form relative to refit baseline uses P_perp r; r-term difference tracked via stat
            joint_c1s = float(Pperp_r @ Pvp - 0.5 * Pvp @ Pvp)
            c_star = float((r @ Pvp) / (Pvp @ Pvp + 1e-30))
        else:
            Pvp = v - P @ v
            raw_free = max(r @ v, 0) ** 2 / (2 * (v @ v) + 1e-30)
            fl = float(np.linalg.norm(Pvp) / (np.linalg.norm(v) + 1e-30))
            joint_free = max(r @ Pvp, 0) ** 2 / (2 * (Pvp @ Pvp) + 1e-30)
            raw_c1 = raw_free; block_c1 = raw_free; joint_c1 = joint_free; joint_c1s = max(Pperp_r @ Pvp, 0) ** 2 / (2 * (Pvp @ Pvp) + 1e-30)
            c_star = float((r @ Pvp) / (Pvp @ Pvp + 1e-30))
        thn, rn, fn = lm(Bm, y, c['newth'], 14)
        if 'newth2' in c:
            thn2, rn2, fn2 = lm(Bm, y, c['newth2'], 14); fn = min(fn, fn2)
        out.append(dict(type=c['type'], raw_free=float(raw_free), joint_free=float(joint_free), raw_c1=raw_c1, block_c1=block_c1,
                        joint_c1=joint_c1s, floor=fl, c_star=c_star, real=0.5 * (r2 - fn)))
    return dict(sb=sb, spacing=spacing, seed=seed, stat=stat, r2=r2, n_split=sum(o['type'] == 'split' for o in out), cands=out)


def summarize(sc):
    C = sc['cands']; real = np.array([c['real'] for c in C]); typ = np.array([c['type'] for c in C])
    res = {}
    for rule in ('raw_free', 'joint_free', 'raw_c1', 'block_c1', 'joint_c1'):
        s = np.array([c[rule] for c in C])
        row = {}
        for pool in ('all', 'split', 'birth'):
            idx = np.arange(len(C)) if pool == 'all' else np.where(typ == pool)[0]
            best_true = idx[np.argmax(real[idx])]; ch = idx[np.argmax(s[idx])]
            row[pool] = dict(choice=int(ch), eff=float(real[ch] / max(real[best_true], 1e-30)) if real[best_true] > 0 else np.nan,
                             hit=int(ch == best_true), rho=spearman(s[idx], real[idx]), is_split=int(typ[ch] == 'split'))
        res[rule] = row
    return res


if __name__ == '__main__':
    sb = None if sys.argv[1] == 'none' else float(sys.argv[1]); sp = float(sys.argv[2]); s0 = int(sys.argv[3]); ns = int(sys.argv[4]); outf = sys.argv[5]
    allsc = []
    t0 = time.time()
    for s in range(s0, s0 + ns):
        sc = scenario(sb, sp, s); sc['sum'] = summarize(sc); allsc.append(sc)
        print(f"seed {s} stat={sc['stat']:.2e} t={time.time()-t0:.0f}s all-eff " +
              " ".join(f"{r}={sc['sum'][r]['all']['eff']:.2f}/{'S' if sc['sum'][r]['all']['is_split'] else 'B'}" for r in sc['sum']), flush=True)
    json.dump(allsc, open(outf, 'w'))
