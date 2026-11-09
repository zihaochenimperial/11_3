"""F0 analysis for the FROZEN contract v2 (contracts/F0_CONTRACT.md). numpy only.
usage: python experiments/f0_analyze.py outputs/F0-<stage>-<tag> [--unit_report outputs/unit_tests_status.json] [--allow_debug]
Writes analysis.json and ANALYSIS.md into the output dir. Implements: sdf = df_oracle^rand - df_frozen (paired bootstrap over m, noise/omega common across S),
validity gates V1-V7 + replay/determinism + R7, H1/H2 (stage full), pilot decision rules of section 7 (stage pilot / pilot128). Pure post-processing of stored arrays."""
import argparse, glob, hashlib, json, os, sys
from pathlib import Path
import numpy as np

B_BOOT = 1000
SEED = 20261105
EPS_REL = (0.01, 0.03, 0.1, 0.3, 1.0)
FIT_EQUIV_FULL = 41000


def load(d):
    cells = {}
    for p in sorted(glob.glob(os.path.join(d, '*.npz'))):
        kind, img, S, x = os.path.basename(p)[:-4].split('__')
        z = np.load(p, allow_pickle=False)
        cells[(kind, img, int(S[1:]), int(x[1:]))] = {k: z[k] for k in z.files}
    return cells


class Boot:
    """paired bootstrap over m with a shared index matrix per sample size"""
    def __init__(self, M, B=B_BOOT, seed=SEED):
        self.M = M; self.B = B
        idx = np.random.default_rng(seed).integers(0, M, size=(B, M))
        self.C = np.stack([np.bincount(r, minlength=M) for r in idx]).astype(np.float64)

    def df(self, G, s2):
        M = self.M; diag = np.diag(G)
        point = (np.trace(G) - G.sum() / M) / (M * s2)
        bt = ((self.C @ diag) - ((self.C @ G) * self.C).sum(1) / M) / (M * s2)
        return point, bt

    def mean(self, v):
        v = np.asarray(v, dtype=np.float64)
        return v.mean(), (self.C @ v) / self.M


def cell_df(c, s2, boot):
    G = c['F'] @ c['E'].T
    return boot.df(G, s2)


def sdf_cell(c, s2, boot, fdcol=0):
    p, bt = cell_df(c, s2, boot)
    fm, fbt = boot.mean(c['FD'][:, fdcol])
    return dict(df=p, df_se=float(bt.std()), fd=float(fm), sdf=float(p - fm), sdf_b=bt - fbt, df_b=bt, sdf_se=float((bt - fbt).std()))


def contrast(a, b):
    d = a['sdf'] - b['sdf']; db = a['sdf_b'] - b['sdf_b']
    return dict(delta=float(d), se=float(db.std()), z=float(d / max(db.std(), 1e-300)), upper95=float(d + 1.645 * db.std()), lower95=float(d - 1.645 * db.std()))


def slope(cells_by_S, Ss):
    l = np.log2(np.array(Ss, dtype=float)); lc = l - l.mean()
    pt = sum(lc[i] * cells_by_S[S]['sdf'] for i, S in enumerate(Ss)) / (lc ** 2).sum()
    bt = sum(lc[i] * cells_by_S[S]['sdf_b'] for i, S in enumerate(Ss)) / (lc ** 2).sum()
    return float(pt), float(np.percentile(bt, 5))


def v6_ok(r, M):
    return abs(r['sdf']) <= max(3 * r['sdf_se'], 0.03 * r['df'])


