"""CA reducer (evaluator side). Contract CA candidate v1 sections 5-7 (v0 + Opus R1-R11). python3 experiments/ca_reduce.py <stage> [--block P] -> outputs/CA/<stage>_REDUCE.json/.txt
Unit = base image (mean over the 4 PSFs). Gap G_b(cell) = Q(OBS-J) - Q(control) [dB; Q = mean over the frozen W grid of PSNR vs the cell's truth]. cells = (rep in R0,R1) x (noise free, noisy).
Labels per cell (delta_D = 0.25 dB): D (deficit) iff BCa one-sided 95% UPPER bound of mean gap < -delta_D; E (no material deficit) iff BCa one-sided 95% LOWER bound > -delta_D; else I (indeterminate).
Verdict rules in priority order are in `verdict()`; they are applied to the primary control RND-J and, side by side, to the secondary controls IND1, OBS-I, SPA-J."""
import os, sys, json, glob, argparse
import numpy as np
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'src')); sys.path.insert(0, os.path.join(ROOT, 'experiments'))
from trn_same_state_reduce import bca
GRID = np.geomspace(1e9, 3e10, 8); BOOT = 10000; SEED = 20261109; DELTA_D = 0.25; TAUS = (4.0, 1.0)
EXPECTED = {'P': 1280, 'S': 768, 'X': 64}      # runs expected on the sealed stage (16 images x 4 PSFs x 4 cells x 5 arms; x 3 arms; X: 4 images x 4 PSFs x 2 cells x 2 arms)
CELLS = [('R0', 0), ('R0', 1), ('R1', 0), ('R1', 1)]; CTRL = ['RND-J', 'IND1', 'OBS-I', 'SPA-J']; PRIMARY = 'RND-J'


def cell_name(c): return '%s/%s' % (c[0], 'noisy' if c[1] else 'free')


def idx_at(W, B): return max(int(np.searchsorted(np.asarray(W), B, side='right')) - 1, 0)


def load(stage, block='P'):
    return [json.load(open(f)) for f in sorted(glob.glob(os.path.join(ROOT, 'outputs', 'CA', stage, 'runs', '*__%s.json' % block)))]


def metrics(r, F0, Fref):
    W = np.asarray(r['trajW'], float); ix = [idx_at(W, B) for B in GRID]; F = r['trajF']; ps = np.asarray(r['psnr']); res = np.asarray(r['resid'])
    out = dict(Q=float(np.mean(ps[ix])), peak=float(ps.max()), end=float(ps[-1]), Qedge=float(np.mean(np.asarray(r['psnr_edge'])[ix])), Qblur=float(np.mean(np.asarray(r['psnr_blur'])[ix])),
               O=float(np.mean([np.log10(max((F[i] - Fref) / (F0 - Fref), 1e-4)) for i in ix])), rej=r['rej'] / max(r['trials'], 1), stop=r['stop'], wall=r['wall'],
               logWpeak=float(np.log10(max(W[int(np.argmax(ps))], 1.0))))                                  # R11: where (in work W) the PSNR peak occurs
    for tau in TAUS:
        hit = np.where(res <= tau)[0]; out['Qfit%g' % tau] = float(ps[hit[0]]) if hit.size else np.nan
    out['nf'] = None if r['nf'] is None else float(np.mean(np.asarray(r['nf'])[ix])); out['mf'] = None if r['mf'] is None else float(np.mean(np.asarray(r['mf'])[ix]))
    out['proj'] = None if r['psnr_vs_proj'] is None else float(np.mean(np.asarray(r['psnr_vs_proj'])[ix]))
    return out


def table(runs):
    """-> (agg, meta, probm): agg[(img, rep, noisy, arm)] = metrics averaged over PSFs; meta[img] = rep_psnr/level/match; probm[(img, rep, noisy, arm)][psf] = per-problem metrics."""
    byprob = {}
    for r in runs: byprob.setdefault((r['img'], r['cond'], r['rep'], r['noisy']), []).append(r)
    per = {}; meta = {}; probm = {}
    for (img, cond, rep, nz), rs in byprob.items():
        Fref = min(r['minVF'] for r in rs); F0 = rs[0]['F0']
        for r in rs:
            m_ = metrics(r, F0, Fref); per.setdefault((img, rep, nz, r['armname']), []).append(m_); probm.setdefault((img, rep, nz, r['armname']), {})[cond] = m_
        meta[img] = dict(rep_psnr=rs[0]['rep_psnr'], level=rs[0]['level'], match=rs[0].get('match'))
    agg = {}
    for k, v in per.items():
        agg[k] = {m: (float(np.nanmean([d[m] for d in v])) if v[0][m] is not None and not isinstance(v[0][m], str) else None) for m in v[0] if m not in ('stop',)}; agg[k]['n'] = len(v)
        agg[k]['stops'] = {s: sum(1 for d in v if d['stop'] == s) for s in set(d['stop'] for d in v)}
    return agg, meta, probm


