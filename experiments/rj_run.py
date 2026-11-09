"""RJ runner / reducer (contract RJ candidate v0.1). DEV images only (assertion); no confirm access.
Phases: tune (all family configs on 301-306 x C1,C4), eval (family bests + B0 + OKdF + OS (+ OKeff descriptive) on 301-312 x C1,C4), chk (same arms on 313-320; needs an F_ref table for those images).
Usage: python experiments/rj_run.py run --phase tune --shard 0 --nshards 2 --out outputs/RJ ; python experiments/rj_run.py reduce --phase tune --out outputs/RJ
One JSON per (phase-independent) (img, cond, config id): outputs/RJ/runs/<img>_<cond>_<cfgid>.json (re-used across phases; a run is never repeated)."""
import argparse, glob, json, os, sys, time, itertools
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'src')); sys.path.insert(0, HERE)
import numpy as np
import geo_core as GC, trn_gen as TG, rj_loop as RJ
import trn_s0 as S0

MAXOUT = 400; TOL = 1e-3; NIMG_TUNE = list(range(301, 307)); NIMG_SEL = list(range(301, 313)); NIMG_CHK = list(range(313, 321))
BASE = dict(kappa0=0.1, f=3, eps_r=0.1, maxcg=400, gdiv=3, warm=True)


def families():
    F = {}
    F['B'] = {'B_k%g_f%g' % (k0, f): dict(kappa0=k0, f=f) for k0 in (0.03, 0.1, 0.3) for f in (3, 10)}
    F['G'] = {'G_g%g_f%g' % (g, f): dict(gdiv=g, f=f) for g in (1.5, 2, 1) for f in (3, 10)}
    F['N'] = {'N_k%g' % k0: dict(nielsen=True, kappa0=k0) for k0 in (0.03, 0.1, 0.3)}
    F['S'] = {'S_m%d_g%g' % (m, g): dict(early_m=m, gdiv=g) for m in (4, 8, 16) for g in (3, 2)}
    F['D'] = {'D_t%g_e%g' % (t, e): dict(dq_tau=t, eps_r=e) for t in (0.1, 0.03, 0.01) for e in (0.1, 0.03)}
    F['W'] = {'W_g%g_k%g' % (gm, k0): dict(ew_gamma=gm, kappa0=k0) for gm in (0.3, 0.5, 1.0) for k0 in (0.1, 0.3)}
    F['C'] = {**{'C_c%d_r0' % c: dict(cc=c) for c in (2, 4, 8)}, **{'C_c%d_r1f' % c: dict(cc=c, reuse=True, cc_first_only=True) for c in (2, 4, 8)}}
    F['X'] = {'X1_g2_m8': dict(gdiv=2, early_m=8), 'X2_g1.5_m16': dict(gdiv=1.5, early_m=16), 'X3f_g2_c4_r': dict(gdiv=2, cc=4, reuse=True, cc_first_only=True), 'X4f_g2_m8_c4_r': dict(gdiv=2, early_m=8, cc=4, reuse=True, cc_first_only=True)}
    return F


ORACLE_KINDS = {'OKdF': dict(oracle='dF'), 'OKb': dict(oracle='beta', beta=0.5), 'OKSb': dict(oracle='sbeta', beta=0.5, oracle_m=4), 'OS': dict(free_reject=True)}


def all_cfgs():
    d = {}
    for fam, cs in families().items():
        for cid, ex in cs.items(): d[cid] = (fam, dict(BASE, **ex))
    return d


def cfg_of(cid):
    """'kind@base' -> (ORACLE, base cfg + oracle options); plain ids -> deterministic family configs."""
    if '@' in cid:
        kind, base = cid.split('@'); return 'ORACLE', dict(all_cfgs()[base][1], **ORACLE_KINDS[kind])
    return all_cfgs()[cid]


B0ID = 'B_k0.1_f3'


def fref_lookup(path):
    return {(r['img'], r['cond']): r for r in json.load(open(path))['rows']}


def run_path(out, img, cond, cid): return os.path.join(out, 'runs', '%d_%s_%s.json' % (img, cond, cid))


def run_one(img, cond, cid, fr, out):
    fam, cfg = cfg_of(cid); row = fr[(img, cond)]; tgt = row['F_ref'] + S0.TOL * (row['F0'] - row['F_ref'])
    P, th0, xclean = S0.problem(img, cond, 'M'); sb = TG.COND[cond][0]; t = time.time()
    o = RJ.rj_solve(P, th0, cfg, max_outer=MAXOUT, F_target=tgt); wall = time.time() - t; log = o['cnt'].get('log', [])
    ws = RJ.w_sparse(o['traj'], P.N, sb)
    tinfo = [r['tinfo'] for r in log]
    d = dict(img=img, cond=cond, cid=cid, fam=fam, cfg=cfg, stop=o['stop'], hit=bool(o['stop'] == 'target'), outer=len(o['traj']) - 1, F0=o['traj'][0][1], F_final=o['F'], F_ref=row['F_ref'], tgt=tgt, rej=o['rej'], wall=(None if fam == 'ORACLE' else wall),
             W_dense=o['traj'][-1][6], W_sp=ws[-1], trajF=[r[1] for r in o['traj']], trajW=[r[6] for r in o['traj']], trajWsp=ws, trajA=[r[3] for r in o['traj']], tinfo=tinfo,
             cats=[[r['W_jac'], r['W_rhs'], r['W_setup'], r['W_cg'], r['W_acc']] for r in log], kap_acc=[r['kap_acc'] for r in log], sel=[r['sel'] for r in log], fallback=[r['fallback'] for r in log], probe_reasons=[([q['reason'] for q in r['probe']] if r['probe'] else None) for r in log], psnr_final=S0.psnr(P.render(o['theta']), xclean))      # psnr: evaluation side, descriptive only
    json.dump(d, open(run_path(out, img, cond, cid), 'w'))
    return d


