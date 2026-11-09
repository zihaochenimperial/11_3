"""Fixture tests for experiments/cf_analyze.py (FAIL-0004 lesson: the analyzer is frozen with the contract and has fixtures covering GO / STOP / INCONCLUSIVE / comparator dominance / pilot masking / INVALID / input integrity).
Round-7 additions (Opus): within-candidate Bonferroni STOP rule with a fixture where the retired c*-rule would have said STOP, ensemble competitors for XAVG, V8 input gate, frozen-file manifest, t-quantile helper."""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experiments'))
import cf_analyze as A

NAMES = (['RAWy', 'RANDy', 'RANDens2', 'RAWy2', 'RAWens2', 'RAWcv', 'RAWoracleR', 'NSens_t1'] + [f'{p}_t{t}' for p in ('RAWg', 'RAWf', 'XFERg', 'NS') for t in ('1', '2', '4')]
         + ['XFERf_t1', 'XAVG_t1', 'XAVGctrl_t1'] + ['RAWy_R%d' % r for r in range(5)])
IMGS = list(A.DEV_IMAGES)


def build(factors, M=4, img_noise=None, seed=0, imgs=None):
    """risk = base_i * factor[name] * (1 + 0.01 z_m) (CRN across arms); optional standardized image-level multiplicative noise on selected arms (dict name->sd)."""
    imgs = imgs or IMGS; rng = np.random.default_rng(seed); U = {}; std_noise = {}
    for n, sd in (img_noise or {}).items():                         # standardized across images (exact mean 0, SD sd) so the fixture is not sample-dependent
        v = rng.standard_normal(len(imgs)); std_noise[n] = sd * (v - v.mean()) / v.std()
    for ii_, i in enumerate(imgs):
        base = {'D1': 4.0, 'D2': 6.5, 'D3': 25.0}[A.img_type(i)] * (1 + 0.05 * rng.standard_normal())
        U[i] = {}; ieff = {n: float(std_noise[n][ii_]) for n in std_noise}
        for m in range(M):
            zc = 0.01 * rng.standard_normal(); r = {}
            for n in NAMES: r[n] = base * (1 + zc)
            for n, f in factors.items(): r[n] = base * f * (1 + zc)
            for n, e_ in ieff.items(): r[n] *= np.exp(e_)
            r['RAWy_R3'] = r['RAWy']
            U[i][m] = dict(risks=r, diag={'noise_corr_t1': 0.0, 'noise_corr_t2': 0.0, 'noise_corr_t4': 0.0, 'ez_corr': 0.0}, K={}, nfit=18.75, Rstar=3, omega1='[20261107,22,100,%d,0]' % m, omega2='[20261107,22,100,%d,1]' % m)
    return U


OTHERS = {'XFERg_t1': 1.6, 'XFERg_t2': 1.4, 'XAVG_t1': 1.2}


def test_go_fixture():
    U = build({'XFERg_t4': 0.90, 'XFERg_t1': 1.5, 'XFERg_t2': 1.2, 'XAVG_t1': 1.1})
    res = A.dev_analysis(U)
    assert res['verdict'] == 'GO-dev' and res['GO_candidates'] == ['XFERg_t4']
    assert res['candidates']['XFERg_t4']['NU_vs_RAWy'] > 0.09


def test_stop_fixture():
    U = build({'XFERg_t4': 1.3, 'XFERg_t1': 1.6, 'XFERg_t2': 1.4, 'XAVG_t1': 1.2})
    res = A.dev_analysis(U)
    assert res['verdict'] == 'STOP' and res['GO_candidates'] == []
    assert all(r['STOP_pass'] for r in res['candidates'].values())


def test_inconclusive_fixture():
    # candidate near +0.5% with large between-image spread: neither GO nor STOP
    U = build({'XFERg_t4': 0.995, **OTHERS}, img_noise={'XFERg_t4': 0.06})
    res = A.dev_analysis(U)
    assert res['verdict'] == 'INCONCLUSIVE', res['candidates']['XFERg_t4']


