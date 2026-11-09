"""Aggregator for K-a (contract-free; not evidence). Usage: python as_ka_aggregate_20261105.py OUTDIR PREFIXGLOB"""
import json, glob, sys, numpy as np
rules = ['raw_free', 'joint_free', 'raw_c1', 'block_c1', 'joint_c1']
files = sorted(glob.glob(sys.argv[1] + '/' + sys.argv[2]))
print("cell | n | stat_med | rule: eff_all hit_all split%chosen | eff_split rho_split | eff_birth rho_birth")
summary = {}
for f in files:
    sc = json.load(open(f)); cell = f.split('/')[-1].replace('.json', '')
    n = len(sc); line = {}
    for r in rules:
        g = lambda pool, key: np.nanmean([s['sum'][r][pool][key] for s in sc])
        line[r] = dict(eff_all=g('all', 'eff'), hit_all=g('all', 'hit'), split_ch=g('all', 'is_split'),
                       eff_split=g('split', 'eff'), rho_split=g('split', 'rho'), eff_birth=g('birth', 'eff'), rho_birth=g('birth', 'rho'),
                       rho_all=g('all', 'rho'))
    # top-1 agreement (all pool) between rules
    agree = {}
    for i, a in enumerate(rules):
        for b in rules[i + 1:]:
            agree[a + '~' + b] = float(np.mean([s['sum'][a]['all']['choice'] == s['sum'][b]['all']['choice'] for s in sc]))
    # realisable-split diagnostics
    cs = [c['c_star'] for s in sc for c in s['cands'] if c['type'] == 'split']
    fl = [c['floor'] for s in sc for c in s['cands']]
    summary[cell] = dict(n=n, stat_med=float(np.median([s['stat'] for s in sc])), line=line, agree=agree,
                         c_star_split_med=float(np.median(cs)), c_star_split_q=[float(np.quantile(cs, q)) for q in (.1, .9)],
                         floor_below_1e3=float(np.mean(np.array(fl) < 1e-3)))
    print(f"{cell:14s} n={n} stat_med={summary[cell]['stat_med']:.1e} c*split med={summary[cell]['c_star_split_med']:.2f} floor<1e-3={summary[cell]['floor_below_1e3']:.3f}")
    for r in rules:
        l = line[r]
        print(f"   {r:10s} eff_all={l['eff_all']:.3f} hit={l['hit_all']:.2f} split%={l['split_ch']:.2f} | eff_split={l['eff_split']:.3f} rho_s={l['rho_split']:.2f} | eff_birth={l['eff_birth']:.3f} rho_b={l['rho_birth']:.2f} | rho_all={l['rho_all']:.2f}")
    print("   top1-agree:", " ".join(f"{k}={v:.2f}" for k, v in agree.items() if k.split('~')[0] in ('raw_c1', 'block_c1') or k in ('raw_free~joint_free',)))
json.dump(summary, open(sys.argv[1] + '/KA_SUMMARY_' + sys.argv[2].replace('*', 'X').replace('.json', '') + '.json', 'w'), indent=1)
