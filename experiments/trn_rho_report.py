"""G-A report item (contract section 7): the rho actually reached by the closed-loop inner stop eps_r in {1e-1,1e-2,1e-3} (relative residual ||g - H x|| <= eps_r ||g||) on B* states.
rho_reached = ||x - delta*||_H^2 / ||delta*||_H^2 (tau-truncated generalized solution, same oracle as the same-state study). Two starts: cold (D0) and ideal warm (x0 = delta*_{t-1} embedded, an upper bound on the D0w start).
Dev images only (dev-sel 301..306 x C1,C4 by default), <=6 equidistant B* states per problem. Descriptive report, no gate. Usage: nice -n 19 python experiments/trn_rho_report.py --out outputs/TRN-S0/rho_report.json"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'src')); sys.path.insert(0, HERE)
import numpy as np
import geo_core as GC, trn_core as TC, trn_study as TS, trn_same_state as SS


def solve_rel(I, D, g, x0, eps, maxit=400):
    idx = D['idx']; ds = D['dstar'][idx]; ds2 = D['dH2']; Hf = D['H']; box = {}
    def tr(x):
        r = g - I.Hmv(x); rel = float(np.linalg.norm(r) / max(np.linalg.norm(g), 1e-300)); e = x[idx] - ds; err = float(e @ Hf @ e)
        box['err'] = err; return dict(err=err, W=0.0, stop=rel <= eps)
    res = TC.dpcg(I, g, I.dinvJ, x0=x0, maxit=maxit, track=tr)
    return box.get('err', ds2) / max(ds2, 1e-300), res['iters']


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--imgs', type=int, nargs='*', default=[301, 302, 303, 304, 305, 306]); ap.add_argument('--conds', nargs='*', default=['C1', 'C4'])
    ap.add_argument('--nstates', type=int, default=6); ap.add_argument('--best', default='outputs/TRN-S0/s0_REDUCE.json'); ap.add_argument('--out', default='outputs/TRN-S0/rho_report.json'); a = ap.parse_args()
    cfgb = dict(json.load(open(a.best))['best']['D0w']); cfgb['arm'] = 'D0w'; rows = []; t0 = time.time()
    for img in a.imgs:
        for cond in a.conds:
            P, o, log = SS.bstar_states(img, cond, 'M', cfgb)
            tsel = sorted(set(np.unique(np.round(np.linspace(1, len(log) - 1, a.nstates)).astype(int)).tolist()))
            for t in tsel:
                Ip = TC.Inner(P, log[t - 1]['th'], log[t - 1]['kap_acc']); Dp = Ip.dense(); It = TC.Inner(P, log[t]['th'], log[t]['kap_acc']); Dt = It.dense()
                if Dt['dq_star'] < 1e-6 * log[t]['F']: continue
                x0w = It._embed(Dt['idx'], np.zeros((len(Dt['idx']),)))
                common = np.intersect1d(Dp['idx'], Dt['idx']); x0w[common] = Dp['dstar'][common]                                 # ideal warm start: previous exact solution on the common free set
                for eps in (1e-1, 1e-2, 1e-3):
                    rc, ic = solve_rel(It, Dt, It.g, None, eps); rw, iw = solve_rel(It, Dt, It.g, x0w, eps)
                    rows.append(dict(img=img, cond=cond, t=t, eps_r=eps, rho_cold=rc, it_cold=ic, rho_warm=rw, it_warm=iw, kappa=log[t]['kap_acc']))
            print('done', img, cond, '%.0fs' % (time.time() - t0), flush=True)
    summ = {}
    for eps in (1e-1, 1e-2, 1e-3):
        v = [r for r in rows if r['eps_r'] == eps]
        summ[str(eps)] = dict(n=len(v), rho_cold_median=float(np.median([r['rho_cold'] for r in v])), rho_cold_q10_q90=[float(np.quantile([r['rho_cold'] for r in v], .1)), float(np.quantile([r['rho_cold'] for r in v], .9))],
                              rho_warm_median=float(np.median([r['rho_warm'] for r in v])), rho_warm_q10_q90=[float(np.quantile([r['rho_warm'] for r in v], .1)), float(np.quantile([r['rho_warm'] for r in v], .9))],
                              it_cold_median=float(np.median([r['it_cold'] for r in v])), it_warm_median=float(np.median([r['it_warm'] for r in v])), frac_cold_rho_le_0p1=float(np.mean([r['rho_cold'] <= 0.1 for r in v])))
    json.dump(dict(summary=summ, rows=rows, cfg=cfgb), open(a.out, 'w'), indent=1); print(json.dumps(summ, indent=1))


if __name__ == '__main__':
    main()
