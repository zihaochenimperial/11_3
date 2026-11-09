"""TRN same-state study library (contract TRN v1 sections 3-5). EVALUATION-side oracle code (uses the dense spectrum, never reads a clean image). Methods inside (D0..D5) are method-side except where marked ORACLE.
Frozen files geo_core/geo_flops are only imported."""
import numpy as np
import geo_core as GC
import geo_flops as FL
import trn_flops as TF
import trn_core as TC

RHO_MAIN = 0.1
RHOS = (0.1, 0.03, 0.01)


def _mk_track(I, D, dstar_full_idx, ds2, floor, rho_list, wbox):
    idx = D['idx']; Hf = D['H']; dst = dstar_full_idx
    def track(xk):
        e = xk[idx] - dst; err = float(e @ Hf @ e)
        return dict(err=err, W=wbox[0], rel=err / ds2)
    return track


def _first_hits(hist, ds2, floor, rhos):
    hits = {}
    for rho in rhos:
        tgt = max(rho * ds2, floor); hit = next((i for i, h in enumerate(hist) if h['err'] <= tgt), None)
        hits[rho] = None if hit is None else (hit, hist[hit]['W'])
    return hits


def run_cg(I, D, g, prec, W=None, setup_work=0.0, x0=None, x0_cost=0.0, safety=400, floor=0.0, rhos=RHOS, keep_lanczos=False, rho_stop=None):
    """One (deflated) PCG solve with oracle error tracking in the H norm w.r.t. the tau-truncated generalized solution. setup_work: flops of set-up that belong to the arm. Returns dict(hits, iters, res)."""
    wbox = [setup_work + x0_cost]; ds2 = D['dH2']; track = _mk_track(I, D, D['dstar'][D['idx']], ds2, floor, rhos, wbox)
    HW = None
    if W is not None and W.shape[1] > 0:
        HW = np.stack([I.Hmv(W[:, j]) for j in range(W.shape[1])], 1)          # the k matvecs: their W is charged in setup_work by the caller (formula), the numbers are shared with the oracle
    def tr2(xk):
        h = track(xk)
        if rho_stop is not None and h['err'] <= max(rho_stop * ds2, floor): h['stop'] = True
        return h
    res = dpcg(I, g, prec, W=W, HW=HW, x0=x0, maxit=min(I.p, safety), track=tr2, work=wbox, keep_lanczos=keep_lanczos)
    hits = _first_hits(res['hist'], ds2, floor, rhos)
    return dict(hits=hits, iters=res['iters'], res=res, Wtot=wbox[0])


dpcg = TC.dpcg


def spectral_subspace(D, k, which='smallest'):
    """ORACLE spectral basis (generalized eigenvectors over lam>tau): k smallest-lam (D1) or k largest-energy (D1e); columns in the embedded full-p coordinates (dense idx)."""
    keep = np.flatnonzero(D['keep'])
    if which == 'smallest': sel = keep[:k]
    else: sel = keep[np.argsort(-D['energy'][keep])[:k]]
    return D['V'][:, sel], sel


def transport_rhs(I_t, I_prev, U_prev_full):
    """Y = M_{t-1} U ; rhs = M_t^T Y = J_t^T (A^T A/sn^2 + sqrt(c_t c_{t-1}) I) J_{t-1} U  (full-p vectors masked by the respective free sets). U_prev_full: (p,k). Also returns ||Y||_F^2."""
    k = U_prev_full.shape[1]; out = np.zeros((I_t.p, k)); cc = np.sqrt(I_t.c * I_prev.c); Ynorm2 = 0.0
    for j in range(k):
        jv = I_prev.Jc @ (I_prev.mask * U_prev_full[:, j]); Aj = I_t.P.op.apply(jv.reshape(I_t.N, I_t.N)).ravel()
        out[:, j] = I_t.mask * (I_t.JcT @ (I_t.P.op.adj(Aj.reshape(I_t.N, I_t.N)).ravel() / I_t.sn ** 2 + cc * jv))
        Ynorm2 += float(Aj @ Aj) / I_prev.sn ** 2 + I_prev.c * float(jv @ jv)           # ||M_{t-1} u||^2 at the state t-1 damping (A is state independent)
    return out, Ynorm2


def transport_wcost_rhs(I_t, I_prev, k):
    """Per column: J_{t-1} u (F_matvec(nnz_{t-1}) = 2 nnz), A and A^T (2 F_A), J_t^T w (F_matvec(nnz_t)); the ||Y||^2 term reuses the same products (Opus S4: no double count)."""
    return k * (FL.F_matvec(I_prev.nnz) + 2.0 * FL.F_A(I_t.N) + FL.F_matvec(I_t.nnz))


