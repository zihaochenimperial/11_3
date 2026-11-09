"""CA data/evaluator side (METHOD-SIDE code must never import this module; test enforces). Contract CA v0 (candidate).
Fresh image indices and seed tags (30 = sharp structured tile, 31 = noise, 32 = K-fit restarts) disjoint from all earlier sets:
  CA-DEV 801..808 (design calibration / pilot only, never evidence), CA-SMOKE 890..892 (pipeline test only), CA-CAL 851..870 (generator calibration of the K-fit representation PSNR only; never run through the methods), CA-CONFIRM 811..826 (sealed, one read),
  reserved & NOT generated here: 831..850, 871..889.
Refused: every index of an earlier set (geo/as/trn/rj/jr: 1..24, 41..58, 101..112, 201..224, 301..398, 401..424, 501..506, 511..522, 531..578, 590..592, 601..624, 701..712)."""
import os, sys, time
import numpy as np
import as_gen as G
import jr_op, jr_core as JC, geo_core as GC

N = 32
DEV_IMGS = list(range(801, 809)); CONFIRM_IMGS = list(range(811, 827)); SMOKE_IMGS = list(range(890, 893)); CAL_IMGS = list(range(851, 871))   # CAL: generator calibration only (representation-PSNR distribution per family); never run through the methods
ALLOWED_OPEN = set(DEV_IMGS) | set(SMOKE_IMGS) | set(CAL_IMGS)
SEALED = {'CONFIRM': set(CONFIRM_IMGS)}
OLD = (set(range(1, 25)) | set(range(41, 59)) | set(range(101, 113)) | set(range(201, 225)) | set(range(301, 345)) | set(range(351, 399)) | set(range(401, 425)) |
       set(range(501, 507)) | set(range(511, 523)) | set(range(531, 579)) | set(range(590, 593)) | set(range(601, 625)) | set(range(701, 713)))
assert not ((ALLOWED_OPEN | SEALED['CONFIRM']) & OLD)
FREEZE_RECORD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contracts', 'CA_FREEZE_RECORD.txt')
_SESSION = {}
SN = 0.02      # common numerical noise scale; objective weight ratio a = 1e-3/SN^2 in EVERY cell (noise-free cells keep SN as the numerical scale, only the data lose the noise term)
PSF = {'G15': ('gauss', dict(s=1.5)), 'AG': ('agauss', dict(smaj=3.0, smin=1.0, th=30.0)), 'MO': ('motion', dict(L=11.0, th=30.0)), 'DK': ('disk', dict(r=3.0))}
PSF_ORDER = ['G15', 'AG', 'MO', 'DK']


def rng_of(*key): return np.random.default_rng(np.random.SeedSequence([int(k) for k in key]))


def _sha_file(path):
    import hashlib
    with open(path, 'rb') as f: return hashlib.sha256(f.read()).hexdigest()


def registered_module_files():
    """Loaded modules that must be sha-registered before the sealed read: every src/ca_*.py and src/jr_*.py plus as_gen.py, geo_core.py, geo_flops.py that lives in the same directory as this file."""
    here = os.path.dirname(os.path.abspath(__file__)); out = []
    for m in list(sys.modules.values()):
        f = getattr(m, '__file__', None)
        if f and os.path.dirname(os.path.abspath(f)) == here and (os.path.basename(f).startswith('ca_') or os.path.basename(f).startswith('jr_') or os.path.basename(f) in ('as_gen.py', 'geo_core.py', 'geo_flops.py')): out.append(f)
    return sorted(set(out))


