"""JR reducer (evaluator side). Contract JR v1 (candidate v1) sections 5, 7-9.
  python3 experiments/jr_reduce.py tune T1|T2|T3  -> outputs/JR/tune/selection_prelim.json (T3 also writes selection.json = final single configuration per arm)
  python3 experiments/jr_reduce.py ridge          -> descriptive ridge sensitivity (never used for selection)
  python3 experiments/jr_reduce.py verify [verify|verify2|dry] -> outputs/JR/<stage>_REDUCE.json + .txt (metrics, BCa gates, decision CONTINUE/STOP)
Q-AUC = mean over GRID of PSNR(theta at the last completed sweep with W<=B; theta0 if none); O-AUC = mean over GRID of log10 max((F-Fref)/(F0-Fref),1e-4), Fref per problem = min visit-level F over ALL arms of the verify run."""
import os, sys, json, glob
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'src')); sys.path.insert(0, os.path.join(ROOT, 'experiments'))
from trn_same_state_reduce import bca
GRID = np.geomspace(1e9, 3e10, 8); CAP = 3.0e10
GROUP_ARMS = ['OBS-J', 'SPA-J', 'OBS-I', 'OBS0-J', 'RND-J', 'OVL-J']; CONTROLS = ['SPA-J', 'OBS-I', 'OBS0-J', 'RND-J', 'OVL-J', 'IND1']; ALL = ['OBS-J'] + CONTROLS + ['FULL']
DELTA = {'SPA-J': 0.15, 'OBS-I': 0.15, 'RND-J': 0.15, 'IND1': 0.15, 'OBS0-J': 0.10, 'OVL-J': 0.10}; GUARD_DB = -0.10; O_NI = 0.05; SIGN_MIN = 8; PSFS = ['G15', 'AG', 'MO', 'DK']
TIE_DB = 0.02; BOOT = 10000; SEED = 20261108


def load(dirn):
    return [json.load(open(f)) for f in sorted(glob.glob(os.path.join(dirn, '*__*.json')))]


def idx_at(W, B):
    i = int(np.searchsorted(np.asarray(W), B, side='right')) - 1; return max(i, 0)


def q_auc(r, free=False):
    W = np.asarray(r['trajW'], float)
    if free: W = W - np.asarray(r['trajGrp'], float)
    return float(np.mean([r['psnr'][idx_at(W, B)] for B in GRID]))


def o_auc(r, F0, Fref, free=False):
    W = np.asarray(r['trajW'], float)
    if free: W = W - np.asarray(r['trajGrp'], float)
    F = r['trajF']; return float(np.mean([np.log10(max((F[idx_at(W, B)] - Fref) / (F0 - Fref), 1e-4)) for B in GRID]))


def cost_to(r, F0, Fref, rho):
    tgt = Fref + rho * (F0 - Fref)
    for W, F in zip(r['vW'], r['vF']):
        if F <= tgt: return W
    return CAP


def bca_one_sided(d):
    """mean, BCa 5% lower bound, BCa 95% upper bound (images resampled, 10000, seed 20261108)."""
    d = np.asarray(d, float); lo, hi = bca(d, stat=np.mean, B=BOOT, seed=SEED, alpha=0.10); return float(d.mean()), float(lo), float(hi)


def key(r): return (r['armname'], r['gs'], r['kappa0'], r.get('R', 1), r.get('ridge', 1.0))


