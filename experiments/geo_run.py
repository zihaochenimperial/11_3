"""GEO experiment runner (method-side solver runs only; reads NO clean image except to synthesise y through geo_gen).
Jobs (contract v2 + pre-D addendum K1): tune_geo, fref, calib_caps, tune_arms, vpass, lamgrid, vpass_lam, h_q2, h_q1, ypair, timing.
Every unit writes one .npz (meta JSON + arrays) under outputs/GEO-<job>/..., skipped if present (restartable). Usage:
  python geo_run.py job=<name> [shard=i/n] [deadline_s=<sec>] [cells=<tune|dev|h201|h202|h12>] [lam=<float>] [reps=<int>] [only=<ARM>]
Selection logic lives in geo_analyze.py (evaluator side) and writes outputs/GEO-D/choices.json, which later jobs read."""
import os, sys, json, time
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_v] = '1'
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'src'))
import numpy as np
import geo_core as GC
import geo_gen as GG

N = 32
CONDS = ('C1', 'C2', 'C3', 'C4'); KS = (16, 36)
TUNE_IMGS = list(range(101, 107)); TUNE_CONDS = ('C1', 'C4')
LAM_TUNE = 1e-3
LAM_GRID = (0.0, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1)
TAU_GRID = (0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0)
GEO_GRID = [dict(kappa0=1e-3, f=f, rcond=r) for r in (1e-8, 1e-4, 1e-2) for f in (3, 10)]
LM_GRID = [dict(kappa0=k, f=f) for k in (1e-4, 1e-3, 1e-2) for f in (3, 10)]
GEO_FAMILY = ('GEO', 'BJ', 'BLK')
ARMS_Q2 = ('LMD', 'GEO', 'GEO-r8', 'BJ', 'BLK', 'LSMR', 'PCG8P', 'PCG8D')
OUT = os.path.join(ROOT, 'outputs')


def tag_of(cfg):
    if 'rcond' in cfg: return 'r%.0e_f%d' % (cfg['rcond'], cfg['f'])
    return 'k%.0e_f%d' % (cfg['kappa0'], cfg['f'])


def lam_tag(lam):
    return 'lam%.0e' % lam if lam > 0 else 'lam0'


def cell_list(which):
    if which == 'tune': return [(i, c, K, 9101) for i in TUNE_IMGS for c in TUNE_CONDS for K in KS]
    if which == 'dev': return [(i, c, K, 9101) for i in GG.DEV_IMGS for c in CONDS for K in KS]
    if which == 'h201': return [(i, c, K, 9201) for i in GG.TEST_IMGS for c in CONDS for K in KS]
    if which == 'h202': return [(i, c, K, 9202) for i in GG.TEST_IMGS for c in CONDS for K in KS]
    if which == 'h12': return [(i, c, K, 9201) for i in GG.TEST_IMGS[:12] for c in CONDS for K in KS]
    if which == 'h6': return [(i, c, K, 9201) for i in GG.TEST_IMGS[:6] for c in CONDS for K in KS]
    raise ValueError(which)


DESC_ARMS = ('LSMR', 'PCG8P', 'PCG8D')                   # descriptive arms (compression step 1 may restrict them to images 201-212)
DEFAULT_PLAN = dict(desc_imgs='all', ypair_imgs='h12', timing_imgs='h12', q1_bases=[9201, 9202], steps=[])


def plan_of(ch):
    """Compression plan fixed once at the end of phase D (analyzer `plan`), read-only in phase H (K1 item 10(vi))."""
    return dict(DEFAULT_PLAN, **(ch.get('plan') or {}))


def make_cell(img, cond, K, base, lam):
    sb, sn = GG.COND[cond]
    op = GC.Op(N, sb); x = GG.clean_image_geo(img); y = GG.noisy_obs_geo(op, x, sn, base, img)      # y is all the method side ever sees
    P = GC.Prob(N, sb, y, sn, lam / sn ** 2); return P, GC.grid_init(P, K)


def thin_idx(n):
    return list(range(n))                                  # K1 R1: every iterate is stored (cap / threshold readings are exact, no interpolation)


