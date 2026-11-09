"""D-02 equivalence tests: numpy analytic-gradient implementation (src/gsfast.py + src/gskernel.py) vs torch autograd reference (src/gsfit.py)."""
import re
from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest
import torch
from numpy.random import SeedSequence
from src import gsfit, gsfast, gskernel
from src.f0_config import F0Config

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize('K', [24, 32, 48])
def test_grad_matches_torch_autograd(K):
    H = W = 64
    rng = np.random.default_rng(K)
    xy = rng.random((K, 2)); ls = np.log(rng.uniform(1.5, 5, (K, 2))); rot = rng.uniform(-1, 1, K); val = rng.normal(0.5, 0.3, K); y = rng.random(H * W)
    tt = [torch.tensor(a, dtype=torch.float64, requires_grad=True) for a in (xy, ls, rot, val)]
    f = gsfit.render(*tt, H, W); loss = ((f - torch.tensor(y.reshape(H, W))) ** 2).mean(); loss.backward()
    lt, ft, gr = gskernel.loss_and_grad_tiled(xy, ls, rot, val, y, H, W)
    assert abs(lt - float(loss)) < 1e-14
    assert np.max(np.abs(ft.reshape(H, W) - f.detach().numpy())) < 1e-13
    for k, t in zip(('xy', 'logscale', 'rot', 'val'), tt):
        g = t.grad.numpy(); assert np.max(np.abs(gr[k] - g)) / (np.max(np.abs(g)) + 1e-300) < 1e-12, k


def test_short_fit_agrees_and_births_equal():
    cfg = replace(F0Config(), steps_per_stage=8)
    y = np.random.default_rng(3).random((64, 64)) * 0.2 + 0.4
    om = SeedSequence(entropy=20261105, spawn_key=(2, 1, 0))
    a, aa = gsfit.fit_pipeline(y, om, 64, cfg); b, bb = gsfast.fit_pipeline(y, om, 64, cfg)
    assert np.max(np.abs(np.asarray(a) - np.asarray(b))) < 1e-9
    assert all(np.array_equal(p, q) for p, q in zip(aa['birth_idx'], bb['birth_idx']))


def test_fast_determinism_and_forced_replay_bitwise():
    cfg = replace(F0Config(), steps_per_stage=8)
    y = np.random.default_rng(4).random((64, 64)) * 0.2 + 0.4
    om = SeedSequence(entropy=20261105, spawn_key=(2, 2, 0))
    f1, a1 = gsfast.fit_pipeline(y, om, 8, cfg); f2, _ = gsfast.fit_pipeline(y, om, 8, cfg)
    f3, _ = gsfast.fit_pipeline(y, om, 8, cfg, forced_idx=a1['birth_idx'])
    assert np.array_equal(f1, f2) and np.array_equal(f1, f3)


def test_no_label_leakage_imports_in_fast_modules():
    for fn in ('gsfast.py', 'gskernel.py'):
        txt = (ROOT / 'src' / fn).read_text(encoding='utf-8')
        assert not re.search(r'^\s*(from|import)\s+.*\b(synth|reference_eval)\b', txt, re.M), fn
        assert not re.search(r'\bnan_to_num\b|np\.clip|np\.maximum\(', txt), fn
