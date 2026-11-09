"""AS contract v2.1 validity gates V1..V17 (unit tests, no data readout). usage: as_test.py [V1 V3 ...]   (default: all)
Failure of any gate = INVALID (infrastructure), not a verdict on the hypothesis."""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ[_v] = '1'
import sys, ast, json, time, hashlib, inspect
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src')); sys.path.insert(0, os.path.join(ROOT, 'experiments'))
import numpy as np
import as_core as C, as_gen as G

N = C.N
RES = []


def check(name, ok, detail=''):
    RES.append((name, bool(ok), detail)); print(('PASS ' if ok else 'FAIL ') + name + ' ' + detail, flush=True)


def small_state(K=3, seed=3, sb=1.0, sn=0.01):
    """A small well-conditioned K-Gaussian state and an arbitrary (non-stationary) residual."""
    rng = np.random.default_rng(seed); op = C.Op(sb)
    th = []
    for k in range(K):
        th.append([rng.uniform(0.5, 1.0), rng.uniform(8, 24), rng.uniform(8, 24), np.log(rng.uniform(2.5, 4.5)), rng.uniform(-0.8, 0.8), np.log(rng.uniform(2.5, 4.5))])
    th = np.array(th); clean = G.clean_image(1); y = G.noisy_obs(op, clean, sn, 9001, 1)
    return op, th, y


def v1():
    rng = np.random.default_rng(0); worst = 0.0
    for _ in range(5):
        p = np.array([rng.uniform(-1, 1), rng.uniform(8, 24), rng.uniform(8, 24), np.log(rng.uniform(1.0, 6)), rng.uniform(-1, 1), np.log(rng.uniform(1.0, 6))])
        g, J = C.g_jac(p)
        for j in range(6):
            h = 1e-5 * (1 if j != 0 else 1); pp = p.copy(); pm = p.copy(); pp[j] += h; pm[j] -= h
            fd = (C.g_img(pp) - C.g_img(pm)) / (2 * h)
            err = np.linalg.norm(fd - J[j]) / (np.linalg.norm(J[j]) + 1e-300); worst = max(worst, err)
    check('V1 analytic Jacobian vs central differences (max rel err < 1e-5)', worst < 1e-5, 'worst=%.2e' % worst)


def v2():
    op, th, y = small_state(4)
    t1, L1, i1 = C.lm(op, y, th, 0.01, 8); t2, L2, i2 = C.lm(op, y, th, 0.01, 8)
    same = np.array_equal(t1, t2) and L1 == L2
    L0 = C.loss(op, y, C.clamp(th), 0.01); Ls = [L0]; cur = C.clamp(th)
    for _ in range(8):
        cur, Lc, _i = C.lm(op, y, cur, 0.01, 1); Ls.append(Lc)
    mono = all(Ls[i + 1] <= Ls[i] + 1e-9 * abs(Ls[i]) for i in range(len(Ls) - 1))
    check('V2 LM deterministic (bitwise) and accepted-step loss non-increasing', same and mono and L1 <= L0, 'bitwise=%s mono=%s L0=%.4g L8=%.4g' % (same, mono, L0, L1))


def _brute(op, th, y, cand, c):
    """minimum over delta of 0.5||r - c v - AJ delta||^2 (unweighted LS, same rcond) and baseline 0.5||P_perp r||^2."""
    x, Jimg = C.render_jac(th); r = (y - op.apply(x)).ravel()
    AJ = op.apply_stack(Jimg).reshape(th.shape[0] * 6, -1).T; v = op.apply(cand['q']).ravel()
    def res(z):
        d = np.linalg.lstsq(AJ, z, rcond=C.RCOND)[0]; e = z - AJ @ d; return 0.5 * float(e @ e)
    return res(r) - res(r - c * v)