def _sealed_gate(name, rec_path=None, environ=None, main_file=None, module_files=None, now=None):
    """Same TRN/JR-style gate: env CA_<name>_UNLOCK=1; freeze record has DEV_DONE and '<name>_UNSEALED' (line-start match); running analyzer (__main__) and loaded src/ca_*.py, src/jr_*.py, as_gen.py, geo_core.py, geo_flops.py registered by sha
    ('ANALYZER_SHA256 <sha> <file>' / 'MODULE_SHA256 <sha> <file>'); number of '<name>_CONSUMED' lines <= number of '<name>_RESUME_OK' lines; then a CONSUMED line is appended. Dry runs only DEV/SMOKE."""
    if _SESSION.get(name): return
    environ = os.environ if environ is None else environ; rec_path = FREEZE_RECORD if rec_path is None else rec_path
    assert environ.get('CA_%s_UNLOCK' % name) == '1', '%s images: locked (env CA_%s_UNLOCK missing)' % (name, name)
    assert os.path.exists(rec_path), '%s images: locked (no freeze record)' % name
    rec = [l.strip() for l in open(rec_path, encoding='utf-8').read().splitlines() if l.strip()]
    assert any(l.startswith('DEV_DONE') for l in rec), '%s images: locked (no DEV_DONE line)' % name
    assert any(l.startswith(name + '_UNSEALED') for l in rec), '%s images: locked (no %s_UNSEALED line)' % (name, name)
    main = main_file if main_file is not None else getattr(sys.modules.get('__main__'), '__file__', None)
    assert main and os.path.exists(main), '%s images: cannot identify the analyzer script' % name
    sha = _sha_file(main); assert any(l.split()[:2] == ['ANALYZER_SHA256', sha] for l in rec), '%s images: analyzer sha not registered' % name
    if module_files is None: module_files = registered_module_files()
    for f in module_files:
        ms = _sha_file(f); assert any(l.split()[:3] == ['MODULE_SHA256', ms, os.path.basename(f)] for l in rec), '%s images: loaded module %s not registered/changed' % (name, os.path.basename(f))
    nc = sum(1 for l in rec if l.startswith(name + '_CONSUMED')); nr = sum(1 for l in rec if l.startswith(name + '_RESUME_OK'))
    assert nc <= nr, '%s images: already consumed (needs a logged %s_RESUME_OK line)' % (name, name)
    with open(rec_path, 'a', encoding='utf-8') as f: f.write('%s_CONSUMED %s pid=%d sha=%s\n' % (name, time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()) if now is None else now, os.getpid(), sha))
    _SESSION[name] = True


def open_sealed(name): _sealed_gate(name)


def _gate(i):
    assert i not in OLD, 'image index belongs to an old/sealed set'
    for name, st in SEALED.items():
        if i in st: _sealed_gate(name); return
    assert i in ALLOWED_OPEN, 'image index not allowed for CA'


# ------------------------------------------------------------------ sharp structured (non-Gaussian) tiles
def _line(rng, x0, y0, ang, length, width, amp):
    """Thin straight line segment: Gaussian profile across (sd=width px), smooth (sd 1 px) end caps; returns amp * profile on the N x N grid (pixel-centre sampled at 4x supersampling)."""
    ss = 4; g = (np.arange(N * ss) + 0.5) / ss; X, Y = np.meshgrid(g, g, indexing='xy')
    c, s = np.cos(ang), np.sin(ang); u = (X - x0) * c + (Y - y0) * s; v = -(X - x0) * s + (Y - y0) * c
    prof = np.exp(-0.5 * (v / width) ** 2) * 0.5 * (np.tanh((u + length / 2) / 1.0) - np.tanh((u - length / 2) / 1.0))
    return amp * prof.reshape(N, ss, N, ss).mean((1, 3))


