"""Analysis for contract v3 (fission + covariance df). usage: python experiments/f3_analyze.py <outputs/F3-...> --unit_report outputs/unit_tests_status.json [--allow_debug]
Writes <dir>/analysis.json and ANALYSIS.md. Pure numpy (no scipy). Estimators are importable for unit tests."""
import argparse, json, hashlib, math, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
B_BOOT = 1000
BOOT_SEED = 20261106   # entropy; resampling stream = spawn_key (13,) (contract C4)


def _legs(d, which):
    """which: 'full' -> (Fp,Fm); 'sdf' -> (Fp-Gp, Fm-Gm); 'par' -> (Gp, Gm). arrays (M,N)."""
    if which == 'full': return d['Fp'], d['Fm']
    if which == 'sdf': return d['Fp'] - d['Gp'], d['Fm'] - d['Gm']
    if which == 'par': return d['Gp'], d['Gm']
    raise ValueError(which)


def df_stat(Xp, Xm, ep, em, sig2, W=None):
    """centred covariance df of the (Xp,Xm) legs: Sum_m[(Xp-Xbar).ep + (Xm-Xbar).em] / ((M-1) 2 sig2) (contract C1). W: optional (B,M) resample weights -> returns (B,) statistics."""
    M = Xp.shape[0]
    if W is None:
        W = np.full((1, M), 1.0 / M)
    dp = np.einsum('mn,mn->m', Xp, ep); dm = np.einsum('mn,mn->m', Xm, em)
    t = W @ (dp + dm) - np.einsum('bn,bn->b', W @ Xp, W @ ep) - np.einsum('bn,bn->b', W @ Xm, W @ em)
    return t * (M / (M - 1.0)) / (2.0 * sig2)      # C1: Sum_m[.]/((M-1)*2 sig'^2) (unbiased sample covariance; e has known mean 0)


class Boot:
    def __init__(self, M, B=B_BOOT, seed=BOOT_SEED):
        rng = np.random.default_rng(np.random.SeedSequence(entropy=seed, spawn_key=(13,)))
        idx = rng.integers(0, M, size=(B, M))
        W = np.zeros((B, M))
        for b in range(B): W[b] = np.bincount(idx[b], minlength=M) / M
        self.W = W


def est(d, which, sig2, boot):
    Xp, Xm = _legs(d, which)
    pt = float(df_stat(Xp, Xm, d['ep'], d['em'], sig2)[0])
    bs = df_stat(Xp, Xm, d['ep'], d['em'], sig2, W=boot.W)
    return pt, float(np.std(bs, ddof=1))


