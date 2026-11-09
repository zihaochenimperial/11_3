"""CF0 analyzer (frozen with contract CF0; pure numpy). usage: python experiments/cf_analyze.py outputs/CF0-pilot-p1 --unit_report outputs/cf_unit_tests_status.json
                                                          python experiments/cf_analyze.py outputs/CF0-dev-d1 [outputs/CF0-dev_ext-d1x] --unit_report ...
Pilot: validity + wall + paired-SD only (risk differences MASKED in code: no NU mean is computed or printed; SDs are report-only, M_dev=32 is FIXED by the contract). Dev: GO / STOP / INCONCLUSIVE per contract section 6.
NU(A vs B)_i = (mean_m risk_B - mean_m risk_A) / mean_m risk_B per image i (image-weighted); pooled NU = mean over images; CIs by bootstrap over images (B=10000, stream key (ENTROPY,24,0)).
Alpha spending (contract s6, Opus round 7): two looks (dev, dev+dev_ext) each use alpha/2 -> GO quantile 0.05/4/2 per candidate; STOP: per candidate min over competitors of the upper bound at quantile 1-(0.05/2)/|C(A)| (Bonferroni within a candidate)."""
import argparse, hashlib, json, math, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ENTROPY = 20261107
TAUS = (1.0, 2.0, 4.0)
TYPES = ('D1', 'D2', 'D3')
B_BOOT = 10000
N_CAND = 4; N_LOOKS = 2
ALPHA_GO = 0.05 / N_CAND / N_LOOKS            # per-candidate GO lower-bound quantile (family Bonferroni 4 x two looks)
ALPHA_STOP_TOTAL = 0.05 / N_LOOKS             # per-candidate STOP budget per look, split over |C(A)| competitors
GO_NU = 0.02; GO_FRAC = 2.0 / 3.0; GO_K_NU = 0.01; STOP_NU = 0.01
M_DEV = 32
PILOT_IMAGES = tuple('E%d' % k for k in (15, 16, 17, 18))
DEV_IMAGES = tuple('E%d' % k for k in range(21, 39))
STAGE_RANK = {'pilot': 0, 'dev': 1, 'dev_ext': 2}
STAGE_SETS = (['pilot'], ['dev'], ['dev', 'dev_ext'])
FROZEN_FILES = ['contracts/CF0_CONTRACT.md', 'experiments/cf_run.py', 'experiments/cf_analyze.py', 'src/cf_fit.py', 'src/gsfast.py', 'src/gskernel.py', 'src/omega.py', 'src/f0_config.py', 'src/synth.py',
                'src/reference_eval.py', 'tests/test_cf_units.py', 'tests/test_cf_analyze.py', 'scripts/run_cf_unit_tests.py']
CANDIDATES = {
    'XFERg_t1': ['RAWy', 'NS_t1', 'RANDy', 'RAWcv'],
    'XFERg_t2': ['RAWy', 'NS_t2', 'RANDy', 'RAWcv'],
    'XFERg_t4': ['RAWy', 'NS_t4', 'RANDy', 'RAWcv'],
    'XAVG_t1': ['RAWy', 'RAWens2', 'XAVGctrl_t1', 'NS_t1', 'NSens_t1', 'RANDy', 'RANDens2', 'RAWcv'],
}


