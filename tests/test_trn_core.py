"""TRN unit tests (contract TRN v1.1 section 8). Run: python3 tests/test_trn_core.py   (S scale only, dev image 301; never prints image values; confirm gate tests use a temp freeze record)."""
import os, sys, tempfile, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import numpy as np
import geo_core as GC, geo_gen as GG, trn_gen as TG, trn_core as TC, trn_study as TS, trn_loop as TL

N, K = 32, 36
def setup(cond='C4', img=301):
    sb, sn = TG.COND[cond]; op = GC.Op(N, sb); x = TG.clean_image_trn(img, N); y = TG.noisy_obs_trn(op, x, sn, 9401, img)
    P = GC.Prob(N, sb, y, sn, 1e-3 / sn ** 2); return P, GC.grid_init(P, K)

def test_seeds_and_sets():
    ks = set(TG.seed_keys()); assert len(ks) > 0
    assert not (ks & set(map(tuple, GG.seed_keys()))), 'TRN keys overlap geo_gen keys'
    assert {k[0] for k in ks} <= {10, 11}
    for a, b in [(TG.DEV_IMGS, TG.CONFIRM_IMGS), (TG.DEV_IMGS, TG.TRAIN_IMGS), (TG.CONFIRM_IMGS, TG.CONFIRM_TRN5_IMGS), (TG.TRAIN_IMGS, TG.CONFIRM_TRN5_IMGS), (TG.CONFIRM_IMGS, TG.TRAIN_IMGS)]:
        assert not set(a) & set(b)
    assert not (set(TG.DEV_IMGS + TG.CONFIRM_IMGS + TG.TRAIN_IMGS + TG.CONFIRM_TRN5_IMGS) & TG.USED_OR_OLD)
    assert 313 in TG.DEV_IMGS and 320 in TG.DEV_IMGS and 401 in TG.CONFIRM_TRN5_IMGS

def _expect_refuse(fn):
    try: fn()
    except AssertionError: return True
    return False

def _modsha_lines():
    here = os.path.dirname(TG.__file__); out = []
    for nm, mod in list(sys.modules.items()):
        f = getattr(mod, '__file__', None)
        if f and os.path.basename(f).startswith('trn_') and os.path.dirname(os.path.abspath(f)) == os.path.abspath(here):
            out.append('MODULE_SHA256 %s %s' % (hashlib.sha256(open(f, 'rb').read()).hexdigest(), os.path.basename(f)))
    return '\n'.join(out) + '\n'

