"""C5 evaluation reference F_ref(img,cond) = min{B* 100-outer final, D0 (PCG-J, eps_r=1e-3, B* kappa0,f) 100-outer final}; flags 'F_ref not converged' when B*'s last-10-outer decrease > 1e-3*(F0-F_ref).
Reads outputs/TRN-S0/s0 (B* runs) and outputs/TRN-S0/fref (D0 eps_r=1e-3). Post-freeze analysis helper (no confirm access)."""
import glob, json, os, sys
import numpy as np
out = sys.argv[1] if len(sys.argv) > 1 else 'outputs/TRN-S0'
R = json.load(open(os.path.join(out, 's0_REDUCE.json'))); b = R['bstar']
rows = []
for f in sorted(glob.glob(os.path.join(out, 'fref', '*.json'))):
    d = json.load(open(f)); img, cond = d['img'], d['cond']
    bs = json.load(open(os.path.join(out, 's0', '%d_%s_M_%s_%g_%d_%g.json' % (img, cond, b['arm'], b['kappa0'], b['f'], b['eps_r']))))
    Fref = min(bs['F_final'], d['F_final']); tr = np.array(bs['trajF']); drop10 = float(tr[-11] - tr[-1]) if len(tr) > 11 else float('nan')
    rows.append(dict(img=img, cond=cond, F0=bs['F0'], F_Bstar=bs['F_final'], F_D0tight=d['F_final'], F_ref=Fref, which='Bstar' if bs['F_final'] <= d['F_final'] else 'D0tight', last10_drop_rel=drop10 / (bs['F0'] - Fref),
                     not_converged=bool(drop10 > 1e-3 * (bs['F0'] - Fref)), psnr_Bstar=bs['psnr_final'], psnr_D0tight=d['psnr_final']))
json.dump(dict(bstar=b, rows=rows), open(os.path.join(out, 'fref_table.json'), 'w'), indent=1)
n = len(rows); nc = sum(r['not_converged'] for r in rows)
print('n=%d, F_ref from B*: %d, from D0(1e-3): %d, not_converged: %d' % (n, sum(r['which'] == 'Bstar' for r in rows), sum(r['which'] == 'D0tight' for r in rows), nc))
for r in rows: print(r['img'], r['cond'], 'F0=%.4g B*=%.5g D0t=%.5g Fref=%.5g (%s) last10drop/(F0-Fref)=%.2e %s psnrB*=%.2f psnrD0t=%.2f' % (r['F0'], r['F_Bstar'], r['F_D0tight'], r['F_ref'], r['which'], r['last10_drop_rel'], 'NOT-CONV' if r['not_converged'] else '', r['psnr_Bstar'], r['psnr_D0tight']))
