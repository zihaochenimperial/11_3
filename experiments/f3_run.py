"""F0 runner for contract v3 (contracts/F0_CONTRACT_v3.md; sha256 in contracts/F0_CONTRACT_v3.sha256). Refuses to run if the hash differs.
Fission design: y+/- = x + e +/- z (independent noises of variance 2*sigma0^2), shared omega, full legs F+/-, frozen legs G+/- (birth indices from the OTHER copy).
Stages: pilot (E1,E2; S in {8,1024}; M=32), stage1 (E3..E14; --M in {32,64,128}). Writes outputs/F3-<stage>-<tag>/ (atomic reservation) with one npz per (kind,img,S,impl) + meta.json.
Fitters only see (y, omega, S/I, cfg); the clean image is used here only to synthesise y / e / anti-input and is never passed as an argument other than through y.
usage (pump py job): python experiments/f3_run.py --stage=pilot --tag=p1 --workers=4   |   debug: --debug_steps=5 --max_tasks=8 -> outputs/DEBUG-F3-... (never evidence)."""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_v] = '1'
import argparse, json, sys, time, hashlib, platform
from dataclasses import asdict, replace
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.f0_config import F0Config, cfg_hash  # noqa: E402
from src import synth  # noqa: E402

ENTROPY = 20261106
TYPES = ('D1', 'D2', 'D3')
S_LIST = (8, 1024)
PLIN_S = (8, 16, 64, 256, 1024)
PLIN_M = 256


def img_index(name):
    if name == 'W0': return 90
    if name == 'W1': return 91
    return 100 + int(name[1:])          # E_k -> 100+k


def rng_for(*key):
    return np.random.default_rng(np.random.SeedSequence(entropy=ENTROPY, spawn_key=tuple(int(k) for k in key)))


def omega_for(*key):
    return np.random.SeedSequence(entropy=ENTROPY, spawn_key=tuple(int(k) for k in key))


def _cfg(cfgd):
    d = dict(cfgd)
    for k, v in list(d.items()):
        if isinstance(v, list): d[k] = tuple(v)
    return F0Config(**d)


@lru_cache(maxsize=32)
def clean(name, cfg_json):
    cfg = _cfg(json.loads(cfg_json)); n = cfg.H * cfg.W
    if name == 'W0': return np.zeros(n)
    if name == 'W1': return 0.1 * synth.make_clean('D1', 3001, cfg).reshape(-1)    # 0.1 * E1
    k = int(name[1:]); return synth.make_clean(TYPES[(k - 1) % 3], 3000 + k, cfg).reshape(-1)


def _fitter(impl):
    if impl == 'fast':
        from src import gsfast as G
    else:
        import torch
        torch.set_num_threads(1)
        from src import gsfit as G
    return G


def run_unit(task):
    """kind 'full': fission legs for (img,S,m) -> F+,F-,G+,G-,(A); kind 'tfull' (P4 torch subset): F+,F- only; kind 'plin': P-lin fission legs."""
    t0 = time.time(); kind = task['kind']; cfg = _cfg(task['cfg']); cj = json.dumps(task['cfg'], sort_keys=True)
    img = task['img']; ii = img_index(img); S = task['S']; m = task['m']
    H, W = cfg.H, cfg.W; N = H * W; s0 = cfg.sigma0
    x = clean(img, cj)
    e = s0 * rng_for(1, ii, m).standard_normal(N); z = s0 * rng_for(12, ii, m).standard_normal(N)
    ep = e + z; em = e - z; yp = x + ep; ym = x + em
    R = lambda v: np.asarray(v, dtype=np.float64).reshape(H, W)
    F = lambda v: np.asarray(v, dtype=np.float64).reshape(-1)
    out = dict(ep=ep, em=em); nf = 0
    if kind in ('full', 'tfull'):
        G = _fitter(task['impl']); om = omega_for(2, ii, m)
        fp, ap = G.fit_pipeline(R(yp), om, S, cfg); fm, am = G.fit_pipeline(R(ym), om, S, cfg); nf += 2
        Ip = [np.asarray(a, dtype=np.int64) for a in ap['birth_idx']]; Im = [np.asarray(a, dtype=np.int64) for a in am['birth_idx']]
        out['Fp'] = F(fp); out['Fm'] = F(fm); out['Ip'] = np.stack(Ip); out['Im'] = np.stack(Im)
        out['idx_equal'] = np.array(bool(all(np.array_equal(a, b) for a, b in zip(Ip, Im))))     # must be True for S=8 (selection independent of y)
        if kind == 'full':
            do_g = (S != 8) or task['g_s8']
            if do_g:
                gp = G.fit_pipeline(R(yp), om, S, cfg, forced_idx=Im)[0]; gm = G.fit_pipeline(R(ym), om, S, cfg, forced_idx=Ip)[0]; nf += 2
                out['Gp'] = F(gp); out['Gm'] = F(gm); out['g_ran'] = np.array(True)
            else:                                                                                # Stage 1, S=8, beyond the first 8 draws: identity G=F (index equality asserted above)
                out['Gp'] = out['Fp']; out['Gm'] = out['Fm']; out['g_ran'] = np.array(False)
            if task['replay']:
                rp = G.fit_pipeline(R(yp), om, S, cfg, forced_idx=Ip)[0]; nf += 1
                out['replay_ok'] = np.array(bool(np.array_equal(F(rp), out['Fp'])))
            else:
                out['replay_ok'] = np.array(True)
            if task['anti']:
                a = G.fit_pipeline(R(x - ep), om, S, cfg)[0]; nf += 1                               # antithetic partner f(x - e+; omega)
                out['A'] = F(a)
        key = (kind, img, S, task['impl'])
    elif kind == 'plin':
        from src import plin
        om = omega_for(10, ii, m)
        fp, ap = plin.plin_pipeline(R(yp), om, S, cfg); fm, am = plin.plin_pipeline(R(ym), om, S, cfg)
        sp = [np.asarray(a, dtype=np.int64) for a in ap['support']]; sm = [np.asarray(a, dtype=np.int64) for a in am['support']]
        gp = plin.plin_frozen(R(yp), sm, cfg); gm = plin.plin_frozen(R(ym), sp, cfg)
        out['Fp'] = F(fp); out['Fm'] = F(fm); out['Gp'] = F(gp); out['Gm'] = F(gm)
        out['rank_p'] = np.array(int(plin.plin_rank(sp, cfg)))
        key = ('plin', img, S, 'np')
    else:
        raise ValueError(kind)
    for k, v in out.items():
        v = np.asarray(v)
        if np.issubdtype(v.dtype, np.floating) and not np.isfinite(v).all(): raise RuntimeError('non-finite in %s %s' % (key, k))
    out['n_fits'] = np.array(nf)
    return key, m, out, time.time() - t0, nf


