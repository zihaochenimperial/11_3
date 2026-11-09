"""CA diagnostic side (E-B): finite structural ambiguity of KNOWN constructed alternatives and of the fitted-truth Gaussian groups. Evaluator/diagnostic code (it knows both alternatives); the method side never imports it.
Definitions (whitened, sigma = SN):  D_img = ||x0 - x1|| / sigma  (sharp-image difference in noise units),  d = ||A (x0 - x1)|| / sigma  (blurred, whitened mean distance of two simple hypotheses),
Bayes error of two equal-prior simple hypotheses with known covariance sigma^2 I = Phi(-d/2). A pair is 'finitely ambiguous' iff D_img >= D_MIN_REL * ||x0||/sigma AND d <= D_THR."""
import numpy as np
from math import erf, sqrt
import geo_core as GC

N = 32
SN = 0.02
D_THR = 3.0            # Phi(-1.5) = 6.7 % Bayes error
D_MIN_REL = 0.15       # structural difference must be >= 15 % of the reference image norm
TOL_J = 1e-6           # relative singular value below which a render-Jacobian direction counts as render-null (gauge)


def Phi(z): return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def bayes_error(d): return Phi(-d / 2.0)


def theta_of(w, mx, my, sa, sc, phi):
    """Gaussian with std sa along direction phi (rad), sc across; covariance R diag(sa^2, sc^2) R^T -> (w, mx, my, log L11, L21, log L22) of geo_core."""
    c, s = np.cos(phi), np.sin(phi); R = np.array([[c, -s], [s, c]]); S = R @ np.diag([sa ** 2, sc ** 2]) @ R.T
    return np.concatenate([[w, mx, my], GC.chol_from_sigma(S)])


def line_pair(sw=1.5, s=1.5, phi=0.0, cx=16.0, cy=16.0, sa=6.0, w1=1.0):
    """Single wide line (std sw across) vs two thin lines at +-s/2 across with matched mass, centroid and across-variance: st^2 + (s/2)^2 = sw^2 (needs s < 2 sw)."""
    assert 0 < s < 2 * sw; st = np.sqrt(sw ** 2 - (s / 2) ** 2); nx, ny = -np.sin(phi), np.cos(phi)
    one = theta_of(w1, cx, cy, sa, sw, phi)[None]
    two = np.stack([theta_of(w1 * sw / (2 * st), cx + nx * s / 2, cy + ny * s / 2, sa, st, phi), theta_of(w1 * sw / (2 * st), cx - nx * s / 2, cy - ny * s / 2, sa, st, phi)])
    return one, two


def measures(op, x0, x1, sigma=SN):
    dimg = float(np.linalg.norm(x0 - x1)) / sigma; d = float(np.linalg.norm(op.apply(x0 - x1))) / sigma; ref = float(np.linalg.norm(x0)) / sigma
    return dict(Dimg=dimg, d=d, rel=dimg / max(ref, 1e-300), hide=d / max(dimg, 1e-300), err=bayes_error(d), amb=bool(dimg >= D_MIN_REL * ref and d <= D_THR))


def tangent_basis(th):
    """Orthonormal basis (columns) of the image tangent space of the primitives th (render-null / gauge directions removed) and the number removed."""
    J = GC.render_jac(th, N)[1].reshape(6 * th.shape[0], -1).T; U, sv, _ = np.linalg.svd(J, full_matrices=False)
    keep = sv > TOL_J * max(sv.max(), 1e-300); return U[:, keep], int((~keep).sum())


def obs_spectrum(op, U, sigma=SN, Pn=None):
    """Whitened observability of a unit-norm image-tangent basis: s_i = ||A u_i||/sigma, ascending; with Pn (orthonormal basis of neighbours' observed tangent space) the neighbours may compensate: s_i = ||(I - Pn Pn^T) A u_i||/sigma."""
    AU = op.A @ U
    if Pn is not None: AU = AU - Pn @ (Pn.T @ AU)
    return np.sort(np.linalg.norm(AU, axis=0) / sigma)


def neighbour_basis(op, thN):
    if thN is None or len(thN) == 0: return None
    U, _ = tangent_basis(thN); AU = op.A @ U; Q, sv, _ = np.linalg.svd(AU, full_matrices=False); return Q[:, sv > 1e-8 * max(sv.max(), 1e-300)]


