"""RJ reducer (contract RJ v1, sections 5-6).
  python experiments/rj_reduce.py --stage sc   --out outputs/RJ   # after eval_det: choose SC (min median W_sp, censored = inf) among the family bests + B0 on 301-312; writes sc.json
  python experiments/rj_reduce.py --stage gate --out outputs/RJ   # after eval_orc: Gate O / Gate T / quality warning -> eval_REDUCE.json
  python experiments/rj_reduce.py --stage chk  --out outputs/RJ   # after chk_det + chk_orc on 313-320 (SC and gate arm fixed by eval) -> chk_REDUCE.json
No confirm access. Oracle arms report no wall-clock (probe time is not rolled back)."""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'src')); sys.path.insert(0, HERE)
import numpy as np
import rj_run as RR
from trn_same_state_reduce import bca

CONDS = ('C1', 'C4')
ORC = ('OKdF', 'OKb', 'OKSb')


def wlow(d): return float(d['W_sp'])                    # W_sp at the end of the run: true value when the target was hit, a LOWER BOUND when censored


def ratio_pc(ctrl, arm):
    """R = W_ctrl / W_arm for one (image, condition) with the contract section 5 censoring rule (R19)."""
    R = wlow(ctrl) / wlow(arm); cc, ca = (not ctrl['hit']), (not arm['hit'])
    if ca and not cc: return min(R, 1.0), 'arm-censored'
    if cc and not ca: return R, 'ctrl-censored(lower bound)'
    if cc and ca: return 1.0, 'both-censored'
    return R, 'ok'


def ratio_stats(runs, ctrl, arm, imgs):
    per_img = []; flags = []
    for i in imgs:
        rc = []
        for c in CONDS:
            R, fl = ratio_pc(runs[(i, c, ctrl)], runs[(i, c, arm)]); rc.append(R); flags.append(fl)
        per_img.append(float(np.exp(np.mean(np.log(rc)))))
    lo, hi = bca(per_img)
    return dict(ctrl=ctrl, arm=arm, median=float(np.median(per_img)), bca_lo=lo, bca_hi=hi, sign=int(sum(v > 1 for v in per_img)), n=len(per_img), per_img=per_img, flags={k: flags.count(k) for k in set(flags)},
                cens_ctrl=float(np.mean([not runs[(i, c, ctrl)]['hit'] for i in imgs for c in CONDS])), cens_arm=float(np.mean([not runs[(i, c, arm)]['hit'] for i in imgs for c in CONDS])))


def stats_arm(runs, cid, imgs):
    rs = [runs[(i, c, cid)] for i in imgs for c in CONDS]; ct = [t for r in rs for o in r['tinfo'] for t in o]; outers = sum(len(r['tinfo']) for r in rs)
    rejit = sum(t['it'] for t in ct if not t['ok']); allit = sum(t['it'] for t in ct)
    capgap = [(r['F_final'] - r['tgt']) / (r['F0'] - r['tgt']) for r in rs if not r['hit'] and r['stop'] == 'max_iter']
    fb = sum(sum(r['fallback']) for r in rs); sel = [o for r in rs for o in r['sel'] if o]
    return dict(cid=cid, n=len(rs), cens=float(np.mean([not r['hit'] for r in rs])), W_med=float(np.median([RR.wval(r) for r in rs])), Wlow_med=float(np.median([wlow(r) for r in rs])), outer_med=float(np.median([r['outer'] for r in rs])),
                rej_it_share=float(rejit / max(allit, 1)), cap_share=float(np.mean([t['cap'] for t in ct])) if ct else float('nan'), trials_per_outer=float(len(ct) / max(outers, 1)), mid_checks_per_outer=float(sum(max(t.get('nacc', 1) - 1, 0) for t in ct) / max(outers, 1)),
                cap_gap_median=(float(np.median(capgap)) if capgap else None), cap_stop_n=len(capgap), oracle_fallback_share=float(fb / max(outers, 1)), sel_j_hist={str(j): int(sum(1 for o in sel if o['j'] == j)) for j in sorted({o['j'] for o in sel})} if sel else None,
                probe_cap_share=(float(np.mean([x == 'cap' for r in rs for pr in r['probe_reasons'] if pr for x in pr])) if any(pr for r in rs for pr in r['probe_reasons']) else None))


