# 004d  GLM result-auditor (READ-ONLY, narrow): does src/gsfast.py reproduce src/gsfit.py's pipeline logic?

Scope: ONLY these three files: src/gsfit.py, src/gsfast.py, src/gskernel.py. Do not edit anything. Do not read other files except src/f0_config.py and src/omega.py if needed.
Answer exactly these five checks, one line each, in the final message, format `CHECK: ok|issue (file:line evidence)`:

PARITY-INIT: gsfast._init and gsfit's initialisation draw the same random numbers in the same order from omega_rng(omega, 0) (xy, then val; same shapes/scales).
PARITY-BIRTH: gsfast._birth_round and gsfit's birth round use the same candidate permutation (omega_rng(omega, 1+r).permutation(N)[:S]), the same smoothing of the residual (y - f_cur, sigma=cfg.smooth_sigma_px), the same selection rule (largest |smoothed residual|, ties by stable sort), ascending order of chosen indices, same new-atom init (position at pixel centre, birth scale, rot 0, value = f_cur + smoothed residual at that pixel).
PARITY-FORCED: with forced_idx the fast path consumes no extra RNG and uses the given indices unchanged in the same way as the torch path.
PARITY-OPT: per stage, Adam hyper-parameters (lrs per group, betas, eps) and step count match gsfit; the optimiser state is created fresh per stage in both (or both carry it); non-finite loss/params raise in both; no clipping.
LEAKAGE: neither gsfast.py nor gskernel.py imports or reads src/synth.py or src/reference_eval.py or any clean image.

If any check cannot be answered from these files, write `CHECK: unknown (reason)`. Final message must contain only the five lines.