def v3():
    worst = 0.0; nsplit = nbirth = 0
    for K, seed in ((2, 11), (3, 12), (4, 13)):
        op, th, y = small_state(K, seed); r_img = y - op.apply(C.render(th))
        cands, ncl = C.gen_candidates(op, th, r_img)
        AJ, Uk, blocks, s0, us = C.projectors(op, th); sc, aux = C.score_candidates(op, th, y, cands, AJ, Uk, blocks)
        # splits: c = 1
        sidx = [i for i, c in enumerate(cands) if c['type'] == 's' and np.isfinite(sc['JOINT'][i])][:6]
        for i in sidx:
            b = _brute(op, th, y, cands[i], 1.0); worst = max(worst, abs(b - sc['JOINT'][i]) / (abs(b) + 1e-12)); nsplit += 1
        bidx = [i for i, c in enumerate(cands) if c['type'] == 'b' and np.isfinite(aux['cols'][i])][:6]
        for i in bidx:
            cj = float(np.clip(aux['cols'][i], -C.CMAX, C.CMAX)); b = _brute(op, th, y, cands[i], cj); worst = max(worst, abs(b - sc['JOINT'][i]) / (abs(b) + 1e-12)); nbirth += 1
    check('V3 JOINT score == brute-force linearised LS gain (K<=4, split and birth; rel err < 1e-8)', worst < 1e-8 and nsplit >= 6 and nbirth >= 6, 'worst=%.2e n_split=%d n_birth=%d' % (worst, nsplit, nbirth))


def v4():
    op, th, y = small_state(3, 21); r_img = y - op.apply(C.render(th)); cands, _ = C.gen_candidates(op, th, r_img)
    AJ, Uk, blocks, s0, us = C.projectors(op, th); sc0, _a = C.score_candidates(op, th, y, cands, AJ, Uk, blocks)
    th2 = np.vstack([th[:1] * np.array([0.5, 1, 1, 1, 1, 1]), th[:1] * np.array([0.5, 1, 1, 1, 1, 1]), th[1:]])      # duplicate Gaussian 0 into two half-amplitude copies
    assert np.allclose(C.render(th2), C.render(th), atol=1e-12)
    AJ2, Uk2, blocks2, s02, us2 = C.projectors(op, th2); sc1, _b = C.score_candidates(op, th2, y, cands, AJ2, Uk2, blocks2)
    m = np.isfinite(sc0['JOINT']); err = np.max(np.abs(sc0['JOINT'][m] - sc1['JOINT'][m]) / (np.abs(sc0['JOINT'][m]) + 1e-12))
    same_rank = np.array_equal(np.argsort(-np.where(m, sc0['JOINT'], -np.inf), kind='stable'), np.argsort(-np.where(m, sc1['JOINT'], -np.inf), kind='stable'))
    check('V4 duplication invariance of JOINT scores/ranking on the original candidate set (< 1e-8)', err < 1e-8 and same_rank, 'max_rel_err=%.2e rank_equal=%s rank(AJ)=%d->%d' % (err, same_rank, Uk.shape[1], Uk2.shape[1]))


