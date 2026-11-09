"""JR unit tests (contract JR candidate v0, section 10). Run: python3 tests/test_jr_core.py   (N=32, K=36; design-smoke image 590 only; never prints image values; no confirm access)."""
import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import numpy as np
import geo_core as GC, jr_op, jr_gen, jr_core as JC

N, K = 32, 36
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')


def setup(cond='G15', img=590):
    op = jr_gen.make_op(cond, N); x = jr_gen.clean_image_jr(img, N); y = jr_gen.noisy_obs_jr(op, x, jr_gen.SN, 9501, img, cond)
    P = JC.JProb(N, op, y, jr_gen.SN, 1e-3 / jr_gen.SN ** 2); return P, GC.grid_init(P, K)


def test_sparse_A_equals_B_kron_B():
    sb = 1.5; B = GC.refl_B(N, sb); A_dense = np.kron(B, B); op = jr_op.SOp(N, jr_op.psf_taps('gauss', s=sb))
    assert np.abs(op.A.toarray() - A_dense).max() < 1e-12
    X = np.random.default_rng(1).standard_normal((N, N)); assert np.abs(op.apply(X) - GC.Op(N, sb).apply(X)).max() < 1e-12
    Y = np.random.default_rng(2).standard_normal((N, N)); assert abs(float(np.sum(op.apply(X) * Y)) - float(np.sum(X * op.adj(Y)))) < 1e-9, 'adjoint != transpose'
    for kind, kw in (('agauss', dict(smaj=3.0, smin=1.0, th=30.0)), ('motion', dict(L=11.0, th=30.0)), ('disk', dict(r=3.0))):
        t = jr_op.psf_taps(kind, **kw); assert abs(t.sum() - 1) < 1e-12 and t.min() >= 0
        o = jr_op.SOp(N, t); assert abs(o.apply(np.ones((N, N))) - 1).max() < 1e-12, 'blur must preserve constants (reflect boundary)'


def test_incremental_forward_equals_full_forward():
    for cond, mode in (('G15', 'joint'), ('MO', 'ind_lp')):
        P, th0 = setup(cond); worst = [0.0]; orig = JC._visit; cnt_v = [0]

        def wrapped(P_, S, J, AJ, members, cfg, cnt, T, vlog):
            ok = orig(P_, S, J, AJ, members, cfg, cnt, T, vlog); F, x, r = P_.F_of(S['th']); cnt_v[0] += 1
            worst[0] = max(worst[0], abs(F - S['F']) / abs(F), float(np.abs(r - S['r']).max()), float(np.abs(x - S['x']).max())); return ok
        JC._visit = wrapped
        try: JC.jr_solve(P, th0, dict(kappa0=0.1, f=3, gs=4, seed=0, arm='OBS', mode=mode), max_sweeps=4)
        finally: JC._visit = orig
        assert cnt_v[0] > 0 and worst[0] < 1e-9, 'incremental state differs from full re-render (%s): %g' % (cond, worst[0])


def test_ind1_first_sweep_equals_geo_core_blk():
    P, th0 = setup('G15'); a = GC.solve('BLK', P, th0, dict(kappa0=0.1, f=3), max_iter=1)
    b = JC.jr_solve(P, th0, dict(kappa0=0.1, f=3, gs=1, seed=0, arm='IND1', mode='joint'), max_sweeps=1)
    assert np.abs(a['theta'] - b['theta']).max() < 1e-9 and abs(a['F'] - b['F']) < 1e-8 * abs(a['F']), 'IND1 sweep != geo_core BLK sweep'