def bca_bounds(d):
    d = np.asarray(d, float); d = d[~np.isnan(d)]
    if d.size < 3 or np.allclose(d, d[0]): return float(d.mean()) if d.size else np.nan, np.nan, np.nan
    lo, hi = bca(d, stat=np.mean, B=BOOT, seed=SEED, alpha=0.10); return float(d.mean()), float(lo), float(hi)


def label(mean, lb, ub):
    if ub < -DELTA_D: return 'D'
    if lb > -DELTA_D: return 'E'
    return 'I'


def img_gap(probm, imgs, c, ctrl, metric, a='OBS-J'):
    """Per-image gap of `metric` (a minus ctrl), paired by problem (image x PSF): mean over the PSFs where both sides are defined; NaN if none (e.g. the matched-data-fit state was never reached)."""
    out = []
    for i in imgs:
        pa, pb = probm.get((i, c[0], c[1], a)), probm.get((i, c[0], c[1], ctrl))
        if pa is None or pb is None: out.append(np.nan); continue
        v = [pa[k][metric] - pb[k][metric] for k in pa if k in pb and pa[k].get(metric) is not None and pb[k].get(metric) is not None]; v = [x for x in v if not np.isnan(x)]
        out.append(float(np.mean(v)) if v else np.nan)
    return np.array(out)


def label_missing(d):
    """Label (D/E/I) of a per-image gap vector with the pre-registered missing-data rule: if more than 25% of the images lack the quantity the label is I."""
    d = np.asarray(d, float); miss = float(np.isnan(d).mean()); n = int((~np.isnan(d)).sum())
    if miss > 0.25 or n < 3: return dict(mean=float(np.nanmean(d)) if n else np.nan, LB5=np.nan, UB95=np.nan, label='I', missing=miss, n=n)
    m, lb, ub = bca_bounds(d); return dict(mean=m, LB5=lb, UB95=ub, label=label(m, lb, ub), missing=miss, n=n)


def qualify(lab_q, lab_p, lab_f):
    """Stop-time qualifier of every D cell of the Q-AUC verdict (Opus R1): STOP-EFFECT if the peak-PSNR gap (oracle best stopping) is E; PERSISTENT if both peak-PSNR gap and matched-data-fit gap are D; otherwise CONFOUNDED."""
    q = {}
    for c, l in lab_q.items():
        if l != 'D': continue
        q[c] = 'STOP-EFFECT' if lab_p[c] == 'E' else ('PERSISTENT' if (lab_p[c] == 'D' and lab_f[c] == 'D') else 'CONFOUNDED')
    return q


def qualify_summary(q):
    v = set(q.values()); return 'n/a' if not v else (next(iter(v)) if len(v) == 1 else 'MIXED')