def load(dirp):
    cells = {}
    for f in sorted(Path(dirp).glob('*.npz')):
        parts = f.stem.split('__'); kind, img, S, impl = parts[0], parts[1], int(parts[2][1:]), parts[3]
        z = np.load(f); cells[(kind, img, S, impl)] = {k: z[k] for k in z.files}
    return cells


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('dir'); ap.add_argument('--unit_report', default=''); ap.add_argument('--allow_debug', action='store_true'); ap.add_argument('--plin_wall_s', type=float, default=0.0, help='pilot_m128 only: P-lin wall seconds from the first pilot analysis (res.wall.plin_wall_s)')
    a = ap.parse_args(); dirp = Path(a.dir)
    meta = json.loads((dirp / 'meta.json').read_text(encoding='utf-8-sig'))
    if meta.get('debug') and not a.allow_debug: print('debug run: pass --allow_debug (never evidence)'); sys.exit(2)
    cells = load(dirp); cfg = meta['cfg']; s0 = cfg['sigma0']; sig2 = 2 * s0 * s0
    stage = meta['stage']; M_run = meta['M']
    want = (ROOT / 'contracts' / 'F0_CONTRACT_v3.sha256').read_text().split()[0] if (ROOT / 'contracts' / 'F0_CONTRACT_v3.sha256').exists() else None
    gates = {}; notes = []; res = {'dir': str(dirp), 'stage': stage}
    gates['contract_hash_matches_frozen'] = (want is not None and meta['contract_sha256'] == want) or bool(meta.get('debug'))
    # V1 unit tests
    if a.unit_report and Path(a.unit_report).exists():
        ur = json.loads(Path(a.unit_report).read_text(encoding='utf-8-sig')); gates['V1_unit_tests'] = bool(ur.get('passed'))
    else:
        gates['V1_unit_tests'] = False; notes.append('no unit-test report -> V1 fails')
    gates['run_not_aborted'] = meta.get('aborted') is None
    # V2 identities
    full_cells = {k: v for k, v in cells.items() if k[0] == 'full'}
    v2 = True; v2d = {}
    for k, v in full_cells.items():
        ok_replay = bool(np.all(v['replay_ok'])); ok_idx = bool(np.all(v['idx_equal'])) if k[2] == 8 else True
        v2d['%s_S%d' % (k[1], k[2])] = dict(replay_ok=ok_replay, idx_equal_S8=ok_idx, n=int(len(v['Fp'])))
        v2 = v2 and ok_replay and ok_idx
        if k[2] == 8 and 'g_ran' in v:
            ran = v['g_ran'].astype(bool)
            v2 = v2 and bool(np.array_equal(v['Gp'][ran], v['Fp'][ran]) and np.array_equal(v['Gm'][ran], v['Fm'][ran]))
    gates['V2_identities'] = v2; res['V2_detail'] = v2d
    # main estimates
    table = {}; boots = {}
    for (kind, img, S, impl), v in sorted(full_cells.items()):
        M = len(v['Fp']); boots.setdefault(M, Boot(M)); bt = boots[M]
        dfull, sefull = est(v, 'full', sig2, bt); sdf, sesdf = est(v, 'sdf', sig2, bt); dpar, separ = est(v, 'par', sig2, bt)
        row = dict(M=M, df_full=dfull, se_df_full=sefull, sdf=sdf, se_sdf=sesdf, df_par=dpar, se_df_par=separ)
        if 'A' in v:
            Mk = len(v['Fp']); c = ((v['Fp'] - v['Fp'].mean(0)) * v['ep']).sum(1) / sig2 * (Mk / (Mk - 1.0))
            an = ((v['Fp'] - v['A']) * v['ep']).sum(1) / (2 * sig2)
            dd = c - an; row['df_cov_Fplus'] = float(c.mean()); row['df_anti'] = float(an.mean()); row['P3_diff_mean'] = float(dd.mean()); row['P3_diff_se'] = float(dd.std(ddof=1) / math.sqrt(M))
            boots_p3 = dd
        table['%s_S%d' % (img, S)] = row
    res['table'] = table
    # P1 precision / M extrapolation (S=1024 sdf)
    p1 = {}; need_M = []
    for key, row in table.items():
        if key.endswith('_S1024'):
            rel = row['se_sdf'] / abs(row['df_par']) if row['df_par'] else float('inf')
            req = None
            for Mc in (32, 64, 128):
                if rel * math.sqrt(row['M'] / Mc) <= 0.015: req = Mc; break
            p1[key] = dict(se_over_dfpar=rel, M_required=req); need_M.append(req)
    res['P1_detail'] = p1
    gates['P1_precision_ok_at_run_M'] = bool(p1) and all(v['se_over_dfpar'] <= 0.015 for v in p1.values())
    # P2 P-lin
    plin = {k: v for k, v in cells.items() if k[0] == 'plin'}; p2 = {}; p2a = True; p2b = None; extra = []
    for (kind, img, S, impl), v in sorted(plin.items()):
        M = len(v['Fp']); boots.setdefault(M, Boot(M)); bt = boots[M]
        sdf, sesdf = est(v, 'sdf', sig2, bt); dpar, separ = est(v, 'par', sig2, bt); dfull, sefull = est(v, 'full', sig2, bt)
        p2['%s_S%d' % (img, S)] = dict(df_full=dfull, sdf=sdf, se_sdf=sesdf, df_par=dpar, se_df_par=separ, rank_mean=float(np.mean(v['rank_p'])))
        if S in (8, 1024) and img in ('W0', 'E1'):                 # contract section 6 P2(a): W0 and E1 only (same rule at pilot and Stage 1; D-03)
            p2a = p2a and abs(dpar - 24.0) <= 2 * separ
        elif S in (8, 1024) and img != 'W1':                          # Stage-1 extra P-lin images: report only, never gated (D-03)
            extra.append(abs(dpar - 24.0) <= 2 * separ)
        if img == 'W0' and S == 1024: p2b = (sdf, sesdf)
    res['P2_plin'] = p2
    if extra: res['P2a_extra_images_report_only'] = dict(n_checked=len(extra), n_within_2se=int(sum(extra)))
    gates['P2a_plin_frozen_df_eq_24'] = bool(plin) and p2a
    if p2b is not None:
        tol = 3 * math.sqrt(p2b[1] ** 2 + 0.83 ** 2); gates['P2b_plin_W0_search_df_about_65'] = abs(p2b[0] - 65.6) <= tol; res['P2b'] = dict(sdf=p2b[0], se=p2b[1], tol=tol)
    else:
        gates['P2b_plin_W0_search_df_about_65'] = False
    # P3 (pilot): antithetic vs random covariance, pooled over images, per S
    if stage == 'pilot':
        p3 = {}; p3ok = True
        for S in (8, 1024):
            ds = []
            for (kind, img, SS, impl), v in full_cells.items():
                if SS == S and 'A' in v:
                    Mk = len(v['Fp']); c = ((v['Fp'] - v['Fp'].mean(0)) * v['ep']).sum(1) / sig2 * (Mk / (Mk - 1.0)); an = ((v['Fp'] - v['A']) * v['ep']).sum(1) / (2 * sig2); ds.append(c - an)
            if ds:
                dd = np.concatenate(ds); m_, se_ = float(dd.mean()), float(dd.std(ddof=1) / math.sqrt(len(dd))); p3[str(S)] = dict(mean_diff=m_, se=se_, ok=abs(m_) <= 2 * se_); p3ok = p3ok and abs(m_) <= 2 * se_
            else: p3ok = False
        res['P3_detail'] = p3; gates['P3_anti_vs_cov'] = p3ok
        # P4: fast vs torch
        tk = [k for k in cells if k[0] == 'tfull']
        if tk:
            kt = tk[0]; vt = cells[kt]; vf = cells[('full', kt[1], kt[2], 'fast')]; m = len(vt['Fp'])
            mt = vt['m_index']; mf = vf['m_index']; sel = np.isin(mf, mt)
            def percov(v, idx):
                Mk = len(idx); return (((v['Fp'][idx] - v['Fp'][idx].mean(0)) * v['ep'][idx]).sum(1) + ((v['Fm'][idx] - v['Fm'][idx].mean(0)) * v['em'][idx]).sum(1)) / (2 * sig2) * (Mk / (Mk - 1.0))
            dd = percov(vf, np.where(sel)[0]) - percov(vt, np.arange(m)); mm, se = float(dd.mean()), float(dd.std(ddof=1) / math.sqrt(len(dd)))
            res['P4_detail'] = dict(mean_diff=mm, se=se, n=len(dd), rel_diff_report_only=mm / max(abs(float(percov(vf, np.where(sel)[0]).mean())), 1e-12), df_fast=float(percov(vf, np.where(sel)[0]).mean()), df_torch=float(percov(vt, np.arange(m)).mean()))
            gates['P4_fast_vs_torch'] = abs(mm) <= 2.5 * se
        else:
            gates['P4_fast_vs_torch'] = False
    # P5 wall (evaluated at the M selected by P1; contract C2)
    def n1_fits(M, scen):
        if scen == 'full': return 12 * M * 6 + 12 * 2 * 4
        if scen == 'a': return 12 * M * 4 + 12 * 1 * 4          # fallback (a): no S=8 fits
        return 8 * M * 4 + 8 * 1 * 4                            # fallback (b): E3..E10, no S=8
    plin_img = {'full': 15, 'a': 15, 'b': 11}
    rate = meta.get('n_fits_per_s') or 0.0
    der = rate * (0.8 if meta.get('wall_s', 0) < 600 else 1.0)
    plin_t = sum(float(np.sum(v['unit_wall_s'])) for k, v in cells.items() if k[0] == 'plin') / max(meta['workers'], 1)
    if stage == 'pilot_m128': plin_t = float(a.plin_wall_s)
    res['wall'] = dict(rate_fits_per_s=rate, rate_used=der, run_wall_s=meta.get('wall_s'), plin_wall_s=plin_t)
    def proj(M, scen): return (n1_fits(M, scen) / der + plin_t * plin_img[scen] / 3.0) if der > 0 else float('inf')
    CAP = 3.5 * 3600
    def p5_decide(M):
        pr = {sc: proj(M, sc) for sc in ('full', 'a', 'b')}; res['stage1_wall_projection_s'] = {'M': M, **pr}
        for sc, tag in (('full', 'PROCEED Stage 1 --M=%d'), ('a', 'PROCEED Stage 1 --M=%d --fallback=a (drop S=8 fits; C2(a))'), ('b', 'PROCEED Stage 1 --M=%d --fallback=b (E3..E10, no S=8, sign rule >=6/8; C2(b))')):
            if pr[sc] <= CAP: return (tag % M) + ' (projected wall %.0f s)' % pr[sc]
        return 'INCONCLUSIVE -> STOP (C2(c): projected Stage-1 wall > 3.5 h even after fallbacks (a),(b)); no other redesign allowed'
    wallcap = str(meta.get('aborted') or '').startswith('WALL_CAP')
    # decision (contract section 7, C2 order: validity gates -> P1 -> P5)
    base = ['contract_hash_matches_frozen', 'V1_unit_tests', 'V2_identities'] + ([] if wallcap else ['run_not_aborted'])
    if stage == 'pilot':
        inval = [g for g in base + ['P2a_plin_frozen_df_eq_24', 'P2b_plin_W0_search_df_about_65', 'P3_anti_vs_cov', 'P4_fast_vs_torch'] if not gates.get(g)]
        okM = [m for m in need_M if m is not None]
        if wallcap: decision = 'P5 FAIL: pilot wall-cap abort is not INVALID (C2). Gates on the partial data failing: %s. Wall-based fallback verdict: %s' % (inval or 'none', p5_decide(max(okM) if okM else 128))
        elif inval: decision = 'INVALID (fix implementation defects only; one rerun; estimand unchanged): ' + ', '.join(inval)
        elif any(m is None for m in need_M) or not need_M: decision = 'P1_SHORT: run the C2 M=128 rerun (--stage=pilot_m128: E1,E2, S=1024, F+-,G+- only, own 60-min cap); if still short -> INCONCLUSIVE, STOP estimator line (no-v4)'
        else: decision = p5_decide(max(okM))
    elif stage == 'pilot_m128':
        inval = [g for g in base if not gates.get(g)]
        if inval: decision = 'INVALID in the M=128 rerun counts as the SECOND INVALID -> STOP estimator line (C2): ' + ', '.join(inval)
        elif not gates['P1_precision_ok_at_run_M']: decision = 'INCONCLUSIVE (P1 still short at M=128) -> STOP estimator line (no-v4)'
        else: decision = p5_decide(128)
    else:
        inval = [g for g in base + ['P2a_plin_frozen_df_eq_24', 'P2b_plin_W0_search_df_about_65'] if not gates.get(g)]
        imgs = sorted({k[1] for k in full_cells if k[2] == 1024}); s_img = np.array([table['%s_S1024' % i]['sdf'] for i in imgs]); p_img = np.array([table['%s_S1024' % i]['df_par'] for i in imgs])
        pooled = float(s_img.mean()); se_pool = float(s_img.std(ddof=1) / math.sqrt(len(imgs))) if len(imgs) > 1 else float('nan'); thr = max(3 * se_pool, 0.05 * float(p_img.mean()))
        npos = int(np.sum(s_img > 0)); need_pos = 9 if len(imgs) == 12 else (6 if len(imgs) == 8 else int(math.ceil(0.75 * len(imgs))))
        res['H1'] = dict(n_images=len(imgs), pooled_sdf=pooled, se_pooled_between_images=se_pool, threshold=thr, df_par_star=float(p_img.mean()), n_positive=npos, need_positive=need_pos, per_image={i: dict(sdf=float(sv), df_par=float(pv)) for i, sv, pv in zip(imgs, s_img, p_img)})
        res['P1_stage1_report_only'] = dict(n_images_over_0p015=int(sum(v['se_over_dfpar'] > 0.015 for v in p1.values())), n_images=len(p1))   # D-03: P1 is a pilot gate (contract section 6); not a Stage-1 validity gate
        if inval: decision = 'NOT JUDGED (validity/precision gates failed): ' + ', '.join(inval)
        else:
            hold = (pooled >= thr) and (npos >= need_pos)
            decision = 'H1 HOLDS (development evidence: search yields sdf>0 in the toy; write H2 contract, ask Opus)' if hold else 'STOP (K1-v3): estimator line stops, no redefinition (no-v4)'
    res['gates'] = gates; res['notes'] = notes; res['decision'] = decision
    (dirp / 'analysis.json').write_text(json.dumps(res, indent=1, default=float), encoding='utf-8')
    md = ['# F3 analysis (contract v3)', '', 'dir: %s | stage: %s | M: %s | debug: %s' % (dirp, stage, M_run, meta.get('debug')), 'contract sha256: %s' % meta.get('contract_sha256'), '', '**DECISION: %s**' % decision, '', '## Gates']
    md += ['- %s: %s' % (k, v) for k, v in gates.items()]
    md += ['', '## Table (full legs; sigma\'^2 = 2 sigma0^2)', '```', json.dumps(table, indent=1, default=float), '```', '## P1', '```', json.dumps(p1, indent=1, default=float), '```']
    for k in ('P3_detail', 'P4_detail', 'P2b', 'wall', 'stage1_wall_projection_s', 'H1', 'P1_stage1_report_only', 'P2a_extra_images_report_only'):
        if k in res: md += ['## ' + k, '```', json.dumps(res[k], indent=1, default=float), '```']
    md += ['## P-lin', '```', json.dumps(p2, indent=1, default=float), '```']
    (dirp / 'ANALYSIS.md').write_text('\n'.join(md), encoding='utf-8')
    print(decision)


if __name__ == '__main__':
    main()
