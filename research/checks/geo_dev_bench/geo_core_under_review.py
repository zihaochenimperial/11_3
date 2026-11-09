"""GEO core, implements contracts/GEO_CONTRACT_CANDIDATE_v2.md (frozen sha in contracts/FROZEN_GEO_CONTRACT_v2.md). numpy + scipy only.
METHOD-SIDE code: no function here takes or reads a clean image (gate V5).
Model: x(theta) = sum_k w_k exp(-1/2 (u-m_k)^T Sigma_k^-1 (u-m_k)), Sigma = L L^T, L = [[e^l11,0],[l21,e^l22]], theta_k = (w,mx,my,l11,l21,l22).
Objective F_a(theta) = 1/(2 sn^2) ||y - A x||^2 + a/2 ||x||^2 (x_ref = 0).
Step (all arms): image-metric-damped Gauss-Newton P: (J^T A^T W^2 A J + (a+eta) J^T J) delta = J^T A^T W^2 r - a J^T x, eta = kappa * Lam_A, Lam_A = ||W A||_2^2.
Acceptance (all arms): theta' = clamp(theta+delta); delta_c = theta'-theta; jv_c = J delta_c; pred(jv_c) > 0; act = F(theta)-F(theta') > 0;
act/pred >= 1e-4; ||x(theta')-x(theta)-jv_c|| <= 0.5 ||jv_c||."""
import time
import numpy as np
import scipy.sparse as sp
import geo_flops as FL
from scipy.sparse.linalg import lsmr, LinearOperator

LMIN, LMAX = float(np.log(0.6)), float(np.log(12.0))
RCOND = 1e-8
RHO_MIN = 1e-4
GUARD = 0.5
KAPPA_MIN, KAPPA_MAX = 1e-12, 1e4
BACKTRACKS = 10
LM_MAX = 1e8

_UC = {}


def _uc(N):
    if N not in _UC:
        u = np.arange(N) + 0.5
        _UC[N] = np.meshgrid(u, u, indexing='ij')      # (UY, UX)
    return _UC[N]


# ------------------------------------------------------------------ operator
def refl_B(N, sb):
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
    """A = B (x) B acting on an N x N image: A X = B X B^T; adjoint B^T X B."""
    def __init__(self, N, sb):
        self.N = N; self.sb = sb; self.B = refl_B(N, sb); self.Bt = np.ascontiguousarray(self.B.T)
        self.normA = float(np.linalg.norm(self.B, 2)) ** 2          # ||A||_2 = ||B||_2^2

    def apply(self, X):
        return self.B @ X @ self.Bt

    def adj(self, X):
        return self.Bt @ X @ self.B

    def apply_stack(self, Xs):
        return np.matmul(np.matmul(self.B, Xs), self.Bt)


# ------------------------------------------------------------------ Gaussian image and analytic Jacobian
def chol_from_sigma(S):
    L = np.linalg.cholesky(S); return np.array([np.log(L[0, 0]), L[1, 0], np.log(L[1, 1])])


def _parts(th, N):
    UY, UX = _uc(N)
    a, mx, my, l11, l21, l22 = (th[:, i][:, None, None] for i in range(6))
    L11 = np.exp(l11); L22 = np.exp(l22)
    dx = UX[None] - mx; dy = UY[None] - my
    z1 = dx / L11; z2 = (dy * L11 - l21 * dx) / (L11 * L22)
    e = np.exp(-0.5 * (z1 * z1 + z2 * z2))
    return a * e, e, z1, z2, L11, L22, l21


def render(th, N):
    return _parts(th, N)[0].sum(0)


def render_jac(th, N):
    g, e, z1, z2, L11, L22, l21 = _parts(th, N)
    w1 = z1 / L11 - l21 * z2 / (L11 * L22)
    w2 = z2 / L22
    J = np.stack([e, g * w1, g * w2, g * w1 * z1 * L11, g * w2 * z1, g * w2 * z2 * L22], axis=1)   # (K,6,N,N)
    return g.sum(0), J.reshape(-1, N, N)                                                              # row 6k+j = d x / d theta_{k,j}


def _window_parts(p, N, rad):
    """Truncated (Mahalanobis radius `rad`) render and 6 derivative maps of ONE Gaussian on its bounding window. Returns (rows, g, Jw(6,n)) with pixel indices."""
    w, mx, my, l11, l21, l22 = p
    L11 = np.exp(l11); L22 = np.exp(l22)
    sx = rad * L11; sy = rad * np.sqrt(l21 * l21 + L22 * L22)
    j0 = max(0, int(np.floor(mx - sx - 0.5))); j1 = min(N, int(np.ceil(mx + sx + 0.5)) + 1)
    i0 = max(0, int(np.floor(my - sy - 0.5))); i1 = min(N, int(np.ceil(my + sy + 0.5)) + 1)
    if j1 <= j0 or i1 <= i0: return None
    UY, UX = np.meshgrid(np.arange(i0, i1) + 0.5, np.arange(j0, j1) + 0.5, indexing='ij')
    dx = UX - mx; dy = UY - my
    z1 = dx / L11; z2 = (dy * L11 - l21 * dx) / (L11 * L22)
    q = z1 * z1 + z2 * z2; msk = q <= rad * rad
    if not msk.any(): return None
    e = np.exp(-0.5 * q) * msk; g = w * e
    w1 = z1 / L11 - l21 * z2 / (L11 * L22); w2 = z2 / L22
    Jw = np.stack([e, g * w1, g * w2, g * w1 * z1 * L11, g * w2 * z1, g * w2 * z2 * L22], 0)[:, msk]
    rows = (np.arange(i0, i1)[:, None] * N + np.arange(j0, j1)[None, :])[msk]
    return rows, g[msk], Jw


