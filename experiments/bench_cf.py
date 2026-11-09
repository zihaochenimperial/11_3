"""Non-evidence timing benchmark for the CF-birth line (single process): wall of one R=4 trajectory (750 steps) and one R=3 pipeline. Output outputs/bench_cf_timing.json."""
import os
for v in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[v]='1'
import json, sys, time
from pathlib import Path
import numpy as np
from numpy.random import SeedSequence
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from src.f0_config import F0Config
from src import cf_fit, gsfast
cfg = F0Config(); rng = np.random.default_rng(1)
y = (0.5 + 0.2*rng.standard_normal((64,64)) * 0.4).reshape(64,64)
om = SeedSequence(entropy=20261107, spawn_key=(22,1,0)); res = {}
for name, fn in (('traj_R4', lambda: cf_fit.trajectory(y, om, 1024, cfg, 4)), ('pipeline_R3', lambda: gsfast.fit_pipeline(y, om, 1024, cfg)), ('traj_R4_b', lambda: cf_fit.trajectory(y, om, 1024, cfg, 4))):
    t0 = time.perf_counter(); fn(); res[name] = time.perf_counter() - t0
res['fits_per_s_single_proc_R3'] = 1.0 / res['pipeline_R3']
(ROOT/'outputs'/'bench_cf_timing.json').write_text(json.dumps(res, indent=1), encoding='utf-8'); print(json.dumps(res))
