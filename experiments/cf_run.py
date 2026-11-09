"""CF-birth runner (contract CF0: contracts/CF0_CONTRACT.md; sha256 in contracts/CF0_CONTRACT.sha256; frozen-file manifest contracts/CF0_FROZEN_FILES.sha256). Refuses to run if any hash differs (debug mode excepted: outputs/DEBUG-CF-*, never evidence).
Per unit (image k, draw m): CRN -- one e, one z, omega1 (and omega2 for the equal-K ensembles) shared by ALL arms. Fitters only receive (y copy, omega, S, cfg, forced_idx); the clean image is used here only to synthesise y and to score risk.
Arms (risk = sum (f-x)^2): RAWy (+ RAWy_R0..R4 snapshots), RANDy (S=8), RANDens2 (RANDy on omega1/omega2 averaged, K=96), RAWy2 / RAWens2 (second omega, K=96 average), per tau in TAUS: RAWg, RAWf (own-copy selection; RAWg = equal-noise control), XFERg (births from y_f, fit y_g), NS (births from y_f, fit y);
tau=1 also: XFERf, XAVG (mean of XFERg,XFERf renders; K=96), XAVGctrl (mean of RAWg,RAWf renders; K=96), NSens (mean of NS(B_f), NS(B_g) on full y; K=96), CV curve cv_R (fission-CV, tau=1 two-way).
usage (pump py job): python experiments/cf_run.py --stage=pilot --tag=p1 --workers=6  |  --stage=dev --M=32 --tag=d1  |  --stage=dev_ext --M=32 (draws 32..63)  |  debug: --debug_steps=5 [--max_tasks=4] [--M=2]"""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_v] = '1'
import argparse, hashlib, json, platform, sys, time
from dataclasses import asdict, replace
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.f0_config import F0Config, cfg_hash  # noqa: E402
from src import synth, gsfast, cf_fit  # noqa: E402
from src.reference_eval import risk  # noqa: E402

ENTROPY = 20261107
TYPES = ('D1', 'D2', 'D3')
TAUS = (1.0, 2.0, 4.0)
S_SEL = 1024
S_RAND = 8
R_MAX = 4
R_BASE = 3
M_DEV = 32
WORKERS_DEFAULT = 6
PILOT_IMAGES = tuple('E%d' % k for k in (15, 16, 17, 18))
DEV_IMAGES = tuple('E%d' % k for k in range(21, 39))      # confirm set k=41..58 is NEVER touched by this runner
FROZEN_FILES = ['contracts/CF0_CONTRACT.md', 'experiments/cf_run.py', 'experiments/cf_analyze.py', 'src/cf_fit.py', 'src/gsfast.py', 'src/gskernel.py', 'src/omega.py', 'src/f0_config.py', 'src/synth.py',
                'src/reference_eval.py', 'tests/test_cf_units.py', 'tests/test_cf_analyze.py', 'scripts/run_cf_unit_tests.py']


def img_index(name):
    return 100 + int(name[1:])


def rng_for(*key):
    return np.random.default_rng(np.random.SeedSequence(entropy=ENTROPY, spawn_key=tuple(int(k) for k in key)))


def omega_for(*key):
    return np.random.SeedSequence(entropy=ENTROPY, spawn_key=tuple(int(k) for k in key))


def _cfg(d):
    d = dict(d)
    for k, v in list(d.items()):
        if isinstance(v, list): d[k] = tuple(v)
    return F0Config(**d)


@lru_cache(maxsize=64)
def clean(name, cfg_json):
    cfg = _cfg(json.loads(cfg_json)); k = int(name[1:])
    assert 15 <= k <= 38, 'image outside the CF0 pilot/dev range (confirm range 41..58 is reserved)'
    return synth.make_clean(TYPES[(k - 1) % 3], 3000 + k, cfg).reshape(-1)


def sha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()[:16]


def fsha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def synth_unit(img, m, cfg, cj):
    """clean image, noise e, fission noise z, observation y = x + e, and the two omega streams of unit (img, m)."""
    ii = img_index(img); N = cfg.H * cfg.W; s0 = cfg.sigma0
    x = clean(img, cj)
    e = s0 * rng_for(21, ii, m).standard_normal(N); z = s0 * rng_for(23, ii, m).standard_normal(N)
    return x, e, z, x + e, omega_for(22, ii, m, 0), omega_for(22, ii, m, 1)


