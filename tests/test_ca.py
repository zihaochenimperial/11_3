"""CA unit tests (contract CA candidate v0). Run: python3 tests/test_ca.py   (uses DEV/SMOKE/CAL indices and cached dev fits only; never opens CONFIRM images; sealed gate exercised on a temporary record with dummy arguments)."""
import os, sys, json, re, tempfile, shutil, inspect, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(HERE, '..', 'src'); EXP = os.path.join(HERE, '..', 'experiments')
sys.path.insert(0, SRC); sys.path.insert(0, EXP)
import numpy as np
import geo_core as GC, jr_op, ca_gen as CG, ca_diag as D

N = CG.N
FITS = os.path.join(HERE, '..', 'outputs', 'CA', 'dev', 'fits')


def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def test_index_sets_disjoint_and_levels():
    sets = dict(DEV=set(CG.DEV_IMGS), SMOKE=set(CG.SMOKE_IMGS), CAL=set(CG.CAL_IMGS), CONFIRM=set(CG.CONFIRM_IMGS)); names = list(sets)
    for a in names:
        assert not (sets[a] & CG.OLD), a + ' overlaps an earlier set'
        for b in names:
            if a < b: assert not (sets[a] & sets[b]), (a, b)
    assert not (set(range(831, 851)) & set().union(*sets.values())) and not (set(range(871, 890)) & set().union(*sets.values())), 'reserved indices used'
    assert all(CG.level_of(i) == 'hi' for i in CG.CONFIRM_IMGS), 'all CONFIRM tiles must be the hi stratum'
    assert [i for i in CG.DEV_IMGS if CG.level_of(i) == 'lo'] == [801, 802]


def test_sharp_image_basic_and_old_sealed_refused():
    for i in (801, 806, 851, 890):
        x = CG.sharp_image(i); assert x.shape == (N, N) and x.min() >= 0 and abs(x.max() - 1) < 1e-12 and np.array_equal(x, CG.sharp_image(i))
    for bad in (701, 712, 424, 1, 590, 831, 895):
        try: CG.sharp_image(bad)
        except AssertionError: continue
        raise AssertionError('index %d must be refused' % bad)
    os.environ.pop('CA_CONFIRM_UNLOCK', None); CG._SESSION.clear()
    try: CG.sharp_image(811)
    except AssertionError: pass
    else: raise AssertionError('sealed CONFIRM tile must be refused without gate')


def test_sealed_gate_on_temporary_record():
    tmp = tempfile.mkdtemp(); rec = os.path.join(tmp, 'REC.txt'); main = os.path.join(tmp, 'analyzer.py'); mod = os.path.join(tmp, 'ca_dummy.py'); open(main, 'w').write('print(1)\n'); open(mod, 'w').write('x=1\n')
    env = {'CA_CONFIRM_UNLOCK': '1'}
    def lines(*extra): return '\n'.join(['DEV_DONE ok', 'CONFIRM_UNSEALED ok', 'ANALYZER_SHA256 %s analyzer.py' % sha(main), 'MODULE_SHA256 %s ca_dummy.py' % sha(mod)] + list(extra)) + '\n'
    def attempt(text=None, environ=env, main_file=main, module_files=(mod,)):
        CG._SESSION.clear()
        if text is not None: open(rec, 'w').write(text)
        try: CG._sealed_gate('CONFIRM', rec_path=rec, environ=environ, main_file=main_file, module_files=list(module_files), now='T'); return True
        except AssertionError: return False
    try:
        assert not attempt(None, environ={}), 'no env'
        assert not os.path.exists(rec) and not attempt(None), 'no record'
        assert not attempt('CONFIRM_UNSEALED x\nANALYZER_SHA256 %s analyzer.py\nMODULE_SHA256 %s ca_dummy.py\n' % (sha(main), sha(mod))), 'no DEV_DONE'
        assert not attempt('DEV_DONE x\nANALYZER_SHA256 %s analyzer.py\nMODULE_SHA256 %s ca_dummy.py\n' % (sha(main), sha(mod))), 'no UNSEALED'
        assert not attempt('DEV_DONE x\nCONFIRM_UNSEALED x\nANALYZER_SHA256 0 analyzer.py\nMODULE_SHA256 %s ca_dummy.py\n' % sha(mod)), 'analyzer sha'
        assert not attempt('DEV_DONE x\nCONFIRM_UNSEALED x\nANALYZER_SHA256 %s analyzer.py\nMODULE_SHA256 0 ca_dummy.py\n' % sha(main)), 'module sha'
        assert not attempt('2026-11-09 DEV_DONE x\n2026-11-09 CONFIRM_UNSEALED x\n'), 'timestamp-prefixed lines must not satisfy the gate'
        assert attempt(lines()), 'valid record must pass'; assert 'CONFIRM_CONSUMED' in open(rec).read()
        assert not attempt(None), 'second consumption must be refused'
        open(rec, 'a').write('CONFIRM_RESUME_OK crash recovery\n'); assert attempt(None), 'RESUME_OK allows one more'
        assert not attempt(None), 'and only one'
    finally: shutil.rmtree(tmp); CG._SESSION.clear()


