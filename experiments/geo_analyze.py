"""GEO evaluator side (reads clean images for quality metrics; never imported by method-side code).
Commands (python geo_analyze.py <cmd>): select_geo, caps, select_arms, vpass, select_lam, report_d (D phase); h_q1, h_q2, h_timing (H phase; see below).
Writes/updates outputs/GEO-D/choices.json (the frozen selection table) and prints a text report. All selections use ONLY dev data (images 101-112, base 9101)."""
import os, sys, json, glob, math
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'src')); sys.path.insert(0, HERE)
import numpy as np
import geo_core as GC
import geo_gen as GG
import geo_run as R

OUT = R.OUT; N = 32; S_FLOOR = 1e-6
STOPS = ('max_iter', 'converged', 'cap', 'no_step', 'no_step_clamp', 'safety', 'discrepancy')
AMEND_TAG = '[amended-V; GEO = rcond-tuned, not the frozen Sec.1 step]'
V_CELLS = 96; V_CELLS_K = 48; MIN_IMG_A = 12; MIN_IMG_T = 6          # frozen thresholds (dry-run harness may lower them; the formal run never does)


def load(path):
    z = np.load(path, allow_pickle=False); m = json.loads(str(z['meta']))
    return m, {k: z[k] for k in z.files if k != 'meta'}


def runs_in(*subdirs):
    out = []
    for sd in subdirs:
        for f in sorted(glob.glob(os.path.join(OUT, sd, '*.npz'))):
            if f.endswith('.tmp.npz'): continue
            m, a = load(f); m['_file'] = f; out.append((m, a))
    return out


def cell_key(m):
    lam = m['lam']; return (m['img'], m['cond'], m['K'], m['base'], R.lam_tag(lam))


def fref_table(runs):
    t = {}
    for m, _ in runs:
        k = cell_key(m); t[k] = min(t.get(k, np.inf), m['F'])
    return t


def s_of(m, Fref):
    return (m['F'] - Fref) / max(m['F0'] - Fref, 1e-300)


def gmean(v):
    v = np.maximum(np.asarray(v, float), S_FLOOR); return float(np.exp(np.mean(np.log(v))))


def choices_path():
    return os.path.join(OUT, 'GEO-D', 'choices.json')


def load_ch():
    p = choices_path(); return json.load(open(p)) if os.path.exists(p) else {}


def save_ch(ch):
    os.makedirs(os.path.dirname(choices_path()), exist_ok=True); json.dump(ch, open(choices_path(), 'w'), indent=1, sort_keys=True)


def tune_table(runs, tune_cells, Fref, group):
    """group(m)->config key. Returns {cfgkey: gmean s over tune cells} (only cfgs with all cells present)."""
    per = {}
    for m, _ in runs:
        if (m['img'], m['cond'], m['K'], m['base']) not in tune_cells: continue
        per.setdefault(group(m), {})[(m['img'], m['cond'], m['K'])] = s_of(m, Fref[cell_key(m)])
    return {k: (gmean(list(v.values())), len(v)) for k, v in per.items()}


def cfg_key(m):
    c = m['cfg']; return (c.get('rcond'), c['f'], c['kappa0'])


def cmd_select_geo():
    runs = runs_in('GEO-D/tune_geo', 'GEO-D/fref'); Fref = fref_table(runs)
    tune = {(i, c, K, b) for (i, c, K, b) in R.cell_list('tune')}
    tab = tune_table([r for r in runs if r[0]['arm'] == 'GEO'], tune, Fref, cfg_key)
    full = {k: v for k, v in tab.items() if v[1] == len(tune)}
    assert len(full) == len(R.GEO_GRID), 'tune_geo incomplete: %s' % {k: v[1] for k, v in tab.items()}
    for k in sorted(full, key=lambda z: (z[0], z[1])): print('GEO rcond=%s f=%s: gmean s = %.4g' % (k[0], k[1], full[k][0]))
    best = min(full, key=lambda z: (full[z][0], -z[0]))        # ties: larger rcond is NOT preferred; first minimal
    r8 = {k: v for k, v in full.items() if k[0] == 1e-8}; best_r8 = min(r8, key=lambda z: r8[z][0])
    ch = load_ch(); ch['GEO'] = dict(kappa0=1e-3, f=best[1], rcond=best[0]); ch['GEO_r8'] = dict(f=best_r8[1])
    ch['GEO_table'] = {'r%.0e_f%d' % (k[0], k[1]): v[0] for k, v in full.items()}; ch['GEO_fref_basis'] = 'tune_geo+fref(tune,lam1e-3)'
    save_ch(ch); print('selected GEO:', ch['GEO'], ' GEO-r8 f:', ch['GEO_r8'])


def cmd_caps():
    ch = load_ch(); runs = runs_in('GEO-D/calib'); caps = {}
    for K in R.KS:
        A = [m['cnt']['A'] for m, _ in runs if m['K'] == K]; W = [m['cnt']['W'] for m, _ in runs if m['K'] == K]
        assert len(A) == len([1 for (i, c, KK, b) in R.cell_list('dev') if KK == K]), 'calib incomplete for K=%d (%d)' % (K, len(A))
        caps[str(K)] = dict(A=5 * float(np.median(A)), W=5 * float(np.median(W)), A_med=float(np.median(A)), W_med=float(np.median(W)), n=len(A),
                            stops={s: sum(1 for m, _ in runs if m['K'] == K and m['stop'] == s) for s in STOPS})
        print('K=%d: median A=%.0f W=%.3e -> caps A=%.0f W=%.3e  stops=%s' % (K, caps[str(K)]['A_med'], caps[str(K)]['W_med'], caps[str(K)]['A'], caps[str(K)]['W'], caps[str(K)]['stops']))
    ch['caps'] = caps; save_ch(ch)


def cmd_select_arms():
    ch = load_ch(); runs = runs_in('GEO-D/tune_geo', 'GEO-D/tune_arms', 'GEO-D/fref'); Fref = fref_table(runs)
    tune = {(i, c, K, b) for (i, c, K, b) in R.cell_list('tune')}
    for arm in ('BJ', 'BLK', 'LMD', 'LSMR', 'PCG8P', 'PCG8D'):
        rr = [r for r in runs if r[0]['arm'] == arm]
        tab = tune_table(rr, tune, Fref, cfg_key); full = {k: v for k, v in tab.items() if v[1] == len(tune)}
        grid = R.GEO_GRID if arm in R.GEO_FAMILY else R.LM_GRID
        assert len(full) == len(grid), '%s tune incomplete: %s' % (arm, {k: v[1] for k, v in tab.items()})
        best = min(full, key=lambda z: full[z][0])
        ch[arm] = dict(kappa0=best[2], f=best[1]);
        if arm in R.GEO_FAMILY: ch[arm]['rcond'] = best[0]
        ch[arm + '_table'] = {('r%.0e_f%d' % (k[0], k[1]) if k[0] is not None else 'k%.0e_f%d' % (k[2], k[1])): v[0] for k, v in full.items()}
        print(arm, 'selected', ch[arm], ' table', {k: round(v, 4) for k, v in ch[arm + '_table'].items()})
    ch['arms_fref_basis'] = 'tune_geo+tune_arms+fref(tune,lam1e-3)'; save_ch(ch)


