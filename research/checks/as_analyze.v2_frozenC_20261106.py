"""AS contract v2.1 FROZEN ANALYZER (run once on S2 outputs; sha256 recorded in contracts/FROZEN_AS_CONTRACT_v2_1.md before any S2 job is submitted).
usage:  as_analyze.py root=<AS-S2 dir> out=<report dir>      (reads <root>/<ARM>/*.json and <root>-ORX/<ARM>/*.json)
        as_analyze.py selftest                              (synthetic-data checks of every statistic and of the decision table; no real results)
The statistics/decision logic is in the pure functions analyze()/decide(); I/O is in load_all(). Evaluator side: this file may read the clean images (it never feeds anything back to methods)."""
import os, sys, json, math, hashlib, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))
import numpy as np

IMGS = list(range(1, 25)); CONDS = ['C1', 'C2', 'C3', 'C4']; SEEDS = [9001, 9002]
KEYS = [(i, c, s) for i in IMGS for c in CONDS for s in SEEDS]           # 192 units
KEYS9001 = [k for k in KEYS if k[2] == 9001]                              # 96 units
FULL12 = [(i, c, 9001) for i in (1, 9, 17, 2, 10, 18) for c in ('C1', 'C4')]
FAMS = {'edge': range(1, 9), 'tex': range(9, 17), 'mix': range(17, 25)}
LOG95 = math.log(0.95); LOG102 = math.log(1.02)
TAU = 1.0


# ------------------------------------------------------------------ statistics
def signflip_p(D):
    """Exact one-sided sign-flip p: #{s in {+-1}^n : mean(s*D) <= mean(D)} / 2^n, by meet-in-the-middle (deterministic). Returns (p, count, total)."""
    D = np.asarray(D, float); n = len(D); n1 = n // 2; n2 = n - n1
    def sums(d):
        m = len(d); bits = (np.arange(2 ** m)[:, None] >> np.arange(m)[None, :]) & 1
        return (1 - 2 * bits) @ d
    A = sums(D[:n1]); B = np.sort(sums(D[n1:])); T = float(D.sum()); tol = 1e-10 * max(1.0, float(np.abs(D).sum()))
    cnt = int(np.searchsorted(B, T + tol - A, side='right').sum()); tot = 2 ** n
    return cnt / tot, cnt, tot


def per_image_D(MJ, MR, keys_by_img=None):
    """D_i = mean over the image's units of log(M_J/M_R); also D_ic (per image x condition, mean over seeds present)."""
    D = []; Dic = {}
    for i in IMGS:
        ks = [k for k in MJ if k[0] == i and k in MR]
        D.append(np.mean([math.log(MJ[k] / MR[k]) for k in ks]) if ks else float('nan'))
        for c in CONDS:
            kc = [k for k in ks if k[1] == c]
            Dic[(i, c)] = float(np.mean([math.log(MJ[k] / MR[k]) for k in kc])) if kc else float('nan')
    return np.array(D), Dic


def gate1_stats(MJ, MR):
    D, Dic = per_image_D(MJ, MR); ok = np.all(np.isfinite(D))
    meanD = float(np.mean(D)); p, cnt, tot = signflip_p(D)
    cond_means = {c: float(np.mean([Dic[(i, c)] for i in IMGS])) for c in CONDS}
    fam_means = {f: float(np.mean([D[i - 1] for i in r])) for f, r in FAMS.items()}
    i_ = meanD <= LOG95; ii = p < 0.05; iii = all(v <= LOG102 for v in cond_means.values()); iv = sum(v <= 0 for v in fam_means.values()) >= 2
    return dict(ok=bool(ok), meanD=meanD, ratio=math.exp(meanD), p=p, count=cnt, total=tot, sd=float(np.std(D, ddof=1)), se=float(np.std(D, ddof=1) / math.sqrt(len(D))),
                cond_means={c: v for c, v in cond_means.items()}, fam_means=fam_means, pass_i=bool(i_), pass_ii=bool(ii), pass_iii=bool(iii), pass_iv=bool(iv), passed=bool(i_ and ii and iii and iv), D=[float(x) for x in D])


def gm_log(M, keys):
    return float(np.mean([math.log(M[k]) for k in keys]))


def H(MX, Mc, keys):
    """H_X = 1 - exp(mean_u log(M_X / M_cheap)) over `keys` (positive = X has lower geometric-mean MSE)."""
    return 1.0 - math.exp(float(np.mean([math.log(MX[k] / Mc[k]) for k in keys])))


