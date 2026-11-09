"""CA E-B diagnostics (design stage: constructed pairs, no images, no seeds except the MC check) and instance-level merge load (stage 'load', reads the cached R0 fits of a stage).
python3 experiments/ca_diag_run.py design        -> outputs/CA/EB_design.json / .txt
python3 experiments/ca_diag_run.py load <stage>  -> outputs/CA/<stage>_EB_load.json / .txt   (stage in dev/smoke/confirm; confirm reads only the cache written by the sealed run)
Outcomes here never enter the CA verdict (they are the 'parallel diagnostics' of the contract: tables of when finite ambiguity exists at all)."""
import os, sys, json, glob
import numpy as np
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, os.path.join(ROOT, 'src'))
import ca_diag as D, ca_gen as CG, geo_core as GC
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
N = 32; SN = D.SN
ORI = [0, 30, 60, 90, 120, 150]; SW = [1.2, 1.5, 2.0]; SFR = [0.5, 0.8, 1.0, 1.3, 1.6, 1.8]


def line_pair_table():
    rows = []
    for pn in CG.PSF_ORDER:
        op = CG.make_op(pn)
        for o in ORI:
            for sw in SW:
                for fr in SFR:
                    s = fr * sw
                    if s >= 2 * sw - 1e-9: continue
                    one, two = D.line_pair(sw=sw, s=s, phi=np.deg2rad(o)); m = D.measures(op, GC.render(one, N), GC.render(two, N)); m.update(psf=pn, ori=o, sw=sw, s=s, sigma_star=m['d'] * SN / D.D_THR if m['d'] > 0 else None); rows.append(m)
    return rows


def edge_gap_table():
    """Continuous step edge of length 20 (smooth profile 1 px) vs the same edge with a gap of g px (an interrupted edge); x0 = interrupted, x1 = continuous."""
    ss = 4; g_ = (np.arange(N * ss) + 0.5) / ss; X, Y = np.meshgrid(g_, g_, indexing='xy'); rows = []
    def edge(ang, gap):
        c, s_ = np.cos(ang), np.sin(ang); u = (X - 16) * c + (Y - 16) * s_; v = -(X - 16) * s_ + (Y - 16) * c
        prof = 0.5 * (1 + np.tanh(v / 1.0)) * 0.5 * (np.tanh((u + 10) / 1.0) - np.tanh((u - 10) / 1.0))
        if gap > 0: prof = np.where((np.abs(u) < gap / 2) & (np.abs(v) < 2.5), 0.5, prof)       # gap: the step is replaced by its mean level in a window of length `gap`
        return prof.reshape(N, ss, N, ss).mean((1, 3))
    for pn in CG.PSF_ORDER:
        op = CG.make_op(pn)
        for o in [0, 45, 90, 135]:
            for gap in [1, 2, 3, 4, 6]:
                m = D.measures(op, edge(np.deg2rad(o), gap), edge(np.deg2rad(o), 0)); m.update(psf=pn, ori=o, gap=gap); rows.append(m)
    return rows


def texture_table():
    ux, uy = np.meshgrid(np.arange(N) + .5, np.arange(N) + .5, indexing='xy'); env = np.exp(-0.5 * ((ux - 16) ** 2 + (uy - 16) ** 2) / 25.0); rows = []
    def gab(f, ang): return 0.5 + 0.4 * env * np.cos(2 * np.pi * f * ((ux - 16) * np.cos(ang) + (uy - 16) * np.sin(ang)))
    for pn in CG.PSF_ORDER:
        op = CG.make_op(pn)
        for f in [0.1, 0.2, 0.3]:
            for da in [10, 20, 45, 90]:
                m = D.measures(op, gab(f, 0.0), gab(f, np.deg2rad(da))); m.update(psf=pn, freq=f, dang=da); rows.append(m)
    return rows