def test_comparator_dominance_blocks_go_and_gives_stop():
    # XFERg_t4 beats RAWy by 10% but NS_t4 (same selection noise, no independence) is better still -> independence explanation dead: no GO
    U = build({'XFERg_t4': 0.90, 'NS_t4': 0.85, **OTHERS})
    res = A.dev_analysis(U)
    assert 'XFERg_t4' not in res['GO_candidates'] and res['verdict'] == 'STOP'
    assert res['candidates']['XFERg_t4']['best_competitor'] == 'NS_t4' and res['candidates']['XFERg_t4']['UB_stop_competitor'] == 'NS_t4'


def test_k_axis_baseline_blocks_go():
    U = build({'XFERg_t4': 0.90, 'RAWcv': 0.895, **OTHERS})
    res = A.dev_analysis(U)
    assert 'XFERg_t4' not in res['GO_candidates']      # NU vs RAWcv = +0.56% < +1%


def test_ensemble_competitors_block_xavg_go():
    # XAVG beats RAWy/RAWens2 by 10% but the equal-K randomized-position ensemble RANDens2 (RandOMP analogue) is better still -> no GO; likewise NSens
    for strong in ('RANDens2', 'NSens_t1'):
        U = build({'XAVG_t1': 0.90, strong: 0.85, 'XFERg_t1': 1.6, 'XFERg_t2': 1.4, 'XFERg_t4': 1.3})
        res = A.dev_analysis(U)
        assert 'XAVG_t1' not in res['GO_candidates'] and res['candidates']['XAVG_t1']['UB_stop_competitor'] == strong and res['verdict'] == 'STOP'
    assert {'NSens_t1', 'RANDens2'} <= set(A.CANDIDATES['XAVG_t1'])


def test_stop_rule_within_candidate_bonferroni_vs_retired_cstar_rule():
    # Candidate beats every competitor by 1.5% (true NU >= 1%), but one competitor's sample happens to look like +0.3% with spread; the retired c*-rule would call STOP, the Bonferroni min-UB rule must not.
    U = build({'XFERg_t4': 0.985, 'NS_t4': 0.985 / 0.997, **OTHERS}, img_noise={'NS_t4': 0.0142})
    res = A.dev_analysis(U); row = res['candidates']['XFERg_t4']
    assert row['best_competitor'] == 'NS_t4' and row['retired_cstar_rule_UB95_report_only'] < A.STOP_NU        # old rule: STOP-eligible
    assert row['UB_stop'] >= A.STOP_NU and not row['STOP_pass']                                                   # new rule: not STOP
    assert res['verdict'] == 'INCONCLUSIVE' and 'XFERg_t4' not in res['GO_candidates']


def test_two_look_alpha_constants_and_stop_quantile():
    assert abs(A.ALPHA_GO - 0.05 / 8) < 1e-15 and abs(A.ALPHA_STOP_TOTAL - 0.025) < 1e-15
    assert abs(A.stop_q(4) - (1 - 0.025 / 4)) < 1e-15 and abs(A.stop_q(8) - (1 - 0.025 / 8)) < 1e-15 and A.B_BOOT == 10000 and A.M_DEV == 32


def test_t_quantiles_report_only_helper():
    assert abs(A.t_ppf(0.975, 17) - 2.1098) < 2e-3 and abs(A.t_ppf(0.95, 17) - 1.7396) < 2e-3 and abs(A.t_ppf(0.95, 1000) - 1.6465) < 3e-3


def test_pilot_masking_all_contrasts():
    U = build({'XFERg_t4': 0.90, 'XFERg_t1': 1.5, 'XFERg_t2': 1.2, 'XAVG_t1': 1.1}, M=8)
    rep = A.pilot_report({k: U[k] for k in IMGS[:4]}, {})
    s = json.dumps(rep)
    assert rep['masked'] and 'NU' not in s and 'mean' not in s.replace('median', '')
    want = {'%s_vs_%s' % (a, b) for a, cs in A.CANDIDATES.items() for b in cs}
    assert set(rep['paired_sd']) == want and len(want) == 20 and 'M_dev' not in rep


