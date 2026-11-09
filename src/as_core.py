"""AS contract v2.1 core (numpy only). METHOD-SIDE code: no function in this module may take or read the clean image (gate V6).
Frozen spec: contracts/AS_CONTRACT_CANDIDATE_v2_1.md (sha256 in contracts/FROZEN_AS_CONTRACT_v2_1.md).
Model: x(theta)=sum_k a_k exp(-1/2 (u-m_k)^T Sigma_k^-1 (u-m_k)), Sigma=L L^T, L=[[e^l11,0],[l21,e^l22]], theta_k=(a,mx,my,l11,l21,l22); pixel centres u=(j+.5,i+.5)."""
import numpy as np, time

N = 32
LMIN, LMAX = float(np.log(0.6)), float(np.log(12.0))
CMAX = 1.5          # birth amplitude coefficient bound
FLOOR = 1e-3        # |P_perp v|/|v| floor for JOINT / JOINT_FREE
RCOND = 1e-10
REG = 1e-6          # loss regulariser 1e-6 sum a^2
LM_CAP = 20         # max rejected steps per refit
_UY, _UX = np.meshgrid(np.arange(N) + 0.5, np.arange(N) + 0.5, indexing='ij')


# ------------------------------------------------------------------ operator
def refl_B(sb):
    if sb is None:
        return np.eye(N)
    r = max(1, int(np.ceil(3 * sb)))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sb) ** 2); k /= k.sum()
    B = np.zeros((N, N))
    for i in range(N):
        for t, w in zip(range(-r, r + 1), k):
            j = i + t
            if j < 0: j = -j - 1
            if j >= N: j = 2 * N - 1 - j
            B[i, j] += w
    return B


class Op:
    """A = B (x) B acting on row-major vec(X): A x = vec(B X B^T); adjoint A^T = B^T (x) B^T. Separable application only; dense() is for unit tests."""
    def __init__(self, sb):
        self.sb = sb; self.B = refl_B(sb); self.Bt = np.ascontiguousarray(self.B.T)

    def apply(self, X):
        return self.B @ X @ self.Bt

    def adj(self, X):
        return self.Bt @ X @ self.B

    def apply_stack(self, Xs):  # (n,N,N)
        return np.einsum('ij,njk,kl->nil', self.B, Xs, self.Bt, optimize=True)

    def dense(self):
        return np.kron(self.B, self.B)

    def tikhonov_gcv(self, y):
        """Context number (K-c): Tikhonov deconvolution in the SVD basis of B, lambda by GCV on a log grid."""
        U, s, Vt = np.linalg.svd(self.B)
        C = U.T @ y @ U                      # coefficients in left basis (A = (U S V^T) (x) (U S V^T))
        sv = np.outer(s, s); best = None
        for lam in 10.0 ** np.arange(-10, 1.01, 0.25):
            f = sv ** 2 / (sv ** 2 + lam)
            gcv = np.sum(((1 - f) * C) ** 2) / (N * N - f.sum()) ** 2
            if best is None or gcv < best[0]: best = (gcv, lam, f)
        _, lam, f = best
        Xc = (sv / (sv ** 2 + lam)) * C
        return Vt.T @ Xc @ Vt, lam


# ------------------------------------------------------------------ Gaussian image and analytic Jacobian
def _parts(p):
    a, mx, my, l11, l21, l22 = p
    L11 = np.exp(l11); L22 = np.exp(l22)
    dx = _UX - mx; dy = _UY - my
    z1 = dx / L11; z2 = (dy * L11 - l21 * dx) / (L11 * L22)
    e = np.exp(-0.5 * (z1 * z1 + z2 * z2))
    return a * e, e, z1, z2, L11, L22


def g_img(p):
    return _parts(p)[0]