def check_registration(stage, rec_path=None, files=None, tags=None):
    """R7: for the sealed stage the reducer and the bootstrap reference must be sha-registered in the freeze record (line-start lines 'REDUCER_SHA256 <sha> ca_reduce.py', 'REFERENCE_SHA256 <sha> trn_same_state_reduce.py ...') AND
    each such line must come BEFORE the first 'CONFIRM_UNSEALED' line (registered before the sealed read, Opus confirm check). tags/files may be overridden (ca_diag_run registers DIAG_SHA256 the same way)."""
    import hashlib
    if stage != 'confirm': return True
    rec_path = rec_path or os.path.join(ROOT, 'contracts', 'CA_FREEZE_RECORD.txt'); here = os.path.dirname(os.path.abspath(__file__))
    files = files or {'ca_reduce.py': os.path.join(here, 'ca_reduce.py'), 'trn_same_state_reduce.py': os.path.join(here, 'trn_same_state_reduce.py')}
    tags = tags or (('REDUCER_SHA256', 'ca_reduce.py'), ('REFERENCE_SHA256', 'trn_same_state_reduce.py'))
    assert os.path.exists(rec_path), 'reduce(confirm): no freeze record'; rec = [l.strip() for l in open(rec_path, encoding='utf-8').read().splitlines() if l.strip()]
    unsealed = [k for k, l in enumerate(rec) if l.startswith('CONFIRM_UNSEALED')]; assert unsealed, 'reduce(confirm): no CONFIRM_UNSEALED line'
    for tag, name in tags:
        sha = hashlib.sha256(open(files[name], 'rb').read()).hexdigest()
        at = [k for k, l in enumerate(rec) if l.split()[:2] == [tag, sha]]
        assert at, 'reduce(confirm): %s of %s not registered in the freeze record (changed after freeze?)' % (tag, name)
        assert min(at) < unsealed[0], 'reduce(confirm): %s line comes after the first CONFIRM_UNSEALED line (must be registered before the sealed read)' % tag
    return True


def verdict(lab, I_ub, N_ub=None, R_ub=None):
    """lab: dict cell->'D'/'E'/'I'. Priority rules (pre-registered, contract section 7):
    1 V-NONE  all four cells E (no cell D and none I)                                    : the JR deficit is not replicated under the common fixed configuration (no D with any I -> V-INS)
    2 V-OPT   (R0,free)=D                                                                : deficit survives without noise and with exact representation (grouping/optimisation effect at this budget)
    3 V-N     (R0,noisy)=D & (R1,noisy)=D & (R1,free)!=D                                 : noise-conditional (see the stop-time qualifier; 'noise interaction' only when PERSISTENT)
    4 V-R     (R1,free)=D & (R1,noisy)=D & (R0,noisy)!=D                                 : representation-conditional (rep + HF content; see qualifiers)
    5 V-NR    (R1,noisy)=D only (others not D) and interaction-contrast upper bound < 0  : needs both factors
    6 V-CO    (R0,noisy)=D & (R1,free)=D & (R1,noisy)=D & (R0,free)!=D                   : both single factors act
    7 V-INS   anything else                                                              : evidence insufficient
    STRONG iff every cell the rule requires to be non-D is labelled E (not merely I); otherwise TENTATIVE (V-OPT and V-INS: STRONG/TENTATIVE as below)."""
    f0, n0, f1, n1 = lab['R0/free'], lab['R0/noisy'], lab['R1/free'], lab['R1/noisy']; nD = [f0, n0, f1, n1].count('D')
    strong = lambda *cells: 'STRONG' if all(c == 'E' for c in cells) else 'TENTATIVE'
    if nD == 0: return ('V-NONE', 'STRONG') if all(c == 'E' for c in (f0, n0, f1, n1)) else ('V-INS', 'TENTATIVE')       # no D is only 'no deficit' if every cell is E; a mix of E and I cannot exclude a deficit
    if f0 == 'D': return 'V-OPT', 'STRONG'
    if n0 == 'D' and n1 == 'D' and f1 != 'D': return 'V-N', strong(f0, f1)
    if f1 == 'D' and n1 == 'D' and n0 != 'D': return 'V-R', strong(f0, n0)
    if n1 == 'D' and n0 != 'D' and f1 != 'D':
        if I_ub is not None and I_ub < 0: return 'V-NR', strong(f0, n0, f1)
        return 'V-INS', 'TENTATIVE'
    if n0 == 'D' and f1 == 'D' and n1 == 'D': return 'V-CO', strong(f0)
    return 'V-INS', 'TENTATIVE'


def inconclusive_reason(stage, block, n_runs, base=None):
    """Contract section 11: on the sealed stage a block with a CAP_EXCEEDED marker or an incomplete run count is INCONCLUSIVE (no partial verdict)."""
    if stage != 'confirm': return None
    mk = os.path.join(base or os.path.join(ROOT, 'outputs', 'CA', 'confirm'), 'CAP_EXCEEDED_%s.txt' % block)
    if os.path.exists(mk): return 'CAP_EXCEEDED marker present'
    if n_runs != EXPECTED.get(block, n_runs): return 'incomplete block: %d of %d runs' % (n_runs, EXPECTED[block])
    return None