def weakest_single_vs_group(op, th_group, thN=None):
    """Weakest whitened observability (a) of each member taken alone with its own 6 columns, (b) of the group tangent space (gauge removed) with fixed neighbours, (c) with neighbours refit (Schur/projection)."""
    singles = [float(obs_spectrum(op, tangent_basis(th_group[k:k + 1])[0])[0]) for k in range(len(th_group))]
    Ug, ngauge = tangent_basis(th_group); fixed = obs_spectrum(op, Ug); Pn = neighbour_basis(op, thN); refit = obs_spectrum(op, Ug, Pn=Pn) if Pn is not None else fixed
    return dict(single_min=singles, group_fixed=fixed, group_refit=refit, n_gauge=ngauge, n_tangent=Ug.shape[1])


def linear_vs_finite(op, th, direction_fn, lams, sigma=SN):
    """Compare ||A J dth||/sigma (linear) and ||A (x(th+dth) - x(th))||/sigma (finite) along th + lam*direction."""
    Jm = GC.render_jac(th, N)[1].reshape(6 * th.shape[0], -1).T; x = GC.render(th, N); out = []
    for lam in lams:
        dth = direction_fn(th) * lam; lin = float(np.linalg.norm(op.A @ (Jm @ dth.ravel()))) / sigma; fin = float(np.linalg.norm(op.apply(GC.render(th + dth, N) - x))) / sigma; out.append((lam, lin, fin))
    return out


# ------------------------------------------------------------------ instance-level merge alternatives (exploratory covariate on R0 truths)
def sigma_of(th):
    L11, L22 = np.exp(th[3]), np.exp(th[5]); L = np.array([[L11, 0.0], [th[4], L22]]); return L @ L.T


def mass_of(th): return float(th[0]) * 2 * np.pi * np.sqrt(max(np.linalg.det(sigma_of(th)), 1e-300))


def merge_pair(a, b):
    """Moment-matched single Gaussian replacing the two (mass = w * 2 pi sqrt(det Sigma); mean and covariance matched with mass weights). Returns theta (6,)."""
    ma, mb = mass_of(a), mass_of(b); M = ma + mb; ca, cb = np.asarray(a[1:3], float), np.asarray(b[1:3], float); c = (ma * ca + mb * cb) / M
    Sa, Sb = sigma_of(a), sigma_of(b); S = (ma * (Sa + np.outer(ca - c, ca - c)) + mb * (Sb + np.outer(cb - c, cb - c))) / M
    w = M / (2 * np.pi * np.sqrt(np.linalg.det(S))); return np.concatenate([[w, c[0], c[1]], GC.chol_from_sigma(S)])


def merge_load(op, th, max_dist=6.0, sigma=SN):
    """For every pair of primitives with centre distance <= max_dist: structural change D_img and observation change d when the pair is replaced by its moment-matched single Gaussian (neighbours fixed;
    the difference only involves the pair, so D_img and d are pair-local). 'rel' = ||x_pair - x_merged|| / ||x_pair|| (pair-local reference, the whole-image norm would hide local structure);
    amb iff rel >= D_MIN_REL and d <= D_THR. Only pairs of positive-weight primitives are merged (the model class has signed weights; signed merges are skipped and counted). Returns (rows, number of ambiguous merges, number of skipped pairs)."""
    rows = []; skipped = 0
    for i in range(len(th)):
        for j in range(i + 1, len(th)):
            dist = float(np.hypot(th[i, 1] - th[j, 1], th[i, 2] - th[j, 2]))
            if dist > max_dist: continue
            if th[i, 0] <= 0 or th[j, 0] <= 0: skipped += 1; continue                 # signed (negative-weight) primitives: a moment-matched single Gaussian is not defined -> skipped and counted
            try: m = merge_pair(th[i], th[j])
            except np.linalg.LinAlgError: skipped += 1; continue
            xa = GC.render(th[[i, j]], N); xm = GC.render(m[None], N)
            r = measures(op, xa, xm, sigma); r.update(i=i, j=j, dist=dist); rows.append(r)
    return rows, int(sum(r['amb'] for r in rows)), skipped
