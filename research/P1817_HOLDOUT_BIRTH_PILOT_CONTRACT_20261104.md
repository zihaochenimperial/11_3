# P1817 matched local holdout-birth pilot contract

Frozen before implementation and execution on 2026-11-04. Classification: **auxiliary/development mechanism pilot**. It cannot establish denoising superiority, originality, or an independent-test result.

## Objective and hypotheses

Selected idea: at one progressive Image-GS birth event, generate a fixed oversampled pool using only A-fold residuals, then either take the first K candidates (matched residual-birth control) or use noisy B-fold error reduction within each candidate's 16x16 tile to select K candidates. Both variants then continue optimization using A pixels only. This tests the leakage-safe local selection mechanism while matching candidate pool, final Gaussian count, optimization steps and seed.

- Research question: does local B-fold ranking of A-proposed births improve an untouched C-fold noisy squared-error audit and known-clean development error relative to the matched first-K control?
- Null/no-go: the implementation fails C-target invariance; candidate pools differ; final K/steps differ; the holdout variant does not improve C-fold noisy MSE; or C-fold noisy and known-clean changes disagree in sign.
- Alternative for expansion only: invariance and matching pass, holdout has strictly lower C-fold noisy MSE, and its known-clean C-fold MSE is also lower. Passing permits a three-structure/two-seed development batch; it is not a paper claim.

## Frozen pilot

- Source: clean Image-GS commit `03088368d42684fb54225c981cfd94b58cc0393a`, MIT license; upstream remains read-only.
- Input: existing 192x192 synthetic noisy development image, sigma 25/255 seed 123, SHA-256 `af17835d24f94488fa042efbfda00aa21628b5c0f299835404c75e7e359b0632`; clean truth SHA-256 `91a7824e38717f2fbece5af0705a8c50ca8aa3057b7d268bc6e1eee86c37e1c5` is evaluator-only.
- Fold map: deterministic three-color pixel checkerboard `(x + 2*y) mod 3`, with A=0 fit/propose, B=1 select, C=2 audit. One rotation only in this pilot.
- Both variants: seed 123; random position initialization; color initialization disabled; masked L2 on A only; SSIM/L1 disabled; fixed 1000 steps; LR scheduling disabled; 256 initial Gaussians; one 64-Gaussian birth at step 500; final K=320; no pruning or quantization.
- Candidate pool: 256 unique A pixels sampled from squared A residual at step 500. Candidate position, scale, rotation and feature use only A-derived quantities. Control takes the first 64. Holdout ranks individual candidates by B-fold squared-error reduction inside the containing 16x16 tile and takes the best 64, even if a score is negative, preserving K.
- C invariance smoke: rerun the holdout path with only C noisy target values deterministically perturbed. Candidate pool, selected indices, checkpoint parameter hash and final render hash must be identical. C values may be read only by the external audit after optimization.

## Required evidence and decisions

The implementation lives outside upstream and records source/tool/input hashes, exact commands, environment, GPU, seed, fold counts, proposal pool, selection scores/indices, steps, K, wall time, peak VRAM, final renders and checkpoint hashes. The fixed evaluator reports A/B/C noisy MSE plus full/C-fold clean MSE and PSNR for both variants. Baseline and holdout must share the candidate-pool hash.

Minimum evidence is the C-invariance smoke plus one matched control/holdout pair. Solid evidence requires the later three-structure/two-seed batch and is not authorized until the minimum gate passes. Any mismatch, non-finite score, output overwrite, source drift or second simultaneous GPU process stops the batch. No automatic parameter tuning or retry is authorized.

## Minimal code-change map

| Path | Planned role | Boundary |
|---|---|---|
| `scripts/p1817_holdout_birth_pilot.py` | Subclass/import pinned Image-GS; create folds; masked A loss/proposal; matched candidate selection; manifests | No edit to upstream or evaluator |
| `scripts/analyze_p1817_holdout_birth.py` | Read immutable outputs and apply the exact null/alternative rule | Clean truth is read only here |
| `runs/p1817_holdout_birth_20261104/` | Ignored live status/logs | Development evidence only |
| `/home/research/msc_inverse_research/runs/p1817_holdout_birth_20261104/` | Heavy checkpoints/renders/manifests | One GPU process at a time |

If the subclass cannot exclude B/C from all initialization, loss, proposal and stopping decisions without modifying upstream, stop at an implementation blocker rather than run a leaky approximation.
