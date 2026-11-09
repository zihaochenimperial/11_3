"""JR core (METHOD-SIDE: never imports jr_gen or any clean-image function; test enforces). Fixed-K 2-D Gaussians, known sparse PSF operator, objective of geo_core:
F_a(theta) = 1/(2 sn^2) ||y - A x(theta)||^2 + a/2 ||x(theta)||^2 (a = 1e-3/sn^2 in the runner).
One outer SWEEP = (i) linearisation at the sweep-start state (J, AJ for all primitives), (ii) partition of the K primitives into groups (arm-specific affinity, size cap gs; rebuilt every R sweeps, reused in between at no grouping cost),
(iii) Gauss-Seidel over the groups in a fixed order (raster of group centroids): per group a bounded finite update with the CURRENT residual, accepted only after an EXACT incremental
forward (r2 = r - A (x_g(new) - x_g(old)), identical to a full re-render of F_a), (iv) a full refresh of (x, r, F).
Group step modes: 'joint' (damped Gauss-Newton on all 6*|g| parameters, image-metric damping kappa*LamA, SVD image-basis solve = geo_core._iter_blk generalised to |g|>1;
|g| = 1 reproduces _iter_blk) and 'ind_lp' (independent 6-parameter steps per primitive from the same residual, then the best |g|-vector of step scales: linear projection on the
span of the independent steps in the undamped quadratic model). Acceptance = geo_core rule (pred > 0, act > 0, act/pred >= RHO_MIN, linearisation guard), clamp, projected-gradient active set.
Cost W = flop proxy of geo_flops formulas; the operator cost per application is 2*nnz(A) (SOp.flops_apply). EVERY operation of the method is charged, by category
(lin, grp, solve, check, refresh). Diagnostics that do not influence the trajectory (singular-value / compensation statistics) are NOT charged and are marked diag."""
import time
import numpy as np
import geo_core as GC
import geo_flops as FL

KAPPA_MIN, KAPPA_MAX = GC.KAPPA_MIN, GC.KAPPA_MAX
BACKTRACKS, RHO_MIN, GUARD = GC.BACKTRACKS, GC.RHO_MIN, GC.GUARD
CATS = ('lin', 'grp', 'solve', 'check', 'refresh')
AGG_C = 10.0          # agglomeration priced at AGG_C*K^3 flops for every grouped arm (Opus R6)


class JProb(GC.Prob):
    """geo_core.Prob with a general sparse operator."""
    def __init__(self, N, op, y, sn, a):
        self.N = N; self.m = N * N; self.op = op; self.y = y; self.sn = float(sn); self.a = float(a)
        self.render = lambda th: GC.render(th, N); self.LamA = op.normA ** 2 / self.sn ** 2; self.wA = op.flops_apply


def _w(cnt, cat, v):
    cnt['W'] += v; cnt['cat'][cat] += v


# ------------------------------------------------------------------ calibrated observation responses and affinities
def calib_scales(th, Jimg):
    """Parameter steps d_kj with a fixed UNBLURRED image effect: ||J_kj d_kj|| = 0.1 ||x_k|| (x_k the primitive's own image, ||x_k|| = |w_k| ||J_k,w||). Unit-free under any
    rescaling of a parameter coordinate (J_kj -> J_kj / c, d_kj -> c d_kj). Zero for a vanished primitive / zero column."""
    jn = np.sqrt((Jimg ** 2).sum((1, 2))); xn = np.abs(th[:, 0]) * jn[0::6]
    return np.where(jn > 0, 0.1 * np.repeat(xn, 6) / np.maximum(jn, 1e-300), 0.0)


def support_boxes(th, N, rp, rad=4.0):
    """Pixel boxes [x0,x1) x [y0,y1) of the rad-Mahalanobis support of each Gaussian dilated by the PSF half width rp (an interaction can exist only if the boxes overlap)."""
    L11 = np.exp(th[:, 3]); L22 = np.exp(th[:, 5]); sx = rad * L11; sy = rad * np.sqrt(th[:, 4] ** 2 + L22 ** 2)
    x0 = np.clip(np.floor(th[:, 1] - sx - rp), 0, N); x1 = np.clip(np.ceil(th[:, 1] + sx + rp) + 1, 0, N)
    y0 = np.clip(np.floor(th[:, 2] - sy - rp), 0, N); y1 = np.clip(np.ceil(th[:, 2] + sy + rp) + 1, 0, N)
    return x0, x1, y0, y1