def g_jac(p):
    a, mx, my, l11, l21, l22 = p
    g, e, z1, z2, L11, L22 = _parts(p)
    w1 = z1 / L11 - l21 * z2 / (L11 * L22)   # (L^-T z)_x
    w2 = z2 / L22                            # (L^-T z)_y
    J = np.empty((6, N, N))
    J[0] = e; J[1] = g * w1; J[2] = g * w2
    J[3] = g * w1 * z1 * L11; J[4] = g * w2 * z1; J[5] = g * w2 * z2 * L22
    return g, J


def render(th):
    x = np.zeros((N, N))
    for p in th: x += g_img(p)
    return x


def render_jac(th):
    x = np.zeros((N, N)); Js = []
    for p in th:
        g, J = g_jac(p); x += g; Js.append(J)
    return x, np.concatenate(Js, 0)       # (K*6,N,N)


def clamp(th):
    t = np.array(th, dtype=float, copy=True)
    t[:, 1] = np.clip(t[:, 1], -4, N + 4); t[:, 2] = np.clip(t[:, 2], -4, N + 4)
    t[:, 3] = np.clip(t[:, 3], LMIN, LMAX); t[:, 5] = np.clip(t[:, 5], LMIN, LMAX)
    t[:, 4] = np.clip(t[:, 4], -12, 12)
    return t


def sigma_of(p3):
    l11, l21, l22 = p3
    L = np.array([[np.exp(l11), 0.0], [l21, np.exp(l22)]]); return L @ L.T


def chol_params(S):
    L = np.linalg.cholesky(S); return float(np.log(L[0, 0])), float(L[1, 0]), float(np.log(L[1, 1]))


# ------------------------------------------------------------------ loss and Levenberg-Marquardt
def loss(op, y, th, sn):
    r = (y - op.apply(render(th))) / sn
    return 0.5 * float(np.sum(r * r)) + REG * float(np.sum(th[:, 0] ** 2))


def sse_half(op, y, th):
    r = y - op.apply(render(th)); return 0.5 * float(np.sum(r * r))


def lm(op, y, th, sn, steps, lam0=1e-3, cap=LM_CAP):
    """Analytic-Jacobian LM, lambda reset to lam0 on entry. A step = one accepted update; rejected trials are counted and capped.
    Returns (theta, loss, info)."""
    th = clamp(th); K = th.shape[0]
    Lc = loss(op, y, th, sn); lam = lam0; rej = 0; acc = 0; capped = False
    aidx = np.arange(K) * 6
    for _ in range(steps):
        x, Jimg = render_jac(th)
        r = ((y - op.apply(x)) / sn).ravel()
        J = op.apply_stack(Jimg).reshape(K * 6, -1).T / sn          # (N^2, 6K)
        H = J.T @ J; g = J.T @ r
        H[aidx, aidx] += 2 * REG; g[aidx] -= 2 * REG * th[:, 0]
        D = np.diag(np.diag(H) + 1e-12); ok = False
        for _t in range(10):
            try:
                d = np.linalg.solve(H + lam * D, g)
            except np.linalg.LinAlgError:
                lam = min(lam * 10, 1e6); rej += 1; continue
            th2 = clamp(th + d.reshape(th.shape)); L2 = loss(op, y, th2, sn)
            if L2 <= Lc:
                th, Lc = th2, L2; lam = max(lam * 0.3, 1e-9); acc += 1; ok = True; break
            lam = min(lam * 10, 1e6); rej += 1
            if rej > cap: capped = True; break
        if capped or not ok: break
    return th, Lc, dict(acc=acc, rej=rej, capped=capped)


def ls_amplitudes(op, y, th):
    cols = []
    for p in th:
        q = np.array(p, dtype=float); q[0] = 1.0; cols.append(op.apply(g_img(q)).ravel())
    a = np.linalg.lstsq(np.stack(cols, 1), y.ravel(), rcond=None)[0]
    t = np.array(th, dtype=float, copy=True); t[:, 0] = a; return t


