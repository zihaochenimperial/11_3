"""GEO phase-V unit tests (contract v2 Sec.6, V1-V7). Run: pytest tests/test_geo_core.py"""
import os, sys, re, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'src'))
import as_core as C, geo_core as GC, geo_gen as GG

N = 32
ARMS = ('GEO', 'LMD', 'LSMR', 'PCG8P', 'PCG8D', 'BJ', 'BLK')
CFG = dict(kappa0=1e-3, f=10)


def _rand_theta(K, seed):
    rng = np.random.default_rng(seed); th = np.zeros((K, 6))
    th[:, 0] = rng.uniform(0.2, 1.0, K); th[:, 1:3] = rng.uniform(2, N - 2, (K, 2))
    th[:, 3] = rng.uniform(np.log(1.2), np.log(3.5), K); th[:, 5] = rng.uniform(np.log(1.2), np.log(3.5), K); th[:, 4] = rng.uniform(-0.6, 0.6, K)
    return th


def _well_theta():
    th = np.array([[0.8, 8, 8, np.log(2.5), 0.0, np.log(2.5)], [0.6, 24, 8, np.log(2.5), 0.1, np.log(2.0)],
                   [0.7, 8, 24, np.log(2.0), -0.1, np.log(2.5)], [0.9, 24, 24, np.log(2.5), 0.0, np.log(2.5)]], float)
    return th


def _prob(sb=1.0, sn=0.01, lam=1e-3, seed=5, th_true=None):
    rng = np.random.default_rng(seed)
    x_true = GC.render(th_true, N) if th_true is not None else rng.uniform(0, 1, (N, N))
    P = GC.Prob(N, sb, None, sn, lam / sn ** 2); P.y = P.op.apply(x_true) + sn * rng.standard_normal((N, N))
    return P


# ---------------------------------------------------------------- V1
def test_V1_render_jac_matches_as_core():
    th = _rand_theta(9, 1)
    x_new, J_new = GC.render_jac(th, N); x_old, J_old = C.render_jac(th)
    assert np.max(np.abs(x_new - x_old)) < 1e-12 and np.max(np.abs(J_new - J_old)) < 1e-12
    assert np.max(np.abs(GC.render(th, N) - C.render(th))) < 1e-12
    A_new = GC.Op(N, 1.0); A_old = C.Op(1.0); X = np.random.default_rng(2).standard_normal((N, N))
    assert np.max(np.abs(A_new.apply(X) - A_old.apply(X))) < 1e-13 and np.max(np.abs(A_new.adj(X) - A_old.adj(X))) < 1e-13
    assert 0.5 < A_new.normA <= 1.0 + 1e-12


def test_V1_finite_difference_jacobian():
    th = _rand_theta(4, 3); _, J = GC.render_jac(th, N); h = 1e-6
    for k in range(4):
        for j in range(6):
            t1 = th.copy(); t1[k, j] += h; t2 = th.copy(); t2[k, j] -= h
            fd = (GC.render(t1, N) - GC.render(t2, N)) / (2 * h)
            assert np.max(np.abs(fd - J[6 * k + j])) <= 1e-6 * max(1.0, np.max(np.abs(J[6 * k + j])))


def test_V1_sparse_truncated_consistent():
    th = _rand_theta(9, 7); xs, Jc = GC.render_jac_sparse(th, N, rad=4.0); xd, Jd = GC.render_jac(th, N)
    assert np.max(np.abs(xs - GC.render_trunc(th, N))) < 1e-12
    g, e, z1, z2, L11, L22, l21 = GC._parts(th, N); mask = (z1 * z1 + z2 * z2 <= 16.0)            # (K,N,N)
    Jmask = Jd.reshape(th.shape[0], 6, N, N) * mask[:, None]
    Jdense = Jc.toarray().T.reshape(th.shape[0], 6, N, N)
    assert np.max(np.abs(Jdense - Jmask)) < 1e-12                                                 # exactly the dense J masked to Mahalanobis radius 4
    assert np.max(np.abs(xs - (g * mask).sum(0))) < 1e-12
    print('descriptive: max |J_trunc - J_dense| =', float(np.max(np.abs(Jdense - Jd.reshape(th.shape[0], 6, N, N)))), ' max |x_trunc - x_dense| =', float(np.max(np.abs(xs - xd))))