REQUIRED = ['OMP', 'BLOCK', 'JOINT', 'FIXED', 'ORACLE_xs', 'ORACLE_ys', 'OMP_b', 'OMP_s', 'JOINT_b', 'JOINT_s']      # BLOCK_b/BLOCK_s dropped by contract section-5 budget cut (4); see variant()
REQ_KEYS = {'ORACLE_ys': KEYS9001}


def analyze(M, aux):
    """M: {arm: {(img,cond,seed): final clean MSE}}; aux: {v10_rate, ...}. Returns the full report dict including the decision."""
    rep = dict(missing=[], notes=[])
    for a in REQUIRED:
        need = REQ_KEYS.get(a, KEYS); miss = [k for k in need if k not in M.get(a, {})]
        if miss: rep['missing'].append((a, len(miss)))
    if rep['missing']:
        rep['decision'] = 'INCOMPLETE'; rep['decision_detail'] = 'required arms/units missing: %s (no decision is made; a missing required unit is an infrastructure failure, not a result)' % rep['missing']
        return rep
    gO = {a: gm_log(M[a], KEYS) for a in ('OMP', 'BLOCK')}
    cheap = 'OMP' if gO['OMP'] <= gO['BLOCK'] else 'BLOCK'; Mc = M[cheap]; rep['cheap'] = cheap; rep['cheap_gm_logs'] = gO
    rep['H'] = {a: H(M[a], Mc, KEYS) for a in ('JOINT', 'OMP', 'BLOCK', 'FIXED', 'ORACLE_xs') + (('RAND',) if 'RAND' in M and all(k in M['RAND'] for k in KEYS) else ()) + (('JOINT_FREE',) if 'JOINT_FREE' in M and all(k in M['JOINT_FREE'] for k in KEYS) else ())}
    rep['H_Oys'] = H(M['ORACLE_ys'], Mc, KEYS9001); rep['H_J_9001'] = H(M['JOINT'], Mc, KEYS9001)
    # ---- Gate 0
    rep['H_Oxs'] = rep['H']['ORACLE_xs']
    if rep['H_Oxs'] >= 0.10: rep['gate0'] = 'PASS'
    else:
        xf = M.get('ORACLE_x_full', {})
        if not all(k in xf for k in FULL12): rep['gate0'] = 'PENDING_FULL'; rep['gate0_detail'] = 'ORACLE_xs < 10% and ORACLE_x-full (12 units) not yet run -> run the conditional plan oracle_x_full'
        else:
            hf = H(xf, Mc, FULL12); hs = H(M['ORACLE_xs'], Mc, FULL12); rep['H_Ofull12'] = hf; rep['H_Oxs12'] = hs
            if hf < 0.10 and hs < 0.10: rep['gate0'] = 'FAIL'
            elif hf >= 0.10 and hs < 0.10: rep['gate0'] = 'INCONCLUSIVE-shortlist'
            else: rep['gate0'] = 'INCONCLUSIVE-unspecified'; rep['notes'].append('H_Oxs(192)<10% but both 12-unit oracles >=10%: case not covered by the contract; not released, flag for Opus')
    # ---- Gate 1 (JOINT vs each cheap rule; intersection-union)
    rep['gate1'] = {R: gate1_stats(M['JOINT'], M[R]) for R in ('OMP', 'BLOCK')}
    rep['gate1_all'] = all(g['passed'] and g['ok'] for g in rep['gate1'].values())
    # ---- Gate F
    gj = gm_log(M['JOINT'], KEYS); gf = gm_log(M['FIXED'], KEYS); rep['gateF_ratio_FIXED_over_JOINT'] = math.exp(gf - gj); rep['gateF_fail'] = (math.exp(gf - gj) <= 1.02)
    # ---- type mix (budget cut (4): BLOCK_s not run; BLOCK_b is bitwise identical to OMP_b -- BLOCK's birth score equals OMP-raw's (no parent) -- verified in S0)
    def variant(R, t):
        a = R + '_' + t
        if a in M and all(k in M[a] for k in KEYS): return M[a]
        if R == 'BLOCK' and t == 'b': return M['OMP_b']
        return None
    tm = {}
    for R in ('OMP', 'BLOCK'):
        g = rep['gate1'][R]
        if g['pass_i'] and g['pass_ii']:
            wins = {}
            for t in ('b', 's'):
                Mv = variant(R, t)
                if Mv is None: wins[t] = None; continue
                Dt, _ = per_image_D(M['JOINT_' + t], Mv); p, _c, _t = signflip_p(Dt); wins[t] = bool(float(np.mean(Dt)) < 0 and p < 0.10); wins[t + '_meanD'] = float(np.mean(Dt)); wins[t + '_p'] = p
            wins['typemix'] = (wins['b'] is False) and (wins['s'] is False)
            wins['unassessed'] = (not wins['typemix']) and (wins['b'] is not True) and (wins['s'] is not True)      # some variant missing and no variant win
            tm[R] = wins
    rep['typemix'] = tm; rep['typemix_flag'] = any(v['typemix'] for v in tm.values()); rep['typemix_unassessed'] = any(v['unassessed'] for v in tm.values())
    rep['v10_rate'] = aux.get('v10_rate'); rep['H_Oys_pos'] = rep['H_Oys'] > 0
    # ---- decision table (order as in the contract)
    rep['decision'], rep['decision_detail'] = decide(rep)
    # ---- secondary reports (no decision weight)
    if 'JOINT_FREE' in M and all(k in M['JOINT_FREE'] for k in KEYS):
        Dj, _ = per_image_D(M['JOINT'], M['JOINT_FREE']); rep['JOINT_vs_JOINT_FREE'] = dict(meanD=float(np.mean(Dj)), ratio=math.exp(float(np.mean(Dj))))
    yf = M.get('ORACLE_y_full', {}); ks = [k for k in sorted(yf) if k in M['JOINT']]
    if ks: rep['JOINT_vs_ORACLE_y_full'] = dict(n=len(ks), geo_ratio_JOINT_over_oracle=math.exp(float(np.mean([math.log(M['JOINT'][k] / yf[k]) for k in ks]))))
    rep['SD_D'] = {R: rep['gate1'][R]['sd'] for R in rep['gate1']}
    return rep