def test_confirm_gate_all_cases_dummy_index():
    """The gate is tested with a DUMMY confirm index (9999): no real confirm image (321-344) is ever synthesised (Opus C6)."""
    old = TG.FREEZE_RECORD; oldc = list(TG.CONFIRM_IMGS); me = os.path.abspath(__file__); sha = hashlib.sha256(open(me, 'rb').read()).hexdigest(); DUM = 9999; mods = _modsha_lines()
    try:
        TG.CONFIRM_IMGS.append(DUM); d = tempfile.mkdtemp(); TG.FREEZE_RECORD = os.path.join(d, 'rec.txt')
        os.environ.pop('TRN_CONFIRM_UNLOCK', None); TG._CONFIRM_SESSION[0] = False
        assert _expect_refuse(lambda: TG.clean_image_trn(DUM, 32)), 'must refuse without env'
        os.environ['TRN_CONFIRM_UNLOCK'] = '1'
        assert _expect_refuse(lambda: TG.clean_image_trn(DUM, 32)), 'must refuse without a record'
        open(TG.FREEZE_RECORD, 'w').write('ANALYZER_SHA256 %s test\n%s' % (sha, mods))
        assert _expect_refuse(lambda: TG.clean_image_trn(DUM, 32)), 'must refuse without CONFIRM_UNSEALED'
        open(TG.FREEZE_RECORD, 'w').write('CONFIRM_UNSEALED x\nANALYZER_SHA256 %s test\n%s' % ('0' * 64, mods))
        assert _expect_refuse(lambda: TG.clean_image_trn(DUM, 32)), 'must refuse with wrong analyzer sha'
        assert _expect_refuse(lambda: TG.noisy_obs_trn(GC.Op(32, 1), np.zeros((32, 32)), 0.01, 9411, DUM)), 'noise generator gated too'
        open(TG.FREEZE_RECORD, 'w').write('CONFIRM_UNSEALED x\nANALYZER_SHA256 %s test\n' % sha)
        assert _expect_refuse(lambda: TG.clean_image_trn(DUM, 32)), 'must refuse when loaded src/trn_* modules are not registered'
        bad = mods.replace('MODULE_SHA256 ', 'MODULE_SHA256 00', 1)
        open(TG.FREEZE_RECORD, 'w').write('CONFIRM_UNSEALED x\nANALYZER_SHA256 %s test\n%s' % (sha, bad))
        assert _expect_refuse(lambda: TG.clean_image_trn(DUM, 32)), 'must refuse when a module sha differs'
        open(TG.FREEZE_RECORD, 'w').write('CONFIRM_UNSEALED x\nANALYZER_SHA256 %s test\nCONFIRM_CONSUMED earlier\n%s' % (sha, mods))
        assert _expect_refuse(lambda: TG.clean_image_trn(DUM, 32)), 'must refuse after consumption'
        assert _expect_refuse(lambda: TG.clean_image_trn(401, 32)), 'confirm-TRN5 sealed unconditionally'
        open(TG.FREEZE_RECORD, 'w').write('CONFIRM_UNSEALED x\nANALYZER_SHA256 %s test\n%s' % (sha, mods))
        x = TG.clean_image_trn(DUM, 32); assert x.shape == (32, 32)
        assert 'CONFIRM_CONSUMED' in open(TG.FREEZE_RECORD).read()
        TG._CONFIRM_SESSION[0] = False
        assert _expect_refuse(lambda: TG.clean_image_trn(DUM, 32)), 'second process/session must refuse'
        assert _expect_refuse(lambda: TG.clean_image_trn(401, 32))
    finally:
        TG.FREEZE_RECORD = old; TG.CONFIRM_IMGS[:] = oldc; TG._CONFIRM_SESSION[0] = False; os.environ.pop('TRN_CONFIRM_UNLOCK', None)

def closed_log(P, th0, n=8, **kw):
    cfg = dict(kappa0=1e-2, f=3, eps_r=1e-2, maxcg=300, inner='J'); cfg.update(kw); o = GC.solve('TRN', P, th0, cfg, max_iter=n)
    return [r for r in o['cnt']['log'] if r.get('kap_acc')], o

def _state(P, th0, t=3):
    log, o = closed_log(P, th0, n=t + 5); assert len(log) > t; p_, c_ = log[t - 1], log[t]                       # B* closed-loop states, accepted-trial kappa (no GEO reference trajectory)
    return TC.Inner(P, p_['th'], p_['kap_acc']), TC.Inner(P, c_['th'], c_['kap_acc']), c_['F']

def test_spectrum_identities():
    P, th0 = setup(); Ip, It, Ft = _state(P, th0); D = It.dense(); V = D['V']
    assert np.abs(V.T @ np.diag(D['D']) @ V - np.eye(len(D['lam']))).max() < 1e-10                    # D-orthonormal
    assert abs(D['energy'].sum() - D['dH2']) < 1e-8 * D['dH2']                                       # sum e = ||delta*||_H^2
    d = D['dstar']; dq = It.g @ d - 0.5 * d[D['idx']] @ D['H'] @ d[D['idx']]; assert abs(dq - D['dq_star']) < 1e-8 * abs(dq)
    v = np.random.default_rng(0).standard_normal(It.p) * It.mask; assert np.abs(It.Hmv(v)[D['idx']] - D['H'] @ v[D['idx']]).max() < 1e-9 * np.abs(D['H'] @ v[D['idx']]).max() + 1e-12
    k = np.flatnonzero(D['keep'])[0]; assert D['lam'][k] > D['tau']                                  # first kept direction is above tau, nothing below tau is used
    assert np.all(D['energy'][~D['keep']] == 0)
    # Delta q(d*) - Delta q(d) = 1/2 ||d - d*||_H^2
    dd = D['dstar'] * 0.5; e = (dd - D['dstar'])[D['idx']]; dqd = It.g @ dd - 0.5 * dd[D['idx']] @ D['H'] @ dd[D['idx']]
    assert abs((D['dq_star'] - dqd) - 0.5 * e @ D['H'] @ e) < 1e-8 * abs(D['dq_star'])