def img_type(img):
    return TYPES[(int(img[1:]) - 1) % 3]


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_units(dirs):
    """Returns (metas, U, integrity). Dirs are ordered by stage (pilot < dev < dev_ext). Duplicate (img, m) are NEVER silently overwritten: first one is kept and the duplicate is reported."""
    dl = []
    for d in dirs:
        d = Path(d); meta = json.loads((d / 'meta.json').read_text(encoding='utf-8')); dl.append((STAGE_RANK.get(meta.get('stage'), 99), str(d), d, meta))
    dl.sort(key=lambda t: (t[0], t[1]))
    metas = []; U = {}; dups = []; manifest_ok = []
    for _, _, d, meta in dl:
        metas.append(meta); files = sorted(d.glob('unit_*.npz'))
        mp = d / 'manifest.json'
        try:
            want = json.loads(mp.read_text(encoding='utf-8'))['sha256'] if mp.exists() else None
        except Exception:
            want = None
        got = {f.name: sha_file(f) for f in files}; got['meta.json'] = sha_file(d / 'meta.json')
        manifest_ok.append(bool(want is not None and got == want))
        for f in files:
            z = np.load(f, allow_pickle=False); _, img, m = f.stem.split('_'); m = int(m)
            if m in U.get(img, {}): dups.append((img, m)); continue
            keys = [str(k) for k in z['risks_keys']]; r = dict(zip(keys, map(float, z['risks_vals'])))
            U.setdefault(img, {})[m] = dict(risks=r, diag=json.loads(str(z['diag'])), K=json.loads(str(z['K'])), nfit=float(z['n_fit_equiv']), e_hash=str(z['e_hash']), z_hash=str(z['z_hash']), omega1=str(z['omega1']), omega2=str(z['omega2']))
    return metas, U, dict(dups=dups, manifest_ok=manifest_ok)


def attach_rcv(U):
    """RAWcv = RAWy snapshot at R*cv = argmin_R cv_R (fission-CV tau=1, two-way), per unit."""
    for img in U:
        for m, u in U[img].items():
            cv = u['diag']['cv_R_t1']; Rs = int(np.argmin(cv)); u['Rstar'] = Rs; u['risks']['RAWcv'] = u['risks']['RAWy_R%d' % Rs]
            ro = [u['risks']['RAWy_R%d' % r] for r in range(5)]; u['risks']['RAWoracleR'] = min(ro)      # report-only (non-implementable)


def image_means(U, name):
    imgs = sorted(U, key=lambda s: int(s[1:])); return imgs, np.array([np.mean([U[i][m]['risks'][name] for m in sorted(U[i])]) for i in imgs])


def nu(U, a, b):
    imgs, ra = image_means(U, a); _, rb = image_means(U, b); return imgs, (rb - ra) / rb


def boot_idx(n):
    rng = np.random.default_rng(np.random.SeedSequence(entropy=ENTROPY, spawn_key=(24, 0)))
    return rng.integers(0, n, size=(B_BOOT, n))


def boot_ci(v, idx, q_lo=None, q_hi=None):
    bs = v[idx].mean(axis=1); out = {}
    if q_lo is not None: out['lb'] = float(np.quantile(bs, q_lo))
    if q_hi is not None: out['ub'] = float(np.quantile(bs, q_hi))
    return out


def stop_q(n_comp):
    return 1.0 - ALPHA_STOP_TOTAL / n_comp


def _t_half_cdf(x, df, n=4000):
    c = math.exp(math.lgamma((df + 1) / 2.0) - math.lgamma(df / 2.0)) / math.sqrt(df * math.pi)
    xs = np.linspace(0.0, x, n + 1); f = c * (1.0 + xs ** 2 / df) ** (-(df + 1) / 2.0); h = x / n
    return float(h / 3.0 * (f[0] + f[-1] + 4.0 * f[1:-1:2].sum() + 2.0 * f[2:-1:2].sum()))


def t_ppf(p, df):
    """Student-t quantile for p in (0.5, 1) by bisection on a Simpson-integrated CDF (report-only helper; no scipy)."""
    lo, hi = 0.0, 200.0
    for _ in range(70):
        mid = 0.5 * (lo + hi)
        if 0.5 + _t_half_cdf(mid, df) < p: lo = mid
        else: hi = mid
    return 0.5 * (lo + hi)


def t_lower(v, alpha):
    n = len(v); return float(np.mean(v) - t_ppf(1.0 - alpha, n - 1) * np.std(v, ddof=1) / math.sqrt(n))


