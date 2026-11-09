# 004e  GLM result-auditor (READ-ONLY, narrow): do experiments/f3_run.py and experiments/f3_analyze.py implement contract v3 section 3 (fission + covariance df)?

Scope: ONLY experiments/f3_run.py (functions run_unit, stage_spec, build_tasks), experiments/f3_analyze.py (functions _legs, df_stat, Boot, est, and the place in main() where sig2 is set) and contracts/F0_CONTRACT_v3.md section 3 (estimands) and section 5 (seeds). Do not edit anything. Do not read other files.
Answer exactly these seven checks, one line each, in the final message, format `CHECK: ok|issue (file:line evidence)`:

FISSION: run_unit draws e from rng_for(1, ii, m) and z from rng_for(12, ii, m), both scaled by sigma0 (cfg.sigma0); then ep = e + z, em = e - z, yp = x + ep, ym = x + em; none of these depend on S or on the implementation (impl).
SHARED-OMEGA: for kind 'full' the legs F+, F-, G+, G-, the replay fit and the antithetic fit all use the same omega = omega_for(2, ii, m) (the P-lin branch uses omega_for(10, ii, m) for both copies).
GLEG: G+ is fit on yp with forced_idx = Im (the birth indices recorded from the fit on ym) and G- is fit on ym with forced_idx = Ip (indices recorded from the fit on yp); neither G leg uses its own copy's indices.
LEAK-IN: every fitter call (fit_pipeline / plin_pipeline / plin_frozen) receives, as its data argument, only R(yp), R(ym) or (antithetic only) R(x - ep); the clean image x is never passed any other way.
ESTIMATOR: df_stat computes Sum_m[(Xp_m - Xbar_p).ep_m + (Xm_m - Xbar_m).em_m] / ((M-1) * 2 * sig2) (algebraically, also when resample weights W are given), and main() passes sig2 = 2*sigma0^2.
SDF-DEF: _legs('sdf') returns (Fp - Gp, Fm - Gm); _legs('par') returns (Gp, Gm); est() computes the point estimate with df_stat and the SE as the sample std (ddof=1) of the bootstrap statistics; Boot draws indices from SeedSequence(entropy=20261106, spawn_key=(13,)) with B=1000 resamples of size M.
S8: for S == 8 the runner asserts the birth-index lists of the two copies are equal (idx_equal) and, when the G leg is not run (Stage 1, m >= 8), sets G = F.

If any check cannot be answered from these files, write `CHECK: unknown (reason)`. Final message must contain only the seven lines.