def decide(rep):
    g0 = rep['gate0']; flags = []
    if rep['gateF_fail']: flags.append('GateF-FAIL(FIXED-K <= 1.02 x JOINT): STOP growth line')
    if not rep['gate1_all']: flags.append('Gate1-FAIL')
    if g0 == 'FAIL': return 'STOP-selection', 'Gate 0 failed (ORACLE_xs and ORACLE_x-full < 10%): bottleneck is not selection. ' + '; '.join(flags)
    if g0 == 'PENDING_FULL': return 'PENDING-gate0-full', rep.get('gate0_detail', '')
    if g0.startswith('INCONCLUSIVE'): return g0.replace('INCONCLUSIVE-', 'INCONCLUSIVE-gate0-'), 'Gate 0 inconclusive; not released; needs a new contract. ' + '; '.join(flags)
    if not rep['gate1_all']: return 'STOP-Q1', 'Gate 0 passed, Gate 1 failed: JOINT compensation shows no (gate-level) advantage over cheap rules. ' + '; '.join(flags)
    if rep['gateF_fail']: return 'STOP-growth', 'Gate 1 passed but FIXED-K <= 1.02 x JOINT: growth control has no independent value on this benchmark.'
    inc = []
    if not rep['H_Oys_pos']: inc.append('INCONCLUSIVE-unexplained')
    if rep['v10_rate'] is None or rep['v10_rate'] < 0.90: inc.append('INCONCLUSIVE-numerics')
    if rep['typemix_flag'] or rep['typemix_unassessed']: inc.append('INCONCLUSIVE-type-mix')
    if inc: return inc[0], 'Gate 0, Gate 1, Gate F passed but flags: %s (not released; needs analysis/new contract)' % inc
    return 'GO', 'Gate 0, Gate 1, Gate F passed, H_Oys>0, V10>=90%, not type-mix. STILL requires an AS-4 contract + real Opus gate (strong baselines, equal-time); not a contribution claim.'


# ------------------------------------------------------------------ I/O
def _ld(path):
    return json.load(open(path))


def final_theta(d):
    return np.array(d['theta']) if 'theta' in d else np.array(d['traj'][-1])


