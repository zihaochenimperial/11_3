"""AS S1 pilot readout (contract section 6): ONLY timing and V-gate bookkeeping. This script never reads trajectories/theta, never renders, never computes MSE or any quality quantity.
usage: as_pilot_readout.py root=<AS-S1 dir> [vm_ratio=<host/VM speed ratio override>]   -> prints JSON + budget projection for the S2 plan."""
import os, sys, json, glob, collections

kv = dict(a.split('=', 1) for a in sys.argv[1:] if '=' in a)
root = kv['root'].rstrip('/\\')
rows = []
for p in sorted(glob.glob(os.path.join(root, '*', '*.json'))):
    if p.endswith('.ckpt.json'): continue
    d = json.load(open(p)); u = d['unit']
    # keep ONLY bookkeeping fields (drop traj / theta immediately)
    rows.append(dict(arm=u['arm'], img=u['img'], cond=u['cond'], wall=d['wall'], logs=[{k: v for k, v in lg.items() if k in ('cand_hash', 'n_cand', 'n_trials', 'lm', 'v10_stable', 'n_clamped_parent', 'n_below_floor', 'stat', 't_score', 't_refit', 'step')} for lg in d.get('logs', [])]))
by = collections.defaultdict(list)
for r in rows: by[r['arm']].append(r)
out = dict(n_units=len(rows), arms={})
for a, rs in by.items():
    w = [r['wall'] for r in rs]; o = dict(n=len(rs), wall_mean=sum(w) / len(w), wall_max=max(w), wall_min=min(w))
    ts = sum(lg.get('t_score', 0.0) for r in rs for lg in r['logs']); tr = sum(lg.get('t_refit', 0.0) for r in rs for lg in r['logs'])
    if ts or tr: o['score_s_total'] = ts; o['refit_s_total'] = tr
    o['n_trials_max'] = max((lg.get('n_trials', 0) for r in rs for lg in r['logs']), default=0)
    o['lm_capped_steps'] = sum(int(lg['lm']['capped']) for r in rs for lg in r['logs'] if 'lm' in lg)
    o['clamped_parent_total'] = sum(lg.get('n_clamped_parent', 0) for r in rs for lg in r['logs']); o['below_floor_total'] = sum(lg.get('n_below_floor', 0) for r in rs for lg in r['logs'])
    st = [lg['stat'] for r in rs for lg in r['logs'] if 'stat' in lg]; o['stat_all_finite'] = all(s == s and abs(s) < 1e9 for s in st) if st else None
    out['arms'][a] = o
# V16: step-0 candidate-set hash identical across arms within a unit (img, cond)
hs = collections.defaultdict(set)
for r in rows:
    if r['logs'] and 'cand_hash' in r['logs'][0]: hs[(r['img'], r['cond'])].add(r['logs'][0]['cand_hash'])
out['V16'] = dict(units=len(hs), mismatches=sum(1 for v in hs.values() if len(v) != 1))
# V10 stability (JOINT arm)
v = [all(lg['v10_stable'].values()) for r in by.get('JOINT', []) for lg in r['logs'] if lg.get('v10_stable')]
out['V10_stable_rate'] = (sum(v) / len(v)) if v else None; out['V10_n'] = len(v)
# budget projection for S2 (CPU-seconds per arm family; fixed/variants/initn/oracle_s measured on the 1-core VM in S0 and scaled by host/VM ratio from OMP)
A = out['arms']; vm_omp = 5.5; ratio = float(kv['vm_ratio']) if 'vm_ratio' in kv else (A['OMP']['wall_mean'] / vm_omp if 'OMP' in A else 1.0)
cheap = (A['OMP']['wall_mean'] + A['BLOCK']['wall_mean']) / 2 if 'OMP' in A and 'BLOCK' in A else None
proj = {}
if cheap:
    proj['rules'] = 192 * (A['OMP']['wall_mean'] + A['BLOCK']['wall_mean'] + A['JOINT']['wall_mean'] + 2 * cheap)      # OMP, BLOCK, JOINT, JOINT_FREE~cheap, RAND~cheap
    proj['variants'] = 192 * 6 * 0.7 * cheap; proj['fixedk'] = 192 * 3 * 4.0 * ratio; proj['initn'] = 96 * 3 * cheap; proj['dose'] = 24 * (A['OMP']['wall_mean'] + A['BLOCK']['wall_mean'] + A['JOINT']['wall_mean'])
    proj['oracle_s'] = 96 * 74.0 * ratio + 192 * 41.0 * ratio
    if 'ORACLE_y_full' in A: proj['oracle_full6'] = 6 * A['ORACLE_y_full']['wall_mean']; proj['oracle_full_ext6'] = 6 * A['ORACLE_y_full']['wall_mean']; proj['oracle_x_full_conditional12'] = 12 * A['ORACLE_y_full']['wall_mean']
    tot = sum(v for k, v in proj.items() if k not in ('oracle_full_ext6', 'oracle_x_full_conditional12')); proj['total_unconditional_cpu_h'] = tot / 3600.0
    proj['wall_h_at_6_procs'] = tot / 3600.0 / 6; proj['with_ext_and_conditional_cpu_h'] = (tot + proj.get('oracle_full_ext6', 0) + proj.get('oracle_x_full_conditional12', 0)) / 3600.0
    proj['host_over_VM_ratio'] = ratio
out['S2_budget_projection_cpu_seconds'] = proj
print(json.dumps(out, indent=1))
