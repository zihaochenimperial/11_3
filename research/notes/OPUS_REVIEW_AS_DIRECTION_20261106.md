claude-opus-5-5
# Opus review: direction after S2 STOP-Q1 (run 20261106T045933Z-opus-review-f652)

Reviewer: independent scientific gate, adversarial. Inputs read in full: OPUS_PACKET_AS_DIRECTION_20261106.md, /home/claude/AS_S2_negative_result_20261106.md. No experiments run, no citations re-verified (literature levels are taken as stated in the packet, L2-L3; any statement below about a paper inherits that level). Status: 0 validated contributions, before and after this review.

## Q1. Collision
A, as stated, is almost entirely covered. "Risk estimation with search-cost correction" (SURE/GCV/Cp + search df) is the F0/H2 object restated: search df of greedy birth, covariance penalty, coupled bootstrap. That line was STOPped, and Ye 1998, Efron 2004, Tibshirani 2015 and arXiv 2308.13630 (msdf by MC resampling) occupy it. "Noise splitting / held-out pixels for stopping" is CF0's report-only RAWcv finding (fission-CV stopping beat fixed K by 33%), plus OMP-CV (1602.06373), data fission/thinning, Noise2Self-style K selection. Running A would revive closed lines under a new name, which the hard rules forbid. B is covered by 2506.15643 (randomised greedy forward selection lowers df and can lower error; this is not plain shrinkage) and by CF0's own "randomisation as regularisation" suspicion. Nothing in S2 is specific enough to make B new: RAND beating data-fit greedy at a fixed, over-grown endpoint is the textbook pattern. One part is not covered by name: these models have continuous geometry, every candidate gets a nonlinear LM refit, and the forward operator is an ill-posed blur. None of the cited work analyses search df or held-out stopping for that combination. That makes it a domain transfer (benchmark value), not a mechanism. I would not count it as a contribution.

## Q2. Residual pre-registrable question
Yes, but only one, and only as a benchmark question. Hypothesis: on new procedural images (not the S2 dev images and not E41-58), with every arm stopped by the same pre-registered held-out/fission criterion (no fixed K_max endpoint), clean-image-oracle selection (ORACLE_xs) still beats the best non-oracle rule (min over BLOCK/RAND/OMP/JOINT) by at least 10% geometric-mean MSE. Kill criterion: if that margin is below 10%, or its paired sign-flip CI includes 0, then S2's Gate 0 margin was over-growth/noise-fitting, not selection headroom, and the "which edit to pick" axis is dead on this task. It is (a) pre-registrable, (b) CPU-cheap (same code, the stopping rule is the only new variable, roughly S2 cost or less), (c) falsifiable, and (d) not a reuse of the post-hoc observations, because it tests the precondition (headroom) on fresh data, not the observed RAND/JOINT_FREE ordering. If it passes, the next question would be A again, and A collides (Q1). So passing buys little, while failing cleanly closes the axis. Expected information is mostly closure.

## Q3. What K-c implies
Under strong blur (C3/C4), Tikhonov-GCV wins by 3.4-6.2 dB (4.6-8.1 dB with oracle λ). In those conditions the problem is ill-posed noise amplification. The Gaussian arms are unregularised least squares, capacity-limited only by K, and K is a coarse, discrete regulariser. So S2 compared "regularised vs unregularised" more than "Gaussian capacity vs pixels". The framing "known-kernel deblurring as first task" is therefore weak exactly where deblurring is hard. Capacity control could matter in a regime where Tikhonov's smoothness prior is wrong and the Gaussian prior is right: weak blur / low noise (C1/C2, where Gaussians already win), or piecewise-smooth/sparse-blob content where Tikhonov blurs edges. But the honest baseline there is TV or another edge-preserving regulariser, not Tikhonov. A fair test needs (i) Gaussians plus an explicit amplitude/smoothness penalty or held-out stopping, (ii) a TV baseline, and (iii) probably different content or degradations. That changes the task and the comparator, i.e. a new mainline. It needs human approval and must not be started autonomously.

## Q4. Verdict: C (stop this mainline, record negative results, wait for the human), with the Q2 check offered to the human as an optional, explicitly labelled D
A is rejected because it collides with closed F0/H2/CF0. B is rejected because it is covered by 2506.15643 and is textbook. D (the Q2 fair-stopping headroom check) must not run autonomously: it falls under the human's mainline only as a "does margin exist" re-check, and its upside is closure, not contribution.

Safeguards before any new contract, whichever option the human picks:
- (1) New G0 for the specific question.
- (2) Freshly generated images with a recorded seed/generator hash: a dev set and a separate confirmation set. No S2 dev images in either. E41-58 stay sealed.
- (3) Hypotheses written only from the pre-S2 rationale or stated as headroom checks. None may be derived from post-hoc observations 2-6 of the S2 note.
- (4) A matched stopping/regularisation policy across all arms. A fixed-K_max endpoint is allowed only as a secondary readout.
- (5) A TV baseline beside Tikhonov whenever task value is discussed.
- (6) Every document labelled "benchmark, innovation claimed = 0". No "possible contribution" label unless a G0 at L4 (full read) finds no nearest neighbour.
- (7) A real Opus gate and a freeze before any run.

Autonomous now:
- Finalise the negative-result record and failure-log entries (S2 STOP-Q1; Gate F fail).
- Update memory/STATE.md and CHECKLIST.
- Upgrade the four cited papers from L2/L3 to L4 (read-only).
- Write a short decision memo for the human with options C, D-headroom (Q2) and D-rescope (Q3: edge-preserving baseline / different task). The memo states the expected value honestly: contribution probability is low for all three options.

Must wait for the human:
- Any new experiment, image generation for a contract, or contract freeze.
- Any task rescope (Q3).
- Any decision to end the overall "Gaussian capacity control" mainline.

## Q5. Biggest unseen risk
The whole S2 "selection" story may be an artefact of over-growth with no regularisation. At K_max=36, roughly 7 parameters per Gaussian gives about 250 continuous parameters against 1024 blurred, noisy pixels, with no stopping. In that regime, any rule that fits the data less well (RAND, JOINT_FREE, FIXED-K) looks better, and ORACLE_xs's 45% Gate-0 margin may mostly be "the clean-image oracle refuses to fit noise". Any decent stopping rule recovers that kind of margin, so it is not headroom for selection. If so, Gate 0 "PASS" was itself mis-specified, and the project has drawn three successive mainline candidates (F0 → CF0 → AS) from one recurring phenomenon (greedy overfitting, cured by held-out stopping), rediscovering known statistics each time. Secondary risks:
- Tiny sub-samples: ORACLE_y-full has n=6 and ORACLE_ys n=96, so those ratios are anecdotes.
- Non-monotone dose-response and an empty INIT-N diagnostic that were never explained.
- 32x32 procedural images built from blob-like primitives may favour Gaussians in C1/C2. The "Gaussians win at weak blur" side of K-c is as untrustworthy as the losing side.
- Forking paths across mainlines: each new hypothesis is mined from the previous dev set. That is why the fresh-data separation in Q4 is non-negotiable.