def test_affinity_invariant_to_parameter_unit_rescaling():
    P, th = setup('AG'); th = th.copy(); th[:, 3:] += 0.1 * np.random.default_rng(0).standard_normal((K, 3))
    J = GC.render_jac(th, N)[1]; AJ = P.op.apply_stack(J).reshape(6 * K, -1).T; cs = np.exp(np.random.default_rng(3).uniform(-2, 2, size=6)); cs[0] = 1.0   # weight coordinate fixed (x_k normalisation uses it)
    c = np.tile(cs, K); J2 = (J.reshape(6 * K, N, N) / c[:, None, None]); AJ2 = AJ / c[None, :]
    R1 = AJ * JC.calib_scales(th, J)[None, :] / P.sn; R2 = AJ2 * JC.calib_scales(th, J2)[None, :] / P.sn
    assert np.abs(R1 - R2).max() < 1e-8 * np.abs(R1).max(), 'calibrated response not unit-free'
    pi, pj, _, _ = JC.candidate_pairs(th, N, P.op.rp); assert np.abs(JC.coupling_matrix(R1, K, pi, pj) - JC.coupling_matrix(R2, K, pi, pj)).max() < 1e-8


def test_non_candidate_pairs_have_zero_coupling_and_negligible_true_coupling():
    P, th0 = setup('G15'); K4 = 4; th = np.array([[1.0, 5, 5, np.log(1.0), 0, np.log(1.0)], [1.0, 9, 5, np.log(1.0), 0, np.log(1.0)], [1.0, 27, 27, np.log(1.0), 0, np.log(1.0)], [1.0, 26, 22, np.log(1.0), 0, np.log(1.0)]])
    pi, pj, inter, box = JC.candidate_pairs(th, N, P.op.rp); cand = set(zip(pi.tolist(), pj.tolist())); assert (0, 2) not in cand and (0, 1) in cand and (2, 3) in cand
    J = GC.render_jac(th, N)[1]; AJ = P.op.apply_stack(J).reshape(6 * K4, -1).T; R = AJ * JC.calib_scales(th, J)[None, :] / P.sn
    full = JC.coupling_matrix(R, K4, *np.triu_indices(K4, 1)); sparse = JC.coupling_matrix(R, K4, pi, pj)
    nonc = [(k, l) for k, l in zip(*np.triu_indices(K4, 1)) if (int(k), int(l)) not in cand]; assert (0, 2) in nonc and len(nonc) >= 2
    for (k, l) in nonc: assert sparse[k, l] == 0.0 and full[k, l] < 1e-3, 'non-candidate pair has true coupling %g' % full[k, l]


def test_cost_counters_consistent_with_operator_calls():
    P, th0 = setup('DK'); calls = [0]; oa, os_ = P.op.apply, P.op.apply_stack
    P.op.apply = lambda X: (calls.__setitem__(0, calls[0] + 1), oa(X))[1]
    P.op.apply_stack = lambda Xs: (calls.__setitem__(0, calls[0] + Xs.shape[0]), os_(Xs))[1]
    out = JC.jr_solve(P, th0, dict(kappa0=0.1, f=3, gs=4, seed=0, arm='OBS', mode='joint'), max_sweeps=3)
    assert abs(sum(out['cnt']['cat'].values()) - out['cnt']['W']) < 1e-6 * out['cnt']['W'], 'categories do not sum to W'
    assert out['cnt']['cat']['grp'] > 0 and out['cnt']['A'] == calls[0], 'A-application count %d != actual calls %d' % (out['cnt']['A'], calls[0])
    cs = []
    for arm in ('SPA', 'RND', 'IND1'):
        o = JC.jr_solve(P, th0, dict(kappa0=0.1, f=3, gs=4, seed=0, arm=arm, mode='joint'), max_sweeps=3); cs.append(o['cnt']['cat']['grp'])
    assert cs[2] == 0.0 and 0 < cs[0] < 0.1 * out['cnt']['cat']['grp'] and 0 < cs[1] < 0.1 * out['cnt']['cat']['grp']


def test_method_side_never_imports_evaluator_side():
    for fn in ('jr_core.py', 'jr_op.py'):
        src = open(os.path.join(SRC, fn), encoding='utf-8').read(); code = '\n'.join(l.split('#')[0] for l in src.splitlines())
        assert not re.search(r'^\s*(import|from)\s+(jr_gen|as_gen|geo_gen|trn_gen)\b', code, re.M), fn + ' imports an evaluator/data module'
        assert 'clean_image' not in code and 'noisy_obs' not in code, fn + ' references clean-image/noise generators'


