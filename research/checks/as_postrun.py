"""AS S2 post-run bookkeeping (no quality quantity is ever computed).
usage: as_postrun.py repro [s1=outputs/AS-S1] [s2=outputs/AS-S2]  -> equality-only comparison of the 16 pilot units (images 1,9 x C1,C4 x seed 9001 x OMP/BLOCK/JOINT/ORACLE_y_full) between the S1 pilot and S2 (trajectory lists compared for exact equality; prints only equal/not-equal/missing)
       as_postrun.py placeholders [root=outputs/AS-S2] [dest=outputs/AS-S2-CUT] [apply=0|1] -> list (apply=0) or mv (apply=1) files containing placeholder_drain, preserving the relative path; infeasible_restricted_set markers are NEVER moved."""
import os, sys, json, glob, shutil
kv = dict(a.split('=', 1) for a in sys.argv[2:] if '=' in a); mode = sys.argv[1]
if mode == 'repro':
    s1 = kv.get('s1', 'outputs/AS-S1'); s2 = kv.get('s2', 'outputs/AS-S2'); res = []
    for arm in ('OMP', 'BLOCK', 'JOINT', 'ORACLE_y_full'):
        for i in (1, 9):
            for c in ('C1', 'C4'):
                f = 'i%02d_%s_s9001.json' % (i, c); p1 = os.path.join(s1, arm, f); p2 = os.path.join(s2, arm, f)
                if not (os.path.exists(p1) and os.path.exists(p2)): res.append((arm, f, 'missing(%s%s)' % ('S1 ' if not os.path.exists(p1) else '', 'S2' if not os.path.exists(p2) else ''))); continue
                a = json.load(open(p1)); b = json.load(open(p2))
                if 'placeholder_drain' in a or 'placeholder_drain' in b: res.append((arm, f, 'placeholder')); continue
                res.append((arm, f, 'EQUAL' if a['traj'] == b['traj'] else 'DIFFERENT'))
    for r in res: print(*r)
    n = {k: sum(1 for r in res if r[2] == k) for k in ('EQUAL', 'DIFFERENT', 'placeholder')}; n['missing'] = sum(1 for r in res if r[2].startswith('missing'))
    print('SUMMARY', n, 'of', len(res))
elif mode == 'placeholders':
    root = kv.get('root', 'outputs/AS-S2').rstrip('/\\'); dest = kv.get('dest', 'outputs/AS-S2-CUT'); apply = kv.get('apply', '0') == '1'; moved = []; kept_inf = 0
    for p in sorted(glob.glob(os.path.join(root, '*', '*.json'))):
        if p.endswith('.ckpt.json'): continue
        d = json.load(open(p))
        if d.get('status') == 'infeasible_restricted_set': kept_inf += 1; continue
        if 'placeholder_drain' in d:
            rel = os.path.relpath(p, root); q = os.path.join(dest, rel); moved.append((p, q))
            if apply: os.makedirs(os.path.dirname(q), exist_ok=True); shutil.move(p, q)
    print('placeholders', len(moved), 'applied' if apply else 'dry-run', '| infeasible markers kept in place:', kept_inf)
    by = {}
    for p, q in moved: by[p.split(os.sep)[-2]] = by.get(p.split(os.sep)[-2], 0) + 1
    print(by)
else: raise SystemExit('unknown mode')
