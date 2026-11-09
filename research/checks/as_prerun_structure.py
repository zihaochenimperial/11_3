"""Structure-only completeness check before the single frozen-analyzer run (no MSE / no quality quantity): per arm, which of the 192 keys (or 96 for ORACLE_ys) are covered by a real unit file or an infeasible marker; marker validity per addendum E (M1)."""
import os, sys, json
IMGS = range(1, 25); KEYS = [(i, c, s) for i in IMGS for c in ('C1', 'C2', 'C3', 'C4') for s in (9001, 9002)]
root = sys.argv[1] if len(sys.argv) > 1 else 'outputs/AS-S2'
arms = {}
for base in (root, root + '-ORX'):
    for a in sorted(os.listdir(base)):
        d = os.path.join(base, a)
        if not os.path.isdir(d): continue
        real, mark, bad, ph, other = set(), {}, [], 0, 0
        for f in os.listdir(d):
            if not (f.startswith('i') and f.endswith('.json')) or f.endswith('.ckpt.json'): other += 1; continue
            r = json.load(open(os.path.join(d, f))); u = r.get('unit', {}); k = (u.get('img'), u.get('cond'), u.get('ns'))
            if 'placeholder_drain' in r: ph += 1
            elif r.get('status') == 'infeasible_restricted_set':
                mark[k] = r.get('empty_step')
                if a not in ('OMP_s', 'JOINT_s', 'BLOCK_s') or r.get('only') != 's' or not isinstance(r.get('empty_step'), int): bad.append(f)
            elif 'traj' in r or 'theta' in r: real.add(k)
            else: bad.append(f)
        arms[a] = (real, mark, bad, ph, other)
need = {'OMP': KEYS, 'BLOCK': KEYS, 'JOINT': KEYS, 'JOINT_FREE': KEYS, 'RAND': KEYS, 'OMP_b': KEYS, 'OMP_s': KEYS, 'JOINT_b': KEYS, 'JOINT_s': KEYS, 'FIXED_g3': KEYS, 'FIXED_g2': KEYS, 'FIXED_j25': KEYS, 'ORACLE_xs': KEYS, 'ORACLE_ys': [k for k in KEYS if k[2] == 9001]}
ok = True
for a, ks in need.items():
    real, mark, bad, ph, other = arms.get(a, (set(), {}, [], 0, 0)); miss = [k for k in ks if k not in real and k not in mark]
    print('%-12s real=%3d markers=%d placeholders=%d bad=%d missing=%d other_files=%d' % (a, len(real), len(mark), ph, len(bad), len(miss), other)); ok &= (not miss and not bad and ph == 0)
s0 = lambda a: {k for k, v in arms.get(a, (0, {}))[1].items() if v == 0}
print('step-0 marker sets equal OMP_s vs JOINT_s:', s0('OMP_s') == s0('JOINT_s'), len(s0('OMP_s')), len(s0('JOINT_s')))
print('markers OMP_s (key->step):', sorted(arms['OMP_s'][1].items())); print('markers JOINT_s (key->step):', sorted(arms['JOINT_s'][1].items()))
print('extra arm dirs:', sorted(set(arms) - set(need)))
print('STRUCTURE', 'OK' if ok and s0('OMP_s') == s0('JOINT_s') else 'PROBLEM')