def test_method_side_never_imports_evaluator_modules():
    for f in sorted(os.listdir(SRC)):
        if not f.endswith('.py') or f.startswith('ca_'): continue
        if f in ('geo_core.py', 'jr_core.py', 'jr_op.py', 'geo_flops.py'):
            t = open(os.path.join(SRC, f)).read(); assert not re.search(r'^\s*(import|from)\s+(ca_gen|ca_diag)\b', t, re.M), f + ' imports evaluator-side module'
    import subprocess
    r = subprocess.run([sys.executable, '-c', 'import sys; sys.path.insert(0, %r); import jr_core, geo_core, jr_op; assert not any(m.startswith("ca_") for m in sys.modules)' % SRC], capture_output=True, text=True); assert r.returncode == 0, r.stderr


def test_paired_noise_shared_across_representations_and_noise_free_zero():
    op = CG.make_op('G15'); xs = CG.sharp_image(801); xg = CG.get_fit(801, FITS)['x']
    y0n, e0 = CG.observe(op, xg, True, 801, 'G15'); y1n, e1 = CG.observe(op, xs, True, 801, 'G15'); assert np.array_equal(e0, e1) and np.abs(e0).max() > 0
    assert abs(e0.std() - CG.SN) < 0.15 * CG.SN
    y0f, ef = CG.observe(op, xg, False, 801, 'G15'); assert np.all(ef == 0) and np.abs((y0n - y0f) - e0).max() < 1e-12 and np.abs(y0f - op.apply(xg)).max() < 1e-12
    assert not np.array_equal(CG.noise_of(801, 'G15'), CG.noise_of(801, 'AG')) and not np.array_equal(CG.noise_of(801, 'G15'), CG.noise_of(802, 'G15'))


def test_noise_free_cells_use_same_numerical_scale_and_ratio():
    t = open(os.path.join(EXP, 'ca_run.py')).read(); calls = re.findall(r'JC\.JProb\(([^)]*)\)', t)
    assert len(calls) == 1 and calls[0].replace(' ', '') == 'N,op,y,CG.SN,ar/CG.SN**2', calls
    import ca_run as RUN
    assert abs(CG.SN - 0.02) < 1e-15 and RUN.A_RATIO == 1e-3
    for blk in ('P', 'S', 'X'):
        assert all(j[6] == 1e-3 for j in RUN.jobs(blk)), blk                          # same a = 1e-3/SN^2 in every cell of every confirm block
    assert all(j[6] == 1e-2 for j in RUN.jobs('A')) and all(set(j[4]) <= {('R0', 1), ('R1', 1)} for j in RUN.jobs('A'))