# ---------------------------------------------------------------- V2
def _geo_step(P, th, kappa):
    x, Jimg = GC.render_jac(th, N); p = Jimg.shape[0]; m = N * N; sn, a = P.sn, P.a
    AJ = P.op.apply_stack(Jimg).reshape(p, m).T; r = P.y - P.op.apply(x)
    U, s, Vt = np.linalg.svd(Jimg.reshape(p, m).T, full_matrices=False); rho = int(np.sum(s > GC.RCOND * s[0]))
    Ur, sr, Vr = U[:, :rho], s[:rho], Vt[:rho].T; B = (AJ @ Vr / sr) / sn
    z = np.linalg.solve(B.T @ B + (a + kappa * P.LamA) * np.eye(rho), B.T @ (r.ravel() / sn) - a * (Ur.T @ x.ravel()))
    return Vr @ (z / sr), Ur @ z, (Jimg, AJ, r, x, Vr, rho, s)


def _dense_ref(P, th, kappa, info):
    """Parameter-space reference: P restricted to the retained right-singular subspace (same rcond), solved densely; plus the full pseudo-inverse solution."""
    Jimg, AJ, r, x, Vr, rho, s = info; p = Jimg.shape[0]; Jm = Jimg.reshape(p, -1).T; sn, a = P.sn, P.a
    Hm = AJ.T @ AJ / sn ** 2 + (a + kappa * P.LamA) * (Jm.T @ Jm); g = AJ.T @ r.ravel() / sn ** 2 - a * (Jm.T @ x.ravel())
    w = np.linalg.solve(Vr.T @ Hm @ Vr, Vr.T @ g); d_sub = Vr @ w
    d_pinv = np.linalg.pinv(Hm, rcond=1e-12, hermitian=True) @ g
    return d_sub, d_pinv, Jm


def test_V2_geo_step_equals_dense_reference():
    worst_par = 0.0
    for seed in range(8):
        for (sb, sn) in ((1.0, 0.01), (2.0, 0.03)):
            th = _rand_theta(9, 10 + seed); P = _prob(sb, sn, 1e-3, seed=seed)
            d_geo, jv_geo, info = _geo_step(P, th, 1e-3); d_sub, d_pinv, Jm = _dense_ref(P, th, 1e-3, info)
            assert np.linalg.norm(jv_geo - Jm @ d_sub) <= 1e-6 * max(np.linalg.norm(jv_geo), 1e-12)
            assert np.linalg.norm(d_geo - d_sub) <= 1e-5 * max(np.linalg.norm(d_sub), 1e-12)
            worst_par = max(worst_par, np.linalg.norm(d_geo - d_pinv) / max(np.linalg.norm(d_pinv), 1e-12))
    print('descriptive: worst relative parameter-step difference GEO vs full pinv(rcond 1e-12) =', worst_par)


def test_V2_rank_deficient_J():
    th = _rand_theta(9, 40); th[1] = th[0].copy(); th[1, 0] = 0.5
    P = _prob(); d_geo, jv_geo, info = _geo_step(P, th, 1e-3); d_sub, _, Jm = _dense_ref(P, th, 1e-3, info)
    assert np.linalg.norm(jv_geo - Jm @ d_sub) <= 1e-6 * max(np.linalg.norm(jv_geo), 1e-12)


