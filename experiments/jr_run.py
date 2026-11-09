"""JR runner (evaluator side: imports jr_gen). Contract JR candidate v0 sections 3-7.
Stages: tune (images 501-506, base 9511; phases T1/T2/T3 and descriptive RIDGE), verify (511-522, base 9521; sealed: reads outputs/JR/tune/selection.json), verify2 (701-712, base 9531; sealed), dry (590-592, base 9501; pipeline test only, never evidence).
One JSON per (stage, image, cond, arm, config): outputs/JR/<stage>/<img>_<cond>__<armname>__<cfgid>.json. Resumable (existing files are skipped). Shard with --shard i --nshards n over the (image,cond) list.
Usage: python3 experiments/jr_run.py --stage tune --phase T1 --workers 2   (verify/verify2: the parent opens the sealed gate once and forks the workers)"""
import os, sys, json, time, argparse
import multiprocessing as mp
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import numpy as np
import geo_core as GC, jr_gen, jr_core as JC

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
N, K = 32, 36
MAX_SWEEPS, W_CAP = 1500, 3.0e10
ARMS = {'OBS-J': dict(arm='OBS', mode='joint'), 'SPA-J': dict(arm='SPA', mode='joint'), 'OBS-I': dict(arm='OBS', mode='ind_lp'), 'OBS0-J': dict(arm='OBS0', mode='joint'),
        'RND-J': dict(arm='RND', mode='joint'), 'OVL-J': dict(arm='OVL', mode='joint'), 'IND1': dict(arm='IND1', mode='joint', gs=1), 'FULL': dict(arm='FULL', mode='joint', gs=K)}
GROUP_ARMS = ['OBS-J', 'SPA-J', 'OBS-I', 'OBS0-J', 'RND-J', 'OVL-J']
STAGES = dict(tune=(jr_gen.TUNE_IMGS, 9511), verify=(jr_gen.VERIFY_IMGS, 9521), verify2=(jr_gen.VERIFY2_IMGS, 9531), dry=(jr_gen.SMOKE_IMGS, 9501))
GS_T1, KAP_T1, R_T2, KAP_T3 = (2, 4, 9), 0.1, 4, (0.03, 0.3)
IND1_KAPS = (0.01, 0.03, 0.1, 0.3, 1.0)
RIDGES = (0.1, 10.0)


def cfg_id(gs, kap, R=1, ridge=1.0): return 'gs%d_k%g_R%d' % (gs, kap, R) + ('' if ridge == 1.0 else '_rg%g' % ridge)


def problem(img, cond, base):
    op = jr_gen.make_op(cond, N); x = jr_gen.clean_image_jr(img, N); y = jr_gen.noisy_obs_jr(op, x, jr_gen.SN, base, img, cond)
    P = JC.JProb(N, op, y, jr_gen.SN, 1e-3 / jr_gen.SN ** 2); return P, GC.grid_init(P, K), x


def resp_counts(P, th):
    """DIAG (uncharged): per-primitive singular values of the calibrated whitened response R_k (m x 6); counts >1 identifiable, (1e-6,1] weak at noise scale, <=1e-6 strict null (numerical)."""
    J = GC.render_jac(th, P.N)[1]; AJ = P.op.apply_stack(J).reshape(6 * K, -1).T; R = AJ * JC.calib_scales(th, J)[None, :] / P.sn; ident = weak = null = 0
    for k in range(K):
        sv = np.linalg.svd(R[:, 6 * k:6 * k + 6], compute_uv=False); ident += int((sv > 1).sum()); weak += int(((sv > 1e-6) & (sv <= 1)).sum()); null += int((sv <= 1e-6).sum())
    return dict(identifiable=ident, weak=weak, null=null)


def run_one(P, th0, xc, spec, gs, kap, R=1, ridge=1.0, seed=0):
    cfg = {**spec, 'kappa0': kap, 'f': 3, 'gs': gs, 'seed': seed, 'R': R, 'ridge': ridge}; t = time.perf_counter()
    o = JC.jr_solve(P, th0, cfg, max_sweeps=MAX_SWEEPS, W_cap=W_CAP, keep_theta=True); wall = time.perf_counter() - t
    ps = [jr_gen.psnr(P.render(th), xc) for th in o['th_hist']]; tr = o['traj']; vis = [v for s in o['sweeps'] for v in s.get('visits', [])]
    comp = [v['comp'] for v in vis if v['s'] > 1]
    res = dict(arm=spec['arm'], mode=spec['mode'], gs=gs, kappa0=kap, R=R, ridge=ridge, stop=o['stop'], F=o['F'], W=o['cnt']['W'], A=o['cnt']['A'], cat=o['cnt']['cat'], T=o['T'], wall=wall, rej=o['rej'], trials=o['trials'],
               clamped=o['clamped'], visits=o['visits'], sweeps=len(tr) - 1, trajF=[t_[1] for t_ in tr], trajW=[t_[2] for t_ in tr], trajGrp=[t_[5] for t_ in tr], psnr=ps,
               vW=[v[0] for v in o['vtraj']], vF=[v[1] for v in o['vtraj']], comp_median=float(np.median(comp)) if comp else None, comp_n=len(comp),
               sizes1=o['sweeps'][0]['sizes'] if o['sweeps'] else None, groups_first12=[s['groups'] for s in o['sweeps'][:12]] if spec['arm'] in ('OBS', 'OBS0', 'SPA', 'OVL') else None)
    return res


