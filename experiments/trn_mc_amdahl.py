"""A-priori Amdahl readings from the S0 B* (D0w) closed-loop runs (dev-sel only; no new experiment, no confirm access). Contract TRN v1.2 section 9 (MC must carry its own Amdahl gate) + extra lever readings.
(1) A-side cap: share of total W in A/A^T applications under the FROZEN dense-B cost model (F_A=4N^3) and under a BANDED-B control (F_A=4 N^2 w, w=2*ceil(3 sb)+1), and the Amdahl cap if A were free relative to the banded control.
(2) Rejected-trial work: share of all CG iterations spent in trials that the frozen acceptor rejected, and the cap 1/(1-share) for perfect rejection avoidance (acceptance-check cost ignored).
Usage: python experiments/trn_mc_amdahl.py outputs/TRN-MC/amdahl_prior.json"""
import glob, json, sys
import numpy as np
sys.path.insert(0, 'src')
import geo_flops as FL
rows = {}
for scale, dirn, N in [('M', 'outputs/TRN-S0/s0', 64), ('L', 'outputs/TRN-S0L/s0', 96)]:
    for cond, sb in (('C1', 1), ('C4', 2)):
        A_d, A_b, rej, bandedcheap, caps = [], [], [], [], []
        for f in sorted(glob.glob('%s/*_%s_%s_D0w*.json' % (dirn, cond, scale))):
            d = json.load(open(f)); w = 2 * int(np.ceil(3 * sb)) + 1
            mv = sum(sum(c) + 2 * len(c) for c in d['cg_trials']); Wtot = d['trajW'][-1]; Fd = FL.F_A(N); Fb = 4.0 * N * N * w
            Ad, Ab = 2 * Fd * mv, 2 * Fb * mv; Wb = Wtot - (Ad - Ab)
            A_d.append(Ad / Wtot); A_b.append(Ab / Wb); bandedcheap.append(Wtot / Wb)
            tot = sum(sum(c) for c in d['cg_trials']); rj = sum(sum(c[:-1]) for c in d['cg_trials']); rej.append(rj / tot)
        a = float(np.median(A_b)); r = float(np.median(rej))
        rows['%s_%s' % (scale, cond)] = dict(n=len(A_d), A_share_dense=float(np.median(A_d)), A_share_banded=a, banded_vs_dense_cost_ratio=float(np.median(bandedcheap)),
                                             amdahl_cap_A_free_vs_banded=1 / (1 - a), amdahl_cap_A_free_vs_dense=1 / (1 - float(np.median(A_d))),
                                             rejected_cg_share_median=r, rejected_cg_share_range=[float(min(rej)), float(max(rej))], amdahl_cap_perfect_rejection_avoidance=1 / (1 - r))
json.dump(rows, open(sys.argv[1], 'w'), indent=1)
for k, v in rows.items(): print(k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()})
