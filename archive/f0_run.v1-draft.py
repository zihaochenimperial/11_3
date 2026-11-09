"""F0 runner (stages: pilot | full). Draft against contracts/F0_CONTRACT_DRAFT_v1.md; run ONLY after the contract is frozen.
Writes outputs/F0-<stage>-<tag>/ (atomically reserved, never overwritten): one npz per (arm, image, S) + meta.json.
The fitters only ever see y (src/gsfit.py, src/plin.py); the clean image is used here only to synthesise y and is never passed to a fitter.
usage (via pump py job): python experiments/f0_run.py --stage=pilot --tag=p1 --workers=18"""
import argparse, json, os, sys, time, hashlib, platform
from dataclasses import asdict, replace
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.f0_config import F0Config, cfg_hash  # noqa: E402
from src import synth  # noqa: E402  (clean images: used here only to build y)

IMG_IDX = {'D1': 0, 'D2': 1, 'D3': 2}
GEN_SEED = {'D1': 1001, 'D2': 1002, 'D3': 1003}
EPS_REL = (0.01, 0.03, 0.1, 0.3, 1.0)
STAGES = {
    # arms: main (rand + frozen [+ MC transplant on first Mmc draws]), fix, sigma (T3 validity), n0, plin, conv
    'pilot': dict(images=('D1',), S=(8, 1024), M=32, Mmc=0, fixw=0, fixM=0, sigma_S=(), n0_M=32, n0_eps=(0.1, 0.3), plin_M=32, conv=False),
    'full': dict(images=('D1', 'D2', 'D3'), S=(8, 16, 64, 256, 1024), M=256, Mmc=64, fixw=4, fixM=128, sigma_S=(8, 256), n0_M=256, n0_eps=EPS_REL, plin_M=256, conv=True),
}


def seed_int(entropy, *key):
    ss = np.random.SeedSequence(entropy=entropy, spawn_key=tuple(int(k) for k in key))
    return int(ss.generate_state(1, dtype=np.uint64)[0] % (2 ** 63 - 1))


def rng_for(entropy, *key):
    return np.random.default_rng(np.random.SeedSequence(entropy=entropy, spawn_key=tuple(int(k) for k in key)))


@lru_cache(maxsize=8)
def clean(name, cfg_json):
    cfg = F0Config(**json.loads(cfg_json))
    return synth.make_clean(name, GEN_SEED[name], cfg).reshape(-1)


def _cfg(cfgd):
    d = dict(cfgd)
    for k, v in list(d.items()):
        if isinstance(v, list):
            d[k] = tuple(v)
    return F0Config(**d)