def jobs_for(stage, phase, sel):
    """List of (armname, gs, kappa0, R, ridge)."""
    J = []
    if stage == 'tune':
        if phase == 'T1':
            for a in GROUP_ARMS:
                for g in GS_T1: J.append((a, g, KAP_T1, 1, 1.0))
            for kp in IND1_KAPS: J.append(('IND1', 1, kp, 1, 1.0))
        elif phase == 'T2':
            for a in GROUP_ARMS: J.append((a, sel['T1'][a]['gs'], KAP_T1, R_T2, 1.0))
        elif phase == 'T3':
            for a in GROUP_ARMS:
                for kp in KAP_T3: J.append((a, sel['T2'][a]['gs'], kp, sel['T2'][a]['R'], 1.0))
        elif phase == 'RIDGE':      # descriptive sensitivity of OBS-J to the affinity ridge at its final configuration; never used for selection
            for rg in RIDGES: J.append(('OBS-J', sel['final']['OBS-J']['gs'], sel['final']['OBS-J']['kappa0'], sel['final']['OBS-J']['R'], rg))
        else: raise SystemExit('tune needs --phase T1|T2|T3|RIDGE')
    elif stage in ('verify', 'verify2', 'dry'):
        for a in list(ARMS):
            if a == 'FULL': J.append((a, K, 0.1, 1, 1.0))
            else: J.append((a, sel['final'][a]['gs'], sel['final'][a]['kappa0'], sel['final'][a].get('R', 1), 1.0))
    return [(a, g, kp, R, rg, cfg_id(g, kp, R, rg)) for a, g, kp, R, rg in J]


def work(args):
    img, cond, base, out, todo = args
    P, th0, xc = problem(img, cond, base); counts0 = resp_counts(P, th0)
    for arm, g, kp, R, rg, cid in todo:
        r = run_one(P, th0, xc, ARMS[arm], g, kp, R, rg); r.update(img=img, cond=cond, armname=arm, cfgid=cid, F0=P.F_of(th0)[0], psnr0=jr_gen.psnr(P.render(th0), xc), counts0=counts0)
        json.dump(r, open('%s/%d_%s__%s__%s.json' % (out, img, cond, arm, cid), 'w'))
    return '%s %d %s done %d runs' % (time.strftime('%H:%M:%S'), img, cond, len(todo))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--stage', required=True); ap.add_argument('--phase', default=''); ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--sel', default=os.path.join(ROOT, 'outputs', 'JR', 'tune', 'selection.json')); ap.add_argument('--arms', default=''); a = ap.parse_args()
    imgs, base = STAGES[a.stage]; out = os.path.join(ROOT, 'outputs', 'JR', a.stage); os.makedirs(out, exist_ok=True)
    if a.stage == 'verify': jr_gen.open_sealed('VERIFY')            # sealed gate, once, in the registered analyzer's parent process; forked workers inherit the session
    if a.stage == 'verify2': jr_gen.open_sealed('VERIFY2')
    sel = None
    if a.stage in ('verify', 'verify2', 'dry') or a.phase in ('T2', 'T3', 'RIDGE'):
        sel = json.load(open(a.sel if a.stage != 'tune' else os.path.join(out, 'selection.json' if a.phase == 'RIDGE' else 'selection_prelim.json')))
    jobs = jobs_for(a.stage, a.phase, sel); want = set(a.arms.split(',')) if a.arms else None; tasks = []
    for img in imgs:
        for cond in jr_gen.PSF_ORDER:
            todo = [(arm, g, kp, R, rg, cid) for arm, g, kp, R, rg, cid in jobs if (want is None or arm in want) and not os.path.exists('%s/%d_%s__%s__%s.json' % (out, img, cond, arm, cid))]
            if todo: tasks.append((img, cond, base, out, todo))
    print(time.strftime('%H:%M:%S'), a.stage, a.phase, 'tasks', len(tasks), 'jobs/problem', len(jobs), flush=True)
    with mp.get_context('fork').Pool(a.workers) as pool:
        for msg in pool.imap_unordered(work, tasks): print(msg, flush=True)


if __name__ == '__main__':
    main()
