"""AS contract v2.1 image generator (numpy only; non-Gaussian procedural 32x32 images, peak 1). Image i in 1..24 uses rng seed 7100+i.
Families: 1-8 G_edge, 9-16 G_tex, 17-24 G_mix. Noise: y = A x_clean + sn * xi, xi ~ N(0,1) from rng seed noise_seed*1000+i (noise_seed in {9001,9002}).
Evaluator/data-side module: the clean image is returned here and must only be consumed by the evaluator (as_analyze / oracle_x)."""
import numpy as np

N = 32
_SS = (np.arange(4) + 0.5) / 4          # 4x4 supersampling


def _grid():
    ys = (np.arange(N)[:, None] + _SS[None, :]).ravel(); xs = ys.copy()
    return np.meshgrid(xs, ys, indexing='xy')     # X[i,j]=xs[j], Y[i,j]=ys[i]; (4N x 4N)


_GX, _GY = _grid()


def _down(m):
    return m.reshape(N, 4, N, 4).mean(axis=(1, 3))


def _halfplane(rng):
    th = rng.uniform(0, 2 * np.pi); c = rng.uniform(-8, 8)
    return _down(((_GX - N / 2) * np.cos(th) + (_GY - N / 2) * np.sin(th) > c).astype(float))


def _polygon(rng):
    cx, cy = rng.uniform(6, 26, 2); nv = int(rng.integers(3, 7)); R = rng.uniform(4, 11)
    ang = np.sort(rng.uniform(0, 2 * np.pi, nv)); rad = R * rng.uniform(0.6, 1.0, nv)
    vx = cx + rad * np.cos(ang); vy = cy + rad * np.sin(ang)
    inside = np.zeros_like(_GX, dtype=bool)          # even-odd ray casting (handles non-convex)
    with np.errstate(divide='ignore', invalid='ignore'):
        for k in range(nv):
            x1, y1, x2, y2 = vx[k], vy[k], vx[(k + 1) % nv], vy[(k + 1) % nv]
            cond = ((y1 > _GY) != (y2 > _GY)) & (_GX < (x2 - x1) * (_GY - y1) / (y2 - y1) + x1)
            inside ^= cond
    return _down(inside.astype(float))


def _edge(rng, nmin=3, nmax=6):
    ang = rng.uniform(0, 2 * np.pi); ux, uy = np.meshgrid(np.arange(N) + .5, np.arange(N) + .5, indexing='xy')
    img = 0.12 + 0.15 * ((ux - N / 2) * np.cos(ang) + (uy - N / 2) * np.sin(ang)) / N
    for _ in range(int(rng.integers(nmin, nmax + 1))):
        m = _halfplane(rng) if rng.random() < 0.35 else _polygon(rng)
        img = img * (1 - m) + rng.uniform(0.2, 1.0) * m
    return img


def _grating(rng, n, fmin=2.0, fmax=7.0):
    ux, uy = np.meshgrid(np.arange(N) + .5, np.arange(N) + .5, indexing='xy'); t = np.zeros((N, N))
    for _ in range(n):
        k = 2 * np.pi * rng.uniform(fmin, fmax) / N; ph = rng.uniform(0, 2 * np.pi); a = rng.uniform(0.5, 1.0); phi = rng.uniform(0, np.pi)
        t += a * np.sin(k * (ux * np.cos(phi) + uy * np.sin(phi)) + ph)
    return t / (np.max(np.abs(t)) + 1e-12)


def _env(rng, smin, smax, lo=8, hi=24):
    ux, uy = np.meshgrid(np.arange(N) + .5, np.arange(N) + .5, indexing='xy'); cx, cy = rng.uniform(lo, hi, 2); s = rng.uniform(smin, smax)
    return np.exp(-0.5 * ((ux - cx) ** 2 + (uy - cy) ** 2) / s ** 2)


def clean_image(i):
    rng = np.random.default_rng(7100 + i)
    if i <= 8:
        img = _edge(rng)
    elif i <= 16:
        img = 0.5 + 0.45 * _grating(rng, int(rng.integers(3, 7))) * _env(rng, 7, 12, 10, 22)
    else:
        img = 0.7 * _edge(rng, 2, 3) + 0.25 * (1 + _grating(rng, 2, 3.0, 8.0)) * _env(rng, 4, 6, 8, 24)
    img = img - min(0.0, float(img.min()))
    return img / img.max()


def family(i):
    return 'edge' if i <= 8 else ('tex' if i <= 16 else 'mix')


def noisy_obs(op, x, sn, noise_seed, i):
    rng = np.random.default_rng(noise_seed * 1000 + i)
    return op.apply(x) + sn * rng.standard_normal((N, N))


COND = {'C1': (1.0, 0.01), 'C2': (1.0, 0.03), 'C3': (2.0, 0.01), 'C4': (2.0, 0.03)}
