"""CA runner (evaluator side: imports ca_gen). Contract CA v1 sections 3, 4, 11.
Stages: dev (801..808), smoke (890..892), confirm (811..826; sealed: CA_CONFIRM_UNLOCK=1 + freeze record + sha registrations + single consumption).
One JSON per (stage, image, PSF, rep, noise, arm, cfg) in outputs/CA/<stage>/runs/. Resumable (existing files are skipped); sharding by --shard/--nshards over (image, PSF).
Blocks: P (primary, common fixed config for all arms), S (secondary, JR-frozen per-arm tuned configs for OBS-J/RND-J/IND1), X (extended 10x budget, descriptive, UNCONDITIONAL: OBS-J/RND-J, cells (R0,free)(R0,noisy), first 4 images),
 A (DEV-ONLY descriptive: OBS-J/RND-J, noisy cells, a = 1e-2/SN^2 instead of 1e-3/SN^2; refused on the sealed stage)."""
import os, sys, json, time, argparse, glob
import multiprocessing as mp
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import numpy as np
import geo_core as GC, jr_core as JC, ca_gen as CG

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
N, K = CG.N, 36
GRID = np.geomspace(1e9, 3e10, 8); MAX_SWEEPS, W_CAP = 1500, 3.0e10
KAP_P = 0.1
A_RATIO = 1e-3; X_IMGS = 4; X_MULT = 10.0; X_MS = 20000
CAPS_CORE_H = {'P': 6.0, 'S': 3.5, 'X': 3.0, 'A': 3.0}       # per-block CPU cap in core-hours (sum of run walls); a block that exceeds it is stopped, marked CAP_EXCEEDED and is INCONCLUSIVE (contract section 11); no extension
ARMS_P = {'OBS-J': dict(arm='OBS', mode='joint', gs=2), 'SPA-J': dict(arm='SPA', mode='joint', gs=2), 'OBS-I': dict(arm='OBS', mode='ind_lp', gs=2),
          'RND-J': dict(arm='RND', mode='joint', gs=2), 'IND1': dict(arm='IND1', mode='joint', gs=1)}
ARMS_S = {'OBS-J': (dict(arm='OBS', mode='joint', gs=2), 0.3), 'RND-J': (dict(arm='RND', mode='joint', gs=2), 0.03), 'IND1': (dict(arm='IND1', mode='joint', gs=1), 0.01)}     # JR-frozen tuned configs (selection.json final)
STAGES = dict(dev=CG.DEV_IMGS, smoke=CG.SMOKE_IMGS, confirm=CG.CONFIRM_IMGS)
REPS = ('R0', 'R1'); NOISE = (0, 1)


def idx_at(W, B): return max(int(np.searchsorted(W, B, side='right')) - 1, 0)


def edge_mask(x):
    gy, gx = np.gradient(x); m = np.hypot(gx, gy); mk = m >= np.quantile(m, 0.75)
    from scipy.ndimage import binary_dilation
    return binary_dilation(mk, structure=np.ones((3, 3), bool))


def mse(a, b, mask=None):
    d = (a - b) ** 2; return float(d.mean() if mask is None else d[mask].mean())


def db(m): return float(10 * np.log10(1.0 / max(m, 1e-30)))


def run_one(P, th0, truth, xg, eps, spec, kap, R=1, cap=W_CAP, ms=MAX_SWEEPS):
    op = P.op; cfg = {**spec, 'kappa0': kap, 'f': 3, 'seed': 0, 'R': R, 'ridge': 1.0}; t = time.perf_counter()
    o = JC.jr_solve(P, th0, cfg, max_sweeps=ms, W_cap=cap, keep_theta=True); wall = time.perf_counter() - t; tr = o['traj']
    X = [GC.render(th, N) for th in o['th_hist']]; msk = edge_mask(truth); m = N * N; sig = P.sn
    ps = [db(mse(x, truth)) for x in X]; pe = [db(mse(x, truth, msk)) for x in X]; pg = [db(mse(x, xg)) for x in X] if xg is not None else None
    AX = [op.apply(x) for x in X]; resid = [float(np.sum((P.y - ax) ** 2)) / (sig ** 2 * m) for ax in AX]          # data misfit ratio ||y - A x||^2 / (sigma^2 m)
    Atruth = op.apply(truth); nf = None; mf = None; pb = [db(mse(ax, Atruth)) for ax in AX]          # error of the fitted blurred image vs the noise-free blurred truth (data space)
    if float(np.linalg.norm(eps)) > 0: nf = [float(np.sum((ax - Atruth) * eps) / np.sum(eps * eps)) for ax in AX]               # fraction of noise energy absorbed by the fitted blurred image (evaluation only)
    if xg is not None and not np.array_equal(truth, xg):
        e = Atruth - op.apply(xg); mf = [float(np.sum((ax - op.apply(xg)) * e) / max(np.sum(e * e), 1e-30)) for ax in AX]    # same for the representation-misfit residual (R1)
    vF = [v[1] for v in o['vtraj']]
    return dict(spec=spec, kappa0=kap, R=R, stop=o['stop'], F=o['F'], W=o['cnt']['W'], A=o['cnt']['A'], cat=o['cnt']['cat'], wall=wall, rej=o['rej'], trials=o['trials'], clamped=o['clamped'], visits=o['visits'], sweeps=len(tr) - 1,
                trajF=[round(t_[1], 6) for t_ in tr], trajW=[t_[2] for t_ in tr], trajGrp=[t_[5] for t_ in tr], minVF=float(min(vF)), psnr=[round(a, 4) for a in ps], psnr_edge=[round(a, 4) for a in pe], psnr_blur=[round(a, 4) for a in pb],
                psnr_vs_proj=None if pg is None else [round(a, 4) for a in pg], resid=[round(a, 5) for a in resid], nf=None if nf is None else [round(a, 5) for a in nf], mf=None if mf is None else [round(a, 5) for a in mf])