def test_block_X_unconditional_and_A_is_dev_only():
    import ca_run as RUN
    xs = RUN.jobs('X'); assert {j[0] for j in xs} == {'OBS-J', 'RND-J'} and all(set(j[4]) == {('R0', 0), ('R0', 1)} for j in xs) and all(abs(j[5] - 10 * RUN.W_CAP) < 1 and j[7] >= 5000 for j in xs)
    assert RUN.block_imgs('X', list(range(811, 827))) == [811, 812, 813, 814] and RUN.block_imgs('P', list(range(811, 827))) == list(range(811, 827))
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(EXP, 'ca_run.py'), '--stage', 'confirm', '--blocks', 'P,A'], capture_output=True, text=True); assert r.returncode != 0 and 'block A is DEV-only' in r.stderr, r.stderr[-300:]


def test_registered_module_files_cover_generation_dependencies():
    import as_gen, geo_flops
    files = CG.registered_module_files(); names = {os.path.basename(f) for f in files}
    assert {'ca_gen.py', 'as_gen.py', 'geo_core.py', 'geo_flops.py', 'jr_core.py', 'jr_op.py'} <= names, names
    assert {os.path.dirname(os.path.abspath(f)) for f in files} == {os.path.dirname(os.path.abspath(CG.__file__))}


def test_generator_consistent_with_cached_fits():
    """Every cached DEV/SMOKE K-fit was produced from the CURRENT sharp-tile generator (the fit's psnr_rep equals the PSNR of its render against sharp_image(i) now)."""
    import glob
    fs = sorted(glob.glob(os.path.join(FITS, 'fit_*.json'))); assert len(fs) >= 8
    for f in fs:
        i = int(os.path.basename(f)[4:-5]); d = json.load(open(f)); assert abs(CG.psnr(np.array(d['x']), CG.sharp_image(i)) - d['psnr_rep']) < 1e-6, f


def test_R0_is_exactly_K_representable_and_psnr_rep_consistent():
    f = CG.get_fit(801, FITS); th = np.array(f['theta']); assert th.shape == (36, 6)
    assert np.abs(GC.render(th, N) - f['x']).max() < 1e-9, 'R0 truth must be the render of K=36 Gaussians'
    assert abs(CG.psnr(f['x'], CG.sharp_image(801)) - f['psnr_rep']) < 1e-6


def test_line_pair_matched_moments():
    ss = 8; g = (np.arange(N * ss) + 0.5) / ss; X, Y = np.meshgrid(g, g, indexing='xy'); one, two = D.line_pair(sw=1.5, s=2.2, phi=np.deg2rad(37), cx=16.0, cy=16.0, sa=6.0)
    def mom(th):
        x = sum(t[0] * np.exp(-0.5 * np.einsum('...i,ij,...j->...', np.stack([X - t[1], Y - t[2]], -1), np.linalg.inv(D.sigma_of(t)), np.stack([X - t[1], Y - t[2]], -1))) for t in th); m = x.sum(); cx = (x * X).sum() / m; cy = (x * Y).sum() / m
        nx, ny = -np.sin(np.deg2rad(37)), np.cos(np.deg2rad(37)); v = (X - 16) * nx + (Y - 16) * ny; return m / ss ** 2, cx, cy, (x * v ** 2).sum() / m
    a, b = mom(one), mom(two)
    assert abs(a[0] - b[0]) / a[0] < 2e-3 and abs(a[1] - b[1]) < 2e-3 and abs(a[2] - b[2]) < 2e-3 and abs(a[3] - b[3]) / a[3] < 2e-3, (a, b)


def test_reparametrisation_controls_have_zero_difference():
    th = np.array([[1.0, 14.0, 16.0, np.log(1.6), 0.2, np.log(2.2)], [0.8, 20.0, 15.0, np.log(2.0), -0.3, np.log(1.4)]]); split = np.vstack([th[0:1] * np.array([0.5, 1, 1, 1, 1, 1]), th[0:1] * np.array([0.5, 1, 1, 1, 1, 1]), th[1:2]])
    for pn in CG.PSF_ORDER:
        for b in (th[::-1], split):
            m = D.measures(CG.make_op(pn), GC.render(th, N), GC.render(b, N)); assert m['Dimg'] < 1e-9 and m['d'] < 1e-9 and not m['amb']