def transport_cg(I_t, U0, rhs, n_tr, Ynorm2, work, dinv):
    """Column-wise PCG on  H_t z = rhs_j  (normal equations of min_Z ||M_t Z - Y||_F), warm start Z0 = U0 (contract M3), n_tr iterations. Returns Z and the LS residual ratio ||M_t Z - Y||_F / ||Y||_F."""
    k = U0.shape[1]; Z = np.zeros_like(U0)
    for j in range(k):
        z = I_t.mask * U0[:, j]; res = rhs[:, j] - I_t.Hmv(z); work[0] += I_t.wH; zz = dinv * res; rz = float(res @ zz); pd = zz.copy()
        for it in range(n_tr):
            if rz <= 1e-300: break
            Hp = I_t.Hmv(pd); work[0] += I_t.wH + 8.0 * I_t.p; den = float(pd @ Hp)
            if not den > 0: break
            al = rz / den; z = z + al * pd; res = res - al * Hp; zz = dinv * res; rz2 = float(res @ zz); pd = zz + (rz2 / rz) * pd; rz = rz2
        Z[:, j] = z
    # LS residual: ||M_t Z - Y||^2 = tr(Z^T H_t Z) - 2 tr(Z^T rhs) + ||Y||^2
    HZ = np.stack([I_t.Hmv(Z[:, j]) for j in range(k)], 1)
    ls2 = float(np.sum(Z * HZ)) - 2.0 * float(np.sum(Z * rhs)) + Ynorm2
    return Z, float(np.sqrt(max(ls2, 0.0) / max(Ynorm2, 1e-300)))


def rr_basis(I, Z, work):
    """Rayleigh-Ritz / H-orthonormalisation of span(Z) at the current H: QR, then H-eigen-decomposition of Q^T H Q (k matvecs charged); returns W (p,k') with W^T H W diagonal, k'<=k (E-eigenvalues < 1e-12 max dropped)."""
    Q, _ = np.linalg.qr(Z * I.mask[:, None]); HQ = np.stack([I.Hmv(Q[:, j]) for j in range(Q.shape[1])], 1)
    E = Q.T @ HQ; E = 0.5 * (E + E.T); lam, Y = np.linalg.eigh(E); keep = lam > 1e-12 * max(lam[-1], 1e-300)
    work[0] += TF.F_defl_setup(I.p, Q.shape[1], I.N, I.nnz) + TF.F_qr(I.p, Q.shape[1])
    return Q @ Y[:, keep], int(keep.sum()), float(lam[-1] / max(lam[keep][0], 1e-300)) if keep.any() else float('nan')


