"""CF0 analyzer (frozen with contract CF0; pure numpy). usage: python experiments/cf_analyze.py outputs/CF0-pilot-p1 --unit_report outputs/cf_unit_tests_status.json
                                                          python experiments/cf_analyze.py outputs/CF0-dev-d1 [outputs/CF0-dev_ext-d1x] --unit_report ...
Pilot: validity + wall + paired-SD only (risk differences MASKED in code: no NU mean is computed or printed). Dev: GO / STOP / INCONCLUSIVE per contract section 6.
NU(A vs B)_i = (mean_m risk_B - mean_m risk_A) / mean_m risk_B per image i (image-weighted); pooled NU = mean over images; CIs by bootstrap over images (B=2000, stream key (ENTROPY,24,0))."""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ENTROPY = 20261107
TAUS = (1.0, 2.0, 4.0)
TYPES = ('D1', 'D2', 'D3')
B_BOOT = 2000
ALPHA_FAMILY = 0.05 / 4          # Bonferroni over the 4 candidates (GO lower bounds)
GO_NU = 0.02; GO_FRAC = 2.0 / 3.0; GO_K_NU = 0.01; STOP_NU = 0.01; SE_TARGET = 0.01; M_CHOICES = (8, 16, 32)
CANDIDATES = {
    'XFERg_t1': ['RAWy', 'NS_t1', 'RANDy', 'RAWcv'],
    'XFERg_t2': ['RAWy', 'NS_t2', 'RANDy', 'RAWcv'],
    'XFERg_t4': ['RAWy', 'NS_t4', 'RANDy', 'RAWcv'],
    'XAVG_t1': ['RAWy', 'RAWens2', 'XAVGctrl_t1', 'NS_t1', 'RANDy', 'RAWcv'],
}


def img_type(img):
    return TYPES[(int(img[1:]) - 1) % 3]


def load_units(dirs):
    meta0 = None; U = {}; metas = []
    for d in dirs:
        d = Path(d); meta = json.loads((d / 'meta.json').read_text(encoding='utf-8')); metas.append(meta)
        for f in sorted(d.glob('unit_*.npz')):
            z = np.load(f, allow_pickle=False); _, img, m = f.stem.split('_'); m = int(m)
            keys = [str(k) for k in z['risks_keys']]; r = dict(zip(keys, map(float, z['risks_vals'])))
            diag = json.loads(str(z['diag']))
            U.setdefault(img, {})[m] = dict(risks=r, diag=diag, K=json.loads(str(z['K'])), nfit=float(z['n_fit_equiv']), e_hash=str(z['e_hash']), z_hash=str(z['z_hash']), omega1=str(z['omega1']), omega2=str(z['omega2']))
    return metas, U


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


def validity(metas, U, unit_report, dev_like=True):
    v = {}
    meta = metas[0]
    ch = (ROOT / 'contracts' / 'CF0_CONTRACT.sha256').read_text().split()[0] if (ROOT / 'contracts' / 'CF0_CONTRACT.sha256').exists() else 'MISSING'
    v['V0_contract_hash'] = bool((not meta.get('debug')) and all(mm.get('contract_sha') == ch for mm in metas))
    ur = unit_report or {}
    cur = hashlib.sha256((ROOT / 'src' / 'cf_fit.py').read_bytes()).hexdigest() if (ROOT / 'src' / 'cf_fit.py').exists() else ''
    v['V1_unit_tests'] = bool(ur.get('passed') and (ur.get('hashes', {}).get('src\\cf_fit.py') == cur or ur.get('hashes', {}).get('src/cf_fit.py') == cur))
    v['V2_replay_bitwise'] = bool(all(mm.get('replay_ok') in (True, None) for mm in metas) and any(mm.get('replay_ok') is True for mm in metas))
    v['V3_complete'] = bool(all((not mm.get('aborted')) and mm.get('done') == mm.get('n_tasks') for mm in metas))
    n_units = sum(len(U[i]) for i in U)
    v['V4_crn_omega_keys'] = bool(all(json.loads(u['omega1'])[:2] == [ENTROPY, 22] and json.loads(u['omega2'])[:2] == [ENTROPY, 22] and json.loads(u['omega1'])[2:4] == json.loads(u['omega2'])[2:4] for i in U for u in U[i].values()))
    ok_ind = True; z_by_tau = {}
    for t in TAUS:
        c = np.array([u['diag']['noise_corr_t%g' % t] for i in U for u in U[i].values()]); se = (1.0 / np.sqrt(64 * 64)) / np.sqrt(len(c)); z_by_tau['%g' % t] = float(c.mean() / se); ok_ind &= abs(c.mean() / se) < 4.0
    v['V5_independence_z<4'] = bool(ok_ind); v['_independence_z'] = z_by_tau
    v['V6_wall<=3h'] = bool(all((mm.get('wall_s') or 1e18) <= 10800 for mm in metas))
    v['V7_finite_consistent'] = bool(all(np.isfinite(list(u['risks'].values())).all() and abs(u['risks']['RAWy'] - u['risks']['RAWy_R3']) < 1e-9 * max(1.0, u['risks']['RAWy']) for i in U for u in U[i].values()))
    v['n_units'] = n_units
    gates = [k for k in v if k.startswith('V') and not k.startswith('_')]
    v['all_valid'] = bool(all(v[k] for k in gates))
    return v


