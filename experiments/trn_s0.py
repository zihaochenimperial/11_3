"""TRN S0 / tuning runner (contract TRN v1.1 sections 6-7). DEV images only (assertion). One JSON per (phase, image, condition, arm, kappa0, f, eps_r).
Phases: tune1 (eps_r=1e-1; kappa0 x f grid), tune2 (best (kappa0,f) per arm from tune1 -> eps_r grid), s0 (final configs, all dev-sel images; long run 100 outer).
Selection (reduce): per arm, W-to-target median over the tuning problems; target F <= F_ref + 1e-3 (F0 - F_ref) with F_ref^tune = min final F over the runs of that stage on the same problem; a run that never hits counts as censored (W=inf).
Usage: python experiments/trn_s0.py run --phase tune1 --scale M --imgs 301 302 --conds C1 C4 --shard 0 --nshards 2 --out outputs/TRN-S0 ; python experiments/trn_s0.py reduce --phase tune1 --out outputs/TRN-S0"""
import argparse, glob, hashlib, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'src'))
import numpy as np
import geo_core as GC, trn_gen as TG, trn_loop as TL

SCALES = dict(S=(32, 36), M=(64, 144), L=(96, 324))
ARMS = {'D0': dict(inner='J'), 'D0w': dict(inner='J', warm=True), 'D0b': dict(inner='BJ')}
GRID1 = [(k0, f) for k0 in (1e-3, 1e-2, 1e-1, 1.0) for f in (3, 10)]
EPS = (1e-1, 1e-2, 1e-3)
MAXOUT = 100; TOL = 1e-3


def problem(img, cond, scale):
    assert img in TG.DEV_IMGS, 'S0/tuning runner: dev images only'
    N, K = SCALES[scale]; sb, sn = TG.COND[cond]; op = GC.Op(N, sb); x = TG.clean_image_trn(img, N); y = TG.noisy_obs_trn(op, x, sn, TG.DEV_SEEDS[0], img)
    P = GC.Prob(N, sb, y, sn, 1e-3 / sn ** 2); return P, GC.grid_init(P, K), x


def psnr(x, xt):
    return float(10 * np.log10(1.0 / max(float(np.mean((x - xt) ** 2)), 1e-300)))


def run_one(img, cond, scale, arm, k0, f, eps, maxout=MAXOUT, keep_theta=False):
    P, th0, xclean = problem(img, cond, scale); cfg = dict(kappa0=k0, f=f, eps_r=eps, maxcg=400, **ARMS[arm]); t = time.time()
    o = GC.solve('TRN', P, th0, cfg, max_iter=maxout, keep_theta=keep_theta); wall = time.time() - t; log = o['cnt'].get('log', [])
    return dict(img=img, cond=cond, scale=scale, arm=arm, kappa0=k0, f=f, eps_r=eps, F0=o['traj'][0][1], F_final=o['F'], stop=o['stop'], outer=len(o['traj']) - 1, rej=o['rej'], wall=wall,
                trajF=[r[1] for r in o['traj']], trajW=[r[6] for r in o['traj']], cg_trials=[r['trials'] for r in log], kap_acc=[r['kap_acc'] for r in log],
                cats=[[r['W_jac'], r['W_rhs'], r['W_setup'], r['W_setup_Ainner'], r['W_cg'], r['W_acc']] for r in log],
                psnr_final=psnr(P.render(o['theta']), xclean),      # evaluation side only
                psnr_traj=([psnr(P.render(t), xclean) for t in o['th_hist']] if keep_theta else None))      # per-iteration PSNR (evaluation side): needed for the iteration-of-first-hit PSNR criterion (Opus C5)


def fname(out, phase, d):
    return os.path.join(out, phase, '%d_%s_%s_%s_%g_%d_%g.json' % (d['img'], d['cond'], d['scale'], d['arm'], d['kappa0'], d['f'], d['eps_r']))


def w_to_target(d, F_ref, tol=TOL):
    tgt = F_ref + tol * (d['F0'] - F_ref)
    for i, F in enumerate(d['trajF']):
        if F <= tgt: return d['trajW'][i], i
    return float('inf'), None


ORDER = {'D0': 0, 'D0w': 1, 'D0b': 2}