def stage_spec(stage, M, fallback=''):
    if stage == 'pilot':
        return dict(images=('E1', 'E2'), M=32, tM=32, t_img='E1', plin_images=('W0', 'W1', 'E1'), anti=True, g_s8_all=True, S_list=S_LIST, replay=True)
    if stage == 'pilot_m128':   # contract C2: P1 rerun, E1,E2, S=1024 only, F+-,G+- only, own 60-min cap, outside the Stage-1 budget
        return dict(images=('E1', 'E2'), M=128, tM=0, t_img=None, plin_images=(), anti=False, g_s8_all=False, S_list=(1024,), replay=False)
    if stage == 'stage1':
        imgs = tuple('E%d' % k for k in range(3, 15))
        if fallback == 'b': imgs = tuple('E%d' % k for k in range(3, 11))          # C2(b): E3..E10
        return dict(images=imgs, M=M, tM=0, t_img=None, plin_images=('W0', 'W1', 'E1') + imgs, anti=False, g_s8_all=False, S_list=((1024,) if fallback in ('a', 'b') else (8, 1024)), replay=True)
    raise ValueError(stage)


def build_tasks(spec, cfgd):
    T = []
    for img in spec['images']:
        for S in spec['S_list']:
            for m in range(spec['M']):
                T.append(dict(kind='full', cfg=cfgd, img=img, S=S, m=m, impl='fast', replay=(spec['replay'] and m < 4), anti=spec['anti'], g_s8=(spec['g_s8_all'] or m < 8)))
    if spec['tM']:
        for m in range(spec['tM']):
            T.append(dict(kind='tfull', cfg=cfgd, img=spec['t_img'], S=1024, m=m, impl='torch'))
    for img in spec['plin_images']:
        for S in PLIN_S:
            for m in range(PLIN_M):
                T.append(dict(kind='plin', cfg=cfgd, img=img, S=S, m=m))
    return T


def file_hashes(paths):
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.exists()}


