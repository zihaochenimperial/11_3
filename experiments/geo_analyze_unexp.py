"""GEO pre-registered reporting-only view (contract addendum K2, appended before the first formal H result): the SAME frozen H readings of geo_analyze.py, recomputed on the 20 UNEXPOSED test images 205-224.
Images 201-204 were seen in dry-run analysis output (FAIL-0029); they stay in the frozen 24-image primary reading, which therefore cannot be called fully unseen evidence.
This file imports geo_analyze UNCHANGED (its sha is frozen in K1.9): no new metric, no new threshold, no re-run, no configuration change. The only derived numbers are the image-count floors, scaled to the same 50%:
  MIN_IMG_A = 10 (50% of the DESIGNED 20 unexposed Q2 images; frozen 12/24), MIN_IMG_T = ceil(0.5 * DESIGNED unexposed timing images) when that design count >= 4 (frozen 6/12; plan h12 -> 8, h6 -> 2).
  Image counts come from the DESIGN (GG.TEST_IMGS and choices.json plan['timing_imgs']), not from whichever files exist: fewer images present than designed, or a designed timing count < 4 -> the view is 'NOT EVALUABLE' (per-K labels and overall).
  The 20-image view can only DEMOTE a label, never raise one. Labels are compared by category (JOINT-MATTERS / JOINT-NOT-MATTERS / INCONCLUSIVE; REG-HELPS / REG-HURTS / REG-NEUTRAL), not by reason suffix.
Usage: python geo_analyze_unexp.py [run]   -> writes outputs/UNEXP20/GEO-H/*.json and outputs/UNEXP20/CONSISTENCY.json (24-image primary vs 20-image view)."""
import os, sys, json, math, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import geo_analyze as A

EXPOSED = (201, 202, 203, 204)


def run(exposed=EXPOSED, real_out=None):
    real = real_out or A.OUT; view = os.path.join(real, 'UNEXP20')
    os.makedirs(os.path.join(view, 'GEO-H'), exist_ok=True); os.makedirs(os.path.join(view, 'GEO-D'), exist_ok=True)
    for f in ('choices.json', 'V_PASS_DEV.json', 'V_PASS_LAMSTAR.json'): shutil.copy(os.path.join(real, 'GEO-D', f), os.path.join(view, 'GEO-D', f))
    orig_runs_in = A.runs_in; orig_out = A.OUT

    def runs_in_unexposed(*subdirs):
        A.OUT = real
        try: r = orig_runs_in(*subdirs)
        finally: A.OUT = view
        return [(m, a) for m, a in r if m.get('img') not in exposed]
    A.runs_in = runs_in_unexposed; A.OUT = view
    try:
        import geo_gen as GG
        ch = A.load_ch(); tim_design = ch.get('plan', {}).get('timing_imgs', 'h12'); tim_pool = GG.TEST_IMGS[:12] if tim_design == 'h12' else GG.TEST_IMGS[:6]
        d_q2 = len([i for i in GG.TEST_IMGS if i not in exposed]); d_t = len([i for i in tim_pool if i not in exposed])
        n_img = len({m['img'] for m, _ in runs_in_unexposed('GEO-H/q2')}); n_t = len({m['img'] for m, _ in runs_in_unexposed('GEO-H/timing')})
        A.MIN_IMG_A = int(math.ceil(0.5 * d_q2)) if d_q2 else 10**9; A.MIN_IMG_T = int(math.ceil(0.5 * d_t)) if d_t >= 4 else 10**9
        complete = bool(n_img >= d_q2 and (d_t < 4 or n_t >= d_t)); timing_ok = bool(d_t >= 4 and n_t >= d_t)
        meta = dict(exposed=list(exposed), design_unexposed_q2_images=d_q2, n_unexposed_q2_images_present=n_img, plan_timing_imgs=tim_design, design_unexposed_timing_images=d_t, n_unexposed_timing_images_present=n_t,
                    MIN_IMG_A=A.MIN_IMG_A, MIN_IMG_T=(A.MIN_IMG_T if d_t >= 4 else None), q2_complete=bool(n_img >= d_q2), timing_evaluable=timing_ok)
        A.cmd_h_q2(); A.cmd_q2_quality(); A.cmd_h_timing(); lab = A.cmd_q2_label(); q1 = A.cmd_h_q1()
    finally:
        A.runs_in = orig_runs_in; A.OUT = orig_out
    # consistency with the frozen 24-image primary reading (labels compared by category; the view can only demote)
    prim = json.load(open(os.path.join(real, 'GEO-H', 'Q2_LABEL.json'))); prim_q1 = json.load(open(os.path.join(real, 'GEO-H', 'Q1_quality.json')))
    cat = lambda x: 'NOT-EVALUABLE' if str(x).startswith('NOT EVALUABLE') else str(x).split(' ')[0]
    cons = dict(meta=meta, primary_24_overall=prim.get('overall'), view_20_overall=None, per_K={}, q1={})
    view_ok = bool(meta['q2_complete'] and meta['timing_evaluable'])
    for K in A.R.KS:
        k = str(K); p = prim[k]['label']; v = lab[k]['label'] if view_ok else 'NOT EVALUABLE'
        cons['per_K'][k] = dict(primary=p, view20=v, primary_category=cat(p), view20_category=cat(v), same=bool(view_ok and cat(p) == cat(v)))
        pq = prim_q1.get(k, prim_q1.get(K)); vq = q1.get(K, q1.get(k))
        if pq is None or vq is None: cons['q1'][k] = dict(primary=(pq or {}).get('label'), view20='NOT EVALUABLE', same=False)
        else: cons['q1'][k] = dict(primary=pq['label'], view20=vq['label'], same=bool(cat(pq['label']) == cat(vq['label'])))
    cons['view_20_overall'] = lab.get('overall') if view_ok else 'NOT EVALUABLE (the 20-image view lacks designed images or has fewer than 4 designed unexposed timing images)'
    same_all = view_ok and all(v['same'] for v in cons['per_K'].values()) and all(v['same'] for v in cons['q1'].values()) and bool(cons['q1'])
    cons['depends_on_exposed_images'] = bool(not same_all)
    cons['rule'] = ('K2: the 20-image view is a subset of the same sample, not an independent replication; it can only demote a label, never raise one. If any per-K Q2 label category or any Q1 label category differs between the 24-image primary and the 20-image view, '
                    'or the view is NOT EVALUABLE, every positive or directional claim (Q2 JOINT-MATTERS/ADVANCE, Q1 REG-HELPS/REG-HURTS) is blocked: it must not be written as ADVANCE and waits for fresh-data confirmation; neutral/negative primary labels are reported as they are with both readings and the difference.')
    json.dump(cons, open(os.path.join(view, 'CONSISTENCY.json'), 'w'), indent=1, default=str); print(json.dumps(cons, indent=1, default=str)); return cons


if __name__ == '__main__':
    run()