def test_pilot_has_no_M_rule_and_M_is_fixed():
    assert A.M_DEV == 32 and not hasattr(A, 'M_CHOICES')


def test_family_bonferroni_and_bootstrap_determinism():
    U = build({'XFERg_t4': 0.95})
    a = A.dev_analysis(U); b = A.dev_analysis(U)
    assert json.dumps(a, default=float) == json.dumps(b, default=float)


# ---------------- validity gates, input integrity and frozen-file manifest
def fake_root(tmp):
    for rel in A.FROZEN_FILES:
        p = tmp / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('content of ' + rel)
    ent = {rel: A.sha_file(tmp / rel) for rel in A.FROZEN_FILES}
    (tmp / 'contracts' / 'CF0_FROZEN_FILES.sha256').write_text(''.join('%s  %s\n' % (h, n) for n, h in ent.items()))
    (tmp / 'contracts' / 'CF0_CONTRACT.sha256').write_text(ent['contracts/CF0_CONTRACT.md'] + '\n')
    return ent, A.sha_file(tmp / 'contracts' / 'CF0_FROZEN_FILES.sha256'), ent['contracts/CF0_CONTRACT.md']


def mk_meta(stage, ch, mdig, **kw):
    images = list(A.PILOT_IMAGES) if stage == 'pilot' else list(A.DEV_IMAGES)
    draws = {'pilot': list(range(8)), 'dev': list(range(32)), 'dev_ext': list(range(32, 64))}[stage]; ext = stage == 'dev_ext'
    m = dict(stage=stage, debug=False, contract_sha=ch, frozen_manifest_sha=mdig, replay_ok=None if ext else True, rawy_pipeline_ok=None if ext else True, aborted=False,
             n_tasks=len(images) * len(draws), done=len(images) * len(draws), wall_s=100.0, M=0 if stage == 'pilot' else 32, images=images, draws=draws, max_tasks=0)
    m.update(kw); return m


def good_setup(tmp, stages=('dev',)):
    ent, mdig, ch = fake_root(tmp)
    U = build({'XFERg_t4': 0.9}, M=64 if 'dev_ext' in stages else 32) if stages != ('pilot',) else build({'XFERg_t4': 0.9}, M=8, imgs=list(A.PILOT_IMAGES))
    metas = [mk_meta(s, ch, mdig) for s in stages]
    ur = dict(passed=True, hashes={k: h for k, h in ent.items() if not k.startswith('contracts/')})
    integ = dict(dups=[], manifest_ok=[True] * len(metas))
    return metas, U, ur, integ, tmp


def test_valid_inputs_pass_all_gates(tmp_path):
    for k, st in enumerate((('pilot',), ('dev',), ('dev', 'dev_ext'))):
        d = tmp_path / ('r%d' % k); d.mkdir()
        metas, U, ur, integ, root = good_setup(d, st)
        v = A.validity(metas, U, ur, integ, root=root)
        assert v['all_valid'], (st, {k_: v[k_] for k_ in v if not k_.startswith('_')}, v['_V8_reasons'])


def _bad(tmp_path, mut, flag):
    metas, U, ur, integ, root = good_setup(tmp_path, ('dev',))
    out = mut(metas, U, ur, integ, root) or (metas, U, ur, integ)
    metas, U, ur, integ = out
    v = A.validity(metas, U, ur, integ, root=root)
    assert not v['all_valid'] and not v[flag], (flag, v)
    return v


