"""AS contract v2.1 EVALUATOR-SIDE oracle (ORACLE_xs / ORACLE_x-full): may read the clean image; writes only diagnostic outputs; never imported by method code (V6 exemption, V17).
Selection among trial refits (T_o=8 steps) by clean-image MSE; the chosen edit is then re-executed with the standard function for T_r=15 steps (parity with rule arms)."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import as_core as C


def mse(th, clean):
    return float(np.mean((C.render(th) - clean) ** 2))


def run_oracle_x(y, op, sn, clean, mode='short', topk=8, T_o=8, S=30, Tr=15, T0=30, ckpt=None):
    t_start = time.time(); tr0, lg0 = C._ckpt_load(ckpt)
    if tr0 is not None: traj, logs = tr0, lg0; th = np.array(traj[-1])
    else: th, L, _ = C.initial_state(op, y, sn, 6.0, T0); traj = [th.tolist()]; logs = []
    for step in range(len(logs), S):
        r_img = y - op.apply(C.render(th)); cands, ncl = C.gen_candidates(op, th, r_img)
        AJ, Uk, blocks, s0, us = C.projectors(op, th); sc, aux = C.score_candidates(op, th, y, cands, AJ, Uk, blocks)
        if mode == 'full': idxs = list(range(len(cands)))
        else:
            sel = set()
            for k in C.RULES:
                s = sc[k].copy(); s[~np.isfinite(s)] = -np.inf
                sel.update(int(i) for i in np.argsort(-s, kind='stable')[:topk] if np.isfinite(s[i]))
            idxs = sorted(sel)
        best = None
        for c in idxs:
            t, Lc, info = C.execute(op, y, th, cands[c], aux['c0'][c], aux['cols'][c], sn, T_o)
            m = mse(t, clean)
            if best is None or m < best[1]: best = (t, m, c)
        th, Ln, info = C.execute(op, y, th, cands[best[2]], aux['c0'][best[2]], aux['cols'][best[2]], sn, Tr)
        traj.append(th.tolist())
        logs.append(dict(step=step, n_cand=len(cands), cand_hash=C.cand_hash(cands), n_trials=len(idxs), chosen=int(best[2]), chosen_type=cands[best[2]]['type'], trial_mse=best[1], train_loss=float(Ln)))
        C._ckpt_save(ckpt, traj, logs)
    return dict(rule='ORACLE_x_' + mode, traj=traj, logs=logs, t_total=time.time() - t_start)
