"""GEO-0 node R (addendum I of contracts/FROZEN_AS_CONTRACT_v2_1.md): READ-ONLY re-look at the already-written S2 trajectories.
Not the frozen analyzer's main(); imports its loader/constants only (sha256 must equal 9adc5b04...). No fits, no new images. Writes only to <out>.
usage: as_node_r.py root=outputs\\AS-S2 out=outputs\\AS-S2-nodeR"""
import os, sys, json, math, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import numpy as np
ANALYZER_SHA = '9adc5b04612c234dab2ba4cc35972b5b27bd6fe573ee636db6951a5e5d7f8168'
REPORT_SHA = '163c79153bef1f3b7b15eb49187263cd51fe40f65c21fffff51655f1cfb0c751'
TQ = 2.0687   # t_{0.975, df=23}
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()

def main():
    kv = dict(a.split('=', 1) for a in sys.argv[1:] if '=' in a)
    root = kv.get('root', os.path.join('outputs', 'AS-S2')); outd = kv.get('out', os.path.join('outputs', 'AS-S2-nodeR'))
    ap = os.path.join(ROOT, 'experiments', 'as_analyze.py'); rp = os.path.join(ROOT, 'outputs', 'AS-S2-report', 'AS_S2_REPORT.json')
    assert sha(ap) == ANALYZER_SHA and sha(rp) == REPORT_SHA, 'frozen file sha mismatch'
    os.makedirs(outd, exist_ok=True)
    import as_analyze as A
    import as_core as C, as_gen as G
    M, aux, extra, clean, op_of = A.load_all(os.path.join(ROOT, root))
    orig = json.load(open(rp, encoding='utf-8'))['report']
    ARMS = ['ORACLE_xs', 'BLOCK', 'OMP', 'JOINT', 'RAND', 'JOINT_FREE']; KS = A.KEYS; res = {}
    missing = {a: [list(k) for k in KS if k not in extra.get(a, {})] for a in ARMS}
    short = {}
    for a in ARMS:
        res[a] = {}
        for k in KS:
            if k not in extra.get(a, {}): continue
            r = extra[a][k]; short.setdefault(a, [])
            if len(r['traj']) != 31: short[a].append([list(k), len(r['traj'])])
            i, c, s = k; sb, sn = r['sb'], r['sn']; op = op_of(sb); y = G.noisy_obs(op, clean[i], sn, s, i)
            ms = []; kd = len(r['traj']) - 1; found = False
            for j, th in enumerate(r['traj']):
                x = C.render(np.array(th)); ms.append(float(np.mean((x - clean[i]) ** 2)))
                if (not found) and float(np.sum((y - op.apply(x)) ** 2)) <= A.TAU * C.N ** 2 * sn ** 2: kd = j; found = True
            res[a][k] = dict(end=ms[-1], stop=ms[kd], best=min(ms), kd=kd, found=found, nj=len(r['traj']), jstar=int(np.argmin(ms)))
    KS = [k for k in KS if all(k in res[a] for a in ARMS)]
    # reproduction check: trajectory endpoint == analyzer's final-theta MSE; endpoint H == original H
    maxdiff = max(abs(res[a][k]['end'] - M[a][k]) / M[a][k] for a in ARMS for k in KS)
    S2H = {'RAND': 0.370, 'JOINT_FREE': 0.314, 'OMP': -0.068, 'JOINT': -0.040, 'ORACLE_xs': 0.4518}
    def H_end(X): return 1.0 - math.exp(float(np.mean([math.log(res[X][k]['end'] / res['BLOCK'][k]['end']) for k in KS])))
    H_e = {a: H_end(a) for a in ARMS if a != 'BLOCK'}; H_o = {a: orig['H'].get(a) for a in ARMS if a != 'BLOCK'}
    repro = dict(max_rel_diff_end_vs_M=maxdiff, H_end=H_e, H_orig=H_o, S2H_rounded=S2H,
                 ok_vs_orig_1e6={a: bool(abs(H_e[a] - H_o[a]) <= 1e-6) for a in H_e}, ok_vs_rounded_1e3={a: bool(abs(H_e[a] - S2H[a]) <= 1e-3) for a in H_e},
                 traj_lengths=sorted({res[a][k]['nj'] for a in ARMS for k in KS}), n_units_used=len(KS), missing_units=missing, short_trajectories=short)
    def stat(X, which, conds=None):
        keys = [k for k in KS if (conds is None or k[1] == conds)]
        D = []
        for i in A.IMGS:
            lr = [math.log(res[X][k][which] / res['BLOCK'][k][which]) for k in keys if k[0] == i]; D.append(float(np.mean(lr)))
        D = np.array(D); n = len(D); m = float(D.mean()); se = float(D.std(ddof=1) / math.sqrt(n)); p, cnt, tot = A.signflip_p(D)
        return dict(H=1.0 - math.exp(m), H_lo95=1.0 - math.exp(m + TQ * se), H_hi95=1.0 - math.exp(m - TQ * se), meanD=m, se=se, p_signflip=p, n_images=n, n_units=len(keys))
    out = dict(note='GEO-0 node R, read-only post-hoc diagnostic on development data (addendum I). Not a gate. (a)=each arm at its own discrepancy stop; (b)=each existing path at its clean-image best step (ideal stopping reference for these paths only, not an upper bound over algorithms); (c)=other arms vs BLOCK; (d)=(a) per condition. FIXED arms: no trajectory -> missing.',
               analyzer_sha256=ANALYZER_SHA, original_report_sha256=REPORT_SHA, reproduction=repro, FIXED='missing (no trajectory)',
               stop_index={a: dict(mean_j=float(np.mean([res[a][k]['kd'] for k in KS])), median_j=float(np.median([res[a][k]['kd'] for k in KS])), mean_K=6 + float(np.mean([res[a][k]['kd'] for k in KS])),
                                   fallback_rate_j30=float(np.mean([not res[a][k]['found'] for k in KS])), mean_jstar=float(np.mean([res[a][k]['jstar'] for k in KS])), median_jstar=float(np.median([res[a][k]['jstar'] for k in KS]))) for a in ARMS})
    out['stop_index_by_condition'] = {c: {a: dict(mean_j=float(np.mean([res[a][k]['kd'] for k in KS if k[1] == c])), median_j=float(np.median([res[a][k]['kd'] for k in KS if k[1] == c])), fallback_rate_j30=float(np.mean([not res[a][k]['found'] for k in KS if k[1] == c])),
                                          mean_jstar=float(np.mean([res[a][k]['jstar'] for k in KS if k[1] == c]))) for a in ARMS} for c in A.CONDS}
    for which, tag in (('stop', 'a_stop'), ('best', 'b_clean_best_step'), ('end', 'endpoint_context')):
        out[tag] = {X: stat(X, which) for X in ARMS if X != 'BLOCK'}
    out['d_stop_by_condition'] = {c: {X: stat(X, 'stop', c) for X in ARMS if X != 'BLOCK'} for c in A.CONDS}
    out['gm_mse'] = {w: {a: math.exp(float(np.mean([math.log(res[a][k][w]) for k in KS]))) for a in ARMS} for w in ('end', 'stop', 'best')}
    assert sha(rp) == REPORT_SHA
    json.dump(out, open(os.path.join(outd, 'NODE_R.json'), 'w'), indent=1)
    L = ['# GEO-0 node R (read-only, post-hoc diagnostic; addendum I)', '', 'reproduction: max rel diff endpoint vs analyzer M = %.2e; traj lengths %s' % (maxdiff, repro['traj_lengths']),
         'H_end (trajectory endpoint, vs BLOCK): %s' % {a: round(v, 4) for a, v in repro['H_end'].items()}, 'H_orig (report): %s' % {a: (round(v, 4) if v is not None else None) for a, v in repro['H_orig'].items()}, '',
         'stop index per arm (mean j, median j, mean K, fallback-to-j30 rate, mean j*): %s' % {a: (round(v['mean_j'], 2), v['median_j'], round(v['mean_K'], 2), round(v['fallback_rate_j30'], 3), round(v['mean_jstar'], 2)) for a, v in out['stop_index'].items()}, 'endpoint repro ok vs orig 1e-6: %s; vs rounded S2 1e-3: %s; missing/short: %s / %s' % (repro['ok_vs_orig_1e6'], repro['ok_vs_rounded_1e3'], {a: len(v) for a, v in missing.items()}, {a: len(v) for a, v in short.items()}), 'gm MSE end/stop/best: %s' % {w: {a: round(v, 5) for a, v in d.items()} for w, d in out['gm_mse'].items()}, '']
    for tag in ('a_stop', 'b_clean_best_step', 'endpoint_context'):
        L.append('## %s (H vs BLOCK; positive = lower MSE; [95%% t-interval over 24 images]; sign-flip p)' % tag)
        for X, s in out[tag].items(): L.append('- %s: H=%.4f [%.4f, %.4f] p=%.4f' % (X, s['H'], s['H_lo95'], s['H_hi95'], s['p_signflip']))
    L.append('## stop index by condition (mean j / fallback rate j30 / mean j*)')
    for c, d in out['stop_index_by_condition'].items(): L.append('- %s: %s' % (c, {a: (round(v['mean_j'], 1), round(v['fallback_rate_j30'], 2), round(v['mean_jstar'], 1)) for a, v in d.items()}))
    L.append('## d_stop_by_condition (ORACLE_xs / RAND / JOINT_FREE / OMP / JOINT vs BLOCK)')
    for c, d in out['d_stop_by_condition'].items(): L.append('- %s: %s' % (c, {X: (round(s['H'], 4), round(s['H_lo95'], 4), round(s['H_hi95'], 4)) for X, s in d.items()}))
    open(os.path.join(outd, 'NODE_R.md'), 'w', encoding='utf-8').write('\n'.join(L)); print('\n'.join(L)[:6000])

if __name__ == '__main__': main()
