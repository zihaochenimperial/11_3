"""TRN same-state inner-problem tools (contract TRN_CONTRACT_CANDIDATE_v0, sections 1,4,5). numpy/scipy only; imports frozen geo_core/geo_flops read-only.
METHOD-SIDE code: never reads a clean image.
Inner problem at state th with damping kappa:  H = J^T (A^T A / sn^2 + c I) J,  c = a + eta, eta = kappa * LamA;  g = J^T (A^T r / sn^2 - a x);  dq(d) = g.d - 1/2 d.H d.
J = truncated (Mahalanobis radius 4) sparse image Jacobian (geo_core.render_jac_sparse) so every arm sees the SAME operator. Coordinates frozen by the eps-active set (geo_core.bound_active)
carry zero vectors (full-p vectors with a mask; H is PSD on the free block)."""
import numpy as np
import scipy.sparse as sp
import geo_core as GC
import geo_flops as FL


class Inner:
    def __init__(self, P, th, kappa):
        self.P = P; self.th = np.array(th, float); self.kappa = float(kappa); N = P.N; self.N = N; self.m = N * N; self.K = th.shape[0]; self.p = 6 * self.K
        x, Jc = GC.render_jac_sparse(self.th, N); self.x = x; self.r = P.y - P.op.apply(x)
        self.sn, self.a = P.sn, P.a; self.c = self.a + self.kappa * P.LamA
        g0 = Jc.T @ (P.op.adj(self.r).ravel() / self.sn ** 2 - self.a * x.ravel())
        self.act = GC.bound_active(self.th, -g0, N)                         # same rule as the frozen step: descent direction -g
        self.free = ~self.act; self.mask = self.free.astype(float)
        self.Jc = (Jc @ sp.diags(self.mask)).tocsr(); self.JcT = self.Jc.T.tocsr(); self.nnz = int(self.Jc.nnz)
        self.g = self.mask * (self.JcT @ (P.op.adj(self.r).ravel() / self.sn ** 2 - self.a * x.ravel()))
        self.wH = 2 * FL.F_matvec(self.nnz) + 2 * FL.F_A(N)                    # flops of one H-matvec (J, A, A^T, J^T)
        self.diagJ = np.asarray(self.Jc.multiply(self.Jc).sum(0)).ravel()
        self.dinvJ = self.mask / (self.diagJ + 1e-12)                             # Jacobi preconditioner P_J (no A-applications)
        self._dense = None

    # -- matrix-free operator (counted by the caller via self.wH per call)
    def Hmv(self, v):
        jv = self.Jc @ (self.mask * v); aj = self.P.op.apply(jv.reshape(self.N, self.N)).ravel()
        w = self.P.op.adj(aj.reshape(self.N, self.N)).ravel() / self.sn ** 2 + self.c * jv
        return self.mask * (self.JcT @ w)

    def AJ_cols(self, idx=None):
        """A applied to the Jacobian columns idx (all free by default): (m, len(idx)); costs len(idx) A-applications."""
        idx = np.flatnonzero(self.free) if idx is None else np.asarray(idx)
        Jd = self.Jc[:, idx].toarray().T.reshape(len(idx), self.N, self.N)
        return self.P.op.apply_stack(Jd).reshape(len(idx), self.m).T, Jd.reshape(len(idx), self.m).T

    # -- dense oracle (diagnostics only; cost NOT charged to any method). v1/M2: everything in the Jacobi-generalized spectrum  H v = lam D v,  D = diag(J^T J) on the free,
    #    non-degenerate coordinates,  V^T D V = I,  tau = TAU_REL * lam_max;  delta*_tau = sum_{lam>tau} v (v^T g)/lam;  e_i = (v_i^T g)^2/lam_i;  sum e = ||delta*_tau||_H^2.
    TAU_REL = 1e-8
    def dense(self):
        if self._dense is None:
            fr = np.flatnonzero(self.free); dg = self.diagJ[fr]; live = dg > 1e-12 * max(float(dg.max()), 1e-300)
            idx = fr[live]; self.degenerate = int((~live).sum())                 # free coordinates with (numerically) zero Jacobian column: frozen, disclosed
            AJ, Jd = self.AJ_cols(idx)
            Hf = AJ.T @ AJ / self.sn ** 2 + self.c * (Jd.T @ Jd); Hf = 0.5 * (Hf + Hf.T)
            dd = self.diagJ[idx]; s = 1.0 / np.sqrt(dd)
            lam, Y = np.linalg.eigh(s[:, None] * Hf * s[None, :]); V = s[:, None] * Y           # D-orthonormal generalized eigenvectors, ascending lam
            tau = self.TAU_REL * max(lam[-1], 1e-300); keep = lam > tau
            gf = self.g[idx]; coef = V.T @ gf
            e = np.where(keep, coef ** 2 / np.where(keep, lam, 1.0), 0.0)
            dstar_f = V[:, keep] @ (coef[keep] / lam[keep])
            full = lambda vf: self._embed(idx, vf)
            self._dense = dict(idx=idx, H=Hf, D=dd, lam=lam, V=V, coef=coef, keep=keep, tau=tau, energy=e, dstar=full(dstar_f), dq_star=0.5 * float(gf @ dstar_f),
                               dH2=float(dstar_f @ Hf @ dstar_f), AJ=AJ, full=full, cond_gen=float(lam[-1] / max(lam[keep][0], 1e-300)) if keep.any() else float('nan'))
        return self._dense

    def _embed(self, idx, vf):
        v = np.zeros((self.p,) + vf.shape[1:]); v[idx] = vf; return v


