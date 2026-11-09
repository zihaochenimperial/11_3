"""V1 unit tests for contract v3 (fission + covariance df). Runs on the host venv via scripts/run_unit_tests.py.
Covers: fission independence/variance, covariance-df estimator (linear smoother = tr H, M-1 unbiased), selection estimator (df_par = k exactly, sdf > 0),
bootstrap identity + stream 13, S=8 I+=I-, forced replay bitwise, P-lin frozen df = rank, static leakage with negative control, C4 key disjointness vs v2, frozen-hash match, stage specs."""
import ast
import hashlib
import importlib
import sys
from dataclasses import asdict, replace
from pathlib import Path
import json
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'experiments'))
import f3_run as R3  # noqa: E402
import f3_analyze as A3  # noqa: E402
from src.f0_config import F0Config  # noqa: E402


def _cfgd(**kw):
    return json.loads(json.dumps(asdict(replace(F0Config(), **kw))))


# ---------------------------------------------------------------- 1. fission
def test_fission_independent_and_variance():
    s0 = F0Config().sigma0; N = 4096; M = 48
    ep = []; em = []; ee = []; zz = []
    for m in range(M):
        e = s0 * R3.rng_for(1, 105, m).standard_normal(N); z = s0 * R3.rng_for(12, 105, m).standard_normal(N)
        ep.append(e + z); em.append(e - z); ee.append(e); zz.append(z)
    ep, em, ee, zz = (np.concatenate(a) for a in (ep, em, ee, zz))
    n = ep.size
    assert abs(ep.var() / (2 * s0 * s0) - 1) < 0.02 and abs(em.var() / (2 * s0 * s0) - 1) < 0.02      # variance 2 sigma0^2
    for a, b in ((ep, em), (ee, zz), (ep, zz)):
        r = float(np.mean(a * b) / np.sqrt(a.var() * b.var()))
        assert abs(r) < 5.0 / np.sqrt(n) or (a is ep and b is zz), r                                   # ep,em and e,z uncorrelated (Gaussian => independent)
    assert abs(float(np.mean(ep * zz)) / (np.sqrt(ep.var() * zz.var())) - 1 / np.sqrt(2)) < 0.02        # sanity: ep = e+z correlates with z at 1/sqrt2
    # same key -> same draw; different key -> different draw
    assert np.array_equal(R3.rng_for(1, 105, 3).standard_normal(5), R3.rng_for(1, 105, 3).standard_normal(5))
    assert not np.array_equal(R3.rng_for(1, 105, 3).standard_normal(5), R3.rng_for(1, 106, 3).standard_normal(5))
    assert not np.array_equal(R3.rng_for(1, 105, 3).standard_normal(5), R3.rng_for(12, 105, 3).standard_normal(5))


def test_run_unit_uses_fission_definitions():
    t = dict(kind='plin', cfg=_cfgd(), img='W0', S=8, m=2)
    key, m, out, w, nf = R3.run_unit(t)
    s0 = F0Config().sigma0
    e = s0 * R3.rng_for(1, 90, 2).standard_normal(64 * 64); z = s0 * R3.rng_for(12, 90, 2).standard_normal(64 * 64)
    assert np.array_equal(out['ep'], e + z) and np.array_equal(out['em'], e - z) and key == ('plin', 'W0', 8, 'np')


# ---------------------------------------------------------------- 2. estimator
def _draws(rng, M, N, s0):
    e = s0 * rng.standard_normal((M, N)); z = s0 * rng.standard_normal((M, N))
    return e + z, e - z


def test_linear_smoother_df_equals_trace_and_m_minus_1_unbiased():
    rng = np.random.default_rng(0); N = 30; s0 = 0.05; sig2 = 2 * s0 * s0; M = 8
    Q, _ = np.linalg.qr(rng.standard_normal((N, N))); lam = np.concatenate([np.ones(6), np.linspace(0.8, 0.1, 6), np.zeros(N - 12)])
    H = (Q * lam) @ Q.T; trH = float(lam.sum()); x = 0.3 * rng.standard_normal(N)
    vals = []
    for r in range(2500):
        ep, em = _draws(rng, M, N, s0)
        vals.append(A3.df_stat((x + ep) @ H.T, (x + em) @ H.T, ep, em, sig2)[0])
    vals = np.array(vals); se = vals.std(ddof=1) / np.sqrt(vals.size)
    assert abs(vals.mean() - trH) < 4 * se, (vals.mean(), trH, se)
    assert abs(vals.mean() - trH) < 0.25            # a /M (instead of /(M-1)) estimator would be ~ trH/8 = 1.1 low at M=8