def render_trunc(th, N, rad=4.0):
    x = np.zeros(N * N)
    for p in th:
        r = _window_parts(p, N, rad)
        if r is not None: np.add.at(x, r[0], r[1])
    return x.reshape(N, N)


def render_jac_sparse(th, N, rad=4.0):
    x = np.zeros(N * N); rr = []; cc = []; vv = []
    for k, p in enumerate(th):
        r = _window_parts(p, N, rad)
        if r is None: continue
        rows, g, Jw = r; np.add.at(x, rows, g)
        for j in range(6):
            rr.append(rows); cc.append(np.full(rows.size, 6 * k + j)); vv.append(Jw[j])
    if rr:
        J = sp.csr_matrix((np.concatenate(vv), (np.concatenate(rr), np.concatenate(cc))), shape=(N * N, 6 * th.shape[0]))
    else:
        J = sp.csr_matrix((N * N, 6 * th.shape[0]))
    return x.reshape(N, N), J


def clamp(th, N):
    t = np.array(th, dtype=float, copy=True)
    t[:, 1] = np.clip(t[:, 1], -4, N + 4); t[:, 2] = np.clip(t[:, 2], -4, N + 4)
    t[:, 3] = np.clip(t[:, 3], LMIN, LMAX); t[:, 5] = np.clip(t[:, 5], LMIN, LMAX)
    t[:, 4] = np.clip(t[:, 4], -12, 12)
    return t


_LO = np.array([-np.inf, -4.0, -4.0, LMIN, -12.0, LMIN]); _HI = np.array([np.inf, 4.0, 4.0, LMAX, 12.0, LMAX])


def bound_active(th, g, N):
    """Projected-gradient active set (pre-D addendum item 6, all arms): True for coordinates sitting on a box bound whose descent direction -g points outward.
    Such coordinates are frozen (their Jacobian columns zeroed) for this outer iteration, so clamping cannot destroy the descent property of the step."""
    hi = _HI.copy(); hi[1] += N; hi[2] += N
    t = np.asarray(th); G = np.asarray(g).reshape(t.shape)
    return (((t <= _LO + 1e-12) & (G > 0)) | ((t >= hi - 1e-12) & (G < 0))).ravel()


# ------------------------------------------------------------------ problem, objective, init
class Prob:
    def __init__(self, N, sb, y, sn, a, renderer=None):
        self.N = N; self.m = N * N; self.op = Op(N, sb); self.y = y; self.sn = float(sn); self.a = float(a)
        self.render = renderer if renderer is not None else (lambda th: render(th, N))
        self.LamA = self.op.normA ** 2 / self.sn ** 2         # ||W A||_2^2

    def F_of(self, th, cnt=None):
        x = self.render(th); r = self.y - self.op.apply(x)
        if cnt is not None: cnt['A'] += 1
        F = 0.5 * float(np.sum(r * r)) / self.sn ** 2 + 0.5 * self.a * float(np.sum(x * x))
        return F, x, r


def grid_init(prob, K):
    """K square. Grid centres, isotropic sigma = spacing/2, amplitudes by least squares on y only (as_core.ls_amplitudes logic)."""
    N = prob.N; q = int(round(np.sqrt(K))); assert q * q == K
    c = [N * (i + 0.5) / q for i in range(q)]; sp_ = N / q; ls = float(np.log(sp_ / 2))
    th = np.array([[1.0, x, y, ls, 0.0, ls] for y in c for x in c])
    cols = [prob.op.apply(prob.render(p.reshape(1, 6))).ravel() for p in th]
    th[:, 0] = np.linalg.lstsq(np.stack(cols, 1), prob.y.ravel(), rcond=None)[0]
    return th


def _w(cnt, v, diag=False):
    cnt['W'] += v
    if diag: cnt['Wd'] += v


def _gain_pred_aj(P, r, x, jv, Aj):
    return float(Aj @ r.ravel()) / P.sn ** 2 - P.a * float(jv @ x.ravel()) - 0.5 * (float(Aj @ Aj) / P.sn ** 2 + P.a * float(jv @ jv))


def _gain_pred(P, r, x, jv, cnt):
    """A applied to jv: COUNTED (A1.4 convention for LSMR / PCG arms)."""
    Aj = P.op.apply(jv.reshape(P.N, P.N)).ravel(); cnt['A'] += 1; _w(cnt, FL.F_A(P.N))
    return _gain_pred_aj(P, r, x, jv, Aj)


