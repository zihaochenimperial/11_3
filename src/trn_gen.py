"""TRN data generator (evaluator/data side). Contract TRN_CONTRACT v1.1 section 2.
Images are mosaics of 32x32 as_gen-recipe tiles (so local statistics, Gaussian density K/N^2 and blur width sb in pixels stay fixed as N grows).
dev-sel 301..312 and dev-chk 313..320 (noise seed 9401); confirm-det 321..344 (seeds 9411,9412) is LOCKED until the freeze record has the analyzer sha and CONFIRM_UNSEALED line, is read by exactly one
registered analyzer process and then consumed; train pool 351..398 (seed 9451); confirm-TRN5 401..424 (seeds 9461,9462) is sealed UNCONDITIONALLY (refused here).
Seed keys use tags 10 (clean image tile) and 11 (noise) -> disjoint from geo_gen tags 0..3 and as_gen seeds 7100+i.
METHOD-SIDE code must never import clean_image_trn (gate V5)."""
import os
import sys
import hashlib
import time
import numpy as np
import as_gen as G

DEV_SEL_IMGS = list(range(301, 313))
DEV_CHK_IMGS = list(range(313, 321))
DEV_IMGS = DEV_SEL_IMGS + DEV_CHK_IMGS
CONFIRM_IMGS = list(range(321, 345))
TRAIN_IMGS = list(range(351, 399))
CONFIRM_TRN5_IMGS = list(range(401, 425))            # sealed unconditionally (TRN-5 appendix, not yet frozen)
DEV_SEEDS = (9401,)
CONFIRM_SEEDS = (9411, 9412)
TRAIN_SEEDS = (9451,)
CONFIRM_TRN5_SEEDS = (9461, 9462)
COND = G.COND
USED_OR_OLD = set(range(1, 25)) | set(range(41, 59)) | set(range(101, 113)) | set(range(201, 225))
TILE = 32
FREEZE_RECORD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contracts', 'TRN_FREEZE_RECORD.txt')
_CONFIRM_SESSION = [False]


def rng_of(*key):
    return np.random.default_rng(np.random.SeedSequence([int(k) for k in key]))


def family_trn(i):
    return ('edge', 'tex', 'mix')[(i - 1) % 3]


def _sha_file(path):
    with open(path, 'rb') as f: return hashlib.sha256(f.read()).hexdigest()


def _confirm_gate():
    """confirm-det read: (1) env TRN_CONFIRM_UNLOCK=1; (2) FREEZE_RECORD exists, has 'CONFIRM_UNSEALED', no 'CONFIRM_CONSUMED' (unless this very process already holds the session);
    (3) the RUNNING analyzer script (sys.modules['__main__'].__file__) has its sha256 registered as an 'ANALYZER_SHA256 <sha> <name>' line. (4) every loaded src/trn_*.py module has a registered 'MODULE_SHA256 <sha> <file>' line. First success appends 'CONFIRM_CONSUMED <utc> <pid> <sha>'."""
    if _CONFIRM_SESSION[0]: return
    assert os.environ.get('TRN_CONFIRM_UNLOCK') == '1', 'confirm-det image: locked (env TRN_CONFIRM_UNLOCK missing)'
    assert os.path.exists(FREEZE_RECORD), 'confirm-det image: locked (no freeze record)'
    rec = open(FREEZE_RECORD, encoding='utf-8').read().splitlines()
    assert any(l.strip().startswith('CONFIRM_UNSEALED') for l in rec), 'confirm-det image: locked (no CONFIRM_UNSEALED line)'
    assert not any(l.strip().startswith('CONFIRM_CONSUMED') for l in rec), 'confirm-det image: already consumed (single use)'
    main = getattr(sys.modules.get('__main__'), '__file__', None)
    assert main and os.path.exists(main), 'confirm-det image: cannot identify the analyzer script'
    sha = _sha_file(main)
    assert any(l.split()[:2] == ['ANALYZER_SHA256', sha] for l in rec if l.strip()), 'confirm-det image: analyzer sha not registered in the freeze record'
    here = os.path.dirname(os.path.abspath(__file__))                                                            # (4) every loaded src/trn_*.py module must match its registered MODULE_SHA256 line (Opus C6)
    for nm, mod in list(sys.modules.items()):
        fpath = getattr(mod, '__file__', None)
        if fpath and os.path.basename(fpath).startswith('trn_') and os.path.dirname(os.path.abspath(fpath)) == here:
            msha = _sha_file(fpath); assert any(l.split()[:3] == ['MODULE_SHA256', msha, os.path.basename(fpath)] for l in rec if l.strip()), 'confirm-det image: loaded module %s not registered/changed' % os.path.basename(fpath)
    with open(FREEZE_RECORD, 'a', encoding='utf-8') as f: f.write('CONFIRM_CONSUMED %s pid=%d sha=%s\n' % (time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), os.getpid(), sha))
    _CONFIRM_SESSION[0] = True


def _gate(i):
    assert i not in CONFIRM_TRN5_IMGS, 'confirm-TRN5 image: sealed unconditionally'
    assert i not in USED_OR_OLD, 'image index belongs to an old/sealed set'
    if i in CONFIRM_IMGS: _confirm_gate()
    else: assert i in DEV_IMGS or i in TRAIN_IMGS, 'image index not allowed'


def _tile(i, a, b):
    rng = rng_of(10, i, a, b); f = (i - 1) % 3
    if f == 0:
        img = G._edge(rng)
    elif f == 1:
        img = 0.5 + 0.45 * G._grating(rng, int(rng.integers(3, 7))) * G._env(rng, 7, 12, 10, 22)
    else:
        img = 0.7 * G._edge(rng, 2, 3) + 0.25 * (1 + G._grating(rng, 2, 3.0, 8.0)) * G._env(rng, 4, 6, 8, 24)
    img = img - min(0.0, float(img.min()))
    return img / max(float(img.max()), 1e-12)


def clean_image_trn(i, N):
    _gate(i); assert N % TILE == 0
    q = N // TILE
    img = np.block([[_tile(i, a, b) for b in range(q)] for a in range(q)])
    return img / img.max()


def noisy_obs_trn(op, x, sn, base, i):
    """y = A x + sn*xi, xi from SeedSequence([11, base, i, N]). Gated like clean_image_trn."""
    _gate(i)
    return op.apply(x) + sn * rng_of(11, base, i, x.shape[0]).standard_normal(x.shape)


def seed_keys(sizes=(32, 64, 96)):
    keys = []
    for i in DEV_IMGS + CONFIRM_IMGS + TRAIN_IMGS + CONFIRM_TRN5_IMGS:
        for N in sizes:
            q = N // TILE; keys += [(10, i, a, b) for a in range(q) for b in range(q)]
    keys += [(11, b, i, N) for b in DEV_SEEDS for i in DEV_IMGS for N in sizes]
    keys += [(11, b, i, N) for b in CONFIRM_SEEDS for i in CONFIRM_IMGS for N in sizes]
    keys += [(11, b, i, N) for b in TRAIN_SEEDS for i in TRAIN_IMGS for N in sizes]
    keys += [(11, b, i, N) for b in CONFIRM_TRN5_SEEDS for i in CONFIRM_TRN5_IMGS for N in sizes]
    return keys
