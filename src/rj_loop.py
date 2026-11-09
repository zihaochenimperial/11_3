"""RJ closed-loop arms (contract RJ candidate v0). METHOD-SIDE code (never reads a clean image). Registers outer-iteration arm 'RJ' into the FROZEN geo_core.solve driver by adding an
entry to GC.ITER / GC.SAFETY at import time (geo_core.py, trn_loop.py are not edited). The frozen acceptance test GC._accept (RHO_MIN, GUARD, clamping) is used unchanged by every arm; the kappa
update rule and the per-trial CG budget are part of each ARM here (contract section 4, Opus R8).
cfg keys (all optional except kappa0, f):
  kappa0, f (reject factor), gdiv (accept & ratio>=0.75 -> kappa/gdiv; 3 = frozen; 1 = hold), nielsen (Nielsen update), eps_r (relative residual forcing, 0.1), maxcg (400), warm (x0 = last accepted step on first trial; default True),
  reuse (CR: retry trial starts from the previous trial's solution), cc (CC: per-trial CG cap = max(8, cc * CG iters of last accepted trial); cc_first_only: cap on the first trial only), early_m (CS: real charged _accept check every m CG iterations, first accepted stops),
  dq_tau (CD: stop when relative increase of the model gain falls below tau), ew_gamma (CW: Eisenstat-Walker choice-2 forcing), oracle ('dF' | 'beta' | 'sbeta': free probing of kappa candidates kappa_ref*3^j, j=-2..3, each run with THIS arm's own trial procedure; only the chosen candidate is charged; dF = largest decrease, beta = cheapest candidate with
  dF >= beta*dF_max, sbeta = additionally stop each candidate at the first accepted checked iterate (every oracle_m=4 CG iterations, free) with dF >= beta*dF_full(kappa)), free_reject (OS: rejected trials cost nothing).
Work W is the frozen flop proxy (same charging as trn_loop._iter_trn); probes are rolled back (S counters, T['back'], cnt['W'], cnt['A'])."""
import numpy as np
import geo_core as GC
import geo_flops as FL
import trn_flops as TF

ALPHA_EW = (1.0 + 5.0 ** 0.5) / 2.0
ORACLE_J = (-2, -1, 0, 1, 2, 3)


def _cat(cnt):
    if 'log' not in cnt: cnt['log'] = []
    return cnt['log']


def _free_accept(P, S, th2raw, Jmul, cnt, T, wmv):
    """GC._accept on a scratch basis: every side effect (S counters, T['back'], cnt W / A) is rolled back. Returns the same tuple as GC._accept."""
    snap = (S['trials'], S['clamped'], S['clamp_trials'], T['back'], cnt['W'], cnt['A'])
    out = GC._accept(P, S, th2raw, Jmul, cnt, T, wmv=wmv)
    S['trials'], S['clamped'], S['clamp_trials'], T['back'], cnt['W'], cnt['A'] = snap
    return out


def _pcg_rj(matvec, g, prec, x0, eps_r, maxcg, wmv, p, cnt, box, every=0, check=None, dq_tau=0.0):
    """Same recursion and charging as trn_loop._pcg_rel (bitwise identical when every=0, dq_tau=0). Extras: check(x, it) every `every` iterations returns None or an acceptance tuple (stop = 'early');
    dq_tau > 0 stops when the model gain 0.5 x.(g + res) rises by <= dq_tau relatively. Returns (x, iterations, reason, early_tuple); reason in tol, den, cap, dq, early."""
    gn = float(np.linalg.norm(g)); x = np.zeros(p) if x0 is None else x0.copy(); res = g.copy(); it = 0
    if x0 is not None and np.any(x0):
        res = g - matvec(x); cnt['mv'] += 1; cnt['A'] += 2; cnt['W'] += wmv; box[0] += wmv
    if gn == 0.0 or float(np.linalg.norm(res)) <= eps_r * gn: return x, 0, 'tol', None
    z = prec(res); rz = float(res @ z); pdir = z.copy(); dq_prev = None; reason = 'cap'
    while it < maxcg:
        Hp = matvec(pdir); cnt['mv'] += 1; cnt['A'] += 2; w = wmv + 8.0 * p; cnt['W'] += w; box[0] += w; den = float(pdir @ Hp)
        if not den > 0: reason = 'den'; break
        al = rz / den; x += al * pdir; res -= al * Hp; it += 1
        if float(np.linalg.norm(res)) <= eps_r * gn: reason = 'tol'; break
        if dq_tau > 0:
            dq = 0.5 * float(x @ (g + res))
            if dq_prev is not None and dq > 0 and (dq - dq_prev) <= dq_tau * dq: reason = 'dq'; break
            dq_prev = dq
        if every and it % every == 0:
            e = check(x, it)
            if e is not None: return x, it, 'early', e
        z = prec(res); rz2 = float(res @ z)
        if abs(rz2) < 1e-300: reason = 'den'; break
        pdir = z + (rz2 / rz) * pdir; rz = rz2
    return x, it, reason, None