def test_V2_lsmr_matches_on_well_conditioned():
    th = _well_theta(); P = _prob(th_true=th, seed=3); d_geo, jv_geo, info = _geo_step(P, th, 1e-3)
    s = info[6]; assert s[0] / s[-1] <= 1e5
    S = dict(th=th, x=info[3], r=info[2], F=P.F_of(th)[0], kappa=1e-3, rej=0, rank=None, trials=0, clamped=0, clamp_trials=0, diag=[], itn=[], alpha=[], act=[])
    cnt = dict(A=0, J=0, mv=0, W=0.0, Ad=0, Wd=0.0); T = dict(jac=0., aj=0., solve=0., back=0.)
    captured = {}
    orig = GC._accept
    def spy(P_, S_, th2raw, Jmul, cnt_, T_, **kw):
        captured['d'] = th2raw - S_['th']; captured['Jmul'] = Jmul; return orig(P_, S_, th2raw, Jmul, cnt_, T_, **kw)
    GC._accept = spy
    try:
        GC._iter_lsmr(P, S, dict(kappa0=1e-3, f=10, atol=1e-12, btol=1e-12), cnt, T)
    finally:
        GC._accept = orig
    jv = captured['Jmul'](captured['d'].ravel())
    assert np.linalg.norm(jv - jv_geo) <= 1e-4 * np.linalg.norm(jv_geo)


# ---------------------------------------------------------------- V3
def test_V3_F_independent_and_monotone():
    th = _rand_theta(9, 60); P = _prob()
    F, x, r = P.F_of(th); sn, a = P.sn, P.a
    F_alt = 0.5 * np.sum(((P.y.ravel() - np.kron(P.op.B, P.op.B) @ x.ravel()) / sn) ** 2) + 0.5 * a * np.sum(x ** 2)
    assert abs(F - F_alt) <= 1e-10 * abs(F)
    for name in ARMS:
        res = GC.solve(name, P, GC.grid_init(P, 9), CFG, max_iter=12)
        Fs = [t[1] for t in res['traj']]
        assert all(Fs[i + 1] <= Fs[i] for i in range(len(Fs) - 1)), name
        assert Fs[-1] < Fs[0], name


def test_V3_clamped_step_uses_clamped_model():
    th0 = np.array([[0.8, N + 3.9, 16, np.log(2.5), 0.0, np.log(2.5)], [0.7, 12, 12, np.log(2.5), 0.0, np.log(2.5)],
                    [0.6, 20, 20, np.log(2.5), 0.0, np.log(2.5)], [0.5, 6, 25, np.log(2.5), 0.0, np.log(2.5)]], float)
    P = _prob(th_true=_well_theta(), seed=4)
    for name in ('GEO', 'LMD', 'BJ'):
        res = GC.solve(name, P, th0, CFG, max_iter=15)
        Fs = [t[1] for t in res['traj']]
        assert all(Fs[i + 1] <= Fs[i] for i in range(len(Fs) - 1)), name
        assert 0.0 <= res['clamp_rate'] <= 1.0 and res['trials'] > 0
    # direct check of the acceptance arithmetic on a step that hits the box: pred must be evaluated at the clamped step
    S = dict(th=GC.clamp(th0, N), x=None, r=None, F=None, rej=0, trials=0, clamped=0, clamp_trials=0)
    F, x, r = P.F_of(S['th']); S.update(x=x, r=r, F=F)
    _, Jimg = GC.render_jac(S['th'], N); Jm = Jimg.reshape(Jimg.shape[0], -1).T
    big = np.zeros_like(th0); big[0, 1] = 50.0                    # pushes mx far beyond N+4
    cnt = dict(A=0, J=0, mv=0, W=0.0, Ad=0, Wd=0.0); T = dict(jac=0., aj=0., solve=0., back=0.)
    ok, ratio, th2, x2, r2, F2 = GC._accept(P, S, S['th'] + big, lambda d: Jm @ d, cnt, T)
    assert abs(th2[0, 1] - (N + 4)) < 1e-12 and S['clamped'] >= 1