def study_state(I_t, D_t, I_prev, D_prev, F_t, k=8, rs=(2, 4), n_trs=(0, 3, 8), safety=400, rho_prev=RHO_MAIN, rng=None, rhos=RHOS):
    """State (theta_t, kappa_t) is supplied by the caller from the B* closed-loop log (contract v1.2 section 3, Opus C1). 'Previous solve' = D0 (PCG-J) cold at (theta_{t-1}, kappa_{t-1}), oracle-stopped at the main rho (same-state convention); D0w x0 = its solution, shared by all arms."""
    rng = rng or np.random.default_rng(0); out = {}; p = I_t.p; floor = 2e-6 * F_t; g = I_t.g
    # ---- skip late states with negligible predicted gain
    if D_t['dq_star'] < 1e-6 * F_t: return dict(skipped=True, dq_star=D_t['dq_star'], F=F_t)
    dJ = I_t.dinvJ
    # ---- baselines (no subspace): D0, D0w, D0b, D0s
    out['D0'] = run_cg(I_t, D_t, g, dJ, floor=floor, safety=safety, rhos=rhos)
    # previous solve (method-side, belongs to state t-1): plain PCG-J to rho_prev with Lanczos kept; also gives its solution for the warm start
    prev = run_cg(I_prev, D_prev, I_prev.g, I_prev.dinvJ, floor=2e-6 * F_t, safety=safety, rhos=rhos, keep_lanczos=True, rho_stop=rho_prev)
    xprev = prev['res']['x']
    out['D0w'] = run_cg(I_t, D_t, g, dJ, x0=I_t.mask * xprev, floor=floor, safety=safety, rhos=rhos)      # H x0 charged once, inside dpcg (Opus C8)
    wb = [0.0]; Mb = TC.block_jacobi(I_t, wb)
    out['D0b'] = run_cg(I_t, D_t, g, Mb, setup_work=wb[0] + 0.0, floor=floor, safety=safety, rhos=rhos)
    out['D0b']['setup_strict'] = wb[0]; out['D0b']['setup_cached'] = wb[0] - I_t.p * FL.F_A(I_t.N)
    cs = np.zeros((p, I_t.K)); cs[0::6][np.arange(I_t.K), np.arange(I_t.K)] = 0.0
    for kk in range(I_t.K): cs[6 * kk, kk] = 1.0                           # D0s: per-Gaussian amplitude coordinate columns (fixed coarse space)
    Wc, kc, _ = rr_basis(I_t, cs, [0.0]); ws = [0.0]; _w, _k, _ = rr_basis(I_t, cs, ws)
    out['D0s'] = run_cg(I_t, D_t, g, dJ, W=Wc, setup_work=ws[0], floor=floor, safety=safety, rhos=rhos); out['D0s']['k'] = kc
    # ---- recycling / transport
    wh = [0.0]; U, ritz = TC.ritz_harvest(prev['res'], k, work=wh, which='smallest')                    # D2 extraction (charged)
    U = U * I_t.mask[:, None]
    for n_tr in n_trs:
        wt = [wh[0]]; Z = U
        rhs = None
        if n_tr > 0:
            rhs, Y2 = transport_rhs(I_t, I_prev, U); wt[0] += transport_wcost_rhs(I_t, I_prev, U.shape[1])
            Z, lsr = transport_cg(I_t, U, rhs, n_tr, Y2, wt, dJ)
        Wb, kq, cnd = rr_basis(I_t, Z, wt)
        name = 'D2' if n_tr == 0 else f'D3p_n{n_tr}'
        out[name] = run_cg(I_t, D_t, g, dJ, W=Wb, setup_work=wt[0], floor=floor, safety=safety, rhos=rhos); out[name].update(k=kq, cond_E=cnd, ls_ratio=None if n_tr == 0 else lsr)
        if n_tr == max(n_trs):                                                                           # keep the deepest-transport basis for D5/D6
            W3p = Wb; setup3p = wt[0]
    # ---- ORACLE isolation chain: D1, D1e at t; D4lambda, D4e (exact LS transport of the t-1 spectral subspaces); D3x (exact LS transport of the harvested U)
    for nm, which in (('D1', 'smallest'), ('D1e', 'energy')):
        V, sel = spectral_subspace(D_t, k, which); Wf = I_t._embed(D_t['idx'], V); out[nm] = run_cg(I_t, D_t, g, dJ, W=Wf, setup_work=0.0, floor=floor, safety=safety, rhos=rhos)   # cost not charged (oracle)
    def exact_transport(Uprev_full):
        rhs_, Y2 = transport_rhs(I_t, I_prev, Uprev_full); idx = D_t['idx']; Hf = D_t['H']
        Zf = np.linalg.lstsq(Hf + 1e-12 * np.trace(Hf) / len(idx) * np.eye(len(idx)), rhs_[idx], rcond=None)[0]; return I_t._embed(idx, Zf)
    for nm, which in (('D4lam', 'smallest'), ('D4e', 'energy')):
        Vp, _ = spectral_subspace(D_prev, k, which); Z = exact_transport(I_prev._embed(D_prev['idx'], Vp)); ws = [0.0]; Wb, kq, cnd = rr_basis(I_t, Z, ws)
        out[nm] = run_cg(I_t, D_t, g, dJ, W=Wb, setup_work=0.0, floor=floor, safety=safety, rhos=rhos); out[nm]['k'] = kq
    Vp4, _ = spectral_subspace(D_prev, k, 'smallest'); Z4 = exact_transport(I_prev._embed(D_prev['idx'], Vp4)); W4, k4, _c4 = rr_basis(I_t, Z4, [0.0]); HW4 = np.stack([I_t.Hmv(W4[:, j]) for j in range(W4.shape[1])], 1)
    E4 = W4.T @ HW4; E4inv = np.linalg.pinv(0.5 * (E4 + E4.T), rcond=1e-12, hermitian=True); x04 = W4 @ (E4inv @ (W4.T @ g)); idx_ = D_t['idx']
    c4 = D_t['V'].T @ (D_t['D'] * (D_t['dstar'][idx_] - x04[idx_])); en4 = D_t['lam'] * c4 ** 2; en4[~D_t['keep']] = 0.0
    for r in rs:
        pick = np.argsort(-en4)[:r]; Wb46, kq46, _ = rr_basis(I_t, np.concatenate([W4, I_t._embed(idx_, D_t['V'][:, pick])], 1), [0.0])
        out[f'D46_r{r}'] = run_cg(I_t, D_t, g, dJ, W=Wb46, setup_work=0.0, floor=floor, safety=safety, rhos=rhos); out[f'D46_r{r}']['k'] = kq46       # G-B main reading: ideal transport + ideal patch, set-up cost 0
    Z = exact_transport(U); ws = [0.0]; Wb, kq, _c = rr_basis(I_t, Z, ws); out['D3x'] = run_cg(I_t, D_t, g, dJ, W=Wb, setup_work=0.0, floor=floor, safety=safety, rhos=rhos); out['D3x']['k'] = kq
    # ---- patches on top of the deepest-transport basis: D5 (method-side Krylov extension, charged), D6 / D6n (ORACLE directions, cost 0)
    idx = D_t['idx']; V = D_t['V']; Dd = D_t['D']; keep = np.flatnonzero(D_t['keep']); lam = D_t['lam']
    Wsub = W3p[idx]; HW = np.stack([I_t.Hmv(W3p[:, j]) for j in range(W3p.shape[1])], 1); E = W3p.T @ HW; Einv = np.linalg.pinv(0.5 * (E + E.T), rcond=1e-12, hermitian=True)
    x0 = W3p @ (Einv @ (W3p.T @ g)); res0 = g - I_t.Hmv(x0)
    for r in rs:
        # D5: r extra directions = short Krylov expansion of the deflated residual (P_J-preconditioned), orthogonalised against W3p; r H-matvecs charged
        vecs = []; v = dJ * res0
        for j in range(r):
            v = v - W3p @ (Einv @ (HW.T @ v)); nv = float(np.linalg.norm(v))
            if nv < 1e-14: break
            vecs.append(v / nv); v = dJ * I_t.Hmv(vecs[-1])
        wk = [setup3p + r * I_t.wH + TF.F_krylov_extend(p, r, I_t.N, I_t.nnz) - r * I_t.wH]
        Z5 = np.concatenate([W3p, np.stack(vecs, 1)], 1) if vecs else W3p; Wb5, kq5, _ = rr_basis(I_t, Z5, wk)
        out[f'D5_r{r}'] = run_cg(I_t, D_t, g, dJ, W=Wb5, setup_work=wk[0], floor=floor, safety=safety, rhos=rhos); out[f'D5_r{r}']['k'] = kq5
        # D6 oracle: remaining error after the initial projection; pick the r generalized-eigen directions with the largest remaining H-energy lam_i c_i^2, c = V^T D err
        err = np.zeros(D_t['idx'].size); err = D_t['dstar'][idx] - x0[idx]; c = V.T @ (Dd * err); en = lam * c ** 2; en[~D_t['keep']] = 0.0
        pick = np.argsort(-en)[:r]; Vd = I_t._embed(idx, V[:, pick])
        Z6 = np.concatenate([W3p, Vd], 1); Wb6, kq6, _ = rr_basis(I_t, Z6, [0.0])
        out[f'D6_r{r}'] = run_cg(I_t, D_t, g, dJ, W=Wb6, setup_work=setup3p, floor=floor, safety=safety, rhos=rhos); out[f'D6_r{r}']['k'] = kq6      # D6 shares the D3p set-up cost, the patch is free (upper bound)
        noisy = []
        for j in pick:
            nvec = rng.standard_normal(idx.size); nvec -= (V[:, j] @ (Dd * nvec)) * V[:, j]; nvec /= np.sqrt(nvec @ (Dd * nvec))        # unit in the D-norm, D-orthogonal to v_j
            noisy.append(0.7 * V[:, j] + np.sqrt(1 - 0.49) * nvec)
        Z6n = np.concatenate([W3p, I_t._embed(idx, np.stack(noisy, 1))], 1); Wb6n, kq6n, _ = rr_basis(I_t, Z6n, [0.0])
        out[f'D6n_r{r}'] = run_cg(I_t, D_t, g, dJ, W=Wb6n, setup_work=setup3p, floor=floor, safety=safety, rhos=rhos); out[f'D6n_r{r}']['k'] = kq6n
    return dict(skipped=False, arms=out, prev_iters=prev['iters'], F=F_t, dq_star=D_t['dq_star'], p=p, rank_eff95=int(np.searchsorted(np.cumsum(np.sort(D_t['energy'])[::-1]) / max(D_t['energy'].sum(), 1e-300), 0.95)) + 1,
                n_free=int(I_t.free.sum()), n_degenerate=getattr(I_t, 'degenerate', 0), cond_gen=D_t['cond_gen'], act_frac=float(I_t.act.mean()))