def test_dpcg_converges_and_deflation_helps():
    P, th0 = setup(); Ip, It, Ft = _state(P, th0); D = It.dense(); idx = D['idx']
    plain = TS.run_cg(It, D, It.g, It.dinvJ, floor=0.0, safety=216, rhos=(1e-2,))
    Vs, _ = TS.spectral_subspace(D, 16, 'smallest'); W = It._embed(idx, Vs)
    defl = TS.run_cg(It, D, It.g, It.dinvJ, W=W, floor=0.0, safety=216, rhos=(1e-2,))
    assert plain['hits'][1e-2] is not None and defl['hits'][1e-2] is not None
    assert defl['hits'][1e-2][0] <= plain['hits'][1e-2][0], (defl['hits'], plain['hits'])
    # exact generalized eigen-space of dimension 'all kept' deflates to a (near) one-shot solve
    Vall, _ = TS.spectral_subspace(D, int(D['keep'].sum()), 'smallest'); Wa = It._embed(idx, Vall)
    full = TS.run_cg(It, D, It.g, It.dinvJ, W=Wa, floor=0.0, safety=216, rhos=(1e-6,)); assert full['hits'][1e-6][0] <= 2

def test_transport_identity_and_nested_d2():
    P, th0 = setup(); Ip, It, Ft = _state(P, th0)
    # identity (LS-ratio floor ~1e-8 from cancellation in ZtHZ - 2Zt rhs + |Y|^2): same state, same eta -> LS transport of U is U itself when U is H-orthogonal to nothing lost (exact solve of H Z = H U gives Z = U on range(H))
    D = It.dense(); idx = D['idx']; Vs, _ = TS.spectral_subspace(D, 6, 'smallest'); U = It._embed(idx, Vs)
    rhs, Y2 = TS.transport_rhs(It, It, U); w = [0.0]; Z, lsr = TS.transport_cg(It, U, rhs, 5, Y2, w, It.dinvJ)
    assert lsr < 1e-6, lsr; assert np.abs(Z - U).max() < 1e-8 * max(np.abs(U).max(), 1e-12)
    D2 = TS.study_state(It, D, Ip, Ip.dense(), Ft, k=8, n_trs=(0, 3), rs=(2,), safety=216)
    if not D2['skipped']:
        a = D2['arms']['D2']; b = D2['arms']['D3p_n3']; assert a['k'] >= 1 and b['k'] >= 1

def test_n_tr_zero_equals_d2_bitwise():
    P, th0 = setup(); Ip, It, Ft = _state(P, th0); D = It.dense(); Dp = Ip.dense()
    R = TS.study_state(It, D, Ip, Dp, Ft, k=8, n_trs=(0, 3), rs=(2,), safety=216)
    if not R['skipped']:
        a = R['arms']['D2']; assert a['ls_ratio'] is None
        # D3p with n_tr=0 is the same code path (name D2): rerun explicitly and compare hits
        R2 = TS.study_state(It, D, Ip, Dp, Ft, k=8, n_trs=(0,), rs=(2,), safety=216); assert R2['arms']['D2']['hits'] == a['hits'] and R2['arms']['D2']['Wtot'] == a['Wtot']

def test_block_jacobi_matches_dense_blocks():
    P, th0 = setup(); Ip, It, Ft = _state(P, th0); D = It.dense(); w = [0.0]; M = TC.block_jacobi(It, w)
    idx = D['idx']; H = D['H']; pos = -np.ones(It.p, int); pos[idx] = np.arange(len(idx))
    # block (Gaussian 0): the block of H restricted to its six coordinates must be inverted by the preconditioner; but H has the full coupling, so compare against the Gram blocks AJ^T AJ/sn^2 + c J^T J
    AJ, Jd = It.AJ_cols(idx)
    for k in (0, 5):
        cols = pos[6 * k:6 * k + 6]; ok = cols >= 0; c = cols[ok]
        B = AJ[:, c].T @ AJ[:, c] / It.sn ** 2 + It.c * (Jd[:, c].T @ Jd[:, c]); v = np.zeros(It.p); v[6 * k:6 * k + 6][ok] = 1.0
        r = np.zeros(It.p); r[6 * k:6 * k + 6][ok] = B @ np.ones(ok.sum()); out = M(r)[6 * k:6 * k + 6][ok]
        assert np.allclose(out, 1.0, rtol=1e-4, atol=1e-6), out
    assert w[0] > It.p * 0.9 * (4.0 * N ** 3)                                                         # strict build cost includes p A-applications