def test_data_gates():
    for i in (501, 506, 590, 592):
        jr_gen.clean_image_jr(i, N)
    os.environ.pop('JR_VERIFY_UNLOCK', None); os.environ.pop('JR_VERIFY2_UNLOCK', None)
    for i in (1, 24, 41, 101, 201, 301, 321, 344, 351, 401, 424, 531, 578, 589, 593, 601, 624, 700, 713, 511, 522, 701, 712):     # sealed/old/unknown indices must be refused WITHOUT synthesising an image
        try: jr_gen.clean_image_jr(i, N); raise RuntimeError('index %d accepted' % i)
        except AssertionError: pass


def test_sealed_gate_logic_with_dummy_record_and_files():
    """Pure gate logic on a temporary record/analyzer/module (no VERIFY image is generated)."""
    import tempfile, hashlib
    d = tempfile.mkdtemp(); rec = os.path.join(d, 'REC.txt'); main = os.path.join(d, 'an.py'); mod = os.path.join(d, 'jr_x.py'); open(main, 'w').write('x=1\n'); open(mod, 'w').write('y=2\n')
    sh = lambda f: hashlib.sha256(open(f, 'rb').read()).hexdigest(); env = {'JR_VERIFY_UNLOCK': '1'}; kw = dict(rec_path=rec, environ=env, main_file=main, module_files=[mod], now='T')
    def refused(**o):
        jr_gen._SESSION.clear()
        try: jr_gen._sealed_gate('VERIFY', **{**kw, **o}); return False
        except AssertionError: return True
    assert refused(rec_path=os.path.join(d, 'none.txt')), 'no record'
    open(rec, 'w').write('TUNE_DONE x\n'); assert refused(), 'no UNSEALED line'
    open(rec, 'w').write('VERIFY_UNSEALED x\n'); assert refused(), 'no TUNE_DONE line'
    open(rec, 'w').write('TUNE_DONE x\nVERIFY_UNSEALED x\n'); assert refused(), 'analyzer sha not registered'
    open(rec, 'a').write('ANALYZER_SHA256 %s an.py\n' % sh(main)); assert refused(), 'module sha not registered'
    open(rec, 'a').write('MODULE_SHA256 %s jr_x.py\n' % sh(mod)); assert refused(environ={}), 'env missing'
    open(mod, 'w').write('y=3\n'); assert refused(), 'modified module must be refused'; open(mod, 'w').write('y=2\n')
    jr_gen._SESSION.clear(); jr_gen._sealed_gate('VERIFY', **kw); assert 'VERIFY_CONSUMED' in open(rec).read(), 'consumption not recorded'
    jr_gen._sealed_gate('VERIFY', **kw)                       # same session (forked worker): allowed, no second consume line
    assert open(rec).read().count('VERIFY_CONSUMED') == 1
    assert refused(), 'second process must be refused after consumption'
    open(rec, 'a').write('VERIFY_RESUME_OK T crash-recovery\n'); jr_gen._SESSION.clear(); jr_gen._sealed_gate('VERIFY', **kw); assert open(rec).read().count('VERIFY_CONSUMED') == 2
    assert refused(), 'consumed again, resume needed again'
    jr_gen._SESSION.clear()