def grid_init(sig, kind='3x2', jitter=0.0, seed=1):
    if kind == '3x2':
        xs = [N / 6, N / 2, 5 * N / 6]; ys = [N / 4, 3 * N / 4]; pts = [(x, y) for y in ys for x in xs]
    else:
        c = [N * (i + 0.5) / 6 for i in range(6)]; pts = [(x, y) for y in c for x in c]
    rng = np.random.default_rng(seed); th = []
    for (x, y) in pts:
        if jitter > 0: x += rng.uniform(-jitter, jitter); y += rng.uniform(-jitter, jitter)
        th.append([1.0, x, y, np.log(sig), 0.0, np.log(sig)])
    return np.array(th)


# ------------------------------------------------------------------ candidates and scores (shared candidate set C_t for all rules)
def projectors(op, th):
    K = th.shape[0]; _, Jimg = render_jac(th)
    AJ = op.apply_stack(Jimg).reshape(K * 6, -1).T                 # (N^2, 6K), unweighted
    U, s, _ = np.linalg.svd(AJ, full_matrices=False)
    k = int(np.sum(s > RCOND * s[0])); Uk = U[:, :k]
    blocks = []
    for kk in range(K):
        Ub, sb_, _ = np.linalg.svd(AJ[:, 6 * kk:6 * kk + 6], full_matrices=False)
        blocks.append(Ub[:, :int(np.sum(sb_ > RCOND * sb_[0]))])
    return AJ, Uk, blocks, float(s[0]), (U, s)


def gen_candidates(op, th, r_img, Bn=12, sigmas=(1.5, 3.0), alphas=(0.4, 0.7)):
    """Births: |A^T r| 3x3 non-max-suppression maxima (min spacing 2 px), top Bn, shapes sigma in sigmas (unit peak).
    Splits: every unclamped parent, major and minor axis, alpha in alphas, mass-preserving moment split (child peak amp (a/2) sqrt(detS/detS'))."""
    cands = []; n_clamped = 0
    g = np.abs(op.adj(r_img)); P = np.pad(g, 1, constant_values=-np.inf)
    nb = np.max([P[1 + di:1 + di + N, 1 + dj:1 + dj + N] for di in (-1, 0, 1) for dj in (-1, 0, 1) if (di, dj) != (0, 0)], axis=0)
    idx = np.argwhere(g >= nb); order = np.argsort(-g[idx[:, 0], idx[:, 1]], kind='stable'); picked = []
    for o in order:
        i, j = idx[o]
        if all(max(abs(i - a), abs(j - b)) >= 2 for a, b in picked):
            picked.append((int(i), int(j)))
        if len(picked) >= Bn: break
    for (i, j) in picked:
        for sg in sigmas:
            row = np.array([1.0, j + 0.5, i + 0.5, np.log(sg), 0.0, np.log(sg)])
            cands.append(dict(type='b', parent=-1, row=row, q=g_img(row)))
    for k in range(th.shape[0]):
        a = th[k, 0]; m = th[k, 1:3]; l11, l22 = th[k, 3], th[k, 5]
        if min(abs(l11 - LMIN), abs(l11 - LMAX), abs(l22 - LMIN), abs(l22 - LMAX)) < 1e-9:
            n_clamped += 1; continue
        S = sigma_of(th[k, 3:6]); w, V = np.linalg.eigh(S)
        for ax in (1, 0):
            e = V[:, ax]; se = np.sqrt(w[ax])
            for al in alphas:
                d = al * se; Sc = S - d * d * np.outer(e, e)
                ac = (a / 2) * np.sqrt(np.linalg.det(S) / np.linalg.det(Sc)); cp = chol_params(Sc)
                c1 = np.array([ac, *(m + d * e), *cp]); c2 = np.array([ac, *(m - d * e), *cp])
                ch = clamp(np.stack([c1, c2]))
                cands.append(dict(type='s', parent=k, rows=ch, q=g_img(ch[0]) + g_img(ch[1]) - g_img(th[k])))
    return cands, n_clamped