def test_bootstrap_weights_reproduce_resampled_statistic_and_use_stream_13():
    rng = np.random.default_rng(1); M = 16; N = 20; s0 = 0.05; sig2 = 2 * s0 * s0
    ep, em = _draws(rng, M, N, s0); x = rng.standard_normal(N)
    Xp = np.tanh(x + ep); Xm = np.tanh(x + em)
    boot = A3.Boot(M, B=50)
    idx = np.random.default_rng(np.random.SeedSequence(entropy=20261106, spawn_key=(13,))).integers(0, M, size=(50, M))   # stream 13 of the v3 entropy
    bs = A3.df_stat(Xp, Xm, ep, em, sig2, W=boot.W)
    for b in (0, 7, 49):
        ref = A3.df_stat(Xp[idx[b]], Xm[idx[b]], ep[idx[b]], em[idx[b]], sig2)[0]
        assert abs(bs[b] - ref) < 1e-12 * max(1.0, abs(ref)), (b, bs[b], ref)
    assert np.allclose(boot.W.sum(axis=1), 1.0)


def test_selection_estimator_dfpar_equals_k_and_sdf_positive():
    """Selection x fission: F+ = y+ restricted to I+ = top-k |y+|, G+ = y+ restricted to I- (selected on the independent copy).
    G is selection-independent => df_par = k exactly; F selects on its own data => sdf > 0 for pure noise."""
    rng = np.random.default_rng(2); N = 40; k = 6; s0 = 0.05; sig2 = 2 * s0 * s0; M = 300
    ep, em = _draws(rng, M, N, s0); yp, ym = ep.copy(), em.copy()              # x = 0
    def top(y):
        m = np.zeros_like(y, dtype=bool); idx = np.argsort(-np.abs(y), axis=1)[:, :k]
        np.put_along_axis(m, idx, True, axis=1); return m
    Ip, Im = top(yp), top(ym)
    d = dict(Fp=yp * Ip, Fm=ym * Im, Gp=yp * Im, Gm=ym * Ip, ep=ep, em=em)
    boot = A3.Boot(M, B=400)
    full, se_f = A3.est(d, 'full', sig2, boot); par, se_p = A3.est(d, 'par', sig2, boot); sdf, se_s = A3.est(d, 'sdf', sig2, boot)
    assert abs(par - k) < 4 * se_p, (par, k, se_p)
    assert sdf > 6 * se_s and sdf > 0.5 * k, (sdf, se_s)
    assert abs(full - par - sdf) < 1e-9


# ---------------------------------------------------------------- 3. pipeline identities on the real fitter (short fits)
def _unit(S, m, img='E1', g_s8=True, replay=True, anti=False):
    t = dict(kind='full', cfg=_cfgd(steps_per_stage=3), img=img, S=S, m=m, impl='fast', replay=replay, anti=anti, g_s8=g_s8)
    return R3.run_unit(t)


def test_s8_birth_indices_equal_and_g_equals_f():
    key, m, out, w, nf = _unit(8, 0)
    assert bool(out['idx_equal']) and np.array_equal(out['Ip'], out['Im'])
    assert np.array_equal(out['Gp'], out['Fp']) and np.array_equal(out['Gm'], out['Fm'])          # frozen replay with the same indices is the full fit, bitwise
    assert bool(out['replay_ok'])


def test_s1024_forced_replay_bitwise_and_g_differs():
    key, m, out, w, nf = _unit(1024, 0)
    assert bool(out['replay_ok'])
    assert not np.array_equal(out['Gp'], out['Fp'])       # frozen leg uses the other copy's births
    key2, m2, out2, *_ = _unit(1024, 0)
    for k in ('Fp', 'Fm', 'Gp', 'Gm'): assert np.array_equal(out[k], out2[k]), k          # determinism