def test_ovl_affinity_is_unwhitened_overlap_area_and_cost_charged():
    P, th0 = setup('AG'); J = GC.render_jac(th0, N)[1]; AJ = P.op.apply_stack(J).reshape(6 * K, -1).T; cnt = dict(A=0, W=0.0, cat={c: 0.0 for c in JC.CATS})
    g, _ = JC.make_groups(P, th0, J, AJ, dict(arm='OVL', gs=4), cnt); assert sorted(k for x in g for k in x) == list(range(K)) and max(len(x) for x in g) <= 4 and cnt['cat']['grp'] > 0
    th = th0.copy(); th[:, 0] *= 7.0 ; g2, _ = JC.make_groups(P, th, J, AJ, dict(arm='OVL', gs=4), dict(A=0, W=0.0, cat={c: 0.0 for c in JC.CATS})); assert g == g2, 'OVL must not depend on amplitudes / responses'
    th3 = th0.copy(); th3[0, 1] += 6.0; g3, _ = JC.make_groups(P, th3, J, AJ, dict(arm='OVL', gs=4), dict(A=0, W=0.0, cat={c: 0.0 for c in JC.CATS})); assert sorted(k for x in g3 for k in x) == list(range(K))


def test_regroup_interval_charges_grouping_only_on_rebuild_sweeps():
    P, th0 = setup('G15'); o = JC.jr_solve(P, th0, dict(kappa0=0.1, f=3, gs=4, seed=0, arm='OBS', mode='joint', R=4), max_sweeps=9); gcum = [t[5] for t in o['traj']]
    inc = np.diff(gcum); assert o['stop'] == 'max_sweeps', o['stop']
    rebuilt = [i for i, v in enumerate(inc, start=1) if v > 0]; assert rebuilt == [1, 5, 9], rebuilt
    o1 = JC.jr_solve(P, th0, dict(kappa0=0.1, f=3, gs=4, seed=0, arm='OBS', mode='joint', R=1), max_sweeps=9); assert np.all(np.diff([t[5] for t in o1['traj']]) > 0)
    assert abs(sum(o['cnt']['cat'].values()) - o['cnt']['W']) < 1e-6 * o['cnt']['W']
    reused = [s for s in o['sweeps'] if s['info'].get('reused')]; assert len(reused) == 6 and all(s['sizes'] for s in reused)


def test_obs_equals_obs0_when_operator_is_identity():
    op = jr_op.SOp(N, np.ones((1, 1))); assert abs(op.A - __import__('scipy.sparse', fromlist=['identity']).identity(N * N)).max() < 1e-15
    x = jr_gen.clean_image_jr(590, N); y = x + 0.02 * np.random.default_rng(0).standard_normal((N, N)); P = JC.JProb(N, op, y, 0.02, 1e-3 / 0.02 ** 2); th = GC.grid_init(P, K)
    J = GC.render_jac(th, N)[1]; AJ = P.op.apply_stack(J).reshape(6 * K, -1).T; d = JC.calib_scales(th, J); pi, pj, _, _ = JC.candidate_pairs(th, N, P.op.rp)
    a1 = JC.coupling_matrix(AJ * d[None, :] / P.sn, K, pi, pj); a0 = JC.coupling_matrix(J.reshape(6 * K, -1).T * d[None, :] / P.sn, K, pi, pj)
    assert np.abs(a1 - a0).max() < 1e-12


def test_groups_are_partitions_with_size_cap():
    P, th0 = setup('AG'); J = GC.render_jac(th0, N)[1]; AJ = P.op.apply_stack(J).reshape(6 * K, -1).T
    for arm in ('OBS', 'OBS0', 'SPA', 'RND', 'OVL'):
        for gs in (2, 4, 9):
            cnt = dict(A=0, W=0.0, cat={c: 0.0 for c in JC.CATS}); g, _ = JC.make_groups(P, th0, J, AJ, dict(arm=arm, gs=gs), cnt, rng_seed=0)
            flat = sorted(k for grp in g for k in grp); assert flat == list(range(K)) and max(len(x) for x in g) <= gs
            g2, _ = JC.make_groups(P, th0, J, AJ, dict(arm=arm, gs=gs), dict(A=0, W=0.0, cat={c: 0.0 for c in JC.CATS}), rng_seed=0); assert g == g2, 'grouping not deterministic'


if __name__ == '__main__':
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            try: fn(); print('PASS', name)
            except Exception as e: fails += 1; print('FAIL', name, '->', repr(e)[:300])
    print('%d failures' % fails); sys.exit(1 if fails else 0)