def _accept(P, S, th2raw, Jmul, cnt, T, AJmul=None, wmv=0.0):
    """Common acceptance. Uses the CLAMPED step for pred and the guard (contract C3). Returns (ok, ratio, th2, x2, r2, F2).
    AJmul given (GEO/BJ/LMD): A*jv_c = (AJ) delta_c costs 0 A-applications (A1.4); wmv = flops of the matrix-vector products done here."""
    t0 = time.perf_counter()
    th, x, r, F = S['th'], S['x'], S['r'], S['F']
    th2 = clamp(th2raw, P.N); S['trials'] += 1; nc = int(np.sum(np.abs(th2raw - th2) > 0)); S['clamped'] += nc; S['clamp_trials'] += int(nc > 0)
    dc = (th2 - th).ravel(); jv = Jmul(dc); _w(cnt, wmv)
    F2, x2, r2 = P.F_of(th2, cnt); _w(cnt, FL.F_A(P.N) + FL.F_render(th.shape[0], P.N))
    pred = _gain_pred(P, r, x, jv, cnt) if AJmul is None else _gain_pred_aj(P, r, x, jv, AJmul(dc))
    act = F - F2
    guard = float(np.linalg.norm((x2 - x).ravel() - jv)) <= GUARD * float(np.linalg.norm(jv))
    ok = bool(pred > 0 and act > 0 and act / pred >= RHO_MIN and guard)
    T['back'] += time.perf_counter() - t0
    return ok, (act / pred if pred > 0 else -1.0), th2, x2, r2, F2


def _finish(S, ok, ratio, th2, x2, r2, F2, kap, f, key='kappa'):
    """kappa rule C6: reject -> *f; accept with ratio>=0.75 -> /3; accept otherwise unchanged."""
    if ok:
        S.update(th=th2, x=x2, r=r2, F=F2); S[key] = max(kap / 3, KAPPA_MIN) if ratio >= 0.75 else kap
        return True
    S['rej'] += 1
    return False


def _jac(P, th, cnt, T):
    t0 = time.perf_counter()
    x, Jimg = render_jac(th, P.N); cnt['J'] += 1; _w(cnt, FL.F_jbuild(Jimg.shape[0] * P.m))
    T['jac'] += time.perf_counter() - t0
    return x, Jimg


def _diag_log(S, cond, rank, th, N):
    w = np.abs(th[:, 0]); S['diag'].append(dict(cond=float(cond), rank=int(rank), near_zero_w=int(np.sum(w < 1e-3 * max(w.max(), 1e-300))),
                                                 outside=int(np.sum((th[:, 1] < 0) | (th[:, 1] > N) | (th[:, 2] < 0) | (th[:, 2] > N)))))


# ------------------------------------------------------------------ per-method outer iterations
def _iter_geo(P, S, cfg, cnt, T):
    th, x, r = S['th'], S['x'], S['r']; K = th.shape[0]; p = 6 * K; m = P.m; sn, a = P.sn, P.a; f = cfg['f']; rc = cfg.get('rcond', RCOND)
    _, Jimg = _jac(P, th, cnt, T)
    t0 = time.perf_counter(); AJ = P.op.apply_stack(Jimg).reshape(p, m).T; cnt['A'] += p; _w(cnt, p * FL.F_A(P.N)); T['aj'] += time.perf_counter() - t0
    t0 = time.perf_counter()
    Jm = Jimg.reshape(p, m).T
    act = bound_active(th, -(AJ.T @ r.ravel()) / sn ** 2 + a * (Jm.T @ x.ravel()), P.N); _w(cnt, 2 * FL.F_matvec(p * m)); S['act'].append(int(act.sum()))
    if act.any(): Jm = np.array(Jm); Jm[:, act] = 0.0; AJ = np.array(AJ); AJ[:, act] = 0.0
    U, s, Vt = np.linalg.svd(Jm, full_matrices=False)
    rho = int(np.sum(s > rc * s[0])); Ur = U[:, :rho]; sr = s[:rho]; Vr = Vt[:rho].T
    B = (AJ @ Vr / sr) / sn
    G = B.T @ B; lam, Q = np.linalg.eigh(G)
    rhs = B.T @ (r.ravel() / sn) - a * (Ur.T @ x.ravel()); rq = Q.T @ rhs
    _w(cnt, FL.F_svd(m, p) + FL.F_gemm(m, p, rho) + FL.F_gram(m, rho) + FL.F_eigh(rho) + 2 * FL.F_matvec(m * rho))
    T['solve'] += time.perf_counter() - t0
    _diag_log(S, s[0] / s[rho - 1], rho, th, P.N); S['rank'] = rho
    kap = S['kappa']; wmv = 2 * FL.F_matvec(p * m)
    for _ in range(BACKTRACKS):
        zq = rq / (lam + a + kap * P.LamA); z = Q @ zq; delta = Vr @ (z / sr); delta[act] = 0.0
        ok, ratio, th2, x2, r2, F2 = _accept(P, S, th + delta.reshape(th.shape), lambda d: Jm @ d, cnt, T, AJmul=lambda d: AJ @ d, wmv=wmv)
        if _finish(S, ok, ratio, th2, x2, r2, F2, kap, f): return True
        if kap >= KAPPA_MAX: break                          # the kappa limit itself has just been tried
        kap = min(kap * f, KAPPA_MAX)
    S['kappa'] = kap
    return False