def candidate_pairs(th, N, rp):
    x0, x1, y0, y1 = support_boxes(th, N, rp); K = th.shape[0]
    wx = np.maximum(np.minimum(x1[:, None], x1[None]) - np.maximum(x0[:, None], x0[None]), 0); wy = np.maximum(np.minimum(y1[:, None], y1[None]) - np.maximum(y0[:, None], y0[None]), 0)
    inter = wx * wy; box = (x1 - x0) * (y1 - y0)
    iu = np.triu_indices(K, 1); sel = inter[iu] > 0
    return iu[0][sel], iu[1][sel], inter, box


def _inv_sqrt_sym(G):
    lam, V = np.linalg.eigh(G); return (V * (1.0 / np.sqrt(np.maximum(lam, 1e-300)))) @ V.T


def coupling_matrix(R, K, pi, pj, ridge=1.0):
    """Normalised cross coupling a_kl = || (R_k'R_k + ridge I)^-1/2 R_k'R_l (R_l'R_l + ridge I)^-1/2 ||_2 for the listed pairs (0 elsewhere). R: m x 6K, columns already whitened by sn
    and scaled by the calibrated steps, so `ridge` = 1 is the noise scale: directions whose calibrated response is below one noise std are damped (weakly identifiable), strictly null
    directions (response 0) contribute nothing. Returns the K x K symmetric matrix."""
    Gm = R.T @ R; W = [_inv_sqrt_sym(Gm[6 * k:6 * k + 6, 6 * k:6 * k + 6] + ridge * np.eye(6)) for k in range(K)]; A = np.zeros((K, K))
    for k, l in zip(pi, pj):
        C = W[k] @ Gm[6 * k:6 * k + 6, 6 * l:6 * l + 6] @ W[l]; A[k, l] = A[l, k] = float(np.linalg.norm(C, 2))
    return A


def agglomerate(aff, cent, s):
    """Average-linkage agglomeration with a group size cap s. aff: K x K symmetric affinity (larger = more affine); cent: K x 2 centres for deterministic tie-breaks."""
    K = aff.shape[0]; L = aff.astype(float).copy(); np.fill_diagonal(L, 0.0); n = np.ones(K); Cs = cent.astype(float).copy(); members = [[i] for i in range(K)]; alive = list(range(K))
    while True:
        ia = np.array(alive); nn = n[ia]; ok = (nn[:, None] + nn[None, :] <= s) & (np.arange(len(ia))[:, None] < np.arange(len(ia))[None, :])
        if not ok.any(): break
        link = L[np.ix_(ia, ia)] / np.outer(nn, nn); cc = Cs[ia] / nn[:, None]; dist = np.linalg.norm(cc[:, None, :] - cc[None, :, :], axis=2)
        link = np.where(ok, np.round(link, 12), -np.inf); best = link.max(); cand = np.argwhere(link == best)
        dsel = dist[cand[:, 0], cand[:, 1]]; a_, b_ = cand[int(np.argmin(dsel))]; a, b = ia[a_], ia[b_]
        L[a, :] += L[b, :]; L[:, a] = L[a, :]; L[a, a] = 0.0; n[a] += n[b]; Cs[a] += Cs[b]; members[a] += members[b]; alive.remove(b)
    return [sorted(members[i]) for i in alive]