def run_unit(task):
    """One unit = one (arm, image, S, m) block of fits. Returns (key, m, arrays dict, wall_s)."""
    import torch
    torch.set_num_threads(1)
    from src import gsfit, plin
    t0 = time.time()
    cfgd = task['cfg']; cfg = _cfg(cfgd); cj = json.dumps(cfgd, sort_keys=True)
    img = task['img']; ii = IMG_IDX[img]; S = task['S']; si = task.get('si', 0); m = task['m']
    H, W = cfg.H, cfg.W; N = H * W; s0 = cfg.sigma0; ent = cfg.entropy
    x = clean(img, cj)
    kind = task['kind']; out = {}
    if kind in ('main', 'conv'):
        y = x + s0 * rng_for(ent, 1, ii, m).standard_normal(N)
        omega = seed_int(ent, 2, ii, si, 0, m)
        f, aux = gsfit.fit_pipeline(y.reshape(H, W), omega, S, cfg)
        out['F'] = f.reshape(-1); out['E'] = y - x
        out['birth_idx'] = np.stack([np.asarray(a, dtype=np.int64) for a in aux['birth_idx']])
        out['xy'] = np.asarray(aux['xy'], dtype=np.float64); out['fit_wall'] = np.array(aux.get('wall_s', np.nan))
        if kind == 'main':
            b0 = rng_for(ent, 3, ii, si, m, 0).standard_normal(N)
            epsf = cfg.eps_frozen_rel * s0
            fb = gsfit.fit_frozen((y + epsf * b0).reshape(H, W), omega, aux['birth_idx'], cfg)
            out['FB'] = fb.reshape(-1); out['B0'] = b0
            if m < task['Mmc']:
                nE = len(EPS_REL); FP = np.zeros((nE, 2, N)); BP = np.zeros((2, N))
                for j in range(2):
                    bj = rng_for(ent, 6, ii, si, m, j).standard_normal(N); BP[j] = bj
                    for k, er in enumerate(EPS_REL):
                        FP[k, j] = gsfit.fit_pipeline((y + er * s0 * bj).reshape(H, W), omega, S, cfg)[0].reshape(-1)
                out['FP'] = FP; out['BP'] = BP
        key = ('main' if kind == 'main' else 'conv', img, S)
    elif kind == 'fix':
        w = task['w']
        y = x + s0 * rng_for(ent, 1, ii, m).standard_normal(N)
        omega = seed_int(ent, 8, ii, si, w)
        f, aux = gsfit.fit_pipeline(y.reshape(H, W), omega, S, cfg)
        out['F'] = f.reshape(-1); out['E'] = y - x
        key = ('fix%d' % w, img, S)
    elif kind == 'sigma':
        er = EPS_REL[task['ei']]; sp = float(np.sqrt(s0 ** 2 + (er * s0) ** 2))
        e = sp * rng_for(ent, 4, ii, si, task['ei'], m).standard_normal(N)
        y = x + e; omega = seed_int(ent, 5, ii, si, task['ei'], m)
        f, aux = gsfit.fit_pipeline(y.reshape(H, W), omega, S, cfg)
        out['F'] = f.reshape(-1); out['E'] = e; out['sigma_prime'] = np.array(sp)
        key = ('sigma%d' % task['ei'], img, S)
    elif kind == 'n0':
        y = x + s0 * rng_for(ent, 1, ii, m).standard_normal(N)
        omega = seed_int(ent, 7, ii, m)
        f = gsfit.fit_no_birth(y.reshape(H, W), omega, cfg)
        out['F'] = f.reshape(-1); out['E'] = y - x
        if m < task['Mmc']:
            eps_list = task['n0_eps']; FP = np.zeros((len(eps_list), N)); BP = rng_for(ent, 9, ii, m).standard_normal(N)
            for k, er in enumerate(eps_list):
                FP[k] = gsfit.fit_no_birth((y + er * s0 * BP).reshape(H, W), omega, cfg).reshape(-1)
            out['FP'] = FP; out['BP'] = BP; out['n0_eps'] = np.array(eps_list)
        key = ('n0', img, 0)
    elif kind == 'plin':
        y = x + s0 * rng_for(ent, 1, ii, m).standard_normal(N)
        omega = seed_int(ent, 10, ii, si, m)
        f, aux = plin.plin_pipeline(y.reshape(H, W), omega, S, cfg)
        supp = np.concatenate([np.asarray(a, dtype=np.int64) for a in aux['support']])
        b0 = rng_for(ent, 11, ii, si, m).standard_normal(N)
        fb = plin.plin_frozen((y + cfg.eps_frozen_rel * s0 * b0).reshape(H, W), aux['support'], cfg)
        out['F'] = np.asarray(f).reshape(-1); out['E'] = y - x; out['FB'] = np.asarray(fb).reshape(-1); out['B0'] = b0; out['support'] = supp
        key = ('plin', img, S)
    else:
        raise ValueError(kind)
    for k, v in out.items():
        if np.issubdtype(np.asarray(v).dtype, np.floating) and not np.isfinite(v).all():
            raise RuntimeError('non-finite in %s %s' % (key, k))
    return key, m, out, time.time() - t0