def load_all(root, with_context=True):
    import as_core as C, as_gen as G
    root = root.rstrip('/\\'); orx = root + '-ORX'
    arms = {}
    for base in (root, orx):
        if os.path.isdir(base):
            for a in sorted(os.listdir(base)):
                d = os.path.join(base, a)
                if os.path.isdir(d): arms[a] = d
    clean = {i: G.clean_image(i) for i in IMGS}; M = {}; extra = {}
    ops = {}
    def op_of(sb):
        if sb not in ops: ops[sb] = C.Op(sb)
        return ops[sb]
    for a, d in arms.items():
        M[a] = {}
        for f in sorted(os.listdir(d)):
            if not f.endswith('.json') or f.endswith('.ckpt.json'): continue
            r = _ld(os.path.join(d, f))
            if 'placeholder_drain' in r: continue
            u = r['unit']; k = (u['img'], u['cond'], u['ns'])
            th = final_theta(r); M[a][k] = float(np.mean((C.render(th) - clean[u['img']]) ** 2))
            extra.setdefault(a, {})[k] = r
    # FIXED = lowest final TRAIN loss among the three preset inits (never looks at MSE)
    M['FIXED'] = {}; extra['FIXED_meta'] = {}
    for k in KEYS:
        cand = [(extra[a][k]['train_loss'], a) for a in ('FIXED_g3', 'FIXED_g2', 'FIXED_j25') if a in extra and k in extra[a]]
        if len(cand) == 3: tl, a = min(cand); M['FIXED'][k] = M[a][k]; extra['FIXED_meta'][k] = a
    aux = {}
    # V10 stability rate over JOINT-arm steps
    st = []
    for k, r in extra.get('JOINT', {}).items():
        for lg in r['logs']:
            v = lg.get('v10_stable')
            if v: st.append(all(v.values()))
    aux['v10_rate'] = float(np.mean(st)) if st else None; aux['v10_n'] = len(st)
    aux['oracle_topk'] = sorted({r.get('topk', 8) for a in ('ORACLE_ys', 'ORACLE_xs') for r in extra.get(a, {}).values()})
    return M, aux, extra, clean, op_of


def diagnostics(M, extra, clean, op_of, aux):
    """Pre-registered secondary reports (no decision weight): overfitting, deviation principle K, dose-response, K-c, INIT-N, V16 hash checks, step diagnostics, timing."""
    import as_core as C, as_gen as G
    out = {}
    # ---- overfitting: train loss & clean MSE at K_max per rule
    out['overfit'] = {}
    for a in ('RAND', 'OMP', 'BLOCK', 'JOINT', 'JOINT_FREE'):
        if a in extra and M.get(a):
            tl = [r['logs'][-1]['train_loss'] for r in extra[a].values()]; out['overfit'][a] = dict(gm_mse=math.exp(float(np.mean([math.log(v) for v in M[a].values()]))), mean_train_loss=float(np.mean(tl)), n=len(tl))
    # ---- deviation principle K (first traj index with ||y-Ax||^2 <= tau N^2 sn^2); MSE there; Gate-1 stats at that K for JOINT vs cheap
    Mdev = {}
    for a in ('OMP', 'BLOCK', 'JOINT'):
        Mdev[a] = {}
        for k, r in extra.get(a, {}).items():
            i, c, s = k; sb, sn = r['sb'], r['sn']; op = op_of(sb); y = G.noisy_obs(op, clean[i], sn, s, i); kd = len(r['traj']) - 1
            for j, th in enumerate(r['traj']):
                if float(np.sum((y - op.apply(C.render(np.array(th)))) ** 2)) <= TAU * C.N ** 2 * sn ** 2: kd = j; break
            Mdev[a][k] = float(np.mean((C.render(np.array(r['traj'][kd])) - clean[i]) ** 2)); r['_kdev'] = kd
    if all(Mdev.get(a) and len(Mdev[a]) == len(KEYS) for a in ('OMP', 'BLOCK', 'JOINT')):
        out['deviation_K'] = {R: {kk: v for kk, v in gate1_stats(Mdev['JOINT'], Mdev[R]).items() if kk != 'D'} for R in ('OMP', 'BLOCK')}
        out['deviation_K_mean_index'] = {a: float(np.mean([extra[a][k]['_kdev'] for k in KEYS])) for a in ('OMP', 'BLOCK', 'JOINT')}
    return out


def dose_response(M, cheap):
    out = {}
    for sb, c in ((0.3, 'D03'), (1.0, 'C2'), (2.0, 'C4')):
        ks = [(i, c, 9001) for i in IMGS]
        if all(k in M.get('JOINT', {}) for k in ks) and all(k in M.get(cheap, {}) for k in ks): out[sb] = H(M['JOINT'], M[cheap], ks)
    if len(out) == 3: out['monotone_H03<=H10<=H20'] = bool(out[0.3] <= out[1.0] <= out[2.0])
    return out


def tik_oracle_lambda_mse(op, y, x):
    """Evaluator-side context only: smallest clean-image MSE of Tikhonov deconvolution over the same log-lambda grid as GCV (uses the clean image; NOT a legal method)."""
    import as_core as C
    U, s, Vt = np.linalg.svd(op.B); Cc = U.T @ y @ U; sv = np.outer(s, s); best = None
    for lam in 10.0 ** np.arange(-10, 1.01, 0.25):
        X = Vt.T @ ((sv / (sv ** 2 + lam)) * Cc) @ Vt; m = float(np.mean((X - x) ** 2))
        if best is None or m < best: best = m
    return best


