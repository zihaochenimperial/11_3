"""Unit tests for src/cf_fit.py (CF-birth line). Small step counts for speed; equivalence / isolation / independence checks."""
from dataclasses import replace
import numpy as np
import pytest
from numpy.random import SeedSequence
from src import gsfast, cf_fit
from src.f0_config import F0Config

CFG = replace(F0Config(), steps_per_stage=6)


def _y(seed=5):
    return np.random.default_rng(seed).random((64, 64)) * 0.3 + 0.35


def _om(a=1):
    return SeedSequence(entropy=20261107, spawn_key=(22, a, 0))


@pytest.mark.parametrize('R', [0, 1, 2, 3])
def test_snapshot_equals_pipeline_bitwise(R):
    y = _y(); om = _om()
    snaps, births, aux = cf_fit.trajectory(y, om, 1024, CFG, R_max=4)
    f, a = gsfast.fit_pipeline(y, om, 1024, replace(CFG, birth_rounds=R))
    assert np.array_equal(snaps[R], f.reshape(-1))
    assert all(np.array_equal(b, c) for b, c in zip(births[:R], a['birth_idx']))


def test_forced_replay_bitwise():
    y = _y(); om = _om()
    snaps, births, _ = cf_fit.trajectory(y, om, 1024, CFG, R_max=3)
    s2, b2, _ = cf_fit.trajectory(y, om, 1024, CFG, R_max=3, forced_idx=births)
    assert np.array_equal(snaps[3], s2[3]) and all(np.array_equal(a, b) for a, b in zip(births, b2))


def test_determinism():
    y = _y(); om = _om()
    a, ba, _ = cf_fit.trajectory(y, om, 1024, CFG, 3); b, bb, _ = cf_fit.trajectory(y, om, 1024, CFG, 3)
    assert all(np.array_equal(p, q) for p, q in zip(a, b)) and all(np.array_equal(p, q) for p, q in zip(ba, bb))


def test_selection_only_sees_selection_copy():
    """births from y_f must not depend on y_g: changing y_g (even to garbage) leaves B_f bitwise unchanged; XFER fit on y_g uses B_f as given."""
    rng = np.random.default_rng(7)
    x = _y(9); e = 0.08 * rng.standard_normal(x.shape); z = 0.08 * rng.standard_normal(x.shape)
    y = x + e; yf, yg = cf_fit.fission_copies(y, z, 2.0); om = _om(3)
    _, Bf, _ = cf_fit.trajectory(yf, om, 1024, CFG, 3)
    # recompute with a different "y_g" in scope: trajectory on y_f never receives y_g, so identical
    yg2 = rng.random(x.shape)
    _, Bf2, _ = cf_fit.trajectory(yf, om, 1024, CFG, 3)
    assert all(np.array_equal(a, b) for a, b in zip(Bf, Bf2))
    sg, bg, _ = cf_fit.trajectory(yg, om, 1024, CFG, 3, forced_idx=Bf)
    sg2, bg2, _ = cf_fit.trajectory(yg2, om, 1024, CFG, 3, forced_idx=Bf)
    assert all(np.array_equal(a, b) for a, b in zip(bg, Bf)) and all(np.array_equal(a, b) for a, b in zip(bg2, Bf))   # births forced exactly
    assert not np.array_equal(sg[3], sg2[3])                                                                          # fit does depend on the fit copy


def test_fission_copies_algebra_and_independence():
    rng = np.random.default_rng(11); n = 400000; s0 = 0.08
    e = s0 * rng.standard_normal(n); z = s0 * rng.standard_normal(n)
    for tau in (0.5, 1.0, 2.0, 4.0):
        yf, yg = cf_fit.fission_copies(e, z, tau)
        assert abs(np.var(yf) / (s0 ** 2 * (1 + tau ** 2)) - 1) < 0.01
        assert abs(np.var(yg) / (s0 ** 2 * (1 + tau ** -2)) - 1) < 0.01
        c = np.corrcoef(yf, yg)[0, 1]; assert abs(c) < 4.5 / np.sqrt(n)          # independence of the Gaussian pair (corr z-test)
        # exact algebra: cov(yf, yg) = s0^2 (1 - 1) = 0 for population; sum identity y = (yf + tau^2 yg)/(1+tau^2)
        assert np.allclose((yf + tau ** 2 * yg) / (1 + tau ** 2), e, atol=1e-12)


def test_no_clean_image_imports():
    import inspect
    src = inspect.getsource(cf_fit)
    code_lines = [l for l in src.splitlines() if l.strip().startswith(('import ', 'from '))]
    assert not any('synth' in l or 'reference_eval' in l for l in code_lines)


# ---------------- runner-level smoke (Opus round 7): arm list, cost accounting, determinism, analyzer/runner key consistency (debug step count; NOT evidence)
def _runner():
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / 'experiments'))
    import cf_run, cf_analyze
    return cf_run, cf_analyze


def test_run_unit_arms_cost_and_determinism():
    from dataclasses import asdict
    cf_run, cf_analyze = _runner()
    task = dict(img='E21', m=0, cfg=asdict(replace(F0Config(), steps_per_stage=3)))
    img, m, out, wall, nfit = cf_run.run_unit(task)
    _, _, out2, _, nfit2 = cf_run.run_unit(task)
    assert str(out['hashes']) == str(out2['hashes']) and np.array_equal(out['risks_vals'], out2['risks_vals'])
    assert abs(nfit - 18.75) < 1e-12 and nfit == nfit2                       # 4.25 base + 6.5 (tau=1) + 2 x 4.0 (tau=2,4)
    keys = set(str(k) for k in out['risks_keys']); K = __import__('json').loads(str(out['K']))
    need = {n for a, cs in cf_analyze.CANDIDATES.items() for n in [a] + cs} - {'RAWcv'}
    assert need <= keys                                                      # every analyzer arm is produced by the runner (guards fixture drift)
    for name in ('RAWens2', 'RANDens2', 'XAVG_t1', 'XAVGctrl_t1', 'NSens_t1'): assert K[name] == 96
    for name in ('RAWy', 'RANDy', 'XFERg_t1', 'NS_t4', 'RAWg_t2'): assert K[name] == 48
    d = __import__('json').loads(str(out['diag']))
    assert len(d['cv_R_t1']) == 5 and abs(d['ez_corr']) < 0.1 and all(abs(d['noise_corr_t%g' % t]) < 0.1 for t in (1.0, 2.0, 4.0))
    assert cf_run.rawy_pipeline_hash(task) == __import__('json').loads(str(out['hashes']))['RAWy']   # RAWy trajectory snapshot == gsfast.fit_pipeline bitwise


def test_runner_refuses_truncation_and_wrong_M(tmp_path):
    import subprocess, sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, str(root / 'experiments' / 'cf_run.py'), '--stage=dev', '--M=16', '--tag=zz_test'], capture_output=True, text=True)
    assert r.returncode != 0 and ('--M must be 32' in r.stderr or 'MISMATCH' in r.stderr or 'MISSING' in r.stderr or 'refusing' in r.stderr)
    r = subprocess.run([sys.executable, str(root / 'experiments' / 'cf_run.py'), '--stage=pilot', '--max_tasks=3', '--tag=zz_test'], capture_output=True, text=True)
    assert r.returncode != 0 and 'max_tasks' in r.stderr
    assert not (root / 'outputs' / 'CF0-dev-zz_test').exists() and not (root / 'outputs' / 'CF0-pilot-zz_test').exists()