def _tile_lines(rng, hi=False):
    img = np.full((N, N), 0.08); nl = int(rng.integers(14, 19)) if hi else int(rng.integers(2, 5)); ang0 = rng.uniform(0, np.pi)
    for k in range(nl):                                         # a "double line": two near-parallel thin lines 1.8..5 px apart (blur makes them look like one wide line)
        cx, cy = rng.uniform(4, 28, 2); L = rng.uniform(7, 15) if hi else rng.uniform(10, 20); w = rng.uniform(0.5, 0.8) if hi else rng.uniform(0.7, 1.2); a = rng.uniform(0.5, 1.0)
        ang = ang0 + rng.uniform(-0.5, 0.5) if not hi else rng.uniform(0, np.pi); d = rng.uniform(1.8, 4.5) if hi else rng.uniform(2.2, 5.0); nx, ny = -np.sin(ang), np.cos(ang)
        img += _line(rng, cx + nx * d / 2, cy + ny * d / 2, ang, L, w, a) + _line(rng, cx - nx * d / 2, cy - ny * d / 2, ang, L, w, a)
    for k in range(int(rng.integers(1, 3))):                    # plus single thin and wide lines
        cx, cy = rng.uniform(6, 26, 2); img += _line(rng, cx, cy, rng.uniform(0, np.pi), rng.uniform(8, 18), rng.uniform(0.8, 2.2), rng.uniform(0.4, 0.9))
    return img


def _confetti(rng, n_lo, n_hi):
    """Many small high-contrast polygons (3..6 vertices, radius 2.5..6 px) over the soft gradient of G._edge: long edge length per unit area -> hard for K=36 Gaussians."""
    ang = rng.uniform(0, 2 * np.pi); ux, uy = np.meshgrid(np.arange(N) + .5, np.arange(N) + .5, indexing='xy')
    img = 0.12 + 0.15 * ((ux - N / 2) * np.cos(ang) + (uy - N / 2) * np.sin(ang)) / N
    for _ in range(int(rng.integers(n_lo, n_hi + 1))):
        cx, cy = rng.uniform(3, 29, 2); nv = int(rng.integers(3, 7)); R = rng.uniform(2.5, 6.0); a = np.sort(rng.uniform(0, 2 * np.pi, nv)); rad = R * rng.uniform(0.6, 1.0, nv)
        vx = cx + rad * np.cos(a); vy = cy + rad * np.sin(a); inside = np.zeros_like(G._GX, dtype=bool)
        with np.errstate(divide='ignore', invalid='ignore'):
            for k in range(nv):
                x1, y1, x2, y2 = vx[k], vy[k], vx[(k + 1) % nv], vy[(k + 1) % nv]
                inside ^= ((y1 > G._GY) != (y2 > G._GY)) & (G._GX < (x2 - x1) * (G._GY - y1) / (y2 - y1) + x1)
        m = G._down(inside.astype(float)); img = img * (1 - m) + rng.uniform(0.2, 1.0) * m
    return img


def level_of(i): return 'lo' if i in (801, 802, 890) else 'hi'     # complexity stratum: lo = JR-like (documents near-exact representability), hi = denser/finer structure (target: K=36 representation PSNR 27..32 dB); all CONFIRM tiles are hi


def sharp_image(i):
    """Sharp structured (non-Gaussian) N x N tile of index i, peak 1. Family f = (i-1) % 4: edge, grating*envelope, lines, edge+grating; stratum level_of(i)."""
    _gate(i); rng = rng_of(30, i); f = (i - 1) % 4; hi = level_of(i) == 'hi'
    if f == 0: img = _confetti(rng, 11, 16) if hi else G._edge(rng)
    elif f == 1: img = 0.5 + 0.45 * G._grating(rng, int(rng.integers(5, 9)), 4.0, 10.0) * G._env(rng, 11, 18, 12, 20) if hi else 0.5 + 0.45 * G._grating(rng, int(rng.integers(3, 7))) * G._env(rng, 7, 12, 10, 22)
    elif f == 2: img = _tile_lines(rng, hi)
    else: img = 0.6 * G._edge(rng, 9, 13) + 0.3 * (1 + G._grating(rng, 6, 5.0, 11.0)) * G._env(rng, 9, 14, 8, 24) if hi else 0.7 * G._edge(rng, 2, 3) + 0.25 * (1 + G._grating(rng, 2, 3.0, 8.0)) * G._env(rng, 4, 6, 8, 24)
    img = img - min(0.0, float(img.min())); return img / max(float(img.max()), 1e-12)


