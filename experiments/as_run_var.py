"""AS contract v2.1 runner, variant "var" (FAIL-0023 / freeze addendum D): identical to experiments/as_run.py (sha 06f2615b...) except (1) restricted birth-only/split-only arms that run out of admissible candidates write a status=infeasible_restricted_set marker (with empty_step) instead of crashing; (2) a failing unit is reported and skipped instead of aborting the whole pool (exit code 1 at the end if any unit failed). The numerics of every feasible unit are untouched (a read-only wrapper around as_core.mask_for).
Original docstring: executes a deterministic plan of units with a process pool (BLAS threads = 1), resumable, one JSON per unit.
usage: as_run.py plan=<pilot|rules|variants|fixedk|initn|dose|oracle_s|oracle_full|oracle_full_ext|oracle_x_full> out=<dir> nproc=<n> [shard=<k>of<m>] [limit=<n>] [run=<run_id>]
Method arms read ONLY (y, op, sigma_n); evaluator-side ORACLE_x arms write to a SEPARATE sibling directory <out>-ORX (V17) and are the only arms handed the clean image."""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))
import numpy as np
import as_core as C, as_gen as G

COND = dict(G.COND); COND['D03'] = (0.3, 0.03)
IMGS = list(range(1, 25)); ALLC = ['C1', 'C2', 'C3', 'C4']
RULE_ARMS = ['OMP', 'BLOCK', 'JOINT', 'JOINT_FREE', 'RAND']
VAR_ARMS = ['OMP_b', 'OMP_s', 'BLOCK_b', 'BLOCK_s', 'JOINT_b', 'JOINT_s']
FIXED = ['FIXED_g3', 'FIXED_g2', 'FIXED_j25']
FULL6 = [(i, c) for i in (1, 9, 17) for c in ('C1', 'C4')]
FULL12 = FULL6 + [(i, c) for i in (2, 10, 18) for c in ('C1', 'C4')]


def plan(name):
    U = []
    def add(arm, imgs, conds, seeds):
        for i in imgs:
            for c in conds:
                for s in seeds: U.append(dict(arm=arm, img=i, cond=c, ns=s))
    if name == 'pilot':        # S1 (contract section 6): 2 images (1 edge, 9 tex) x C1,C4 x seed 9001 x {OMP-raw, BLOCK, JOINT, ORACLE_y-full}; timing and V gates only, no quality reading
        add('ORACLE_y_full', (1, 9), ('C1', 'C4'), (9001,))       # long units first so they start immediately
        for arm in ('OMP', 'BLOCK', 'JOINT'): add(arm, (1, 9), ('C1', 'C4'), (9001,))
    elif name == 'rules':
        for arm in RULE_ARMS: add(arm, IMGS, ALLC, (9001, 9002))
    elif name == 'variants':
        for arm in VAR_ARMS: add(arm, IMGS, ALLC, (9001, 9002))
    elif name == 'fixedk':
        for arm in FIXED: add(arm, IMGS, ALLC, (9001, 9002))
    elif name == 'initn':
        for arm in ('INITN_OMP', 'INITN_BLOCK', 'INITN_JOINT'): add(arm, IMGS, ALLC, (9001,))
    elif name == 'dose':
        for arm in ('OMP', 'BLOCK', 'JOINT'): add(arm, IMGS, ('D03',), (9001,))
    elif name == 'oracle_s':
        add('ORACLE_ys', IMGS, ALLC, (9001,)); add('ORACLE_xs', IMGS, ALLC, (9001, 9002))
    elif name == 'oracle_full':
        for (i, c) in FULL6: U.append(dict(arm='ORACLE_y_full', img=i, cond=c, ns=9001))
    elif name == 'oracle_full_ext':
        for (i, c) in FULL12[6:]: U.append(dict(arm='ORACLE_y_full', img=i, cond=c, ns=9001))
    elif name == 'oracle_x_full':      # CONDITIONAL: only if the analyzer reports Gate-0 shortfall of ORACLE_xs
        for (i, c) in FULL12: U.append(dict(arm='ORACLE_x_full', img=i, cond=c, ns=9001))
    else:
        raise SystemExit('unknown plan ' + name)
    return U


def unit_dir(out, u):
    o = out.rstrip('/\\')
    return (o + '-ORX') if u['arm'].startswith('ORACLE_x') else o


def unit_path(out, u):
    return os.path.join(unit_dir(out, u), u['arm'], 'i%02d_%s_s%d.json' % (u['img'], u['cond'], u['ns']))


