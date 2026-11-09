"""Host parallel-scaling diagnostic for the F0 fitter (not evidence; timing only).
For each worker count W: W single-threaded processes each run NFIT short pipelines (steps_per_stage=40 -> 160 steps) back-to-back on the same data;
report aggregate fits/s and per-fit wall. Also samples the CPU clock (read-only WMI query) during the W>=14 runs.
Writes outputs/bench_scaling.json."""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_v] = '1'
import json, sys, time, subprocess
from pathlib import Path
from multiprocessing import Pool

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
NFIT = 4
STEPS = 40


def work(args):
    impl, seed = args
    import numpy as np
    from dataclasses import replace
    from numpy.random import SeedSequence
    from src.f0_config import F0Config
    cfg = replace(F0Config(), steps_per_stage=STEPS)
    if impl == 'torch':
        import torch
        torch.set_num_threads(1)
        from src import gsfit as mod
    else:
        from src import gsfast as mod
    rng = np.random.default_rng(seed)
    y = rng.random((64, 64)) * 0.2 + 0.4
    om = SeedSequence(entropy=20261105, spawn_key=(2, seed, 0))
    walls = []
    for _ in range(NFIT):
        t0 = time.perf_counter(); mod.fit_pipeline(y, om, 64, cfg); walls.append(time.perf_counter() - t0)
    return walls


def clock():
    try:
        out = subprocess.run(['powershell', '-NoProfile', '-Command',
                              'Get-CimInstance Win32_Processor | Select-Object CurrentClockSpeed,MaxClockSpeed,LoadPercentage | ConvertTo-Json -Compress'],
                             capture_output=True, text=True, timeout=20).stdout.strip()
        return out
    except Exception as ex:  # read-only diagnostic; never fail the benchmark on it
        return 'clock_query_failed %r' % (ex,)


if __name__ == '__main__':
    res = {'steps_per_fit': 4 * STEPS, 'nfit_per_worker': NFIT, 'cpu_count': os.cpu_count(), 'runs': []}
    for impl in (sys.argv[1:] or ['torch', 'fast']):
        for W in (1, 4, 8, 14, 18):
            t0 = time.perf_counter()
            with Pool(W) as pool:
                ar = pool.map_async(work, [(impl, 100 + i) for i in range(W)])
                time.sleep(8.0)
                clk = clock() if W in (14, 18) else None
                allw = ar.get()
            wall = time.perf_counter() - t0
            flat = [x for w in allw for x in w]
            rec = dict(impl=impl, W=W, wall_s=wall, fits=len(flat), fits_per_s=len(flat) / wall, mean_fit_s=sum(flat) / len(flat), clock_sample=clk)
            res['runs'].append(rec); print(json.dumps(rec), flush=True)
    Path(ROOT, 'outputs').mkdir(exist_ok=True)
    Path(ROOT, 'outputs', 'bench_scaling.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