def reparam_controls():
    """Same rendered image from different parameters (D_img must be 0 -> never ambiguous)."""
    th = np.array([[1.0, 14.0, 16.0, np.log(1.6), 0.2, np.log(2.2)], [0.8, 20.0, 15.0, np.log(2.0), -0.3, np.log(1.4)]]); rows = []
    split = np.vstack([th[0:1] * np.array([0.5, 1, 1, 1, 1, 1]), th[0:1] * np.array([0.5, 1, 1, 1, 1, 1]), th[1:2]]); swapped = th[::-1].copy()
    for pn in CG.PSF_ORDER:
        op = CG.make_op(pn)
        for nm, b in (('order swap', swapped), ('weight split', split)):
            m = D.measures(op, GC.render(th, N), GC.render(b, N)); m.update(psf=pn, ctrl=nm); rows.append(m)
    return rows


def spectrum_table():
    """Weakest whitened observability: single members alone vs group tangent space (fixed neighbours) vs neighbours refit; linear d vs finite d along the merge direction."""
    rows = []; rng = np.random.default_rng(5)
    nbr = np.stack([[0.6, 7.0, 8.0, np.log(1.8), 0.0, np.log(1.8)], [0.5, 25.0, 9.0, np.log(2.0), 0.0, np.log(1.5)], [0.7, 8.0, 25.0, np.log(1.6), 0.1, np.log(2.4)], [0.5, 24.0, 24.0, np.log(2.2), 0.0, np.log(2.2)]])
    for pn in CG.PSF_ORDER:
        op = CG.make_op(pn)
        for o in [0, 60, 120]:
            for s in [1.6, 2.2, 2.8]:
                one, two = D.line_pair(sw=1.5, s=s, phi=np.deg2rad(o)); th = np.vstack([two, nbr]); wk = D.weakest_single_vs_group(op, two, thN=nbr)
                rows.append(dict(psf=pn, ori=o, s=s, single_min=float(min(wk['single_min'])), group_fixed_min=float(wk['group_fixed'][0]), group_refit_min=float(wk['group_refit'][0]), n_gauge=wk['n_gauge'], n_tangent=wk['n_tangent']))
    return rows


def mc_check(n_trials=40000):
    """Monte-Carlo check of the two-simple-hypotheses error Phi(-d/2) with the exact likelihood-ratio test on a few constructed pairs."""
    rows = []; rng = np.random.default_rng(11)
    for pn, o, s in [('AG', 120, 2.6), ('AG', 120, 1.8), ('G15', 0, 2.6), ('MO', 90, 2.4), ('DK', 60, 2.8)]:
        op = CG.make_op(pn); one, two = D.line_pair(sw=1.5, s=s, phi=np.deg2rad(o)); mu0 = op.apply(GC.render(one, N)).ravel(); mu1 = op.apply(GC.render(two, N)).ravel(); dvec = mu1 - mu0; d = float(np.linalg.norm(dvec) / SN)
        z = rng.standard_normal((n_trials, mu0.size)) * SN; mid = 0.5 * (mu0 + mu1)
        y0 = mu0 + z; y1 = mu1 + z        # equal priors; LRT: decide H1 iff <y - mid, dvec> > 0
        e = 0.5 * float(np.mean((y0 - mid) @ dvec > 0)) + 0.5 * float(np.mean((y1 - mid) @ dvec <= 0))
        rows.append(dict(psf=pn, ori=o, s=s, d=d, bayes_formula=D.bayes_error(d), mc_error=e, mc_se=float(np.sqrt(e * (1 - e) / n_trials))))
    return rows


def summarize(rows, keys):
    L = []
    for r in rows: L.append('  ' + '  '.join('%s=%s' % (k, ('%.3g' % r[k]) if isinstance(r[k], float) else r[k]) for k in keys))
    return L


