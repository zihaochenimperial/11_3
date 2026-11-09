"""Host benchmark/equivalence check: src/gsfast.py (numpy, analytic gradients) vs src/gsfit.py (torch autograd). Run via pump 'py' job on an otherwise idle machine.
Writes outputs/bench_fast.json. Checks: gradient agreement, short-fit agreement, determinism+forced replay of the fast path, per-step and per-fit timing."""
import json, sys, time
from pathlib import Path
import numpy as np
import torch
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
torch.set_num_threads(1)
from dataclasses import replace
from src.f0_config import F0Config
from src import gsfit, gsfast, synth

res = {}
cfg = F0Config(); H = W = 64; K = 48
rng = np.random.default_rng(1)
xy = rng.random((K, 2)); ls = np.log(rng.uniform(1.5, 5, (K, 2))); rot = rng.uniform(-1, 1, K); val = rng.normal(0.5, 0.3, K); y = rng.random(H * W)
tt = [torch.tensor(a, dtype=torch.float64, requires_grad=True) for a in (xy, ls, rot, val)]
f = gsfit.render(*tt, H, W); loss = ((f - torch.tensor(y.reshape(H, W))) ** 2).mean(); loss.backward()
lf, ff, gr = gsfast.loss_and_grad(xy, ls, rot, val, y, H, W)
res['grad_rel_err'] = {k: float(np.max(np.abs(gr[k] - t.grad.numpy())) / (np.max(np.abs(t.grad.numpy())) + 1e-300)) for k, t in zip(('xy', 'logscale', 'rot', 'val'), tt)}
res['loss_abs_diff'] = abs(lf - float(loss)); res['render_max_abs_diff'] = float(np.max(np.abs(ff.reshape(H, W) - f.detach().numpy())))
# timing per step
def tm(fn, n):
    t0 = time.perf_counter()
    for _ in range(n): fn()
    return (time.perf_counter() - t0) / n * 1000
def torch_step():
    t2 = [torch.tensor(a, dtype=torch.float64, requires_grad=True) for a in (xy, ls, rot, val)]
    l = ((gsfit.render(*t2, H, W) - torch.tensor(y.reshape(H, W))) ** 2).mean(); l.backward()
from src.gskernel import loss_and_grad_tiled
lt, _ft, grt = loss_and_grad_tiled(xy, ls, rot, val, y, H, W, tile=512)
res['tiled_grad_rel_err'] = {k: float(np.max(np.abs(grt[k] - t.grad.numpy())) / (np.max(np.abs(t.grad.numpy())) + 1e-300)) for k, t in zip(('xy', 'logscale', 'rot', 'val'), tt)}
res['ms_per_step_tiled'] = tm(lambda: loss_and_grad_tiled(xy, ls, rot, val, y, H, W, tile=512, want_f=False), 20)
res['ms_per_step_torch'] = tm(torch_step, 20); res['ms_per_step_fast'] = tm(lambda: gsfast.loss_and_grad(xy, ls, rot, val, y, H, W), 20)
# short and full fits
from numpy.random import SeedSequence
x = synth.make_clean('D1', 1001, cfg); yy = synth.add_noise(x, cfg.sigma0, 7)
om = SeedSequence(entropy=20261105, spawn_key=(2, 0, 0))
for steps in (5, 25):
    c = replace(cfg, steps_per_stage=steps)
    a, aa = gsfit.fit_pipeline(yy, om, 64, c); b, bb = gsfast.fit_pipeline(yy, om, 64, c)
    res['fit_agree_steps%d' % steps] = dict(max_abs_diff=float(np.max(np.abs(a - b))), births_equal=bool(all(np.array_equal(p, q) for p, q in zip(aa['birth_idx'], bb['birth_idx']))))
b1, a1 = gsfast.fit_pipeline(yy, om, 64, replace(cfg, steps_per_stage=5)); b2, a2 = gsfast.fit_pipeline(yy, om, 64, replace(cfg, steps_per_stage=5))
b3, _ = gsfast.fit_pipeline(yy, om, 64, replace(cfg, steps_per_stage=5), forced_idx=a1['birth_idx'])
res['fast_determinism_bitwise'] = bool(np.array_equal(b1, b2)); res['fast_forced_replay_bitwise'] = bool(np.array_equal(b1, b3))
t0 = time.perf_counter(); gsfast.fit_pipeline(yy, om, 64, cfg); res['fit_s_fast_full600'] = time.perf_counter() - t0
t0 = time.perf_counter(); gsfit.fit_pipeline(yy, om, 64, cfg); res['fit_s_torch_full600'] = time.perf_counter() - t0
Path(ROOT, 'outputs').mkdir(exist_ok=True)
Path(ROOT, 'outputs', 'bench_fast.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
print(json.dumps(res, indent=1))