def kc_flag(M, clean, op_of, extra):
    """K-c (pre-registered, not a gate): flag if Tikhonov/Wiener with GCV lambda beats the best Gaussian arm by >1 dB in >=3 conditions.
    GCV under-regularises this strongly ill-posed operator (measured in S0), so the evaluator-side best-lambda Tikhonov MSE is reported alongside as a stronger context number (no effect on the flag)."""
    import as_core as C, as_gen as G
    res = {}; flags = 0; flags_or = 0
    for c in CONDS:
        ks = [k for k in KEYS if k[1] == c]; sb, sn = {'C1': (1.0, .01), 'C2': (1.0, .03), 'C3': (2.0, .01), 'C4': (2.0, .03)}[c]; op = op_of(sb); tik = []; tko = []
        for (i, cc, s) in ks:
            y = G.noisy_obs(op, clean[i], sn, s, i); X, lam = op.tikhonov_gcv(y); tik.append(float(np.mean((X - clean[i]) ** 2))); tko.append(tik_oracle_lambda_mse(op, y, clean[i]))
        gt = float(np.mean(np.log(tik))); go = float(np.mean(np.log(tko)))
        best = min(float(np.mean([math.log(M[a][k]) for k in ks])) for a in ('RAND', 'OMP', 'BLOCK', 'JOINT', 'JOINT_FREE', 'FIXED') if a in M and all(k in M[a] for k in ks))
        db = 10 * (best - gt) / math.log(10); dbo = 10 * (best - go) / math.log(10)      # dB by which Tikhonov is lower than the best Gaussian arm (positive: Tikhonov better)
        res[c] = dict(tik_gcv_gm_mse=math.exp(gt), tik_oracle_lambda_gm_mse=math.exp(go), best_gauss_gm_mse=math.exp(best), tik_gcv_better_dB=db, tik_oracle_lambda_better_dB=dbo); flags += int(db > 1.0); flags_or += int(dbo > 1.0)
    res['flag_gaussian_capacity_no_task_value'] = flags >= 3; res['flag_with_oracle_lambda_context_only'] = flags_or >= 3
    return res


def step_diag(extra):
    out = {}; r = extra.get('JOINT', {})
    if not r: return out
    ag = {k: [] for k in ('OMP', 'BLOCK', 'JOINT_FREE')}; rho = {}; stat = []; ptype = []; excl = dict(clamped=0, below_floor=0, capped=0); tt = dict(score=0.0, refit=0.0); pr = []
    for rr in r.values():
        for lg in rr['logs']:
            for k in ag: ag[k].append(lg['tops'][k] == lg['tops']['JOINT'])
            for kk, v in lg['rho'].items(): rho.setdefault(kk, []).append(v)
            stat.append(lg['stat']); ptype.append(lg['chosen_type'] == 's'); excl['clamped'] += lg['n_clamped_parent']; excl['below_floor'] += lg['n_below_floor']; excl['capped'] += int(lg['lm']['capped'])
            tt['score'] += lg['t_score']; tt['refit'] += lg['t_refit']
            if lg.get('pred_joint') is not None: pr.append((lg['pred_joint'], lg['real_half_sse']))
    out['top1_agree_with_JOINT'] = {k: float(np.mean(v)) for k, v in ag.items()}
    out['mean_spearman'] = {k: float(np.nanmean(v)) for k, v in rho.items()}
    out['stationarity_ratio_mean'] = float(np.mean(stat)); out['JOINT_split_share'] = float(np.mean(ptype)); out['exclusions_and_caps'] = excl; out['time_seconds_total'] = tt
    if len(pr) > 3:
        a = np.array(pr); ra = np.argsort(np.argsort(a[:, 0])); rb = np.argsort(np.argsort(a[:, 1])); out['pred_vs_real_chosen_spearman'] = float(np.corrcoef(ra, rb)[0, 1])
    d5 = []
    for rr in r.values():
        for lg in rr['logs']:
            if 'diag_top5_pred_real' in lg and len(lg['diag_top5_pred_real']) >= 3:
                p, q = zip(*lg['diag_top5_pred_real']); ra = np.argsort(np.argsort(p)); rb = np.argsort(np.argsort(q))
                if ra.std() > 0 and rb.std() > 0: d5.append(float(np.corrcoef(ra, rb)[0, 1]))
    if d5: out['top5_pred_vs_real_spearman_mean'] = float(np.mean(d5)); out['top5_n'] = len(d5)
    return out