def pilot_report(U, v):
    """Masked: only SDs of paired per-draw relative differences (no means)."""
    imgs = sorted(U, key=lambda s: int(s[1:])); out = {}; worst = 0.0
    pairs = [('XFERg_t1', 'RAWy'), ('XFERg_t2', 'RAWy'), ('XFERg_t4', 'RAWy'), ('XAVG_t1', 'RAWy'), ('XAVG_t1', 'RAWens2'), ('XFERg_t4', 'NS_t4'), ('XFERg_t4', 'RAWcv')]
    for a, b in pairs:
        sds = []
        for i in imgs:
            ms = sorted(U[i]); rb = np.array([U[i][m]['risks'][b] for m in ms]); ra = np.array([U[i][m]['risks'][a] for m in ms])
            d = (rb - ra) / rb.mean(); sds.append(float(np.std(d, ddof=1)))
        out['%s_vs_%s' % (a, b)] = dict(per_image_sd=sds, median_sd=float(np.median(sds))); worst = max(worst, float(np.median(sds)))
    Mneed = next((M for M in M_CHOICES if worst / np.sqrt(M) <= SE_TARGET), None)
    return dict(masked=True, paired_sd=out, worst_median_sd=worst, M_dev=(Mneed if Mneed else 32), LIMITED_POWER=(Mneed is None), rule='smallest M in {8,16,32} with max_contrast median_i SD / sqrt(M) <= 0.01; else 32 and LIMITED_POWER')