def score_candidates(op, th, y, cands, AJ, Uk, blocks):
    """Returns dict of score arrays (len C) for rules OMP, BLOCK, JOINT, JOINT_FREE plus bookkeeping."""
    r = (y - op.apply(render(th))).ravel()
    C = len(cands)
    V = op.apply_stack(np.stack([c['q'] for c in cands])).reshape(C, -1).T          # (N^2, C)
    Vp = V - Uk @ (Uk.T @ V)
    rv = r @ V; rvp = r @ Vp; vv = np.sum(V * V, 0); vpvp = np.sum(Vp * Vp, 0)
    fl = np.sqrt(vpvp) / (np.sqrt(vv) + 1e-300)
    sc = {k: np.full(C, -np.inf) for k in ('OMP', 'BLOCK', 'JOINT', 'JOINT_FREE')}
    c0 = np.full(C, np.nan); cols = np.full(C, np.nan)
    for c in range(C):
        ok = fl[c] >= FLOOR
        if cands[c]['type'] == 's':
            sc['OMP'][c] = rv[c] - 0.5 * vv[c]
            Ub = blocks[cands[c]['parent']]; vb = V[:, c] - Ub @ (Ub.T @ V[:, c])
            sc['BLOCK'][c] = r @ vb - 0.5 * vb @ vb
            if ok:
                sc['JOINT'][c] = rvp[c] - 0.5 * vpvp[c]
                sc['JOINT_FREE'][c] = max(rvp[c], 0.0) ** 2 / (2 * vpvp[c])
        else:
            cr = float(np.clip(rv[c] / vv[c], -CMAX, CMAX)); sc['OMP'][c] = cr * rv[c] - 0.5 * cr * cr * vv[c]
            sc['BLOCK'][c] = sc['OMP'][c]; c0[c] = cr
            if ok:
                cj = float(np.clip(rvp[c] / vpvp[c], -CMAX, CMAX)); cols[c] = cj
                sc['JOINT'][c] = cj * rvp[c] - 0.5 * cj * cj * vpvp[c]
                sc['JOINT_FREE'][c] = max(rvp[c], 0.0) ** 2 / (2 * vpvp[c])
    return sc, dict(c0=c0, cols=cols, floor=fl, r=r, V=V)


def apply_edit(th, cand, c_init=None):
    """Theta after the edit. Split: replace parent by two children (c=1, exact). Birth: append unit shape scaled by c_init."""
    if cand['type'] == 's':
        return np.vstack([np.delete(th, cand['parent'], 0), cand['rows']])
    row = cand['row'].copy(); row[0] = c_init; return np.vstack([th, row[None]])


def execute(op, y, th, cand, aux_c0, aux_cols, sn, steps):
    """Standard edit execution (identical for every rule/arm): split c=1; birth from {c0, c*_OLS} (the latter only if above the floor), refit `steps` LM steps each, keep lower loss."""
    if cand['type'] == 's':
        t, L, info = lm(op, y, apply_edit(th, cand), sn, steps); return t, L, info
    best = None
    inits = [aux_c0] + ([aux_cols] if np.isfinite(aux_cols) else [])
    for ci in inits:
        t, L, info = lm(op, y, apply_edit(th, cand, ci), sn, steps)
        if best is None or L < best[1]: best = (t, L, info)
    return best


