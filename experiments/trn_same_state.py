"""TRN same-state study driver (contract TRN v1.1 sections 3-5, 7 G-B/G-C/G-D). DEV images only. States come from the B* closed-loop trajectory (tuned config from the S0 REDUCE json);
for every sampled pair (t-1 -> t) the (theta, kappa_accepted) problems are built and all same-state arms are run (src/trn_study.study_state).
Usage: python experiments/trn_same_state.py run --scale M --imgs 301 302 --conds C1 C4 --best outputs/TRN-S0/tune2_REDUCE.json --bstar D0 --stride 2 --k 8 --shard 0 --nshards 2 --out outputs/TRN-SS
       python experiments/trn_same_state.py reduce --out outputs/TRN-SS"""
import argparse, glob, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'src')); sys.path.insert(0, HERE)
import numpy as np
import geo_core as GC, trn_gen as TG, trn_core as TC, trn_loop as TL, trn_study as TS
import trn_s0 as S0


def bstar_states(img, cond, scale, cfgb, maxout=100):
    P, th0, _ = S0.problem(img, cond, scale); cfg = dict(kappa0=cfgb['kappa0'], f=cfgb['f'], eps_r=cfgb['eps_r'], maxcg=400, **S0.ARMS[cfgb['arm']])
    o = GC.solve('TRN', P, th0, cfg, max_iter=maxout); log = [r for r in o['cnt']['log'] if r.get('kap_acc')]
    return P, o, log


def compact(res):
    arms = {}
    for a, v in res['arms'].items():
        arms[a] = dict(hits={str(k): (None if h is None else [int(h[0]), float(h[1])]) for k, h in v['hits'].items()}, iters=int(v['iters']), W=float(v['Wtot']),
                       k=v.get('k'), ls_ratio=v.get('ls_ratio'), cond_E=v.get('cond_E'), setup_strict=v.get('setup_strict'), setup_cached=v.get('setup_cached'))
    return dict(arms=arms, **{k: res[k] for k in ('prev_iters', 'F', 'dq_star', 'p', 'rank_eff95', 'n_free', 'n_degenerate', 'cond_gen', 'act_frac')})


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['run', 'reduce']); ap.add_argument('--scale', default='M'); ap.add_argument('--imgs', type=int, nargs='*', default=[])
    ap.add_argument('--conds', nargs='*', default=['C1', 'C4']); ap.add_argument('--best', default=None); ap.add_argument('--bstar', default='D0'); ap.add_argument('--stride', type=int, default=2)
    ap.add_argument('--k', type=int, default=8); ap.add_argument('--shard', type=int, default=0); ap.add_argument('--nshards', type=int, default=1); ap.add_argument('--out', default='outputs/TRN-SS')
    ap.add_argument('--maxstates', type=int, default=12); a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.cmd == 'reduce': raise SystemExit('reduce: implemented in experiments/trn_same_state_reduce.py (written after the freeze)')
    cfgb = dict(json.load(open(a.best))['best'][a.bstar]); cfgb['arm'] = a.bstar
    probs = [(i, c) for i in a.imgs for c in a.conds]; mine = [p for j, p in enumerate(probs) if j % a.nshards == a.shard]
    for (img, cond) in mine:
        out = os.path.join(a.out, '%d_%s_%s_k%d.json' % (img, cond, a.scale, a.k))
        if os.path.exists(out): continue
        t0 = time.time(); P, o, log = bstar_states(img, cond, a.scale, cfgb); recs = []
        tsel = sorted(set(np.unique(np.round(np.linspace(1, len(log) - 1, min(a.maxstates, len(log) - 1))).astype(int)).tolist())) if len(log) > 1 else []     # equidistant in t (Opus C7)
        for t in tsel:
            Ip = TC.Inner(P, log[t - 1]['th'], log[t - 1]['kap_acc']); It = TC.Inner(P, log[t]['th'], log[t]['kap_acc']); Dp = Ip.dense(); Dt = It.dense()
            res = TS.study_state(It, Dt, Ip, Dp, log[t]['F'], k=a.k)
            recs.append(dict(t=t, skipped=bool(res['skipped']), kappa=log[t]['kap_acc'], **(compact(res) if not res['skipped'] else dict(dq_star=res['dq_star'], F=res['F']))))
        json.dump(dict(img=img, cond=cond, scale=a.scale, bstar=cfgb, n_outer=len(o['traj']) - 1, states=recs, wall=time.time() - t0), open(out, 'w')); print('done', out, len(recs), 'states %.0fs' % (time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