def test_closed_loop_smoke_all_baselines():
    P, th0 = setup(); ref = GC.solve('TRN', P, th0, dict(kappa0=1e-2, f=3, eps_r=1e-2, maxcg=300, inner='J'), max_iter=12)
    for cfg in (dict(inner='J'), dict(inner='J', warm=True), dict(inner='BJ')):
        o = GC.solve('TRN', P, th0, dict(kappa0=1e-2, f=3, eps_r=1e-2, maxcg=300, **cfg), max_iter=12)
        assert np.isfinite(o['F']) and o['F'] < o['traj'][0][1], cfg
        s = TL.summarize(o, ref['F']); assert 0 <= s['f_iter'] <= 1 and 0 <= s['f_asm'] <= 1 and s['f_iter'] + s['f_asm'] <= 1.0 + 1e-9

def test_closed_loop_log_states_and_kappa():
    P, th0 = setup(); log, o = closed_log(P, th0, n=10)
    assert len(log) >= 4 and all(r['kap_acc'] > 0 and r['th'].shape == (K, 6) and r['d'].shape == (6 * K,) and r['F'] > 0 for r in log)
    k0 = 1e-2; assert all(abs(np.log(r['kap_acc'] / k0) / np.log(3) - round(np.log(r['kap_acc'] / k0) / np.log(3))) < 1e-6 for r in log), 'accepted kappa must lie on the kappa0*3^j lattice of the frozen rule'
    assert all(log[i]['F'] >= log[i + 1]['F'] for i in range(len(log) - 1)), 'F at the START of accepted steps must be non-increasing'

def test_d0w_cost_counted_once():
    P, th0 = setup(); Ip, It, Ft = _state(P, th0); D = It.dense(); p = It.p
    a = TS.run_cg(It, D, It.g, It.dinvJ, floor=0.0, safety=216, rhos=(0.1,)); b = TS.run_cg(It, D, It.g, It.dinvJ, x0=np.zeros(p), floor=0.0, safety=216, rhos=(0.1,))
    assert a['Wtot'] == b['Wtot'] and a['hits'] == b['hits'], 'D0w with x0=0 must cost exactly D0'
    c = TS.run_cg(It, D, It.g, It.dinvJ, x0=0.5 * D['dstar'], floor=0.0, safety=1, rhos=(0.1,)); assert abs(c['Wtot'] - (2 * It.wH + 8.0 * p)) < 1.0, c['Wtot'] - 2 * It.wH     # H x0 charged once + exactly one CG iteration (wH + 8p)

def test_transport_rhs_cost_formula():
    import geo_flops as FL
    P, th0 = setup(); Ip, It, Ft = _state(P, th0); k = 5
    assert abs(TS.transport_wcost_rhs(It, Ip, k) - k * (FL.F_matvec(Ip.nnz) + 2 * FL.F_A(N) + FL.F_matvec(It.nnz))) < 1e-6

def test_d46_arms_and_no_ref_states():
    P, th0 = setup(); Ip, It, Ft = _state(P, th0); R = TS.study_state(It, It.dense(), Ip, Ip.dense(), Ft, k=8, n_trs=(0, 3), rs=(2,), safety=216)
    assert not hasattr(TS, 'ref_states'), 'same-state code must not carry the GEO state source'
    if not R['skipped']: assert 'D46_r2' in R['arms'] and 'D6_r2' in R['arms'] and 'D5_r2' in R['arms']

def test_static_no_gate_bypass():
    import re
    here = os.path.dirname(os.path.abspath(__file__)); bad = re.compile(r'\b(clean_image_trn|_tile|rng_of)\b')
    for f in ('src/trn_core.py', 'src/trn_loop.py', 'src/trn_study.py', 'src/trn_flops.py'): assert not bad.search(open(os.path.join(here, '..', f)).read()), 'method/oracle-side module touches the data generator: ' + f
    for f in ('experiments/trn_s0.py', 'experiments/trn_same_state.py', 'experiments/trn_same_state_reduce.py'):
        t = open(os.path.join(here, '..', f)).read(); assert not re.search(r'\b(_tile|rng_of)\b', t), 'analyzer bypasses the gate via _tile/rng_of: ' + f

if __name__ == '__main__':
    fns = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    for f in fns:
        f(); print('PASS', f.__name__)
    print('ALL PASS', len(fns))