def reject_rate(m):
    return m['rej'] / max(m['trials'], 1)                    # K1 C14 definition: rejected trials / all trials (Opus Q-i must-fix 1)


def _vstats(rr, Fref):
    s = [s_of(m, Fref[cell_key(m)]) for m, _ in rr]
    return dict(n=len(s), frac_s_le_0p1=float(np.mean(np.array(s) <= 0.1)) if s else None, gmean_s=gmean(s) if s else None, stops={st: sum(1 for m, _ in rr if m['stop'] == st) for st in STOPS},
                rej_per_iter=float(np.mean([reject_rate(m) for m, _ in rr])) if rr else None, clamp_rate=float(np.mean([m['clamp_rate'] for m, _ in rr])) if rr else None,
                act_mean=float(np.mean([m['act_mean'] for m, _ in rr])) if rr else None, no_step_clamp_rate=float(np.mean([m['stop'] == 'no_step_clamp' for m, _ in rr])) if rr else None)


def cmd_vpass():
    """Dual V-pass (K1 item 8): (i) frozen spec: GEO-r8 and LMD; (ii) amended: rcond-tuned GEO and LMD; (ii) gates phase H. Budgeted caps, lambda=1e-3, 96 dev cells."""
    runs = runs_in('GEO-D/vpass', 'GEO-D/fref', 'GEO-D/calib'); Fref = fref_table(runs); res = {}
    for arm in ('GEO', 'LMD', 'GEO-r8'):
        rr = [r for r in runs if r[0]['arm'] == arm and r[0]['lam'] == R.LAM_TUNE and 'caps' in r[0] and r[0]['caps']]
        res[arm] = _vstats(rr, Fref); print(arm, res[arm])
    g, l, r8 = res['GEO'], res['LMD'], res['GEO-r8']
    ok = lambda d: bool(d['n'] == V_CELLS and d['frac_s_le_0p1'] >= 0.95)
    res['V_pass_frozen_spec'] = dict(GEO_r8=ok(r8), LMD=ok(l), passed=bool(ok(r8) and ok(l)))
    res['V_pass_amended'] = dict(GEO_tuned=ok(g), LMD=ok(l), passed=bool(ok(g) and ok(l)), label=AMEND_TAG)
    # C14 failure-mode trigger on TUNED GEO (GEO-r8 informational): rejection rate, clamp rate, mean |I|, no_step_clamp rate >= 3x LMD
    res['C14_flag_tuned_GEO'] = bool(g['rej_per_iter'] >= 3 * l['rej_per_iter'] or g['clamp_rate'] >= 3 * l['clamp_rate'] or g['act_mean'] >= 3 * max(l['act_mean'], 1e-9)
                                     or g['no_step_clamp_rate'] >= 3 * max(l['no_step_clamp_rate'], 1e-9) and g['no_step_clamp_rate'] > 0)
    res['C14_info_GEO_r8'] = dict(rej_per_iter=r8['rej_per_iter'], clamp_rate=r8['clamp_rate'], act_mean=r8['act_mean'], no_step_clamp_rate=r8['no_step_clamp_rate'])
    res['STOP_GEO_V_frozen_spec_text'] = None if res['V_pass_frozen_spec']['passed'] else ('STOP-GEO-V under the frozen spec (rcond=1e-8): Euclidean minimum-norm back-substitution amplifies weak directions '
                                                                                      '(not erased by the amended V-pass; amended results carry ' + AMEND_TAG + ')')
    print('V_pass frozen spec:', res['V_pass_frozen_spec'], '| amended:', res['V_pass_amended'], '| C14 flag (tuned GEO):', res['C14_flag_tuned_GEO'])
    if res['STOP_GEO_V_frozen_spec_text']: print('>>> LOG AS FAILURE:', res['STOP_GEO_V_frozen_spec_text'])
    json.dump(res, open(os.path.join(OUT, 'GEO-D', 'V_PASS_DEV.json'), 'w'), indent=1)


def cmd_vpass_lam():
    """Amended-V re-check at lambda* (Opus addition (1)), per K layer: GEO (lamgrid run at lambda*) and LMD (vpass_lam) at >=95% of that layer's 48 dev cells with s<=0.1 relative to F_ref(lambda*)
    (min over all same-(cell, lambda*) runs incl. 3 LMD-500 restarts). A failing K layer makes Q2 in that layer INCONCLUSIVE (= JOINT-NOT-MATTERS for ADVANCE) and tags Q1 there."""
    ch = load_ch(); runs = runs_in('GEO-D/lamgrid', 'GEO-D/vpass_lam', 'GEO-D/fref'); Fref = fref_table(runs); res = {}
    for K in R.KS:
        res[str(K)] = {}; okall = True
        for arm in ('GEO', 'LMD'):
            rr = [(m, a) for m, a in runs if m['arm'] == arm and m['K'] == K and m['base'] == 9101 and abs(m['lam'] - ch['lam_star']['%s_K%d' % (m['cond'], K)]) <= 1e-15 * max(m['lam'], 1.0)]
            st = _vstats(rr, Fref); st['pass'] = bool(st['n'] == V_CELLS_K and st['frac_s_le_0p1'] >= 0.95); res[str(K)][arm] = st; okall &= st['pass']
        res[str(K)]['pass'] = bool(okall); print('K=%d at lambda*:' % K, json.dumps(res[str(K)], default=str)[:1500])
    json.dump(res, open(os.path.join(OUT, 'GEO-D', 'V_PASS_LAMSTAR.json'), 'w'), indent=1)
    return res


def clean(i):
    return GG.clean_image_geo(i)


def mse(theta, img):
    return float(np.mean((GC.render(theta, N) - clean(img)) ** 2))