def reduce(stage, block='P'):
    check_registration(stage); runs = load(stage, block); agg, meta, probm = table(runs); imgs = sorted({k[0] for k in agg}); out = dict(stage=stage, block=block, n_images=len(imgs), n_runs=len(runs), images=imgs, meta=meta, arms={}, gaps={}, verdicts={}, mechanism={}, notes=[])
    inconc = inconclusive_reason(stage, block, len(runs))
    out['inconclusive'] = inconc
    arms = sorted({k[3] for k in agg}); cellarm = {}
    for c in CELLS:
        for a in arms:
            v = [agg[(i, c[0], c[1], a)] for i in imgs if (i, c[0], c[1], a) in agg]
            if v: cellarm[(c, a)] = {m: float(np.nanmean([d[m] for d in v])) for m in ('Q', 'peak', 'end', 'Qedge', 'Qblur', 'O', 'rej', 'wall') } | {'stops': {s: sum(d['stops'].get(s, 0) for d in v) for s in {s for d in v for s in d['stops']}}}
    out['arms'] = {'%s|%s' % (cell_name(c), a): v for (c, a), v in cellarm.items()}
    def G(ctrl, c, m='Q'): return np.array([agg[(i, c[0], c[1], 'OBS-J')][m] - agg[(i, c[0], c[1], ctrl)][m] for i in imgs if (i, c[0], c[1], 'OBS-J') in agg and (i, c[0], c[1], ctrl) in agg])
    for ctrl in CTRL:
        if not all((i, r, n, ctrl) in agg for i in imgs for (r, n) in CELLS): continue
        g = {}; lab = {}
        for c in CELLS:
            d = G(ctrl, c); m, lb, ub = bca_bounds(d); g[cell_name(c)] = dict(mean=m, LB5=lb, UB95=ub, wins=int((d > 0).sum()), n=int(d.size), sd=float(d.std(ddof=1)), label=label(m, lb, ub), per_image=[float(v) for v in d]); lab[cell_name(c)] = g[cell_name(c)]['label']
        gm = {cell_name(c): G(ctrl, c) for c in CELLS}
        Nb = 0.5 * ((gm['R0/noisy'] - gm['R0/free']) + (gm['R1/noisy'] - gm['R1/free'])); Rb = 0.5 * ((gm['R1/noisy'] - gm['R0/noisy']) + (gm['R1/free'] - gm['R0/free']))
        Ib = (gm['R1/noisy'] - gm['R0/noisy']) - (gm['R1/free'] - gm['R0/free'])
        con = {}
        # R5: secondary contrast R_eval = 1/2 sum over noise of [ gap vs the projection x_G in the R1 cell - gap in the R0 cell ]: separates 'the DATA contain an unrepresentable component' from 'the TRUTH itself is harder'
        Gp1 = {nz: img_gap(probm, imgs, ('R1', nz), ctrl, 'proj') for nz in (0, 1)}
        Re = 0.5 * ((Gp1[1] - gm['R0/noisy']) + (Gp1[0] - gm['R0/free']))
        for nm, d in (('N_effect(noise)', Nb), ('R_effect(rep+HF content)', Rb), ('I_interaction', Ib), ('R_eval(data misfit, truth=x_G; secondary)', Re)):
            m, lb, ub = bca_bounds(d); con[nm] = dict(mean=m, LB5=lb, UB95=ub, sd=float(np.nanstd(d, ddof=1)), MDE80=float((1.645 + 0.8416) * np.nanstd(d, ddof=1) / np.sqrt(np.sum(~np.isnan(d)))), per_image=[float(v) for v in d])
        v, s = verdict(lab, con['I_interaction']['UB95'])
        if inconc: v, s = 'INCONCLUSIVE', inconc
        # R1: stop-time labels (peak PSNR = oracle best stop; PSNR at the first state with residual ratio <= 1 = matched data fit; missing-data rule 25%)
        gp = {cell_name(c): label_missing(img_gap(probm, imgs, c, ctrl, 'peak')) for c in CELLS}; gf = {cell_name(c): label_missing(img_gap(probm, imgs, c, ctrl, 'Qfit1')) for c in CELLS}
        qual = qualify(lab, {k: x['label'] for k, x in gp.items()}, {k: x['label'] for k, x in gf.items()})
        out['gaps'][ctrl] = dict(cells=g, contrasts=con, peak_cells=gp, fit_cells=gf); out['verdicts'][ctrl] = dict(verdict=v, strength=s, labels=lab, qualifiers=qual, qualifier_summary=qualify_summary(qual))
        # supportive outcomes (secondary metrics, same sign convention: OBS-J minus control)
        if ctrl == PRIMARY:
            sup = {}
            for m in ('peak', 'end', 'Qedge', 'Qblur', 'O', 'Qfit4', 'Qfit1', 'nf', 'mf', 'proj', 'logWpeak'):
                for c in CELLS:
                    try:
                        d = np.array([agg[(i, c[0], c[1], 'OBS-J')][m] - agg[(i, c[0], c[1], ctrl)][m] for i in imgs]) if all(agg[(i, c[0], c[1], 'OBS-J')].get(m) is not None for i in imgs) else None
                    except KeyError: d = None
                    if d is not None and not np.all(np.isnan(d)): mm, lb, ub = bca_bounds(d); sup['%s|%s' % (m, cell_name(c))] = dict(mean=mm, LB5=lb, UB95=ub, n=int((~np.isnan(d)).sum()))
            out['mechanism'] = sup
    ms = [meta[i]['match'] for i in imgs if meta[i].get('match')]
    if ms: out['match_stats'] = {k: dict(mean=float(np.mean([m[k] for m in ms])), min=float(np.min([m[k] for m in ms])), max=float(np.max([m[k] for m in ms]))) for k in ms[0]}
    # descriptive decomposition pairs (no verdict): where does the joint-vs-independent / grouping-rule difference sit in the 2x2?  Gap = Q(a) - Q(b)
    out['decomp'] = {}
    for a_, b_ in (('RND-J', 'IND1'), ('SPA-J', 'RND-J'), ('OBS-I', 'IND1'), ('OBS-J', 'SPA-J')):
        if not all((i, r, n, x) in agg for i in imgs for (r, n) in CELLS for x in (a_, b_)): continue
        dd = {cell_name(c): np.array([agg[(i, c[0], c[1], a_)]['Q'] - agg[(i, c[0], c[1], b_)]['Q'] for i in imgs]) for c in CELLS}
        rec = {cn: dict(zip(('mean', 'LB5', 'UB95'), bca_bounds(d))) for cn, d in dd.items()}
        Nb = 0.5 * ((dd['R0/noisy'] - dd['R0/free']) + (dd['R1/noisy'] - dd['R1/free'])); Ib = (dd['R1/noisy'] - dd['R0/noisy']) - (dd['R1/free'] - dd['R0/free'])
        rec['N_effect(noise)'] = dict(zip(('mean', 'LB5', 'UB95'), bca_bounds(Nb))); rec['I_interaction'] = dict(zip(('mean', 'LB5', 'UB95'), bca_bounds(Ib))); out['decomp']['%s - %s' % (a_, b_)] = rec
    rp = np.array([meta[i]['rep_psnr'] for i in imgs]); out['rep_psnr'] = dict(mean=float(rp.mean()), min=float(rp.min()), max=float(rp.max()), per_image={str(i): meta[i]['rep_psnr'] for i in imgs})
    if PRIMARY in out['gaps']:
        from scipy.stats import spearmanr
        Ib = np.array(out['gaps'][PRIMARY]['contrasts']['R_effect(rep+HF content)']['per_image']); ge = np.array([meta[i]['match']['grad_energy_ratio'] if meta[i].get('match') else np.nan for i in imgs])
        out['dose_response_R_effect'] = dict(spearman_vs_neg_rep_psnr=float(spearmanr(-rp, Ib)[0]) if len(imgs) > 3 else None, spearman_vs_grad_energy_ratio=float(spearmanr(ge, Ib, nan_policy='omit')[0]) if len(imgs) > 3 and not np.isnan(ge).all() else None,
                                                  note='descriptive; x1 = -rep_psnr (larger = more representation error); x2 = gradient-energy ratio R0/R1 (smaller = R0 smoother)')
    json.dump(out, open(os.path.join(ROOT, 'outputs', 'CA', '%s_REDUCE_%s.json' % (stage, block)), 'w'), indent=1, default=float)
    L = ['CA reduce %s block %s: %d images, %d runs; rep_psnr mean %.1f (min %.1f max %.1f)' % (stage, block, len(imgs), len(runs), out['rep_psnr']['mean'], out['rep_psnr']['min'], out['rep_psnr']['max']), '']
    if 'match_stats' in out: L.append('R0-vs-R1 matching (descriptive): ' + '; '.join('%s %.3f [%.3f, %.3f]' % (k, v['mean'], v['min'], v['max']) for k, v in out['match_stats'].items())); L.append('')
    L.append('Q-AUC [dB] by cell and arm (mean over images):'); L.append('%-14s' % 'cell' + ''.join('%10s' % a for a in arms))
    for c in CELLS: L.append('%-14s' % cell_name(c) + ''.join('%10.2f' % cellarm[(c, a)]['Q'] if (c, a) in cellarm else '%10s' % '-' for a in arms))
    for ctrl, d in out['gaps'].items():
        L += ['', 'GAP OBS-J - %s (dB; BCa 90%% two-sided = one-sided 95%% bounds; D if UB<-%.2f, E if LB>-%.2f):' % (ctrl, DELTA_D, DELTA_D)]
        for cn, g in d['cells'].items(): L.append('  %-10s mean %+.3f  LB5 %+.3f  UB95 %+.3f  wins %d/%d  sd %.2f  -> %s' % (cn, g['mean'], g['LB5'], g['UB95'], g['wins'], g['n'], g['sd'], g['label']))
        for cn, g in d['contrasts'].items(): L.append('  %-18s mean %+.3f  LB5 %+.3f  UB95 %+.3f  sd %.2f  MDE80 %.2f' % (cn, g['mean'], g['LB5'], g['UB95'], g['sd'], g['MDE80']))
        L.append('  VERDICT (%s): %s %s' % (ctrl, out['verdicts'][ctrl]['verdict'], out['verdicts'][ctrl]['strength']))
        L.append('  wording rule (contract section 7): the words "noise interaction" are authorised only when every D cell below is PERSISTENT; STOP-EFFECT = earlier crossing of the PSNR peak, not worse grouping/repair; CONFOUNDED = stop-time confound not excluded')
        L.append('  stop-time labels (peak-PSNR gap | matched-fit gap): ' + '  '.join('%s %s(%+.2f)|%s(%+.2f)' % (cn, d['peak_cells'][cn]['label'], d['peak_cells'][cn]['mean'], d['fit_cells'][cn]['label'], d['fit_cells'][cn]['mean']) for cn in d['cells']))
        L.append('  stop-time qualifier of the D cells (R1): %s %s' % (out['verdicts'][ctrl]['qualifier_summary'], out['verdicts'][ctrl]['qualifiers']))
    if out['decomp']:
        L += ['', 'Descriptive decomposition pairs (Q-AUC gap a - b, dB; no verdict):']
        for k, rec in out['decomp'].items(): L.append('  %-14s ' % k + '  '.join('%s %+.2f[%+.2f,%+.2f]' % (cn.replace('(', '').replace(')', '')[:11], g['mean'], g['LB5'], g['UB95']) for cn, g in rec.items()))
    if out['mechanism']:
        L += ['', 'Supportive outcomes (OBS-J - %s):' % PRIMARY]
        for k, g in out['mechanism'].items(): L.append('  %-18s mean %+.3f  LB5 %+.3f  UB95 %+.3f  n=%d' % (k, g['mean'], g['LB5'], g['UB95'], g['n']))
    open(os.path.join(ROOT, 'outputs', 'CA', '%s_REDUCE_%s.txt' % (stage, block)), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L)); return out


