"""Fixture tests for experiments/cf_analyze.py (FAIL-0004 lesson: the analyzer is frozen with the contract and has fixtures covering GO / STOP / INCONCLUSIVE / comparator dominance / pilot masking / INVALID)."""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experiments'))
import cf_analyze as A

NAMES = ['RAWy', 'RANDy', 'RAWy2', 'RAWens2', 'RAWcv', 'RAWoracleR'] + [f'{p}_t{t}' for p in ('RAWg', 'RAWf', 'XFERg', 'NS') for t in ('1', '2', '4')] + ['XFERf_t1', 'XAVG_t1', 'XAVGctrl_t1'] + ['RAWy_R%d' % r for r in range(5)]
IMGS = ['E%d' % k for k in range(21, 39)]


def build(factors, M=4, img_noise=0.0, seed=0):
    """risk = base_i * factor[name] * (1 + 0.01 z_m) (CRN across arms); optional per-image multiplicative noise on selected arms (dict name->sd)."""
    rng = np.random.default_rng(seed); U = {}
    std_noise = {}
    for n, sd in (img_noise or {}).items():                         # standardized across images (exact mean 0, SD sd) so the fixture is not sample-dependent
        v = rng.standard_normal(len(IMGS)); std_noise[n] = sd * (v - v.mean()) / v.std()
    for ii_, i in enumerate(IMGS):
        base = {'D1': 4.0, 'D2': 6.5, 'D3': 25.0}[A.img_type(i)] * (1 + 0.05 * rng.standard_normal())
        U[i] = {}; ieff = {n: float(std_noise[n][ii_]) for n in std_noise}      # image-level multiplicative effect, shared by all draws
        for m in range(M):
            zc = 0.01 * rng.standard_normal(); r = {}
            for n in NAMES: r[n] = base * (1 + zc)
            for n, f in factors.items(): r[n] = base * f * (1 + zc)
            for n, e_ in ieff.items(): r[n] *= np.exp(e_)
            r['RAWy_R3'] = r['RAWy']
            U[i][m] = dict(risks=r, diag={'noise_corr_t1': 0.0, 'noise_corr_t2': 0.0, 'noise_corr_t4': 0.0}, K={}, nfit=17.75, Rstar=3, omega1='[20261107,22,100,%d,0]' % m, omega2='[20261107,22,100,%d,1]' % m)
    return U


def test_go_fixture():
    U = build({'XFERg_t4': 0.90, 'XFERg_t1': 1.5, 'XFERg_t2': 1.2, 'XAVG_t1': 1.1})
    res = A.dev_analysis(U)
    assert res['verdict'] == 'GO-dev' and res['GO_candidates'] == ['XFERg_t4']
    assert res['candidates']['XFERg_t4']['NU_vs_RAWy'] > 0.09


def test_stop_fixture():
    U = build({'XFERg_t4': 1.3, 'XFERg_t1': 1.6, 'XFERg_t2': 1.4, 'XAVG_t1': 1.2})
    res = A.dev_analysis(U)
    assert res['verdict'] == 'STOP' and res['GO_candidates'] == []


def test_inconclusive_fixture():
    # candidate near +0.5% with large between-image spread: neither GO nor STOP
    U = build({'XFERg_t4': 0.995, 'XFERg_t1': 1.6, 'XFERg_t2': 1.4, 'XAVG_t1': 1.2}, img_noise={'XFERg_t4': 0.06})
    res = A.dev_analysis(U)
    assert res['verdict'] == 'INCONCLUSIVE', res['candidates']['XFERg_t4']


def test_comparator_dominance_blocks_go_and_gives_stop():
    # XFERg_t4 beats RAWy by 10% but NS_t4 (same selection noise, no independence) is better still -> independence explanation dead: no GO
    U = build({'XFERg_t4': 0.90, 'NS_t4': 0.85, 'XFERg_t1': 1.6, 'XFERg_t2': 1.4, 'XAVG_t1': 1.2})
    res = A.dev_analysis(U)
    assert 'XFERg_t4' not in res['GO_candidates'] and res['verdict'] == 'STOP'
    assert res['candidates']['XFERg_t4']['best_competitor'] == 'NS_t4'


def test_k_axis_baseline_blocks_go():
    U = build({'XFERg_t4': 0.90, 'RAWcv': 0.895, 'XFERg_t1': 1.6, 'XFERg_t2': 1.4, 'XAVG_t1': 1.2})
    res = A.dev_analysis(U)
    assert 'XFERg_t4' not in res['GO_candidates']      # NU vs RAWcv = +0.56% < +1%


def test_pilot_masking_and_M_rule():
    U = build({'XFERg_t4': 0.90, 'XFERg_t1': 1.5, 'XFERg_t2': 1.2, 'XAVG_t1': 1.1}, M=8)
    rep = A.pilot_report({k: U[k] for k in IMGS[:4]}, {})
    s = json.dumps(rep)
    assert rep['masked'] and 'NU' not in s and 'mean' not in s.replace('median', '')
    assert rep['M_dev'] in A.M_CHOICES and set(rep['paired_sd']) >= {'XFERg_t4_vs_RAWy', 'XAVG_t1_vs_RAWens2'}


def test_validity_flags(tmp_path, monkeypatch):
    U = build({'XFERg_t4': 0.9}, M=2)
    metas = [dict(debug=False, contract_sha='X', replay_ok=False, aborted=False, done=36, n_tasks=36, wall_s=100.0)]
    v = A.validity(metas, U, {'passed': True, 'hashes': {}})
    assert not v['all_valid'] and not v['V2_replay_bitwise'] and not v['V0_contract_hash'] and not v['V1_unit_tests']
    metas2 = [dict(debug=False, contract_sha='X', replay_ok=True, aborted=True, done=10, n_tasks=36, wall_s=100.0)]
    assert not A.validity(metas2, U, None)['V3_complete']


def test_family_bonferroni_and_bootstrap_determinism():
    U = build({'XFERg_t4': 0.95})
    a = A.dev_analysis(U); b = A.dev_analysis(U)
    assert json.dumps(a, default=float) == json.dumps(b, default=float)
    assert abs(A.ALPHA_FAMILY - 0.0125) < 1e-12