def match_stats(xs, xg):
    """Descriptive R0 (projection xg) vs R1 (sharp xs) matching report: mass, peak, gradient energy, Laplacian (high-pass) energy ratios R0/R1."""
    from scipy.ndimage import laplace
    gy, gx = np.gradient(xs); hy, hx = np.gradient(xg)
    return dict(mass_ratio=float(xg.sum() / xs.sum()), peak_R0=float(xg.max()), peak_R1=float(xs.max()), grad_energy_ratio=float((hx ** 2 + hy ** 2).sum() / (gx ** 2 + gy ** 2).sum()), lap_energy_ratio=float((laplace(xg) ** 2).sum() / (laplace(xs) ** 2).sum()))


def jobs(block):
    """List of (armname, spec, kappa0, cfgid, cells, cap, aratio, max_sweeps). aratio is the regularisation ratio a = aratio / SN^2 (1e-3 for every block except the DEV-only block A)."""
    allc = [(r, n) for r in REPS for n in NOISE]
    if block == 'P': return [(a, sp, KAP_P, 'P', allc, W_CAP, A_RATIO, MAX_SWEEPS) for a, sp in ARMS_P.items()]
    if block == 'S': return [(a, sp, k, 'S', allc, W_CAP, A_RATIO, MAX_SWEEPS) for a, (sp, k) in ARMS_S.items()]
    if block == 'X': return [(a, ARMS_P[a], KAP_P, 'X', [('R0', 0), ('R0', 1)], X_MULT * W_CAP, A_RATIO, X_MS) for a in ('OBS-J', 'RND-J')]
    if block == 'A': return [(a, ARMS_P[a], KAP_P, 'A', [('R0', 1), ('R1', 1)], W_CAP, 1e-2, MAX_SWEEPS) for a in ('OBS-J', 'RND-J')]
    raise SystemExit('unknown block')


def block_imgs(block, imgs): return imgs[:X_IMGS] if block == 'X' else imgs


def work(args):
    stage, img, cond, out, blocks, cache = args
    fit = CG.get_fit(img, os.path.join(out, 'fits')); xs = CG.sharp_image(img); xg = fit['x']; op = CG.make_op(cond); done = 0; wall = 0.0
    for rep in REPS:
        truth = xs if rep == 'R1' else xg
        for noisy in NOISE:
            todo = []
            for blk in blocks:
                for a, s, kap, cid, cells, cap, ar, ms in jobs(blk):
                    f = '%s/%d_%s_%s_n%d__%s__%s.json' % (os.path.join(out, 'runs'), img, cond, rep, noisy, a, cid)
                    if (rep, noisy) in cells and not os.path.exists(f): todo.append((a, s, kap, cid, cap, ar, ms, f))
            if not todo: continue
            y, eps = CG.observe(op, truth, bool(noisy), img, cond)
            for a, s, kap, cid, cap, ar, ms, f in todo:
                P = JC.JProb(N, op, y, CG.SN, ar / CG.SN ** 2); th0 = GC.grid_init(P, K); F0 = P.F_of(th0)[0]          # the ONLY problem construction: same SN and same ratio a = ar/SN^2 in noisy and noise-free cells (ar = 1e-3 except DEV-only block A)
                r = run_one(P, th0, truth, xg, eps, s, kap, 1, cap, ms); r.update(img=img, cond=cond, rep=rep, noisy=noisy, armname=a, cfgid=cid, aratio=ar, F0=F0, psnr0=db(mse(GC.render(th0, N), truth)), rep_psnr=fit['psnr_rep'], level=CG.level_of(img), match=match_stats(xs, xg))
                json.dump(r, open(f + '.tmp', 'w')); os.replace(f + '.tmp', f); done += 1; wall += r['wall']
    return '%s %d %s done %d runs (%.2f core-min)' % (time.strftime('%H:%M:%S'), img, cond, done, wall / 60.0), wall / 3600.0


