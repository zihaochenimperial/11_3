"""F0 runner for the FROZEN contract v2 (contracts/F0_CONTRACT.md; sha256 in contracts/F0_CONTRACT.sha256).
Refuses to run if the contract file hash differs from the recorded one. Stages: pilot (D1, S in {8,1024}, M=32), pilot128 (C2 one-time rerun, M=128), full (Stage 1).
Writes outputs/F0-<stage>-<tag>/ (atomically reserved with os.makedirs(exist_ok=False), never overwritten): one npz per (kind, image, S, extra) + meta.json.
Fitters (src/gsfit.py, src/plin.py) only ever see (y, omega, S/I, cfg); the clean image is used here only to synthesise y / e and is never passed to a fitter.
usage (via pump py job): python experiments/f0_run.py --stage=pilot --tag=p1 --workers=18
debug: --debug_steps=5 --max_tasks=6 --tag=smoke  -> outputs/DEBUG-F0-... (never evidence)."""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_v] = '1'   # 18 single-thread workers: no BLAS oversubscription (inherited by pool workers)
import argparse, json, sys, time, hashlib, platform
from dataclasses import asdict, replace
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.f0_config import F0Config, cfg_hash  # noqa: E402
from src import synth  # noqa: E402  (clean images: used here only to build y)

IMG_IDX = {'D1': 0, 'D2': 1, 'D3': 2, 'W0': 3, 'W1': 4}
GEN_SEED = {'D1': 1001, 'D2': 1002, 'D3': 1003}
EPS_REL = (0.01, 0.03, 0.1, 0.3, 1.0)
EPSF_PILOT = (0.003, 0.01, 0.03)
FIT_EQUIV_FULL = 41000  # rough fit-equivalent count of Stage 1 (contract section 4), used only for the wall-clock projection in the analysis


def stage_spec(stage, epsf):
    if stage in ('pilot', 'pilot128'):
        M = 32 if stage == 'pilot' else 128
        return dict(images=('D1',), S=(8, 1024), M=M, epsf=EPSF_PILOT, anti_M=M, mc_rule='pilot', n0_M=M, n0_mc=True, n0_epsf=(0.01,), fixw=0, fixM=0,
                    sigma_S=(), conv=False, plin_images=('D1', 'W0'), plin_M=256, plin_S=(8, 16, 64, 256, 1024), plin_epsf=0.01, v7_images=('D1', 'W0'), v7_n=8, det=True)
    if stage == 'full':
        return dict(images=('D1', 'D2', 'D3'), S=(8, 16, 64, 256, 1024), M=256, epsf=(epsf,), anti_M=128, mc_rule='full', n0_M=256, n0_mc=False, n0_epsf=(epsf,), fixw=4, fixM=128,
                    sigma_S=(8, 256), conv=True, plin_images=('D1', 'D2', 'D3', 'W0', 'W1'), plin_M=256, plin_S=(8, 16, 64, 256, 1024), plin_epsf=epsf, v7_images=('D1', 'W0'), v7_n=8, det=True)
    raise ValueError(stage)


def mc_plan(rule, S, m):
    """list of (eps_index, probe_j) transplanted-MC evaluations for sample m (contract sections 3-4)."""
    if rule == 'pilot':
        return [(ei, j) for ei in (3, 4) for j in (0, 1)]
    plan = []
    if m < 64:
        plan += [(ei, j) for ei in range(5) for j in (0, 1)]
    if S in (8, 256) and m < 256:
        plan += [(ei, 0) for ei in (3, 4) if (ei, 0) not in plan]  # T3 identity cells, J=1, 256 samples (reuses the base fit)
    return plan


def rng_for(entropy, *key):
    return np.random.default_rng(np.random.SeedSequence(entropy=entropy, spawn_key=tuple(int(k) for k in key)))


def omega_for(entropy, *key):
    return np.random.SeedSequence(entropy=entropy, spawn_key=tuple(int(k) for k in key))


def _cfg(cfgd):
    d = dict(cfgd)
    for k, v in list(d.items()):
        if isinstance(v, list):
            d[k] = tuple(v)
    return F0Config(**d)


