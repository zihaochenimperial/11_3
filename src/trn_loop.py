"""TRN closed-loop inner solvers (contract TRN v1 sections 4, 6). METHOD-SIDE code (never reads a clean image). Registers an outer-iteration arm 'TRN' into the FROZEN
geo_core.solve driver by adding entries to GC.ITER / GC.SAFETY at import time (geo_core.py itself is not edited), so the frozen acceptance rule (_accept/_finish: kappa rule, RHO_MIN, guard,
clamping), the frozen active set and the frozen convergence logic are shared by every arm.
Arm configuration (cfg): kappa0, f, inner in {'J' (Jacobi diag J^T J), 'BJ' (6x6 block Jacobi), 'BJ0' ... }, eps_r (relative residual forcing), maxcg, warm (D0w: x0 = last accepted step).
Work W is the frozen flop proxy; per-category counters in out['cnt']['log'] (one dict per outer iteration): W_jac (Jacobian build), W_rhs (gradient), W_setup (preconditioner / deflation set-up),
W_cg (CG iterations incl. rejected trials), W_acc (acceptance: render, A applications), W_asm_strict / cached split for BJ (cached = strict minus the p A-applications of the AJ columns)."""
import time
import numpy as np
import scipy.sparse as sp
import geo_core as GC
import geo_flops as FL
import trn_flops as TF


def _bj_blocks(J, P, th, free):
    """Per-Gaussian 6x6 Gram blocks of AJ and J (sparse truncated J, free coordinates only). Returns GA (K,6,6) (already / sn^2), GJ (K,6,6), AJ-application count."""
    K = th.shape[0]; N = P.N; m = N * N; idx = np.flatnonzero(free)
    Jd = J.Jc[:, idx].toarray().T.reshape(len(idx), N, N); AJ = P.op.apply_stack(Jd).reshape(len(idx), m); Jd = Jd.reshape(len(idx), m)
    GA = np.zeros((K, 6, 6)); GJ = np.zeros((K, 6, 6)); pos = -np.ones(6 * K, int); pos[idx] = np.arange(len(idx))
    for k in range(K):
        cols = pos[6 * k:6 * k + 6]; ok = cols >= 0
        if not ok.any(): continue
        c = cols[ok]; a_ = AJ[c] @ AJ[c].T / P.sn ** 2; j_ = Jd[c] @ Jd[c].T; sub = np.ix_(ok, ok)
        GA[k][sub] = a_; GJ[k][sub] = j_
    return GA, GJ, len(idx)


def _bj_inverse(GA, GJ, cc, free):
    """Batched pseudo-inverse of the K 6x6 blocks B_k = GA_k + cc GJ_k (hermitian pinv, rcond 1e-12; frozen/zero-column coordinates have zero rows/columns and map to 0)."""
    B = GA + cc * GJ; B = 0.5 * (B + np.transpose(B, (0, 2, 1)))
    return np.linalg.pinv(B, rcond=1e-12, hermitian=True)


def _cat(cnt):
    if 'log' not in cnt: cnt['log'] = []
    return cnt['log']


def _pcg_rel(matvec, g, prec, x0, eps_r, maxcg, wmv, p, cnt, W_cg_box):
    """CG on H x = g with callable preconditioner; stop at ||res|| <= eps_r ||g||. Charges matvecs (wmv each) and 8p vector work per iteration to cnt['W'] and W_cg_box[0]."""
    gn = float(np.linalg.norm(g)); x = np.zeros(p) if x0 is None else x0.copy(); res = g.copy(); it = 0
    if x0 is not None and np.any(x0):
        res = g - matvec(x); cnt['mv'] += 1; cnt['A'] += 2; cnt['W'] += wmv; W_cg_box[0] += wmv
    if gn == 0.0 or float(np.linalg.norm(res)) <= eps_r * gn: return x, 0
    z = prec(res); rz = float(res @ z); pdir = z.copy()
    while it < maxcg:
        Hp = matvec(pdir); cnt['mv'] += 1; cnt['A'] += 2; w = wmv + 8.0 * p; cnt['W'] += w; W_cg_box[0] += w; den = float(pdir @ Hp)
        if not den > 0: break
        al = rz / den; x += al * pdir; res -= al * Hp; it += 1
        if float(np.linalg.norm(res)) <= eps_r * gn: break
        z = prec(res); rz2 = float(res @ z)
        if abs(rz2) < 1e-300: break
        pdir = z + (rz2 / rz) * pdir; rz = rz2
    return x, it