def cmd_select_lam():
    ch = load_ch(); runs = runs_in('GEO-D/lamgrid'); lam_star = {}; tau_star = {}; table = {}
    for c in R.CONDS:
        for K in R.KS:
            key = '%s_K%d' % (c, K); best = None; tb = {}
            for lam in R.LAM_GRID:
                rr = [(m, a) for m, a in runs if m['cond'] == c and m['K'] == K and m['lam'] == lam]
                assert len(rr) == len(GG.DEV_IMGS), 'lamgrid incomplete %s lam=%g (%d)' % (key, lam, len(rr))
                g = gmean([mse(a['theta'], m['img']) for m, a in rr]); tb[R.lam_tag(lam)] = g
                if best is None or g < best[0]: best = (g, lam)
            lam_star[key] = best[1]; table[key] = tb
            rr = [(m, a) for m, a in runs if m['cond'] == c and m['K'] == K and m['lam'] == 0.0]
            tbt = {}
            for j, tau in enumerate(R.TAU_GRID):
                tbt[str(tau)] = gmean([mse(a['tau_theta'][j], m['img']) for m, a in rr])
            tau_star[key] = float(min(R.TAU_GRID, key=lambda t: tbt[str(t)]))
            trig = float(np.mean([a['tau_idx'][list(R.TAU_GRID).index(tau_star[key])] >= 0 for m, a in rr]))
            table[key + '_tau'] = dict(mse=tbt, trigger_rate_at_tau_star=trig)
            print(key, 'lam* =', lam_star[key], ' tau* =', tau_star[key], ' trigger rate at tau* (dev):', round(trig, 2))
    ch['lam_star'] = lam_star; ch['tau_star'] = tau_star; ch['lam_tau_tables'] = table; save_ch(ch)



# ================================================================== H phase (held-out): metrics are fixed here BEFORE any H result is visible
from scipy import stats as _st


def t_interval(v, level=0.95):
    v = np.asarray(v, float); n = len(v); mu = float(v.mean()); se = float(v.std(ddof=1) / np.sqrt(n)); tq = float(_st.t.ppf(0.5 + level / 2, n - 1))
    return mu, mu - tq * se, mu + tq * se


def H_of(logratio_mean):                      # H = 1 - exp(mean log(M_X / M_ref)); positive = X better than ref
    return 1.0 - math.exp(logratio_mean)


def H_interval(v):
    mu, lo, hi = t_interval(v); return H_of(mu), H_of(hi), H_of(lo)       # H decreasing in the log ratio