@lru_cache(maxsize=16)
def clean(name, cfg_json):
    cfg = _cfg(json.loads(cfg_json)); n = cfg.H * cfg.W
    if name == 'W0':
        return np.zeros(n)
    if name == 'W1':
        return 0.1 * synth.make_clean('D1', GEN_SEED['D1'], cfg).reshape(-1)
    return synth.make_clean(name, GEN_SEED[name], cfg).reshape(-1)


def run_unit(task):
    """One task = one (kind, image, S, m) block of fits. Returns (key, m, arrays, wall_s, n_fits)."""
    from src import plin
    if os.environ.get('F0_IMPL', 'torch') == 'fast':   # D-02: numpy analytic-gradient implementation of the SAME model (src/gsfast.py, src/gskernel.py)
        from src import gsfast as gsfit
    else:
        import torch
        torch.set_num_threads(1)
        from src import gsfit
    if not getattr(plin, '_atoms_cached', False):   # runner-side cache of the fixed 1024-atom dictionary (src/ untouched; A is never mutated)
        plin.plin_atoms = lru_cache(maxsize=4)(plin.plin_atoms); plin._atoms_cached = True
    t0 = time.time()
    cfg = _cfg(task['cfg']); cj = json.dumps(task['cfg'], sort_keys=True)
    img = task['img']; ii = IMG_IDX[img]; S = task['S']; m = task['m']; kind = task['kind']
    H, W = cfg.H, cfg.W; N = H * W; s0 = cfg.sigma0; ent = cfg.entropy
    x = clean(img, cj); out = {}; nf = 0
    e = s0 * rng_for(ent, 1, ii, m).standard_normal(N); y = x + e   # noise stream 1: independent of S, omega, arm
    R = lambda v: np.asarray(v, dtype=np.float64).reshape(H, W)

    if kind in ('main', 'conv'):
        om = omega_for(ent, 2, ii, m)                                # omega stream 2: independent of S (R9)
        tb = time.perf_counter(); f, aux = gsfit.fit_pipeline(R(y), om, S, cfg); out['base_fit_s'] = np.array(time.perf_counter() - tb); nf += 1
        f = np.asarray(f, dtype=np.float64).reshape(-1)
        bi = [np.asarray(a, dtype=np.int64) for a in aux['birth_idx']]
        g0 = np.asarray(gsfit.fit_pipeline(R(y), om, S, cfg, forced_idx=bi)[0], dtype=np.float64).reshape(-1); nf += 1
        out['replay_ok'] = np.array(bool(np.array_equal(g0, f)))     # R1: bitwise replay, every m
        out['F'] = f; out['E'] = e; out['birth_idx'] = np.stack(bi)
        b0 = rng_for(ent, 3, ii, m).standard_normal(N)               # frozen-probe stream 3: independent of S and eps_f
        fd = np.full(len(task['epsf']), np.nan)
        for k, er in enumerate(task['epsf']):
            ef = er * s0
            gp = np.asarray(gsfit.fit_pipeline(R(y + ef * b0), om, S, cfg, forced_idx=bi)[0], dtype=np.float64).reshape(-1); nf += 1
            fd[k] = float(np.sum(b0 * (gp - f)) / ef)
        out['FD'] = fd
        out['ANTI'] = np.array(np.nan)
        if m < task['anti_M']:                                       # R9 secondary: antithetic fit at x - e, same omega
            fm = np.asarray(gsfit.fit_pipeline(R(x - e), om, S, cfg)[0], dtype=np.float64).reshape(-1); nf += 1
            out['ANTI'] = np.array(float(np.sum((f - fm) * e) / (2 * s0 ** 2)))
        div = np.full((len(EPS_REL), 2), np.nan)
        for (ei, j) in task['plan']:
            bj = rng_for(ent, 6, ii, m, j).standard_normal(N); er = EPS_REL[ei] * s0
            fp = np.asarray(gsfit.fit_pipeline(R(y + er * bj), om, S, cfg)[0], dtype=np.float64).reshape(-1); nf += 1
            div[ei, j] = float(np.sum(bj * (fp - f)) / er)
        out['DIV'] = div
        key = (kind, img, S, 0)
    elif kind == 'fix':
        k = task['k']; om = omega_for(ent, 8, ii, k)
        f = np.asarray(gsfit.fit_pipeline(R(y), om, S, cfg)[0], dtype=np.float64).reshape(-1); nf += 1
        out['F'] = f; out['E'] = e
        key = ('fix', img, S, k)
    elif kind == 'sigma':
        ei = task['ei']; sp = float(np.sqrt(s0 ** 2 + (EPS_REL[ei] * s0) ** 2))
        e2 = sp * rng_for(ent, 4, ii, ei, m).standard_normal(N); om = omega_for(ent, 5, ii, ei, m)
        f = np.asarray(gsfit.fit_pipeline(R(x + e2), om, S, cfg)[0], dtype=np.float64).reshape(-1); nf += 1
        out['F'] = f; out['E'] = e2; out['sigma_prime'] = np.array(sp)
        key = ('sigma', img, S, ei)
    elif kind == 'n0':
        om = omega_for(ent, 7, ii, m)
        tb = time.perf_counter(); f = np.asarray(gsfit.fit_no_birth(R(y), om, cfg), dtype=np.float64).reshape(-1); out['base_fit_s'] = np.array(time.perf_counter() - tb); nf += 1
        out['F'] = f; out['E'] = e
        b = rng_for(ent, 9, ii, m, 0).standard_normal(N); fd = np.full(len(task['epsf']), np.nan)
        for k, er in enumerate(task['epsf']):
            ef = er * s0
            gp = np.asarray(gsfit.fit_no_birth(R(y + ef * b), om, cfg), dtype=np.float64).reshape(-1); nf += 1
            fd[k] = float(np.sum(b * (gp - f)) / ef)
        out['FD'] = fd
        div = np.full((len(EPS_REL), 2), np.nan)
        for (ei, j) in task['plan']:
            bj = rng_for(ent, 9, ii, m, 1 + j).standard_normal(N); er = EPS_REL[ei] * s0
            fp = np.asarray(gsfit.fit_no_birth(R(y + er * bj), om, cfg), dtype=np.float64).reshape(-1); nf += 1
            div[ei, j] = float(np.sum(bj * (fp - f)) / er)
        out['DIV'] = div
        key = ('n0', img, 0, 0)
    elif kind == 'plin':
        om = omega_for(ent, 10, ii, m)
        f, aux = plin.plin_pipeline(R(y), om, S, cfg); f = np.asarray(f, dtype=np.float64).reshape(-1)
        sup = [np.asarray(a, dtype=np.int64) for a in aux['support']]
        f2 = np.asarray(plin.plin_frozen(R(y), sup, cfg), dtype=np.float64).reshape(-1)
        out['replay_ok'] = np.array(bool(np.array_equal(f2, f)))
        b = rng_for(ent, 11, ii, m).standard_normal(N); ef = task['epsf'] * s0
        gp = np.asarray(plin.plin_frozen(R(y + ef * b), sup, cfg), dtype=np.float64).reshape(-1)
        out['F'] = f; out['E'] = e; out['FD'] = np.array([float(np.sum(b * (gp - f)) / ef)]); out['rank'] = np.array(int(plin.plin_rank(sup, cfg)))
        out['support'] = np.concatenate(sup)
        key = ('plin', img, S, 0)
    elif kind == 'v7':
        om = omega_for(ent, 10, ii, m)
        f, aux = plin.plin_pipeline(R(y), om, S, cfg); f = np.asarray(f, dtype=np.float64).reshape(-1)
        sup = [np.asarray(a, dtype=np.int64) for a in aux['support']]
        ef = task['epsf'] * s0
        G = np.asarray(plin.plin_frozen_cols(y[:, None] + ef * np.eye(N), sup, cfg), dtype=np.float64)   # exact full-coordinate FD (I4)
        out['trace'] = np.array(float(np.sum(np.diag(G) - f) / ef)); out['rank'] = np.array(int(plin.plin_rank(sup, cfg)))
        key = ('v7', img, S, 0)
    elif kind == 'det':
        om = omega_for(ent, 2, ii, m); b = rng_for(ent, 3, ii, m).standard_normal(N); ef = min(EPSF_PILOT) * s0
        a1 = np.asarray(gsfit.fit_pipeline(R(y), om, S, cfg)[0]).reshape(-1); a2 = np.asarray(gsfit.fit_pipeline(R(y), om, S, cfg)[0]).reshape(-1)
        p1 = np.asarray(gsfit.fit_pipeline(R(y + ef * b), om, S, cfg)[0]).reshape(-1); p2 = np.asarray(gsfit.fit_pipeline(R(y + ef * b), om, S, cfg)[0]).reshape(-1)
        out['det_f_ok'] = np.array(bool(np.array_equal(a1, a2))); out['det_pert_ok'] = np.array(bool(np.array_equal(p1, p2))); nf += 4
        key = ('det', img, S, 0)
    else:
        raise ValueError(kind)
    for k, v in out.items():
        v = np.asarray(v)
        if np.issubdtype(v.dtype, np.floating) and k not in ('FD', 'DIV', 'ANTI') and not np.isfinite(v).all():
            raise RuntimeError('non-finite in %s %s' % (key, k))
    out['n_fits'] = np.array(nf)
    return key, m, out, time.time() - t0, nf