def reduce_phase(out, phase):
    runs = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(out, phase, '*.json')))]
    byprob = {}
    for d in runs: byprob.setdefault((d['img'], d['cond'], d['scale']), []).append(d)
    Fref = {k: min(d['F_final'] for d in v) for k, v in byprob.items()}                  # F_ref^sel (selection only): min final F over the runs of THIS stage on the same problem (baseline arms only)
    table = {}; stats = {}; gaps = {}
    for k, v in byprob.items():
        for d in v:
            w, it = w_to_target(d, Fref[k]); key = (d['arm'], d['kappa0'], d['f'], d['eps_r']); table.setdefault(key, []).append(w); gaps.setdefault(key, []).append((d['F_final'] - Fref[k]) / max(d['F0'] - Fref[k], 1e-300))
            if it is not None and it > 0:
                cg = d['cg_trials'][:it]; ct = np.array(d['cats'][:it], float); tot = ct[:, [0, 1, 2, 4, 5]].sum()
                stats.setdefault(key, []).append(dict(f_iter=float(ct[:, 4].sum() / tot), f_asm=float((ct[:, 0] + ct[:, 2]).sum() / tot), f_asm_cached=float((ct[:, 0] + ct[:, 2] - ct[:, 3]).sum() / tot),
                                                    mv_per_outer_med=float(np.median([sum(c) for c in cg])), rej_per_outer=float(np.mean([len(c) - 1 for c in cg]))))
    summ = []
    for key, ws in table.items():
        ws = np.array(ws); fin = np.isfinite(ws); med = float(np.median(ws))             # median with censored (= inf) values: inf if more than half are censored
        st = stats.get(key, []); g = (lambda n: float(np.median([x[n] for x in st])) if st else float('nan'))
        summ.append(dict(arm=key[0], kappa0=key[1], f=key[2], eps_r=key[3], n=len(ws), cens=float(np.mean(~fin)), W_median=med, gap_median=float(np.median(gaps[key])), f_iter=g('f_iter'), f_asm=g('f_asm'), f_asm_cached=g('f_asm_cached'), mv_per_outer_med=g('mv_per_outer_med'), rej_per_outer=g('rej_per_outer')))
    sk = lambda s_: (s_['W_median'], s_['cens'], s_['gap_median'], ORDER.get(s_['arm'], 9), -s_['eps_r'], s_['kappa0'], s_['f'])        # ties (all-censored: fewer censored, smaller final gap): then D0<D0w<D0b, larger eps_r (Opus C2/C3)
    best = {}
    for s_ in sorted(summ, key=sk):
        best.setdefault(s_['arm'], s_)
    bstar = min(best.values(), key=sk)
    json.dump(dict(phase=phase, n_runs=len(runs), problems=sorted(map(list, byprob)), summary=sorted(summ, key=sk), best=best, bstar=bstar, note='F_ref^sel = min final F over this stage runs per problem (selection only; contract v1.2 section 6)'), open(os.path.join(out, phase + '_REDUCE.json'), 'w'), indent=1, default=str)
    return best, summ


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['run', 'reduce']); ap.add_argument('--phase', required=True); ap.add_argument('--scale', default='M')
    ap.add_argument('--imgs', type=int, nargs='*', default=[]); ap.add_argument('--conds', nargs='*', default=['C1', 'C4']); ap.add_argument('--shard', type=int, default=0); ap.add_argument('--nshards', type=int, default=1)
    ap.add_argument('--out', default='outputs/TRN-S0'); ap.add_argument('--arms', nargs='*', default=list(ARMS)); ap.add_argument('--maxout', type=int, default=MAXOUT)
    ap.add_argument('--best', default=None, help='tune2/s0: path of the REDUCE json from the previous phase'); a = ap.parse_args()
    if a.cmd == 'reduce':
        best, summ = reduce_phase(a.out, a.phase); [print(k, {kk: (round(v[kk], 3) if isinstance(v[kk], float) else v[kk]) for kk in ('kappa0', 'f', 'eps_r', 'W_median', 'cens', 'f_iter', 'f_asm', 'mv_per_outer_med', 'rej_per_outer')}) for k, v in best.items()]; print('B*:', json.load(open(os.path.join(a.out, a.phase + '_REDUCE.json')))['bstar']['arm']); return
    os.makedirs(os.path.join(a.out, a.phase), exist_ok=True)
    probs = [(i, c) for i in a.imgs for c in a.conds]; mine = [p for j, p in enumerate(probs) if j % a.nshards == a.shard]
    prev = json.load(open(a.best))['best'] if (a.best and a.phase != 'fref') else None
    for (img, cond) in mine:
        for arm in a.arms:
            if a.phase == 'tune1': cfgs = [(k0, f, 1e-1) for (k0, f) in GRID1]
            elif a.phase == 'tune2': b = prev[arm]; cfgs = [(b['kappa0'], b['f'], e) for e in EPS if e != b['eps_r']] + [(b['kappa0'], b['f'], b['eps_r'])]
            elif a.phase == 's0': b = prev[arm]; cfgs = [(b['kappa0'], b['f'], b['eps_r'])]
            elif a.phase == 'fref':                                                  # C5: D0 (PCG-J), eps_r=1e-3, B* kappa0 and f, 100 outer (needs --best s0_REDUCE.json and --bstar via the json)
                if arm != 'D0': continue
                b = json.load(open(a.best))['bstar']; cfgs = [(b['kappa0'], b['f'], 1e-3)]
            for (k0, f, eps) in cfgs:
                d = dict(img=img, cond=cond, scale=a.scale, arm=arm, kappa0=k0, f=f, eps_r=eps); p = fname(a.out, a.phase, d)
                if os.path.exists(p): continue
                r = run_one(img, cond, a.scale, arm, k0, f, eps, a.maxout, keep_theta=a.phase in ('s0', 'fref')); json.dump(r, open(p, 'w')); print('done', os.path.basename(p), 'F=%.5g stop=%s outer=%d wall=%.0fs' % (r['F_final'], r['stop'], r['outer'], r['wall']), flush=True)


if __name__ == '__main__':
    main()