def v5():
    op, th, y = small_state(3, 31); r_img = y - op.apply(C.render(th)); cands, _ = C.gen_candidates(op, th, r_img)
    AJ, Uk, blocks, s0, us = C.projectors(op, th); sc0, _a = C.score_candidates(op, th, y, cands, AJ, Uk, blocks)
    # amplitude x10 (and y x10): scores scale by 100, ranking unchanged
    thA = th.copy(); thA[:, 0] *= 10; AJA, UkA, bA, _s, _u = C.projectors(op, thA)
    cA = []
    for c in cands:      # candidate image increments scale with amplitudes: rebuild by scaling q (splits/births: births are unit-shape, scaled by the optimal c* anyway)
        d = dict(c); d['q'] = c['q'] * (10.0 if c['type'] == 's' else 1.0); cA.append(d)
    scA, _b = C.score_candidates(op, thA, 10 * y, cA, AJA, UkA, bA)
    m = np.isfinite(sc0['JOINT']) & np.isfinite(scA['JOINT'])
    ratio_split = [scA['JOINT'][i] / sc0['JOINT'][i] for i in np.where(m)[0] if cands[i]['type'] == 's' and abs(sc0['JOINT'][i]) > 1e-14]
    ok_amp = np.allclose(ratio_split, 100.0, rtol=1e-6)
    rk0 = np.argsort(-np.where(np.isfinite(sc0['JOINT']) & np.array([c['type'] == 's' for c in cands]), sc0['JOINT'], -np.inf), kind='stable')[:10]
    rkA = np.argsort(-np.where(np.isfinite(scA['JOINT']) & np.array([c['type'] == 's' for c in cands]), scA['JOINT'], -np.inf), kind='stable')[:10]
    # log <-> linear length parameterisation: column scaling of the two log-l columns by exp(l) leaves range(AJ) (hence JOINT) unchanged
    x, Jimg = C.render_jac(th); K = th.shape[0]
    AJo = op.apply_stack(Jimg).reshape(K * 6, -1).T; s = np.ones(K * 6)
    for k in range(K): s[6 * k + 3] = 1.0 / np.exp(th[k, 3]); s[6 * k + 5] = 1.0 / np.exp(th[k, 5])
    AJl = AJo * s[None, :]
    def Uof(M):
        U, sv, _ = np.linalg.svd(M, full_matrices=False); return U[:, :int(np.sum(sv > C.RCOND * sv[0]))]
    U1, U2 = Uof(AJo), Uof(AJl); proj_err = float(np.linalg.norm(U1 @ U1.T - U2 @ U2.T))
    scL, _c = C.score_candidates(op, th, y, cands, AJl, U2, blocks); mm = np.isfinite(sc0['JOINT'])
    errL = float(np.max(np.abs(scL['JOINT'][mm] - sc0['JOINT'][mm]) / (np.abs(sc0['JOINT'][mm]) + 1e-12)))
    check('V5 rescaling invariance (amplitude x10: scores x100 and same ranking; log<->linear length columns: same projector/JOINT)', ok_amp and np.array_equal(rk0, rkA) and proj_err < 1e-8 and errL < 1e-8,
          'amp_ratio_ok=%s rank_equal=%s proj_err=%.2e score_err=%.2e' % (ok_amp, np.array_equal(rk0, rkA), proj_err, errL))


def v6():
    src = open(os.path.join(ROOT, 'src', 'as_core.py')).read(); tree = ast.parse(src); bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.arg) and ('clean' in node.arg.lower() or node.arg.lower() in ('gt', 'x_true', 'truth')): bad.append('arg:' + node.arg)
        if isinstance(node, ast.Name) and 'clean' in node.id.lower(): bad.append('name:' + node.id)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] + ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            if any(n and ('as_gen' in n or 'as_oracle' in n) for n in names): bad.append('import:' + str(names))
    sigs_ok = all(('clean' not in str(inspect.signature(f)).lower()) for _n, f in inspect.getmembers(C, inspect.isfunction))
    check('V6 method-side module has no clean-image argument/name/import (AST + signatures); ORACLE_x exempt', not bad and sigs_ok, 'violations=%s' % bad)


def v8():
    op, th, y = small_state(5, 41); r_img = y - op.apply(C.render(th)); h = [C.cand_hash(C.gen_candidates(op, th, r_img)[0]) for _ in range(3)]
    check('V8 candidate generation deterministic', len(set(h)) == 1, h[0])