def test_s8_identity_shortcut_matches_full_gleg_when_not_run():
    _, _, a, *_ = _unit(8, 9, g_s8=True, replay=False)
    _, _, b, *_ = _unit(8, 9, g_s8=False, replay=False)
    assert np.array_equal(a['Gp'], b['Gp']) and np.array_equal(a['Gm'], b['Gm']) and not bool(b['g_ran'])


def test_plin_frozen_df_equals_mean_rank():
    cfgd = _cfgd(); M = 64; S = 16
    outs = [R3.run_unit(dict(kind='plin', cfg=cfgd, img='W0', S=S, m=m))[2] for m in range(M)]
    d = {k: np.stack([o[k] for o in outs]) for k in ('Fp', 'Fm', 'Gp', 'Gm', 'ep', 'em')}
    s0 = F0Config().sigma0; sig2 = 2 * s0 * s0; boot = A3.Boot(M, B=300)
    par, se = A3.est(d, 'par', sig2, boot); rk = float(np.mean([o['rank_p'] for o in outs]))
    assert abs(par - rk) < 4 * se + 0.5, (par, rk, se)


# ---------------------------------------------------------------- 4. static leakage (+ negative control)
FITTER_CALLS = {'fit_pipeline', 'plin_pipeline', 'plin_frozen', 'fit_no_birth', 'plin_frozen_cols'}
BAD_MODULES = {'synth', 'src.synth', 'reference_eval', 'src.reference_eval'}


def _imports_of(tree):
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): found |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module); found |= {a.name for a in node.names}; found |= {node.module + '.' + a.name for a in node.names}
    return found


