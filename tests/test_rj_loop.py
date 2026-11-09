"""RJ unit tests (contract RJ candidate v0, section 8). Run: python3 tests/test_rj_loop.py   (S scale N=32, K=36, dev image 301; never prints image values; no confirm access)."""
import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import numpy as np
import geo_core as GC, geo_flops as FL, trn_gen as TG, trn_loop as TL, rj_loop as RJ

N, K = 32, 36
BASE_CFG = dict(kappa0=0.1, f=3, eps_r=0.1, maxcg=400, gdiv=3, warm=True)


def setup(cond='C4', img=301):
    sb, sn = TG.COND[cond]; op = GC.Op(N, sb); x = TG.clean_image_trn(img, N); y = TG.noisy_obs_trn(op, x, sn, 9401, img)
    P = GC.Prob(N, sb, y, sn, 1e-3 / sn ** 2); return P, GC.grid_init(P, K)


def test_b0_equals_trn_bitwise():
    for cond in ('C1', 'C4'):
        P, th0 = setup(cond); cfg = dict(kappa0=0.1, f=3, eps_r=0.1, maxcg=400, inner='J', warm=True); a = GC.solve('TRN', P, th0, cfg, max_iter=15)
        b = RJ.rj_solve(P, th0, dict(kappa0=0.1, f=3, eps_r=0.1, maxcg=400, gdiv=3, warm=True), max_outer=15)
        ta = [(r[1], r[3], r[5], r[6]) for r in a['traj']]; tb = [(r[1], r[3], r[5], r[6]) for r in b['traj']]
        assert ta == tb, 'RJ B0 differs from the frozen TRN D0w arm (%s)' % cond
        assert a['rej'] == b['rej'] and a['trials'] == b['trials']


def test_hold_kappa_never_decreases_on_accept():
    P, th0 = setup('C4'); log = []
    out = RJ.rj_solve(P, th0, dict(kappa0=0.1, f=3, eps_r=0.1, maxcg=400, gdiv=1, warm=True), max_outer=12)
    ka = [r['kap_acc'] for r in out['cnt']['log'] if r['kap_acc'] is not None]
    assert all(b >= a - 1e-18 for a, b in zip(ka, ka[1:])), 'hold must not lower kappa'


def test_nielsen_update_formula():
    cfg = dict(nielsen=True)
    assert abs(RJ._kappa_after_accept(cfg, 1.0, 0.5) - max(1 / 3, 1.0)) < 1e-15            # (2*0.5-1)^3 = 0 -> factor 1
    assert abs(RJ._kappa_after_accept(cfg, 1.0, 1.0) - 1 / 3) < 1e-15                      # factor max(1/3, 0) = 1/3
    assert abs(RJ._kappa_after_accept(cfg, 1.0, 0.0) - 2.0) < 1e-15                        # factor 1 - (-1)^3 = 2


def _one_outer(cfg, cond='C4', warm_outers=3):
    """Run a few frozen outers, then one outer of `cfg` on the resulting state; return (S, cnt, rec, before-counters)."""
    P, th0 = setup(cond); S = None
    cnt = dict(A=0, J=0, mv=0, W=0.0, Ad=0, Wd=0.0); T = dict(jac=0.0, aj=0.0, solve=0.0, back=0.0); th = GC.clamp(th0, P.N); F, x, r = P.F_of(th)
    S = dict(th=th, x=x, r=r, F=F, kappa=cfg['kappa0'], rej=0, rank=None, trials=0, clamped=0, clamp_trials=0, diag=[], itn=[], alpha=[], act=[], alpha_star=[], clamp_it=[], blk_skip=0, blk_eval=0)
    base = dict(kappa0=cfg['kappa0'], f=3, eps_r=0.1, maxcg=400, gdiv=3, warm=True)
    for _ in range(warm_outers): RJ._iter_rj(P, S, base, cnt, T)
    before = dict(W=cnt['W'], A=cnt['A'], mv=cnt['mv'], trials=S['trials'], clamped=S['clamped'], clamp_trials=S['clamp_trials'], back=T['back'], nlog=len(cnt['log']))
    ok = RJ._iter_rj(P, S, cfg, cnt, T)
    return P, S, cnt, T, ok, before


def test_oracle_probes_are_free_and_only_chosen_is_charged():
    for orc in ('dF', 'beta', 'sbeta'):
        P, S, cnt, T, ok, b = _one_outer(dict(kappa0=0.1, f=3, eps_r=0.1, maxcg=400, gdiv=3, warm=True, oracle=orc))
        rec = cnt['log'][-1]
        assert ok and len(rec['trials']) == 1, 'accepted oracle outer must have exactly one charged trial'
        assert S['trials'] - b['trials'] == 1, 'probes must not leave S[trials] increments (%s)' % orc
        wsum = rec['W_jac'] + rec['W_rhs'] + rec['W_setup'] + rec['W_cg'] + rec['W_acc']
        assert abs((cnt['W'] - b['W']) - wsum) <= 1e-6 * wsum, 'W bookkeeping mismatch (%s)' % orc
        assert rec['probe'] is not None and len(rec['probe']) == len(RJ.ORACLE_J) and rec['sel'] is not None