def v10():
    op, th, y = small_state(3, 51); AJ, Uk, blocks, s0, us = C.projectors(op, th)
    # a candidate whose v lies in range(AJ): amplitude change of Gaussian 0 -> P_perp v ~ 0 -> must be excluded from JOINT
    q = C.g_img(np.concatenate([[1.0], th[0, 1:]])); cands = [dict(type='s', parent=0, rows=th[:2], q=q), dict(type='b', parent=-1, row=np.array([1.0, 3.0, 3.0, np.log(2), 0, np.log(2)]), q=C.g_img(np.array([1.0, 3.0, 3.0, np.log(2), 0, np.log(2)])))]
    sc, aux = C.score_candidates(op, th, y, cands, AJ, Uk, blocks)
    excl = (aux['floor'][0] < C.FLOOR) and not np.isfinite(sc['JOINT'][0]) and np.isfinite(sc['OMP'][0])
    # stability logging exists in run_path (JOINT arm): one short real run, S=1
    res = C.run_path(y, op, 0.01, 'JOINT', S=1, Tr=3, T0=3); st = res['logs'][0]['v10_stable']
    check('V10 floor 1e-3 excludes range(AJ) candidate from JOINT; rcond-stability of JOINT top-1 is recorded', excl and isinstance(st, dict) and set(st) == {'1e-08', '1e-12'},
          'floor_ratio=%.2e stab=%s' % (aux['floor'][0], st))


def v11():
    op = C.Op(2.0); A = op.dense(); rng = np.random.default_rng(1); X = rng.standard_normal((N, N))
    e = np.linalg.norm(A @ X.ravel() - op.apply(X).ravel()) / np.linalg.norm(op.apply(X))
    check('V11 separable A vs dense A relative error < 1e-12', e < 1e-12, '%.2e' % e)


def v12():
    worst = 0.0; asym = 0.0
    for sb in (1.0, 2.0):
        op = C.Op(sb); rng = np.random.default_rng(2); X = rng.standard_normal((N, N)); Z = rng.standard_normal((N, N))
        a = float(np.sum(op.apply(X) * Z)); b = float(np.sum(X * op.adj(Z))); worst = max(worst, abs(a - b) / abs(a)); asym = max(asym, float(np.abs(op.B - op.B.T).max()))
    # contract premise 'reflective-boundary B is asymmetric' is false for half-sample reflection + symmetric kernel (B comes out symmetric, asym above);
    # the adjoint test is therefore also run on a deliberately asymmetric B so that adj() = B^T is really exercised.
    op2 = C.Op(1.0); rng = np.random.default_rng(5); Ba = np.abs(rng.standard_normal((N, N))) + np.eye(N); Ba /= Ba.sum(1, keepdims=True)
    op2.B = Ba; op2.Bt = np.ascontiguousarray(Ba.T); X = rng.standard_normal((N, N)); Z = rng.standard_normal((N, N))
    a2 = float(np.sum(op2.apply(X) * Z)); b2 = float(np.sum(X * op2.adj(Z))); w2 = abs(a2 - b2) / abs(a2); asym2 = float(np.abs(Ba - Ba.T).max())
    check('V12 adjoint <Ax,z> = <x,A^T z> to 1e-12 on the real operators and on a deliberately asymmetric B', worst < 1e-12 and w2 < 1e-12 and asym2 > 1e-3,
          'real_worst=%.2e real_asym=%.2e (B symmetric: contract premise corrected) asym_test_worst=%.2e asym2=%.2e' % (worst, asym, w2, asym2))


def v13():
    op, th, y = small_state(3, 61); res = C.run_path(y, op, 0.01, 'OMP', S=2, Tr=2, T0=3)
    ok = all(('stat' in r and np.isfinite(r['stat'])) for r in res['logs'])
    check('V13 stationarity ratio recorded before every scoring', ok, str([round(r['stat'], 4) for r in res['logs']]))


def v14():
    op, th, y = small_state(3, 71); th2 = th.copy(); th2[1, 3] = C.LMIN       # parent 1 clamped at lower log-l bound
    r_img = y - op.apply(C.render(th2)); cands, ncl = C.gen_candidates(op, th2, r_img)
    has = any(c['type'] == 's' and c['parent'] == 1 for c in cands); other = any(c['type'] == 's' and c['parent'] == 0 for c in cands)
    check('V14 clamped parent candidates excluded and counted', (not has) and other and ncl == 1, 'n_clamped=%d' % ncl)