def tune(phase):
    out = os.path.join(ROOT, 'outputs', 'JR', 'tune'); runs = [r for r in load(out) if r.get('ridge', 1.0) == 1.0]; rows = {}
    for r in runs: rows.setdefault(key(r), []).append(r)
    summ = {k: dict(n=len(v), Q=float(np.mean([q_auc(r) for r in v])), W=float(np.mean([r['W'] for r in v])), wall=float(np.mean([r['wall'] for r in v])), cfgid=v[0]['cfgid']) for k, v in rows.items()}
    def best(cands):      # cands: list of (key, summary); max Q, ties (|dQ|<=TIE_DB) -> lower mean W, then smaller gs, R, kappa0
        qmax = max(s['Q'] for _, s in cands); ok = [(k, s) for k, s in cands if s['Q'] >= qmax - TIE_DB]; return min(ok, key=lambda ks: (ks[1]['W'], ks[0][1], ks[0][3], ks[0][2]))
    def need(a, pred, n_expected):
        c = [(k, s) for k, s in summ.items() if k[0] == a and pred(k)]; assert len(c) == n_expected and all(s['n'] == 24 for _, s in c), '%s: expected %d complete configs, have %s' % (a, n_expected, [(k, s['n']) for k, s in c]); return c
    pp = os.path.join(out, 'selection_prelim.json'); sel = json.load(open(pp)) if os.path.exists(pp) else {}
    lines = ['%-7s %-22s n=%d Q-AUC %.3f dB  meanW %.3g  wall %.1fs' % (k[0], s['cfgid'], s['n'], s['Q'], s['W'], s['wall']) for k, s in sorted(summ.items(), key=lambda kv: (ALL.index(kv[0][0]), kv[0][1], kv[0][3], kv[0][2]))]
    if phase == 'T1':
        sel['T1'] = {}
        for a in GROUP_ARMS:
            k, s = best(need(a, lambda k: k[2] == 0.1 and k[3] == 1, 3)); sel['T1'][a] = dict(gs=k[1], Q=s['Q'], cfgid=s['cfgid'])
        k, s = best(need('IND1', lambda k: True, 5)); sel['T1']['IND1'] = dict(gs=1, kappa0=k[2], Q=s['Q'], cfgid=s['cfgid'])
    elif phase == 'T2':
        sel['T2'] = {}
        for a in GROUP_ARMS:
            g = sel['T1'][a]['gs']; k, s = best(need(a, lambda k: k[1] == g and k[2] == 0.1, 2)); sel['T2'][a] = dict(gs=g, R=k[3], Q=s['Q'], cfgid=s['cfgid'])
    elif phase == 'T3':
        sel['final'] = {}
        for a in GROUP_ARMS:
            g, R = sel['T2'][a]['gs'], sel['T2'][a]['R']; k, s = best(need(a, lambda k: k[1] == g and k[3] == R, 3)); sel['final'][a] = dict(gs=g, R=R, kappa0=k[2], Q=s['Q'], cfgid=s['cfgid'], edge=bool(g in (2, 9) or k[2] in (0.03, 0.3) or R == 4))
        t1 = sel['T1']['IND1']; sel['final']['IND1'] = dict(gs=1, R=1, kappa0=t1['kappa0'], Q=t1['Q'], cfgid=t1['cfgid'], edge=bool(t1['kappa0'] in (0.01, 1.0)))
        sel['tune_cpu_h'] = float(sum(r['wall'] for r in runs) / 3600.0)
        json.dump(sel, open(os.path.join(out, 'selection.json'), 'w'), indent=1)
    else: raise SystemExit('phase T1|T2|T3')
    json.dump(sel, open(pp, 'w'), indent=1); print('\n'.join(lines)); print(json.dumps({k: v for k, v in sel.items()}, indent=1))


def ridge():
    out = os.path.join(ROOT, 'outputs', 'JR', 'tune'); runs = load(out); sel = json.load(open(os.path.join(out, 'selection.json')))['final']['OBS-J']
    for rg in (0.1, 1.0, 10.0):
        v = [r for r in runs if r['armname'] == 'OBS-J' and r['gs'] == sel['gs'] and r['kappa0'] == sel['kappa0'] and r.get('R', 1) == sel['R'] and r.get('ridge', 1.0) == rg]
        print('OBS-J ridge %.1f n=%d Q-AUC %.3f dB (descriptive only)' % (rg, len(v), float(np.mean([q_auc(r) for r in v])) if v else float('nan')))


