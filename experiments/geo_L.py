"""GEO phase L (cost-structure ladder; contract v2 §5 + addendum A2). Exclusive single-thread job; writes outputs/GEO-L/L_<N>_<K>.json per size.
Ordinary implementation = LSMR on the sparse 4-sigma-truncated Jacobian (self-consistent truncated forward model).
Measured per size and per state (grid init / after 5 LSMR outer iterations with kappa0=1e-3, f=10):
 (i) per-stage seconds of ONE LSMR outer iteration (jac / aj / solve / back), median of 3 repeats; (ii) inner LSMR iterations until
 ||At(b-A d_k)|| <= 1e-6 ||At b|| (explicit check, atol=btol=0, maxiter=20p; censored if hit) for eta=0 (primary) and kappa=1e-3 (secondary);
 (iii) dense GEO / LMD one-outer-iteration time up to (96,324); (iv) Gram coupling sparsity (block-level, descriptive)."""
import os, sys, json, time
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_v] = '1'
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'src'))
import numpy as np
import scipy.sparse as sp
import geo_core as GC
import geo_gen as GG

LADDER = ((32, 36), (64, 144), (80, 225), (96, 324), (128, 576))
SB, SN, LAM = 1.5, 0.01, 1e-3
OUT = os.path.join(ROOT, 'outputs', 'GEO-L')


TOLS = (1e-2, 1e-3, 1e-4, 1e-6)           # relative normal-equation tolerances; primary = 1e-3 (pre-D addendum K1 item 11), others reported as sensitivity


def lsmr_first_converged(mv, rmv, b, n, tols=TOLS, maxiter=None):
    """Golub-Kahan LSMR (Fong & Saunders; damp=0, operator already augmented). Returns (dict tol -> iteration count or None if censored at maxiter, x_last, normar0, dict(n_tests, t_tests)).
    For each tol the count is the first k with the EXPLICIT test ||A^T(b-A x_k)|| <= tol ||A^T b||; the exact-arithmetic estimate |zetabar| only triggers when
    the explicit test is evaluated (it is then evaluated every iteration until it holds)."""
    maxiter = maxiter or 20 * n
    pend = sorted(tols, reverse=True); found = {t: None for t in tols}
    u = b.copy(); beta = np.linalg.norm(u)
    if beta == 0: return {t: 0 for t in tols}, np.zeros(n), 0.0, dict(n_tests=0, t_tests=0.0)
    u /= beta; v = rmv(u); alpha = np.linalg.norm(v); v /= alpha
    normar0 = alpha * beta
    alphabar, zetabar, rho, rhobar, cbar, sbar = alpha, alpha * beta, 1.0, 1.0, 1.0, 0.0
    h = v.copy(); hbar = np.zeros(n); x = np.zeros(n); trig = False; n_tests = 0; t_tests = 0.0; maxrbar = 0.0; minrbar = 1e100
    for itn in range(1, maxiter + 1):
        u = mv(v) - alpha * u; beta = np.linalg.norm(u)
        if beta > 0:
            u /= beta; v = rmv(u) - beta * v; alpha = np.linalg.norm(v)
            if alpha > 0: v /= alpha
        rhoold = rho; rho = np.hypot(alphabar, beta); c = alphabar / rho; s = beta / rho
        thetanew = s * alpha; alphabar = c * alpha
        rhobarold = rhobar; thetabar = sbar * rho
        rhobar = np.hypot(cbar * rho, thetanew); cbar_new = cbar * rho / rhobar; sbar = thetanew / rhobar; cbar = cbar_new
        maxrbar = max(maxrbar, rhobarold); minrbar = min(minrbar, rhobarold) if itn > 1 else minrbar          # cond(A~) bookkeeping (Fong-Saunders estimate; scalars only)
        zeta = cbar * zetabar; zetabar = -sbar * zetabar
        hbar = h - (thetabar * rho / (rhoold * rhobarold)) * hbar
        x = x + (zeta / (rho * rhobar)) * hbar
        h = v - (thetanew / rho) * h
        while pend and (abs(zetabar) <= pend[0] * normar0 or trig):
            trig = True; _t = time.perf_counter(); _ok = bool(np.linalg.norm(rmv(b - mv(x))) <= pend[0] * normar0); t_tests += time.perf_counter() - _t; n_tests += 1      # cost of the explicit residual test (descriptive)
            if _ok:
                found[pend.pop(0)] = itn; trig = False
            else:
                break
        if not pend or alpha == 0 or beta == 0: break
    return found, x, normar0, dict(n_tests=n_tests, t_tests=t_tests, cond_est=float(max(maxrbar, rhobar) / min(minrbar, rhobar)), itn_last=itn)