def test_bayes_error_formula_vs_monte_carlo():
    op = CG.make_op('AG'); one, two = D.line_pair(sw=1.5, s=2.6, phi=np.deg2rad(120)); mu0 = op.apply(GC.render(one, N)).ravel(); mu1 = op.apply(GC.render(two, N)).ravel(); dv = mu1 - mu0; d = np.linalg.norm(dv) / CG.SN
    rng = np.random.default_rng(3); n = 30000; z = rng.standard_normal((n, mu0.size)) * CG.SN; mid = 0.5 * (mu0 + mu1)
    e = 0.5 * np.mean((mu0 + z - mid) @ dv > 0) + 0.5 * np.mean((mu1 + z - mid) @ dv <= 0); se = np.sqrt(e * (1 - e) / n)
    assert abs(e - D.bayes_error(d)) < 4 * se + 1e-3, (e, D.bayes_error(d))
    assert abs(D.bayes_error(0.0) - 0.5) < 1e-15 and D.bayes_error(3.0) < D.bayes_error(1.0)


def test_merge_pair_preserves_mass_and_mean():
    a = np.array([1.0, 14.0, 16.0, np.log(2.0), 0.0, np.log(2.0)]); b = np.array([0.7, 18.0, 17.0, np.log(2.5), 0.2, np.log(1.8)]); m = D.merge_pair(a, b)
    assert abs(D.mass_of(m) - (D.mass_of(a) + D.mass_of(b))) < 1e-9 * D.mass_of(m)
    c = (D.mass_of(a) * a[1:3] + D.mass_of(b) * b[1:3]) / (D.mass_of(a) + D.mass_of(b)); assert np.abs(m[1:3] - c).max() < 1e-12
    xa, xm = GC.render(np.vstack([a, b]), N), GC.render(m[None], N); assert abs(xa.sum() - xm.sum()) / xa.sum() < 5e-3


def test_merge_load_skips_signed_pairs_and_runs_on_cached_fit():
    th = np.array([[1.0, 14.0, 16.0, np.log(1.6), 0.2, np.log(2.2)], [-0.8, 16.0, 16.0, np.log(2.0), -0.3, np.log(1.4)], [0.9, 18.0, 15.0, np.log(1.8), 0.0, np.log(1.8)]])
    rows, n, sk = D.merge_load(CG.make_op('AG'), th); assert sk == 2 and len(rows) == 1 and n in (0, 1)
    f = CG.get_fit(804, FITS); rows, n, sk = D.merge_load(CG.make_op('G15'), np.array(f['theta'])); assert sk > 0 and len(rows) > 0 and all(r['d'] >= 0 for r in rows)


def test_tangent_gauge_directions_removed():
    th = np.array([[1.0, 14.0, 16.0, np.log(1.6), 0.2, np.log(2.2)], [0.8, 20.0, 15.0, np.log(2.0), -0.3, np.log(1.4)]]); thd = np.vstack([th, th[0:1]])      # duplicated primitive -> rank-deficient (render-null directions exist)
    U, ng = D.tangent_basis(th); Ud, ngd = D.tangent_basis(thd); assert ng == 0 and U.shape[1] == 12 and Ud.shape[1] <= 12 and ngd >= 6, (U.shape, ng, Ud.shape, ngd)
    assert np.abs(U.T @ U - np.eye(U.shape[1])).max() < 1e-9


