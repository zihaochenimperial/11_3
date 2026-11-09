"""Terminal-review checks requested by the Opus gate (R2, R4, R5, R6, suspicion points 1,2,4,5,6): descriptive, dev-only, no confirm access.
(a) R6/susp.4: the frozen B (refl_B) IS banded (truncated Gaussian, half-width ceil(3 sb), reflect folding): a sparse (CSR) copy of the SAME B reproduces A X exactly; report nnz(B), max abs difference, and the banded flop count 4 N nnz(B).
(b) R2/susp.1,2: censor_rate per arm and the both-hit-subset readings (iteration ratio and W ratio vs the strongest control D0w) from outputs/TRN-SS*/ at k=8 and 16.
(c) susp.6: share of CG trials hitting maxcg (>=400) in B* runs, split by rejected/accepted. (d) R5: G-A f_iter and mv/outer recomputed under the banded-A cost (same operator).
Usage: python experiments/trn_terminal_checks.py outputs/TRN-MC/terminal_checks.json"""
import glob, json, sys
import numpy as np
import scipy.sparse as sp
sys.path.insert(0, 'src'); sys.path.insert(0, 'experiments')
import geo_core as GC, geo_flops as FL
out = {}
# (a)
for N, sb in ((64, 1), (64, 2), (96, 1), (96, 2)):
    op = GC.Op(N, sb); Bs = sp.csr_matrix(op.B); rng = np.random.default_rng(1); X = rng.standard_normal((N, N)); Y = op.apply(X); Ys = (Bs @ (Bs @ X.T).T.T) if False else (Bs @ (Bs @ X.T).T)
    # A X = B X B^T = (B (B X^T)^T) since (B X B^T) = B (B X^T)^T
    Ys2 = Bs @ ((Bs @ X.T).T)
    out['same_operator_N%d_sb%d' % (N, sb)] = dict(nnz_B=int(Bs.nnz), band_bound_N_2r1=N * (2 * int(np.ceil(3 * sb)) + 1), max_abs_diff=float(np.abs(Y - Ys2).max()), rel_diff=float(np.abs(Y - Ys2).max() / np.abs(Y).max()),
                                                 flops_dense=FL.F_A(N), flops_sparse_exact=4.0 * N * Bs.nnz, ratio_dense_over_sparse=FL.F_A(N) / (4.0 * N * Bs.nnz))
# (b) censor rates and both-hit subset readings
for k, d in ((8, 'outputs/TRN-SS'), (16, 'outputs/TRN-SS-k16')):
    S = []
    for f in sorted(glob.glob(d + '/*.json')):
        j = json.load(open(f)); S += [(j['img'], j['cond'], s) for s in j['states'] if not s['skipped']]
    arms = ['D0', 'D0w', 'D0b', 'D0s', 'D2', 'D4lam', 'D46_r4', 'D3x', 'D3p_n3', 'D3p_n8']
    hit = lambda s, a: s['arms'][a]['hits']['0.1']
    cr = {a: float(np.mean([hit(s, a) is None for _, _, s in S])) for a in arms}
    bh = {}
    for a in arms:
        ri, rw = [], []
        for _, _, s in S:
            hc, ha = hit(s, 'D0w'), hit(s, a)
            if hc is not None and ha is not None and ha[0] > 0 and hc[0] > 0: ri.append(hc[0] / ha[0]); rw.append(hc[1] / ha[1])
        bh[a] = dict(n=len(rw), iter_ratio_median=float(np.median(ri)) if ri else None, W_ratio_median=float(np.median(rw)) if rw else None)
    out['same_state_k%d' % k] = dict(n_states=len(S), censor_rate_rho0p1=cr, both_hit_vs_D0w=bh)
# (c),(d)
for scale, dirn, N in (('M', 'outputs/TRN-S0/s0', 64), ('L', 'outputs/TRN-S0L/s0', 96)):
    for cond, sb in (('C1', 1), ('C4', 2)):
        cap_rej = cap_acc = nrej = nacc = 0; fb = []; mvb = []; fd = []
        for f in sorted(glob.glob('%s/*_%s_%s_D0w*.json' % (dirn, cond, scale))):
            d = json.load(open(f)); op = GC.Op(N, sb); nnzB = sp.csr_matrix(op.B).nnz
            for c in d['cg_trials']:
                for i, v in enumerate(c):
                    if i < len(c) - 1: nrej += 1; cap_rej += (v >= 400)
                    else: nacc += 1; cap_acc += (v >= 400)
            ct = np.array(d['cats'], float); tot = ct[:, [0, 1, 2, 4, 5]].sum(); fd.append(ct[:, 4].sum() / tot)
            mv = sum(sum(c) + 2 * len(c) for c in d['cg_trials']); Wtot = d['trajW'][-1]; Ad = 2 * FL.F_A(N) * mv; Ab = 2 * 4.0 * N * nnzB * mv
            Wb = Wtot - (Ad - Ab); Wcg_b = ct[:, 4].sum() - (Ad - Ab); fb.append(Wcg_b / (tot - (Ad - Ab)))
        out['Bstar_%s_%s' % (scale, cond)] = dict(n=len(fd), maxcg_hit_share_rejected=cap_rej / max(nrej, 1), maxcg_hit_share_accepted=cap_acc / max(nacc, 1), f_iter_dense=float(np.median(fd)), f_iter_banded_same_operator=float(np.median(fb)))
json.dump(out, open(sys.argv[1], 'w'), indent=1)
for k, v in out.items(): print(k, json.dumps(v)[:420])