def _iter_lmd(P, S, cfg, cnt, T):
    th, x, r = S['th'], S['x'], S['r']; K = th.shape[0]; p = 6 * K; m = P.m; sn, a = P.sn, P.a; f = cfg['f']
    _, Jimg = _jac(P, th, cnt, T)
    t0 = time.perf_counter(); AJ = P.op.apply_stack(Jimg).reshape(p, m).T; cnt['A'] += p; _w(cnt, p * FL.F_A(P.N)); T['aj'] += time.perf_counter() - t0
    t0 = time.perf_counter()
    Jm = Jimg.reshape(p, m).T
    act = bound_active(th, -(AJ.T @ r.ravel()) / sn ** 2 + a * (Jm.T @ x.ravel()), P.N); _w(cnt, 2 * FL.F_matvec(p * m)); S['act'].append(int(act.sum()))
    if act.any(): Jm = np.array(Jm); Jm[:, act] = 0.0; AJ = np.array(AJ); AJ[:, act] = 0.0
    H = AJ.T @ AJ / sn ** 2 + a * (Jm.T @ Jm); g = AJ.T @ (r.ravel() / sn ** 2) - a * (Jm.T @ x.ravel())
    D = np.diag(np.diag(H) + 1e-12)
    _w(cnt, 2 * FL.F_gram(m, p) + 2 * FL.F_matvec(m * p))
    T['solve'] += time.perf_counter() - t0
    if cfg.get('diag_cond'):                                    # diagnostic only: NOT counted in W or T
        sv = np.linalg.svd(Jm, compute_uv=False); rk = int(np.sum(sv > RCOND * sv[0])); _diag_log(S, sv[0] / sv[rk - 1], rk, th, P.N)
    lam = S['kappa']; S['rank'] = None; wmv = 2 * FL.F_matvec(p * m)
    for _ in range(BACKTRACKS):
        t0 = time.perf_counter()
        try:
            delta = np.linalg.solve(H + lam * D, g); delta[act] = 0.0
        except np.linalg.LinAlgError:
            lam = min(lam * f, LM_MAX); S['rej'] += 1; continue
        _w(cnt, FL.F_chol(p))
        T['solve'] += time.perf_counter() - t0
        ok, ratio, th2, x2, r2, F2 = _accept(P, S, th + delta.reshape(th.shape), lambda d: Jm @ d, cnt, T, AJmul=lambda d: AJ @ d, wmv=wmv)
        if ok:
            S.update(th=th2, x=x2, r=r2, F=F2, kappa=max(lam * 0.3, 1e-12) if ratio >= 0.75 else lam); return True
        S['rej'] += 1; lam = min(lam * f, LM_MAX)
    S['kappa'] = lam
    return False


class JOp:
    """Image Jacobian as an operator: mul(v)=J v (m,), tmul(u)=J^T u (p,), colnorm2(); nnz = stored entries (dense: p*m)."""
    def __init__(self, Jimg=None, Jcsr=None):
        self.dense = Jimg is not None
        if self.dense: self.Jf = Jimg.reshape(Jimg.shape[0], -1); self.nnz = int(self.Jf.size)           # (p,m)
        else: self.Jc = Jcsr; self.JcT = Jcsr.T.tocsr(); self.nnz = int(Jcsr.nnz)
        self.p = self.Jf.shape[0] if self.dense else Jcsr.shape[1]

    def mul(self, v):
        return self.Jf.T @ v if self.dense else self.Jc @ v

    def tmul(self, u):
        return self.Jf @ u if self.dense else self.JcT @ u

    def colnorm2(self):
        return np.einsum('ij,ij->i', self.Jf, self.Jf) if self.dense else np.asarray(self.Jc.multiply(self.Jc).sum(0)).ravel()


def _mask_J(J, act):
    if not act.any(): return J
    if J.dense: J.Jf = np.array(J.Jf); J.Jf[act, :] = 0.0
    else: dg = sp.diags((~act).astype(float)); J.Jc = (J.Jc @ dg).tocsr(); J.JcT = J.Jc.T.tocsr()
    return J


def _make_J(P, th, cnt, T, sparse=False):
    t0 = time.perf_counter()
    if sparse:
        x, Jc = render_jac_sparse(th, P.N); J = JOp(Jcsr=Jc)
    else:
        x, Jimg = render_jac(th, P.N); J = JOp(Jimg=Jimg)
    cnt['J'] += 1; _w(cnt, FL.F_jbuild(J.nnz)); T['jac'] += time.perf_counter() - t0
    return J