def test_reducer_pipeline_on_synthetic_runs():
    import ca_reduce as R
    tmp = tempfile.mkdtemp(); root0 = R.ROOT; R.ROOT = tmp; rd = os.path.join(tmp, 'outputs', 'CA', 'fake', 'runs'); os.makedirs(rd); rng = np.random.default_rng(0); W = list(R.GRID)
    try:
        for img in range(8):
            for cond in ('G15', 'AG'):
                for rep in ('R0', 'R1'):
                    for nz in (0, 1):
                        base = 30 + rng.normal(0, 0.5); minVF = 10.0
                        for arm in ('OBS-J', 'RND-J', 'IND1', 'OBS-I', 'SPA-J'):
                            delta = -0.6 if (arm == 'OBS-J' and nz == 1) else 0.0               # synthetic truth: focal deficit only in the noisy cells (both representations) -> V-N
                            q = base + delta + rng.normal(0, 0.05); json.dump(dict(img=img, cond=cond, rep=rep, noisy=nz, armname=arm, rep_psnr=31.0, level='hi', F0=100.0, trajW=W, trajF=[50.0 - k for k in range(8)], psnr=[q] * 8, psnr_edge=[q - 3] * 8, psnr_blur=[q + 8] * 8,
                                resid=[1.0] * 8, nf=[0.1] * 8 if nz else None, mf=[0.1] * 8 if rep == 'R1' else None, psnr_vs_proj=[q + 5] * 8 if rep == 'R1' else None, rej=1, trials=10, stop='budget', wall=1.0, minVF=minVF),
                                open(os.path.join(rd, '%d_%s_%s_n%d__%s__P.json' % (img, cond, rep, nz, arm)), 'w'))
        out = R.reduce('fake', 'P'); v = out['verdicts']['RND-J']; assert v['verdict'] == 'V-N' and v['strength'] == 'STRONG', v
        c = out['gaps']['RND-J']['cells']; assert c['R0/noisy']['label'] == 'D' and c['R1/noisy']['label'] == 'D' and c['R0/free']['label'] == 'E' and c['R1/free']['label'] == 'E'
        assert abs(out['gaps']['RND-J']['contrasts']['N_effect(noise)']['mean'] + 0.6) < 0.1 and abs(out['gaps']['RND-J']['contrasts']['R_effect(rep+HF content)']['mean']) < 0.1
        assert out['gaps']['RND-J']['contrasts']['N_effect(noise)']['MDE80'] > 0
    finally: R.ROOT = root0; shutil.rmtree(tmp)


def test_stop_time_qualifier_and_missing_rule():
    import ca_reduce as R
    lq = {'R0/free': 'E', 'R0/noisy': 'D', 'R1/free': 'E', 'R1/noisy': 'D'}
    assert R.qualify(lq, {c: 'E' for c in lq}, {c: 'I' for c in lq}) == {'R0/noisy': 'STOP-EFFECT', 'R1/noisy': 'STOP-EFFECT'}
    assert R.qualify(lq, {c: 'D' for c in lq}, {c: 'D' for c in lq}) == {'R0/noisy': 'PERSISTENT', 'R1/noisy': 'PERSISTENT'}
    assert R.qualify(lq, {c: 'D' for c in lq}, {c: 'I' for c in lq}) == {'R0/noisy': 'CONFOUNDED', 'R1/noisy': 'CONFOUNDED'} and R.qualify(lq, {c: 'I' for c in lq}, {c: 'E' for c in lq})['R0/noisy'] == 'CONFOUNDED'
    assert R.qualify_summary({}) == 'n/a' and R.qualify_summary({'a': 'STOP-EFFECT', 'b': 'STOP-EFFECT'}) == 'STOP-EFFECT' and R.qualify_summary({'a': 'STOP-EFFECT', 'b': 'PERSISTENT'}) == 'MIXED'
    d = np.array([-1.0 + 0.01 * k for k in range(12)] + [np.nan] * 4); assert R.label_missing(d)['label'] == 'D'                   # exactly 25% missing is allowed
    d = np.array([-1.0 + 0.01 * k for k in range(11)] + [np.nan] * 5); assert R.label_missing(d)['label'] == 'I' and R.label_missing(d)['missing'] > 0.25


