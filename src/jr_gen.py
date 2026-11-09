"""JR data generator (evaluator/data side). METHOD-SIDE code must never import this module (test: tests/test_jr_core.py).
New image indices and seed tags (20 = clean tile, 21 = noise) disjoint from geo_gen 0..3, as_gen 7100+i, trn_gen 10/11:
  design-smoke 590..592 (calibration/smoke only; never part of tune/verify), tune 501..506, verify 511..522, verify-2 701..712 (both sealed, see _sealed_gate).
  reserved & NOT generated here: train pool 531..578 (stage-2 network), future confirm 601..624 (sealed unconditionally).
Old sealed/used sets (1..24, 41..58, 101..112, 201..224, 301..344 dev+confirm-det, 351..398 train, 401..424 confirm-TRN5) are refused.
PSF conditions are known to the method; noise sigma is fixed per condition set."""
import os
import sys
import time
import numpy as np
import as_gen as G
import jr_op

TUNE_IMGS = list(range(501, 507)); VERIFY_IMGS = list(range(511, 523)); SMOKE_IMGS = list(range(590, 593))
VERIFY2_IMGS = list(range(701, 713))   # sealed (see _sealed_gate)
ALLOWED_OPEN = set(TUNE_IMGS) | set(SMOKE_IMGS)                    # freely readable: tune + design-smoke/dry-run
SEALED = {'VERIFY': set(VERIFY_IMGS), 'VERIFY2': set(VERIFY2_IMGS)}
ALLOWED = ALLOWED_OPEN | SEALED['VERIFY'] | SEALED['VERIFY2']
FREEZE_RECORD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contracts', 'JR_FREEZE_RECORD.txt')
OLD = set(range(1, 25)) | set(range(41, 59)) | set(range(101, 113)) | set(range(201, 225)) | set(range(301, 345)) | set(range(351, 399)) | set(range(401, 425))
assert not (ALLOWED & OLD)
_SESSION = {}


def _sha_file(path):
    import hashlib
    with open(path, 'rb') as f: return hashlib.sha256(f.read()).hexdigest()


def _sealed_gate(name, rec_path=None, environ=None, main_file=None, module_files=None, now=None):
    """Sealed-set read gate (TRN-style, Opus R7). To read the VERIFY (or VERIFY2) images ALL must hold:
    (1) env JR_<name>_UNLOCK=1; (2) the freeze record exists and has 'TUNE_DONE' (VERIFY only) and '<name>_UNSEALED' lines; (3) the RUNNING analyzer script (__main__) has a registered 'ANALYZER_SHA256 <sha> <file>' line and every
    loaded src/jr_*.py module a registered 'MODULE_SHA256 <sha> <file>' line; (4) the number of '<name>_CONSUMED' lines is <= the number of '<name>_RESUME_OK' lines (first read allowed; every later process needs an explicit,
    logged resume line); then a '<name>_CONSUMED <utc> pid sha' line is appended and the process holds the session (forked workers inherit it). Dry runs may only use TUNE or 590-592."""
    if _SESSION.get(name): return
    environ = os.environ if environ is None else environ; rec_path = FREEZE_RECORD if rec_path is None else rec_path
    assert environ.get('JR_%s_UNLOCK' % name) == '1', '%s image: locked (env JR_%s_UNLOCK missing)' % (name, name)
    assert os.path.exists(rec_path), '%s image: locked (no freeze record)' % name
    rec = [l.strip() for l in open(rec_path, encoding='utf-8').read().splitlines() if l.strip()]
    if name == 'VERIFY': assert any(l.startswith('TUNE_DONE') for l in rec), 'VERIFY image: locked (no TUNE_DONE line)'
    assert any(l.startswith(name + '_UNSEALED') for l in rec), '%s image: locked (no %s_UNSEALED line)' % (name, name)
    main = main_file if main_file is not None else getattr(sys.modules.get('__main__'), '__file__', None)
    assert main and os.path.exists(main), '%s image: cannot identify the analyzer script' % name
    sha = _sha_file(main); assert any(l.split()[:2] == ['ANALYZER_SHA256', sha] for l in rec), '%s image: analyzer sha not registered' % name
    here = os.path.dirname(os.path.abspath(__file__))
    if module_files is None:
        module_files = [f for f in (getattr(m, '__file__', None) for m in list(sys.modules.values())) if f and os.path.basename(f).startswith('jr_') and os.path.dirname(os.path.abspath(f)) == here]
    for f in module_files:
        ms = _sha_file(f); assert any(l.split()[:3] == ['MODULE_SHA256', ms, os.path.basename(f)] for l in rec), '%s image: loaded module %s not registered/changed' % (name, os.path.basename(f))
    nc = sum(1 for l in rec if l.startswith(name + '_CONSUMED')); nr = sum(1 for l in rec if l.startswith(name + '_RESUME_OK'))
    assert nc <= nr, '%s image: already consumed (needs a logged %s_RESUME_OK line)' % (name, name)
    with open(rec_path, 'a', encoding='utf-8') as f: f.write('%s_CONSUMED %s pid=%d sha=%s\n' % (name, time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()) if now is None else now, os.getpid(), sha))
    _SESSION[name] = True


def open_sealed(name):
    """Called once by the registered analyzer's parent process before it forks workers."""
    _sealed_gate(name)


TILE = 32
SN = 0.02
PSF = {'G15': ('gauss', dict(s=1.5)), 'AG': ('agauss', dict(smaj=3.0, smin=1.0, th=30.0)), 'MO': ('motion', dict(L=11.0, th=30.0)), 'DK': ('disk', dict(r=3.0))}
PSF_ORDER = ['G15', 'AG', 'MO', 'DK']


def rng_of(*key): return np.random.default_rng(np.random.SeedSequence([int(k) for k in key]))


def _gate(i):
    assert i not in OLD, 'image index belongs to an old/sealed set'
    for name, st in SEALED.items():
        if i in st: _sealed_gate(name); return
    assert i in ALLOWED_OPEN, 'image index not allowed for JR'


def _tile(i, a, b):
    rng = rng_of(20, i, a, b); f = (i - 1) % 3
    if f == 0: img = G._edge(rng)
    elif f == 1: img = 0.5 + 0.45 * G._grating(rng, int(rng.integers(3, 7))) * G._env(rng, 7, 12, 10, 22)
    else: img = 0.7 * G._edge(rng, 2, 3) + 0.25 * (1 + G._grating(rng, 2, 3.0, 8.0)) * G._env(rng, 4, 6, 8, 24)
    img = img - min(0.0, float(img.min())); return img / max(float(img.max()), 1e-12)


def clean_image_jr(i, N):
    _gate(i); assert N % TILE == 0; q = N // TILE
    img = np.block([[_tile(i, a, b) for b in range(q)] for a in range(q)]); return img / img.max()


def make_op(cond, N):
    kind, kw = PSF[cond]; return jr_op.SOp(N, jr_op.psf_taps(kind, **kw))


def noisy_obs_jr(op, x, sn, base, i, cond):
    _gate(i); return op.apply(x) + sn * rng_of(21, base, i, x.shape[0], PSF_ORDER.index(cond)).standard_normal(x.shape)


def psnr(x, ref):
    mse = float(np.mean((x - ref) ** 2)); return 10 * np.log10(1.0 / max(mse, 1e-30))
