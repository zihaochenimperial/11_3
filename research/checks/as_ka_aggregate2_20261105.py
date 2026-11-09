"""K-a aggregator v2 (contract-free; descriptive diagnostics, NOT evidence, NOT a frozen analyzer).
Merges files sb*_sp*.json and sb*_sp*_b.json per cell; per scenario computes relative regret of each rule:
  regret = (best realised gain over candidates - realised gain of chosen)/(0.5*|r|^2)   [pool: all / split / birth]
Reports cell means, pooled means, paired mean-differences vs raw_c1/block_c1 with a sign-flip permutation p (descriptive only),
top-1 agreement and Spearman(score, realised) means."""
import json, glob, sys, numpy as np
D = sys.argv[1]
rules = ['raw_free', 'joint_free', 'raw_c1', 'block_c1', 'joint_c1']
cells = {}
for f in sorted(glob.glob(D + '/sb*_sp*.json')):
    base = f.split('/')[-1].replace('_b.json', '').replace('.json', '')
    cells.setdefault(base, []).extend(json.load(open(f)))
rng = np.random.default_rng(0)
def signflip(d, B=4000):
    d = np.asarray(d); obs = d.mean(); s = rng.choice([-1, 1], size=(B, len(d)))
    return obs, float((np.abs((s * d).mean(1)) >= abs(obs) - 1e-15).mean())
per = {}
for cell, scs in cells.items():
    rows = {r: {p: [] for p in ('all', 'split', 'birth')} for r in rules}; rho = {r: {p: [] for p in ('all', 'split', 'birth')} for r in rules}
    ch = {r: [] for r in rules}; spl = {r: [] for r in rules}
    for sc in scs:
        real = np.array([c['real'] for c in sc['cands']]); typ = np.array([c['type'] for c in sc['cands']]); den = 0.5 * sc['r2']
        for r in rules:
            s = np.array([c[r] for c in sc['cands']])
            for p in ('all', 'split', 'birth'):
                idx = np.arange(len(real)) if p == 'all' else np.where(typ == p)[0]
                ci = idx[np.argmax(s[idx])]; rows[r][p].append((real[idx].max() - real[ci]) / den)
                rho[r][p].append(sc['sum'][r][p]['rho'])
            ch[r].append(int(np.argmax(s))); spl[r].append(int(typ[int(np.argmax(s))] == 'split'))
    per[cell] = dict(n=len(scs), regret=rows, rho=rho, choice=ch, split=spl, stat=[sc['stat'] for sc in scs])
print("cell n | mean relative regret (all-pool) per rule | split%chosen | rho_all | top1-agree raw_c1~joint_c1, block_c1~joint_c1")
tot = {r: [] for r in rules}
for cell, d in per.items():
    print(f"{cell:12s} n={d['n']:3d} | " + " ".join(f"{r}={np.mean(d['regret'][r]['all']):.3f}" for r in rules) + " | split%: " +
          " ".join(f"{np.mean(d['split'][r]):.2f}" for r in rules) + " | rho_all: " + " ".join(f"{np.nanmean(d['rho'][r]['all']):.2f}" for r in rules) +
          f" | agree {np.mean(np.array(d['choice']['raw_c1'])==np.array(d['choice']['joint_c1'])):.2f} {np.mean(np.array(d['choice']['block_c1'])==np.array(d['choice']['joint_c1'])):.2f}")
    for r in rules: tot[r].extend(d['regret'][r]['all'])
print("POOLED regret (all-pool): " + " ".join(f"{r}={np.mean(tot[r]):.3f}" for r in rules), " n=", len(tot['raw_c1']))
for pool in ('all', 'split', 'birth'):
    print(f"-- paired differences in relative regret, pool={pool} (negative = joint_c1 picks better), pooled over cells; sign-flip p descriptive")
    for ref in ('raw_c1', 'block_c1', 'raw_free', 'joint_free'):
        for tgt in ('joint_c1',) if ref != 'joint_free' else ('joint_c1',):
            d = np.concatenate([np.array(per[c]['regret'][tgt][pool]) - np.array(per[c]['regret'][ref][pool]) for c in per])
            m, p = signflip(d); print(f"   {tgt} - {ref}: mean={m:+.4f} (sd={d.std():.3f}, n={len(d)}) p~{p:.3f}")
    d = np.concatenate([np.array(per[c]['regret']['joint_free'][pool]) - np.array(per[c]['regret']['raw_free'][pool]) for c in per])
    m, p = signflip(d); print(f"   joint_free - raw_free: mean={m:+.4f} n={len(d)} p~{p:.3f}")
print("-- by blur (pooled over spacing), regret(all-pool) joint_c1 - raw_c1 / joint_c1 - block_c1 / joint_free - raw_free")
for sb in ('0.3', '1.5', '3.0'):
    cs = [c for c in per if c.startswith('sb' + sb + '_')]
    f = lambda a, b: np.mean(np.concatenate([np.array(per[c]['regret'][a]['all']) - np.array(per[c]['regret'][b]['all']) for c in cs]))
    print(f"   sb={sb}: {f('joint_c1','raw_c1'):+.3f} / {f('joint_c1','block_c1'):+.3f} / {f('joint_free','raw_free'):+.3f}")
print("-- Spearman(score, realised) mean over scenarios, pooled over cells")
for p in ('all', 'split', 'birth'):
    print(f"   {p}: " + " ".join(f"{r}={np.nanmean(np.concatenate([per[c]['rho'][r][p] for c in per])):.2f}" for r in rules))
print("-- median stationarity ratio (|J'r|/(smax|r|)) per cell:", " ".join(f"{c}:{np.median(d['stat']):.0e}" for c, d in per.items()))