def _iter_lsmr(P, S, cfg, cnt, T):
    th, x, r = S['th'], S['x'], S['r']; p = th.shape[0] * 6; m = P.m; sn, a, N = P.sn, P.a, P.N; f = cfg['f']
    J = _make_J(P, th, cnt, T, cfg.get('sparse', False)); kap = S['kappa']; wJ = FL.F_matvec(J.nnz); wA = FL.F_A(N)
    t0 = time.perf_counter(); g = -J.tmul(P.op.adj(r).ravel() / sn ** 2) + a * J.tmul(x.ravel()); cnt['A'] += 1; _w(cnt, wA + 2 * wJ); T['aj'] += time.perf_counter() - t0
    act = bound_active(th, g, N); S['act'].append(int(act.sum())); J = _mask_J(J, act)
    for _ in range(BACKTRACKS):
        c = float(np.sqrt(a + kap * P.LamA))

        def mv(v):
            t0 = time.perf_counter(); jv = J.mul(v); Aj = P.op.apply(jv.reshape(N, N)); cnt['A'] += 1; cnt['mv'] += 1; _w(cnt, wJ + wA)
            out = np.concatenate([Aj.ravel() / sn, c * jv]); T['aj'] += time.perf_counter() - t0; return out

        def rmv(u):
            t0 = time.perf_counter(); w = P.op.adj(u[:m].reshape(N, N)).ravel() / sn + c * u[m:]; cnt['A'] += 1; cnt['mv'] += 1
            out = J.tmul(w); _w(cnt, wJ + wA); T['aj'] += time.perf_counter() - t0; return out
        Lop = LinearOperator((2 * m, p), matvec=mv, rmatvec=rmv, dtype=float)
        b = np.concatenate([r.ravel() / sn, -a * x.ravel() / c])
        t0 = time.perf_counter(); aj0 = T['aj']
        sol = lsmr(Lop, b, atol=cfg.get('atol', 1e-10), btol=cfg.get('btol', 1e-10), maxiter=int(cfg.get('maxiter_mult', 1) * p), conlim=1e12)
        T['solve'] += time.perf_counter() - t0 - (T['aj'] - aj0)
        delta = sol[0]; S['itn'].append(int(sol[2])); S['rank'] = None
        ok, ratio, th2, x2, r2, F2 = _accept(P, S, th + delta.reshape(th.shape), J.mul, cnt, T, wmv=wJ)
        if _finish(S, ok, ratio, th2, x2, r2, F2, kap, f): return True
        if kap >= KAPPA_MAX: break                          # the kappa limit itself has just been tried
        kap = min(kap * f, KAPPA_MAX)
    S['kappa'] = kap
    return False


def _cg(matvec, g, dinv, iters, cnt):
    d = np.zeros_like(g); res = g.copy(); z = res * dinv; pdir = z.copy(); rz = float(res @ z)
    for _ in range(iters):
        Pp = matvec(pdir); den = float(pdir @ Pp)
        if den <= 0: break
        al = rz / den; d += al * pdir; res -= al * Pp
        z = res * dinv; rz2 = float(res @ z)
        if abs(rz2) < 1e-300 or np.sqrt(abs(rz2)) < 1e-12: break
        pdir = z + (rz2 / rz) * pdir; rz = rz2
    return d


def _iter_pcg(P, S, cfg, cnt, T):
    """PCG8P: <=8 iterations Jacobi(diag J^T J)-preconditioned CG on P (truncated GEO-type step; NOT 3DGS-LM)."""
    th, x, r = S['th'], S['x'], S['r']; p = th.shape[0] * 6; m = P.m; sn, a, N = P.sn, P.a, P.N; f = cfg['f']
    J = _make_J(P, th, cnt, T, cfg.get('sparse', False)); wJ = FL.F_matvec(J.nnz); wA = FL.F_A(N)
    t0 = time.perf_counter(); g = J.tmul(P.op.adj(r).ravel() / sn ** 2) - a * J.tmul(x.ravel()); cnt['A'] += 1; _w(cnt, wA + 2 * wJ); T['aj'] += time.perf_counter() - t0
    act = bound_active(th, -g, N); S['act'].append(int(act.sum())); J = _mask_J(J, act); g[act] = 0.0
    t0 = time.perf_counter(); dinv = 1.0 / (J.colnorm2() + 1e-12); dinv[act] = 0.0; _w(cnt, wJ); T['solve'] += time.perf_counter() - t0
    kap = S['kappa']
    for _ in range(BACKTRACKS):
        cc = a + kap * P.LamA

        def matvec(v):
            t0 = time.perf_counter(); jv = J.mul(v); Aj = P.op.apply(jv.reshape(N, N)); out = J.tmul(P.op.adj(Aj).ravel() / sn ** 2 + cc * jv)
            cnt['A'] += 2; cnt['mv'] += 2; _w(cnt, 2 * wJ + 2 * wA); T['aj'] += time.perf_counter() - t0; return out
        t0 = time.perf_counter(); aj0 = T['aj']
        d = _cg(matvec, g, dinv, cfg.get('pcg_iters', 8), cnt)
        T['solve'] += time.perf_counter() - t0 - (T['aj'] - aj0); S['rank'] = None
        ok, ratio, th2, x2, r2, F2 = _accept(P, S, th + d.reshape(th.shape), J.mul, cnt, T, wmv=wJ)
        if _finish(S, ok, ratio, th2, x2, r2, F2, kap, f): return True
        if kap >= KAPPA_MAX: break                          # the kappa limit itself has just been tried
        kap = min(kap * f, KAPPA_MAX)
    S['kappa'] = kap
    return False


