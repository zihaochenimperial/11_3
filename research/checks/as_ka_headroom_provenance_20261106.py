"""Provenance for the K-a 'oracle gain fraction' numbers quoted in AS_KA_RESULT (observation-space RESIDUAL ENERGY, not clean-image MSE).
gain fraction = realised/(1/2 |r|^2) = 1 - |r_new|^2/|r|^2 (y-space). Reads ka_out/ (v1 realised value, n=270) and ka_out2/ (rule-neutral v2, n=108)."""
import json, glob, numpy as np
for d in ('ka_out', 'ka_out2'):
    og = []; rc = []; jc = []
    for f in sorted(glob.glob(f'research/checks/{d}/sb*_sp*.json')):
        for sc in json.load(open(f)):
            real = np.array([c['real'] for c in sc['cands']]); den = 0.5 * sc['r2']
            og.append(real.max() / den)
            for r, l in (('raw_c1', rc), ('joint_c1', jc)):
                s = np.array([c[r] for c in sc['cands']]); l.append(real[np.argmax(s)] / den)
    print(d, 'oracle gain frac of 1/2|r|^2: mean %.3f | raw_c1 %.3f | joint_c1 %.3f | n=%d' % (np.mean(og), np.mean(rc), np.mean(jc), len(og)))