def flush(out_dir, key, d, walls):
    ms = sorted(d)
    stacked = {k: np.stack([np.asarray(d[mm][k]) for mm in ms]) for k in d[ms[0]]}
    stacked['m_index'] = np.array(ms); stacked['unit_wall_s'] = np.array(walls[key])
    np.savez_compressed(out_dir / ('%s__%s__S%d__%s.npz' % key), **stacked)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', required=True, choices=['pilot', 'pilot_m128', 'stage1']); ap.add_argument('--tag', required=True)
    ap.add_argument('--workers', type=int, default=4); ap.add_argument('--M', type=int, default=32, help='stage1 only: draws per image in {32,64,128} (chosen by precision extrapolation, contract section 4)')
    ap.add_argument('--fallback', default='', choices=['', 'a', 'b'], help='stage1 only: contract C2 fallback (a: drop S=8 fits; b: also E3..E10 only)'); ap.add_argument('--cap_seconds', type=int, default=0); ap.add_argument('--max_tasks', type=int, default=0, help='debug only'); ap.add_argument('--debug_steps', type=int, default=0, help='debug only')
    a = ap.parse_args()
    contract = ROOT / 'contracts' / 'F0_CONTRACT_v3.md'
    want = (ROOT / 'contracts' / 'F0_CONTRACT_v3.sha256').read_text().split()[0]; have = hashlib.sha256(contract.read_bytes()).hexdigest()
    debug = bool(a.debug_steps or a.max_tasks)
    if want != have and not debug:
        print('CONTRACT v3 HASH MISMATCH (frozen %s vs file %s) -> refusing to run' % (want, have)); sys.exit(2)
    if a.stage == 'stage1' and a.M not in (32, 64, 128): print('stage1 M must be in {32,64,128}'); sys.exit(2)
    cfg = F0Config()
    if a.debug_steps: cfg = replace(cfg, steps_per_stage=a.debug_steps)
    cfgd = json.loads(json.dumps(asdict(cfg)))
    spec = stage_spec(a.stage, a.M if a.stage == 'stage1' else 0, a.fallback)
    cap = a.cap_seconds or (1800 if a.stage == 'pilot' else (3600 if a.stage == 'pilot_m128' else 4 * 3600))
    prefix = 'DEBUG-' if debug else ''
    out_dir = ROOT / 'outputs' / ('%sF3-%s-%s' % (prefix, a.stage, a.tag))
    os.makedirs(out_dir, exist_ok=False)
    tasks = build_tasks(spec, cfgd)
    if a.max_tasks: tasks = tasks[:a.max_tasks]
    expected = {}
    for t in tasks:
        k = (t['kind'], t['img'], t['S'], t.get('impl', 'np')); expected[k] = expected.get(k, 0) + 1
    meta = dict(stage=a.stage, tag=a.tag, debug=debug, started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), n_tasks=len(tasks), workers=a.workers, cap_seconds=cap, M=spec['M'], fallback=a.fallback,
                contract_sha256=have, entropy=ENTROPY, cfg=cfgd, cfg_hash=cfg_hash(cfg), python=sys.version, platform=platform.platform(), expected={'%s__%s__S%d__%s' % k: v for k, v in expected.items()},
                code_hashes=file_hashes(sorted((ROOT / 'src').glob('*.py')) + sorted((ROOT / 'experiments').glob('f3_*.py'))))
    import scipy
    meta['versions'] = dict(numpy=np.__version__, scipy=scipy.__version__)
    try:
        import torch; meta['versions']['torch'] = torch.__version__
    except Exception: pass
    (out_dir / 'meta.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    t0 = time.time(); acc = {}; walls = {}; aborted = None; done = 0; fits = 0; flushed = set()
    with Pool(a.workers) as pool:
        try:
            for key, m, arrs, w, nf in pool.imap_unordered(run_unit, tasks, chunksize=1):
                acc.setdefault(key, {})[m] = arrs; walls.setdefault(key, []).append(w); done += 1; fits += nf
                if key[0] == 'full':
                    if key[2] == 8 and not bool(arrs['idx_equal']): aborted = 'S8_INDEX_MISMATCH %s m=%d' % (key, m); pool.terminate(); break
                    if not bool(arrs['replay_ok']): aborted = 'REPLAY_MISMATCH %s m=%d' % (key, m); pool.terminate(); break
                    if key[2] == 8 and bool(arrs['g_ran']) and not (np.array_equal(arrs['Gp'], arrs['Fp']) and np.array_equal(arrs['Gm'], arrs['Fm'])):
                        aborted = 'S8_G_NEQ_F %s m=%d' % (key, m); pool.terminate(); break
                if len(acc[key]) == expected[key]:
                    flush(out_dir, key, acc.pop(key), walls); flushed.add(key)
                if done % 25 == 0:
                    (out_dir / 'progress.txt').write_text('%d/%d tasks, %d fits, %.0fs\n' % (done, len(tasks), fits, time.time() - t0), encoding='utf-8')
                if time.time() - t0 > cap:
                    aborted = 'WALL_CAP %ds' % cap; pool.terminate(); break
        except Exception as ex:
            aborted = 'WORKER_ERROR %r' % (ex,); pool.terminate()
    for key, d in list(acc.items()):
        if d: flush(out_dir, key, d, walls); flushed.add(key)
    meta.update(finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), wall_s=time.time() - t0, tasks_done=done, fits_done=fits, aborted=aborted, n_fits_per_s=fits / max(time.time() - t0, 1e-9))
    (out_dir / 'meta.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    print(json.dumps({k: meta[k] for k in ('stage', 'tag', 'tasks_done', 'n_tasks', 'fits_done', 'wall_s', 'aborted')}))
    if aborted: sys.exit(3)


if __name__ == '__main__':
    main()
