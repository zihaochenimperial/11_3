"""CA freeze helper (not an analyzer). Prints the gate-format registration lines (no timestamp prefix) for the freeze record and REHEARSES the sealed gate on a COPY of the record.
usage: python3 experiments/ca_freeze_check.py lines            -> prints MODULE_SHA256/ANALYZER_SHA256/REDUCER_SHA256/TEST_SHA256/REFERENCE_SHA256 lines for the current files
       python3 experiments/ca_freeze_check.py rehearse          -> copies contracts/CA_FREEZE_RECORD.txt to a temp file, runs ca_gen._sealed_gate('CONFIRM') against the copy with the exact module set the real run will load; reports PASS/FAIL; never touches the real record or any CONFIRM image."""
import os, sys, hashlib, tempfile, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..'); SRC = os.path.join(ROOT, 'src'); sys.path.insert(0, SRC); sys.path.insert(0, HERE)
MODS = ['as_gen.py', 'ca_diag.py', 'ca_gen.py', 'geo_core.py', 'geo_flops.py', 'jr_core.py', 'jr_op.py']
ANALYZER = os.path.join(HERE, 'ca_run.py')


def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def lines():
    out = []
    for m in MODS:
        p = os.path.join(SRC, m)
        if os.path.exists(p): out.append('MODULE_SHA256 %s %s' % (sha(p), m))
    out.append('ANALYZER_SHA256 %s ca_run.py' % sha(ANALYZER))
    out.append('REDUCER_SHA256 %s ca_reduce.py' % sha(os.path.join(HERE, 'ca_reduce.py')))
    out.append('REFERENCE_SHA256 %s trn_same_state_reduce.py (bca)' % sha(os.path.join(HERE, 'trn_same_state_reduce.py')))
    out.append('DIAG_SHA256 %s ca_diag_run.py' % sha(os.path.join(HERE, 'ca_diag_run.py')))
    out.append('TEST_SHA256 %s tests/test_ca.py' % sha(os.path.join(ROOT, 'tests', 'test_ca.py')))
    g1, g2, n = generator_fingerprint(); out.append('GENERATOR_FINGERPRINT_SRC %s (functions %s)' % (g1, ','.join(GEN_FUNCS))); out.append('GENERATOR_FINGERPRINT_IMAGES %s (open index sets, n=%d)' % (g2, n))
    n, bad = consistency(); out.append('GENERATOR_CONSISTENCY cached_fits=%d inconsistent=%d' % (n, len(bad)))
    out.extend(chronology())
    return out


GEN_FUNCS = ['_line', '_tile_lines', '_confetti', 'level_of', 'sharp_image', '_starts', 'kfit', 'noise_of', 'observe', 'make_op', 'psnr']


def generator_fingerprint():
    """R7: (a) sha256 of the source text of the sharp-tile / K-fit / noise generator functions (stable against later edits of the gate code); (b) sha256 of the generated open images (DEV, SMOKE, CAL; never CONFIRM)."""
    import inspect, numpy as np, ca_gen as CG
    src = ''.join(inspect.getsource(getattr(CG, f)) for f in GEN_FUNCS); h2 = hashlib.sha256()
    for i in sorted(CG.ALLOWED_OPEN): h2.update(np.ascontiguousarray(CG.sharp_image(i), dtype=np.float64).tobytes())
    return hashlib.sha256(src.encode()).hexdigest(), h2.hexdigest(), len(CG.ALLOWED_OPEN)


def consistency():
    """R7 proof: every cached DEV/SMOKE K-fit was produced from the CURRENT sharp-tile generator (psnr_rep equals the PSNR of its render against sharp_image(i) now)."""
    import glob, json, numpy as np, ca_gen as CG
    bad = []; n = 0
    for st in ('dev', 'smoke'):
        for f in sorted(glob.glob(os.path.join(ROOT, 'outputs', 'CA', st, 'fits', 'fit_*.json'))):
            i = int(os.path.basename(f)[4:-5]); d = json.load(open(f)); n += 1
            if abs(CG.psnr(np.array(d['x']), CG.sharp_image(i)) - d['psnr_rep']) > 1e-6: bad.append(f)
    return n, bad


def chronology():
    """R7: container file mtimes (UTC) of the cached fits and of the first/last DEV block-P pilot run, so that 'pilot started after the fits' is checkable; measured, not asserted."""
    import glob
    fz = lambda g: sorted(os.path.getmtime(f) for f in glob.glob(os.path.join(ROOT, 'outputs', 'CA', *g)))
    t = lambda x: __import__('time').strftime('%Y-%m-%dT%H:%M:%SZ', __import__('time').gmtime(x))
    fits = fz(['dev', 'fits', 'fit_*.json']); runs = fz(['dev', 'runs', '*__P.json'])
    return ['CHRONOLOGY dev_fits_first %s last %s (n=%d)' % (t(fits[0]), t(fits[-1]), len(fits)), 'CHRONOLOGY dev_pilot_blockP_runs_first %s last %s (n=%d)' % (t(runs[0]), t(runs[-1]), len(runs)),
            'CHRONOLOGY pilot_first_run_after_last_fit %s' % (runs[0] > fits[-1])]


def rehearse():
    import importlib
    rec = os.path.join(ROOT, 'contracts', 'CA_FREEZE_RECORD.txt'); assert os.path.exists(rec), 'no freeze record yet'
    tmp = tempfile.mkdtemp(); cp = os.path.join(tmp, 'REC_COPY.txt'); shutil.copy(rec, cp)
    # load exactly the modules the real run loads: import the analyzer's dependencies the same way ca_run does (ca_gen -> as_gen, jr_op, jr_core, geo_core, ...)
    import ca_gen as CG, ca_diag, geo_core, jr_core, jr_op, as_gen, geo_flops
    here = os.path.dirname(os.path.abspath(CG.__file__))
    mods = [f for f in (getattr(m, '__file__', None) for m in list(sys.modules.values())) if f and (os.path.basename(f).startswith('ca_') or os.path.basename(f).startswith('jr_') or os.path.basename(f) in ('as_gen.py', 'geo_core.py', 'geo_flops.py')) and os.path.dirname(os.path.abspath(f)) == here]
    CG._SESSION.clear()
    try:
        CG._sealed_gate('CONFIRM', rec_path=cp, environ={'CA_CONFIRM_UNLOCK': '1'}, main_file=ANALYZER, module_files=mods, now='REHEARSAL')
        ok = 'CONFIRM_CONSUMED' in open(cp).read() and 'CONFIRM_CONSUMED' not in open(rec).read().replace('CONFIRM_CONSUMED_REHEARSAL', '')
        print('REHEARSAL PASS: gate accepts the record copy for analyzer ca_run.py and modules %s; CONSUMED appended to the copy only: %s' % (sorted(os.path.basename(m) for m in mods), ok))
    except AssertionError as e: print('REHEARSAL FAIL:', e); sys.exit(1)
    finally: shutil.rmtree(tmp)


if __name__ == '__main__':
    if sys.argv[1] == 'lines': print('\n'.join(lines()))
    else: rehearse()