def reduce_X(stage):
    """Block X (10x budget, descriptive; 4 images x 4 PSFs x cells (R0,free),(R0,noisy) x {OBS-J, RND-J}): PSNR at the matched work W=3e10, at the end of the long run, the peak, and where the peak occurs; per-image gaps (n small: no labels)."""
    check_registration(stage); runs = load(stage, 'X'); rows = {}; inc = inconclusive_reason(stage, 'X', len(runs))
    for r in runs:
        W = np.asarray(r['trajW'], float); ps = np.asarray(r['psnr']); k0 = idx_at(W, 3e10)
        rows.setdefault((r['img'], r['rep'], r['noisy'], r['armname']), []).append(dict(at3e10=float(ps[k0]), end=float(ps[-1]), peak=float(ps.max()), logWpeak=float(np.log10(max(W[int(np.argmax(ps))], 1.0))), Wend=float(W[-1]), stop=r['stop']))
    imgs = sorted({k[0] for k in rows}); out = dict(stage=stage, block='X', images=imgs, n_runs=len(runs), inconclusive=inc, cells={})
    for rep, nz in (('R0', 0), ('R0', 1)):
        cn = cell_name((rep, nz)); rec = {}
        for m in ('at3e10', 'end', 'peak', 'logWpeak'):
            d = np.array([np.mean([x[m] for x in rows[(i, rep, nz, 'OBS-J')]]) - np.mean([x[m] for x in rows[(i, rep, nz, 'RND-J')]]) for i in imgs if (i, rep, nz, 'OBS-J') in rows and (i, rep, nz, 'RND-J') in rows])
            rec[m] = dict(mean=float(d.mean()), per_image=[float(v) for v in d])
        rec['stops'] = {s_: sum(1 for k, v in rows.items() if k[1] == rep and k[2] == nz for x in v if x['stop'] == s_) for s_ in {x['stop'] for v in rows.values() for x in v}}; out['cells'][cn] = rec
    json.dump(out, open(os.path.join(ROOT, 'outputs', 'CA', '%s_REDUCE_X.json' % stage), 'w'), indent=1, default=float)
    L = ['CA reduce %s block X (10x budget, descriptive; OBS-J - RND-J gaps, dB; log10 W at peak for logWpeak): %d images, %d runs' % (stage, len(imgs), len(runs))]
    if inc: L.append('  INCONCLUSIVE (%s): numbers below are partial and must not be interpreted' % inc)
    for cn, rec in out['cells'].items(): L.append('  %-9s ' % cn + '  '.join('%s %+.2f %s' % (m, rec[m]['mean'], np.round(rec[m]['per_image'], 2).tolist()) for m in ('at3e10', 'end', 'peak', 'logWpeak')) + '  stops %s' % rec['stops'])
    open(os.path.join(ROOT, 'outputs', 'CA', '%s_REDUCE_X.txt' % stage), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L)); return out