def _kappa_after_accept(cfg, kap, ratio):
    if cfg.get('nielsen'):
        return min(max(kap * max(1.0 / 3.0, 1.0 - (2.0 * ratio - 1.0) ** 3), GC.KAPPA_MIN), GC.KAPPA_MAX)
    gdiv = cfg.get('gdiv', 3)
    return max(kap / gdiv, GC.KAPPA_MIN) if ratio >= 0.75 else kap


def _iter_rj(P, S, cfg, cnt, T):
    th, x, r = S['th'], S['x'], S['r']; N = P.N; K = th.shape[0]; p = K * 6; sn, a = P.sn, P.a; f = cfg['f']; maxcg = cfg.get('maxcg', 400); eps_r = cfg.get('eps_r', 0.1); oracle = cfg.get('oracle'); m_every = int(cfg.get('early_m', 0) or 0)
    rec = dict(W_jac=0.0, W_rhs=0.0, W_setup=0.0, W_setup_Ainner=0.0, W_cg=0.0, W_acc=0.0, trials=[], kap_acc=None, tinfo=[], probe=None, eps_used=None, sel=None, fallback=False)
    w0 = cnt['W']; J = GC._make_J(P, th, cnt, T, True); rec['W_jac'] = cnt['W'] - w0
    wJ = FL.F_matvec(J.nnz); wA = FL.F_A(N); wmv = TF.F_H_matvec(N, J.nnz)
    w0 = cnt['W']; g = J.tmul(P.op.adj(r).ravel() / sn ** 2) - a * J.tmul(x.ravel()); cnt['A'] += 1; cnt['W'] += wA + 2 * wJ; rec['W_rhs'] = cnt['W'] - w0
    act = GC.bound_active(th, -g, N); S['act'].append(int(act.sum())); J = GC._mask_J(J, act); g[act] = 0.0; free = ~act; mask = free.astype(float)
    w0 = cnt['W']; dg = J.colnorm2(); cnt['W'] += wJ; rec['W_setup'] = cnt['W'] - w0
    dinv = mask / (dg + 1e-12); prec = lambda rr: dinv * rr
    if cfg.get('ew_gamma'):                                                               # CW: Eisenstat-Walker choice 2 (g-norm of this and the previous outer iteration)
        gnorm = float(np.linalg.norm(g)); prev = S.get('gn_prev')
        if prev: eps_r = float(min(max(cfg['ew_gamma'] * (gnorm / prev) ** ALPHA_EW, 1e-3), 0.5))
        S['gn_prev'] = gnorm
    rec['eps_used'] = eps_r
    x0w = (mask * S['dprev']) if (cfg.get('warm', True) and S.get('dprev') is not None) else None
    wacc_one = wJ + 2 * wA + FL.F_render(K, N)                                            # what one GC._accept charges: J mul + F_of (A, render) + gain_pred (A)
    last_acc_it = S['itn'][-1] if S['itn'] else None

    def mk_matvec(kap):
        cc = a + kap * P.LamA

        def matvec(v):
            jv = J.mul(mask * v); Aj = P.op.apply(jv.reshape(N, N)); return mask * J.tmul(P.op.adj(Aj.reshape(N, N)).ravel() / sn ** 2 + cc * jv)
        return matvec

    def cap_of(tri=0):                                                                    # cc_first_only (amendment A1/R27): the budget cap applies to the first trial only, retries use maxcg
        if cfg.get('cc') and last_acc_it is not None and not (cfg.get('cc_first_only') and tri > 0): return int(min(maxcg, max(8, cfg['cc'] * last_acc_it)))
        return maxcg

    def trial(kap, x0, cap, free_mode, every=None, use_dq=True):
        """The arm's trial procedure at damping kap. free_mode: all costs go to a scratch counter and every acceptance call is rolled back (oracle probe); otherwise charged to cnt. Returns a dict with the solution,
        its acceptance tuple, the CG cost `box`, the number of acceptance calls `nacc` (mid-CG checks + the final one unless the last check coincides with the end) and the scratch counter `sc`."""
        sc = dict(mv=0, A=0, W=0.0) if free_mode else cnt; box = [0.0]; nacc = [0]; last = [None]; wacc = [0.0]
        every = m_every if every is None else every

        def acc(xx):
            nacc[0] += 1
            if free_mode: return _free_accept(P, S, th + xx.reshape(th.shape), J.mul, sc, T, wJ)
            w1 = cnt['W']; t_ = GC._accept(P, S, th + xx.reshape(th.shape), J.mul, cnt, T, wmv=wJ); wacc[0] += cnt['W'] - w1; return t_

        def chk(xx, it_):
            t_ = acc(xx); last[0] = (it_, t_); return t_ if t_[0] else None
        d, itc, reason, early = _pcg_rj(mk_matvec(kap), g, prec, x0, eps_r, cap, wmv, p, sc, box, every=every, check=chk, dq_tau=(cfg.get('dq_tau', 0.0) if use_dq else 0.0))
        tup = early if early is not None else (last[0][1] if (last[0] is not None and last[0][0] == itc) else acc(d))
        return dict(kap=kap, d=d, it=itc, reason=reason, early=early is not None, tup=tup, box=box[0], nacc=nacc[0], sc=sc, wacc=wacc[0], cost=box[0] + nacc[0] * wacc_one)

    def accept_state(kap, tr):
        ok, ratio, th2, x2, r2, F2 = tr['tup']; S.update(th=th2, x=x2, r=r2, F=F2); S['kappa'] = _kappa_after_accept(cfg, kap, ratio)
        S['dprev'] = tr['d'].copy(); S['itn'].append(tr['it']); rec['kap_acc'] = kap; rec['th'] = th.copy(); rec['d'] = tr['d'].copy(); rec['F'] = float(S['F']); _cat(cnt).append(rec)

    kap = S['kappa']
    if oracle:                                                                            # ---- free probing of kappa candidates (composed with this arm's trial procedure); only the chosen one is charged
        kref = kap; cands = sorted({float(min(max(kref * 3.0 ** j, GC.KAPPA_MIN), GC.KAPPA_MAX)) for j in ORACLE_J}); probes = []; w_fixed = rec['W_jac'] + rec['W_rhs'] + rec['W_setup']; beta = float(cfg.get('beta', 0.5))
        for kc in cands:
            if oracle == 'sbeta':                                                         # OKSbeta: stop at the first accepted checked iterate with dF >= beta * dF_full(kappa); the arm's own early_m is ignored
                tr = trial(kc, x0w, cap_of(), True, every=0); okf, _, _, _, _, F2f = tr['tup']; dFf = (S['F'] - F2f) if okf else 0.0
                sc2 = dict(mv=0, A=0, W=0.0); box2 = [0.0]

                def chk2(xx, it_):
                    t_ = _free_accept(P, S, th + xx.reshape(th.shape), J.mul, sc2, T, wJ)
                    if t_[0] and (S['F'] - t_[5]) >= beta * dFf: return t_
                    return None
                d2, it2, reason2, early2 = _pcg_rj(mk_matvec(kc), g, prec, x0w, eps_r, cap_of(), wmv, p, sc2, box2, every=cfg.get('oracle_m', 4), check=chk2, dq_tau=cfg.get('dq_tau', 0.0))
                if early2 is not None: tr = dict(kap=kc, d=d2, it=it2, reason='early', early=True, tup=early2, box=box2[0], nacc=1, sc=dict(sc2), wacc=0.0, cost=box2[0] + wacc_one)
                else: tr['nacc'] = 1; tr['cost'] = tr['box'] + wacc_one
            else: tr = trial(kc, x0w, cap_of(), True)
            ok_, ratio_ = tr['tup'][0], tr['tup'][1]; dF = (S['F'] - tr['tup'][5]) if ok_ else 0.0
            probes.append(dict(tr, ok=bool(ok_), ratio=float(ratio_), dF=float(dF), cost=float(w_fixed + tr['cost'])))
        okp = [q for q in probes if q['ok']]
        rec['probe'] = [dict(kap=q['kap'], it=q['it'], reason=q['reason'], ok=q['ok'], dF=q['dF'], cost=q['cost'], nacc=q['nacc'], A=int(q['sc']['A'])) for q in probes]
        if okp:
            if oracle == 'dF': best = max(okp, key=lambda q: q['dF'])
            else:
                dmax = max(q['dF'] for q in okp); best = min([q for q in okp if q['dF'] >= beta * dmax], key=lambda q: q['cost'])      # beta / sbeta: cheapest candidate with dF >= beta * dF_max
            rec['sel'] = dict(kap=best['kap'], kref=kref, j=int(round(np.log(best['kap'] / kref) / np.log(3.0))) if best['kap'] > 0 else None, it=best['it'], reason=best['reason'], nacc=best['nacc'])
            extra = best['nacc'] - 1                                                      # acceptance calls of the arm's procedure beyond the one GC._accept executed below
            cnt['W'] += best['box'] + extra * wacc_one; cnt['mv'] += best['sc']['mv']; cnt['A'] += best['sc']['A'] + 2 * extra; S['trials'] += extra; rec['W_cg'] += best['box']
            w1 = cnt['W']; ok, ratio, th2, x2, r2, F2 = GC._accept(P, S, th + best['d'].reshape(th.shape), J.mul, cnt, T, wmv=wJ); rec['W_acc'] += (cnt['W'] - w1) + extra * wacc_one
            assert ok, 'oracle probe / charged acceptance mismatch'
            rec['trials'].append(best['it']); rec['tinfo'].append(dict(kap=best['kap'], it=best['it'], ok=True, reason=best['reason'], cap=bool(best['reason'] == 'cap'), early=bool(best['early']), nacc=best['nacc'], ratio=float(ratio)))
            accept_state(best['kap'], dict(d=best['d'], it=best['it'], tup=(ok, ratio, th2, x2, r2, F2))); return True
        kap = cands[-1]; rec['fallback'] = True                                           # no candidate accepted: re-run (charged) from the largest candidate, then x f ...
    nu = 2.0; d_prev_trial = None
    for tri in range(GC.BACKTRACKS):
        x0 = x0w if tri == 0 else ((mask * d_prev_trial) if (cfg.get('reuse') and d_prev_trial is not None) else None); snap_c = (cnt['W'], cnt['A'], cnt['mv'])
        tr = trial(kap, x0, cap_of(tri), False); rec['W_cg'] += tr['box']; rec['W_acc'] += tr['wacc']; rec['trials'].append(tr['it']); ok, ratio = tr['tup'][0], tr['tup'][1]
        rec['tinfo'].append(dict(kap=kap, it=tr['it'], ok=bool(ok), reason=tr['reason'], cap=bool(tr['reason'] == 'cap'), early=bool(tr['early']), nacc=tr['nacc'], ratio=float(ratio)))
        if cfg.get('free_reject') and not ok:                                             # OS: rejected trials cost nothing (same kappa sequence, same trajectory as the base arm)
            cnt['W'], cnt['A'], cnt['mv'] = snap_c; rec['W_cg'] -= tr['box']; rec['W_acc'] -= tr['wacc']
        if ok: accept_state(kap, tr); return True
        S['rej'] += 1; d_prev_trial = tr['d']
        if kap >= GC.KAPPA_MAX: break
        if cfg.get('nielsen'): kap = min(kap * nu, GC.KAPPA_MAX); nu *= 2.0
        else: kap = min(kap * f, GC.KAPPA_MAX)
    S['kappa'] = kap; _cat(cnt).append(rec)
    return False