def psnr(x, ref):
    mse = float(np.mean((x - ref) ** 2)); return 10 * np.log10(1.0 / max(mse, 1e-30))


# ------------------------------------------------------------------ strong K-Gaussian fit of the SHARP image (identity operator; representation-error estimate)
def _starts(x, K, rng, n_rand):
    q = int(round(np.sqrt(K))); c = [N * (j + 0.5) / q for j in range(q)]; sp = N / q; out = []
    for sc in (0.5, 0.35, 0.7):
        th = np.array([[1.0, a, b, np.log(sp * sc), 0.0, np.log(sp * sc)] for b in c for a in c]); out.append(th)
    for _ in range(n_rand):      # image-mass-weighted random centres, random scales
        p = (x + 1e-3).ravel() / (x + 1e-3).sum(); idx = rng.choice(N * N, K, replace=False, p=p); cy, cx = np.divmod(idx, N)
        s = rng.uniform(0.8, 2.5, K); th = np.stack([np.ones(K), cx + .5 + rng.normal(0, .3, K), cy + .5 + rng.normal(0, .3, K), np.log(s), np.zeros(K), np.log(s)], 1); out.append(th)
    return out


def kfit(x_sharp, K=36, i=0, n_rand=5, W_cap=1.0e10, kap0=0.03, max_sweeps=400):
    """Best K-Gaussian approximation of the sharp tile (strong multi-start single-primitive Gauss-Newton with the exact same engine/objective as the experiment, A = I, ridge 0).
    Returns dict(theta, x, psnr_rep, per_start psnr list). The result is an UPPER bound on the true best-K error (non-convex fit); the per-start spread reports how far the solver is from saturation."""
    op = jr_op.SOp(N, np.ones((1, 1))); P = JC.JProb(N, op, x_sharp.copy(), SN, 0.0); res = []; rng = rng_of(32, i)
    for th0 in _starts(x_sharp, K, rng, n_rand):
        cols = [P.render(p.reshape(1, 6)).ravel() for p in th0]; th0 = th0.copy(); th0[:, 0] = np.linalg.lstsq(np.stack(cols, 1), x_sharp.ravel(), rcond=None)[0]
        o = JC.jr_solve(P, th0, dict(arm='IND1', mode='joint', gs=1, kappa0=kap0, f=3, seed=0, R=1, ridge=1.0), max_sweeps=max_sweeps, W_cap=W_cap)
        xh = GC.render(o['theta'], N); res.append((psnr(xh, x_sharp), o['theta'], xh))
    b = max(res, key=lambda r: r[0]); return dict(theta=b[1], x=b[2], psnr_rep=b[0], starts=[r[0] for r in res])


# ------------------------------------------------------------------ cells: truth images, observation with paired noise
def make_op(cond): kind, kw = PSF[cond]; return jr_op.SOp(N, jr_op.psf_taps(kind, **kw))


def noise_of(i, cond): return SN * rng_of(31, i, PSF_ORDER.index(cond)).standard_normal((N, N))      # the SAME eps for R0 and R1 of an image/PSF; noise-free cells use eps = 0


def observe(op, x_true, noisy, i, cond):
    eps = noise_of(i, cond) if noisy else np.zeros((N, N)); return op.apply(x_true) + eps, eps


def get_fit(i, cache_dir, K=36):
    """K-Gaussian projection of the sharp tile i (cached; deterministic seeds). Returns dict(theta, x, psnr_rep, starts)."""
    import json
    p = os.path.join(cache_dir, 'fit_%d.json' % i)
    if os.path.exists(p):
        d = json.load(open(p)); d['theta'] = np.array(d['theta']); d['x'] = np.array(d['x']); return d
    xs = sharp_image(i); r = kfit(xs, K=K, i=i); os.makedirs(cache_dir, exist_ok=True)
    json.dump(dict(theta=r['theta'].tolist(), x=r['x'].tolist(), psnr_rep=r['psnr_rep'], starts=r['starts'], level=level_of(i), family=(i - 1) % 4), open(p, 'w')); return r