class EmptyRestricted(Exception):
    def __init__(self, step): super().__init__('empty restricted candidate set at step %d' % step); self.step = step


def do_unit(args):
    u, out, runid = args
    p = unit_path(out, u)
    if os.path.exists(p): return p, 0.0, 'skip'
    sb, sn = COND[u['cond']]; op = C.Op(sb); y = None
    arm = u['arm']; t0 = time.time(); ck = p[:-5] + '.ckpt.json'
    if arm.startswith('ORACLE_x'):
        clean = G.clean_image(u['img']); y = G.noisy_obs(op, clean, sn, u['ns'], u['img'])   # evaluator-side only
    else:
        y = G.noisy_obs(op, G.clean_image(u['img']), sn, u['ns'], u['img'])                 # clean image is consumed here only to synthesise y; never passed on
    if arm in RULE_ARMS: res = C.run_path(y, op, sn, arm, seed=u['img'] * 100 + u['ns'] % 100, diag_top5=(arm == 'JOINT' and u['ns'] == 9001 and u['cond'] != 'D03'))
    elif arm in VAR_ARMS:
        r, o = arm.split('_'); st = dict(step=-1); orig_mask = C.mask_for
        def _mask(cands, only):
            m = orig_mask(cands, only); st['step'] += 1
            if only is not None and not bool(m.any()): raise EmptyRestricted(st['step'])
            return m
        C.mask_for = _mask
        try:
            res = C.run_path(y, op, sn, r, only=o, seed=u['img']); res['only'] = o
        except EmptyRestricted as e:
            res = dict(status='infeasible_restricted_set', empty_step=e.step, rule=r, only=o)
        finally:
            C.mask_for = orig_mask
    elif arm.startswith('INITN_'): res = C.run_path(y, op, sn, arm.split('_')[1], init_sigma=3.0)
    elif arm in FIXED: res = C.run_fixed_k(y, op, sn, arm.split('_')[1])
    elif arm == 'ORACLE_ys': res = C.run_oracle_y(y, op, sn, 'short', ckpt=ck)
    elif arm == 'ORACLE_y_full': res = C.run_oracle_y(y, op, sn, 'full', ckpt=ck)
    elif arm in ('ORACLE_xs', 'ORACLE_x_full'):
        import as_oracle_x as X
        res = X.run_oracle_x(y, op, sn, clean, 'short' if arm == 'ORACLE_xs' else 'full', ckpt=ck)
    else: raise SystemExit('bad arm ' + arm)
    res.update(unit=u, sb=sb, sn=sn, run_id=runid, wall=time.time() - t0)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + '.tmp'; json.dump(res, open(tmp, 'w')); os.replace(tmp, p)
    if os.path.exists(ck):
        try: os.remove(ck)
        except OSError: pass
    return p, res['wall'], 'done'


def do_unit_safe(args):
    try: return do_unit(args)
    except Exception:
        import traceback; return args[0], 0.0, 'ERROR ' + traceback.format_exc().replace('\n', ' | ')


def main():
    kv = dict(a.split('=', 1) for a in sys.argv[1:] if '=' in a)
    U = plan(kv['plan']); out = kv.get('out', os.path.join(ROOT, 'outputs', 'AS-S2')); n = int(kv.get('nproc', '2')); runid = kv.get('run', 'n/a')
    if 'shard' in kv:
        k, m = kv['shard'].split('of'); U = [u for j, u in enumerate(U) if j % int(m) == int(k)]
    if 'limit' in kv: U = U[:int(kv['limit'])]
    print('plan', kv['plan'], 'units', len(U), 'out', out, 'nproc', n, flush=True)
    t0 = time.time(); tasks = [(u, out, runid) for u in U]; nerr = 0
    if n <= 1:
        for t in tasks:
            r = do_unit_safe(t); nerr += str(r[2]).startswith('ERROR'); print(r, flush=True)
    else:
        import multiprocessing as mp
        with mp.get_context('spawn').Pool(n, maxtasksperchild=4) as pool:
            for r in pool.imap_unordered(do_unit_safe, tasks): nerr += str(r[2]).startswith('ERROR'); print(r, round(time.time() - t0), flush=True)
    print('finished', round(time.time() - t0), 's', 'errors', nerr, flush=True)
    if nerr: sys.exit(1)


if __name__ == '__main__':
    main()