def make_groups(P, th, Jimg, AJ, cfg, cnt, rng_seed=0):
    """Partition of the K primitives per arm. Charged to category 'grp' (affinity pair blocks on the exact-support pair set + the agglomeration)."""
    K = th.shape[0]; N = P.N; arm = cfg['arm']; s = cfg['gs']; cent = th[:, 1:3]
    if arm == 'FULL': return [list(range(K))], dict(note='single group')
    if arm == 'IND1' or s == 1: return [[k] for k in range(K)], dict(note='singletons')
    info = {}
    if arm in ('OBS', 'OBS0'):
        d = calib_scales(th, Jimg); base = AJ if arm == 'OBS' else Jimg.reshape(6 * K, -1).T
        R = base * d[None, :] / P.sn; pi, pj, inter, box = candidate_pairs(th, N, P.op.rp)
        aff = coupling_matrix(R, K, pi, pj, ridge=cfg.get('ridge', 1.0))
        _w(cnt, 'grp', float(2.0 * np.sum(box) * 36 + 2.0 * np.sum(inter[pi, pj]) * 36 + K * FL.F_eigh(6) + len(pi) * (4 * 216 + 30 * 216) + AGG_C * K ** 3))   # priced as the support-sparse implementation (code builds the dense Gram: wall time is higher, W is the reference)
        allp = np.triu_indices(K, 1); noncand = np.ones(len(allp[0]), bool); key = set(zip(pi.tolist(), pj.tolist())); noncand = np.array([(a_, b_) not in key for a_, b_ in zip(*allp)])
        info = dict(n_pairs=int(len(pi)), n_all=int(len(allp[0])), aff_noncand_max=float(aff[allp][noncand].max()) if noncand.any() else 0.0)
    elif arm == 'SPA':
        dd = np.linalg.norm(cent[:, None, :] - cent[None, :, :], axis=2); aff = -dd; _w(cnt, 'grp', 6.0 * K * K + AGG_C * K ** 3)
    elif arm == 'OVL':    # DAOPHOT-style: overlap area of the PSF-dilated 4-sigma support boxes (no whitening, no ridge)
        pi, pj, inter, box = candidate_pairs(th, N, P.op.rp); aff = inter.astype(float); np.fill_diagonal(aff, 0.0); _w(cnt, 'grp', 12.0 * K * K + AGG_C * K ** 3)
    elif arm == 'RND':
        rg = np.random.default_rng(rng_seed); aff = rg.random((K, K)); aff = (aff + aff.T) / 2; _w(cnt, 'grp', 2.0 * K * K + AGG_C * K ** 3)
    else: raise ValueError(arm)
    return agglomerate(aff, cent, s), info


# ------------------------------------------------------------------ one group visit
def _decomp(Jg, AJg, r, x, P, rc):
    """SVD image-basis decomposition of a group (geo_core._iter_blk, generalised). Returns None if rank 0, else (Vr, sr, lam, Q, rq, rho)."""
    sn, a = P.sn, P.a; U, sv, Vt = np.linalg.svd(Jg, full_matrices=False); rho = int(np.sum(sv > rc * max(sv[0], 1e-300)))
    if rho == 0: return None
    Ur = U[:, :rho]; sr = sv[:rho]; Vr = Vt[:rho].T; B = (AJg @ Vr / sr) / sn; G = B.T @ B; lam, Q = np.linalg.eigh(G)
    rhs = B.T @ (r.ravel() / sn) - a * (Ur.T @ x.ravel()); return Vr, sr, lam, Q, Q.T @ rhs, rho


def _step(dec, kap, P):
    Vr, sr, lam, Q, rq, rho = dec; z = Q @ (rq / (lam + P.a + kap * P.LamA)); return Vr @ (z / sr)