def verify(stage):
    out = os.path.join(ROOT, 'outputs', 'JR', stage); runs = load(out); P = {}
    for r in runs: P.setdefault((r['img'], r['cond']), {})[r['armname']] = r
    probs = sorted(P); assert probs, 'no runs'; missing = [(p, a) for p in probs for a in ALL if a not in P[p]]; assert not missing, 'incomplete: %s' % missing[:5]
    M = {a: {} for a in ALL}
    for p in probs:
        F0 = P[p]['OBS-J']['F0']; Fref = min(min(r['vF']) for r in P[p].values())
        for a in ALL:
            r = P[p][a]; ps = np.asarray(r['psnr']); pk = int(np.argmax(ps)); M[a][p] = dict(Q=q_auc(r), O=o_auc(r, F0, Fref), Qfree=q_auc(r, True), Qend=r['psnr'][-1], Fend=r['F'], c10=cost_to(r, F0, Fref, 0.1), c03=cost_to(r, F0, Fref, 0.03), W=r['W'], wall=r['wall'], stop=r['stop'],
                                      rej=r['rej'] / max(r['trials'], 1), grp_share=r['cat']['grp'] / max(r['W'], 1.0), comp=r['comp_median'], peakQ=float(ps.max()), peakW=float(r['trajW'][pk]))
    imgs = sorted({p[0] for p in probs}); res = dict(stage=stage, n_images=len(imgs), n_problems=len(probs), arms={}, gates={}, notes=[])
    def iv(a, key_, tab=None): return np.array([np.mean([M[a][(i, c)][key_] for c in PSFS]) for i in imgs])
    for a in ALL:
        res['arms'][a] = {k: float(np.mean([M[a][p][k] for p in probs])) for k in ('Q', 'O', 'Qend', 'Fend', 'c10', 'c03', 'W', 'wall', 'rej', 'grp_share', 'peakQ', 'peakW')}
        res['arms'][a]['censored_c03'] = int(sum(M[a][p]['c03'] >= CAP for p in probs)); res['arms'][a]['stops'] = {s: int(sum(M[a][p]['stop'] == s for p in probs)) for s in sorted({M[a][p]['stop'] for p in probs})}
    for x in CONTROLS:
        dq = iv('OBS-J', 'Q') - iv(x, 'Q'); do = iv('OBS-J', 'O') - iv(x, 'O'); mq, lq, uq = bca_one_sided(dq); mo, lo_, uo = bca_one_sided(do); wins = int((dq > 0).sum())
        c1 = bool(mq >= DELTA[x] and lq > 0 and wins >= SIGN_MIN); c2 = bool(uo <= O_NI)
        res['gates'][x] = dict(mean_dQ=mq, LB5=lq, UB95=uq, delta=DELTA[x], wins=wins, n=len(dq), mean_dO=mo, UB95_dO=uo, quality_ok=c1, O_noninferior=c2, PASS=bool(c1 and c2), label=('PASS' if (c1 and c2) else ('regularisation effect, not mechanism increment' if c1 else 'FAIL')))
    strongest = max(CONTROLS, key=lambda x: float(np.mean(iv(x, 'Q')))); res['strongest_control'] = strongest; guard = {}
    for c in PSFS: guard[c] = float(np.mean([M['OBS-J'][(i, c)]['Q'] - M[strongest][(i, c)]['Q'] for i in imgs]))
    res['per_psf_dQ_vs_strongest'] = guard; res['guard_PASS'] = bool(all(v >= GUARD_DB for v in guard.values()))
    res['decision'] = 'CONTINUE' if (all(res['gates'][x]['PASS'] for x in CONTROLS) and res['guard_PASS']) else 'STOP'
    # descriptive: free-grouping reading (grouping cost removed from W for the OBS-grouped arms); not used in the decision
    fr = {}
    for x in ('OBS-I', 'IND1'):
        qa = np.array([np.mean([M['OBS-J'][(i, c)]['Qfree'] for c in PSFS]) for i in imgs]); qb = np.array([np.mean([M[x][(i, c)]['Qfree' if x == 'OBS-I' else 'Q'] for c in PSFS]) for i in imgs]); fr[x] = float((qa - qb).mean())
    res['descriptive_free_grouping_mean_dQ'] = fr
    if stage == 'dry': res['decision'] = 'DRY-RUN (pipeline test only; %s is NOT evidence)' % res['decision']
    res['diag'] = dict(comp_median={a: float(np.nanmean([M[a][p]['comp'] if M[a][p]['comp'] is not None else np.nan for p in probs])) for a in ALL}, counts0={c: P[(imgs[0], c)]['OBS-J']['counts0'] for c in PSFS})
    from math import comb
    import collections
    def ari(a, b):
        ca, cb, cab = collections.Counter(a), collections.Counter(b), collections.Counter(zip(a, b)); t = comb(len(a), 2); s_ = sum(comb(v, 2) for v in cab.values()); sa = sum(comb(v, 2) for v in ca.values()); sb = sum(comb(v, 2) for v in cb.values())
        e = sa * sb / t; mx = (sa + sb) / 2; return 1.0 if mx == e else (s_ - e) / (mx - e)
    def lab(gr, K=36):
        l = [0] * K
        for gi, g in enumerate(gr):
            for k in g: l[k] = gi
        return l
    a_sp = []; a_ps = []; a_ad = []; a_ov = []
    for p in probs:
        o = P[p]['OBS-J']['groups_first12']; s_ = P[p]['SPA-J']['groups_first12']; v = P[p]['OVL-J']['groups_first12']
        if o and s_ and v: a_sp.append(ari(lab(o[0]), lab(s_[0]))); a_ov.append(ari(lab(o[0]), lab(v[0]))); a_ad += [ari(lab(o[i]), lab(o[i + 1])) for i in range(len(o) - 1)]
    for i in imgs:
        g_ = {c: lab(P[(i, c)]['OBS-J']['groups_first12'][0]) for c in PSFS}; a_ps += [ari(g_[c1], g_[c2]) for ii, c1 in enumerate(PSFS) for c2 in PSFS[ii + 1:]]
    res['diag']['ARI'] = dict(OBS_vs_SPA_sweep1=float(np.mean(a_sp)), OBS_vs_OVL_sweep1=float(np.mean(a_ov)), OBS_across_PSF_sweep1=float(np.mean(a_ps)), OBS_adjacent_sweeps=float(np.mean(a_ad)))
    json.dump(res, open(os.path.join(ROOT, 'outputs', 'JR', '%s_REDUCE.json' % stage), 'w'), indent=1)
    L = ['JR %s reduce: %d images x %d problems' % (stage, len(imgs), len(probs)), 'DECISION: %s' % res['decision'], 'strongest control (Q-AUC): %s ; per-PSF mean dQ(OBS-J - strongest): %s ; guard %s' % (strongest, {k: round(v, 3) for k, v in guard.items()}, res['guard_PASS']), '']
    L.append('%-7s %8s %8s %8s %8s %10s %10s %10s %9s %6s %6s %s' % ('arm', 'Q-AUC', 'O-AUC', 'Qend', 'peakQ', 'c(rho=.1)', 'c(rho=.03)', 'meanW', 'wall[s]', 'rej', 'grp%', 'stops / censored(.03)'))
    for a in ALL:
        s = res['arms'][a]; L.append('%-7s %8.3f %8.3f %8.3f %8.3f %10.3g %10.3g %10.3g %9.1f %6.2f %6.2f %s / %d' % (a, s['Q'], s['O'], s['Qend'], s['peakQ'], s['c10'], s['c03'], s['W'], s['wall'], s['rej'], s['grp_share'], s['stops'], s['censored_c03']))
    L.append(''); L.append('gates (image-level, n=%d, BCa %d resamples; dQ = Q-AUC(OBS-J) - Q-AUC(X) [dB]; dO = O-AUC(OBS-J) - O-AUC(X) [log10, lower=OBS better]):' % (len(imgs), BOOT))
    for x in CONTROLS:
        g = res['gates'][x]; L.append('  vs %-7s dQ %+.3f  LB5 %+.3f  (delta %.2f, wins %d/%d) | dO %+.3f  UB95 %+.3f (<= %.2f) | %s' % (x, g['mean_dQ'], g['LB5'], g['delta'], g['wins'], g['n'], g['mean_dO'], g['UB95_dO'], O_NI, g['label']))
    L.append('descriptive free-grouping mean dQ: ' + json.dumps({k: round(v, 3) for k, v in fr.items()})); L.append('diag: ' + json.dumps(res['diag']))
    open(os.path.join(ROOT, 'outputs', 'JR', '%s_REDUCE.txt' % stage), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L))


if __name__ == '__main__':
    if sys.argv[1] == 'tune': tune(sys.argv[2])
    elif sys.argv[1] == 'ridge': ridge()
    else: verify(sys.argv[2] if len(sys.argv) > 2 else 'verify')
