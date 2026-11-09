"""AS S2 ERRATUM-192 (FAIL-0025; plan = contracts/FROZEN_AS_CONTRACT_v2_1.md addendum H). READ-ONLY recomputation, NOT the frozen analyzer, no new fits.
Imports the frozen analyzer unmodified (sha256 must equal 9adc5b04...), checks (a) reproduction of the original report from the unrestricted data, (b) re-runs the same
analyze()/diagnostics() functions with every arm restricted to the contract main set KEYS (192 units). Writes only to <out> (never to outputs/AS-S2-report).
usage: as_erratum_192.py root=outputs\\AS-S2 out=outputs\\AS-S2-erratum192"""
import os, sys, json, math, hashlib, collections, copy
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'experiments'))
ANALYZER_SHA = '9adc5b04612c234dab2ba4cc35972b5b27bd6fe573ee636db6951a5e5d7f8168'
REPORT_SHA = '163c79153bef1f3b7b15eb49187263cd51fe40f65c21fffff51655f1cfb0c751'
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()

def main():
    kv = dict(a.split('=', 1) for a in sys.argv[1:] if '=' in a)
    root = kv.get('root', os.path.join('outputs', 'AS-S2')); outd = kv.get('out', os.path.join('outputs', 'AS-S2-erratum192'))
    ap = os.path.join(ROOT, 'experiments', 'as_analyze.py'); rp = os.path.join(ROOT, 'outputs', 'AS-S2-report', 'AS_S2_REPORT.json')
    s_an, s_rep0 = sha(ap), sha(rp)
    assert s_an == ANALYZER_SHA, 'analyzer sha mismatch: %s' % s_an
    assert s_rep0 == REPORT_SHA, 'original report sha mismatch: %s' % s_rep0
    if os.path.abspath(outd).startswith(os.path.abspath(os.path.join(ROOT, 'outputs', 'AS-S2-report'))): raise SystemExit('refusing to write into the original report dir')
    os.makedirs(outd, exist_ok=True)
    import as_analyze as A
    orig = json.load(open(rp, encoding='utf-8'))
    M, aux, extra, clean, op_of = A.load_all(os.path.join(ROOT, root))
    KS = set(A.KEYS)
    # (a) reproduction on unrestricted data
    rep_full = A.analyze(M, aux)
    def g1(r): return {R: dict(meanD=r['gate1'][R]['meanD'], p=r['gate1'][R]['p'], cond_means=r['gate1'][R]['cond_means'], fam_means=r['gate1'][R]['fam_means']) for R in ('OMP', 'BLOCK')}
    o = orig['report']; mism = []
    for R in ('OMP', 'BLOCK'):
        for q in ('meanD', 'p'):
            if abs(rep_full['gate1'][R][q] - o['gate1'][R][q]) > 1e-9: mism.append((R, q, rep_full['gate1'][R][q], o['gate1'][R][q]))
    for a, v in o['H'].items():
        if abs(rep_full['H'][a] - v) > 1e-9: mism.append(('H', a, rep_full['H'][a], v))
    if abs(rep_full['gateF_ratio_FIXED_over_JOINT'] - o['gateF_ratio_FIXED_over_JOINT']) > 1e-9: mism.append(('gateF',))
    if rep_full['decision'] != o['decision'].split(' ')[0] and rep_full['decision'] != o['decision']: mism.append(('decision', rep_full['decision'], o['decision']))
    repro = dict(ok=(not mism), mismatches=mism, decision_unrestricted=rep_full['decision'])
    # (b) restricted to the contract main set
    removed = {a: collections.Counter(k[1] for k in d if k not in KS) for a, d in M.items()}
    removed = {a: dict(c) for a, c in removed.items() if c}
    M192 = {a: {k: v for k, v in d.items() if k in KS} for a, d in M.items()}
    extra192 = {a: ({k: v for k, v in d.items() if k in KS} if isinstance(d, dict) else d) for a, d in extra.items()}
    aux192 = dict(aux); aux192['infeasible'] = {a: {k: v for k, v in d.items() if k in KS} for a, d in aux.get('infeasible', {}).items()}
    rep192 = A.analyze(M192, aux192)
    diag192 = {}
    if rep192['decision'] != 'INCOMPLETE':
        diag192 = A.diagnostics(M192, extra192, clean, op_of, aux192)
    cmp = {}
    for R in ('OMP', 'BLOCK'):
        a_, b_ = o['gate1'][R], rep192['gate1'][R]
        cmp[R] = dict(orig=dict(meanD=a_['meanD'], ratio=a_['ratio'], p=a_['p'], cond_means=a_['cond_means'], fam_means=a_['fam_means'], pass_i=a_['pass_i'], pass_ii=a_['pass_ii'], pass_iii=a_['pass_iii'], pass_iv=a_['pass_iv'], passed=a_['passed']),
                      err192=dict(meanD=b_['meanD'], ratio=b_['ratio'], p=b_['p'], cond_means=b_['cond_means'], fam_means=b_['fam_means'], pass_i=b_['pass_i'], pass_ii=b_['pass_ii'], pass_iii=b_['pass_iii'], pass_iv=b_['pass_iv'], passed=b_['passed']))
    cmp['decision'] = dict(orig=o['decision'], err192=rep192['decision']); cmp['decision_same'] = (o['decision'] == rep192['decision'])
    cmp['gate1_flags_same'] = all(cmp[R]['orig'][f] == cmp[R]['err192'][f] for R in ('OMP', 'BLOCK') for f in ('pass_i', 'pass_ii', 'pass_iii', 'pass_iv', 'passed'))
    cmp['H_same'] = all(abs(o['H'][a] - rep192['H'][a]) < 1e-12 for a in o['H']); cmp['gateF'] = dict(orig=o['gateF_ratio_FIXED_over_JOINT'], err192=rep192['gateF_ratio_FIXED_over_JOINT'])
    s_rep1 = sha(rp)
    out = dict(erratum=True, note='READ-ONLY erratum recomputation (FAIL-0025, addendum H). Not the frozen analyzer. Original statistics retained in outputs/AS-S2-report.',
               analyzer_sha256=s_an, original_report_sha256_before=s_rep0, original_report_sha256_after=s_rep1, original_report_unchanged=(s_rep0 == s_rep1),
               reproduction=repro, units_removed_by_arm_and_cond=removed, n_units={a: len(M192[a]) for a in ('OMP', 'BLOCK', 'JOINT', 'FIXED', 'RAND', 'JOINT_FREE', 'ORACLE_xs', 'ORACLE_ys') if a in M192},
               report_192=rep192, diagnostics_192=diag192, comparison=cmp)
    json.dump(out, open(os.path.join(outd, 'ERRATUM_AS_S2_192.json'), 'w'), indent=1, default=str)
    L = ['# AS S2 ERRATUM-192 (read-only; FAIL-0025)', '', 'reproduction of original report from unrestricted data: ok=%s mismatches=%s' % (repro['ok'], repro['mismatches']), 'original report unchanged: %s' % (s_rep0 == s_rep1), 'units removed (arm: {cond: n}): %s' % removed, '',
         'decision orig=%s | err192=%s | same=%s | gate1 flags same=%s | H same=%s' % (o['decision'], rep192['decision'], cmp['decision_same'], cmp['gate1_flags_same'], cmp['H_same']), 'GateF orig=%.4f err192=%.4f' % (cmp['gateF']['orig'], cmp['gateF']['err192']), '']
    for R in ('OMP', 'BLOCK'):
        for tag in ('orig', 'err192'):
            g = cmp[R][tag]; L.append('Gate1 vs %s [%s]: meanD=%.4f (ratio %.4f) p=%.5f cond=%s fam=%s pass(i,ii,iii,iv)=%s,%s,%s,%s' % (R, tag, g['meanD'], g['ratio'], g['p'], {c: round(v, 4) for c, v in g['cond_means'].items()}, {c: round(v, 4) for c, v in g['fam_means'].items()}, g['pass_i'], g['pass_ii'], g['pass_iii'], g['pass_iv']))
    L += ['', 'deviation-principle K diagnostic (contract-required; Gate-1 stats at the deviation K; no decision weight): %s' % json.dumps(diag192.get('deviation_K'), default=str)[:3000], 'deviation_K_mean_index: %s' % diag192.get('deviation_K_mean_index'), 'overfit(192): %s' % json.dumps(diag192.get('overfit'), default=str)[:1500]]
    open(os.path.join(outd, 'ERRATUM_AS_S2_192.md'), 'w', encoding='utf-8').write('\n'.join(L)); print('\n'.join(L)[:5000])

if __name__ == '__main__': main()