def _visit(P, S, J, AJ, members, cfg, cnt, T, vlog):
    """Bounded finite update of one group with the current residual; True if accepted."""
    th, x, r, F = S['th'], S['x'], S['r'], S['F']; N, m, sn, a = P.N, P.m, P.sn, P.a; s = len(members); rc = cfg.get('rcond', GC.RCOND); f = cfg['f']; wA = P.wA
    idx = np.concatenate([np.arange(6 * k, 6 * k + 6) for k in members]); Jg = J[:, idx].copy(); AJg = AJ[:, idx].copy()
    t0 = time.perf_counter()
    act = GC.bound_active(th[members], -(AJg.T @ r.ravel()) / sn ** 2 + a * (Jg.T @ x.ravel()), N); _w(cnt, 'solve', 2 * FL.F_matvec(6 * s * m)); S['act'] += int(act.sum())
    if act.any(): Jg[:, act] = 0.0; AJg[:, act] = 0.0
    mode = cfg.get('mode', 'joint')
    if mode == 'joint' or s == 1:
        dec = _decomp(Jg, AJg, r, x, P, rc)
        if dec is None: T['solve'] += time.perf_counter() - t0; return False
        rho = dec[5]; _w(cnt, 'solve', FL.F_svd(m, 6 * s) + FL.F_gemm(m, 6 * s, rho) + FL.F_gram(m, rho) + FL.F_eigh(rho) + 2 * FL.F_matvec(m * rho))
        decs = [dec]
    else:
        decs = []
        for j in range(s):
            sl = slice(6 * j, 6 * j + 6); Jj = Jg[:, sl].copy(); AJj = AJg[:, sl].copy(); d_ = _decomp(Jj, AJj, r, x, P, rc)
            if d_ is not None: _w(cnt, 'solve', FL.F_svd(m, 6) + FL.F_gemm(m, 6, d_[5]) + FL.F_gram(m, d_[5]) + FL.F_eigh(d_[5]) + 2 * FL.F_matvec(m * d_[5]))
            decs.append(d_)
        if all(d_ is None for d_ in decs): T['solve'] += time.perf_counter() - t0; return False
    T['solve'] += time.perf_counter() - t0
    kap = float(np.max(S['kap'][members])); S['visits'] += 1
    for bt in range(BACKTRACKS):
        t1 = time.perf_counter()
        if mode == 'joint' or s == 1: delta = _step(decs[0], kap, P)
        else:
            D = np.zeros((6 * s, s))
            for j, d_ in enumerate(decs):
                if d_ is not None: D[6 * j:6 * j + 6, j] = _step(d_, kap, P)
            JD = Jg @ D; AJD = AJg @ D; M = AJD.T @ AJD / sn ** 2 + a * (JD.T @ JD); b = AJD.T @ r.ravel() / sn ** 2 - a * (JD.T @ x.ravel())
            _w(cnt, 'solve', 2 * FL.F_gemm(m, 6 * s, s) + 2 * FL.F_gram(m, s) + 2 * FL.F_matvec(m * s) + s ** 3)
            try: c = np.linalg.solve(M + 1e-12 * np.trace(M) / s * np.eye(s), b)
            except np.linalg.LinAlgError: c = np.zeros(s)
            delta = D @ c
        delta[act] = 0.0
        t6raw = th[members] + delta.reshape(s, 6); t6 = GC.clamp(t6raw, N); S['trials'] += 1; nc = int(np.sum(np.abs(t6raw - t6) > 0)); S['clamped'] += nc; S['clamp_trials'] += int(nc > 0)
        dg = P.render(t6) - P.render(th[members]); x2 = x + dg; r2 = r - P.op.apply(dg); cnt['A'] += 1; _w(cnt, 'check', wA + 2 * FL.F_render(s, N))
        dk = (t6 - th[members]).ravel(); jv = Jg @ dk; Aj = AJg @ dk; _w(cnt, 'check', 2 * FL.F_matvec(6 * s * m))
        F2 = 0.5 * float(np.sum(r2 * r2)) / sn ** 2 + 0.5 * a * float(np.sum(x2 * x2)); pred = GC._gain_pred_aj(P, r, x, jv, Aj); actual = F - F2
        guard = float(np.linalg.norm((x2 - x).ravel() - jv)) <= GUARD * float(np.linalg.norm(jv))
        ok = bool(pred > 0 and actual > 0 and actual / pred >= RHO_MIN and guard); T['check'] += time.perf_counter() - t1
        if ok:
            parts = [np.linalg.norm(AJg[:, 6 * j:6 * j + 6] @ dk[6 * j:6 * j + 6]) for j in range(s)]; comp = float(np.linalg.norm(Aj) / max(sum(parts), 1e-300))
            vlog.append(dict(s=s, bt=bt, ratio=float(actual / pred), gain=float(actual), comp=comp, kap=kap, mode=mode)); S['th'][members] = t6; S.update(x=x2, r=r2, F=F2)
            S['kap'][members] = max(kap / 3, KAPPA_MIN) if actual / pred >= 0.75 else kap; return True
        S['rej'] += 1
        if kap >= KAPPA_MAX: break
        kap = min(kap * f, KAPPA_MAX)
    S['kap'][members] = kap; return False


