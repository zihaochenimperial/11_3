# Opus packet: direction after S2 STOP-Q1 (run 20261106T045933Z-opus-review-f652)

You are the scientific gate (Opus). Be adversarial and concise. This is a review of a *research direction*, not code. Nothing here is validated; there are 0 validated contributions so far. Reviewer must self-report the model it is running as (exact id string) in the first line of the review.

## Project context
Project "Gaussian": CPU-first mechanism validation for adaptive 2D Gaussian growth. Genuine human authorisation (2026-11-05): new candidate mainline = Gaussian capacity/geometry control for recoverable detail under degraded observations, first task known-kernel single-image deblurring; do nearest-neighbour refutation and a full small joint reference first; only if margin exists proceed to cheap local approximations and split/merge; do not rename Fisher/Schur/spectral regularisation as innovation; advance autonomously but every new experiment needs a new G0 + new contract + real Opus gate + freeze. Hard rules: STOPped F0/H2 (FAIL-0001) and CF0 (FAIL-0013) are never revived; E41-58 confirmation images sealed; no GPU; no claims of originality or score.

## What just happened (S2, frozen contract v2.1; mechanical verdict STOP-Q1)
Full note: /home/claude/AS_S2_negative_result_20261106.md (read it). Summary: 24 procedural 32x32 images x 4 degradation conditions C1-C4 x 2 seeds = 192 units, K0=6 -> K_max=36, 30 greedy steps, 15 LM refit steps per candidate.
- Gate 0 PASS: ORACLE_xs (select edits using the CLEAN image) lowers MSE 45% vs cheap rule BLOCK (H=+0.452).
- Gate 1 FAIL: compensation-aware JOINT vs OMP-raw: mean log ratio -0.034 (ratio 0.966), exact sign-flip p=0.130, condition C4 +13.6% worse; vs BLOCK: JOINT +2.7% worse, p=0.759.
- Gate F FAIL: FIXED-K reaches 0.816x JOINT's MSE (growth has no independent value on this benchmark).
- Post-hoc (descriptive, same dev data, NOT evidence): ORACLE_ys (select by data-fit y) is 64% WORSE than the cheap rule; RAND is 37% better than BLOCK, JOINT_FREE 31% better, FIXED-K 15% better; data-fit greedy overfits at K_max=36; Tikhonov (GCV) beats best Gaussian result by 3.4/6.2 dB in strong-blur C3/C4, Gaussian wins in C1/C2.

## Candidate follow-ups (all proposed)
- A. Generalisation-aware selection/stopping: risk estimation (SURE/GCV/Cp with search-cost correction), noise splitting / held-out pixels, stability-based stopping for Gaussian growth.
- B. Direct test of data-fit greedy vs random/diverse/regularised selection under noise.
- C. Stop this mainline; record negative results; wait for the human.
- D. (reviewer may propose another) e.g. a different axis or a rescoped task.

## Prior closed lines (do not revive)
- F0/H2 (search degrees of freedom sdf of Gaussian birth search): H1 passed in toy, H2 STOP by Opus: R-hat(S) depends only on df_full(S); covariance-penalty/coupled bootstrap covered by fission-CV. Prior art noted: Ye 1998, Efron 2004, Janson-Fithian-Hastie 2015.
- CF0 (cross-fitted birth positions): STOP; decisive control NS ~ 0 (same honest positions fitted on full y gave no benefit). Report-only: fission-CV stopping (RAWcv) beat fixed K=48 by 33% -> "CV/discrepancy/Cp-SURE family, overlaps F0/H2"; "randomisation as regularisation" suspected for the equal-noise selection effect. Opus then estimated: K-axis benchmark study GO ~20-30%, "can call it new" <5%.

## G0 near-neighbour findings this round (levels: L2-L3 tool summaries, not full reads)
- Tibshirani 2015 "Degrees of Freedom and Model Search" (sdf of best subset/forward stepwise) [L2 title only; prior knowledge].
- arXiv 2308.13630 "Degrees of Freedom: Search Cost and Self-consistency": msdf, MC resampling estimate, best subset/lasso/trees/MARS; no new search-corrected Cp/SURE; forward stepwise not separately analysed [L3].
- arXiv 2506.15643 "Revisiting Randomization in Greedy Model Search": randomised feature-subsampled forward selection and ensembles in orthogonal-design linear regression; randomisation can lower both bias, variance, training error and df; not plain shrinkage [L3].
- arXiv 1602.06373 OMP-CV: held-out measurements choose OMP stopping iterate; theory under Gaussian sensing [L3].
- Image-GS (error-proportional position sampling, fixed budget, no validation), SteepGS (decoupled pointwise split criterion), ADCG, OLS (Soussen), IRGNM+DWR, Noise2Self/blind-spot K selection, data fission/thinning, Wasserman-Roeder [read in earlier rounds, mixed L3/L4].
- Two further searches (2D GS overfitting/SURE/held-out; GS deblurring vs Tikhonov) returned only 3DGS deblurring/densification papers, no direct nearest neighbour [L2, not read].

## Questions (answer each, <= 1 short paragraph)
1. Collision: do A and B, as stated, add anything beyond (i) the closed F0/H2 and CF0 lines and (ii) the published work above? Which part, if any, is not covered?
2. Is there a residual question that is (a) pre-registrable, (b) CPU-cheap, (c) falsifiable, (d) not answered by the S2 post-hoc observations being reused as evidence? If yes, state it as a one-sentence hypothesis with a kill criterion. If no, say so.
3. The K-c result (Tikhonov beats Gaussians by 3-6 dB at strong blur) — what does it imply about the task framing "known-kernel deblurring is the first task"? Is there a regime where Gaussian capacity control could still matter, and would testing it be a new mainline needing human approval?
4. Verdict: choose one of A / B / C / D and state the required safeguards: what must hold before any new contract (new images, development/confirmation separation, label "benchmark, innovation claimed = 0" vs possible contribution). What should I do autonomously now, and what must wait for the human?
5. Biggest risk I am not seeing (e.g. selection bias from reusing dev data, benchmark artefacts such as K_max=36 over-growing, procedural-image distribution).

Output: write your review to /tmp/claude-0/-home-claude/c30445bf-b91f-5725-a565-964b312260f4/scratchpad/AS/OPUS_REVIEW_AS_DIRECTION_20261106.md (first line: your self-reported model id), then return a 5-line summary including your verdict.
