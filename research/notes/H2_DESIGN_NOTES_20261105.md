# H2 design notes (PROPOSED, unreviewed, not a contract; written 2026-11-05 while Stage 1 runs; no H2 result exists)
Status labels: everything below is *proposed*. It becomes a contract only if H1 holds (Stage 1, contract v3 section 6), after a real Opus gate. If H1 fails the estimator line STOPs (no-v4) and this file is moot.

## What H2 must show (from the standing mandate)
Without clean data, estimate the search degrees of freedom (sdf) of the adaptive-Gaussian pipeline from the noisy image alone, and use the correction to make birth / freeze / stop decisions that beat baselines **at equal wall time**.

## Decision task (candidate): choose the search budget S per image (S in {8, 64, 1024}) — or when to stop births — by minimising an estimated risk
Risk(S) = E||f_S(y) - x||^2. Single-image estimator family: R_hat(S) = ||f_S(y) - y||^2 + 2 sigma0^2 df_hat(S) - N sigma0^2. Oracle regret is measured on synthetic images where x is known (x is used only by the evaluator, never by an estimator).

## Candidate estimators / baselines (all must get the same wall-time budget)
1. Param-count df (6 K): ignores sdf. Expected to over-select large S if sdf is real. (cheapest; the null the correction must beat)
2. Fixed Friedman-style per-birth charge (d per birth, d = 2..4): 1991 GCV precedent (secondary source only, G0 log S11). The pilot's exploratory per-birth sdf is of the same order (not an H2 result).
3. MC-SURE / Ye-GDF perturbation slope (finite difference): v2 showed the 600-step pipeline is numerically chaotic below ~0.1 sigma0, so small-eps FD is not identifiable here (labelled post-hoc diagnostic); include at eps >= 0.3 sigma0 for fairness.
4. **Data-fission / coupled-bootstrap cross-validation (the strongest baseline, derivative-free, no df at all):** from y alone form y+ = y + g z, y- = y - z/g (z ~ N(0, sigma0^2)); the copies are independent given x; E||f(y+) - y-||^2 = risk at inflated noise sigma0^2(1+g^2) + N sigma0^2 (1+1/g^2). One fit per replicate. If this baseline already picks S as well as the sdf-corrected SURE at lower cost, **the sdf correction has no decision value** and the project line should say so.
5. Proposed method: R_hat with df_hat = df_par(parameter count or frozen-leg df) + sdf_hat, where sdf_hat comes from fission around y (not around x): F+- = f(y+-), G+- = frozen legs (births from the other copy) — same code path as v3, but with x replaced by the observed y. Open question for Opus: the bias of the covariance df measured around y (noise level inflated, centre = y not x).
6. Global-K holdout (pixel holdout with inpainting) — include only if it can be run at equal wall time; otherwise report as not comparable.

## Evaluation protocol (to be frozen before any H2 run)
Fresh images (not E1..E14), fixed generator seeds, oracle loss ||f_S - x||^2 per S (evaluator only), metrics: selected-S regret vs oracle-best S, rank agreement, wall time per image; paired over images; equal-wall-time frontier (replicates per image tuned so every method uses the same seconds). Kill criteria: method not better than baseline 4 (fission-CV) at equal wall time with a pre-registered margin => STOP, report that the correction adds nothing over known data-fission CV.

## Known risks to hand to Opus
- sdf>0 on a synthetic toy at S=1024 is nearly guaranteed by selection; H1 is a headroom check, not a result. The scientific question is H2's decision regret vs baseline 4.
- The fitted-S decision may be insensitive (flat risk across S) which would make every method tie.
- Estimator around y vs around x: need a bias study with x known (synthetic) before any decision experiment.
- GPU not needed; CPU wall budget ~ hours; no GPU work before contract + headroom evidence + idle check.