def summarize(res):
    d = res['diag']; it = max(len(res['traj']) - 1, 1)
    out = dict(stop=res['stop'], iters=len(res['traj']) - 1, rej=res['rej'], clamp_rate=res['clamp_rate'], clamp_entries_per_trial=res['clamp_entries_per_trial'], trials=res['trials'],
               cnt={k: float(v) for k, v in res['cnt'].items()}, T={k: float(v) for k, v in res['T'].items()}, kappa=float(res['kappa']), F=float(res['F']),
               act_mean=float(np.mean(res['act'])) if res['act'] else 0.0, itn_mean=float(np.mean(res['itn'])) if res['itn'] else None,
               alpha_mean=float(np.mean(res['alpha'])) if res['alpha'] else None, alpha_lt1=float(np.mean(np.array(res['alpha']) < 1)) if res['alpha'] else None,
               blk_skip=int(res['blk_skip']), blk_eval=int(res['blk_eval']), wall=float(res['traj'][-1][2]),
               alpha_star_gt1=(float(np.mean(np.array(res['alpha_star']) > 1.0)) if res['alpha_star'] else None), alpha_star_n=len(res['alpha_star']),
               clamp_it_mean=float(np.mean(res['clamp_it'])) if res['clamp_it'] else 0.0, no_step_clamp=bool(res['stop'] == 'no_step_clamp'), safety_censored=bool(res['stop'] == 'safety'))
    if d:
        out['diag'] = dict(cond_med=float(np.median([e['cond'] for e in d])), cond_max=float(np.max([e['cond'] for e in d])), rank_med=float(np.median([e['rank'] for e in d])),
                           near_zero_w_max=int(np.max([e['near_zero_w'] for e in d])), outside_max=int(np.max([e['outside'] for e in d])))
    return out