def jr_sweep(P, S, cfg, cnt, T, F_target=None, vtraj=None, sweep_no=0):
    th = S['th']; K = th.shape[0]; N, m = P.N, P.m; t0 = time.perf_counter()
    Jimg = GC.render_jac(th, N)[1]; _w(cnt, 'lin', FL.F_jbuild(Jimg.shape[0] * m)); AJ = P.op.apply_stack(Jimg).reshape(6 * K, m).T; cnt['A'] += 6 * K; _w(cnt, 'lin', 6 * K * P.wA)
    J = Jimg.reshape(6 * K, m).T; T['lin'] += time.perf_counter() - t0
    R_ = int(cfg.get('R', 1)); t0 = time.perf_counter()
    if R_ > 1 and S.get('groups') is not None and (sweep_no - 1) % R_ != 0: groups, info = S['groups'], dict(reused=True)      # reuse of the previous partition: no grouping cost this sweep
    else: groups, info = make_groups(P, th, Jimg, AJ, cfg, cnt, rng_seed=cfg.get('seed', 0) * 100003 + sweep_no); S['groups'] = groups
    T['grp'] += time.perf_counter() - t0
    order = sorted(range(len(groups)), key=lambda g: (float(np.mean(th[groups[g], 2])), float(np.mean(th[groups[g], 1])))); vlog = []; any_ok = False; hit = False
    S['sweeps'].append(dict(sizes=[len(g) for g in groups], info=info, groups=[list(map(int, g)) for g in groups]))
    for g in order:
        ok = _visit(P, S, J, AJ, groups[g], cfg, cnt, T, vlog); any_ok |= ok
        if vtraj is not None: vtraj.append((cnt['W'], S['F']))
        if F_target is not None and S['F'] <= F_target: hit = True; break
    S['sweeps'][-1]['visits'] = vlog
    if hit: return True, True
    if any_ok:
        t0 = time.perf_counter(); F_true, x_t, r_t = P.F_of(S['th'], cnt); _w(cnt, 'refresh', P.wA + FL.F_render(K, N)); S.update(x=x_t, r=r_t, F=F_true); T['refresh'] += time.perf_counter() - t0
    return any_ok, False


def jr_solve(P, th0, cfg, max_sweeps=300, W_cap=None, F_target=None, keep_theta=False):
    cnt = dict(A=0, W=0.0, cat={c: 0.0 for c in CATS}); T = dict(lin=0.0, grp=0.0, solve=0.0, check=0.0, refresh=0.0)
    th = GC.clamp(th0, P.N); F, x, r = P.F_of(th, cnt); K = th.shape[0]; _w(cnt, 'refresh', P.wA + FL.F_render(K, P.N))   # initial state evaluation is charged too
    S = dict(th=th.copy(), x=x, r=r, F=F, kap=np.full(K, cfg['kappa0']), rej=0, trials=0, clamped=0, clamp_trials=0, act=0, visits=0, sweeps=[], groups=None)
    traj = [(0, F, 0.0, 0, 0.0, 0.0)]; vtraj = [(0.0, F)]; th_hist = [th.copy()] if keep_theta else None; fails = 0; small = 0; stop = 'max_sweeps'; clock0 = time.perf_counter()
    for it in range(1, max_sweeps + 1):
        Fold = S['F']; ok, hit = jr_sweep(P, S, cfg, cnt, T, F_target, vtraj, it)
        traj.append((it, S['F'], cnt['W'], cnt['A'], time.perf_counter() - clock0, cnt['cat']['grp']))
        if keep_theta: th_hist.append(S['th'].copy())
        if hit: stop = 'target'; break
        if W_cap is not None and cnt['W'] >= W_cap: stop = 'cap'; break
        if not ok:
            fails += 1
            if fails >= 3: stop = 'no_step'; break
            continue
        fails = 0; small = small + 1 if (Fold - S['F']) <= 1e-9 * abs(Fold) else 0
        if small >= 3: stop = 'converged'; break
    out = dict(theta=S['th'], F=S['F'], traj=traj, vtraj=vtraj, stop=stop, rej=S['rej'], trials=S['trials'], clamped=S['clamped'], visits=S['visits'], cnt=cnt, T=T, sweeps=S['sweeps'], kap=S['kap'])
    if keep_theta: out['th_hist'] = th_hist
    return out