def analyze(d, a):
    meta = json.loads(Path(d, 'meta.json').read_text(encoding='utf-8'))
    out = dict(dir=str(d), stage=meta['stage'], debug=meta.get('debug', False), contract_sha256=meta.get('contract_sha256'), aborted=meta.get('aborted'), gates={}, notes=[])
    if meta.get('debug') and not a.allow_debug:
        raise SystemExit('refusing to analyze a DEBUG run (never evidence); pass --allow_debug for a pipeline smoke test only')
    s0 = meta['cfg']['sigma0']; s2 = s0 ** 2
    cells = load(d); spec = meta['stage_spec']; stage = meta['stage']
    imgs = spec['images']; Ss = spec['S']; M = spec['M']
    G = out['gates']
    # contract hash must match the recorded frozen hash
    frozen = Path(os.path.dirname(os.path.abspath(__file__)), '..', 'contracts', 'F0_CONTRACT.sha256').read_text().split()[0]
    G['contract_hash_matches_frozen'] = bool(meta.get('contract_sha256') == frozen)
    # V1 unit-test report
    if a.unit_report and os.path.exists(a.unit_report):
        ur = json.loads(Path(a.unit_report).read_text(encoding='utf-8-sig')); G['V1_unit_tests'] = bool(ur.get('passed'))
    else:
        G['V1_unit_tests'] = None; out['notes'].append('V1 unit-test report missing -> verdict cannot be a scientific conclusion')
    # V2 determinism + replay (R1)
    det = [c for k, c in cells.items() if k[0] == 'det']
    G['V2_determinism'] = bool(det) and all(bool(c['det_f_ok'].all()) and bool(c['det_pert_ok'].all()) for c in det)
    rep = [bool(c['replay_ok'].all()) for k, c in cells.items() if 'replay_ok' in c]
    G['R1_replay_bitwise_all_m'] = bool(rep) and all(rep)
    # main cells
    R = {}
    boot = Boot(M)
    for img in imgs:
        for S in Ss:
            c = cells.get(('main', img, S, 0))
            if c is None or len(c['F']) != M: out['notes'].append('missing/partial main cell %s S=%d' % (img, S)); continue
            R[(img, S)] = sdf_cell(c, s2, boot, fdcol=(1 if len(c['FD'][0]) > 1 else 0))
    n0 = {}
    for img in imgs:
        c = cells.get(('n0', img, 0, 0))
        if c is not None:
            bn = Boot(len(c['F'])); n0[img] = sdf_cell(c, s2, bn, fdcol=0)
    # V6
    G['V6_S8_and_N0_sdf_zero'] = bool(R) and all(v6_ok(R[(i, 8)], M) for i in imgs if (i, 8) in R) and bool(n0) and all(v6_ok(n0[i], M) for i in n0)
    out['V6_detail'] = {i: dict(S8=_pub(R.get((i, 8))), N0=_pub(n0.get(i))) for i in imgs}
    # P-lin V3 + V7
    pl = {}
    for img in spec['plin_images']:
        cs = {S: cells.get(('plin', img, S, 0)) for S in spec['plin_S']}
        if any(v is None for v in cs.values()): continue
        bp = Boot(len(cs[8]['F'])); pl[img] = {S: sdf_cell(cs[S], s2, bp, 0) for S in spec['plin_S']}
        pl[img]['rank_mean'] = float(np.mean([cs[S]['rank'].mean() for S in spec['plin_S']]))
    plc = {i: contrast(pl[i][1024], pl[i][8]) for i in pl}
    G['V3_plin_W0_trend_gt_4SE'] = bool('W0' in plc and plc['W0']['delta'] > 4 * plc['W0']['se'])
    out['plin'] = {i: dict(contrast_1024_minus_8=plc[i], sdf={S: _pub(pl[i][S]) for S in spec['plin_S']}, rank_mean=pl[i]['rank_mean']) for i in pl}
    v7 = [c for k, c in cells.items() if k[0] == 'v7']
    if v7:
        tr = np.concatenate([c['trace'] for c in v7]); rk = np.concatenate([c['rank'] for c in v7]).astype(float)
        G['V7_plin_exact_fd_equals_rank_1e-6'] = bool(np.all(np.abs(tr - rk) / rk <= 1e-6) and np.all(rk == 24))
        out['V7_detail'] = dict(max_rel_err=float(np.max(np.abs(tr - rk) / rk)), ranks=sorted(set(rk.astype(int).tolist())))
    else:
        G['V7_plin_exact_fd_equals_rank_1e-6'] = None
    # R7 eps_f check (pilot stages)
    if len(spec['epsf']) == 3:
        r7 = {}
        for S in Ss:
            c = cells.get(('main', imgs[0], S, 0))
            if c is None: continue
            fd = c['FD']; df = R[(imgs[0], S)]['df']
            diffs = {'%g-%g' % (spec['epsf'][i], spec['epsf'][j]): float(abs((fd[:, i] - fd[:, j]).mean())) for i in range(3) for j in range(i + 1, 3)}
            r7[S] = dict(max_pair_mean_diff=max(diffs.values()), diffs=diffs, df=df, ok=bool(max(diffs.values()) <= 0.01 * df), fd_means=[float(fd[:, i].mean()) for i in range(3)])
        out['R7'] = r7
        G['R7_eps_f_within_1pct'] = bool(r7) and all(v['ok'] for v in r7.values())
    # antithetic (secondary)
    out['antithetic_secondary'] = {}
    for (img, S), r in R.items():
        c = cells[('main', img, S, 0)]; an = c['ANTI']; ok = ~np.isnan(an)
        if ok.any():
            fdc = c['FD'][:, (1 if c['FD'].shape[1] > 1 else 0)]
            out['antithetic_secondary']['%s_S%d' % (img, S)] = dict(n=int(ok.sum()), df_anti=float(an[ok].mean()), se=float(an[ok].std(ddof=1) / np.sqrt(ok.sum())), sdf_anti=float(an[ok].mean() - fdc[ok].mean()), df_rand=r['df'], df_rand_se=r['df_se'])
    # contrasts / H1 pieces
    S_lo, S_hi = min(Ss), max(Ss)
    h1 = {}
    for img in imgs:
        if (img, S_lo) in R and (img, S_hi) in R:
            ct = contrast(R[(img, S_hi)], R[(img, S_lo)])
            row = dict(sdf_by_S={S: _pub(R[(img, S)]) for S in Ss if (img, S) in R}, contrast=ct, df_hi=R[(img, S_hi)]['df'])
            row['H1a'] = bool(ct['delta'] > 4 * ct['se'] and ct['delta'] > 0.05 * R[(img, S_hi)]['df'])
            if len(Ss) >= 3 and all((img, S) in R for S in Ss):
                sl, lo = slope({S: R[(img, S)] for S in Ss}, Ss); row['slope'] = sl; row['slope_lo95'] = lo; row['H1c'] = bool(lo > 0)
            h1[img] = row
    out['H1_table'] = h1
    # conv report (R6)
    conv = {}
    for img in imgs:
        cs = {S: cells.get(('conv', img, S, 0)) for S in (8, 1024)}
        if all(v is not None for v in cs.values()):
            bc = Boot(len(cs[8]['F'])); rc = {S: sdf_cell(cs[S], s2, bc, 0) for S in (8, 1024)}
            ct = contrast(rc[1024], rc[8]); conv[img] = dict(contrast_2x=ct, H1a_2x=bool(ct['delta'] > 4 * ct['se'] and ct['delta'] > 0.05 * rc[1024]['df']), sdf_2x={S: _pub(rc[S]) for S in rc})
    out['R6_conv_2x_steps'] = conv
    if conv and 'D1' in h1:
        out['R6_budget_dependent'] = bool(conv['D1']['H1a_2x'] != h1['D1']['H1a'])
    # fix family report
    fx = {}
    for img in imgs:
        for S in Ss:
            dfs = []
            for k in range(spec.get('fixw', 0)):
                c = cells.get(('fix', img, S, k))
                if c is not None: dfs.append(cell_df(c, s2, Boot(len(c['F'])))[0])
            if dfs: fx['%s_S%d' % (img, S)] = dict(df_fix=[float(v) for v in dfs], spread=float(np.ptp(dfs)))
    out['fix_family_report'] = fx
    # MC / H2 pieces
    mc = {}
    for img in imgs:
        for S in Ss:
            c = cells.get(('main', img, S, 0))
            if c is None or (img, S) not in R: continue
            D = c['DIV']; rows = {}
            for ei in range(5):
                col = D[:, ei, :]
                if np.isnan(col[:, 0]).all(): continue
                m64 = ~np.isnan(col[:, 0]) & ~np.isnan(col[:, 1])
                if m64.sum() >= 4:
                    mean_j = col[m64].mean(1); allv = col[m64].ravel()
                    rows[ei] = dict(n_J2=int(m64.sum()), mean=float(mean_j.mean()), sd1_sq=float(allv.var(ddof=1)), se_J2=float(mean_j.std(ddof=1) / np.sqrt(m64.sum())), sd_J2_rel=float(mean_j.std(ddof=1) / R[(img, S)]['df']))
                j0 = col[:, 0][~np.isnan(col[:, 0])]
                if len(j0) >= 4: rows.setdefault(ei, {}).update(n_J1=int(len(j0)), mean_J1=float(j0.mean()), se_J1=float(j0.std(ddof=1) / np.sqrt(len(j0))))
            mc[(img, S)] = rows
    out['MC_report'] = {'%s_S%d' % k: v for k, v in mc.items()}
    # V4 (full): T3 identity at eps in {0.3,1.0}, S in {8,256}
    v4 = {}
    if stage == 'full':
        for img in imgs:
            for S in spec.get('sigma_S', ()):
                for ei in (3, 4):
                    cs = cells.get(('sigma', img, S, ei)); cm = mc.get((img, S), {}).get(ei)
                    if cs is None or cm is None or 'n_J1' not in cm: v4['%s_S%d_e%g' % (img, S, EPS_REL[ei])] = dict(status='MISSING'); continue
                    sp = float(cs['sigma_prime'][0]); p, bt = cell_df(cs, sp ** 2, Boot(len(cs['F'])))
                    diff = cm['mean_J1'] - p; se = float(np.hypot(cm['se_J1'], bt.std()))
                    status = 'PASS' if (abs(diff) <= 0.02 * p and se <= 0.01 * p) else ('SE_EXCEEDED(A2)' if se > 0.01 * p else 'FAIL')
                    v4['%s_S%d_e%g' % (img, S, EPS_REL[ei])] = dict(div_mean=cm['mean_J1'], df_sigma_prime=float(p), diff=float(diff), rel_diff=float(diff / p), se=se, rel_se=float(se / p), n_div=cm['n_J1'], n_oracle=len(cs['F']), status=status)
        st = [v['status'] for v in v4.values()]
        G['V4_T3_identity'] = (None if not st else ('PENDING_A2' if (all(s in ('PASS', 'SE_EXCEEDED(A2)') for s in st) and 'SE_EXCEEDED(A2)' in st) else all(s == 'PASS' for s in st)))
    out['V4_detail'] = v4
    # H2 (only meaningful if H1 passes)
    h2 = {}
    if stage == 'full':
        for img in imgs:
            hi = mc.get((img, S_hi), {}); lo = mc.get((img, S_lo), {})
            if (img, S_hi) not in R: continue
            df = R[(img, S_hi)]['df']; best = None; rows = {}
            for ei, r in hi.items():
                if 'sd1_sq' not in r or ei not in lo or 'sd1_sq' not in lo[ei]: continue
                bias = abs(r['mean'] - df) / df; exc = (r['sd1_sq'] - lo[ei]['sd1_sq']) / df ** 2; sej = r['se_J2'] / df
                ok = bool(bias <= 0.05 and exc <= 0.01 and sej <= 0.05)
                rows[EPS_REL[ei]] = dict(rel_bias=float(bias), excess_var_over_df2=float(exc), se_J2_rel=float(sej), sd_J2_rel_single_sample=r['sd_J2_rel'], ok=ok)
                if ok and best is None: best = EPS_REL[ei]
            h2[img] = dict(eps_rows=rows, eps_star=best, adequate=bool(best is not None), cost_fits_per_sample=3)
    out['H2_table'] = h2
    # ---------------- decisions
    hard = [G['contract_hash_matches_frozen'], G['V1_unit_tests'], G['V2_determinism'], G['R1_replay_bitwise_all_m'], G['V6_S8_and_N0_sdf_zero'], G['V3_plin_W0_trend_gt_4SE'], G['V7_plin_exact_fd_equals_rank_1e-6']]
    if 'R7_eps_f_within_1pct' in G: hard.append(G['R7_eps_f_within_1pct'])
    if stage == 'full': hard.append(G.get('V4_T3_identity'))
    invalid = [k for k, v in G.items() if v is False]
    pending = [k for k, v in G.items() if v is None or v == 'PENDING_A2']
    if out['aborted']: invalid.append('RUN_ABORTED:' + str(out['aborted']))
    out['invalid_reasons'] = invalid; out['pending_gates'] = pending
    dec = None
    if stage in ('pilot', 'pilot128'):
        img = imgs[0]; n_per = sum(float(c['unit_wall_s'].sum()) for k, c in cells.items() if k[0] in ('main', 'n0')); nfit = sum(int(c['n_fits'].sum()) for k, c in cells.items() if k[0] in ('main', 'n0'))
        per_fit = n_per / max(nfit, 1); proj_wall = per_fit * FIT_EQUIV_FULL / max(meta['workers'], 1)
        ct = contrast(R[(img, S_hi)], R[(img, S_lo)]); z_proj = ct['delta'] / (ct['se'] * np.sqrt(M / 256.0)) if ct['se'] > 0 else float('nan')
        df_hi = R[(img, S_hi)]['df']
        plin_ok = bool(G['V3_plin_W0_trend_gt_4SE'] and G['V7_plin_exact_fd_equals_rank_1e-6'])
        stop = bool(ct['upper95'] < 0.02 * df_hi and plin_ok)
        rec = {}
        for ei in (3, 4):
            a_ = mc.get((img, S_hi), {}).get(ei); n_ = None
            c = cells.get(('n0', img, 0, 0))
            if c is not None and a_ is not None:
                col = c['DIV'][:, ei, :]; m64 = ~np.isnan(col).any(1)
                if m64.sum() >= 4:
                    sd1n = float(col[m64].ravel().var(ddof=1)); sejn = float(col[m64].mean(1).std(ddof=1) / np.sqrt(m64.sum()))
                    rec[EPS_REL[ei]] = dict(excess_var_real_minus_N0_over_df2=float((a_['sd1_sq'] - sd1n) / df_hi ** 2), N0_se_J2_projected_M64_rel=float(sejn * np.sqrt(m64.sum() / 64.0) / df_hi), N0_se_J2_projected_M256_rel=float(sejn * np.sqrt(m64.sum() / 256.0) / df_hi))
        out['pilot'] = dict(effect=ct, z_proj=float(z_proj), df_hi=df_hi, equivalence_upper95_lt_0p02df=bool(ct['upper95'] < 0.02 * df_hi), plin_pass=plin_ok, per_fit_s=per_fit, projected_stage1_wall_s=proj_wall, record_only_rule7=rec)
        if invalid: dec = 'INVALID (no scientific conclusion): ' + ', '.join(invalid)
        elif pending: dec = 'PENDING_GATES: ' + ', '.join(pending)
        elif stop: dec = 'STOP_K1 (equivalence: upper95 of sdf(%d)-sdf(%d) < 0.02 df and P-lin pass)' % (S_hi, S_lo) + (' [ANOMALY: significantly NEGATIVE search effect, lower95=%.2f < -0.02 df: not a clean null; Opus must review before acting]' % ct['lower95'] if ct['lower95'] < -0.02 * df_hi else '')
        elif not (z_proj >= 4): dec = ('REDESIGN_POWER -> rerun pilot ONCE as pilot128 (M=128) per C2' if stage == 'pilot' else 'INCONCLUSIVE (underpowered at budget): no K1 claim; no escalation to Stage 1 or GPU (C2)')
        elif proj_wall > 4 * 3600: dec = 'REDESIGN_WALL (projected Stage 1 wall %.0f s > 4 h; C1 overrides PROCEED)' % proj_wall
        else: dec = 'PROCEED to Stage 1 (after A1 records eps_f)'
    else:
        h1pass_imgs = [i for i, r in h1.items() if r.get('H1a') and r.get('H1c')]
        h1ok = len(h1pass_imgs) >= 2
        h2imgs = [i for i, r in h2.items() if r['adequate']]
        out['H1_pass_images'] = h1pass_imgs; out['H2_adequate_images'] = h2imgs
        if invalid: dec = 'INVALID (no K conclusion): ' + ', '.join(invalid)
        elif pending: dec = 'PENDING_GATES: ' + ', '.join(pending)
        elif not h1ok: dec = 'STOP_K1 (H1 failed on >=2 of 3 images; report upper CI of sdf contrast)'
        elif len(h2imgs) >= 2: dec = 'K2: transplanted full-pipeline MC adequate on >=2 images -> no new-correction claim; submit to Opus for revise/stop'
        else: dec = 'H1 PASS and H2 NOT adequate -> draft F1 contract (decomposed estimator M1); requires Opus gate before any GPU'
        if out.get('R6_budget_dependent'): dec += ' [label: budget-dependent (R6)]'
    out['decision'] = dec
    return out