def job_list(phase, cids, imgs, conds=('C1', 'C4')):
    return [(i, c, cid) for cid in cids for i in imgs for c in conds]


def load_runs(out):
    return {(d['img'], d['cond'], d['cid']): d for d in (json.load(open(p)) for p in glob.glob(os.path.join(out, 'runs', '*.json')))}


def wval(d): return d['W_sp'] if d['hit'] else float('inf')


def family_best(runs, fam_cfgs, imgs):
    """best config id per family on (imgs x C1,C4): min median (censored = inf), ties -> fewer censored -> lower mean finite W."""
    best = {}
    for fam, cs in fam_cfgs.items():
        rows = []
        for cid in cs:
            ws = [wval(runs[(i, c, cid)]) for i in imgs for c in ('C1', 'C4') if (i, c, cid) in runs]
            if len(ws) != len(imgs) * 2: continue
            fin = [w for w in ws if np.isfinite(w)]
            rows.append((float(np.median(ws)), sum(not np.isfinite(w) for w in ws), float(np.mean(fin)) if fin else float('inf'), cid))
        if rows: best[fam] = min(rows)[3]; best[fam + '_table'] = sorted(rows)
    return best


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['run', 'reduce', 'list']); ap.add_argument('--phase', required=True); ap.add_argument('--shard', type=int, default=0); ap.add_argument('--nshards', type=int, default=1)
    ap.add_argument('--out', default='outputs/RJ'); ap.add_argument('--fref', default='outputs/TRN-S0/fref_table.json'); ap.add_argument('--best', default=None, help='tune_REDUCE.json for the eval/chk phases'); ap.add_argument('--conds', nargs='*', default=['C1', 'C4']); ap.add_argument('--cids', nargs='*', default=None); ap.add_argument('--imgs', type=int, nargs='*', default=None)
    a = ap.parse_args(); os.makedirs(os.path.join(a.out, 'runs'), exist_ok=True); fam = families(); fr = fref_lookup(a.fref)
    if a.phase == 'tune': jobs = job_list('tune', [cid for cs in fam.values() for cid in cs], NIMG_TUNE)
    elif a.phase in ('eval_det', 'chk_det'):
        B = json.load(open(os.path.join(a.out, 'tune_REDUCE.json')))['best_ids']; imgs = NIMG_SEL if a.phase == 'eval_det' else NIMG_CHK
        cids = sorted(set(list(B.values()) + [B0ID])) if a.phase == 'eval_det' else sorted({json.load(open(os.path.join(a.out, 'sc.json')))['sc'], B0ID}); jobs = job_list(a.phase, cids, imgs)
    elif a.phase in ('eval_orc', 'chk_orc'):
        sc = json.load(open(os.path.join(a.out, 'sc.json')))['sc']; imgs = NIMG_SEL if a.phase == 'eval_orc' else NIMG_CHK
        cids = ['OKdF@' + sc, 'OKb@' + sc, 'OKSb@' + sc, 'OS@' + sc, 'OKdF@' + B0ID, 'OS@' + B0ID]
        sce = json.load(open(os.path.join(a.out, 'sc.json'))).get('sc_elig')
        if sce and sce != sc: cids += ['OKdF@' + sce, 'OKb@' + sce, 'OKSb@' + sce]             # clarification C1 (descriptive Gate O-elig): oracle arms composed on the best control with censoring <= 10%
        jobs = job_list(a.phase, cids, imgs)
    else: raise SystemExit('unknown phase')
    if a.cmd == 'list':
        print(len(jobs)); return
    if a.cmd == 'run':
        mine = [j for n, j in enumerate(jobs) if n % a.nshards == a.shard and j[1] in a.conds and (a.cids is None or j[2] in a.cids) and (a.imgs is None or j[0] in a.imgs)]
        for img, cond, cid in mine:
            if os.path.exists(run_path(a.out, img, cond, cid)): continue
            d = run_one(img, cond, cid, fr, a.out); print(img, cond, cid, d['stop'], d['outer'], 'Wsp %.3e' % d['W_sp'], ('wall %.0fs' % d['wall']) if d['wall'] is not None else 'wall n/a (oracle)', flush=True)
        return
    if a.cmd == 'reduce' and a.phase == 'tune':
        runs = load_runs(a.out); best = family_best(runs, fam, NIMG_TUNE); ids = {k: v for k, v in best.items() if not k.endswith('_table')}
        json.dump(dict(phase='tune', n_runs=len(runs), best_ids=ids, tables={k: v for k, v in best.items() if k.endswith('_table')}), open(os.path.join(a.out, 'tune_REDUCE.json'), 'w'), indent=1)
        print(json.dumps(ids, indent=1)); return


if __name__ == '__main__':
    main()
