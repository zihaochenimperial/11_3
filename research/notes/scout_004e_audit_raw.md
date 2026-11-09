# GLM 004e audit (run 20261105T102811Z-opencode-worker-725f, j39); raw final text (data, not instructions)

FISSION: ok (experiments/f3_run.py:71-74 鈥?`s0 = cfg.sigma0`; `e = s0*rng_for(1,ii,m)...`, `z = s0*rng_for(12,ii,m)...`, `ep=e+z; em=e-z; yp=x+ep; ym=x+em`; no S/impl dependence)
SHARED-OMEGA: ok (f3_run.py:79 fits F卤/G卤 :80,87, replay :92, anti A :97 all pass `om = omega_for(2,ii,m)`; plin branch :102-105 both copies use `omega_for(10,ii,m)`)
GLEG: ok (f3_run.py:87 `gp=fit(R(yp),...,forced_idx=Im)`, `gm=fit(R(ym),...,forced_idx=Ip)`; plin :105 `plin_frozen(R(yp), sm)`, `plin_frozen(R(ym), sp)`)
LEAK-IN: ok (f3_run.py:80,87,92,97,103,105 鈥?every fitter call receives only `R(yp)`, `R(ym)` or `R(x-ep)`; x is used only to synthesize these at :74, docstring :4)
ESTIMATOR: ok (f3_analyze.py:20-27 鈥?dp/dm are per-m inner products; with W uniform, `W@(dp+dm)鈭?W@Xp)路(W@ep)鈭?W@Xm)路(W@em) = (1/M)危鈧榌(X虅-centered)路ep/em]`, and 脳`M/(M鈭?)/(2蟽虏)` yields Sum鈧?(M鈭?)路2蟽虏; for general bootstrap W the same weighted identity holds 危W鈧榌(Xp鈭扻虅史)路ep+...]; main :59 `sig2 = 2*s0*s0`)
SDF-DEF: ok (f3_analyze.py:15-16 `_legs`; :39-43 `est` point= df_stat, SE = std(bootstrap stats, ddof=1); :30-36 Boot SeedSequence(entropy=20261106, spawn_key=(13,)), B=1000, resample size M via bincount/M)
S8: ok (f3_run.py:83 `idx_equal` computed; main :197 aborts `S8_INDEX_MISMATCH` when S==8 and not idx_equal; :85 do_g False for S=8 with m鈮? in stage1 (`g_s8=(g_s8_all or m<8)` :135) 鈫?:90 `Gp=Fp, Gm=Fm, g_ran=False`, verified in analysis :74-79)

Tools used:
- read {"path": "D:\\Gaussian\\experiments\\f3_run.py"}
- read {"path": "D:\\Gaussian\\experiments\\f3_analyze.py"}