def _pub(r):
    if r is None: return None
    return dict(df=r['df'], df_se=r['df_se'], fd=r['fd'], sdf=r['sdf'], sdf_se=r['sdf_se'])


def md(out):
    L = ['# F0 analysis (frozen contract v2)', '', 'dir: %s | stage: %s | debug: %s' % (out['dir'], out['stage'], out['debug']), 'contract sha256: %s' % out['contract_sha256'], '', '**DECISION: %s**' % out['decision'], '', '## Gates']
    for k, v in out['gates'].items(): L.append('- %s: %s' % (k, v))
    if out['invalid_reasons']: L.append('- INVALID reasons: %s' % out['invalid_reasons'])
    if out['notes']: L += ['', '## Notes'] + ['- ' + n for n in out['notes']]
    if 'pilot' in out:
        p = out['pilot']; L += ['', '## Pilot rule quantities', '- effect sdf(hi)-sdf(lo): %.3f +- %.3f (z=%.2f); z_proj(256)=%.2f; df_hi=%.2f' % (p['effect']['delta'], p['effect']['se'], p['effect']['z'], p['z_proj'], p['df_hi']),
              '- equivalence upper95 = %.3f vs 0.02 df = %.3f -> %s' % (p['effect']['upper95'], 0.02 * p['df_hi'], p['equivalence_upper95_lt_0p02df']), '- P-lin pass: %s' % p['plin_pass'],
              '- per-fit %.2f s; projected Stage-1 wall %.0f s (cap 14400)' % (p['per_fit_s'], p['projected_stage1_wall_s']), '- record-only rule 7: %s' % json.dumps(p['record_only_rule7'])]
    for name in ('H1_table', 'H2_table', 'V4_detail', 'R7', 'R6_conv_2x_steps', 'plin', 'V6_detail'):
        if out.get(name): L += ['', '## ' + name, '```', json.dumps(out[name], indent=1, default=float)[:6000], '```']
    return '\n'.join(L)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('dir'); ap.add_argument('--unit_report', default=''); ap.add_argument('--allow_debug', action='store_true')
    a = ap.parse_args()
    out = analyze(a.dir, a)
    Path(a.dir, 'analysis.json').write_text(json.dumps(out, indent=1, default=float), encoding='utf-8')
    Path(a.dir, 'ANALYSIS.md').write_text(md(out), encoding='utf-8')
    print(out['decision']); print(json.dumps(out['gates'], default=str))