def test_reducer_registration_check_on_temporary_record():
    import ca_reduce as R, hashlib
    tmp = tempfile.mkdtemp(); a = os.path.join(tmp, 'ca_reduce.py'); b = os.path.join(tmp, 'trn_same_state_reduce.py'); open(a, 'w').write('x=1\n'); open(b, 'w').write('y=2\n'); rec = os.path.join(tmp, 'REC.txt')
    sh = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest(); files = {'ca_reduce.py': a, 'trn_same_state_reduce.py': b}
    try:
        assert R.check_registration('dev') is True                                           # only the sealed stage is checked
        for text in ('', 'REDUCER_SHA256 %s ca_reduce.py\n' % sh(a), 'REFERENCE_SHA256 %s trn_same_state_reduce.py (bca)\n' % sh(b), 'REDUCER_SHA256 0 ca_reduce.py\nREFERENCE_SHA256 %s trn_same_state_reduce.py\n' % sh(b)):
            open(rec, 'w').write(text)
            try: R.check_registration('confirm', rec_path=rec, files=files)
            except AssertionError: continue
            raise AssertionError('registration must be refused for: %r' % text[:40])
        reg = 'REDUCER_SHA256 %s ca_reduce.py\nREFERENCE_SHA256 %s trn_same_state_reduce.py (bca)\n' % (sh(a), sh(b))
        open(rec, 'w').write(reg)
        try: R.check_registration('confirm', rec_path=rec, files=files); raise AssertionError('a record without CONFIRM_UNSEALED must be refused')
        except AssertionError as e: assert 'CONFIRM_UNSEALED' in str(e), e
        open(rec, 'w').write('CONFIRM_UNSEALED x\n' + reg)                                       # registered AFTER the unseal line: refused (Opus confirm check)
        try: R.check_registration('confirm', rec_path=rec, files=files); raise AssertionError('registration after CONFIRM_UNSEALED must be refused')
        except AssertionError as e: assert 'before the sealed read' in str(e), e
        open(rec, 'w').write(reg + 'CONFIRM_UNSEALED x\n'); assert R.check_registration('confirm', rec_path=rec, files=files) is True
        dg = os.path.join(tmp, 'ca_diag_run.py'); open(dg, 'w').write('z=3\n'); open(rec, 'w').write(reg + 'DIAG_SHA256 %s ca_diag_run.py\nCONFIRM_UNSEALED x\n' % sh(dg))
        assert R.check_registration('confirm', rec_path=rec, files={'ca_diag_run.py': dg}, tags=(('DIAG_SHA256', 'ca_diag_run.py'),)) is True
        open(dg, 'w').write('z=4\n')
        try: R.check_registration('confirm', rec_path=rec, files={'ca_diag_run.py': dg}, tags=(('DIAG_SHA256', 'ca_diag_run.py'),)); raise AssertionError('changed diag runner must be refused')
        except AssertionError as e: assert 'not registered' in str(e), e
    finally: shutil.rmtree(tmp)


