"""Self-test of experiments/f0_analyze.py on a TOY 'pipeline' with known df (numpy only, no src/ fitters).
Toy: N=256 coordinates; 3 rounds x b=8 births chosen as the top-|y| among the first S entries of a per-round permutation (omega, independent of S);
fit = y on the selected coordinates (projection), 0 elsewhere => df_frozen = 24 exactly, sdf = df - 24 >= 0 grows with S when the signal is weak (selection noise-driven).
Writes a fake outputs dir in the runner's npz format (same task structure via f0_run.build_tasks), then calls analyze(). NOT evidence; outputs a toy dir given on the command line.
usage: python experiments/f0_analyze_selftest.py <outdir> [pilot|full]"""
import json, sys, os, types
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'experiments'))
import f0_run as R  # noqa: E402  (task structure, stage specs, stream conventions)
import f0_analyze as A  # noqa: E402

N = 256; S0 = 0.08; ENT = 20261105


def sig(img):
    x = np.zeros(N)
    if img == 'D1': x[:48] = 0.10
    if img == 'D2': x[:48] = 0.05
    if img == 'D3': x[:48] = 0.20
    if img == 'W1': x[:48] = 0.01
    return x


def perm(om, r): return R.rng_for(ENT, *om, 1 + r).permutation(N)


def toy_fit(y, om, S, forced=None):
    sel = []; idx = []
    for r in range(3):
        cand = [c for c in perm(om, r) if c not in sel][:S]
        if forced is None:
            ch = np.sort(np.array(cand)[np.argsort(-np.abs(y[cand]), kind='stable')[:8]])
        else:
            ch = forced[r]
        sel += list(ch); idx.append(ch)
    f = np.zeros(N); f[sel] = y[sel]
    return f, idx


def toy_n0(y, om):
    I = R.rng_for(ENT, *om, 0).permutation(N)[:24]; f = np.zeros(N); f[I] = y[I]; return f


def unit(t):
    kind = t['kind']; img = t['img']; S = t['S']; m = t['m']; ii = R.IMG_IDX[img]; x = sig(img)
    e = S0 * R.rng_for(ENT, 1, ii, m).standard_normal(N); y = x + e; out = {}; nf = 0
    if kind in ('main', 'conv'):
        om = (2, ii, m); f, idx = toy_fit(y, om, S); g0, _ = toy_fit(y, om, S, forced=idx)
        out.update(F=f, E=e, replay_ok=np.array(bool(np.array_equal(f, g0))), birth_idx=np.stack(idx), base_fit_s=np.array(0.01))
        b0 = R.rng_for(ENT, 3, ii, m).standard_normal(N); fd = []
        for er in t['epsf']:
            ef = er * S0; gp, _ = toy_fit(y + ef * b0, om, S, forced=idx); fd.append(np.sum(b0 * (gp - f)) / ef)
        out['FD'] = np.array(fd); out['ANTI'] = np.array(np.nan)
        if m < t['anti_M']:
            fm, _ = toy_fit(x - e, om, S); out['ANTI'] = np.array(np.sum((f - fm) * e) / (2 * S0 ** 2))
        div = np.full((5, 2), np.nan)
        for (ei, j) in t['plan']:
            bj = R.rng_for(ENT, 6, ii, m, j).standard_normal(N); er = R.EPS_REL[ei] * S0; fp, _ = toy_fit(y + er * bj, om, S); div[ei, j] = np.sum(bj * (fp - f)) / er
        out['DIV'] = div; key = (kind, img, S, 0); nf = 3
    elif kind == 'fix':
        om = (8, ii, t['k']); f, _ = toy_fit(y, om, S); out.update(F=f, E=e); key = ('fix', img, S, t['k'])
    elif kind == 'sigma':
        ei = t['ei']; sp = np.sqrt(S0 ** 2 + (R.EPS_REL[ei] * S0) ** 2); e2 = sp * R.rng_for(ENT, 4, ii, ei, m).standard_normal(N)
        f, _ = toy_fit(x + e2, (5, ii, ei, m), S); out.update(F=f, E=e2, sigma_prime=np.array(sp)); key = ('sigma', img, S, ei)
    elif kind == 'n0':
        om = (7, ii, m); f = toy_n0(y, om); out.update(F=f, E=e, base_fit_s=np.array(0.01))
        b = R.rng_for(ENT, 9, ii, m, 0).standard_normal(N); out['FD'] = np.array([np.sum(b * (toy_n0(y + er * S0 * b, om) - f)) / (er * S0) for er in t['epsf']])
        div = np.full((5, 2), np.nan)
        for (ei, j) in t['plan']:
            bj = R.rng_for(ENT, 9, ii, m, 1 + j).standard_normal(N); er = R.EPS_REL[ei] * S0; div[ei, j] = np.sum(bj * (toy_n0(y + er * bj, om) - f)) / er
        out['DIV'] = div; key = ('n0', img, 0, 0); nf = 3
    elif kind == 'plin':
        om = (10, ii, m); f, idx = toy_fit(y, om, S); g0, _ = toy_fit(y, om, S, forced=idx)
        b = R.rng_for(ENT, 11, ii, m).standard_normal(N); ef = t['epsf'] * S0; gp, _ = toy_fit(y + ef * b, om, S, forced=idx)
        out.update(F=f, E=e, FD=np.array([np.sum(b * (gp - f)) / ef]), rank=np.array(24), replay_ok=np.array(bool(np.array_equal(f, g0))), support=np.concatenate(idx)); key = ('plin', img, S, 0)
    elif kind == 'v7':
        om = (10, ii, m); f, idx = toy_fit(y, om, S); sel = np.concatenate(idx); ef = t['epsf'] * S0
        tr = sum(((y[i] + ef) - y[i]) / ef for i in sel); out.update(trace=np.array(tr), rank=np.array(24)); key = ('v7', img, S, 0)
    elif kind == 'det':
        out.update(det_f_ok=np.array(True), det_pert_ok=np.array(True)); key = ('det', img, S, 0)
    out['n_fits'] = np.array(max(nf, 1)); return key, m, out, 0.05, max(nf, 1)