def build_tasks(spec, cfgd):
    T = []; ds = spec
    for img in ds['images']:
        for S in ds['S']:
            for m in range(ds['M']):
                T.append(dict(kind='main', cfg=cfgd, img=img, S=S, m=m, epsf=list(ds['epsf']), anti_M=ds['anti_M'], plan=mc_plan(ds['mc_rule'], S, m)))
        for m in range(ds['n0_M']):
            T.append(dict(kind='n0', cfg=cfgd, img=img, S=0, m=m, epsf=list(ds['n0_epsf']), plan=(mc_plan('pilot', 0, m) if ds['n0_mc'] else [])))
        for S in ds['S']:
            for k in range(ds['fixw']):
                for m in range(ds['fixM']):
                    T.append(dict(kind='fix', cfg=cfgd, img=img, S=S, m=m, k=k))
        for S in ds['sigma_S']:
            for ei in (3, 4):
                for m in range(256):
                    T.append(dict(kind='sigma', cfg=cfgd, img=img, S=S, m=m, ei=ei))
        if ds['conv'] and img == 'D1':
            c2 = dict(cfgd); c2['steps_per_stage'] = 2 * cfgd['steps_per_stage']
            for S in (8, 1024):
                for m in range(ds['M']):
                    T.append(dict(kind='conv', cfg=c2, img=img, S=S, m=m, epsf=list(ds['epsf']), anti_M=0, plan=[]))
    for img in ds['plin_images']:
        for S in ds['plin_S']:
            for m in range(ds['plin_M']):
                T.append(dict(kind='plin', cfg=cfgd, img=img, S=S, m=m, epsf=ds['plin_epsf']))
    for img in ds['v7_images']:
        for m in range(ds['v7_n']):
            T.append(dict(kind='v7', cfg=cfgd, img=img, S=256, m=m, epsf=ds['plin_epsf']))
    if ds['det']:
        for S in (8, 1024):
            T.append(dict(kind='det', cfg=cfgd, img='D1', S=S, m=0))
    return T