def run_unit(task):
    t0 = time.time(); cfg = _cfg(task['cfg']); cj = json.dumps(task['cfg'], sort_keys=True)
    img = task['img']; ii = img_index(img); m = task['m']; H, W = cfg.H, cfg.W
    x, e, z, y, om1, om2 = synth_unit(img, m, cfg, cj)
    R = lambda v: np.asarray(v, dtype=np.float64).reshape(H, W)
    Fl = lambda v: np.asarray(v, dtype=np.float64).reshape(-1)
    K48 = cfg.K0 + R_BASE * cfg.births_per_round
    risks = {}; hashes = {}; diag = {}; nfit = 0.0; K = {}
    def rec(name, f, kk=K48):
        f = Fl(f); risks[name] = risk(f, x); hashes[name] = sha(f); K[name] = kk
    diag['ez_corr'] = float(np.corrcoef(e, z)[0, 1])
    # ---- base arms (sigma0)
    sy, by, ay = cf_fit.trajectory(R(y), om1, S_SEL, cfg, R_MAX); nfit += (R_MAX + 1) / 4.0
    for r in range(R_MAX + 1): risks['RAWy_R%d' % r] = risk(sy[r], x)
    rec('RAWy', sy[R_BASE]); hashes['RAWy_traj'] = sha(np.stack(sy)); diag['RAWy_disp'] = ay['birth_disp_px'][:R_BASE]; diag['RAWy_resid'] = ay['resid_at_births'][:R_BASE]
    fr = gsfast.fit_pipeline(R(y), om1, S_RAND, cfg)[0]; nfit += 1; rec('RANDy', fr)
    fr2 = gsfast.fit_pipeline(R(y), om2, S_RAND, cfg)[0]; nfit += 1; rec('RANDens2', 0.5 * (Fl(fr) + Fl(fr2)), 2 * K48)
    f2 = gsfast.fit_pipeline(R(y), om2, S_SEL, cfg)[0]; nfit += 1; rec('RAWy2', f2)
    rec('RAWens2', 0.5 * (Fl(sy[R_BASE]) + Fl(f2)), 2 * K48)
    # ---- fission arms
    for tau in TAUS:
        yf, yg = cf_fit.fission_copies(y, z, tau); t = '%g' % tau
        Rm = R_MAX if tau == 1.0 else R_BASE            # R4 snapshots are only used by the tau=1 fission-CV curve
        sF, bF, aF = cf_fit.trajectory(R(yf), om1, S_SEL, cfg, Rm); sG, bG, aG = cf_fit.trajectory(R(yg), om1, S_SEL, cfg, Rm); nfit += 2 * (Rm + 1) / 4.0
        Bf = bF[:R_BASE]; Bg = bG[:R_BASE]
        rec('RAWg_t' + t, sG[R_BASE]); rec('RAWf_t' + t, sF[R_BASE])
        sXg, bXg, aXg = cf_fit.trajectory(R(yg), om1, S_SEL, cfg, R_BASE, forced_idx=Bf); nfit += 1; rec('XFERg_t' + t, sXg[R_BASE])
        sNS, bNS, aNS = cf_fit.trajectory(R(y), om1, S_SEL, cfg, R_BASE, forced_idx=Bf); nfit += 1; rec('NS_t' + t, sNS[R_BASE])
        assert all(np.array_equal(a, b) for a, b in zip(bXg, Bf)) and all(np.array_equal(a, b) for a, b in zip(bNS, Bf))      # forced births honoured exactly
        diag['XFERg_t%s_disp' % t] = aXg['birth_disp_px']; diag['XFERg_t%s_resid' % t] = aXg['resid_at_births']; diag['RAWg_t%s_resid' % t] = aG['resid_at_births'][:R_BASE]
        diag['RAWg_t%s_disp' % t] = aG['birth_disp_px'][:R_BASE]; diag['NS_t%s_disp' % t] = aNS['birth_disp_px']
        diag['idx_overlap_t%s' % t] = float(np.mean([len(np.intersect1d(a, b)) / len(a) for a, b in zip(Bf, Bg)]))             # |B_f ∩ B_g| / b, report-only
        diag['idx_overlap_y_t%s' % t] = float(np.mean([len(np.intersect1d(a, b)) / len(a) for a, b in zip(Bf, by[:R_BASE])]))   # |B_f ∩ B_y| / b
        # independence check on the NOISE parts of the copies (clean image removed): corr(e+tau z, e - z/tau)
        ef, eg = cf_fit.fission_copies(e, z, tau); diag['noise_corr_t' + t] = float(np.corrcoef(ef, eg)[0, 1])
        if tau == 1.0:
            sXf, bXf, aXf = cf_fit.trajectory(R(yf), om1, S_SEL, cfg, R_BASE, forced_idx=Bg); nfit += 1; rec('XFERf_t1', sXf[R_BASE])
            sNg, bNg, aNg = cf_fit.trajectory(R(y), om1, S_SEL, cfg, R_BASE, forced_idx=Bg); nfit += 1
            assert all(np.array_equal(a, b) for a, b in zip(bXf, Bg)) and all(np.array_equal(a, b) for a, b in zip(bNg, Bg))
            rec('NSens_t1', 0.5 * (Fl(sNS[R_BASE]) + Fl(sNg[R_BASE])), 2 * K48)          # sNS here is the tau=1 NS fit on full y with births B_f; sNg uses B_g
            rec('XAVG_t1', 0.5 * (Fl(sXg[R_BASE]) + Fl(sXf[R_BASE])), 2 * K48)
            rec('XAVGctrl_t1', 0.5 * (Fl(sG[R_BASE]) + Fl(sF[R_BASE])), 2 * K48)
            cv = [0.5 * (float(np.sum((sG[r] - Fl(yf)) ** 2)) + float(np.sum((sF[r] - Fl(yg)) ** 2))) for r in range(R_MAX + 1)]     # fission-CV at tau=1, two-way (held-out copy squared error)
            diag['cv_R_t1'] = cv
    out = dict(risks_keys=np.array(sorted(risks)), risks_vals=np.array([risks[k] for k in sorted(risks)]), hashes=json.dumps(hashes, sort_keys=True), diag=json.dumps(diag, sort_keys=True),
               K=json.dumps(K, sort_keys=True), n_fit_equiv=np.array(nfit), e_hash=sha(e), z_hash=sha(z), omega1=json.dumps([ENTROPY, 22, ii, m, 0]), omega2=json.dumps([ENTROPY, 22, ii, m, 1]))
    for k, v in risks.items():
        if not np.isfinite(v): raise RuntimeError('non-finite risk %s' % k)
    return task['img'], m, out, time.time() - t0, nfit


