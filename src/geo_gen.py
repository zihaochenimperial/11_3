"""GEO data generator (evaluator/data side). New images disjoint from S2 (1-24) and sealed E41-58.
dev = 101..112 (noise seed 9101); held-out = 201..224 (noise seeds 9201, 9202); cost-scaling synthetic targets use seed 9301.
Family of image i: ((i-1) mod 3) -> 0 edge, 1 tex, 2 mix; every stream is a SeedSequence([tag, ...]) (contract v2 C10):
tag 0 = clean image (0,i); tag 1 = noise (1,base,i) shared by the four conditions; tag 2 = F_ref restarts (2,base,i,restart); tag 3 = ladder target (3,N,K).
Family recipes copied from as_gen.clean_image.
METHOD-SIDE code must never import this module's clean_image_geo / ladder_target (gate V5)."""
import numpy as np
import as_gen as G

N32 = 32
DEV_IMGS = list(range(101, 113))
TEST_IMGS = list(range(201, 225))
DEV_SEEDS = (9101,)
TEST_SEEDS = (9201, 9202)
LADDER_SEED = 9301
COND = G.COND                     # {'C1': (1.0, 0.01), 'C2': (1.0, 0.03), 'C3': (2.0, 0.01), 'C4': (2.0, 0.03)}
SEALED_OR_USED = set(range(1, 25)) | set(range(41, 59))


def rng_of(*key):
    return np.random.default_rng(np.random.SeedSequence([int(k) for k in key]))


def seed_keys():
    """All (tag, ...) keys used by this experiment, for the V5 disjointness assertion."""
    keys = [(0, i) for i in DEV_IMGS + TEST_IMGS]
    keys += [(1, b, i) for b in DEV_SEEDS for i in DEV_IMGS] + [(1, b, i) for b in TEST_SEEDS for i in TEST_IMGS]
    return keys


def family_geo(i):
    return ('edge', 'tex', 'mix')[(i - 1) % 3]


def clean_image_geo(i):
    assert i not in SEALED_OR_USED and (i in DEV_IMGS or i in TEST_IMGS), 'image index not allowed'
    rng = rng_of(0, i)
    f = (i - 1) % 3
    if f == 0:
        img = G._edge(rng)
    elif f == 1:
        img = 0.5 + 0.45 * G._grating(rng, int(rng.integers(3, 7))) * G._env(rng, 7, 12, 10, 22)
    else:
        img = 0.7 * G._edge(rng, 2, 3) + 0.25 * (1 + G._grating(rng, 2, 3.0, 8.0)) * G._env(rng, 4, 6, 8, 24)
    img = img - min(0.0, float(img.min()))
    return img / img.max()


def noisy_obs_geo(op, x, sn, base, i):
    """y = A x + sn * xi, xi = standard normal from SeedSequence([1, base, i]) (same xi for the four conditions)."""
    return op.apply(x) + sn * rng_of(1, base, i).standard_normal(x.shape)


def ladder_target(N, K, seed=LADDER_SEED):
    """Synthetic Gaussian-mixture target for COST SCALING only (not an image-quality benchmark).
    Density fixed at ~1 target Gaussian per N*N/K px^2 -> K_true = K; sizes fixed in pixels so locality does not grow with N."""
    rng = rng_of(3, N, K)
    from geo_core import render, chol_from_sigma
    th = np.zeros((K, 6))
    th[:, 0] = rng.uniform(0.2, 1.0, K)
    th[:, 1] = rng.uniform(0.0, N, K); th[:, 2] = rng.uniform(0.0, N, K)
    for k in range(K):
        s1, s2 = rng.uniform(1.5, 4.0, 2); phi = rng.uniform(0, np.pi)
        R = np.array([[np.cos(phi), -np.sin(phi)], [np.sin(phi), np.cos(phi)]])
        S = R @ np.diag([s1 ** 2, s2 ** 2]) @ R.T
        th[k, 3:] = chol_from_sigma(S)
    x = render(th, N)
    return x / x.max()