def signflip_p(v):
    """Exact two-sided sign-flip p-value of mean(v) (descriptive); meet-in-the-middle over 2^n sign patterns."""
    v = np.asarray(v, float); n = len(v); obs = abs(v.sum()); h = n // 2

    def sums(w):
        s = np.zeros(1)
        for x in w: s = np.concatenate([s + x, s - x])
        return s
    a = sums(v[:h]); b = np.sort(sums(v[h:])); cnt = 0
    for chunk in np.array_split(a, max(1, len(a) // 4096)):
        # count b with |chunk_i + b| >= obs - tol
        lo = np.searchsorted(b, -obs - chunk - 1e-12, side='right'); hi = np.searchsorted(b, obs - chunk + 1e-12, side='left')
        cnt += int(np.sum(lo)) + int(np.sum(len(b) - hi))
    return cnt / (len(a) * len(b))


_CLEAN = {}


def Mq(theta, img):
    if img not in _CLEAN: _CLEAN[img] = clean(img)
    x = GC.render(theta, N); return float(np.mean((x - _CLEAN[img]) ** 2)), float(np.mean(x - _CLEAN[img]))


def tr_cols(a):
    tr = a['traj']; it, F, t, A, W, rss, Ad, Wd = tr.T
    return F, t, A - Ad, W - Wd                                   # effective (cached for PCG8D) counts: A_eff, W_eff


def s_series(m, a, Fref):
    F = tr_cols(a)[0]; return (F - Fref) / max(m['F0'] - Fref, 1e-300)


def s_at_level(s, cnt, level):
    """R1: s at the LAST stored iterate whose work count is <= level (no interpolation); an arm that stopped earlier carries its final s forward."""
    j = np.where(cnt <= level)[0]; return float(s[j[-1]]) if j.size else 1.0


def first_hit(s, thr=1e-2):
    h = np.where(s <= thr)[0]; return int(h[0]) if h.size else None


def traj_metrics(m, a, Fref, caps):
    F, t, Ae, We = tr_cols(a); s = s_series(m, a, Fref)
    out = dict(s_end=float(s[-1]), A_end=float(Ae[-1]), W_end=float(We[-1]), stop=m['stop'], t_end=float(t[-1]), censored=bool(m['stop'] == 'safety'))
    out['s_Acap'] = s_at_level(s, Ae, caps['A']); out['s_Wcap'] = s_at_level(s, We, caps['W'])
    pl = np.where(np.abs(F - F[-1]) <= 1e-6 * abs(F[-1]))[0]; j = int(pl[0]) if pl.size else len(F) - 1
    out['A_plateau'] = float(Ae[j]); out['W_plateau'] = float(We[j]); out['t_plateau'] = float(t[j])
    j = first_hit(s)
    if j is not None: out['A_1e2'] = float(Ae[j]); out['W_1e2'] = float(We[j]); out['t_1e2'] = float(t[j])
    else: out['A_1e2'] = out['W_1e2'] = out['t_1e2'] = None
    return out


def load_q2(include_timing=False):
    ch = load_ch(); subs = ['GEO-H/q2', 'GEO-H/fref'] + (['GEO-H/timing'] if include_timing else [])
    runs = runs_in(*subs); Fref = fref_table(runs); cells = {}
    for m, a in runs:
        if m['arm'] == 'FREF' or m['base'] != 9201 or 'timing' in m['_file']: continue
        cells.setdefault((m['img'], m['cond'], m['K']), {})[m['arm']] = (m, a)
    return ch, Fref, cells


def _pair_levels(ma, aa, mb, ab, caps):
    """R-common level (Opus Q-f): the cap, lowered to the final work of any safety-censored arm of the pair."""
    _, _, Aea, Wea = tr_cols(aa); _, _, Aeb, Web = tr_cols(ab); LA, LW = caps['A'], caps['W']
    for mm, Ae, We in ((ma, Aea, Wea), (mb, Aeb, Web)):
        if mm['stop'] == 'safety': LA = min(LA, float(Ae[-1])); LW = min(LW, float(We[-1]))
    return LA, LW


def cmd_h_q2():
    """Phase H, Q2 work comparison per K layer, frozen readings R1-R6 + Opus Q-f (see contract addendum K1). Quality (R6) and the wall-clock direction are added by cmd_q2_label."""
    ch, Fref, cells = load_q2(); res = {}
    for K in R.KS:
        caps = ch['caps'][str(K)]; keys = sorted(k for k in cells if k[2] == K); rowsK = {}
        for arm in R.ARMS_Q2:
            rows = []
            for k in keys:
                if arm not in cells[k]: continue
                m, a = cells[k][arm]; Fr = Fref[cell_key(m)]; r = traj_metrics(m, a, Fr, caps); r['key'] = k; r['is_ref'] = bool(m['F'] <= Fr * (1 + 1e-12)); rows.append(r)
            rowsK[arm] = rows
        res[K] = dict(n_cells=len(keys), caps=caps)
        for arm, rows in rowsK.items():
            if not rows: continue
            res[K][arm] = dict(n=len(rows), s_end_gmean=gmean([r['s_end'] for r in rows]), s_Acap_gmean=gmean([r['s_Acap'] for r in rows]), s_Wcap_gmean=gmean([r['s_Wcap'] for r in rows]),
                               fail_Acap=float(np.mean([r['s_Acap'] > 1e-2 for r in rows])), fail_Wcap=float(np.mean([r['s_Wcap'] > 1e-2 for r in rows])), fail_end=float(np.mean([r['s_end'] > 1e-2 for r in rows])),
                               ref_holder=float(np.mean([r['is_ref'] for r in rows])), A_plateau_med=float(np.median([r['A_plateau'] for r in rows])), W_plateau_med=float(np.median([r['W_plateau'] for r in rows])),
                               censor_rate=float(np.mean([r['censored'] for r in rows])), stops={st: sum(1 for r in rows if r['stop'] == st) for st in STOPS})
        # ---- pairwise readings GEO vs X at common levels; clause (a) on jointly reached cells; clause (b) arm-wise (R4, R5)
        byk = {arm: {r['key']: r for r in rows} for arm, rows in rowsK.items()}; pairs = {}
        for other in ('BJ', 'BLK', 'LMD', 'LSMR', 'PCG8P', 'PCG8D', 'GEO-r8'):
            if other not in byk or 'GEO' not in byk: continue
            ks = [k for k in byk['GEO'] if k in byk[other]]; fg = {'A': [], 'W': []}; fo = {'A': [], 'W': []}; lr = {'A': {}, 'W': {}}
            for k in ks:
                (mg, ag), (mo, ao) = cells[k]['GEO'], cells[k][other]; Fr = Fref[cell_key(mg)]; LA, LW = _pair_levels(mg, ag, mo, ao, caps); sg, so = s_series(mg, ag, Fr), s_series(mo, ao, Fr)
                _, _, Aeg, Weg = tr_cols(ag); _, _, Aeo, Weo = tr_cols(ao)
                fg['A'].append(s_at_level(sg, Aeg, LA) > 1e-2); fo['A'].append(s_at_level(so, Aeo, LA) > 1e-2); fg['W'].append(s_at_level(sg, Weg, LW) > 1e-2); fo['W'].append(s_at_level(so, Weo, LW) > 1e-2)
                rg, ro = byk['GEO'][k], byk[other][k]
                for acc in ('A', 'W'):
                    if rg[acc + '_1e2'] is not None and ro[acc + '_1e2'] is not None: lr[acc].setdefault(k[0], []).append(math.log(rg[acc + '_1e2'] / ro[acc + '_1e2']))
            pr = dict(n_cells=len(ks), n_geo_fail_A=int(np.sum(fg['A'])), n_geo_fail_W=int(np.sum(fg['W'])), n_other_fail_A=int(np.sum(fo['A'])), n_other_fail_W=int(np.sum(fo['W'])), geo_fail_A=float(np.mean(fg['A'])) if ks else None, geo_fail_W=float(np.mean(fg['W'])) if ks else None, other_fail_A=float(np.mean(fo['A'])) if ks else None,
                      other_fail_W=float(np.mean(fo['W'])) if ks else None)
            for acc in ('A', 'W'):
                per_img = [float(np.mean(v)) for _, v in sorted(lr[acc].items())]; n = len(per_img)
                if n >= 2:
                    mu, lo, hi = t_interval(per_img); pr['ratio_' + acc] = dict(n_images=n, ratio=math.exp(mu), lo=math.exp(lo), hi=math.exp(hi), n_cells_joint=sum(len(v) for v in lr[acc].values()))
                else: pr['ratio_' + acc] = dict(n_images=n, ratio=None)
            pairs[other] = pr
        res[K]['pairs'] = pairs
        cens = {arm: res[K][arm]['censor_rate'] for arm in ('GEO', 'BJ', 'BLK') if arm in res[K]}
        censor_fail = any(v > 0.10 for v in cens.values())
        clause_a = all(pairs.get(o, {}).get('ratio_' + acc, {}).get('ratio') is not None and pairs[o]['ratio_' + acc]['n_images'] >= MIN_IMG_A and pairs[o]['ratio_' + acc]['ratio'] <= 0.5
                       for o in ('BJ', 'BLK') for acc in ('A', 'W'))
        def cb(o):
            pr = pairs.get(o)
            return bool(pr and pr['other_fail_A'] >= 0.25 and pr['other_fail_W'] >= 0.25 and pr['geo_fail_A'] <= 0.10 and pr['geo_fail_W'] <= 0.10)
        clause_b = bool(cb('BJ') or cb('BLK'))
        res[K]['work_decision'] = dict(censoring_rates=cens, censor_fail=censor_fail, clause_a=bool(clause_a), clause_b=clause_b, clause_b_BJ=cb('BJ'), clause_b_BLK=cb('BLK'))
    json.dump(res, open(os.path.join(OUT, 'GEO-H', 'Q2_work.json'), 'w'), indent=1, default=str)
    for K in R.KS: print('K=%d' % K, json.dumps(res[K]['work_decision'], default=str))
    return res


def quality_logratios(arm_theta, ref_theta):
    """dicts key->(theta) ; returns per-key (log ratio M_X/M_ref, bias_X)."""
    out = {}
    for k in arm_theta:
        if k in ref_theta:
            mx, bx = Mq(arm_theta[k], k[0]); mr, br = Mq(ref_theta[k], k[0]); out[k] = (math.log(mx / mr), bx)
    return out


def per_image(lr, K, conds=R.CONDS):
    """lr: key (img, cond, K, base)->(logratio, bias). Per image mean over conditions and bases within tier K."""
    d = {}
    for (i, c, KK, b), (v, _) in lr.items():
        if KK == K: d.setdefault(i, []).append(v)
    return [float(np.mean(v)) for i, v in sorted(d.items())]


def cmd_h_q1():
    ch = load_ch(); res = {}
    q1 = runs_in('GEO-H/q1'); q2 = runs_in('GEO-H/q2')
    reg = {}; dp = {}; f0conv = {}; lmd_dp = {}; trig = {}
    for m, a in q1 + q2:
        key = (m['img'], m['cond'], m['K'], m['base'])
        if m['arm'] == 'GEO' and m['lam'] > 0: reg[key] = a['theta']
        elif m['arm'] == 'F0GEO':
            j = list(R.TAU_GRID).index(ch['tau_star']['%s_K%d' % (m['cond'], m['K'])]); dp[key] = a['tau_theta'][j]; f0conv[key] = a['theta']; trig[key] = bool(a['tau_idx'][j] >= 0)
        elif m['arm'] == 'F0LMD':
            j = list(R.TAU_GRID).index(ch['tau_star']['%s_K%d' % (m['cond'], m['K'])]); lmd_dp[key] = a['tau_theta'][j]
    for K in R.KS:
        lr = quality_logratios({k: v for k, v in reg.items() if k[2] == K}, dp); v = per_image(lr, K)
        if len(v) < 3: continue
        H, lo, hi = H_interval(v); conds = {}
        for c in R.CONDS:
            vv = [x[0] for k, x in lr.items() if k[1] == c]; conds[c] = H_of(float(np.mean(vv))) if vv else None
        cond_nonneg = sum(1 for x in conds.values() if x is not None and x >= 0)
        trate = float(np.mean([t for k, t in trig.items() if k[2] == K])) if trig else None
        label = 'REG-HELPS' if (H >= 0.05 and lo > 0 and cond_nonneg >= 3) else ('REG-HURTS' if (H <= -0.05 and hi < 0) else 'REG-NEUTRAL')
        bias = float(np.mean([x[1] for x in lr.values()]))
        lr2 = quality_logratios({k: v for k, v in dp.items() if k[2] == K}, lmd_dp); v2 = per_image(lr2, K)
        lr3 = quality_logratios({k: v for k, v in reg.items() if k[2] == K}, f0conv); v3 = per_image(lr3, K)
        res[K] = dict(H=H, H_lo=lo, H_hi=hi, n_images=len(v), conds=conds, cond_nonneg=cond_nonneg, dp_trigger_rate=trate, label=label, mean_intensity_bias_reg_minus_truth=bias,
                      signflip_p_desc=signflip_p(v) if len(v) <= 24 else None,
                      note=('F_a(lam*) vs converged F_0 (DP trigger rate < 50%)' if (trate is not None and trate < 0.5) else 'F_a(lam*) vs F_0+GEO+DP(tau*)'),
                      GEO_dp_vs_LMD_dp_H=H_interval(v2) if len(v2) >= 3 else None, REG_vs_F0_converged_H=H_interval(v3) if len(v3) >= 3 else None)
        print('K=%d' % K, json.dumps(res[K], default=str))
    # y-only pairing (descriptive): lambda_DP from ypair runs vs tau=1 (F0GEO tau idx 2)
    yp = runs_in('GEO-H/ypair'); byc = {}
    for m, a in yp: byc.setdefault((m['img'], m['cond'], m['K'], m['base']), {})[m['lam']] = (m, a)
    pair = {}; infeas = {}; nonmono = {}
    for key, d in byc.items():
        ok = sorted([lam for lam, (m, a) in d.items() if a['traj'][-1][5] <= N * N * m_sn2(key[1])])
        infeas[key] = len(ok) == 0
        if ok:
            lam_dp = max(ok); grid = sorted(d); idxs = [grid.index(l) for l in ok]; nonmono[key] = (max(idxs) - min(idxs) + 1) != len(idxs)
        else: lam_dp = min(d); nonmono[key] = False
        pair[key] = d[lam_dp][1]['theta']
    f0tau = {}
    for m, a in q1:
        if m['arm'] == 'F0GEO': f0tau[(m['img'], m['cond'], m['K'], m['base'])] = a['tau_theta'][list(R.TAU_GRID).index(1.0)]
    for K in R.KS:
        lrp = quality_logratios({k: v for k, v in pair.items() if k[2] == K}, f0tau); vp = per_image(lrp, K)
        strata = {c: dict(infeasible=float(np.mean([infeas[k] for k in infeas if k[1] == c and k[2] == K])) if any(k[1] == c and k[2] == K for k in infeas) else None,
                          nonmonotone=float(np.mean([nonmono[k] for k in nonmono if k[1] == c and k[2] == K])) if any(k[1] == c and k[2] == K for k in nonmono) else None) for c in R.CONDS}
        if len(vp) >= 3:
            res.setdefault('ypair', {})[K] = dict(H_lamDP_vs_tau1=H_interval(vp), strata=strata)
    json.dump(res, open(os.path.join(OUT, 'GEO-H', 'Q1_quality.json'), 'w'), indent=1, default=str)
    return res


def m_sn2(cond):
    return GG.COND[cond][1] ** 2


def cmd_q2_quality():
    """R6: quality condition GEO vs BJ (and BLK, descriptive) at BOTH the A_cap and the W_cap readings: H = 1 - exp(mean over images of mean over (cond) of log(M_GEO/M_X)); lower 95% t-bound must be >= -0.02."""
    ch, Fref, cells = load_q2(); res = {}
    for K in R.KS:
        res[K] = {}
        for other in ('BJ', 'BLK'):
            for rd in ('Acap', 'Wcap'):
                per = {}
                for k, d in cells.items():
                    if k[2] != K or 'GEO' not in d or other not in d: continue
                    th_g, th_o = d['GEO'][1]['theta_' + rd], d[other][1]['theta_' + rd]
                    per.setdefault(k[0], []).append(math.log(Mq(th_g, k[0])[0] / Mq(th_o, k[0])[0]))
                v = [float(np.mean(x)) for _, x in sorted(per.items())]
                if len(v) >= 3: H, lo, hi = H_interval(v); res[K][other + '_' + rd] = dict(n_images=len(v), H=H, H_lo=lo, H_hi=hi, ok=bool(lo >= -0.02))
                else: res[K][other + '_' + rd] = dict(n_images=len(v), ok=None)
        res[K]['quality_ok_BJ'] = bool(res[K]['BJ_Acap'].get('ok') and res[K]['BJ_Wcap'].get('ok'))
        print('K=%d quality:' % K, json.dumps(res[K], default=str))
    json.dump(res, open(os.path.join(OUT, 'GEO-H', 'Q2_quality.json'), 'w'), indent=1, default=str); return res


def cmd_h_timing():
    """Wall-clock direction (Opus Q-d). Exclusive single-thread repeats (mean over reps of the time at each iterate). Per K layer and per X in (BJ, BLK): cells where GEO and X both reach s<=1e-2;
    three log-ratios (t, n_A, W) of GEO/X at the first s<=1e-2 iterate, mean within image then across images; direction_ok = all three means < 0 (GEO cheaper).
    If fewer than 6 images are jointly reached: wall-clock analogue of clause (b): t*=GEO time to s<=1e-2; X's s at t* > 1e-2 in >=25% of the K layer's timing cells while GEO fails <=10%."""
    ch, Fref, _ = load_q2(include_timing=True); runs = [r for r in runs_in('GEO-H/timing')]; by = {}
    for m, a in runs: by.setdefault((m['arm'], m['img'], m['cond'], m['K']), []).append((m, a))
    res = {}
    for K in R.KS:
        caps = ch['caps'][str(K)]; res[K] = {}
        for other in ('BJ', 'BLK'):
            cells = sorted({(i, c) for (arm, i, c, KK) in by if KK == K and arm == 'GEO' and (other, i, c, K) in by}); per_t = {}; per_A = {}; per_W = {}; nG = nO = 0; hitO = 0
            for (i, c) in cells:
                LG, LO = by[('GEO', i, c, K)], by[(other, i, c, K)]
                def prep(L):
                    m0, a0 = L[0]; Fr = Fref[cell_key(m0)]; s = s_series(m0, a0, Fr); F, t0, Ae, We = tr_cols(a0)
                    t = np.mean([tr_cols(a)[1] for _, a in L], axis=0); return s, t, Ae, We
                sg, tg, Aeg, Weg = prep(LG); so, to, Aeo, Weo = prep(LO); jg, jo = first_hit(sg), first_hit(so)
                nG += int(jg is None)
                if jg is not None:
                    tstar = tg[jg]; jj = np.where(to <= tstar)[0]; hitO += int((so[jj[-1]] if jj.size else 1.0) > 1e-2)
                if jg is not None and jo is not None:
                    per_t.setdefault(i, []).append(math.log(tg[jg] / to[jo])); per_A.setdefault(i, []).append(math.log(Aeg[jg] / Aeo[jo])); per_W.setdefault(i, []).append(math.log(Weg[jg] / Weo[jo]))
            n_img = len(per_t); n_cells = len(cells)
            if n_img >= MIN_IMG_T:
                m3 = {nm: float(np.mean([float(np.mean(v)) for _, v in sorted(d.items())])) for nm, d in (('t', per_t), ('A', per_A), ('W', per_W))}
                res[K][other] = dict(mode='ratio', n_images=n_img, mean_log_ratio=m3, ratio={nm: math.exp(v) for nm, v in m3.items()}, direction_ok=bool(all(v < 0 for v in m3.values())))
            else:
                fg = nG / n_cells if n_cells else None; fo = hitO / n_cells if n_cells else None
                res[K][other] = dict(mode='clause_b_analogue', n_images=n_img, n_cells=n_cells, geo_fail=fg, other_s_gt_1e2_at_tstar=fo, direction_ok=bool(n_cells > 0 and fo >= 0.25 and fg <= 0.10))
        print('K=%d timing:' % K, json.dumps(res[K], default=str))
    json.dump(res, open(os.path.join(OUT, 'GEO-H', 'TIMING.json'), 'w'), indent=1, default=str); return res


def cmd_q2_label():
    """Combine V (amended, at lambda*), censoring, work clauses, quality, wall-clock direction into the Q2 label per K layer and overall (both layers). All labels carry the amended-V tag."""
    work = json.load(open(os.path.join(OUT, 'GEO-H', 'Q2_work.json'))); qual = json.load(open(os.path.join(OUT, 'GEO-H', 'Q2_quality.json')))
    tim = json.load(open(os.path.join(OUT, 'GEO-H', 'TIMING.json'))); vl = json.load(open(os.path.join(OUT, 'GEO-D', 'V_PASS_LAMSTAR.json'))); vd = json.load(open(os.path.join(OUT, 'GEO-D', 'V_PASS_DEV.json')))
    out = {}
    for K in R.KS:
        k = str(K); w = work[k]['work_decision']; v_ok = bool(vl[k]['pass']); c14 = bool(vd['C14_flag_tuned_GEO']); q_ok = bool(qual[k]['quality_ok_BJ']); t_ok = bool(tim[k]['BJ']['direction_ok'] and tim[k]['BLK']['direction_ok'])
        if c14: lab = 'JOINT-NOT-MATTERS (C14: GEO-specific failure mode on dev; not Q2 evidence, contract Sec.7)'
        elif not v_ok: lab = 'INCONCLUSIVE (V re-check at lambda* failed in this K layer; counts as JOINT-NOT-MATTERS for ADVANCE)'
        elif w['censor_fail']: lab = 'JOINT-NOT-MATTERS (>10% safety-censored decision arm)'
        else: lab = 'JOINT-MATTERS' if ((w['clause_a'] or w['clause_b']) and q_ok and t_ok) else 'JOINT-NOT-MATTERS'
        out[k] = dict(label=lab, C14_flag_tuned_GEO=c14, V_lamstar=v_ok, censor_fail=w['censor_fail'], clause_a=w['clause_a'], clause_b=w['clause_b'], quality_ok=q_ok, wallclock_ok=t_ok)
    both = all(out[str(K)]['label'] == 'JOINT-MATTERS' for K in R.KS)
    out['overall'] = ('JOINT-MATTERS (both K layers) ' if both else 'JOINT-NOT-MATTERS / INCONCLUSIVE (not both K layers) ') + AMEND_TAG
    out['V_pass_amended_dev'] = vd['V_pass_amended']['passed']; out['V_pass_frozen_spec'] = vd['V_pass_frozen_spec']['passed']
    print(json.dumps(out, indent=1)); json.dump(out, open(os.path.join(OUT, 'GEO-H', 'Q2_LABEL.json'), 'w'), indent=1); return out


def cmd_l_report():
    """Phase L report (Q3). Rule = pre-D addendum K1 #11 as amended by the Opus review (Q-g): tolerances {1e-2,1e-3,1e-4} must all pass the criterion; censoring of ANY of them at ANY size/state at eta=0 => INCONCLUSIVE;
    1e-3 headline only; share (a) measured once per size from the LSMR arm's own settings (maxiter=p; median over the 3 exclusive repeats x 2 states = 6); descriptive: per-tolerance/per-state/kappa=1e-3 slopes,
    cond estimates, residual-test cost, maxiter-hit fraction."""
    import glob as _g
    recs = sorted([json.load(open(f)) for f in _g.glob(os.path.join(OUT, 'GEO-L', 'L_*.json'))], key=lambda r: r['K'])
    assert len(recs) == 5, 'phase L incomplete (%d/5)' % len(recs)
    res = dict(sizes=[(r['N'], r['K']) for r in recs]); logK = np.log([r['K'] for r in recs]); TOL = ('0.01', '0.001', '0.0001'); ST = ('grid', 'iter5')

    def slope(y, x):
        n = len(x); X = np.vstack([np.ones(n), x]).T; beta = np.linalg.lstsq(X, y, rcond=None)[0]; resid = y - X @ beta
        s2 = float(resid @ resid / (n - 2)); se = math.sqrt(s2 / float(((x - x.mean()) ** 2).sum())); tq = float(_st.t.ppf(0.975, n - 2))
        return float(beta[1]), float(beta[1] - tq * se), float(beta[1] + tq * se)
    sh = {}; mh = {}
    for r in recs:
        reps = [q for sname in ST for q in r['states'][sname]['stage_reps']]; med = {k: float(np.median([q[k] for q in reps])) for k in ('jac', 'aj', 'solve', 'back')}; tot = sum(med.values())
        sh['%d_%d' % (r['N'], r['K'])] = dict(aj_solve=(med['aj'] + med['solve']) / tot, jac=med['jac'] / tot, back=med['back'] / tot, med_s=med)
        mh['%d_%d' % (r['N'], r['K'])] = float(np.mean([bool(q.get('hit_maxiter')) for q in reps]))
    two = ['%d_%d' % (r['N'], r['K']) for r in recs[-2:]]
    res['shares_by_size'] = sh; res['LSMR_arm_hit_maxiter_fraction_by_size'] = mh
    cond_a = all(sh[k]['aj_solve'] >= 0.5 for k in two); assembly = all(sh[k]['jac'] >= 0.5 for k in two)
    ok_b = {}; cens_any = {}; desc = {}
    for dname in ('eta0', 'kappa1e-3'):
        desc[dname] = {}
        for tol in ('0.01', '0.001', '0.0001', '1e-06'):
            cens = {'%d_%d_%s' % (r['N'], r['K'], sname): bool(r['states'][sname][dname]['censored'][tol]) for r in recs for sname in ST}
            d = dict(iters={'%d_%d' % (r['N'], r['K']): {sname: r['states'][sname][dname]['iters'][tol] for sname in ST} for r in recs}, censored_cells=[k for k, v in cens.items() if v])
            if not any(cens.values()):
                ymean = np.array([np.mean([math.log(r['states'][sname][dname]['iters'][tol]) for sname in ST]) for r in recs])
                sl, lo, hi = slope(ymean, logK); loo = [slope(np.delete(ymean, j), np.delete(logK, j))[0] for j in range(5)]
                per_state = {sname: slope(np.array([math.log(r['states'][sname][dname]['iters'][tol]) for r in recs]), logK)[0] for sname in ST}
                d.update(slope=sl, lo=lo, hi=hi, loo=loo, per_state_slopes=per_state, sign_flip_between_states=bool(per_state['grid'] * per_state['iter5'] < 0), crit=bool(sl >= 0.25 and lo > 0 and all(x > 0 for x in loo)))
            desc[dname][tol] = d
            if dname == 'eta0' and tol in TOL: cens_any[tol] = any(cens.values()); ok_b[tol] = d.get('crit')
    res['by_damping_and_tolerance'] = desc
    inconclusive = any(cens_any.values())
    label = 'INCONCLUSIVE(=FLAT for ADVANCE)' if inconclusive else ('BOTTLENECK-OPTIMISABLE' if (cond_a and all(ok_b[t] for t in TOL)) else ('ASSEMBLY-BOUND' if assembly else 'FLAT'))
    res['Q3_label'] = label; res['Q3_detail'] = dict(cond_a_share_two_largest=cond_a, criterion_b_by_tol=ok_b, censored_any_size_by_tol=cens_any, assembly_bound=assembly, headline_tol_1e3_slope=desc['eta0']['0.001'].get('slope'))
    res['cond_est_lsmr_internal_descriptive'] = {'%d_%d_%s_%s' % (r['N'], r['K'], sname, dn): r['states'][sname][dn].get('residual_test', {}).get('cond_est') for r in recs for sname in ST for dn in ('eta0', 'kappa1e-3')}
    res['residual_test_cost'] = {'%d_%d_%s_%s' % (r['N'], r['K'], sname, dn): r['states'][sname][dn].get('residual_test') for r in recs for sname in ST for dn in ('eta0', 'kappa1e-3')}
    res['gram_block_density'] = {'%d_%d' % (r['N'], r['K']): r['states']['grid']['gram_block_density'] for r in recs}
    res['dense_one_iter_s'] = {'%d_%d' % (r['N'], r['K']): r['dense_one_iter_s'] for r in recs}
    json.dump(res, open(os.path.join(OUT, 'GEO-L', 'Q3.json'), 'w'), indent=1); print(json.dumps(res, indent=1)); return res


def cmd_lam_stops():
    """Opus addition (1): stop-reason distribution of GEO at lambda* vs lambda=1e-3 per (condition, K) on the dev cells (budgeted lamgrid runs)."""
    ch = load_ch(); runs = runs_in('GEO-D/lamgrid'); out = {}
    for c in R.CONDS:
        for K in R.KS:
            key = '%s_K%d' % (c, K); ls = ch['lam_star'][key]
            for nm, lam in (('lam_star', ls), ('lam_1e-3', R.LAM_TUNE)):
                rr = [m for m, _ in runs if m['cond'] == c and m['K'] == K and m['lam'] == lam]
                out['%s_%s' % (key, nm)] = dict(lam=lam, n=len(rr), stops={st: sum(1 for m in rr if m['stop'] == st) for st in STOPS})
    json.dump(out, open(os.path.join(OUT, 'GEO-D', 'LAM_STOPS.json'), 'w'), indent=1); print(json.dumps(out)[:3000]); return out


def cmd_plan():
    """Compute-plan projection and compression (K1 item 10(vi); Opus Q-d). Run ONCE at the end of phase D (before any H job); the result is written to choices.json['plan'] and never changed in H.
    projection = sum(dev median wall-s per cell per arm and K) x (number of cells) x 1.2.  Args: plan [deadline_utc=YYYY-MM-DDTHH:MMZ (the COMPRESSION deadline)] [cap_h=40] [now_utc=...] [extra_h=<wall-clock hours of phases still to run after the plan, incl. phase L and the lambda* re-check>].
    If projection > cap_h CPU-h OR projected finish (now + projection/2 concurrent jobs + extra) is later than deadline: apply in order (1) descriptive arms LSMR/PCG8P/PCG8D on images 201-212 only,
    (2) HIST on 201-212 (HIST is not implemented: zero cost, recorded), (3) y-pairing images halved to 201-206, (4) timing subset halved to 48 cells (201-206), (5) Q1 arms drop base 9202.
    F_ref restarts and V tests are never cut. Every step and its projection is recorded."""
    import datetime as _dt
    kv = dict(a.split('=', 1) for a in sys.argv[2:] if '=' in a); cap_h = float(kv.get('cap_h', 40)); extra_h = float(kv.get('extra_h', 0))
    pt = lambda x: _dt.datetime.strptime(x, '%Y-%m-%dT%H:%MZ').replace(tzinfo=_dt.timezone.utc)
    now = pt(kv['now_utc']) if 'now_utc' in kv else _dt.datetime.now(_dt.timezone.utc); deadline = pt(kv['deadline_utc']) if 'deadline_utc' in kv else None
    ch = load_ch(); med = {}
    runs = runs_in('GEO-D/vpass', 'GEO-D/tune_arms', 'GEO-D/fref')
    for K in R.KS:
        for arm in ('GEO', 'GEO-r8', 'LMD'):
            w = [m['wall'] for m, _ in runs if m['arm'] == arm and m['K'] == K and 'vpass' in m['_file']]
            if w: med[(arm, K)] = float(np.median(w))
        for arm in ('BJ', 'BLK', 'LSMR', 'PCG8P', 'PCG8D'):
            c = ch[arm]; w = [m['wall'] for m, _ in runs if m['arm'] == arm and m['K'] == K and 'tune_arms' in m['_file'] and m['cfg']['f'] == c['f'] and m['cfg'].get('rcond') == c.get('rcond') and m['cfg']['kappa0'] == c['kappa0']]
            if w: med[(arm, K)] = float(np.median(w))
        w = [m['wall'] for m, _ in runs if m['arm'] == 'FREF' and m['K'] == K]
        if w: med[('FREF', K)] = float(np.median(w))
    miss = [(a, K) for K in R.KS for a in ('GEO', 'GEO-r8', 'LMD', 'BJ', 'BLK', 'LSMR', 'PCG8P', 'PCG8D', 'FREF') if (a, K) not in med]; assert not miss, 'plan: missing dev medians %s' % miss
    ncell = len(R.CONDS) * len(GG.TEST_IMGS); n12 = len(R.CONDS) * min(12, len(GG.TEST_IMGS)); n6 = len(R.CONDS) * min(6, len(GG.TEST_IMGS)); nlam = len(R.LAM_GRID) - 1
    def proj(desc12, ypair6, timing6, drop9202):
        """-> (total CPU-h incl. x1.2 margin, exclusive timing-subset CPU-h). Timing runs on one job, so its wall time equals its CPU time."""
        tot = 0.0; tim = 0.0
        for K in R.KS:
            for arm in ('GEO', 'GEO-r8', 'LMD', 'BJ', 'BLK'): tot += med[(arm, K)] * ncell
            for arm in R.DESC_ARMS: tot += med[(arm, K)] * (n12 if desc12 else ncell)
            tot += med[('FREF', K)] * 3 * ncell * (1 if drop9202 else 2)                                  # F_ref restarts per cell and base (9201, and 9202 while kept)
            q1 = (med[('GEO', K)] + med[('LMD', K)]) * ncell + (0 if drop9202 else (med[('GEO', K)] * 2 + med[('LMD', K)]) * ncell)       # F0GEO+F0LMD (+ GEO@lam*, F0GEO, F0LMD for base 9202)
            tot += q1; tot += med[('GEO', K)] * (n6 if ypair6 else n12) * nlam
            tim += (med[('GEO', K)] + med[('BJ', K)] + med[('BLK', K)] + med[('LMD', K)]) * (n6 if timing6 else n12) * 2
        return 1.2 * (tot + tim) / 3600.0, 1.2 * tim / 3600.0
    flags = dict(desc12=False, ypair6=False, timing6=False, drop9202=False); _p = proj(**flags); steps = [dict(step='none', projection_cpu_h=_p[0], timing_exclusive_h=_p[1])]
    def finish(st): return now + _dt.timedelta(hours=(st['projection_cpu_h'] - st['timing_exclusive_h']) / 2.0 + st['timing_exclusive_h'] + extra_h)     # 2 concurrent jobs, exclusive timing alone (Opus Q-j 7)
    def over(st): return st['projection_cpu_h'] > cap_h or (deadline is not None and finish(st) > deadline)
    order = [('(1) descriptive arms LSMR/PCG8P/PCG8D on images 201-212 only', 'desc12'), ('(2) HIST on 201-212 (HIST not implemented; no cost change)', None), ('(3) y-pairing halved to 201-206', 'ypair6'),
             ('(4) timing subset halved to 48 cells (201-206)', 'timing6'), ('(5) Q1 arms drop base 9202', 'drop9202')]
    for name, fl in order:
        if not over(steps[-1]): break
        if fl: flags[fl] = True
        _p = proj(**flags); steps.append(dict(step=name, projection_cpu_h=_p[0], timing_exclusive_h=_p[1]))
    for st in steps: st['finish_utc'] = finish(st).strftime('%Y-%m-%dT%H:%MZ')
    plan = dict(desc_imgs='h12' if flags['desc12'] else 'all', ypair_imgs='h6' if flags['ypair6'] else 'h12', timing_imgs='h6' if flags['timing6'] else 'h12', q1_bases=[9201] if flags['drop9202'] else [9201, 9202],
                steps=steps, cap_h=cap_h, deadline_utc=kv.get('deadline_utc'), now_utc=now.strftime('%Y-%m-%dT%H:%MZ'), extra_h=extra_h, dev_median_wall_s={'%s_K%d' % k: v for k, v in med.items()}, over_after=bool(over(steps[-1])))
    ch['plan'] = plan; save_ch(ch); print(json.dumps(plan, indent=1))


def cmd_report_d():
    ch = load_ch(); print(json.dumps({k: v for k, v in ch.items() if not k.endswith('_table') and k != 'lam_tau_tables'}, indent=1, sort_keys=True))


if __name__ == '__main__':
    globals()['cmd_' + sys.argv[1]]()