def file_hashes(paths):
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.exists()}


def flush(out_dir, key, d, walls):
    ms = sorted(d)
    stacked = {k: np.stack([np.asarray(d[mm][k]) for mm in ms]) for k in d[ms[0]]}
    stacked['m_index'] = np.array(ms); stacked['unit_wall_s'] = np.array(walls[key])
    np.savez_compressed(out_dir / ('%s__%s__S%d__x%d.npz' % key), **stacked)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', required=True, choices=['pilot', 'pilot128', 'full']); ap.add_argument('--tag', required=True)
    ap.add_argument('--workers', type=int, default=18); ap.add_argument('--cap_seconds', type=int, default=0)
    ap.add_argument('--epsf', type=float, default=0.01, help='full stage: eps_f/sigma0 frozen by amendment A1 after the pilot R7 check')
    ap.add_argument('--impl', default='torch', choices=['torch', 'fast'], help='D-02: fast = numpy analytic gradients (same model, validated vs torch)'); ap.add_argument('--max_tasks', type=int, default=0, help='debug only'); ap.add_argument('--debug_steps', type=int, default=0, help='debug only: steps_per_stage override')
    a = ap.parse_args()
    contract = ROOT / 'contracts' / 'F0_CONTRACT.md'
    want = (ROOT / 'contracts' / 'F0_CONTRACT.sha256').read_text().split()[0]; have = hashlib.sha256(contract.read_bytes()).hexdigest()
    if want != have:
        print('CONTRACT HASH MISMATCH (frozen %s vs file %s) -> refusing to run' % (want, have)); sys.exit(2)
    os.environ['F0_IMPL'] = a.impl   # inherited by spawned pool workers
    cfg = F0Config()
    if a.debug_steps: cfg = replace(cfg, steps_per_stage=a.debug_steps)
    cfgd = json.loads(json.dumps(asdict(cfg)))
    spec = stage_spec(a.stage, a.epsf)
    cap = a.cap_seconds or (1800 if a.stage.startswith('pilot') else 4 * 3600)
    prefix = 'DEBUG-' if (a.debug_steps or a.max_tasks) else ''
    out_dir = ROOT / 'outputs' / ('%sF0-%s-%s' % (prefix, a.stage, a.tag))
    os.makedirs(out_dir, exist_ok=False)  # atomic reservation; fails if it exists
    tasks = build_tasks(spec, cfgd)
    if a.max_tasks: tasks = tasks[:a.max_tasks]
    expected = {}
    for t in tasks:
        k = (t['kind'], t['img'], t['S'], t.get('k', t.get('ei', 0)))
        expected[k] = expected.get(k, 0) + 1
    meta = dict(stage=a.stage, tag=a.tag, debug=bool(prefix), started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), n_tasks=len(tasks), workers=a.workers, cap_seconds=cap,
                contract_sha256=have, impl=a.impl, epsf_full=a.epsf, cfg=cfgd, cfg_hash=cfg_hash(cfg), python=sys.version, platform=platform.platform(),
                stage_spec={k: (list(v) if isinstance(v, tuple) else v) for k, v in spec.items()},
                code_hashes=file_hashes(sorted((ROOT / 'src').glob('*.py')) + sorted((ROOT / 'experiments').glob('f0_*.py'))))
    import scipy, torch
    meta['versions'] = dict(numpy=np.__version__, scipy=scipy.__version__, torch=torch.__version__)
    (out_dir / 'meta.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    t0 = time.time(); acc = {}; walls = {}; aborted = None; done = 0; fits = 0; flushed = set()
    with Pool(a.workers) as pool:
        try:
            for key, m, arrs, w, nf in pool.imap_unordered(run_unit, tasks, chunksize=1):
                acc.setdefault(key, {})[m] = arrs; walls.setdefault(key, []).append(w); done += 1; fits += nf
                if 'replay_ok' in arrs and not bool(arrs['replay_ok']):
                    aborted = 'REPLAY_MISMATCH %s m=%d (contract R1: INVALID)' % (key, m); pool.terminate(); break
                if len(acc[key]) == expected[key]:
                    flush(out_dir, key, acc.pop(key), walls); flushed.add(key)
                if done % 25 == 0:
                    (out_dir / 'progress.txt').write_text('%d/%d tasks, %d fits, %.0fs\n' % (done, len(tasks), fits, time.time() - t0), encoding='utf-8')
                if time.time() - t0 > cap:
                    aborted = 'WALL_CAP %ds' % cap; pool.terminate(); break
        except Exception as ex:  # a worker raised (non-finite etc.): keep partial results, report
            aborted = 'WORKER_ERROR %r' % (ex,); pool.terminate()
    for key, d in list(acc.items()):
        if d: flush(out_dir, key, d, walls); flushed.add(key)   # partial cells (only after abort)
    meta.update(finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), wall_s=time.time() - t0, tasks_done=done, fits_done=fits, aborted=aborted,
                n_fits_per_s=fits / max(time.time() - t0, 1e-9))
    (out_dir / 'meta.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    print(json.dumps({k: meta[k] for k in ('stage', 'tag', 'tasks_done', 'n_tasks', 'fits_done', 'wall_s', 'aborted')}))
    if aborted: sys.exit(3)


if __name__ == '__main__':
    main()