GC.ITER['RJ'] = _iter_rj
GC.SAFETY['RJ'] = 5000


def rj_solve(P, th0, cfg, max_outer=150, F_target=None, keep_theta=False):
    """Driver identical to the frozen GC.solve loop logic (reject streak 'dead' rule, 3 consecutive relative decreases <= 1e-9 -> converged) with two additions: stop='target' when F <= F_target
    (checked after an accepted iteration) and an outer cap max_outer. Returns the GC.solve-style dict (traj rows (it, F, t, A, J, mv, W, rss, Ad, Wd))."""
    import time
    cnt = dict(A=0, J=0, mv=0, W=0.0, Ad=0, Wd=0.0); T = dict(jac=0.0, aj=0.0, solve=0.0, back=0.0)
    th = GC.clamp(th0, P.N); F, x, r = P.F_of(th)
    S = dict(th=th, x=x, r=r, F=F, kappa=cfg['kappa0'], rej=0, rank=None, trials=0, clamped=0, clamp_trials=0, diag=[], itn=[], alpha=[], act=[], alpha_star=[], clamp_it=[], blk_skip=0, blk_eval=0)
    traj = [(0, F, 0.0, 0, 0, 0, 0.0, float(np.sum(r * r)), 0, 0.0)]; th_hist = [th.copy()] if keep_theta else None
    small = 0; fails = 0; stop = 'max_iter'; clock0 = time.perf_counter()
    for it in range(1, max_outer + 1):
        Fold = S['F']; cl_before = S['clamped']; ct_before = S['clamp_trials']; ok = _iter_rj(P, S, cfg, cnt, T); S['clamp_it'].append(S['clamped'] - cl_before)
        t_now = time.perf_counter() - clock0; rss = float(np.sum(S['r'] ** 2))
        traj.append((it, S['F'], t_now, cnt['A'], cnt['J'], cnt['mv'], cnt['W'], rss, cnt['Ad'], cnt['Wd']))
        if keep_theta: th_hist.append(S['th'].copy())
        if not ok:
            if fails == 0: ct_first = ct_before
            fails += 1
            if S['kappa'] >= GC.KAPPA_MAX and fails >= 2: stop = 'no_step_clamp' if S['clamp_trials'] > ct_first else 'no_step'; break
            continue
        fails = 0
        if F_target is not None and S['F'] <= F_target: stop = 'target'; break
        small = small + 1 if (Fold - S['F']) <= 1e-9 * abs(Fold) else 0
        if small >= 3: stop = 'converged'; break
    out = dict(theta=S['th'], F=S['F'], traj=traj, stop=stop, rej=S['rej'], trials=S['trials'], itn=S['itn'], act=S['act'], cnt=cnt, T=T, kappa=S['kappa'])
    if keep_theta: out['th_hist'] = th_hist
    return out


def nnz_B(N, sb):
    return int(np.count_nonzero(GC.refl_B(N, sb)))


def w_sparse(traj, N, sb):
    """Primary cost basis (contract section 3): W_sp(t) = W(t) - A(t) (F_A_dense - F_A_sparse) with F_A_sparse = 4 N nnz(B) (the same operator B (x) B applied as two sparse products)."""
    delta = FL.F_A(N) - 4.0 * N * nnz_B(N, sb)
    return [float(row[6] - row[3] * delta) for row in traj]
