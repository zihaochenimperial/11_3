"""F_ref for the dev-chk images 313-320 x C1,C4 (contract RJ v1 section 2): same recipe as trn_fref_table (C5 evaluation reference) = min{B* 100-outer final, D0 (PCG-J, eps_r=1e-3, B* kappa0,f) 100-outer final},
computed with the frozen TRN arm only (no RJ arm touches F_ref). Writes <out>/fref_chk_table.json with the same row layout as outputs/TRN-S0/fref_table.json. Dev-chk images only."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'src')); sys.path.insert(0, HERE)
import numpy as np
import trn_s0 as S0, trn_gen as TG

out = sys.argv[1] if len(sys.argv) > 1 else 'outputs/RJ'; shard = int(sys.argv[2]) if len(sys.argv) > 2 else 0; nsh = int(sys.argv[3]) if len(sys.argv) > 3 else 1
os.makedirs(os.path.join(out, 'fref_chk'), exist_ok=True); jobs = [(i, c) for i in TG.DEV_CHK_IMGS for c in ('C1', 'C4')]
for n, (i, c) in enumerate(jobs):
    if n % nsh != shard: continue
    pth = os.path.join(out, 'fref_chk', '%d_%s.json' % (i, c))
    if os.path.exists(pth): continue
    b = S0.run_one(i, c, 'M', 'D0w', 0.1, 3, 0.1, maxout=100); d = S0.run_one(i, c, 'M', 'D0', 0.1, 3, 1e-3, maxout=100)
    json.dump(dict(img=i, cond=c, bstar={k: b[k] for k in ('F0', 'F_final', 'psnr_final', 'trajF')}, d0tight={k: d[k] for k in ('F_final', 'psnr_final')}), open(pth, 'w')); print(i, c, flush=True)
if nsh == 1 or shard == 0:
    rows = []
    for i, c in jobs:
        pth = os.path.join(out, 'fref_chk', '%d_%s.json' % (i, c))
        if not os.path.exists(pth): continue
        d = json.load(open(pth)); b, t = d['bstar'], d['d0tight']; Fref = min(b['F_final'], t['F_final']); tr = np.array(b['trajF']); drop10 = float(tr[-11] - tr[-1]) if len(tr) > 11 else float('nan')
        rows.append(dict(img=i, cond=c, F0=b['F0'], F_Bstar=b['F_final'], F_D0tight=t['F_final'], F_ref=Fref, which='Bstar' if b['F_final'] <= t['F_final'] else 'D0tight', last10_drop_rel=drop10 / (b['F0'] - Fref), not_converged=bool(drop10 > 1e-3 * (b['F0'] - Fref))))
    json.dump(dict(rows=rows), open(os.path.join(out, 'fref_chk_table.json'), 'w'), indent=1)