def t_upper(v, alpha):
    n = len(v); return float(np.mean(v) + t_ppf(1.0 - alpha, n - 1) * np.std(v, ddof=1) / math.sqrt(n))


def read_manifest(root):
    p = Path(root) / 'contracts' / 'CF0_FROZEN_FILES.sha256'
    if not p.exists(): return None, None
    ent = {}
    for ln in p.read_text(encoding='utf-8').splitlines():
        ln = ln.strip()
        if ln:
            h, name = ln.split(None, 1); ent[name.strip().replace('\\', '/')] = h
    return ent, sha_file(p)


def manifest_matches(root):
    ent, dig = read_manifest(root)
    if ent is None: return False, None
    ok = set(FROZEN_FILES) <= set(ent) and all((Path(root) / n).exists() and sha_file(Path(root) / n) == h for n, h in ent.items())
    return bool(ok), dig


def inputs_check(metas, U, integrity):
    """V8: the analyzer accepts only complete, non-duplicated, non-debug, same-contract inputs of exactly pilot | dev | dev+dev_ext (Opus round 7, B4)."""
    stages = [mm.get('stage') for mm in metas]; why = []
    if stages not in [list(s) for s in STAGE_SETS]: why.append('stages=%s' % stages)
    if any(mm.get('debug') for mm in metas): why.append('debug run')
    if len({mm.get('contract_sha') for mm in metas}) != 1: why.append('contract_sha differs across dirs')
    if len({mm.get('frozen_manifest_sha') for mm in metas}) != 1: why.append('frozen_manifest_sha differs across dirs')
    if stages == ['pilot']: images = set(PILOT_IMAGES); draws = set(range(8))
    else:
        if any(mm.get('M') != M_DEV for mm in metas): why.append('M != %d' % M_DEV)
        images = set(DEV_IMAGES); draws = set(range(M_DEV)) if stages == ['dev'] else set(range(2 * M_DEV))
    if set(U) != images: why.append('image set %s' % sorted(set(U) ^ images))
    bad = [i for i in U if set(U[i]) != draws]
    if bad: why.append('draw set incomplete/extra for %s' % sorted(bad)[:5])
    if (integrity or {}).get('dups'): why.append('duplicate (img,m): %s' % (integrity['dups'][:3],))
    mo = (integrity or {}).get('manifest_ok', [])
    if len(mo) != len(metas) or not all(mo): why.append('manifest.json missing/mismatch')
    for mm in metas:
        nt = len(mm.get('images', [])) * len(mm.get('draws', []))
        if mm.get('max_tasks') or mm.get('n_tasks') != nt: why.append('truncated or inconsistent n_tasks (%s vs %s)' % (mm.get('n_tasks'), nt))
    return (len(why) == 0), why