def _iter_pcgd(P, S, cfg, cnt, T):
    """PCG8D (3DGS-LM-like): <=8 iterations Jacobi-preconditioned CG on the LMD system (H_a + lam diag(H_a)); diag(H_a) from exact AJ column norms.
    The diagonal costs p A-applications: logged as the 'diag' part (cnt['Ad'], cnt['Wd']); strict accounting = all, cached accounting = minus the diag part (A3)."""
    th, x, r = S['th'], S['x'], S['r']; p = th.shape[0] * 6; m = P.m; sn, a, N = P.sn, P.a, P.N; f = cfg['f']
    _, Jimg = _jac(P, th, cnt, T); J = JOp(Jimg=Jimg); wJ = FL.F_matvec(J.nnz); wA = FL.F_A(N)
    t0 = time.perf_counter(); g = J.tmul(P.op.adj(r).ravel() / sn ** 2) - a * J.tmul(x.ravel()); cnt['A'] += 1; _w(cnt, wA + 2 * wJ); T['aj'] += time.perf_counter() - t0
    act = bound_active(th, -g, N); S['act'].append(int(act.sum())); J = _mask_J(J, act); g[act] = 0.0; Jimg = J.Jf.reshape(Jimg.shape)
    t0 = time.perf_counter(); AJ = P.op.apply_stack(Jimg).reshape(p, m); cnt['A'] += p; cnt['Ad'] += p; _w(cnt, p * wA + 2 * wJ, diag=True)
    dH = np.einsum('ij,ij->i', AJ, AJ) / sn ** 2 + a * J.colnorm2() + 1e-12; T['aj'] += time.perf_counter() - t0
    lam = S['kappa']
    for _ in range(BACKTRACKS):
        def matvec(v):
            t0 = time.perf_counter(); jv = J.mul(v); Aj = P.op.apply(jv.reshape(N, N)); out = J.tmul(P.op.adj(Aj).ravel() / sn ** 2 + a * jv) + lam * dH * v
            cnt['A'] += 2; cnt['mv'] += 2; _w(cnt, 2 * wJ + 2 * wA); T['aj'] += time.perf_counter() - t0; return out
        t0 = time.perf_counter(); aj0 = T['aj']
        dinv = 1.0 / (dH * (1.0 + lam)); dinv[act] = 0.0
        d = _cg(matvec, g, dinv, cfg.get('pcg_iters', 8), cnt)
        T['solve'] += time.perf_counter() - t0 - (T['aj'] - aj0); S['rank'] = None
        ok, ratio, th2, x2, r2, F2 = _accept(P, S, th + d.reshape(th.shape), J.mul, cnt, T, wmv=wJ)
        if ok:
            S.update(th=th2, x=x2, r=r2, F=F2, kappa=max(lam * 0.3, 1e-12) if ratio >= 0.75 else lam); return True
        S['rej'] += 1; lam = min(lam * f, LM_MAX)
    S['kappa'] = lam
    return False


def _iter_bj(P, S, cfg, cnt, T):
    """Block-Jacobi joint step: Gram made block-diagonal per Gaussian (K 6x6 blocks, image-metric damping, same rcond), solved in one vectorised batch.
    Relaxation (A5.1, capped at 1 = pre-D addendum item 7): step = alpha sum_k delta_k, alpha = min(1, alpha*), alpha* = argmin_{alpha>0} of the UNDAMPED quadratic model along J(sum delta_k) (closed form from AJ and r, 0 extra A-applications);
    cfg['alpha_one'] forces alpha=1 (unit test V7 only)."""
    th, x, r = S['th'], S['x'], S['r']; K = th.shape[0]; p = 6 * K; m = P.m; sn, a = P.sn, P.a; f = cfg['f']; rc = cfg.get('rcond', RCOND)
    _, Jimg = _jac(P, th, cnt, T)
    t0 = time.perf_counter(); AJ = P.op.apply_stack(Jimg); cnt['A'] += p; _w(cnt, p * FL.F_A(P.N)); T['aj'] += time.perf_counter() - t0
    t0 = time.perf_counter()
    act = bound_active(th, -(AJ.reshape(p, m) @ r.ravel()) / sn ** 2 + a * (Jimg.reshape(p, m) @ x.ravel()), P.N); _w(cnt, 2 * FL.F_matvec(p * m)); S['act'].append(int(act.sum()))
    if act.any(): Jimg = np.array(Jimg); Jimg[act] = 0.0; AJ = np.array(AJ); AJ[act] = 0.0
    Jb = Jimg.reshape(K, 6, m).transpose(0, 2, 1); AJb = AJ.reshape(K, 6, m).transpose(0, 2, 1)
    U, s, Vt = np.linalg.svd(Jb, full_matrices=False)                                   # (K,m,6),(K,6),(K,6,6)
    keep = s > rc * np.maximum(s[:, :1], 1e-300); sinv = np.where(keep, 1.0 / np.where(keep, s, 1.0), 0.0)
    V = Vt.transpose(0, 2, 1); Ur = U * keep[:, None, :]
    Bk = np.einsum('kmi,kij->kmj', AJb, V) * sinv[:, None, :] / sn
    G = np.einsum('kmi,kmj->kij', Bk, Bk); lam, Q = np.linalg.eigh(G)
    rhs = np.einsum('kmi,m->ki', Bk, r.ravel() / sn) - a * np.einsum('kmi,m->ki', Ur, x.ravel()); rq = np.einsum('kij,ki->kj', Q, rhs)
    _w(cnt, FL.F_block_solve(K, m) + 2 * K * FL.F_matvec(6 * m))
    T['solve'] += time.perf_counter() - t0
    Jm = Jimg.reshape(p, m).T; AJm = AJ.reshape(p, m).T; kap = S['kappa']; S['rank'] = int(keep.sum()); wmv = 2 * FL.F_matvec(p * m)
    for _ in range(BACKTRACKS):
        zq = rq / (lam + a + kap * P.LamA); z = np.einsum('kij,kj->ki', Q, zq); du = np.einsum('kij,kj->ki', V, z * sinv).ravel(); du[act] = 0.0
        if cfg.get('alpha_one'):
            alpha = 1.0
        else:
            jv_u = Jm @ du; Aj_u = AJm @ du; _w(cnt, wmv)
            g_d = float(Aj_u @ r.ravel()) / sn ** 2 - a * float(jv_u @ x.ravel()); q_d = float(Aj_u @ Aj_u) / sn ** 2 + a * float(jv_u @ jv_u)
            alpha = min(g_d / q_d, 1.0) if (g_d > 0 and q_d > 0 and np.isfinite(g_d / q_d)) else 0.0
        S['alpha'].append(alpha)
        if alpha <= 0:
            S['rej'] += 1
            if kap >= KAPPA_MAX: break
            kap = min(kap * f, KAPPA_MAX)
            continue
        ok, ratio, th2, x2, r2, F2 = _accept(P, S, th + alpha * du.reshape(th.shape), lambda d: Jm @ d, cnt, T, AJmul=lambda d: AJm @ d, wmv=wmv)
        if _finish(S, ok, ratio, th2, x2, r2, F2, kap, f): return True
        if kap >= KAPPA_MAX: break                          # the kappa limit itself has just been tried
        kap = min(kap * f, KAPPA_MAX)
    S['kappa'] = kap
    return False