def dev_analysis(U):
    imgs = sorted(U, key=lambda s: int(s[1:])); n = len(imgs); idx = boot_idx(n); types = np.array([img_type(i) for i in imgs])
    res = dict(n_images=n, candidates={}); go = []; stop_all = True
    for a, comps in CANDIDATES.items():
        _, nu_y = nu(U, a, 'RAWy'); ci_go = boot_ci(nu_y, idx, q_lo=ALPHA_FAMILY); ci95 = boot_ci(nu_y, idx, q_lo=0.05, q_hi=0.95)
        row = dict(NU_vs_RAWy=float(nu_y.mean()), LB_go=ci_go['lb'], frac_pos=float((nu_y > 0).mean()), ci95=ci95, per_type={t: float(nu_y[types == t].mean()) for t in TYPES if (types == t).any()}, vs={})
        ok = (nu_y.mean() >= GO_NU) and (ci_go['lb'] > 0) and ((nu_y > 0).mean() >= GO_FRAC)
        worst_c = None; worst_v = np.inf
        for c in comps:
            _, nc = nu(U, a, c); cg = boot_ci(nc, idx, q_lo=ALPHA_FAMILY); c95 = boot_ci(nc, idx, q_hi=0.95)
            row['vs'][c] = dict(NU=float(nc.mean()), LB_go=cg['lb'], UB95=c95['ub'])
            if c != 'RAWy': ok &= (cg['lb'] > 0)
            if c == 'RAWcv': ok &= (nc.mean() >= GO_K_NU)
            if nc.mean() < worst_v: worst_v = float(nc.mean()); worst_c = c
        row['best_competitor'] = worst_c; row['UB95_vs_best_competitor'] = row['vs'][worst_c]['UB95']; row['GO_pass'] = bool(ok)
        stop_all &= (row['UB95_vs_best_competitor'] < STOP_NU)
        if ok: go.append(a)
        res['candidates'][a] = row
    res['GO_candidates'] = go
    res['verdict'] = 'GO-dev' if go else ('STOP' if stop_all else 'INCONCLUSIVE')
    # report-only diagnostics
    rep = {}
    for t in TAUS:
        k = '%g' % t
        for a, b, name in ((f'XFERg_t{k}', f'RAWg_t{k}', f'CF1_selection_effect_equal_noise_t{k}'), (f'XFERg_t{k}', f'NS_t{k}', f'XFERg_vs_NS_t{k}'), (f'RAWg_t{k}', 'RAWy', f'info_loss_RAWg_vs_RAWy_t{k}'), (f'NS_t{k}', 'RAWy', f'NS_vs_RAWy_t{k}')):
            _, v_ = nu(U, a, b); rep[name] = dict(pooled=float(v_.mean()), per_type={tt: float(v_[types == tt].mean()) for tt in TYPES if (types == tt).any()})
    for a, b, name in (('RANDy', 'RAWy', 'RANDy_vs_RAWy'), ('RAWoracleR', 'RAWy', 'oracleR_vs_RAWy_nonimplementable'), ('RAWcv', 'RAWy', 'RAWcv_vs_RAWy'), ('RAWens2', 'RAWy', 'RAWens2_vs_RAWy'), ('XAVGctrl_t1', 'RAWy', 'XAVGctrl_vs_RAWy')):
        _, v_ = nu(U, a, b); rep[name] = dict(pooled=float(v_.mean()), per_type={tt: float(v_[types == tt].mean()) for tt in TYPES if (types == tt).any()})
    dg = {}
    for key in ('XFERg_t1_disp', 'XFERg_t4_disp', 'RAWg_t4_disp', 'NS_t4_disp', 'RAWy_disp', 'XFERg_t4_resid', 'RAWg_t4_resid', 'idx_overlap_t1', 'idx_overlap_y_t4'):
        vals = [np.mean(u['diag'][key]) for i in U for u in U[i].values() if key in u['diag']]; dg[key] = float(np.mean(vals)) if vals else None
    rep['diagnostics_mean'] = dg
    rep['Rstar_hist'] = {str(r): int(sum(u['Rstar'] == r for i in U for u in U[i].values())) for r in range(5)}
    rep['cost_fit_equiv_per_unit'] = float(np.mean([u['nfit'] for i in U for u in U[i].values()]))
    rep['K_by_arm'] = next(iter(U[imgs[0]].values()))['K']
    # pre-registered numeric predictions (report-only)
    p1 = res['candidates']['XFERg_t1']['NU_vs_RAWy']; p4 = res['candidates']['XFERg_t4']['per_type']; p4all = res['candidates']['XFERg_t4']['NU_vs_RAWy']
    rep['predictions'] = dict(NU_XFERg_t1_vs_RAWy=dict(observed=p1, predicted_range=[-1.0, -0.25], inside=bool(-1.0 <= p1 <= -0.25)),
                              NU_XFERg_t4_D1D2=dict(observed={k: p4.get(k) for k in ('D1', 'D2')}, predicted_range=[-0.10, 0.05], inside=bool(all((p4.get(k) is not None) and (-0.10 <= p4[k] <= 0.05) for k in ('D1', 'D2')))),
                              NU_XFERg_t4_pooled_negative=dict(observed=p4all, predicted='<0', inside=bool(p4all < 0)))
    res['report_only'] = rep
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('dirs', nargs='+'); ap.add_argument('--unit_report', default=str(ROOT / 'outputs' / 'cf_unit_tests_status.json')); ap.add_argument('--out', default=None)
    a = ap.parse_args()
    metas, U = load_units(a.dirs); attach_rcv(U)
    ur = json.loads(Path(a.unit_report).read_text(encoding='utf-8')) if Path(a.unit_report).exists() else None
    v = validity(metas, U, ur)
    pilot = metas[0]['stage'] == 'pilot'
    res = dict(dirs=a.dirs, stage=metas[0]['stage'], validity=v)
    debug = bool(metas[0].get('debug'))
    if not v['all_valid'] and not debug:
        res['verdict'] = 'INVALID'
    elif pilot:
        res['pilot'] = pilot_report(U, v); res['verdict'] = 'PILOT_OK (M_dev=%d%s)' % (res['pilot']['M_dev'], ', LIMITED_POWER' if res['pilot']['LIMITED_POWER'] else '')
    else:
        res.update(dev_analysis(U))
    if debug: res['verdict'] = 'DEBUG-NOT-EVIDENCE:' + res['verdict']
    outp = Path(a.out) if a.out else Path(a.dirs[0]) / 'analysis.json'
    outp.write_text(json.dumps(res, indent=1, default=float), encoding='utf-8')
    print(json.dumps({'verdict': res['verdict'], 'validity': {k: v[k] for k in v if k.startswith('V') or k == 'all_valid'}}, default=float))


if __name__ == '__main__':
    main()