def v15():
    op, th, y = small_state(3, 81); th0 = th.copy(); th0[:, 1:3] += 5.0      # bad start: forces rejections
    t, L, info = C.lm(op, y, th0, 0.01, 5, cap=0)
    check('V15 LM rejected-step cap trigger is recorded (info.capped/rej)', 'capped' in info and 'rej' in info and (info['capped'] or info['rej'] == 0), str(info))


def v16():
    op, th, y = small_state(3, 91)
    r1 = C.run_path(y, op, 0.01, 'OMP', S=1, Tr=2, T0=3); r2 = C.run_path(y, op, 0.01, 'JOINT', S=1, Tr=2, T0=3); r3 = C.run_oracle_y(y, op, 0.01, 'short', S=1, Tr=2, T0=3)
    same_hash = r1['logs'][0]['cand_hash'] == r2['logs'][0]['cand_hash'] == r3['logs'][0]['cand_hash']
    srcs = {n: inspect.getsource(f) for n, f in (('run_path', C.run_path), ('run_oracle_y', C.run_oracle_y))}
    ox = open(os.path.join(ROOT, 'src', 'as_oracle_x.py')).read()
    uses_execute = all('execute(' in s for s in srcs.values()) and 'C.execute(' in ox
    check('V16 identical C_1 (hash) across arms and one shared edit-execution function', same_hash and uses_execute, 'hash=%s uses_execute=%s' % (r1['logs'][0]['cand_hash'], uses_execute))


def v17():
    run_src = open(os.path.join(ROOT, 'experiments', 'as_run.py')).read(); an_path = os.path.join(ROOT, 'experiments', 'as_analyze.py')
    core_src = open(os.path.join(ROOT, 'src', 'as_core.py')).read()
    sep = "(o + '-ORX')" in run_src and 'AS-S2-ORX' not in core_src
    # method arms never read result files: the only exists() in the runner is its own output path; as_core contains no file reads of results
    reads = [ln for ln in run_src.splitlines() if 'json.load' in ln or "open(" in ln and "'r'" in ln]
    core_reads = [ln for ln in core_src.splitlines() if 'json.load' in ln and '_ckpt_load' not in ln and 'd = json.load' not in ln]
    an_ok = os.path.exists(an_path)
    check('V17 ORACLE_x outputs in separate directory (<out>-ORX), method code reads no result files', sep and not reads and not core_reads, 'separate_dir=%s runner_reads=%d core_reads=%d analyzer_present=%s' % (sep, len(reads), len(core_reads), an_ok))


def vsmoke():
    """Not a V gate: end-to-end crash check on a tiny budget + candidate counts + timing (no quality reading)."""
    op = C.Op(1.0); y = G.noisy_obs(op, G.clean_image(1), 0.01, 9001, 1); t0 = time.time()
    res = C.run_path(y, op, 0.01, 'JOINT', S=3, Tr=3, T0=5, diag_top5=True)
    print('smoke: 3 steps %.1fs; logs keys=%s; n_cand=%s' % (time.time() - t0, sorted(res['logs'][0].keys()), [r['n_cand'] for r in res['logs']]))
    check('SMOKE end-to-end run_path executes', len(res['traj']) == 4 and len(res['logs']) == 3)


ALL = dict(V1=v1, V2=v2, V3=v3, V4=v4, V5=v5, V6=v6, V8=v8, V10=v10, V11=v11, V12=v12, V13=v13, V14=v14, V15=v15, V16=v16, V17=v17, SMOKE=vsmoke)

if __name__ == '__main__':
    sel = sys.argv[1:] or list(ALL)
    for k in sel:
        t0 = time.time()
        try: ALL[k]()
        except Exception as e:
            import traceback; traceback.print_exc(); check(k + ' (exception)', False, repr(e))
        print('  [%s %.1fs]' % (k, time.time() - t0), flush=True)
    nf = sum(1 for r in RES if not r[1]); print('SUMMARY: %d checks, %d failed' % (len(RES), nf)); sys.exit(1 if nf else 0)