def _iter_blk(P, S, cfg, cnt, T):
    """Gauss-Seidel sweep over the K Gaussians in fixed order; block-wise image-basis step with the CURRENT residual; block kappa_k (carried across sweeps),
    <= 10 backtracks per block (A5.2), true-F_a acceptance; a block still rejected after 10 backtracks is skipped for this sweep (S['blk_skip'])."""
    th = S['th'].copy(); K = th.shape[0]; m = P.m; sn, a, N = P.sn, P.a, P.N; f = cfg['f']; rc = cfg.get('rcond', RCOND)
    _, Jimg = _jac(P, th, cnt, T)
    x = S['x'].copy(); r = S['r'].copy(); F = S['F']; kap = S['kap_blk']; any_ok = False; wA = FL.F_A(N)
    for k in range(K):
        t0 = time.perf_counter()
        Jk = Jimg[6 * k:6 * k + 6].reshape(6, m).T; AJk = P.op.apply_stack(Jimg[6 * k:6 * k + 6]).reshape(6, m).T; cnt['A'] += 6; _w(cnt, 6 * wA); T['aj'] += time.perf_counter() - t0
        t0 = time.perf_counter()
        actk = bound_active(th[k:k + 1], -(AJk.T @ r.ravel()) / sn ** 2 + a * (Jk.T @ x.ravel()), N); _w(cnt, 2 * FL.F_matvec(6 * m)); S['act'].append(int(actk.sum()))
        if actk.any(): Jk = np.array(Jk); Jk[:, actk] = 0.0; AJk = np.array(AJk); AJk[:, actk] = 0.0
        U, s, Vt = np.linalg.svd(Jk, full_matrices=False)
        rho = int(np.sum(s > rc * max(s[0], 1e-300)))
        if rho == 0: T['solve'] += time.perf_counter() - t0; continue
        Ur = U[:, :rho]; sr = s[:rho]; Vr = Vt[:rho].T
        B = (AJk @ Vr / sr) / sn; G = B.T @ B; lam, Q = np.linalg.eigh(G)
        rhs = B.T @ (r.ravel() / sn) - a * (Ur.T @ x.ravel()); rq = Q.T @ rhs
        _w(cnt, FL.F_svd(m, 6) + FL.F_gemm(m, 6, rho) + FL.F_gram(m, rho) + FL.F_eigh(rho) + 2 * FL.F_matvec(m * rho))
        T['solve'] += time.perf_counter() - t0
        S['blk_eval'] += 1; done = False
        for _ in range(BACKTRACKS):
            zq = rq / (lam + a + kap[k] * P.LamA); z = Q @ zq; delta = Vr @ (z / sr); delta[actk] = 0.0
            t0 = time.perf_counter()
            t6raw = th[k] + delta; t6 = clamp(t6raw.reshape(1, 6), N)[0]; S['trials'] += 1; nc = int(np.sum(np.abs(t6raw - t6) > 0)); S['clamped'] += nc; S['clamp_trials'] += int(nc > 0)
            dg = P.render(t6.reshape(1, 6)) - P.render(th[k].reshape(1, 6))
            x2 = x + dg; r2 = r - P.op.apply(dg); cnt['A'] += 1; _w(cnt, wA + 2 * FL.F_render(1, N))
            dk = t6 - th[k]; jv = Jk @ dk; Aj = AJk @ dk; _w(cnt, 2 * FL.F_matvec(6 * m))
            F2 = 0.5 * float(np.sum(r2 * r2)) / sn ** 2 + 0.5 * a * float(np.sum(x2 * x2))
            pred = _gain_pred_aj(P, r, x, jv, Aj); act = F - F2
            guard = float(np.linalg.norm((x2 - x).ravel() - jv)) <= GUARD * float(np.linalg.norm(jv))
            ok = bool(pred > 0 and act > 0 and act / pred >= RHO_MIN and guard); T['back'] += time.perf_counter() - t0
            if ok:
                th[k] = t6; x = x2; r = r2; F = F2; any_ok = True; done = True
                kap[k] = max(kap[k] / 3, KAPPA_MIN) if act / pred >= 0.75 else kap[k]; break
            kap[k] = min(kap[k] * f, KAPPA_MAX); S['rej'] += 1
        if not done: S['blk_skip'] += 1
    S['rank'] = None
    if any_ok:
        F_true, x_t, r_t = P.F_of(th, cnt); _w(cnt, wA + FL.F_render(K, N)); S.update(th=th, x=x_t, r=r_t, F=F_true); return True
    return False