def v16_check(extra):
    """V16: step-0 candidate hash identical across all arms of the same unit; V13: stationarity recorded; V15: cap counts."""
    bad = 0; n = 0
    by = {}
    for a, d in extra.items():
        if a == 'FIXED_meta' or a.startswith('FIXED') or a.startswith('INITN') or a.endswith('_b') or a.endswith('_s'): continue
        for k, r in d.items():
            if r.get('logs') and 'cand_hash' in r['logs'][0]: by.setdefault(k, set()).add(r['logs'][0]['cand_hash'])
    for k, hs in by.items():
        n += 1; bad += int(len(hs) != 1)
    return dict(units_checked=n, units_with_hash_mismatch=bad, ok=(bad == 0 and n > 0))


def initn_report(extra, M):
    out = {}
    ks = [(i, c, 9001) for i in IMGS for c in CONDS]
    if all(a in M and all(k in M[a] for k in ks) for a in ('INITN_OMP', 'INITN_BLOCK', 'INITN_JOINT')):
        for R in ('OMP', 'BLOCK'):
            out[R] = {kk: v for kk, v in gate1_stats(M['INITN_JOINT'], M['INITN_' + R]).items() if kk != 'D'}
    return out


def md_report(rep, diag):
    L = ['# AS contract v2.1 -- S2 analysis report (mechanical)', '', 'Decision: **%s**' % rep['decision'], '', rep.get('decision_detail', ''), '']
    if rep.get('missing'): L += ['Missing: %s' % rep['missing'], '']; return '\n'.join(L)
    L += ['cheap rule (fixed once): %s; H (vs cheap, 192 units): %s' % (rep['cheap'], {k: round(v, 4) for k, v in rep['H'].items()}), 'H_Oxs=%.4f  H_Oys(96)=%.4f  gate0=%s' % (rep['H_Oxs'], rep['H_Oys'], rep['gate0']), '']
    for R, g in rep['gate1'].items():
        L.append('Gate1 vs %s: meanD=%.4f (ratio %.4f) p=%.5f (count %d/%d) cond=%s fam=%s pass(i,ii,iii,iv)=%s,%s,%s,%s  SD(D)=%.4f SE=%.4f' % (R, g['meanD'], g['ratio'], g['p'], g['count'], g['total'], {c: round(v, 4) for c, v in g['cond_means'].items()}, {c: round(v, 4) for c, v in g['fam_means'].items()}, g['pass_i'], g['pass_ii'], g['pass_iii'], g['pass_iv'], g['sd'], g['se']))
    L += ['', 'GateF: FIXED/JOINT geometric-mean MSE ratio = %.4f (fail if <= 1.02): %s' % (rep['gateF_ratio_FIXED_over_JOINT'], rep['gateF_fail']), 'typemix: %s' % rep['typemix'], 'V10 stability rate: %s' % rep['v10_rate'], '']
    for k in ('JOINT_vs_JOINT_FREE', 'JOINT_vs_ORACLE_y_full'):
        if k in rep: L.append('%s: %s' % (k, rep[k]))
    L += ['', 'Diagnostics (no decision weight):', '```', json.dumps(diag, indent=1, default=str)[:6000], '```']
    return '\n'.join(L)


def main():
    kv = dict(a.split('=', 1) for a in sys.argv[1:] if '=' in a)
    root = kv['root']; outd = kv.get('out', root + '-report'); os.makedirs(outd, exist_ok=True)
    M, aux, extra, clean, op_of = load_all(root)
    rep = analyze(M, aux)
    diag = {}
    if rep['decision'] != 'INCOMPLETE':
        diag = diagnostics(M, extra, clean, op_of, aux); diag['dose_response'] = dose_response(M, rep['cheap']); diag['K_c'] = kc_flag(M, clean, op_of, extra)
        diag['step'] = step_diag(extra); diag['V16'] = v16_check(extra); diag['INIT_N'] = initn_report(extra, M)
        if not diag['V16']['ok']: rep['decision'] = 'INVALID-V16'; rep['decision_detail'] = 'V16 failed: candidate-set hash mismatch across arms (infrastructure failure, not a verdict). Underlying table decision was above.'
    rep['oracle_topk_values'] = aux.get('oracle_topk')
    if rep['decision'] != 'INCOMPLETE' and len(aux.get('oracle_topk') or []) > 1: rep['decision'] = 'INVALID-topk-mix'; rep['decision_detail'] = 'ORACLE_ys/xs units were run with different shortlist sizes (infrastructure failure, not a verdict)'
    rep['analyzer_sha256'] = hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest()
    json.dump(dict(report=rep, diagnostics=diag), open(os.path.join(outd, 'AS_S2_REPORT.json'), 'w'), indent=1, default=str)
    open(os.path.join(outd, 'AS_S2_REPORT.md'), 'w').write(md_report(rep, diag)); print(md_report(rep, diag)[:4000])