def test_inputs_gate_duplicates_mixed_stages_incomplete_and_truncated(tmp_path):
    import copy
    def dup(m, U, ur, i, r): i['dups'] = [('E21', 3)]
    (tmp_path / 'a').mkdir(); _bad(tmp_path / 'a', dup, 'V8_inputs')
    def mixed(m, U, ur, i, r):
        _, ch, md = m[0], m[0]['contract_sha'], m[0]['frozen_manifest_sha']; return [mk_meta('pilot', ch, md), m[0]], U, ur, dict(dups=[], manifest_ok=[True, True])
    (tmp_path / 'b').mkdir(); _bad(tmp_path / 'b', mixed, 'V8_inputs')
    def ext_only(m, U, ur, i, r): return [mk_meta('dev_ext', m[0]['contract_sha'], m[0]['frozen_manifest_sha'])], U, ur, i
    (tmp_path / 'c').mkdir(); _bad(tmp_path / 'c', ext_only, 'V8_inputs')
    def wrongM(m, U, ur, i, r): m[0]['M'] = 16
    (tmp_path / 'd').mkdir(); _bad(tmp_path / 'd', wrongM, 'V8_inputs')
    def missing_draw(m, U, ur, i, r): del U['E21'][5]
    (tmp_path / 'e').mkdir(); _bad(tmp_path / 'e', missing_draw, 'V8_inputs')
    def missing_img(m, U, ur, i, r): del U['E38']
    (tmp_path / 'f').mkdir(); _bad(tmp_path / 'f', missing_img, 'V8_inputs')
    def pilot_img(m, U, ur, i, r): U['E15'] = copy.deepcopy(U['E21'])
    (tmp_path / 'g').mkdir(); _bad(tmp_path / 'g', pilot_img, 'V8_inputs')
    def trunc(m, U, ur, i, r): m[0]['max_tasks'] = 5
    (tmp_path / 'h').mkdir(); _bad(tmp_path / 'h', trunc, 'V8_inputs')
    def nomanifest(m, U, ur, i, r): i['manifest_ok'] = [False]
    (tmp_path / 'i').mkdir(); _bad(tmp_path / 'i', nomanifest, 'V8_inputs')
    def debug(m, U, ur, i, r): m[0]['debug'] = True
    (tmp_path / 'j').mkdir(); v = _bad(tmp_path / 'j', debug, 'V8_inputs'); assert not v['V0_contract_and_frozen_files']


def test_frozen_file_tamper_replay_and_unit_report_flags(tmp_path):
    def tamper(m, U, ur, i, r): (r / 'experiments' / 'cf_run.py').write_text('tampered')
    (tmp_path / 'a').mkdir(); _bad(tmp_path / 'a', tamper, 'V0_contract_and_frozen_files')
    def badreplay(m, U, ur, i, r): m[0]['replay_ok'] = False
    (tmp_path / 'b').mkdir(); _bad(tmp_path / 'b', badreplay, 'V2_replay_bitwise')
    def norawy(m, U, ur, i, r): m[0]['rawy_pipeline_ok'] = False
    (tmp_path / 'c').mkdir(); _bad(tmp_path / 'c', norawy, 'V7_finite_and_RAWy_equals_pipeline')
    def badunit(m, U, ur, i, r): ur['hashes']['src/cf_fit.py'] = 'deadbeef'
    (tmp_path / 'd').mkdir(); _bad(tmp_path / 'd', badunit, 'V1_unit_tests')
    def abort(m, U, ur, i, r): m[0].update(aborted=True, done=10)
    (tmp_path / 'e').mkdir(); _bad(tmp_path / 'e', abort, 'V3_complete')
    def slow(m, U, ur, i, r): m[0]['wall_s'] = 20000.0
    (tmp_path / 'f').mkdir(); _bad(tmp_path / 'f', slow, 'V6_wall<=3h_per_run')
    def dependent(m, U, ur, i, r):
        for im in U:
            for u in U[im].values(): u['diag']['ez_corr'] = 0.05
    (tmp_path / 'g').mkdir(); _bad(tmp_path / 'g', dependent, 'V5_independence_abs_z<4')