def test_synthetic_stop_time_effect_is_qualified_not_called_mechanism():
    """Synthetic data in which OBS-J reaches a HIGHER peak but then falls faster in the noisy cells (the Opus-flagged confound): Q-AUC verdict V-N with qualifier STOP-EFFECT."""
    import ca_reduce as R
    tmp = tempfile.mkdtemp(); root0 = R.ROOT; R.ROOT = tmp; rd = os.path.join(tmp, 'outputs', 'CA', 'fake', 'runs'); os.makedirs(rd); rng = np.random.default_rng(1); W = list(R.GRID)
    try:
        for img in range(10):
            for cond in ('G15', 'AG'):
                for rep in ('R0', 'R1'):
                    for nz in (0, 1):
                        base = 30 + rng.normal(0, 0.3)
                        for arm in ('OBS-J', 'RND-J', 'IND1', 'OBS-I', 'SPA-J'):
                            ps = [base] * 8
                            if arm == 'OBS-J' and nz == 1: ps = [base, base + 1, base + 1, base + .5, base - .5, base - 1, base - 1.5, base - 2]      # higher peak, faster decline
                            ps = [p + rng.normal(0, 0.02) for p in ps]; resid = [3.0, 2.0, 1.5, 1.0, 0.8, 0.8, 0.8, 0.8]
                            json.dump(dict(img=img, cond=cond, rep=rep, noisy=nz, armname=arm, rep_psnr=31.0, level='hi', F0=100.0, trajW=W, trajF=[50.0 - k for k in range(8)], psnr=ps, psnr_edge=[p - 3 for p in ps], psnr_blur=[p + 8 for p in ps], resid=resid,
                                nf=[0.1] * 8 if nz else None, mf=[0.1] * 8 if rep == 'R1' else None, psnr_vs_proj=[p + 5 for p in ps] if rep == 'R1' else None, rej=1, trials=10, stop='budget', wall=1.0, minVF=10.0, match=dict(grad_energy_ratio=0.9)),
                                open(os.path.join(rd, '%d_%s_%s_n%d__%s__P.json' % (img, cond, rep, nz, arm)), 'w'))
        out = R.reduce('fake', 'P'); v = out['verdicts']['RND-J']
        assert v['verdict'] == 'V-N' and v['qualifier_summary'] == 'STOP-EFFECT', v
        assert out['gaps']['RND-J']['peak_cells']['R0/noisy']['label'] == 'E' and out['gaps']['RND-J']['peak_cells']['R0/noisy']['mean'] > 0.5
        assert 'R_eval(data misfit, truth=x_G; secondary)' in out['gaps']['RND-J']['contrasts'] and 'spearman_vs_grad_energy_ratio' in out['dose_response_R_effect']
    finally: R.ROOT = root0; shutil.rmtree(tmp)


def test_verdict_priority_table():
    import ca_reduce as R
    L = lambda f0, n0, f1, n1: {'R0/free': f0, 'R0/noisy': n0, 'R1/free': f1, 'R1/noisy': n1}
    assert R.verdict(L('E', 'E', 'E', 'E'), 0.1) == ('V-NONE', 'STRONG') and R.verdict(L('D', 'D', 'D', 'D'), 0.1)[0] == 'V-OPT'
    assert R.verdict(L('E', 'D', 'E', 'D'), 0.1) == ('V-N', 'STRONG') and R.verdict(L('E', 'E', 'D', 'D'), 0.1) == ('V-R', 'STRONG')
    assert R.verdict(L('I', 'D', 'E', 'D'), 0.1) == ('V-N', 'TENTATIVE') and R.verdict(L('E', 'D', 'I', 'D'), 0.1)[0] == 'V-N' and R.verdict(L('E', 'D', 'I', 'D'), 0.1)[1] == 'TENTATIVE'
    assert R.verdict(L('I', 'E', 'D', 'D'), 0.1) == ('V-R', 'TENTATIVE') and R.verdict(L('E', 'E', 'E', 'I'), 0.1) == ('V-INS', 'TENTATIVE') and R.verdict(L('I', 'I', 'I', 'I'), 0.1) == ('V-INS', 'TENTATIVE')
    assert R.verdict(L('E', 'E', 'E', 'D'), -0.1)[0] == 'V-NR' and R.verdict(L('E', 'E', 'E', 'D'), 0.1)[0] == 'V-INS' and R.verdict(L('E', 'D', 'D', 'D'), 0.1)[0] == 'V-CO'
    assert R.label(-1.0, -1.5, -0.5) == 'D' and R.label(-0.1, -0.2, 0.1) == 'E' and R.label(-0.3, -0.6, 0.2) == 'I'