def reduce_A(stage='dev'):
    """DEV-only block A (descriptive, Opus R10): noisy cells, {OBS-J, RND-J}, a = 1e-2/SN^2 (block A) vs a = 1e-3/SN^2 (block P): gaps in Q-AUC, peak, end, logWpeak."""
    assert stage != 'confirm', 'block A is DEV-only'
    ra, rp_ = load(stage, 'A'), load(stage, 'P'); aggA, _, _ = table(ra); aggP, _, _ = table([r for r in rp_ if r['armname'] in ('OBS-J', 'RND-J') and r['noisy'] == 1]); imgs = sorted({k[0] for k in aggA}); out = {}; L = ['CA block A (DEV-only, descriptive): OBS-J - RND-J in the noisy cells at a=1e-3/SN^2 (block P) vs a=1e-2/SN^2 (block A); %d images' % len(imgs)]
    for rep in ('R0', 'R1'):
        for nm, agg in (('a=1e-3', aggP), ('a=1e-2', aggA)):
            rec = {}
            for m in ('Q', 'peak', 'end', 'logWpeak'):
                d = np.array([agg[(i, rep, 1, 'OBS-J')][m] - agg[(i, rep, 1, 'RND-J')][m] for i in imgs if (i, rep, 1, 'OBS-J') in agg and (i, rep, 1, 'RND-J') in agg]); rec[m] = dict(mean=float(d.mean()), per_image=[float(v) for v in d])
            out['%s %s' % (rep, nm)] = rec; L.append('  %s noisy %s: ' % (rep, nm) + '  '.join('%s %+.3f' % (m, rec[m]['mean']) for m in rec))
    json.dump(out, open(os.path.join(ROOT, 'outputs', 'CA', '%s_REDUCE_A.json' % stage), 'w'), indent=1, default=float); open(os.path.join(ROOT, 'outputs', 'CA', '%s_REDUCE_A.txt' % stage), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L)); return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('stage'); ap.add_argument('--block', default='P'); a = ap.parse_args()
    if a.block == 'X': reduce_X(a.stage)
    elif a.block == 'A': reduce_A(a.stage)
    else: reduce(a.stage, a.block)