def validity(metas, U, unit_report, integrity=None, root=None):
    root = Path(root) if root else ROOT
    v = {}
    try:
        rec = (root / 'contracts' / 'CF0_CONTRACT.sha256').read_text().split()[0]; cur_c = sha_file(root / 'contracts' / 'CF0_CONTRACT.md')
    except Exception:
        rec = 'MISSING'; cur_c = 'MISSING2'
    mok, mdig = manifest_matches(root)
    v['V0_contract_and_frozen_files'] = bool((not any(mm.get('debug') for mm in metas)) and rec == cur_c and all(mm.get('contract_sha') == rec for mm in metas) and mok and all(mm.get('frozen_manifest_sha') == mdig for mm in metas))
    ur = unit_report or {}; ent, _ = read_manifest(root); hs = {k.replace('\\', '/'): h for k, h in (ur.get('hashes') or {}).items()}
    try: cur = sha_file(root / 'src' / 'cf_fit.py')
    except Exception: cur = ''
    v['V1_unit_tests'] = bool(ur.get('passed') and hs.get('src/cf_fit.py') == cur and ent is not None and all(hs[k] == ent[k] for k in hs if k in ent) and all(k in hs for k in ent if k.startswith(('src/', 'tests/', 'scripts/', 'experiments/'))))
    nonext = [mm for mm in metas if mm.get('stage') in ('pilot', 'dev')]
    v['V2_replay_bitwise'] = bool(len(nonext) >= 1 and all(mm.get('replay_ok') is True for mm in nonext) and all(mm.get('replay_ok') is None for mm in metas if mm.get('stage') == 'dev_ext'))
    v['V3_complete'] = bool(all((not mm.get('aborted')) and mm.get('done') == mm.get('n_tasks') for mm in metas))
    v['V4_crn_omega_keys'] = bool(all(json.loads(u['omega1'])[:2] == [ENTROPY, 22] and json.loads(u['omega2'])[:2] == [ENTROPY, 22] and json.loads(u['omega1'])[2:4] == json.loads(u['omega2'])[2:4] for i in U for u in U[i].values()))
    ok_ind = True; z_by = {}
    for t in TAUS:
        c = np.array([u['diag']['noise_corr_t%g' % t] for i in U for u in U[i].values()]); se = (1.0 / math.sqrt(64 * 64)) / math.sqrt(len(c)); z_by['noise_corr_t%g' % t] = float(c.mean() / se); ok_ind &= abs(c.mean() / se) < 4.0
    c = np.array([u['diag']['ez_corr'] for i in U for u in U[i].values()]); se = (1.0 / math.sqrt(64 * 64)) / math.sqrt(len(c)); z_by['ez_corr'] = float(c.mean() / se); ok_ind &= abs(c.mean() / se) < 4.0
    v['V5_independence_abs_z<4'] = bool(ok_ind); v['_independence_z'] = z_by
    v['V6_wall<=3h_per_run'] = bool(all((mm.get('wall_s') or 1e18) <= 10800 for mm in metas))
    v['V7_finite_and_RAWy_equals_pipeline'] = bool(all(np.isfinite(list(u['risks'].values())).all() for i in U for u in U[i].values()) and all(mm.get('rawy_pipeline_ok') is True for mm in nonext) and len(nonext) >= 1)
    ok8, why = inputs_check(metas, U, integrity); v['V8_inputs'] = bool(ok8); v['_V8_reasons'] = why
    v['n_units'] = sum(len(U[i]) for i in U)
    gates = [k for k in v if k.startswith('V') and not k.startswith('_')]
    v['all_valid'] = bool(all(v[k] for k in gates))
    return v


def pilot_report(U, v=None):
    """Masked: only SDs of paired per-draw relative differences for every gate contrast (report-only; no means of risk differences)."""
    imgs = sorted(U, key=lambda s: int(s[1:])); out = {}; worst = 0.0
    for a, comps in CANDIDATES.items():
        for b in comps:
            sds = []
            for i in imgs:
                ms = sorted(U[i]); rb = np.array([U[i][m]['risks'][b] for m in ms]); ra = np.array([U[i][m]['risks'][a] for m in ms])
                d = (rb - ra) / rb.mean(); sds.append(float(np.std(d, ddof=1)))
            out['%s_vs_%s' % (a, b)] = dict(per_image_sd=sds, median_sd=float(np.median(sds))); worst = max(worst, float(np.median(sds)))
    return dict(masked=True, paired_sd=out, worst_median_sd=worst, note='report-only; M_dev=%d is fixed by the contract; nothing here sets a threshold' % M_DEV)