# ------------------------------------------------------------------ self-test (synthetic only)
def _synthetic(effect=0.0, noise=0.05, oracle_gain=0.2, fixed_pen=1.3, seed=0, v10=1.0, yoracle_gain=0.1):
    rng = np.random.default_rng(seed); M = {}; base = {k: math.exp(rng.normal(math.log(1e-3), 0.3) + 0.1 * (k[1] == 'C4')) for k in KEYS}
    def make(f, sd=noise, keys=KEYS): return {k: base[k] * f * math.exp(rng.normal(0, sd)) for k in keys}
    M['OMP'] = make(1.0); M['BLOCK'] = make(1.01); M['JOINT'] = make(1 - effect); M['RAND'] = make(1.2); M['JOINT_FREE'] = make(1 - effect)
    for t in ('b', 's'):
        M['OMP_' + t] = make(1.0); M['BLOCK_' + t] = make(1.0); M['JOINT_' + t] = make(1 - effect)
    M['FIXED'] = make((1 - effect) * fixed_pen); M['ORACLE_xs'] = make(1 - oracle_gain); M['ORACLE_ys'] = make(1 - yoracle_gain, keys=KEYS9001)
    return M, dict(v10_rate=v10)


def selftest():
    ok_all = True
    def chk(name, cond, det=''):
        nonlocal ok_all; ok_all &= bool(cond); print(('PASS ' if cond else 'FAIL ') + name, det, flush=True)
    # signflip exactness vs brute force (n=14) and meet-in-the-middle on odd n
    rng = np.random.default_rng(1)
    for n in (11, 14):
        D = rng.normal(-0.05, 0.1, n); p, cnt, tot = signflip_p(D)
        bits = (np.arange(2 ** n)[:, None] >> np.arange(n)[None, :]) & 1; sums = (1 - 2 * bits) @ D; bf = int(np.sum(sums <= D.sum() + 1e-10))
        chk('signflip exact n=%d' % n, cnt == bf and tot == 2 ** n, 'cnt=%d brute=%d p=%.5f' % (cnt, bf, p))
    p24, c24, t24 = signflip_p(np.full(24, -0.1)); chk('signflip n=24 all-equal negative: only the identity vector is <= observed (p = 2^-24)', c24 == 1 and t24 == 2 ** 24, '%d/%d' % (c24, t24))
    p24b, c24b, _ = signflip_p(np.zeros(24) + 1e-3 * np.sign(rng.normal(size=24))); chk('signflip n=24 runs and p in (0,1]', 0 < p24b <= 1, 'p=%.4f' % p24b)
    # decision table on synthetic data
    M, aux = _synthetic(effect=0.0); r = analyze(M, aux); chk('null effect -> not GO, STOP-Q1 (Gate 0 passes since oracle 20%)', r['decision'] == 'STOP-Q1', r['decision'] + ' meanD=%.4f' % r['gate1']['OMP']['meanD'])
    M, aux = _synthetic(effect=0.12); r = analyze(M, aux); chk('effect 12% + oracle 20% + FIXED worse + H_Oys>0 + V10 1.0 -> GO', r['decision'] == 'GO', r['decision'] + ' | p=%.2g' % r['gate1']['OMP']['p'])
    M, aux = _synthetic(effect=0.12, fixed_pen=1.0); r = analyze(M, aux); chk('Gate F: FIXED == JOINT -> STOP-growth', r['decision'] == 'STOP-growth', r['decision'])
    M, aux = _synthetic(effect=0.12, oracle_gain=0.03); r = analyze(M, aux); chk('Gate 0 shortfall without ORACLE_x-full -> PENDING (not decided)', r['decision'] == 'PENDING-gate0-full', r['decision'])
    M2 = dict(M); M2['ORACLE_x_full'] = {k: M['OMP'][k] * 0.97 for k in FULL12}; r = analyze(M2, aux); chk('Gate 0 shortfall with ORACLE_x-full <10% -> STOP-selection', r['decision'] == 'STOP-selection', r['decision'])
    M2['ORACLE_x_full'] = {k: M['OMP'][k] * 0.80 for k in FULL12}; r = analyze(M2, aux); chk('x-full >=10% but ORACLE_xs short -> INCONCLUSIVE-gate0-shortlist', r['decision'] == 'INCONCLUSIVE-gate0-shortlist', r['decision'])
    M, aux = _synthetic(effect=0.12, yoracle_gain=-0.05); r = analyze(M, aux); chk('H_Oys<=0 with gates passed -> INCONCLUSIVE-unexplained', r['decision'] == 'INCONCLUSIVE-unexplained', r['decision'])
    M, aux = _synthetic(effect=0.12, v10=0.8); r = analyze(M, aux); chk('V10 < 90% -> INCONCLUSIVE-numerics', r['decision'] == 'INCONCLUSIVE-numerics', r['decision'])
    M, aux = _synthetic(effect=0.12)
    for t in ('b', 's'): M['JOINT_' + t] = {k: M['OMP_' + t][k] for k in KEYS}; M['BLOCK_' + t] = {k: M['OMP_' + t][k] for k in KEYS}
    r = analyze(M, aux); chk('mixed-pool win but neither variant wins -> INCONCLUSIVE-type-mix', r['decision'] == 'INCONCLUSIVE-type-mix', r['decision'])
    M, aux = _synthetic(effect=0.12)
    for a in ('BLOCK_b', 'BLOCK_s'): M.pop(a, None)
    r = analyze(M, aux); chk('cut (4): BLOCK_b/BLOCK_s absent -> not INCOMPLETE; JOINT wins on births so type-mix assessed false (BLOCK_b := OMP_b)', r['decision'] == 'GO' and not r['typemix_unassessed'], r['decision'] + ' ' + str({k: (v['b'], v['s']) for k, v in r['typemix'].items()}))
    M, aux = _synthetic(effect=0.12)
    for a in ('BLOCK_b', 'BLOCK_s'): M.pop(a, None)
    M['JOINT_b'] = {k: M['OMP_b'][k] for k in KEYS}; M['JOINT_s'] = {k: M['OMP_s'][k] for k in KEYS}
    r = analyze(M, aux); chk('cut (4): no variant win and BLOCK_s missing -> INCONCLUSIVE-type-mix (OMP typemix true / BLOCK unassessed)', r['decision'] == 'INCONCLUSIVE-type-mix', r['decision'] + ' ' + str(r['typemix']))
    M, aux = _synthetic(effect=0.12); M['JOINT'] = {k: v for k, v in M['JOINT'].items() if k[0] != 3}; r = analyze(M, aux); chk('missing required units -> INCOMPLETE, no decision', r['decision'] == 'INCOMPLETE', str(r['missing']))
    # harm in one condition blocks Gate 1 (iii); one family-condition worse, etc.
    M, aux = _synthetic(effect=0.12)
    for k in KEYS:
        if k[1] == 'C4': M['JOINT'][k] = M['OMP'][k] * 1.10
    r = analyze(M, aux); chk('harm >2% in condition C4 -> Gate 1 (iii) fails', not r['gate1']['OMP']['pass_iii'] and r['decision'] == 'STOP-Q1', str(r['gate1']['OMP']['cond_means']))
    # cheap-rule choice is fixed by global geometric mean (BLOCK better here)
    M, aux = _synthetic(effect=0.0); M['BLOCK'] = {k: v * 0.9 for k, v in M['OMP'].items()}; r = analyze(M, aux); chk('cheap = the better global geometric-mean rule', r['cheap'] == 'BLOCK', r['cheap'])
    # Tikhonov correctness (K-c ingredient): noiseless observation is inverted accurately (GCV picks the smallest lambda). NOTE: with noise GCV can be WORSE than the blurred observation (measured; known GCV under-regularisation here), so no such claim is tested.
    import as_core as C, as_gen as G
    op = C.Op(1.0); x = G.clean_image(1); y0 = op.apply(x); m0 = tik_oracle_lambda_mse(op, y0, x); X0, lam0 = op.tikhonov_gcv(y0)
    chk('Tikhonov SVD-basis inverse is correct: noiseless y, best lambda on the grid recovers x (< 1e-8)', m0 < 1e-8, 'best-grid mse=%.2e (GCV on noiseless data picks lam=%.1e, mse=%.2e)' % (m0, lam0, np.mean((X0 - x) ** 2)))
    y1 = G.noisy_obs(op, x, 0.01, 9001, 1); mo = tik_oracle_lambda_mse(op, y1, x); X1, _l = op.tikhonov_gcv(y1)
    chk('oracle-lambda Tikhonov MSE <= GCV-lambda Tikhonov MSE (grid contains the GCV lambda)', mo <= float(np.mean((X1 - x) ** 2)) + 1e-15, 'oracle=%.2e gcv=%.2e' % (mo, np.mean((X1 - x) ** 2)))
    print('SELFTEST', 'OK' if ok_all else 'FAILED'); sys.exit(0 if ok_all else 1)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'selftest': selftest()
    else: main()