def quality(runs, sc, arm, imgs):
    d = [runs[(i, c, arm)]['psnr_final'] - runs[(i, c, sc)]['psnr_final'] for i in imgs for c in CONDS]
    return dict(median_dpsnr=float(np.median(d)), share_worse_005=float(np.mean([v < -0.05 for v in d])))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--stage', required=True, choices=['sc', 'gate', 'chk']); ap.add_argument('--out', default='outputs/RJ'); a = ap.parse_args(); runs = RR.load_runs(a.out)
    if a.stage == 'sc':
        best = json.load(open(os.path.join(a.out, 'tune_REDUCE.json')))['best_ids']; det = sorted(set(list(best.values()) + [RR.B0ID])); imgs = RR.NIMG_SEL
        st = {c: stats_arm(runs, c, imgs) for c in det}; sc = min(det, key=lambda c: (st[c]['W_med'], st[c]['cens'], st[c]['Wlow_med']))
        elig = [c for c in det if st[c]['cens'] <= 0.10]; sc_elig = min(elig, key=lambda c: (st[c]['W_med'], st[c]['Wlow_med'])) if elig else None
        json.dump(dict(sc=sc, sc_elig=sc_elig, sc_censor=st[sc]['cens'], rule='min median W_sp (censored=inf) over family bests + B0 on 301-312 x C1,C4; ties: fewer censored, lower lower-bound median', arms=st, best_ids=best), open(os.path.join(a.out, 'sc.json'), 'w'), indent=1, default=float)
        print('SC =', sc, 'censor', st[sc]['cens'], '| best eligible (censor<=10%%) =', sc_elig)
        for c in det: print(' ', c, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in st[c].items() if k not in ('cid', 'sel_j_hist', 'probe_cap_share')})
        return
    sc = json.load(open(os.path.join(a.out, 'sc.json')))['sc']; imgs = RR.NIMG_SEL if a.stage == 'gate' else RR.NIMG_CHK; B0 = RR.B0ID
    arms_all = [sc, B0] + [k + '@' + sc for k in ORC] + ['OS@' + sc, 'OKdF@' + B0, 'OS@' + B0]; st = {c: stats_arm(runs, c, imgs) for c in arms_all}
    res = dict(stage=a.stage, sc=sc, imgs=imgs, arms=st)
    for k in ORC: res['R_%s@SC_vs_SC' % k] = ratio_stats(runs, sc, k + '@' + sc, imgs)
    res['R_SC_vs_B0'] = ratio_stats(runs, B0, sc, imgs); res['R_OKdF@B0_vs_B0'] = ratio_stats(runs, B0, 'OKdF@' + B0, imgs); res['R_OS@SC_vs_SC'] = ratio_stats(runs, sc, 'OS@' + sc, imgs); res['R_OS@B0_vs_B0'] = ratio_stats(runs, B0, 'OS@' + B0, imgs)
    if a.stage == 'gate':
        gate_arm = max(ORC, key=lambda k: res['R_%s@SC_vs_SC' % k]['median']); res['gate_arm'] = gate_arm + '@' + sc; json.dump(dict(gate_arm=gate_arm + '@' + sc, sc=sc), open(os.path.join(a.out, 'gate_arm.json'), 'w'))
    else: gate_arm = json.load(open(os.path.join(a.out, 'gate_arm.json')))['gate_arm'].split('@')[0]; res['gate_arm'] = gate_arm + '@' + sc
    r = res['R_%s@SC_vs_SC' % gate_arm]; res['R_gate_vs_B0'] = ratio_stats(runs, B0, gate_arm + '@' + sc, imgs); cens_bad = r['cens_ctrl'] > 0.10 or r['cens_arm'] > 0.10
    res['quality'] = quality(runs, sc, gate_arm + '@' + sc, imgs); res['quality_warning'] = bool(res['quality']['share_worse_005'] > 0.25)
    det_all = sorted(set(list(json.load(open(os.path.join(a.out, 'sc.json')))['best_ids'].values()) + [B0])); stc = {c: stats_arm(runs, c, imgs) for c in det_all if all((i, cc_, c) in runs for i in imgs for cc_ in CONDS)}
    elig = [c for c in stc if stc[c]['cens'] <= 0.10]
    if elig and a.stage == 'gate':
        sce = min(elig, key=lambda c: (stc[c]['W_med'], stc[c]['Wlow_med'])); res['gate_O_elig_descriptive'] = dict(sc_elig=sce, note='descriptive only (A1/Q2): gate arm@SC vs the best control with censoring <=10%', R=ratio_stats(runs, sce, gate_arm + '@' + sc, imgs))
        if sce != sc and all((i, c0, k + '@' + sce) in runs for i in imgs for c0 in CONDS for k in ORC):                # clarification C1: oracle arms composed on the eligible control, defined before eval_orc ran
            for k in ORC: res['R_%s@SCelig_vs_SCelig' % k] = ratio_stats(runs, sce, k + '@' + sce, imgs)
            ge = max(ORC, key=lambda k: res['R_%s@SCelig_vs_SCelig' % k]['median']); res['gate_O_elig_descriptive']['gate_arm_elig'] = ge + '@' + sce; res['gate_O_elig_descriptive']['R_oracle_on_elig'] = res['R_%s@SCelig_vs_SCelig' % ge]
            res['gate_O_elig_descriptive']['R_elig_vs_B0'] = ratio_stats(runs, B0, sce, imgs)
    if a.stage == 'gate':
        passO = (r['median'] >= 1.5 and r['bca_lo'] >= 1.3 and r['sign'] >= 9); res['gate_O'] = 'INCONCLUSIVE(censoring>10%)' if cens_bad else ('PASS' if passO else 'FAIL')
        L_SC = float(np.log(res['R_SC_vs_B0']['median'])); L_OK = float(np.log(res['R_gate_vs_B0']['median']))
        res['gate_T'] = dict(L_SC=L_SC, L_OK=L_OK, deterministic_captures=bool(L_OK > 0 and L_SC >= (2.0 / 3.0) * L_OK), rule='L_SC >= 2/3 L_OK -> deterministic tuning suffices (no estimator)')
    else: res['gate_O_chk'] = 'INCONCLUSIVE(censoring>10%)' if cens_bad else ('PASS' if r['median'] >= 1.3 else 'FAIL')
    json.dump(res, open(os.path.join(a.out, ('eval' if a.stage == 'gate' else 'chk') + '_REDUCE.json'), 'w'), indent=1, default=float)
    print('SC =', sc, '| gate arm =', res['gate_arm'])
    for k in ORC:
        q = res['R_%s@SC_vs_SC' % k]; print('R %s@SC vs SC: median %.3f BCa [%.3f, %.3f] sign %d/%d cens ctrl %.2f arm %.2f flags %s' % (k, q['median'], q['bca_lo'], q['bca_hi'], q['sign'], q['n'], q['cens_ctrl'], q['cens_arm'], q['flags']))
    print('R SC vs B0 %.3f | gate arm vs B0 %.3f | OKdF@B0 vs B0 %.3f | OS@SC vs SC %.3f | OS@B0 vs B0 %.3f' % (res['R_SC_vs_B0']['median'], res['R_gate_vs_B0']['median'], res['R_OKdF@B0_vs_B0']['median'], res['R_OS@SC_vs_SC']['median'], res['R_OS@B0_vs_B0']['median']))
    print('gate:', res.get('gate_O') or res.get('gate_O_chk'), res.get('gate_T'), 'quality', res['quality'], 'warn', res['quality_warning'])
    for c in arms_all: print(' ', c, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in st[c].items() if k not in ('cid',)})


if __name__ == '__main__':
    main()