def rawy_pipeline_hash(task):
    """Replay check (contract V7): RAWy from the trajectory snapshot must equal gsfast.fit_pipeline(y, omega1, S=1024) bitwise."""
    cfg = _cfg(task['cfg']); cj = json.dumps(task['cfg'], sort_keys=True)
    x, e, z, y, om1, om2 = synth_unit(task['img'], task['m'], cfg, cj)
    f = gsfast.fit_pipeline(np.asarray(y, dtype=np.float64).reshape(cfg.H, cfg.W), om1, S_SEL, cfg)[0]
    return sha(np.asarray(f, dtype=np.float64).reshape(-1))


def stage_spec(stage, M):
    if stage == 'pilot': return dict(images=PILOT_IMAGES, draws=list(range(8)), replay_m=[0])
    if stage == 'dev': return dict(images=DEV_IMAGES, draws=list(range(int(M))), replay_m=[0])
    if stage == 'dev_ext': return dict(images=DEV_IMAGES, draws=list(range(int(M), 2 * int(M))), replay_m=[])
    raise ValueError(stage)


def verify_frozen():
    p = ROOT / 'contracts' / 'CF0_FROZEN_FILES.sha256'
    if not p.exists(): return False, 'manifest MISSING', None
    ent = {}
    for ln in p.read_text(encoding='utf-8').splitlines():
        ln = ln.strip()
        if ln:
            h, name = ln.split(None, 1); ent[name.strip().replace('\\', '/')] = h
    miss = [n for n in FROZEN_FILES if n not in ent]
    bad = [n for n, h in ent.items() if not (ROOT / n).exists() or fsha(ROOT / n) != h]
    return (not miss and not bad), 'missing_entries=%s mismatching_files=%s' % (miss, bad), fsha(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', required=True, choices=['pilot', 'dev', 'dev_ext']); ap.add_argument('--tag', default='x'); ap.add_argument('--M', type=int, default=0)
    ap.add_argument('--workers', type=int, default=WORKERS_DEFAULT); ap.add_argument('--cap_seconds', type=float, default=10800)
    ap.add_argument('--debug_steps', type=int, default=0); ap.add_argument('--max_tasks', type=int, default=0)
    a = ap.parse_args()
    cfg = F0Config(); debug = a.debug_steps > 0
    if debug: cfg = replace(cfg, steps_per_stage=a.debug_steps)
    if a.max_tasks and not debug: sys.exit('--max_tasks is only allowed together with --debug_steps (truncated runs are never evidence)')
    ch = hashlib.sha256((ROOT / 'contracts' / 'CF0_CONTRACT.md').read_bytes()).hexdigest() if (ROOT / 'contracts' / 'CF0_CONTRACT.md').exists() else 'MISSING'
    want = (ROOT / 'contracts' / 'CF0_CONTRACT.sha256').read_text().split()[0] if (ROOT / 'contracts' / 'CF0_CONTRACT.sha256').exists() else 'MISSING'
    fok, fmsg, mdig = verify_frozen()
    if not debug and ch != want: sys.exit('CONTRACT HASH MISMATCH (%s vs %s): refusing to run' % (ch, want))
    if not debug and not fok: sys.exit('FROZEN FILE MANIFEST MISMATCH (%s): refusing to run' % fmsg)
    if a.stage != 'pilot' and (a.M != M_DEV if not debug else a.M <= 0): sys.exit('--M must be %d (pre-registered, fixed)' % M_DEV)
    spec = stage_spec(a.stage, a.M)
    outdir = ROOT / 'outputs' / (('DEBUG-CF-' if debug else 'CF0-') + a.stage + '-' + a.tag)
    outdir.mkdir(parents=True, exist_ok=False)      # atomic reservation: refuse to overwrite
    tasks = [dict(img=i, m=m, cfg=asdict(cfg)) for i in spec['images'] for m in spec['draws']]
    n_expected = len(tasks)
    if a.max_tasks: tasks = tasks[:a.max_tasks]
    t0 = time.time(); done = 0; nfit = 0.0; aborted = False; walls = []
    meta = dict(stage=a.stage, tag=a.tag, debug=debug, M=a.M, draws=spec['draws'], images=list(spec['images']), workers=a.workers, cfg=asdict(cfg), cfg_hash=cfg_hash(cfg), contract_sha=ch, frozen_manifest_sha=mdig, entropy=ENTROPY, taus=list(TAUS),
                python=platform.python_version(), numpy=np.__version__, platform=platform.platform(), start_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), n_tasks=len(tasks), n_expected=n_expected, max_tasks=a.max_tasks)
    (outdir / 'meta.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    with Pool(a.workers) as pool:
        for img, m, out, wall, nf in pool.imap_unordered(run_unit, tasks):
            np.savez_compressed(outdir / ('unit_%s_%d.npz' % (img, m)), **out); done += 1; nfit += nf; walls.append(wall)
            if time.time() - t0 > a.cap_seconds: aborted = True; pool.terminate(); break
    replay_ok = None; rawy_ok = None
    if not aborted and spec['replay_m'] and not a.max_tasks:
        bad = []; bad2 = []
        for i in spec['images']:
            for m in spec['replay_m']:
                _, _, out2, _, _ = run_unit(dict(img=i, m=m, cfg=asdict(cfg)))
                o1 = np.load(outdir / ('unit_%s_%d.npz' % (i, m)), allow_pickle=False)
                if str(o1['hashes']) != str(out2['hashes']) or not np.array_equal(o1['risks_vals'], out2['risks_vals']): bad.append((i, m))
                if rawy_pipeline_hash(dict(img=i, m=m, cfg=asdict(cfg))) != json.loads(str(o1['hashes']))['RAWy']: bad2.append((i, m))
        replay_ok = (len(bad) == 0); rawy_ok = (len(bad2) == 0); meta['replay_bad'] = bad; meta['rawy_pipeline_bad'] = bad2
    meta.update(done=done, n_fit_equiv=nfit, wall_s=time.time() - t0, aborted=aborted, replay_ok=replay_ok, rawy_pipeline_ok=rawy_ok, end_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), unit_wall_median=float(np.median(walls)) if walls else None)
    (outdir / 'meta.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    man = {f.name: fsha(f) for f in sorted(outdir.glob('unit_*.npz'))}; man['meta.json'] = fsha(outdir / 'meta.json')
    (outdir / 'manifest.json').write_text(json.dumps(dict(sha256=man, n_units=len(man) - 1), indent=1), encoding='utf-8')
    print(json.dumps({k: meta[k] for k in ('stage', 'tag', 'done', 'n_tasks', 'wall_s', 'aborted', 'replay_ok', 'rawy_pipeline_ok', 'n_fit_equiv')}))
    sys.exit(3 if aborted else 0)


if __name__ == '__main__':
    main()