def build_tasks(stage, cfgd):
    sp = STAGES[stage]; T = []
    for img in sp['images']:
        for si, S in enumerate(sp['S']):
            for m in range(sp['M']):
                T.append(dict(kind='main', cfg=cfgd, img=img, S=S, si=si, m=m, Mmc=sp['Mmc']))
            for w in range(sp['fixw']):
                for m in range(sp['fixM']):
                    T.append(dict(kind='fix', cfg=cfgd, img=img, S=S, si=si, m=m, w=w))
            for m in range(sp['plin_M']):
                T.append(dict(kind='plin', cfg=cfgd, img=img, S=S, si=si, m=m))
        for m in range(sp['n0_M']):
            T.append(dict(kind='n0', cfg=cfgd, img=img, S=0, m=m, Mmc=(sp['n0_M'] if stage == 'pilot' else sp['Mmc']), n0_eps=list(sp['n0_eps'])))
        for si, S in enumerate(sp['sigma_S']):
            for ei in range(len(EPS_REL)):
                for m in range(sp['M']):
                    T.append(dict(kind='sigma', cfg=cfgd, img=img, S=S, si=si, ei=ei, m=m))
        if sp['conv'] and img == 'D1':
            c2 = dict(cfgd); c2['steps_per_stage'] = 2 * cfgd['steps_per_stage']
            for si, S in enumerate((8, 1024)):
                for m in range(sp['M']):
                    T.append(dict(kind='conv', cfg=c2, img=img, S=S, si=si, m=m, Mmc=0))
    return T


def file_hashes(paths):
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.exists()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', required=True, choices=list(STAGES)); ap.add_argument('--tag', required=True)
    ap.add_argument('--workers', type=int, default=18); ap.add_argument('--cap_seconds', type=int, default=4 * 3600)
    ap.add_argument('--max_tasks', type=int, default=0, help='debug only: truncate the task list')
    a = ap.parse_args()
    cfg = F0Config(); cfgd = json.loads(json.dumps(asdict(cfg)))
    out_dir = ROOT / 'outputs' / ('F0-%s-%s' % (a.stage, a.tag))
    os.makedirs(out_dir, exist_ok=False)  # atomic reservation; fails if it exists
    tasks = build_tasks(a.stage, cfgd)
    if a.max_tasks: tasks = tasks[:a.max_tasks]
    meta = dict(stage=a.stage, tag=a.tag, started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), n_tasks=len(tasks), workers=a.workers, cap_seconds=a.cap_seconds,
                cfg=cfgd, cfg_hash=cfg_hash(cfg), python=sys.version, platform=platform.platform(), stage_spec={k: (list(v) if isinstance(v, tuple) else v) for k, v in STAGES[a.stage].items()},
                code_hashes=file_hashes(sorted((ROOT / 'src').glob('*.py')) + [Path(__file__)] + sorted((ROOT / 'experiments').glob('f0_*.py'))))
    import numpy, scipy, torch
    meta['versions'] = dict(numpy=numpy.__version__, scipy=scipy.__version__, torch=torch.__version__)
    (out_dir / 'meta.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    t0 = time.time(); acc = {}; walls = {}; aborted = False; done = 0
    with Pool(a.workers) as pool:
        for key, m, arrs, w in pool.imap_unordered(run_unit, tasks, chunksize=1):
            acc.setdefault(key, {})[m if not key[0].startswith('fix') else (m, len(acc.get(key, {})))] = arrs
            walls.setdefault(key, []).append(w); done += 1
            if done % 50 == 0:
                (out_dir / 'progress.txt').write_text('%d/%d %.0fs\n' % (done, len(tasks), time.time() - t0), encoding='utf-8')
            if time.time() - t0 > a.cap_seconds:
                aborted = True; pool.terminate(); break
    for key, d in acc.items():
        ms = sorted(d, key=lambda z: z if isinstance(z, int) else z[1])
        stacked = {}
        for k in d[ms[0]]:
            stacked[k] = np.stack([np.asarray(d[mm][k]) for mm in ms])
        stacked['m_index'] = np.array([mm if isinstance(mm, int) else mm[0] for mm in ms])
        stacked['unit_wall_s'] = np.array(walls[key])
        np.savez_compressed(out_dir / ('%s__%s__S%d.npz' % key), **stacked)
    meta['finished_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()); meta['wall_s'] = time.time() - t0; meta['units_done'] = done; meta['aborted_by_cap'] = aborted
    (out_dir / 'meta.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    print(json.dumps({k: meta[k] for k in ('stage', 'tag', 'units_done', 'n_tasks', 'wall_s', 'aborted_by_cap')}))
    if aborted: sys.exit(3)


if __name__ == '__main__':
    main()