def _iter_trn(P, S, cfg, cnt, T):
    th, x, r = S['th'], S['x'], S['r']; N = P.N; p = th.shape[0] * 6; sn, a = P.sn, P.a; f = cfg['f']; kind = cfg.get('inner', 'J'); eps_r = cfg.get('eps_r', 1e-2); maxcg = cfg.get('maxcg', 400)
    rec = dict(W_jac=0.0, W_rhs=0.0, W_setup=0.0, W_setup_Ainner=0.0, W_cg=0.0, W_acc=0.0, trials=[], kap_acc=None)
    w0 = cnt['W']; J = GC._make_J(P, th, cnt, T, True); rec['W_jac'] = cnt['W'] - w0
    wJ = FL.F_matvec(J.nnz); wA = FL.F_A(N); wmv = TF.F_H_matvec(N, J.nnz)
    w0 = cnt['W']; g = J.tmul(P.op.adj(r).ravel() / sn ** 2) - a * J.tmul(x.ravel()); cnt['A'] += 1; cnt['W'] += wA + 2 * wJ; rec['W_rhs'] = cnt['W'] - w0
    act = GC.bound_active(th, -g, N); S['act'].append(int(act.sum())); J = GC._mask_J(J, act); g[act] = 0.0; free = ~act; mask = free.astype(float)
    w0 = cnt['W']; dg = J.colnorm2(); cnt['W'] += wJ
    if kind in ('BJ',):
        GA, GJ, nfree = _bj_blocks(J, P, th, free); cnt['A'] += nfree; cnt['Ad'] += nfree
        wbuild = nfree * wA + th.shape[0] * (2.0 * N * N * 36 * 2); cnt['W'] += wbuild; cnt['Wd'] += nfree * wA; rec['W_setup_Ainner'] = nfree * wA
    rec['W_setup'] = cnt['W'] - w0
    kap = S['kappa']; x0 = S.get('dprev') if cfg.get('warm') else None
    for trial in range(GC.BACKTRACKS):
        cc = a + kap * P.LamA

        def matvec(v):
            jv = J.mul(mask * v); Aj = P.op.apply(jv.reshape(N, N)); return mask * J.tmul(P.op.adj(Aj.reshape(N, N)).ravel() / sn ** 2 + cc * jv)
        if kind == 'J':
            dinv = mask / (dg + 1e-12); prec = lambda rr: dinv * rr
        else:
            Binv = _bj_inverse(GA, GJ, cc, free); prec = lambda rr: mask * (Binv @ rr.reshape(-1, 6, 1)).reshape(-1)
        box = [0.0]; d, itc = _pcg_rel(matvec, g, prec, None if (x0 is None or trial > 0) else mask * x0, eps_r, maxcg, wmv, p, cnt, box); rec['W_cg'] += box[0]; rec['trials'].append(itc)
        w0 = cnt['W']; ok, ratio, th2, x2, r2, F2 = GC._accept(P, S, th + d.reshape(th.shape), J.mul, cnt, T, wmv=wJ); rec['W_acc'] += cnt['W'] - w0
        if GC._finish(S, ok, ratio, th2, x2, r2, F2, kap, f):
            S['dprev'] = d.copy(); S['itn'].append(rec['trials'][-1]); rec['kap_acc'] = kap; rec['th'] = th.copy(); rec['d'] = d.copy(); rec['F'] = float(S['F']); _cat(cnt).append(rec); return True
        if kap >= GC.KAPPA_MAX: break
        kap = min(kap * f, GC.KAPPA_MAX)
    S['kappa'] = kap; _cat(cnt).append(rec)
    return False


GC.ITER['TRN'] = _iter_trn
GC.SAFETY['TRN'] = 5000


def summarize(out, F_ref, tol=1e-3):
    """Per-run S0 readout from a solve() result: iterations/W to the target F - F_ref <= tol (F0 - F_ref), category split over the iterations up to that crossing, f_iter, f_asm (J build + set-up),
    matvecs per outer iteration. Returns dict (target_hit False -> censored at the end of the run)."""
    tr = out['traj']; F0 = tr[0][1]; tgt = F_ref + tol * (F0 - F_ref); hit = None
    for i, row in enumerate(tr):
        if row[1] <= tgt: hit = i; break
    last = hit if hit is not None else len(tr) - 1
    log = out['cnt'].get('log', [])[:last] if last > 0 else []
    tot = {k: sum(r[k] for r in log) for k in ('W_jac', 'W_rhs', 'W_setup', 'W_setup_Ainner', 'W_cg', 'W_acc')}; Wtot = sum(tot[k] for k in ('W_jac', 'W_rhs', 'W_setup', 'W_cg', 'W_acc'))
    mv = [sum(r['trials']) for r in log]
    return dict(hit=hit is not None, iters=last, W_to_target=float(Wtot), W_run_total=float(tr[-1][6]), cats=tot, f_iter=float(tot['W_cg'] / Wtot) if Wtot > 0 else float('nan'),
                f_asm=float((tot['W_jac'] + tot['W_setup']) / Wtot) if Wtot > 0 else float('nan'), f_asm_cached=float((tot['W_jac'] + tot['W_setup'] - tot['W_setup_Ainner']) / Wtot) if Wtot > 0 else float('nan'),
                cg_per_outer_median=float(np.median(mv)) if mv else float('nan'), cg_trials=[r['trials'] for r in log], kap_acc=[r['kap_acc'] for r in log], stop=out['stop'], rej=out['rej'])