def rank_corr(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 3: return float('nan')
    ra = np.argsort(np.argsort(a[m])); rb = np.argsort(np.argsort(b[m]))
    if ra.std() == 0 or rb.std() == 0: return float('nan')
    return float(np.corrcoef(ra, rb)[0, 1])


RULES = ('OMP', 'BLOCK', 'JOINT', 'JOINT_FREE')


def choose(rule, sc, mask, rng):
    idx = np.where(mask)[0]
    if rule == 'RAND': return int(rng.choice(idx))
    s = sc[rule][idx]
    if not np.any(np.isfinite(s)): s = sc['OMP'][idx]
    s = np.where(np.isfinite(s), s, -np.inf)
    return int(idx[int(np.argmax(s))])        # first max (deterministic)


def cand_hash(cands):
    """V16: hash of the candidate set (types, parents, exact image increments)."""
    import hashlib
    h = hashlib.sha1()
    for c in cands:
        h.update(c['type'].encode()); h.update(str(c['parent']).encode()); h.update(np.ascontiguousarray(c['q']).tobytes())
    return h.hexdigest()[:16]


def _ckpt_load(ckpt):
    import json, os
    if ckpt and os.path.exists(ckpt):
        d = json.load(open(ckpt)); return d['traj'], d['logs']
    return None, None


def _ckpt_save(ckpt, traj, logs):
    import json, os
    if not ckpt: return
    os.makedirs(os.path.dirname(ckpt) or '.', exist_ok=True)
    tmp = ckpt + '.tmp'; json.dump(dict(traj=traj, logs=logs), open(tmp, 'w')); os.replace(tmp, ckpt)


def mask_for(cands, only):
    t = np.array([c['type'] for c in cands])
    return np.ones(len(cands), bool) if only is None else (t == only)


def initial_state(op, y, sn, init_sigma=6.0, T0=30):
    th = ls_amplitudes(op, y, grid_init(init_sigma)); return lm(op, y, th, sn, T0)


# ------------------------------------------------------------------ path runner (rule arms; y-only)
def run_path(y, op, sn, rule, init_sigma=6.0, only=None, seed=0, S=30, Tr=15, T0=30, diag_top5=False):
    """Greedy capacity growth K0=6 -> 36 with `rule` in {RAND, OMP, BLOCK, JOINT, JOINT_FREE}. Returns dict of trajectory (theta per step, logs)."""
    rng = np.random.default_rng(seed); t_start = time.time()
    th, L, info0 = initial_state(op, y, sn, init_sigma, T0)
    traj = [th.tolist()]; logs = []
    for step in range(S):
        t1 = time.time(); r_img = y - op.apply(render(th))
        cands, ncl = gen_candidates(op, th, r_img)
        AJ, Uk, blocks, s0, us = projectors(op, th)
        sc, aux = score_candidates(op, th, y, cands, AJ, Uk, blocks)
        stat = float(np.linalg.norm(AJ.T @ aux['r']) / (s0 * np.linalg.norm(aux['r']) + 1e-300))
        mask = mask_for(cands, only)
        ch = choose(rule, sc, mask, rng)
        stab = None
        if rule == 'JOINT':      # V10: JOINT top-1 under rcond 1e-8 / 1e-12 (same candidate set)
            stab = {}
            U_, s_ = us
            for rc in (1e-8, 1e-12):
                k_ = int(np.sum(s_ > rc * s_[0])); sc2, _a = score_candidates(op, th, y, cands, AJ, U_[:, :k_], blocks)
                stab[str(rc)] = int(choose('JOINT', sc2, mask, rng)) == ch
        tops = {k: int(choose(k, sc, np.ones(len(cands), bool), rng)) for k in RULES}
        rho = {k + '~JOINT': rank_corr(sc[k], sc['JOINT']) for k in ('OMP', 'BLOCK', 'JOINT_FREE')}
        t2 = time.time()
        L_before = sse_half(op, y, th)
        th_new, L_new, info = execute(op, y, th, cands[ch], aux['c0'][ch], aux['cols'][ch], sn, Tr)
        rec = dict(step=step, K=int(th.shape[0]), n_cand=len(cands), cand_hash=cand_hash(cands), n_split=int(sum(c['type'] == 's' for c in cands)), chosen=ch, chosen_type=cands[ch]['type'],
                   tops=tops, rho=rho, stat=stat, v10_stable=stab, n_clamped_parent=ncl, n_below_floor=int(np.sum(aux['floor'] < FLOOR)),
                   pred_joint=float(sc['JOINT'][ch]) if np.isfinite(sc['JOINT'][ch]) else None, real_half_sse=L_before - sse_half(op, y, th_new),
                   train_loss=float(L_new), lm=info, t_score=t2 - t1, t_refit=time.time() - t2)
        if diag_top5:
            order = np.argsort(-np.where(np.isfinite(sc['JOINT']), sc['JOINT'], -np.inf))[:5]; d5 = []
            for o in order:
                if not np.isfinite(sc['JOINT'][o]): continue
                tt, _, _ = execute(op, y, th, cands[int(o)], aux['c0'][o], aux['cols'][o], sn, Tr)
                d5.append((float(sc['JOINT'][o]), L_before - sse_half(op, y, tt)))
            rec['diag_top5_pred_real'] = d5
        logs.append(rec); th = th_new; traj.append(th.tolist())
    return dict(rule=rule, only=only, init_sigma=init_sigma, traj=traj, logs=logs, T0_loss=float(L), t_total=time.time() - t_start)


# ------------------------------------------------------------------ legal oracle (training loss) over full / shortlist candidate set
def run_oracle_y(y, op, sn, mode='short', seed=0, S=30, Tr=15, T0=30, topk=8, ckpt=None):
    """ORACLE_y-full (mode='full') / ORACLE_ys (mode='short'): trial-refit candidates T_o=T_r steps, pick the lowest TRAINING loss; continues on its own path.
    ckpt: optional per-step checkpoint file (resumable; the path state at the start of a step is exactly theta, no rng is used)."""
    t_start = time.time(); tr0, lg0 = _ckpt_load(ckpt)
    if tr0 is not None: traj, logs = tr0, lg0; th = np.array(traj[-1])
    else: th, L, info0 = initial_state(op, y, sn, 6.0, T0); traj = [th.tolist()]; logs = []
    for step in range(len(logs), S):
        r_img = y - op.apply(render(th)); cands, ncl = gen_candidates(op, th, r_img)
        AJ, Uk, blocks, s0, us = projectors(op, th); sc, aux = score_candidates(op, th, y, cands, AJ, Uk, blocks)
        if mode == 'full': idxs = list(range(len(cands)))
        else:
            sel = set()
            for k in RULES:
                s = sc[k].copy(); s[~np.isfinite(s)] = -np.inf; sel.update(int(i) for i in np.argsort(-s, kind='stable')[:topk] if np.isfinite(s[i]))
            idxs = sorted(sel)
        best = None
        for c in idxs:
            t, Lc, info = execute(op, y, th, cands[c], aux['c0'][c], aux['cols'][c], sn, Tr)
            if best is None or Lc < best[1]: best = (t, Lc, c)
        th = best[0]; traj.append(th.tolist())
        logs.append(dict(step=step, K=int(th.shape[0]) - 1, n_cand=len(cands), cand_hash=cand_hash(cands), n_trials=len(idxs), chosen=int(best[2]), chosen_type=cands[best[2]]['type'], train_loss=float(best[1])))
        _ckpt_save(ckpt, traj, logs)
    return dict(rule='ORACLE_y_' + mode, traj=traj, logs=logs, t_total=time.time() - t_start)


# ------------------------------------------------------------------ fixed-capacity arm
def run_fixed_k(y, op, sn, kind, S=30, Tr=15, T0=30):
    """FIXED-K: K_max=36 from a preset grid init, same total LM budget (T0 + S*Tr) in the same refit chunking. kind in {'g3','g2','j25'}."""
    if kind == 'g3': th0 = grid_init(3.0, '6x6')
    elif kind == 'g2': th0 = grid_init(2.0, '6x6')
    else: th0 = grid_init(2.5, '6x6', jitter=1.5, seed=1)
    th = ls_amplitudes(op, y, th0); th, L, _ = lm(op, y, th, sn, T0)
    for _ in range(S): th, L, _ = lm(op, y, th, sn, Tr)
    return dict(rule='FIXED_' + kind, theta=th.tolist(), train_loss=float(L))
