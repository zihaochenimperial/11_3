"""TRN same-state reducer / analyzer (contract TRN v1.1 sections 5, 7). Reads outputs/TRN-SS/*.json written by trn_same_state.py; computes G-B / G-C / G-D readings at the main rho (0.1).
Definitions (pre-registered): per state W_arm = W to reach rho (censored at the safety budget: W_tot of the run, flagged); strongest control = argmin over {D0,D0w,D0b,D0s,D2} of the median state-W over the analysed set;
per (image,condition) trajectory ratio R = sum_t W_ctrl / sum_t W_arm; per image = geometric mean over its conditions; reading = median over images, sign count (#images with R>1), BCa 95% CI by image-cluster bootstrap (B=4000, fixed seed 20261108).
Also: censoring rates, a leave-out-301 reading, and the per-state a-priori break-even table (Opus S1). Descriptive extras are printed but only G-readings enter the gates.
Usage: python experiments/trn_same_state_reduce.py --dir outputs/TRN-SS --rho 0.1 [--exclude 301] [--img-set 301..312] --out outputs/TRN-SS_REDUCE.json"""
import argparse, glob, json, math, os, sys
import numpy as np
from math import erf, sqrt

BASE = ('D0', 'D0w', 'D0b', 'D0s', 'D2')


def _Phi(z): return 0.5 * (1.0 + erf(z / sqrt(2.0)))
def _Phiinv(p):
    from statistics import NormalDist
    return NormalDist().inv_cdf(min(max(p, 1e-12), 1 - 1e-12))


def bca(vals, stat=np.median, B=4000, seed=20261108, alpha=0.05):
    v = np.asarray(vals, float); n = len(v)
    if n < 3: return (float('nan'), float('nan'))
    rng = np.random.default_rng(seed); th = stat(v); bs = np.array([stat(v[rng.integers(0, n, n)]) for _ in range(B)])
    z0 = _Phiinv(float(np.mean(bs < th)) + 0.5 * float(np.mean(bs == th))); jk = np.array([stat(np.delete(v, i)) for i in range(n)]); d = jk.mean() - jk
    acc = float((d ** 3).sum() / (6.0 * ((d ** 2).sum() ** 1.5 + 1e-300)))
    out = []
    for q in (alpha / 2, 1 - alpha / 2):
        zq = _Phiinv(q); a = _Phi(z0 + (z0 + zq) / (1 - acc * (z0 + zq))); out.append(float(np.quantile(bs, min(max(a, 0.0), 1.0))))
    return tuple(out)


def state_W(rec, arm, rho):
    a = rec['arms'][arm]; h = a['hits'].get(str(rho))
    if h is None: return float(a['W']), True                                   # censored: W_tot at the safety budget
    return float(h[1]), False


def load(dirn, imgs=None, exclude=(), scale=None, k=None):
    runs = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(dirn, '*.json')))]
    return [r for r in runs if (imgs is None or r['img'] in imgs) and r['img'] not in exclude and (scale is None or r['scale'] == scale) and (k is None or ('_k%d.json' % k) in str(r.get('_file', '_k%d.json' % k)))]


def analyse(runs, rho, arms_num, ctrl=None):
    allw = {}; cens = {}
    for r in runs:
        for s in r['states']:
            if s['skipped']: continue
            for a in s['arms']:
                w, c = state_W(s, a, rho); allw.setdefault(a, []).append(w); cens.setdefault(a, []).append(c)
    base = [b for b in BASE if b in allw]
    med = {b: float(np.median(allw[b])) for b in base}; ctrl = ctrl or min(med, key=med.get)
    res = dict(ctrl=ctrl, ctrl_median_W=med, censor_rate={a: float(np.mean(v)) for a, v in cens.items()}, arms={})
    for arm in arms_num:
        if arm not in allw: continue
        per_img = {}
        for r in runs:
            ws_c = 0.0; ws_a = 0.0; n = 0
            for s in r['states']:
                if s['skipped'] or arm not in s['arms'] or ctrl not in s['arms']: continue
                ws_c += state_W(s, ctrl, rho)[0]; ws_a += state_W(s, arm, rho)[0]; n += 1
            if n and ws_a > 0: per_img.setdefault(r['img'], []).append(ws_c / ws_a)
        R = {i: float(np.exp(np.mean(np.log(v)))) for i, v in per_img.items()}; v = np.array(list(R.values()))
        if len(v) == 0: continue
        lo, hi = bca(v)
        res['arms'][arm] = dict(n_images=len(v), median=float(np.median(v)), sign_gt1=int((v > 1).sum()), bca95=[lo, hi], per_image={str(i): x for i, x in R.items()})
    return res


def iters_ratio(runs, rho, arm, ctrl):
    num = []; 
    for r in runs:
        for s in r['states']:
            if s['skipped'] or arm not in s['arms'] or ctrl not in s['arms']: continue
            ha = s['arms'][arm]['hits'].get(str(rho)); hc = s['arms'][ctrl]['hits'].get(str(rho))
            ia = (ha[0] if ha else s['arms'][arm]['iters']); ic = (hc[0] if hc else s['arms'][ctrl]['iters']); num.append((ic + 1) / (ia + 1))
    return float(np.median(num)) if num else float('nan')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--dir', default='outputs/TRN-SS'); ap.add_argument('--rho', type=float, default=0.1); ap.add_argument('--exclude', type=int, nargs='*', default=[])
    ap.add_argument('--imgs', type=int, nargs='*', default=None); ap.add_argument('--scale', default=None); ap.add_argument('--out', default=None); a = ap.parse_args()
    runs = load(a.dir, a.imgs, a.exclude, a.scale)
    nums = sorted({arm for r in runs for s in r['states'] if not s['skipped'] for arm in s['arms']} - set(BASE))
    full = analyse(runs, a.rho, nums); noctrl = analyse([r for r in runs if r['img'] != 301], a.rho, nums, ctrl=full['ctrl'])
    out = dict(rho=a.rho, n_runs=len(runs), full=full, minus301=noctrl, iters_ratio_D4lam_D6={arm: iters_ratio(runs, a.rho, arm, full['ctrl']) for arm in nums if arm.startswith('D46')})
    print('strongest control:', full['ctrl'], full['ctrl_median_W'])
    for arm, v in full['arms'].items(): print('%-9s median %.3f  sign>1 %d/%d  BCa %s  censor %.2f' % (arm, v['median'], v['sign_gt1'], v['n_images'], np.round(v['bca95'], 3).tolist(), full['censor_rate'].get(arm, float('nan'))))
    if a.out: json.dump(out, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