def design():
    out = dict(line_pair=line_pair_table(), edge_gap=edge_gap_table(), texture=texture_table(), reparam=reparam_controls(), spectrum=spectrum_table(), mc=mc_check())
    json.dump(out, open(os.path.join(ROOT, 'outputs', 'CA', 'EB_design.json'), 'w'), indent=1, default=float)
    L = ['CA E-B design-stage tables (constructed pairs; sigma=%.3f; ambiguous iff rel>=%.2f and d<=%.1f)' % (SN, D.D_MIN_REL, D.D_THR), '']
    lp = out['line_pair']; L.append('Line pairs (single wide vs matched-moment two thin): %d pairs, %d ambiguous' % (len(lp), sum(r['amb'] for r in lp)))
    for pn in CG.PSF_ORDER:
        sub = [r for r in lp if r['psf'] == pn]; a = [r for r in sub if r['amb']]
        L.append('  %s: %d/%d ambiguous; orientations with any ambiguous pair: %s; min d %.2f max d %.2f' % (pn, len(a), len(sub), sorted({r['ori'] for r in a}), min(r['d'] for r in sub), max(r['d'] for r in sub)))
    eg = out['edge_gap']; L.append('Edge-gap pairs: %d pairs, %d ambiguous; by PSF %s' % (len(eg), sum(r['amb'] for r in eg), {pn: sum(r['amb'] for r in eg if r['psf'] == pn) for pn in CG.PSF_ORDER}))
    tx = out['texture']; L.append('Texture-orientation pairs: %d pairs, %d ambiguous; by PSF %s' % (len(tx), sum(r['amb'] for r in tx), {pn: sum(r['amb'] for r in tx if r['psf'] == pn) for pn in CG.PSF_ORDER}))
    rp = out['reparam']; L.append('Reparametrisation negative controls: max D_img %.2e, max d %.2e, ambiguous %d (must be 0)' % (max(r['Dimg'] for r in rp), max(r['d'] for r in rp), sum(r['amb'] for r in rp)))
    L.append('Spectra (weakest whitened observability, group tangent space gauge-removed):'); sp = out['spectrum']
    for pn in CG.PSF_ORDER:
        sub = [r for r in sp if r['psf'] == pn]; L.append('  %s: single_min %.3g..%.3g  group_fixed_min %.3g..%.3g  group_refit_min %.3g..%.3g' % (pn, min(r['single_min'] for r in sub), max(r['single_min'] for r in sub), min(r['group_fixed_min'] for r in sub), max(r['group_fixed_min'] for r in sub), min(r['group_refit_min'] for r in sub), max(r['group_refit_min'] for r in sub)))
    L.append('MC check of Phi(-d/2):'); L += summarize(out['mc'], ['psf', 'ori', 's', 'd', 'bayes_formula', 'mc_error', 'mc_se'])
    open(os.path.join(ROOT, 'outputs', 'CA', 'EB_design.txt'), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L))


def load(stage):
    if stage == 'confirm':                  # sealed-stage reads of the cache require this runner to be sha-registered before CONFIRM_UNSEALED (Opus confirm check)
        import ca_reduce as R; R.check_registration('confirm', files={'ca_diag_run.py': os.path.abspath(__file__)}, tags=(('DIAG_SHA256', 'ca_diag_run.py'),))
    fits = {int(os.path.basename(f)[4:-5]): json.load(open(f)) for f in sorted(glob.glob(os.path.join(ROOT, 'outputs', 'CA', stage, 'fits', 'fit_*.json')))}; out = {}
    for i, f in fits.items():
        th = np.array(f['theta']); per = {}
        for pn in CG.PSF_ORDER:
            rows, n, sk = D.merge_load(CG.make_op(pn), th); per[pn] = dict(n_pairs=len(rows), n_amb=n, n_skipped_signed=sk, min_d=min([r['d'] for r in rows]) if rows else None)
        out[str(i)] = dict(level=f.get('level'), rep_psnr=f['psnr_rep'], psf=per)
    json.dump(out, open(os.path.join(ROOT, 'outputs', 'CA', '%s_EB_load.json' % stage), 'w'), indent=1, default=float)
    L = ['CA instance-level merge-alternative load (%s): per image, per PSF: ambiguous merges / evaluated near pairs (<=6 px, both weights > 0) (+ skipped signed pairs)' % stage]
    for i, v in out.items(): L.append('  img %s %s rep %.1f ' % (i, v['level'], v['rep_psnr']) + ' '.join('%s:%d/%d(+%dskip)' % (pn, v['psf'][pn]['n_amb'], v['psf'][pn]['n_pairs'], v['psf'][pn]['n_skipped_signed']) for pn in CG.PSF_ORDER))
    open(os.path.join(ROOT, 'outputs', 'CA', '%s_EB_load.txt' % stage), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L))


if __name__ == '__main__':
    if sys.argv[1] == 'design': design()
    else: load(sys.argv[2])