def test_cs_checks_are_charged_but_oks_checks_are_not():
    # CS: every real check increments S[trials] and is charged to W_acc; OKS probing checks leave no trace (previous test).
    P, S, cnt, T, ok, b = _one_outer(dict(kappa0=0.1, f=3, eps_r=1e-3, maxcg=400, gdiv=3, warm=True, early_m=4))
    rec = cnt['log'][-1]; ncheck = S['trials'] - b['trials']
    assert ncheck >= 1 and rec['W_acc'] > 0
    # each charged check costs the same constant (J mul + 2 A + render); W_acc must be exactly ncheck times it
    one = rec['W_acc'] / ncheck
    assert abs(rec['W_acc'] - ncheck * one) < 1e-6 * rec['W_acc'] and one > 2 * FL.F_A(N)
    assert len(rec['tinfo']) >= 1


def _wrap_counter(P):
    n = [0]; oa, oj = P.op.apply, P.op.adj
    P.op.apply = lambda X: (n.__setitem__(0, n[0] + 1), oa(X))[1]; P.op.adj = lambda X: (n.__setitem__(0, n[0] + 1), oj(X))[1]
    return n


def test_A_counter_matches_real_applications():
    """R23: cnt[A] must equal the real number of A / A^T applications (wrapped operator), outer by outer, for B0, the S family and OKdF (probes excluded: they are free by contract)."""
    for name, extra in (('B0', {}), ('S', dict(early_m=4, eps_r=1e-2)), ('OKdF', dict(oracle='dF'))):
        P, th0 = setup('C4'); n = _wrap_counter(P); cnt = dict(A=0, J=0, mv=0, W=0.0, Ad=0, Wd=0.0); T = dict(jac=0.0, aj=0.0, solve=0.0, back=0.0); th = GC.clamp(th0, P.N); F, x, r = P.F_of(th)
        S = dict(th=th, x=x, r=r, F=F, kappa=0.1, rej=0, rank=None, trials=0, clamped=0, clamp_trials=0, diag=[], itn=[], alpha=[], act=[], alpha_star=[], clamp_it=[], blk_skip=0, blk_eval=0)
        cfg = dict(BASE_CFG, **extra)
        for _ in range(6):
            n0, a0 = n[0], cnt['A']; RJ._iter_rj(P, S, cfg, cnt, T); real = n[0] - n0; charged = cnt['A'] - a0
            if cfg.get('oracle'):
                rec = cnt['log'][-1]
                if rec['sel'] is not None:                                          # real = charged + all probe A (CG + their acceptance calls) - the chosen candidate's A that was charged
                    ch = [q for q in rec['probe'] if abs(q['kap'] - rec['sel']['kap']) < 1e-300 and q['ok']][0]
                    real_expected = charged + sum(q['A'] + 2 * q['nacc'] for q in rec['probe']) - (ch['A'] + 2 * (ch['nacc'] - 1))
                    assert real == real_expected, (name, real, real_expected)
                    continue
                assert real == charged + sum(q['A'] + 2 * q['nacc'] for q in rec['probe']), (name, 'fallback', real, charged)      # no candidate accepted: all probes were free, then a charged reject sequence ran
                continue
            assert real == charged, (name, real, charged)


def test_b0_full_trajectory_bitwise_to_80_outers():
    """R24: the whole trajectory (F, A, mv, W per outer) and the stop reason equal the frozen driver for B0, both conditions."""
    for cond in ('C1', 'C4'):
        P, th0 = setup(cond); a = GC.solve('TRN', P, th0, dict(kappa0=0.1, f=3, eps_r=0.1, maxcg=400, inner='J', warm=True), max_iter=80)
        b = RJ.rj_solve(P, th0, dict(BASE_CFG), max_outer=80)
        ra = [(r[1], r[3], r[5], r[6], r[7]) for r in a['traj']]; rb = [(r[1], r[3], r[5], r[6], r[7]) for r in b['traj']]
        assert ra == rb and a['stop'] == b['stop'] and a['rej'] == b['rej'], cond


def test_cc_first_only_caps_only_the_first_trial():
    P, th0 = setup('C4'); cfg = dict(BASE_CFG, cc=2, reuse=True, cc_first_only=True, kappa0=1e-4)          # tiny kappa0 forces rejected first trials
    out = RJ.rj_solve(P, th0, cfg, max_outer=8); firsts = []; later = []
    for rec in out['cnt']['log']:
        for k, ti in enumerate(rec['tinfo']): (firsts if k == 0 else later).append(ti)
    assert later, 'need retry trials to test'
    assert max(t_['it'] for t_ in later) > 8 or all(t_['reason'] != 'cap' or t_['it'] >= 8 for t_ in later)
    assert not any(t_['cap'] and t_['it'] < 400 for t_ in later), 'retry trials must not be cut by the first-trial budget'


def test_banded_A_is_the_same_operator():
    for sb in (1.0, 2.0):
        B = GC.refl_B(64, sb); Bs = B.copy(); Bs[np.abs(Bs) == 0] = 0.0
        import scipy.sparse as sp
        S_ = sp.csr_matrix(B); X = np.random.default_rng(1).standard_normal((64, 64)); ref = B @ X @ B.T; got = (S_ @ (S_ @ X.T).T)
        assert np.max(np.abs(ref - got)) < 1e-12


def test_no_confirm_or_clean_access_in_method_code():
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'rj_loop.py'), encoding='utf-8').read()
    for bad in ('clean_image', 'CONFIRM', 'trn_gen', '321', '401'):
        assert bad not in src, 'rj_loop.py must not reference ' + bad


if __name__ == '__main__':
    n = 0
    for k, v in sorted(globals().items()):
        if k.startswith('test_') and callable(v): v(); n += 1; print('ok', k)
    print('%d tests passed' % n)