def block_wall(out, blk):
    """Core-hours already spent on a block (sum of the run walls of its JSON files; makes resumed sessions count earlier work)."""
    tot = 0.0
    for f in glob.glob(os.path.join(out, 'runs', '*__%s.json' % blk)):
        try: tot += float(json.load(open(f))['wall'])
        except Exception: pass
    return tot / 3600.0


def fit_one(args):
    i, d = args; return i, CG.get_fit(i, d)['psnr_rep']


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--stage', required=True); ap.add_argument('--blocks', default='P'); ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--imgs', default=''); ap.add_argument('--conds', default=''); ap.add_argument('--cap', type=float, default=0.0, help='override the W cap (mechanical smoke only)'); ap.add_argument('--cap-core-h', type=float, default=0.0, help='override the per-block core-hour cap (mechanical smoke only)'); a = ap.parse_args()
    if a.cap > 0:
        assert a.stage != 'confirm', 'no cap override on the sealed run'; globals()['W_CAP'] = a.cap
    blocks = a.blocks.split(','); assert not (a.stage == 'confirm' and 'A' in blocks), 'block A is DEV-only'
    if a.stage == 'confirm': assert not a.imgs and not a.conds and blocks == ['P', 'S', 'X'], 'sealed run: no --imgs/--conds subsetting and exactly --blocks P,S,X (no post-hoc choices; contract section 11)'          # before the gate, so a refused call consumes nothing
    if a.stage == 'confirm': CG.open_sealed('CONFIRM')            # sealed gate, once, in the registered analyzer's parent process; forked workers inherit
    imgs = [int(v) for v in a.imgs.split(',')] if a.imgs else STAGES[a.stage]; conds = a.conds.split(',') if a.conds else CG.PSF_ORDER
    out = os.path.join(ROOT, 'outputs', 'CA', a.stage); os.makedirs(os.path.join(out, 'runs'), exist_ok=True); os.makedirs(os.path.join(out, 'fits'), exist_ok=True)
    print(time.strftime('%H:%M:%S'), a.stage, 'blocks', blocks, flush=True)
    caps = dict(CAPS_CORE_H)
    if a.cap_core_h > 0:
        assert a.stage != 'confirm', 'no core-hour cap override on the sealed run'; caps = {k: a.cap_core_h for k in caps}
    with mp.get_context('fork').Pool(a.workers) as pool:         # K-fits first (cached) so that workers do not duplicate them
        for i, ps in pool.imap_unordered(fit_one, [(i, os.path.join(out, 'fits')) for i in imgs]): print(time.strftime('%H:%M:%S'), 'fit', i, 'rep_psnr %.2f' % ps, flush=True)
    for b in blocks:                                              # block order as given (P, S, X): one block at a time, same process, one gate consumption
        spent = block_wall(out, b); marker = os.path.join(out, 'CAP_EXCEEDED_%s.txt' % b); tasks = [(a.stage, i, c, out, [b], None) for i in block_imgs(b, imgs) for c in conds]
        print(time.strftime('%H:%M:%S'), 'block', b, 'tasks', len(tasks), 'core-h already %.2f of cap %.2f' % (spent, caps[b]), flush=True)
        if spent > caps[b]: open(marker, 'w').write('block %s exceeded %.2f core-h at start (%.2f)\n' % (b, caps[b], spent)); print('CAP_EXCEEDED', b, flush=True); continue
        with mp.get_context('fork').Pool(a.workers) as pool:
            for msg, wh in pool.imap_unordered(work, tasks):
                spent += wh; print(msg, 'block %s %.3f/%.2f core-h' % (b, spent, caps[b]), flush=True)
                if spent > caps[b]:
                    open(marker, 'w').write('block %s exceeded %.2f core-h (%.2f); remaining tasks not run; block is INCONCLUSIVE\n' % (b, caps[b], spent)); print('CAP_EXCEEDED', b, flush=True); pool.terminate(); break


if __name__ == '__main__':
    main()