def dpcg(inner, g, dinv, W=None, HW=None, x0=None, maxit=None, track=None, work=None, keep_lanczos=False):
    """Deflated preconditioned CG (Saad-Yeung-Erhel-Guyomarc'h / Erhel-Guyomarc'h form) for H x = g on the free block.
    W: deflation basis (p,k) with HW = H W (the k matvecs are charged by the caller). track(x) -> dict recorded each iteration (oracle error etc.); work[0] accumulates flops.
    keep_lanczos: store the preconditioned Lanczos vectors q_j = (-1)^j z_j / sqrt(r_j.z_j) and the tridiagonal T (for Ritz harvesting; valid for the (deflated) operator the CG saw)."""
    p = inner.p; maxit = maxit or p
    wk = work if work is not None else [0.0]
    prec = dinv if callable(dinv) else (lambda rr: dinv * rr)
    have_w = W is not None and W.shape[1] > 0
    if have_w:
        E = W.T @ HW; E = 0.5 * (E + E.T); Einv = np.linalg.pinv(E, rcond=1e-12, hermitian=True); k = W.shape[1]
    x = np.zeros(p) if x0 is None else inner.mask * x0
    r = g.copy()
    if x0 is not None and np.any(x): r = g - inner.Hmv(x); wk[0] += inner.wH
    if have_w:
        x = x + W @ (Einv @ (W.T @ r)); r = g - inner.Hmv(x); wk[0] += inner.wH + 4.0 * p * k
    z = prec(r); rz = float(r @ z); pdir = z.copy()
    if have_w: pdir = pdir - W @ (Einv @ (HW.T @ z)); wk[0] += 4.0 * p * k
    hist = []; al_l = []; be_l = []; Q = []; it = 0
    if track is not None: hist.append(track(x))
    while it < maxit and rz > 1e-300:
        if keep_lanczos: Q.append(((-1) ** it) * z / np.sqrt(rz))
        Hp = inner.Hmv(pdir); wk[0] += inner.wH; den = float(pdir @ Hp)
        if not den > 0: break
        al = rz / den; x = x + al * pdir; r = r - al * Hp; z = prec(r); rz2 = float(r @ z); it += 1; wk[0] += 8.0 * p
        al_l.append(al); be_l.append(rz2 / rz)
        if track is not None:
            h = track(x); hist.append(h)
            if h.get('stop'): break
        pdir = z + (rz2 / rz) * pdir
        if have_w: pdir = pdir - W @ (Einv @ (HW.T @ z)); wk[0] += 4.0 * p * k
        rz = rz2
    return dict(x=x, iters=it, hist=hist, alphas=al_l, betas=be_l, Q=Q)


def lanczos_T(alphas, betas):
    """Tridiagonal of the preconditioned Lanczos process from CG coefficients (alpha_j, beta_j = r_{j+1}.z_{j+1}/r_j.z_j)."""
    n = len(alphas); T = np.zeros((n, n))
    for j in range(n):
        T[j, j] = 1.0 / alphas[j] + (betas[j - 1] / alphas[j - 1] if j > 0 else 0.0)
        if j + 1 < n: T[j, j + 1] = T[j + 1, j] = np.sqrt(betas[j]) / alphas[j]
    return T


def ritz_harvest(res, k, work=None, which='smallest'):
    """k extreme Ritz vectors (original coordinates; generalized pencil H u = theta M u, M = diag(1/dinv)) from a stored CG run. Cost O(p n k) + O(n^3) small eig, charged to work."""
    n = len(res['alphas']); Q = np.array(res['Q'][:n]).T          # (p, n)
    T = lanczos_T(res['alphas'], res['betas']); th, Y = np.linalg.eigh(T); sel = np.arange(min(k, n)) if which == 'smallest' else np.arange(n - min(k, n), n)
    U = Q @ Y[:, sel]
    if work is not None: work[0] += 2.0 * Q.shape[0] * n * len(sel) + 9.0 * n ** 3
    return U, th[sel]


def hbasis(inner, Z, work=None):
    """Orthonormalise Z (QR) and compute H Z with len(cols) matvecs (charged)."""
    Zq, _ = np.linalg.qr(Z * inner.mask[:, None]); HZ = np.stack([inner.Hmv(Zq[:, j]) for j in range(Zq.shape[1])], 1)
    if work is not None: work[0] += Zq.shape[1] * inner.wH + 4.0 * inner.p * Zq.shape[1] ** 2
    return Zq, HZ


def block_jacobi(inner, work=None):
    """6x6 per-Gaussian block Jacobi (D0b): blocks of H from AJ column groups. Build cost (charged): p A-applications + Gram work. Returns a callable M^{-1}."""
    K = inner.K; idx = np.arange(inner.p); AJ, Jd = inner.AJ_cols(np.flatnonzero(inner.free))
    fr = np.flatnonzero(inner.free); pos = -np.ones(inner.p, int); pos[fr] = np.arange(len(fr))
    Binv = np.zeros((K, 6, 6))
    for k in range(K):
        cols = pos[6 * k:6 * k + 6]; ok = cols >= 0
        if not ok.any(): Binv[k] = np.eye(6); continue
        c = cols[ok]; B = AJ[:, c].T @ AJ[:, c] / inner.sn ** 2 + inner.c * (Jd[:, c].T @ Jd[:, c])
        Bi = np.eye(6); Bi_sub = np.linalg.pinv(B + 1e-12 * np.trace(B) * np.eye(len(c)), hermitian=True); sub = np.zeros((6, 6)); sub[np.ix_(ok, ok)] = Bi_sub; Binv[k] = sub
    if work is not None: work[0] += inner.p * FL.F_A(inner.N) + K * (2.0 * inner.m * 36 * 2 + 9.0 * 216)
    return lambda r: (Binv @ r.reshape(K, 6, 1)).reshape(-1)