ITER = dict(GEO=_iter_geo, LMD=_iter_lmd, LSMR=_iter_lsmr, PCG8P=_iter_pcg, PCG8D=_iter_pcgd, BJ=_iter_bj, BLK=_iter_blk)
SAFETY_ITERS = 5000


def solve(name, P, th0, cfg, max_iter=200, A_cap=None, W_cap=None, dp_tau=None, keep_theta=False):
    """Run arm `name` on P from th0. cfg: kappa0 (lam0 for LMD/PCG8D), f (retry factor), [rcond (GEO family), sparse, atol, btol, pcg_iters, alpha_one, diag_cond].
    CALIBRATION mode (A_cap or W_cap None): at most max_iter outer iterations (the 200-iteration rule used only to calibrate A_cap, W_cap from GEO).
    BUDGETED mode (both caps given, A1.2): stops only when A_eff >= A_cap AND W >= W_cap (A_eff = A - cnt['Ad'] = cached accounting for PCG8D), on convergence
    (3 consecutive accepted steps with relative decrease <= 1e-9), when no acceptable step exists (kappa/lambda_LM limit), or at SAFETY_ITERS outer iterations (stop='safety').
    dp_tau given: stop at the first accepted iterate with ||y-Ax||^2 <= dp_tau N^2 sn^2 (stop='discrepancy').
    Returns dict(theta, F, traj=[(it, F, t_solver, A, J, mv, W, rss, Ad, Wd)], stop, rej, clamp_rate (fraction of trial steps with >=1 clamped parameter), clamp_entries_per_trial,
    trials, diag, itn, alpha (BJ), blk_skip / blk_eval (BLK), cnt, T, kappa, [th_hist])."""
    cnt = dict(A=0, J=0, mv=0, W=0.0, Ad=0, Wd=0.0); T = dict(jac=0.0, aj=0.0, solve=0.0, back=0.0)
    th = clamp(th0, P.N); F, x, r = P.F_of(th)
    S = dict(th=th, x=x, r=r, F=F, kappa=cfg['kappa0'], rej=0, rank=None, trials=0, clamped=0, clamp_trials=0, diag=[], itn=[], alpha=[], act=[], blk_skip=0, blk_eval=0)
    if name == 'BLK': S['kap_blk'] = np.full(th.shape[0], cfg['kappa0'])
    traj = [(0, F, 0.0, 0, 0, 0, 0.0, float(np.sum(r * r)), 0, 0.0)]; th_hist = [th.copy()] if keep_theta else None
    small = 0; fails = 0; stop = 'max_iter'; clock0 = time.perf_counter(); budgeted = A_cap is not None and W_cap is not None
    limit = SAFETY_ITERS if budgeted else max_iter
    for it in range(1, limit + 1):
        Fold = S['F']; ok = ITER[name](P, S, cfg, cnt, T)
        t_now = time.perf_counter() - clock0
        rss = float(np.sum(S['r'] ** 2))
        traj.append((it, S['F'], t_now, cnt['A'], cnt['J'], cnt['mv'], cnt['W'], rss, cnt['Ad'], cnt['Wd']))
        if keep_theta: th_hist.append(S['th'].copy())
        if not ok:
            fails += 1                                  # an iteration whose backtracks were all rejected: damping was raised and is carried, retry from the same theta
            if name == 'BLK': dead = fails >= 3         # every evaluated block has then reached the kappa limit (3^10 > 1e4 / kappa0 within two sweeps)
            else: dead = S['kappa'] >= (LM_MAX if name in ('LMD', 'PCG8D') else KAPPA_MAX) and fails >= 2
            if dead: stop = 'no_step'; break
            continue
        fails = 0
        if dp_tau is not None and rss <= dp_tau * P.N ** 2 * P.sn ** 2: stop = 'discrepancy'; break
        small = small + 1 if (Fold - S['F']) <= 1e-9 * abs(Fold) else 0
        if small >= 3: stop = 'converged'; break
        if budgeted and (cnt['A'] - cnt['Ad']) >= A_cap and (cnt['W'] - cnt['Wd']) >= W_cap: stop = 'cap'; break
    else:
        stop = 'safety' if budgeted else 'max_iter'
    out = dict(theta=S['th'], F=S['F'], traj=traj, stop=stop, rej=S['rej'], clamp_rate=S['clamp_trials'] / max(S['trials'], 1), clamp_entries_per_trial=S['clamped'] / max(S['trials'], 1),
               trials=S['trials'], diag=S['diag'], itn=S['itn'], alpha=S['alpha'], act=S['act'], blk_skip=S['blk_skip'], blk_eval=S['blk_eval'], cnt=cnt, T=T, kappa=S['kappa'])
    if keep_theta: out['th_hist'] = th_hist
    return out
