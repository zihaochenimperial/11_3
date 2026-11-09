"""JR operator side (method-side safe: contains no image data). General known-PSF blur A as an exact sparse matrix with reflect (half-sample symmetric) boundary.
A x (i,j) = sum_{dy,dx} taps[dy+r,dx+r] * x(refl(i+dy), refl(j+dx)); refl(t) = -t-1 for t<0, 2N-1-t for t>=N (same convention as geo_core.refl_B).
For taps = outer(k,k) of the 1-D normalised Gaussian of geo_core.refl_B this is EXACTLY A = B (x) B (test: tests/test_jr_core.py).
Adjoint is the exact transpose. Cost proxy for one application to one image: 2*nnz(A) flops (stored-matrix product, as in geo_flops F_matvec)."""
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import eigsh


def _gauss1d(s):
    r = max(1, int(np.ceil(3 * s))); t = np.arange(-r, r + 1); k = np.exp(-0.5 * (t / s) ** 2); return k / k.sum()


def psf_taps(kind, **kw):
    """Normalised 2-D tap array (odd side). Kinds: gauss(s) separable (identical to refl_B), agauss(smaj,smin,th deg), motion(L,th deg), disk(r)."""
    if kind == 'gauss':
        k = _gauss1d(kw['s']); return np.outer(k, k)
    if kind == 'agauss':
        smaj, smin, th = kw['smaj'], kw['smin'], np.deg2rad(kw['th']); r = max(1, int(np.ceil(3 * smaj)))
        y, x = np.mgrid[-r:r + 1, -r:r + 1].astype(float); u = np.cos(th) * x + np.sin(th) * y; v = -np.sin(th) * x + np.cos(th) * y
        t = np.exp(-0.5 * ((u / smaj) ** 2 + (v / smin) ** 2)); return t / t.sum()
    if kind == 'motion':
        L, th = kw['L'], np.deg2rad(kw['th']); r = int(np.ceil(L / 2)) + 1; t = np.zeros((2 * r + 1, 2 * r + 1)); ns = int(16 * L)
        for s in (np.arange(ns) + 0.5) / ns - 0.5:
            px, py = r + s * L * np.cos(th), r + s * L * np.sin(th); x0, y0 = int(np.floor(px)), int(np.floor(py)); fx, fy = px - x0, py - y0
            t[y0, x0] += (1 - fx) * (1 - fy); t[y0, x0 + 1] += fx * (1 - fy); t[y0 + 1, x0] += (1 - fx) * fy; t[y0 + 1, x0 + 1] += fx * fy
        return t / t.sum()
    if kind == 'disk':
        rad = kw['r']; r = int(np.ceil(rad)) + 1; ss = 8; o = (np.arange(ss) + 0.5) / ss - 0.5; t = np.zeros((2 * r + 1, 2 * r + 1))
        for iy in range(-r, r + 1):
            for ix in range(-r, r + 1):
                yy, xx = np.meshgrid(iy + o, ix + o, indexing='ij'); t[iy + r, ix + r] = float(np.mean(yy * yy + xx * xx <= rad * rad))
        return t / t.sum()
    raise ValueError(kind)


def _refl(t, N):
    t = np.where(t < 0, -t - 1, t); return np.where(t >= N, 2 * N - 1 - t, t)


class SOp:
    """Sparse exact blur operator on N x N images."""
    def __init__(self, N, taps):
        self.N = N; m = N * N; r = taps.shape[0] // 2; self.rp = r; self.taps = taps
        I, J = np.meshgrid(np.arange(N), np.arange(N), indexing='ij'); rows = (I * N + J).ravel()
        R, C, V = [], [], []
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                w = taps[dy + r, dx + r]
                if w == 0: continue
                R.append(rows); C.append((_refl(I + dy, N) * N + _refl(J + dx, N)).ravel()); V.append(np.full(m, w))
        self.A = sp.csr_matrix((np.concatenate(V), (np.concatenate(R), np.concatenate(C))), shape=(m, m)); self.AT = self.A.T.tocsr()
        self.nnz = int(self.A.nnz); self.flops_apply = 2.0 * self.nnz
        self.normA = float(np.sqrt(eigsh(self.AT @ self.A, k=1, which='LA', return_eigenvectors=False)[0]))

    def apply(self, X): return (self.A @ X.reshape(-1)).reshape(self.N, self.N)

    def adj(self, X): return (self.AT @ X.reshape(-1)).reshape(self.N, self.N)

    def apply_stack(self, Xs):
        p = Xs.shape[0]; return (self.A @ Xs.reshape(p, -1).T).T.reshape(p, self.N, self.N)