# ---------------------------------------------------------------- V4
def test_V4_first_order_optimality_small_well_posed():
    th_true = _well_theta(); P = _prob(sb=1.0, sn=0.01, lam=1e-3, seed=9, th_true=th_true)
    th0 = th_true + np.random.default_rng(1).normal(0, 0.15, th_true.shape)
    res = GC.solve('GEO', P, GC.clamp(th0, N), dict(kappa0=1e-3, f=3), max_iter=300)
    th = res['theta']; x, Jimg = GC.render_jac(th, N); p = Jimg.shape[0]; Jm = Jimg.reshape(p, -1).T
    AJ = P.op.apply_stack(Jimg).reshape(p, -1).T; r = P.y - P.op.apply(x)
    grad = -(AJ.T @ r.ravel()) / P.sn ** 2 + P.a * (Jm.T @ x.ravel())
    _, Jimg0 = GC.render_jac(GC.clamp(th0, N), N); x0 = GC.render(GC.clamp(th0, N), N); r0 = P.y - P.op.apply(x0); p0 = Jimg0.shape[0]
    Jm0 = Jimg0.reshape(p0, -1).T; AJ0 = P.op.apply_stack(Jimg0).reshape(p0, -1).T
    grad0 = -(AJ0.T @ r0.ravel()) / P.sn ** 2 + P.a * (Jm0.T @ x0.ravel())
    free = np.ones(p, bool)
    for k in range(th.shape[0]):
        for j, lo, hi in ((3, GC.LMIN, GC.LMAX), (5, GC.LMIN, GC.LMAX), (1, -4, N + 4), (2, -4, N + 4), (4, -12, 12)):
            if abs(th[k, j] - lo) < 1e-9 or abs(th[k, j] - hi) < 1e-9: free[6 * k + j] = False
    rel = np.linalg.norm(grad[free]) / np.linalg.norm(grad0)
    print('V4 relative projected gradient =', rel, 'stop=', res['stop'], 'iters=', len(res['traj']) - 1)
    assert rel <= 1e-6


# ---------------------------------------------------------------- V5
def test_V5_method_side_source_scan_and_seeds():
    src = open(os.path.join(os.path.dirname(HERE), 'src', 'geo_core.py'), encoding='utf-8').read()
    assert not re.search(r'geo_gen|clean_image|x_true|ladder_target|as_gen|noisy_obs', src)
    assert set(GG.DEV_IMGS).isdisjoint(GG.SEALED_OR_USED) and set(GG.TEST_IMGS).isdisjoint(GG.SEALED_OR_USED) and set(GG.DEV_IMGS).isdisjoint(GG.TEST_IMGS)
    keys = GG.seed_keys(); assert len(keys) == len(set(keys))
    assert set(k[1] for k in keys if k[0] == 1).issubset({9101, 9201, 9202})
    for i in (1, 24, 41, 58, 100, 113, 200, 225):
        try: GG.clean_image_geo(i); assert False, i
        except AssertionError as e: assert 'not allowed' in str(e)
    from collections import Counter
    fam = Counter(GG.family_geo(i) for i in GG.DEV_IMGS); assert set(fam.values()) == {4}
    fam = Counter(GG.family_geo(i) for i in GG.TEST_IMGS); assert set(fam.values()) == {8}


# ---------------------------------------------------------------- V6
def test_V6_reproducible():
    P = _prob(); th0 = GC.grid_init(P, 9)
    for name in ARMS:
        a = GC.solve(name, P, th0, CFG, max_iter=6); b = GC.solve(name, P, th0, CFG, max_iter=6)
        assert np.array_equal(a['theta'], b['theta']) and [t[1] for t in a['traj']] == [t[1] for t in b['traj']], name