def main():
    outdir = Path(sys.argv[1]); stage = sys.argv[2] if len(sys.argv) > 2 else 'pilot'
    os.makedirs(outdir, exist_ok=True)
    spec = R.stage_spec(stage, 0.01); cfgd = dict(sigma0=S0, steps_per_stage=150)
    tasks = R.build_tasks(spec, cfgd); acc = {}; walls = {}
    for t in tasks:
        key, m, arrs, w, nf = unit(t); acc.setdefault(key, {})[m] = arrs; walls.setdefault(key, []).append(w)
    for key, d in acc.items(): R.flush(outdir, key, d, walls)
    frozen = (ROOT / 'contracts' / 'F0_CONTRACT.sha256').read_text().split()[0]
    meta = dict(stage=stage, tag='selftest', debug=True, contract_sha256=frozen, cfg=dict(sigma0=S0), workers=18, aborted=None, stage_spec={k: (list(v) if isinstance(v, tuple) else v) for k, v in spec.items()})
    (outdir / 'meta.json').write_text(json.dumps(meta), encoding='utf-8')
    (outdir / 'unit_report.json').write_text(json.dumps(dict(passed=True)), encoding='utf-8')
    a = types.SimpleNamespace(unit_report=str(outdir / 'unit_report.json'), allow_debug=True)
    out = A.analyze(str(outdir), a)
    (outdir / 'analysis.json').write_text(json.dumps(out, indent=1, default=float), encoding='utf-8'); (outdir / 'ANALYSIS.md').write_text(A.md(out), encoding='utf-8')
    print('DECISION:', out['decision']); print(json.dumps(out['gates'], default=str))
    for im, r in out['H1_table'].items(): print(im, 'contrast', {k: round(v, 3) for k, v in r['contrast'].items()}, 'H1a', r['H1a'], r.get('H1c'))
    for im, r in out['plin'].items(): print('plin', im, {k: round(v, 3) for k, v in r['contrast_1024_minus_8'].items()})
    if 'pilot' in out: print('pilot', json.dumps({k: v for k, v in out['pilot'].items() if k != 'record_only_rule7'}, default=float)[:600])
    print('H2', json.dumps({i: (r['eps_star'], r['adequate']) for i, r in out['H2_table'].items()}))


if __name__ == '__main__':
    main()