def dev_analysis(U):
    imgs = sorted(U, key=lambda s: int(s[1:])); n = len(imgs); idx = boot_idx(n); types = np.array([img_type(i) for i in imgs])
    res = dict(n_images=n, alpha=dict(go_per_candidate=ALPHA_GO, stop_budget_per_candidate_per_look=ALPHA_STOP_TOTAL, looks=N_LOOKS, B_boot=B_BOOT), candidates={}); go = []; stop_all = True
    for a, comps in CANDIDATES.items():
        _, nu_y = nu(U, a, 'RAWy'); ci_go = boot_ci(nu_y, idx, q_lo=ALPHA_GO); ci95 = boot_ci(nu_y, idx, q_lo=0.05, q_hi=0.95)
        row = dict(NU_vs_RAWy=float(nu_y.mean()), LB_go=ci_go['lb'], t_LB_go_report_only=t_lower(nu_y, ALPHA_GO), frac_pos=float((nu_y > 0).mean()), ci95=ci95,
                   per_type={t: float(nu_y[types == t].mean()) for t in TYPES if (types == t).any()}, vs={})
        ok = (nu_y.mean() >= GO_NU) and (ci_go['lb'] > 0) and ((nu_y > 0).mean() >= GO_FRAC)
        qs = stop_q(len(comps)); best_ub = np.inf; best_ub_c = None; old_v = np.inf; old_c = None
        for c in comps:
            _, nc = nu(U, a, c); cg = boot_ci(nc, idx, q_lo=ALPHA_GO, q_hi=qs); c95 = boot_ci(nc, idx, q_hi=0.95)
            row['vs'][c] = dict(NU=float(nc.mean()), LB_go=cg['lb'], UB_stop=cg['ub'], UB95=c95['ub'], t_LB_go_report_only=t_lower(nc, ALPHA_GO), t_UB_stop_report_only=t_upper(nc, ALPHA_STOP_TOTAL / len(comps)))
            if c != 'RAWy': ok &= (cg['lb'] > 0)
            if c == 'RAWcv': ok &= (nc.mean() >= GO_K_NU)
            if cg['ub'] < best_ub: best_ub = cg['ub']; best_ub_c = c
            if nc.mean() < old_v: old_v = float(nc.mean()); old_c = c
        row['UB_stop'] = float(best_ub); row['UB_stop_competitor'] = best_ub_c; row['STOP_pass'] = bool(best_ub < STOP_NU); row['GO_pass'] = bool(ok)
        row['best_competitor'] = old_c; row['retired_cstar_rule_UB95_report_only'] = row['vs'][old_c]['UB95']          # the c*-selected rule (invalid multiplicity, Opus round 7 B1): kept for report only
        stop_all &= row['STOP_pass']
        if ok: go.append(a)
        res['candidates'][a] = row
    res['GO_candidates'] = go
    res['verdict'] = 'GO-dev' if go else ('STOP' if stop_all else 'INCONCLUSIVE')
    rep = {}
    for t in TAUS:
        k = '%g' % t
        for a, b, name in ((f'XFERg_t{k}', f'RAWg_t{k}', f'CF1_selection_effect_equal_noise_t{k}'), (f'XFERg_t{k}', f'RAWf_t{k}', f'XFERg_vs_RAWf_t{k}'), (f'XFERg_t{k}', f'NS_t{k}', f'XFERg_vs_NS_t{k}'), (f'RAWg_t{k}', 'RAWy', f'info_loss_RAWg_vs_RAWy_t{k}'), (f'NS_t{k}', 'RAWy', f'NS_vs_RAWy_t{k}')):
            _, v_ = nu(U, a, b); rep[name] = dict(pooled=float(v_.mean()), per_type={tt: float(v_[types == tt].mean()) for tt in TYPES if (types == tt).any()})
    for a, b, name in (('RANDy', 'RAWy', 'RANDy_vs_RAWy'), ('RANDens2', 'RAWy', 'RANDens2_vs_RAWy'), ('NSens_t1', 'RAWy', 'NSens_vs_RAWy'), ('RAWoracleR', 'RAWy', 'oracleR_vs_RAWy_nonimplementable'), ('RAWcv', 'RAWy', 'RAWcv_vs_RAWy'),
                       ('RAWens2', 'RAWy', 'RAWens2_vs_RAWy'), ('XAVGctrl_t1', 'RAWy', 'XAVGctrl_vs_RAWy')):
        _, v_ = nu(U, a, b); rep[name] = dict(pooled=float(v_.mean()), per_type={tt: float(v_[types == tt].mean()) for tt in TYPES if (types == tt).any()})
    dg = {}
    for key in ('XFERg_t1_disp', 'XFERg_t4_disp', 'RAWg_t4_disp', 'NS_t4_disp', 'RAWy_disp', 'XFERg_t4_resid', 'RAWg_t4_resid', 'idx_overlap_t1', 'idx_overlap_y_t4'):
        vals = [np.mean(u['diag'][key]) for i in U for u in U[i].values() if key in u['diag']]; dg[key] = float(np.mean(vals)) if vals else None
    rep['diagnostics_mean'] = dg
    rep['Rstar_hist'] = {str(r): int(sum(u['Rstar'] == r for i in U for u in U[i].values())) for r in range(5)}
    rep['cost_fit_equiv_per_unit'] = float(np.mean([u['nfit'] for i in U for u in U[i].values()]))
    rep['K_by_arm'] = next(iter(U[imgs[0]].values()))['K']
    rep['scope_note'] = 'STOP/GO concern honest position transfer (XFERg/XAVG) only; NS/RANDy/RANDens2/NSens vs RAWy are report-only findings and do not mean "births cannot be improved"'
    p1 = res['candidates']['XFERg_t1']['NU_vs_RAWy']; p4 = res['candidates']['XFERg_t4']['per_type']; p4all = res['candidates']['XFERg_t4']['NU_vs_RAWy']
    rep['predictions'] = dict(NU_XFERg_t1_vs_RAWy_pooled=dict(observed=p1, predicted_range=[-1.0, -0.25], inside=bool(-1.0 <= p1 <= -0.25)),
                              NU_XFERg_t4_D1D2=dict(observed={k: p4.get(k) for k in ('D1', 'D2')}, predicted_range=[-0.10, 0.05], inside=bool(all((p4.get(k) is not None) and (-0.10 <= p4[k] <= 0.05) for k in ('D1', 'D2')))),
                              NU_XFERg_t4_pooled_negative=dict(observed=p4all, predicted='<0', inside=bool(p4all < 0)))
    res['report_only'] = rep
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('dirs', nargs='+'); ap.add_argument('--unit_report', default=str(ROOT / 'outputs' / 'cf_unit_tests_status.json')); ap.add_argument('--out', default=None)
    a = ap.parse_args()
    metas, U, integ = load_units(a.dirs); attach_rcv(U)
    ur = json.loads(Path(a.unit_report).read_text(encoding='utf-8')) if Path(a.unit_report).exists() else None
    v = validity(metas, U, ur, integ)
    pilot = metas[0]['stage'] == 'pilot'
    res = dict(dirs=a.dirs, stages=[mm.get('stage') for mm in metas], validity=v)
    debug = any(bool(mm.get('debug')) for mm in metas)
    if not v['all_valid'] and not debug:
        res['verdict'] = 'INVALID'
    elif pilot:
        res['pilot'] = pilot_report(U, v); res['verdict'] = 'PILOT_OK (validity+wall only; M_dev=%d fixed)' % M_DEV
    else:
        res.update(dev_analysis(U))
    if debug: res['verdict'] = 'DEBUG-NOT-EVIDENCE:' + res['verdict']
    outp = Path(a.out) if a.out else Path(a.dirs[0]) / 'analysis.json'
    outp.write_text(json.dumps(res, indent=1, default=float), encoding='utf-8')
    print(json.dumps({'verdict': res['verdict'], 'validity': {k: v[k] for k in v if k.startswith('V') or k == 'all_valid'}}, default=float))


if __name__ == '__main__':
    main()