# ---------------------------------------------------------------- V7
def test_V7_K1_bj_blk_equal_geo():
    """A5.3: K=1. BJ with alpha forced to 1 and BLK equal GEO exactly; BJ with alpha* equals GEO's step scaled by alpha* (no clamp active), alpha* logged."""
    th0 = np.array([[0.8, 15.0, 17.0, np.log(3.0), 0.1, np.log(2.5)]]); P = _prob(th_true=np.array([[0.9, 16.0, 16.0, np.log(3.2), 0.0, np.log(2.8)]]), seed=2)
    r = {n: GC.solve(n, P, th0, CFG, max_iter=1) for n in ('GEO', 'BJ', 'BLK')}
    assert np.max(np.abs(r['BLK']['theta'] - r['GEO']['theta'])) <= 1e-8
    r1 = GC.solve('BJ', P, th0, dict(CFG, alpha_one=True), max_iter=1)
    assert np.max(np.abs(r1['theta'] - r['GEO']['theta'])) <= 1e-8
    # alpha*: unrelaxed block step du == GEO step; relaxed BJ step = alpha* du
    S = dict(th=GC.clamp(th0, N), x=None, r=None, F=None, kappa=CFG['kappa0'], rej=0, rank=None, trials=0, clamped=0, clamp_trials=0, diag=[], itn=[], alpha=[], act=[])
    F, x, rr = P.F_of(S['th']); S.update(x=x, r=rr, F=F)
    cnt = dict(A=0, J=0, mv=0, W=0.0, Ad=0, Wd=0.0); T = dict(jac=0., aj=0., solve=0., back=0.)
    ok = GC._iter_bj(P, S, CFG, cnt, T)
    al = S['alpha'][0]; assert al > 0
    d_bj = (S['th'] - GC.clamp(th0, N)) if ok else None
    d_geo = r['GEO']['theta'] - GC.clamp(th0, N)
    if ok and S['alpha'][-1] == al:                                   # accepted at the first trial: same kappa as GEO's first trial
        assert np.max(np.abs(d_bj - al * d_geo)) <= 1e-8 * max(1.0, np.max(np.abs(d_geo)))


def test_V7_bj_alpha_branch_exercised():
    th0 = np.array([[0.8, 15.0, 17.0, np.log(3.0), 0.1, np.log(2.5)]]); P = _prob(th_true=np.array([[0.9, 16.0, 16.0, np.log(3.2), 0.0, np.log(2.8)]]), seed=2)
    S = dict(th=GC.clamp(th0, N), x=None, r=None, F=None, kappa=CFG['kappa0'], rej=0, rank=None, trials=0, clamped=0, clamp_trials=0, diag=[], itn=[], alpha=[], act=[])
    F, x, rr = P.F_of(S['th']); S.update(x=x, r=rr, F=F)
    cnt = dict(A=0, J=0, mv=0, W=0.0, Ad=0, Wd=0.0); T = dict(jac=0., aj=0., solve=0., back=0.)
    ok = GC._iter_bj(P, S, CFG, cnt, T)
    assert ok and len(S['alpha']) == 1 and 0 < S['alpha'][0]
    g = GC.solve('GEO', P, th0, CFG, max_iter=1); d_geo = g['theta'] - GC.clamp(th0, N); d_bj = S['th'] - GC.clamp(th0, N)
    assert np.max(np.abs(d_bj - S['alpha'][0] * d_geo)) <= 1e-8 * max(1.0, np.max(np.abs(d_geo)))


# ---------------------------------------------------------------- V8 (A1.4 counting conventions, deterministic W)
def test_V8_counting_conventions_and_deterministic_W():
    P = _prob(); th0 = GC.grid_init(P, 9); K = 9; p = 6 * K
    g = GC.solve('GEO', P, th0, CFG, max_iter=3)
    # per accepted/rejected trial: exactly 1 A-application (F evaluation); AJ formation p per outer iteration; A*jv_c via (AJ) delta_c costs 0
    its = len(g['traj']) - 1
    assert g['cnt']['A'] == its * p + g['trials'], (g['cnt']['A'], its, p, g['trials'])
    a1 = GC.solve('GEO', P, th0, CFG, max_iter=3); assert a1['cnt']['W'] == g['cnt']['W'] and a1['cnt']['A'] == g['cnt']['A']
    l = GC.solve('LSMR', P, th0, CFG, max_iter=2)
    assert l['cnt']['A'] == l['cnt']['mv'] + l['trials'] * 2 + (len(l['traj']) - 1) and l['cnt']['W'] > 0   # mv counted 1 A each; each trial: F eval (1) + A*jv_c (1); active-set gradient: 1 A^T per outer iteration
    d = GC.solve('PCG8D', P, th0, CFG, max_iter=3)
    assert d['cnt']['Ad'] == (len(d['traj']) - 1) * p and d['cnt']['Wd'] > 0 and d['traj'][-1][8] == d['cnt']['Ad']
    b = GC.solve('BLK', P, th0, CFG, max_iter=2)
    assert b['blk_eval'] > 0 and b['cnt']['W'] > 0