def save_unit(path, meta, res, extra=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tr = np.array(res['traj'], dtype=float); keep = thin_idx(len(tr))
    arrays = dict(theta=res['theta'], traj=tr[keep][:, [0, 1, 2, 3, 6, 7, 8, 9]])          # it, F, t, A, W, rss, Ad, Wd
    if extra: arrays.update(extra)
    meta = dict(meta); meta.update(summarize(res))
    tmp = path + '.tmp.npz'
    np.savez_compressed(tmp, meta=json.dumps(meta), **arrays); os.replace(tmp, path)


def load_choices():
    p = os.path.join(OUT, 'GEO-D', 'choices.json')
    if not os.path.exists(p): raise SystemExit('choices.json missing: run geo_analyze.py first')
    return json.load(open(p))


def arm_setup(arm, ch):
    """-> (solver_name, cfg)."""
    if arm == 'GEO-r8': return 'GEO', dict(kappa0=1e-3, f=ch['GEO_r8']['f'], rcond=1e-8)
    c = ch[arm]; cfg = dict(kappa0=c['kappa0'], f=c['f'])
    if arm in GEO_FAMILY: cfg['rcond'] = c['rcond']
    return arm, cfg


def run_arm(solver, P, th0, cfg, caps, keep_theta=False, max_iter=200):
    if caps is None: return GC.solve(solver, P, th0, cfg, max_iter=max_iter, keep_theta=keep_theta)
    return GC.solve(solver, P, th0, cfg, A_cap=caps['A'], W_cap=caps['W'], keep_theta=keep_theta)


def tau_crossings(res, P):
    """First accepted iterate with ||y-Ax||^2 <= tau N^2 sn^2 for each tau in TAU_GRID: (index or -1, theta). Uses the in-memory theta history."""
    rss = np.array([e[7] for e in res['traj']]); thr_base = P.N ** 2 * P.sn ** 2; idx = []
    for tau in TAU_GRID:
        hit = np.where(rss[1:] <= tau * thr_base)[0]
        idx.append(int(hit[0] + 1) if hit.size else -1)
    ths = np.stack([res['th_hist'][i] if i >= 0 else res['theta'] for i in idx])
    return dict(tau_idx=np.array(idx), tau_theta=ths)


class Runner:
    def __init__(self, argv):
        kv = dict(a.split('=', 1) for a in argv if '=' in a)
        self.job = kv['job']; self.kv = kv
        s = kv.get('shard', '0/1').split('/'); self.si, self.sn = int(s[0]), int(s[1])
        self.deadline = float(kv['deadline_s']) if 'deadline_s' in kv else None
        self.t0 = time.perf_counter(); self.done = 0; self.skipped = 0; self.cnt = 0

    def time_up(self):
        return self.deadline is not None and (time.perf_counter() - self.t0) > self.deadline

    def units(self, items):
        """items: list of (path, fn); shard by index, skip existing; fn() does the work and saves."""
        for n, (path, fn) in enumerate(items):
            if n % self.sn != self.si: continue
            self.cnt += 1
            if os.path.exists(path): self.skipped += 1; continue
            if self.time_up(): print('DEADLINE reached, exiting with partial results', flush=True); return False
            t = time.perf_counter(); fn()
            self.done += 1
            print('[%s %d/%d] %s %.1fs (elapsed %.0fs)' % (self.job, n + 1, len(items), os.path.relpath(path, OUT), time.perf_counter() - t, time.perf_counter() - self.t0), flush=True)
        return True

    # ---------------------------------------------------------------- jobs
    def job_tune_geo(self):
        items = []
        for (i, c, K, b) in cell_list('tune'):
            for cfg in GEO_GRID:
                path = os.path.join(OUT, 'GEO-D', 'tune_geo', 'GEO_%s_K%d_i%d_%s.npz' % (c, K, i, tag_of(cfg)))
                items.append((path, (lambda i=i, c=c, K=K, b=b, cfg=cfg, path=path: self._run_one(path, 'GEO', 'GEO', cfg, i, c, K, b, LAM_TUNE, None))))
        return self.units(items)

    def _run_one(self, path, arm, solver, cfg, i, c, K, b, lam, caps, keep_theta=False, taus=False, max_iter=200, cap_theta=False):
        P, th0 = make_cell(i, c, K, b, lam)
        res = run_arm(solver, P, th0, cfg, caps, keep_theta=keep_theta or taus or cap_theta, max_iter=max_iter)
        extra = tau_crossings(res, P) if taus else {}
        if cap_theta and caps is not None:                                  # theta at the last iterate with A_eff <= A_cap / W_eff <= W_cap (quality readings, K1 R6)
            tr = np.array(res['traj'], dtype=float); Ae = tr[:, 3] - tr[:, 8]; We = tr[:, 6] - tr[:, 9]
            iA = int(np.where(Ae <= caps['A'])[0][-1]); iW = int(np.where(We <= caps['W'])[0][-1])
            extra.update(theta_Acap=res['th_hist'][iA], theta_Wcap=res['th_hist'][iW], cap_idx=np.array([iA, iW]))
        meta = dict(arm=arm, solver=solver, cfg=cfg, img=i, cond=c, K=K, base=b, lam=lam, caps=caps, F0=float(P.F_of(th0)[0]))
        save_unit(path, meta, res, extra or None)

    def job_fref(self):
        cells = cell_list(self.kv.get('cells', 'tune')); lam_mode = self.kv.get('lam', str(LAM_TUNE))
        ch = load_choices() if lam_mode == 'star' else None
        items = []
        for (i, c, K, b) in cells:
            lam = LAM_TUNE if ch is None else ch['lam_star']['%s_K%d' % (c, K)]
            for r in range(3):
                path = os.path.join(OUT, 'GEO-D' if b == 9101 else 'GEO-H', 'fref', 'FREF_%s_K%d_i%d_b%d_%s_r%d.npz' % (c, K, i, b, lam_tag(lam), r))
                items.append((path, (lambda i=i, c=c, K=K, b=b, lam=lam, r=r, path=path: self._fref_one(path, i, c, K, b, lam, r))))
        return self.units(items)

    def _fref_one(self, path, i, c, K, b, lam, r):
        P, th0 = make_cell(i, c, K, b, lam)
        th0 = th0.copy(); th0[:, 1:3] += 0.5 * GG.rng_of(2, b, i, r).standard_normal((K, 2))
        res = GC.solve('LMD', P, th0, dict(kappa0=1e-3, f=3), max_iter=500)
        save_unit(path, dict(arm='FREF', img=i, cond=c, K=K, base=b, lam=lam, restart=r), res)

    def job_calib_caps(self):
        ch = load_choices(); items = []
        for (i, c, K, b) in cell_list('dev'):
            cfg = dict(kappa0=1e-3, f=ch['GEO']['f'], rcond=ch['GEO']['rcond'])
            path = os.path.join(OUT, 'GEO-D', 'calib', 'GEO_%s_K%d_i%d.npz' % (c, K, i))
            items.append((path, (lambda i=i, c=c, K=K, b=b, cfg=cfg, path=path: self._run_one(path, 'GEO', 'GEO', cfg, i, c, K, b, LAM_TUNE, None))))
        return self.units(items)

    def job_tune_arms(self):
        ch = load_choices(); items = []
        only = self.kv.get('only')
        for arm in ('BJ', 'BLK', 'LMD', 'LSMR', 'PCG8P', 'PCG8D'):
            if only and arm != only: continue
            grid = GEO_GRID if arm in GEO_FAMILY else LM_GRID
            for (i, c, K, b) in cell_list('tune'):
                for cfg in grid:
                    path = os.path.join(OUT, 'GEO-D', 'tune_arms', '%s_%s_K%d_i%d_%s.npz' % (arm, c, K, i, tag_of(cfg)))
                    items.append((path, (lambda arm=arm, i=i, c=c, K=K, b=b, cfg=cfg, path=path: self._run_one(path, arm, arm, cfg, i, c, K, b, LAM_TUNE, ch['caps'][str(K)], max_iter=200))))
        return self.units(items)

    def job_vpass(self):
        ch = load_choices(); items = []
        for arm in ('GEO', 'LMD', 'GEO-r8'):
            for (i, c, K, b) in cell_list('dev'):
                solver, cfg = arm_setup(arm, ch)
                path = os.path.join(OUT, 'GEO-D', 'vpass', '%s_%s_K%d_i%d.npz' % (arm, c, K, i))
                items.append((path, (lambda arm=arm, solver=solver, cfg=cfg, i=i, c=c, K=K, b=b, path=path: self._run_one(path, arm, solver, cfg, i, c, K, b, LAM_TUNE, ch['caps'][str(K)]))))
        return self.units(items)

    def job_lamgrid(self):
        ch = load_choices(); items = []
        solver, cfg = arm_setup('GEO', ch)
        for lam in LAM_GRID:
            for (i, c, K, b) in cell_list('dev'):
                path = os.path.join(OUT, 'GEO-D', 'lamgrid', 'GEO_%s_K%d_i%d_%s.npz' % (c, K, i, lam_tag(lam)))
                items.append((path, (lambda i=i, c=c, K=K, b=b, lam=lam, path=path: self._run_one(path, 'GEO', solver, cfg, i, c, K, b, lam, ch['caps'][str(K)], taus=(lam == 0.0)))))
        return self.units(items)

    def job_vpass_lam(self):
        """Amended-V re-check at lambda* (Opus addition (1)): LMD (budgeted, caps fixed at lambda=1e-3) on the 96 dev cells at lambda*_{cond,K}; GEO at lambda* is the lamgrid run."""
        ch = load_choices(); items = []; solver, cfg = arm_setup('LMD', ch)
        for (i, c, K, b) in cell_list('dev'):
            lam = ch['lam_star']['%s_K%d' % (c, K)]
            path = os.path.join(OUT, 'GEO-D', 'vpass_lam', 'LMD_%s_K%d_i%d_%s.npz' % (c, K, i, lam_tag(lam)))
            items.append((path, (lambda i=i, c=c, K=K, b=b, lam=lam, path=path: self._run_one(path, 'LMD', solver, cfg, i, c, K, b, lam, ch['caps'][str(K)]))))
        return self.units(items)

    def job_h_q2(self):
        ch = load_choices(); pl = plan_of(ch); items = []
        desc_ok = set(i for (i, c, K, b) in cell_list('h12')) if pl['desc_imgs'] == 'h12' else None
        for (i, c, K, b) in cell_list('h201'):
            lam = ch['lam_star']['%s_K%d' % (c, K)]
            for arm in ARMS_Q2:
                if arm in DESC_ARMS and desc_ok is not None and i not in desc_ok: continue
                solver, cfg = arm_setup(arm, ch)
                path = os.path.join(OUT, 'GEO-H', 'q2', '%s_%s_K%d_i%d_b%d.npz' % (arm, c, K, i, b))
                items.append((path, (lambda arm=arm, solver=solver, cfg=cfg, i=i, c=c, K=K, b=b, lam=lam, path=path: self._run_one(path, arm, solver, cfg, i, c, K, b, lam, ch['caps'][str(K)], cap_theta=True))))
        return self.units(items)

    def job_h_q1(self):
        ch = load_choices(); items = []
        solver, cfg = arm_setup('GEO', ch); lmd_s, lmd_cfg = arm_setup('LMD', ch)
        pl = plan_of(ch)
        for which in ('h201', 'h202'):
            if which == 'h202' and 9202 not in pl['q1_bases']: continue
            for (i, c, K, b) in cell_list(which):
                lam = ch['lam_star']['%s_K%d' % (c, K)]; caps = ch['caps'][str(K)]
                if b == 9202:
                    path = os.path.join(OUT, 'GEO-H', 'q1', 'GEO_%s_K%d_i%d_b%d.npz' % (c, K, i, b))
                    items.append((path, (lambda i=i, c=c, K=K, b=b, lam=lam, caps=caps, path=path: self._run_one(path, 'GEO', solver, cfg, i, c, K, b, lam, caps))))
                path = os.path.join(OUT, 'GEO-H', 'q1', 'F0GEO_%s_K%d_i%d_b%d.npz' % (c, K, i, b))
                items.append((path, (lambda i=i, c=c, K=K, b=b, caps=caps, path=path: self._run_one(path, 'F0GEO', solver, cfg, i, c, K, b, 0.0, caps, taus=True))))
                path = os.path.join(OUT, 'GEO-H', 'q1', 'F0LMD_%s_K%d_i%d_b%d.npz' % (c, K, i, b))
                items.append((path, (lambda i=i, c=c, K=K, b=b, caps=caps, path=path: self._run_one(path, 'F0LMD', lmd_s, lmd_cfg, i, c, K, b, 0.0, caps, taus=True))))
        return self.units(items)

    def job_ypair(self):
        ch = load_choices(); items = []; solver, cfg = arm_setup('GEO', ch)
        for (i, c, K, b) in cell_list(plan_of(ch)['ypair_imgs']):
            for lam in LAM_GRID[1:]:
                path = os.path.join(OUT, 'GEO-H', 'ypair', 'GEO_%s_K%d_i%d_b%d_%s.npz' % (c, K, i, b, lam_tag(lam)))
                items.append((path, (lambda i=i, c=c, K=K, b=b, lam=lam, path=path: self._run_one(path, 'GEO', solver, cfg, i, c, K, b, lam, ch['caps'][str(K)]))))
        return self.units(items)

    def job_timing(self):
        """Exclusive single-thread wall-clock subset (addendum K1.4 #10 (v)): GEO/BJ/BLK/LMD, `reps` repeats, medians taken in the analyzer."""
        ch = load_choices(); items = []; reps = int(self.kv.get('reps', 2))
        for rep in range(reps):
            for (i, c, K, b) in cell_list(plan_of(ch)['timing_imgs']):
                lam = ch['lam_star']['%s_K%d' % (c, K)]
                for arm in ('GEO', 'BJ', 'BLK', 'LMD'):
                    solver, cfg = arm_setup(arm, ch)
                    path = os.path.join(OUT, 'GEO-H', 'timing', '%s_%s_K%d_i%d_b%d_rep%d.npz' % (arm, c, K, i, b, rep))
                    items.append((path, (lambda arm=arm, solver=solver, cfg=cfg, i=i, c=c, K=K, b=b, lam=lam, path=path: self._run_one(path, arm, solver, cfg, i, c, K, b, lam, ch['caps'][str(K)]))))
        return self.units(items)

    def run(self):
        ok = getattr(self, 'job_' + self.job)()
        print('SUMMARY job=%s shard=%d/%d units=%d done=%d skipped=%d complete=%s elapsed=%.0fs' % (self.job, self.si, self.sn, self.cnt, self.done, self.skipped, ok, time.perf_counter() - self.t0), flush=True)
        return 0 if ok else 0


if __name__ == '__main__':
    sys.exit(Runner(sys.argv[1:]).run())