def aug_ops(P, Jc, th, damp_eta):
    """Augmented operator [A J / sn ; c J] with c = sqrt(a + eta), eta = damp_eta * Lam_A, and rhs [r/sn ; -a x / c] at theta (truncated forward model)."""
    N, m, sn, a = P.N, P.m, P.sn, P.a; x = P.render(th); r = P.y - P.op.apply(x); c = float(np.sqrt(a + damp_eta * P.LamA)); p = Jc.shape[1]; JcT = Jc.T.tocsr()

    def mv(v):
        jv = Jc @ v; return np.concatenate([P.op.apply(jv.reshape(N, N)).ravel() / sn, c * jv])

    def rmv(u):
        return JcT @ (P.op.adj(u[:m].reshape(N, N)).ravel() / sn + c * u[m:])
    b = np.concatenate([r.ravel() / sn, -a * x.ravel() / c])
    return mv, rmv, b, p


def run_size(N, K):
    t_all = time.perf_counter(); rec = dict(N=N, K=K, p=6 * K, states={})
    sb, sn = SB, SN; op = GC.Op(N, sb); x = GG.ladder_target(N, K); y = GG.noisy_obs_geo(op, x, sn, GG.LADDER_SEED, K)
    P = GC.Prob(N, sb, y, sn, LAM / sn ** 2, renderer=lambda th: GC.render_trunc(th, N))
    th_grid = GC.grid_init(P, K)
    res5 = GC.solve('LSMR', P, th_grid, dict(kappa0=1e-3, f=10, sparse=True), max_iter=5)
    states = dict(grid=th_grid, iter5=res5['theta']); rec['iter5_stop'] = res5['stop']; rec['iter5_outer_itn'] = res5['itn']
    for sname, th in states.items():
        sr = dict()
        # (i) stage times of one outer LSMR iteration, 3 repeats
        reps = []
        for _ in range(3):
            r1 = GC.solve('LSMR', P, th, dict(kappa0=1e-3, f=10, sparse=True), max_iter=1)
            reps.append(dict(r1['T']) | dict(ok=not r1['stop'].startswith('no_step'), itn=r1['itn'][0] if r1['itn'] else None, hit_maxiter=bool(r1['itn'] and r1['itn'][0] >= 6 * K)))
        sr['stage_reps'] = reps
        med = {k: float(np.median([q[k] for q in reps])) for k in ('jac', 'aj', 'solve', 'back')}; tot = sum(med.values()); sr['stage_median'] = med
        sr['share'] = {k: v / tot for k, v in med.items()}
        # (ii) inner iterations to the explicit tolerance
        _, Jc = GC.render_jac_sparse(th, N)
        for dname, dkap in (('eta0', 0.0), ('kappa1e-3', 1e-3)):
            mv, rmv, b, n = aug_ops(P, Jc, th, dkap)
            t0 = time.perf_counter(); found, xk, na0, tst = lsmr_first_converged(mv, rmv, b, n); secs = time.perf_counter() - t0
            sr[dname] = dict(iters={('%g' % t): found[t] for t in TOLS}, censored={('%g' % t): found[t] is None for t in TOLS}, normar0=float(na0), seconds=secs, maxiter=20 * n,
                             residual_test=tst)
        # (iv) Gram coupling sparsity at block level
        Gm = (Jc.T @ Jc).tocoo(); kk = np.unique((Gm.row // 6) * K + (Gm.col // 6)); sr['gram_block_density'] = float(kk.size / (K * K))
        sr['J_nnz'] = int(Jc.nnz); rec['states'][sname] = sr
        print('  N=%d K=%d state=%s: iters eta0=%s kappa1e-3=%s  shares=%s' % (N, K, sname, sr['eta0']['iters'], sr['kappa1e-3']['iters'], {k: round(v, 2) for k, v in sr['share'].items()}), flush=True)
    # (iii) dense GEO / LMD one outer iteration (up to (96,324); (128,576) marked as over the limit)
    dense = {}
    if (N, K) != (128, 576):
        Pd = GC.Prob(N, sb, y, sn, LAM / sn ** 2)
        for arm, cfg in (('GEO', dict(kappa0=1e-3, f=10)), ('LMD', dict(kappa0=1e-3, f=10))):
            for sname, th in states.items():
                reps = 3 if N <= 64 else 1; ts = []
                for _ in range(reps):
                    t0 = time.perf_counter(); r1 = GC.solve(arm, Pd, th, cfg, max_iter=1); ts.append(time.perf_counter() - t0)
                dense['%s_%s' % (arm, sname)] = float(np.median(ts))
    else:
        dense['status'] = 'over the limit (not run)'
    rec['dense_one_iter_s'] = dense; rec['total_s'] = time.perf_counter() - t_all
    os.makedirs(OUT, exist_ok=True); json.dump(rec, open(os.path.join(OUT, 'L_%d_%d.json' % (N, K)), 'w'), indent=1)
    return rec


if __name__ == '__main__':
    kv = dict(a.split('=', 1) for a in sys.argv[1:] if '=' in a)
    sizes = [s for s in LADDER if 'only' not in kv or kv['only'] == '%d_%d' % s]
    for (N, K) in sizes:
        if os.path.exists(os.path.join(OUT, 'L_%d_%d.json' % (N, K))): print('skip', N, K); continue
        print('L size', N, K, flush=True); run_size(N, K)
    print('LADDER DONE', flush=True)