def test_inconclusive_rule_and_core_hour_cap_smoke():
    import ca_reduce as R, subprocess
    d = tempfile.mkdtemp()
    try:
        assert R.inconclusive_reason('dev', 'P', 3, d) is None, 'rule applies to the sealed stage only'
        assert R.inconclusive_reason('confirm', 'P', R.EXPECTED['P'], d) is None
        assert 'incomplete' in R.inconclusive_reason('confirm', 'S', 700, d) and 'incomplete' in R.inconclusive_reason('confirm', 'X', 63, d)
        open(os.path.join(d, 'CAP_EXCEEDED_P.txt'), 'w').write('x')
        assert 'CAP_EXCEEDED' in R.inconclusive_reason('confirm', 'P', R.EXPECTED['P'], d), 'marker wins even when the count looks complete'
        assert R.inconclusive_reason('confirm', 'S', R.EXPECTED['S'], d) is None, 'marker is per block'
    finally: shutil.rmtree(d)
    assert (R.EXPECTED['P'], R.EXPECTED['S'], R.EXPECTED['X']) == (16 * 4 * 4 * 5, 16 * 4 * 4 * 3, 4 * 4 * 2 * 2)
    src = open(os.path.join(EXP, 'ca_run.py')).read()
    assert "assert a.stage != 'confirm', 'no core-hour cap override" in src and 'CAPS_CORE_H' in src


def test_freeze_helper_fingerprint_consistency_and_chronology():
    import ca_freeze_check as FC
    g1, g2, n = FC.generator_fingerprint(); assert len(g1) == 64 and len(g2) == 64 and n == len(CG.ALLOWED_OPEN) and g1 != g2
    assert FC.generator_fingerprint()[:2] == (g1, g2), 'fingerprint must be deterministic'
    nfit, bad = FC.consistency(); assert nfit >= 11 and bad == [], bad
    ch = FC.chronology(); assert ch[-1].endswith('True'), 'DEV pilot runs must start after the last cached fit: ' + str(ch)
    ln = FC.lines(); keys = [l.split()[0] for l in ln]
    for k in ('MODULE_SHA256', 'ANALYZER_SHA256', 'REDUCER_SHA256', 'REFERENCE_SHA256', 'DIAG_SHA256', 'TEST_SHA256', 'GENERATOR_FINGERPRINT_SRC', 'GENERATOR_FINGERPRINT_IMAGES', 'GENERATOR_CONSISTENCY', 'CHRONOLOGY'): assert k in keys, k
    assert not any(l.startswith(('CONFIRM', 'DEV_DONE')) for l in ln), 'helper must never emit unseal lines'


def test_all_confirm_reducers_check_registration_and_inconclusive():
    import ca_reduce as R
    for fn in (R.reduce, R.reduce_X): src = inspect.getsource(fn); assert 'check_registration(stage)' in src and 'inconclusive_reason(' in src, fn.__name__
    assert 'assert stage != \'confirm\'' in inspect.getsource(R.reduce_A), 'block A reducer must refuse the sealed stage'


def test_sealed_run_refuses_subsetting_and_block_choices_before_the_gate():
    import subprocess
    for extra in (['--blocks', 'P'], ['--blocks', 'P,S'], ['--blocks', 'S,P,X'], ['--blocks', 'P,S,X', '--imgs', '811'], ['--blocks', 'P,S,X', '--conds', 'AG']):
        r = subprocess.run([sys.executable, os.path.join(EXP, 'ca_run.py'), '--stage', 'confirm'] + extra, capture_output=True, text=True)
        assert r.returncode != 0 and 'sealed run: no --imgs/--conds subsetting' in r.stderr, (extra, r.stderr[-300:])
    import ca_diag_run as DR
    assert 'check_registration' in inspect.getsource(DR.load) and 'DIAG_SHA256' in inspect.getsource(DR.load)


if __name__ == '__main__':
    fs = [(k, v) for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]; bad = 0
    for k, f in fs:
        try: f(); print('PASS', k)
        except Exception as e: bad += 1; print('FAIL', k, type(e).__name__, str(e)[:300])
    print('%d/%d passed' % (len(fs) - bad, len(fs))); sys.exit(1 if bad else 0)