def _fitter_call_args(tree):
    """first-positional-argument source of every fitter call (the data vector the fitter sees)."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func; nm = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
            if nm in FITTER_CALLS and node.args: out.append(ast.unparse(node.args[0]))
    return out


ALLOWED_FIRST_ARGS = {'R(yp)', 'R(ym)', 'R(x - ep)'}           # R(x - ep): antithetic input f(x - e+; omega) (pilot P3 only); the fitter receives an array, never the clean-image object


def _violations(src):
    tree = ast.parse(src)
    v = []
    if _imports_of(tree) & {'reference_eval', 'src.reference_eval'}: v.append('imports reference_eval')
    v += ['fitter call with disallowed data arg: ' + a for a in _fitter_call_args(tree) if a not in ALLOWED_FIRST_ARGS]
    return v


def test_leakage_detector_negative_controls():
    assert _violations("from src import reference_eval\n")
    assert _violations("G.fit_pipeline(R(x), om, S, cfg)\n")
    assert _violations("plin.plin_frozen(clean_img, sm, cfg)\n")
    assert not _violations("G.fit_pipeline(R(yp), om, S, cfg)\n")
    assert _imports_of(ast.parse('from src import synth')) & BAD_MODULES and _imports_of(ast.parse('import src.synth')) & BAD_MODULES


@pytest.mark.parametrize('mod', ['gsfit', 'gsfast', 'gskernel', 'plin', 'omega', 'df_est'])
def test_fitter_modules_do_not_import_truth(mod):
    p = ROOT / 'src' / (mod + '.py')
    if not p.exists(): pytest.skip(mod + ' missing')
    assert not (_imports_of(ast.parse(p.read_text(encoding='utf-8'))) & BAD_MODULES), mod


def test_f3_run_fitter_calls_only_see_noisy_vectors():
    assert _violations((ROOT / 'experiments' / 'f3_run.py').read_text(encoding='utf-8')) == []
    assert _fitter_call_args(ast.parse((ROOT / 'experiments' / 'f3_run.py').read_text(encoding='utf-8')))     # the scan actually found calls


def test_f3_analyze_is_pure_numpy_no_src_no_fitters():
    imps = _imports_of(ast.parse((ROOT / 'experiments' / 'f3_analyze.py').read_text(encoding='utf-8')))
    assert not any(i == 'src' or i.startswith('src.') for i in imps), imps
    assert not (imps & BAD_MODULES) and 'torch' not in imps and 'scipy' not in imps


# ---------------------------------------------------------------- 5. C4: seed keys disjoint from v2; hash gate
def test_c4_v3_seed_keys_disjoint_from_v2_and_stream13_independent():
    f0 = importlib.import_module('f0_run')
    v2_ent = F0Config().entropy
    assert R3.ENTROPY != v2_ent and A3.BOOT_SEED == R3.ENTROPY
    src = (ROOT / 'experiments' / 'f3_run.py').read_text(encoding='utf-8'); tree = ast.parse(src)
    run_unit = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'run_unit')
    streams = {n.args[0].value for n in ast.walk(run_unit) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ('rng_for', 'omega_for') and n.args and isinstance(n.args[0], ast.Constant)}
    assert streams == {1, 2, 10, 12}, streams                      # the only streams run_unit draws from
    assert 13 not in streams                                       # bootstrap stream 13 is independent of all data/fit streams
    v3_imgs = {R3.img_index(n) for n in ['W0', 'W1'] + ['E%d' % k for k in range(1, 15)]}
    v2_imgs = set(f0.IMG_IDX.values())
    assert not (v3_imgs & v2_imgs), (v3_imgs, v2_imgs)             # keys are disjoint even if the entropy were equal
    v3_keys = {(s, i) for s in streams | {13} for i in v3_imgs}; v2_keys = {(s, i) for s in range(1, 12) for i in v2_imgs}
    assert not (v3_keys & v2_keys)


def test_contract_v3_hash_matches_frozen_file():
    want = (ROOT / 'contracts' / 'F0_CONTRACT_v3.sha256').read_text().split()[0]
    have = hashlib.sha256((ROOT / 'contracts' / 'F0_CONTRACT_v3.md').read_bytes()).hexdigest()
    assert want == have == '85328d4e9c20b41af3aabfd329d6dd4f561f95a1335357e5788c19294bb699d3'


# ---------------------------------------------------------------- 6. stage specs / task lists
def test_stage_specs_and_tasks():
    cfgd = _cfgd()
    p = R3.stage_spec('pilot', 0)
    assert p['images'] == ('E1', 'E2') and p['M'] == 32 and p['S_list'] == (8, 1024) and p['g_s8_all'] and p['anti'] and p['tM'] == 32 and p['t_img'] == 'E1' and set(p['plin_images']) == {'W0', 'W1', 'E1'}
    q = R3.stage_spec('pilot_m128', 0)
    assert q['images'] == ('E1', 'E2') and q['M'] == 128 and q['S_list'] == (1024,) and not q['replay'] and not q['anti'] and q['tM'] == 0 and q['plin_images'] == ()
    s = R3.stage_spec('stage1', 64)
    assert s['images'] == tuple('E%d' % k for k in range(3, 15)) and s['S_list'] == (8, 1024) and s['M'] == 64 and not set(s['images']) & set(p['images'])
    assert R3.stage_spec('stage1', 64, 'a')['S_list'] == (1024,) and len(R3.stage_spec('stage1', 64, 'a')['images']) == 12
    b = R3.stage_spec('stage1', 64, 'b'); assert b['S_list'] == (1024,) and b['images'] == tuple('E%d' % k for k in range(3, 11))
    T = R3.build_tasks(p, cfgd)
    full = [t for t in T if t['kind'] == 'full']; assert len(full) == 2 * 2 * 32
    assert all(t['g_s8'] for t in full) and all(t['replay'] == (t['m'] < 4) for t in full)
    T1 = [t for t in R3.build_tasks(R3.stage_spec('stage1', 32), cfgd) if t['kind'] == 'full']
    assert len(T1) == 12 * 2 * 32 and all(t['g_s8'] == (t['m'] < 8) for t in T1 if t['S'] == 8)
    assert all(not t['replay'] for t in R3.build_tasks(q, cfgd))
    assert len([t for t in R3.build_tasks(q, cfgd)]) == 2 * 128
    assert [t for t in T if t['kind'] == 'tfull'] and all(t['impl'] == 'torch' and t['S'] == 1024 for t in T if t['kind'] == 'tfull')


# ---------------------------------------------------------------- 7. Stage-1 decision branch on synthetic fixtures (analyzer scope = contract text; D-03)
def _write_stage1_fixture(tmp, sdf_effect, n_img=12, M=32, N=60, k=6, seed=5, bad_plin_extra=False):
    """Toy Stage-1 directory: selection model (top-k |y|); S=1024 frozen legs use the other copy's indices when sdf_effect else G=F; S=8: G=F, I+=I-.
    P-lin cells for W0 / E1 are copied from the real pilot output (deterministic, independent of the fitter)."""
    import shutil
    pil = ROOT / 'outputs' / 'F3-pilot-p1'
    if not (pil / 'plin__W0__S1024__np.npz').exists(): pytest.skip('pilot P-lin outputs missing')
    tmp.mkdir(parents=True, exist_ok=True)
    s0 = F0Config().sigma0; rng = np.random.default_rng(seed)
    def top(y):
        m = np.zeros(y.shape, dtype=bool); idx = np.argsort(-np.abs(y), axis=1)[:, :k]; np.put_along_axis(m, idx, True, axis=1); return m
    for i in range(3, 3 + n_img):
        x = np.zeros(N); x[:5] = 0.4 * (1 + 0.2 * (i % 3))
        e = s0 * rng.standard_normal((M, N)); z = s0 * rng.standard_normal((M, N)); ep, em = e + z, e - z; yp, ym = x + ep, x + em
        Ip, Im = top(yp), top(ym)
        for S in (8, 1024):
            Fp, Fm = yp * Ip, ym * Im
            if S == 1024 and sdf_effect: Gp, Gm = yp * Im, ym * Ip
            else: Gp, Gm = Fp.copy(), Fm.copy()
            np.savez_compressed(tmp / ('full__E%d__S%d__fast.npz' % (i, S)), Fp=Fp, Fm=Fm, Gp=Gp, Gm=Gm, ep=ep, em=em, replay_ok=np.ones(M, bool),
                                idx_equal=np.ones(M, bool) if S == 8 else np.zeros(M, bool), g_ran=np.ones(M, bool), m_index=np.arange(M), unit_wall_s=np.ones(M))
    for img in ('W0', 'E1'):
        for S in (8, 16, 64, 256, 1024):
            shutil.copy(pil / ('plin__%s__S%d__np.npz' % (img, S)), tmp / ('plin__%s__S%d__np.npz' % (img, S)))
    if bad_plin_extra:                                         # a Stage-1 extra-image P-lin cell that would violate df=24 badly: must NOT gate
        z0 = dict(np.load(pil / 'plin__W0__S1024__np.npz')); z0['Gp'] = z0['Gp'] * 3.0; z0['Gm'] = z0['Gm'] * 3.0
        np.savez_compressed(tmp / 'plin__E3__S1024__np.npz', **z0)
    meta = dict(stage='stage1', tag='fx', debug=False, M=M, workers=8, wall_s=3000.0, aborted=None, n_fits_per_s=1.0, cfg=asdict(F0Config()),
                contract_sha256='85328d4e9c20b41af3aabfd329d6dd4f561f95a1335357e5788c19294bb699d3')
    (tmp / 'meta.json').write_text(json.dumps(meta), encoding='utf-8')
    unit = tmp / 'unit.json'; unit.write_text(json.dumps(dict(passed=True)), encoding='utf-8')
    return unit


def _run_analyze(tmp, unit):
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / 'experiments' / 'f3_analyze.py'), str(tmp), '--unit_report', str(unit)], capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads((tmp / 'analysis.json').read_text(encoding='utf-8'))


def test_stage1_branch_h1_holds_when_search_df_present(tmp_path):
    unit = _write_stage1_fixture(tmp_path / 'fx_pos', sdf_effect=True, bad_plin_extra=True)
    res = _run_analyze(tmp_path / 'fx_pos', unit)
    assert res['gates']['P2a_plin_frozen_df_eq_24'] and res['gates']['V2_identities'], res['gates']
    assert res['decision'].startswith('H1 HOLDS'), (res['decision'], res.get('H1'))
    assert res['H1']['n_positive'] == 12 and res['H1']['pooled_sdf'] >= res['H1']['threshold']
    assert 'P1_stage1_report_only' in res and 'P2a_extra_images_report_only' in res        # reported, not gated


def test_stage1_branch_stops_when_no_search_df(tmp_path):
    unit = _write_stage1_fixture(tmp_path / 'fx_null', sdf_effect=False)
    res = _run_analyze(tmp_path / 'fx_null', unit)
    assert res['decision'].startswith('STOP'), (res['decision'], res.get('H1'))
    assert res['H1']['pooled_sdf'] == 0.0 and res['H1']['n_positive'] == 0
