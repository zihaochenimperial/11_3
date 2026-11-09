claude-opus-5-5

# Opus narrow review: GEO pre-D addendum K1 (deviations #6-#10, K1.2-K1.3 recording)

Reviewer: Opus 5.5 (self-reported model id on line 1). Read-only with respect to the project. Files read: OPUS_PACKET_GEO_PRED_ADDENDUM_20261106.md, GEO_PRE_D_ADDENDUM_K1_DRAFT.md, GEO_CONTRACT_CANDIDATE_v2.md, OPUS_REVIEW_GEO_DEVIATIONS_20261106.md, geo_dev_bench/geo_core_under_review.py (sha256 580af07f..., matches K1.6), geo_flops_under_review.py (076a0a61..., matches K1.6), the bench scripts and both probe logs.

What I ran: copies of geo_core_under_review.py, geo_flops_under_review.py and geo_gen/as_gen/as_core, placed in my own scratch directory (scratchpad/opus_k1_review/) and run with `python3 -I`. This was dev cells 101/C1/K36, 102/C2/K16 and 103/C4/K36, 200-iteration calibration mode only, base 9101. I did not run budget_probe.py. No held-out image, no F_ref and no quality metric was touched. Everything below that comes from these runs is **development evidence, not a result**. Validated contributions: 0.

**Verdicts:**

| Question | Verdict | Decision impact |
|---|---|---|
| Q-a | ACCEPT-WITH-CHANGES | Affects every arm's trajectory. The tolerance is wrong, shown on a dev cell. |
| Q-b | ACCEPT-WITH-CHANGES | Logging and V7 only. |
| Q-c | ACCEPT-WITH-CHANGES | Affects V-pass and Q2 labelling. |
| Q-d | ACCEPT-WITH-CHANGES | Changes the compression order and wall-clock definitions. |
| Q-e | ACCEPT-WITH-CHANGES | Three omissions to append. |
| Q-f | ACCEPT-WITH-CHANGES | Fixes a binding safety-limit bias in Q2 and freezes six ambiguous readings. |

| Addition (1): caps at λ=1e-3, H at λ* | ACCEPT-WITH-CHANGES | Adds a λ* budget-adequacy gate for Q2 and Q1. |
| Q-g: #11 Phase L tolerance rule | ACCEPT-WITH-CHANGES | Affects Q3 and ADVANCE. |

None of these is a REJECT. The last two rows were added after the first version of this review, at the coordinator's request. They are in the sections "Addition (1)" and "Q-g" at the end.

---

## Q-a. #6 active-set freeze: ACCEPT-WITH-CHANGES

**What is right.**
- Freezing coordinates whose projected gradient points outward is the standard projected-Newton / L-BFGS-B treatment of bounds.
- The rule is applied identically to every arm, and I checked the sign in each:
  - GEO, LMD and BJ use ∇F = −(AJ)ᵀr/σ² + aJᵀx.
  - LSMR computes ∇F directly.
  - PCG8P and PCG8D pass −g.
  - BLK applies it per block with the current residual, which is consistent with Gauss-Seidel.
- The extra cost is small. LSMR pays 1 extra A-application per outer iteration against roughly 2p Krylov applications, a cost below 1% that is counted in n_A. All other arms get the gradient for free.
- Log-parameterisation or an interior-point method would change the problem: the S2 box, the parameterisation that all arms share, and F_ref. That is a contract change, not a fix. **I reject those alternatives.**

**What is wrong: the absolute tolerance 1e-12 leaves the failure in place.**
- Dev cell 103/C4/K36, GEO rcond=1e-4, current code: the run stops with `no_step` at iteration 65, F=633.46.
- My diagnosis of the final θ:
  - Coordinate 211 (the mx of Gaussian 35) sits at 35.9999958, which is 4.2e-6 below its upper bound of 36.
  - The gradient there is −2.10, so the descent direction points outward.
  - Because it is not within 1e-12 of the bound, it is not frozen.
  - At every κ from 1e-3 to 1e4 the step still crosses the bound: |δ| = 1.1e-5 at κ=1e4. The clamp then yields pred < 0 (−8.0e-6 at κ=1e4). This is exactly failure K1.2 #2, one coordinate off the bound.
- With ε = 1e-3 the same cell runs the full 200 iterations to F=630.66. Cells 101 and 102 change by less than 0.1% (101 GEO rc1e-4: 2102.18, unchanged).

**Replacement text for #6 (replaces the first sentence of K1.4 #6):**
> #6 ε-active-set freeze (all arms except HIST): at the start of each outer iteration, at the current θ with ∇F_a(θ), the active set is
>
> I = {i bounded : (θ_i ≤ lo_i + ε and ∂_iF > 0) or (θ_i ≥ hi_i − ε and ∂_iF < 0)}, with ε = 1e-3 absolute in parameter units (px for positions; log units for l11 and l22; raw units for l21). Amplitudes are unbounded and never active.
>
> Coordinates in I are frozen for the whole outer iteration, including all its backtracks: their columns of J and AJ are zeroed and their step components are set to 0. All other coordinates are solved, clamped and accepted as in §1. BLK applies the rule per block with the current residual.
>
> HIST (as_core.lm) is left unchanged, because it is the historical control.
>
> Logged per iteration: |I|, and the number of clamped coordinates that were not in I.
>
> A `no_step` stop whose last rejected trial had at least one clamped coordinate is labelled `no_step_clamp`. Its rate is reported per arm.

**Append to C14 (V-pass reporting):**
> The "GEO-specific failure mode" trigger also fires if tuned GEO's mean |I| per iteration, or its `no_step_clamp` rate, is ≥ 3× LMD's on dev.
>
> Reason: #6 converts clamp failures into active-set freezes. Without this clause, the C14 trigger would be masked by the fix.
>
> Rates are per trial: rejection rate = rejected trials / all trials; clamp rate = trials with ≥1 clamp / all trials.

**Freeze record:**
- The new geo_core sha.
- A V3 sub-test: a constructed case with one coordinate 1e-6 inside a bound and an outward gradient must be frozen, and the step must be accepted.
- Dev evidence for 103/C4/K36: 633.46 `no_step` at iteration 65 becomes 630.66 at 200 iterations.

## Q-b. #7 BJ α = min(1, α*): ACCEPT-WITH-CHANGES

**Consistency with A5.** A5's intent was to correct the overshoot of the unrelaxed block sum. The cap leaves α = α* exactly where α* < 1, which is the overshoot case, and stops α* from cancelling κ when α* > 1. That is the intent.

**Is it the strong form?** Yes. It also has a property worth freezing:
- The quadratic model along the BJ direction gives α* = 1 + η‖J du‖²/q_d whenever du is the exact damped minimiser.
- At K=1 this means α* ≥ 1, so min(1, α*) = 1. Capped BJ is then exactly GEO at every κ, with no α-forcing switch.
- My copy confirms it: K=1, 20 iterations, max |θ_BJ − θ_GEO| = 1.8e-15.

**Alternative I tested: the damped-model optimum α_κ = g_d/(q_d + κΛ_A‖J du‖²).** This is principled, needs no cap, and is also exact at K=1 (5e-16). At 200 iterations it gave essentially the same values:

| Cell | Capped α | α_κ |
|---|---|---|
| 101/C1/K36 | 2678.9 | 2710.9 |
| 102/C2/K16 | 872.4 | 895.2 |
| 103/C4/K36 | 657.4 | 656.2 |

The capped α is not weaker than α_κ (better in 2 of 3 cells, within 3%). So I do not require switching. Do not add α_κ as an extra arm.

**Changes (append to A5.1 / #7):**
> - α* (before the cap) and α are both logged per trial. The fraction of trials with α* > 1 is reported. In dev it was about 0.35-0.40.
> - α* ≤ 0 (or non-finite) counts as a rejected trial: κ ← fκ, 0 A-applications, the trial is counted, no F evaluation.
>
> A5.3 / V7 is replaced by: at K=1, BJ (with the cap, no forcing) and BLK must equal GEO to relative 1e-12 in θ over 20 iterations. The `alpha_one` test is kept as a second check.

## Q-c. #8 rcond tuning for the GEO family, GEO-r8, and the amended V-pass: ACCEPT-WITH-CHANGES

**Budget.** Six combinations against six is equal in count, and κ adapts, so fixing κ0 = 1e-3 is harmless. The change is honest **only if** the frozen-spec gate is still evaluated and its failure is recorded, rather than replaced.

**My dev evidence.** On 102/C2/K16, GEO with rcond=1e-8 stops with `no_step` at iteration 9 at F=2206.1 against F_init 2207.4. That is s ≈ 1, so the frozen spec will very likely fail the original V-pass in some cells. Moving the gate after seeing that is a goalpost change unless it is labelled as one.

**Two-sided risk to note.** rcond=1e-2 is not just slow; it can stop at a false fixed point:
- 102/C2/K16: `converged` at iteration 43 with F=1269 (rcond=1e-4: 584).
- 101/C1/K36: F=3946 (rcond=1e-4: 2102).

Selecting on dev s should exclude it, but the knob changes GEO's fixed point, not just its speed.

**Replacement text for the V-pass part of #8:**
> V-pass is evaluated twice on dev, both recorded.
>
> **(i) Frozen V-pass.** V1-V7, and GEO-r8 and LMD each with ≥95% of the 96 dev cells at s ≤ 0.1 within budget.
> - If GEO-r8 fails, a FAIL entry is written to FAILURES.md: "STOP-GEO-V under the frozen spec (rcond=1e-8): Euclidean minimum-norm back-substitution amplifies weak directions".
> - This FAIL is not erased by (ii).
>
> **(ii) Amended V-pass.** The same criterion with tuned GEO in place of GEO-r8. Only (ii) gates phase H.
> - If (ii) passes but (i) failed, every Q2 label and ADVANCE label carries the suffix "[amended-V; GEO = rcond-tuned, not the frozen §1 step]".
>
> Each GEO-family arm (GEO, BJ, BLK) selects its own (rcond, f) independently. They do not share one rcond, because rcond on 6×6 blocks has a different meaning.
>
> V2 is run at all three rcond values. The comparison is image step against a dense pseudo-inverse with the same rcond, tolerance 1e-6.
>
> The C14 trigger is computed for tuned GEO, which decides whether the result counts as Q2 evidence. It is reported for GEO-r8 for information only.

**Ambiguity to freeze.** "GEO 族先调 (校准模式)" must mean **only GEO** is tuned in calibration mode (≤200 iterations), because its hyperparameters define A_cap and W_cap.

> BJ and BLK are tuned like every other arm: in budgeted mode, after A_cap and W_cap are frozen.

Tuning BJ or BLK at a 200-iteration horizon would handicap exactly the arms the Q2 decision compares GEO against. The probe logs show BJ needs more than 4000 iterations to reach W_cap. Disclose that GEO's selection horizon (200 iterations) differs from its evaluation horizon (the budget).

## Q-d. #10 compute plan: ACCEPT-WITH-CHANGES

**Statistical power.**
- Dropping base 9202 for the Q2 arms keeps 24 images per K layer. The statistical unit is the image, so the t-interval stays at df=23. Only within-image averaging is lost. Acceptable.
- For Q2 clause (b), each K layer now has 96 cells (not 192). The binomial standard error is about 3.1% at the 10% threshold and about 4.4% at 25%. Report the raw counts next to the fractions.
- S_tune covers the corner conditions C1 and C4 with 2 images per family, which is adequate for choosing 1 of 6 combinations.
- Running λ and τ on all 96 dev cells, with DP evaluated after the fact from the stored λ=0 trajectory, is exact: the trajectory does not depend on τ before the stop.
- The y-only arm is descriptive, so 12 images is fine.

**The compression trigger depends only on cost, but the order is wrong.** It cuts decision inputs (the wall-clock check in Q2 and base 9202 in Q1) before descriptive ones. LSMR, at about 110 s per K36 cell, is the most expensive arm and decides nothing.

**Replacement text for #10 (vi):**
> (vi) Compression order. It is computed once, at the end of phase D and before any held-out job starts, and is never changed during phase H.
>
> Projection = Σ over planned H and timing jobs of (dev median CPU-seconds per cell for that arm and K) × number of cells × 1.2.
>
> If the projection exceeds 40 CPU-h, **or** the projected wall-clock finish (2 concurrent jobs, then the exclusive timing run) is later than 2026-11-08T02:38Z (deadline minus 4 h), apply in order until both conditions hold:
> 1. Descriptive arms LSMR, PCG8P and PCG8D run on images 201-212 only.
> 2. HIST runs on images 201-212 only.
> 3. The y-only pairing is halved to images 201-206.
> 4. The timing subset is halved to 48 cells (images 201-206).
> 5. Q1 arms drop base 9202.
>
> F_ref restarts and V tests are never cut. Each step is written to STATE and appended to the freeze record together with its projection numbers.

**Replacement text for the Q2 wall-clock definition (K1.4 last block). The aggregation is made consistent with §2, which takes the image as the unit:**
> On the timing subset, for each K layer separately, take the cells where GEO and the other arm (BJ, and separately BLK) both reach s ≤ 1e-2.
> - For each cell, compute three log-ratios: log(t_GEO/t_other), log(n_A,GEO/n_A,other) and log(W_GEO/W_other). Each is read at the first iterate with s ≤ 1e-2, with t = cumulative solver time from traj.
> - Average each log-ratio within each image, then across images.
> - "Same direction" means all three image-level means have the same sign.
>
> If fewer than 6 images have a jointly-reached cell in a K layer (relevant when JOINT-MATTERS would come through clause (b)), use the wall-clock analogue of clause (b) instead:
> - t* = GEO's wall time to reach s ≤ 1e-2.
> - Require the other arm's s at t* > 1e-2 in ≥25% of timing cells, with GEO failing to reach in ≤10%.
>
> Two repeats are combined by their mean (with two values the median is the mean; say "mean").

**Disclosure.** About 35 CPU-h (roughly 18 h wall-clock at 2 concurrent jobs, plus about 5 h exclusive) fits before 2026-11-08T06:38Z only if phase D stays at about 12 CPU-h or less and there is no rerun. Record the phase-D CPU actually used in the freeze record.

## Q-e. Recording of A1-A5 in K1.3: ACCEPT-WITH-CHANGES

I checked fidelity only. A1, A3, the A1.4 counting conventions, and A5.2 (κ_k carried in `kap_blk`, skip logged) match both my text and the code. Five things are missing or unrecorded:

1. **A2.** My text required reporting the per-state slopes (grid initial state and iteration 5) descriptively, as well as the κ=1e-3 slope. K1.3 records only the κ=1e-3 slope and the sign flag. Append: "per-state η=0 slopes reported descriptively".
2. **A4.** "Computed per held-out cell from y only" is dropped. Append it verbatim. It is the reason the pairing exists.
3. **Unrecorded implementation choices that A1.2's "κ/λ_LM upper limit" depends on.** These differ between arms and must be on record:
   - The LMD and PCG8D λ_LM upper limit is 1e8 (LM_MAX); the κ limit for the other arms is 1e4. LMD gets 4 more decades before `no_step`.
   - The exact stop rule in code is `kappa ≥ limit and fails ≥ 2`: the trial at the limit is rejected in an outer iteration that follows another fully rejected iteration. For BLK it is 3 consecutive sweeps with no accepted block.
   - LMD's singular-solve fallback: on LinAlgError, λ ← fλ, counted as a rejection, no F evaluation.

   Append these three verbatim as "#9 code alignment (recorded, not deviations)".
4. **A5.3** is superseded by the exact K=1 equality (Q-b).
5. **K1.6** must also hash geo_flops.py *before* any phase-D calibration (A1 closing paragraph). It currently says "at the moment the review is frozen". The two coincide only if no phase-D job has started. State that explicitly.

## Q-f. Accuracy of K1.2 and decision ambiguities: ACCEPT-WITH-CHANGES

**K1.2 items 1-5 are not exaggerated.** My reruns reproduce:
- GEO(rc1e-4) 2102.18 and BJ 2678.9 on 101.
- GEO(rc1e-8) `no_step` at iteration 9, F=2206.1, on 102.

Two items are understated:

- **(F1) The #2 failure persists after the fix** for coordinates near but not exactly on a bound: 103/C4/K36, `no_step` at iteration 65 (Q-a). Append it to FAIL-0026 as item 2b.
- **(F2) The 5000-iteration safety limit binds for the Q2 decision arms.** In probe_101_C1_36.log the arms that stopped on `safety` reached only part of W_cap = 5.8e11:

  | Arm | W at safety stop | Share of W_cap |
  |---|---|---|
  | BJ | 2.59e11 | 45% |
  | BLK | 2.73e11 | 47% |
  | PCG8D | 2.36e11 | 41% (total W; cached slightly lower) |
  | PCG8P | 9.2e10 | 16% (A = 44% of A_cap) |

  K1.2 tags only BJ and BLK as "(safety)" and does not mention PCG8P or PCG8D. The probe's "F@Wcap" for these arms is really F at the safety stop, not F at W_cap. s is non-increasing in work, so reading BJ and BLK at less than half the W budget favours clause (b) of JOINT-MATTERS under the W reading. **This is a bias toward the pre-expected label and must be fixed before phase D.**

**Replacement text (append to A1.2):**
> SAFETY_ITERS is 20000 for GEO, LMD, BJ and BLK, and stays 5000 for LSMR, PCG8P and PCG8D (descriptive arms; a safety stop is flagged as "safety-censored" in their rows).
>
> If a decision arm still stops on `safety` before W ≥ W_cap (or A ≥ A_cap), that cell is read at the common level for every pairwise Q2 comparison:
> - W_c = min(W_cap, W_end of each arm in the pair), and likewise A_c.
> - Both arms are read at W_c (and A_c).
> - An arm that stopped on `converged` or `no_step` carries its final s forward.
>
> The censoring rate is reported per arm and K. If more than 10% of a decision arm's cells in a K layer are censored, Q2 in that K layer is JOINT-NOT-MATTERS.
>
> Cost: about +50 s (BJ) and +70 s (BLK) per K36 cell. This goes into the (vi) projection.

**Ambiguous decision readings, and how I would freeze them (append verbatim):**

> **R1. Reading "s at A_cap" / "s at W_cap"** = s of the last iterate whose cumulative count is ≤ the cap. No interpolation. An arm that stopped earlier carries its final value forward. For PCG8D, the cached count.
>
> **R2. A_cap(K) and W_cap(K)** = median over all 48 dev cells of that K (all 4 conditions, 12 images) of tuned GEO's calibration run. Every stop reason is included (`max_iter`, `converged`, `no_step`), and the distribution of stop reasons is reported.
>
> **R3. Geometric mean of s** (tuning criteria, §3 and #10(i)) uses max(s, 1e-6). s = 0 occurs for the cell that holds F_ref, which would otherwise make the log −∞.
>
> **R4. Q2 clause (a)** "GEO ≤ 0.5× BJ and ≤ 0.5× BLK":
> - The statistic is exp(image-level mean of the per-image mean log-ratio over jointly-reached cells), a point estimate, required ≤ 0.5 against each arm.
> - It is evaluated separately in n_A and in W.
> - It needs at least 12 of the 24 images with a jointly-reached cell in that K layer; otherwise clause (a) is false.
> - The t-interval is reported.
>
> **R5. Q2 clause (b)** "BJ 或 BLK" is read arm-wise: (fraction of cells with s_BJ > 1e-2 ≥ 25%) **or** (fraction of cells with s_BLK > 1e-2 ≥ 25%), with GEO's fraction ≤ 10%.
> - It is a per-arm fraction over the cells of the K layer, **not** the union per cell.
> - It is evaluated at the A reading and at the W reading. Both must hold (A1.3).
>
> **R6. Q2 quality condition** "H(GEO vs BJ) lower t-bound ≥ −0.02" must hold at both the A_cap and W_cap endpoints.
> - The endpoint of the budgeted run is used for quality.
> - The comparison is against BJ only (the contract text), with BLK reported.

**Freeze-record items before the first formal phase-D number is visible:**
1. #6 replaced by the ε-active-set rule (ε = 1e-3), with the `no_step_clamp` label, the C14 extension and the V3 sub-test.
2. #7 kept, with α* and α logging and the exact K=1 V7.
3. #8 with the dual V-pass (frozen FAIL kept), independent per-arm rcond, V2 at all three rcond values, and only GEO tuned in calibration mode.
4. #10(vi) replaced by the new compression order; the wall-clock definition aggregated at image level.
5. The A1.2 safety change and common-level reading.
6. R1-R6.
7. The K1.3 omissions (Q-e items 1-5).
8. FAIL-0026 items 2b and the safety binding.
9. New sha256 for geo_core.py and tests, and the geo_flops.py sha recorded before any phase-D job.
10. Host V rerun (V1-V8, including the new V3 sub-test and V7) with its run id.

11. Addition (1): caps fixed at λ=1e-3, plus the λ* budget-adequacy gate (below).
12. #11 / Q-g: the tolerance rule with the changes below, and the exposure disclosure including the two-point slopes.

---

## Addition (1). Tuning and caps at λ=1e-3, phase H at λ*: ACCEPT-WITH-CHANGES

**Caps must not be per-λ\*.** Keep A_cap(K) and W_cap(K) fixed at λ=1e-3:
- The budget is a common work allowance for all arms in a cell. Fairness between arms does not depend on which λ set its size.
- Per-λ\* caps would tie the budget to a choice made on clean-image MSE. They would also give different (condition, K) strata different budgets after a quality-driven selection.
- Q1 compares GEO@λ\* with F_0+GEO+DP inside the same cell. Both run under the same cap whichever way it is set.

**The real risk is budget adequacy.**
- λ\* can be 0 (a=0, the worst-conditioned case for GEO) or 1e-1. The iteration counts behind the caps were measured at a=1e-3/σ_n².
- A cap that is too small at λ\* turns Q2 clause (b) into "neither arm finished", and Q1 into a comparison of unfinished iterates. The V-pass at λ=1e-3 does not certify λ\*.

**Replacement text (append to #10 (i)):**
> Control hyperparameters, A_cap(K) and W_cap(K) are tuned and calibrated at the fixed objective λ=1e-3. They are not recalibrated at λ\*.
>
> After λ\* and τ\* are frozen, run a **λ\* adequacy check** on all 96 dev cells, each at its own (condition, K) λ\*:
> - It uses the budgeted runs of GEO (tuned) that already exist from the λ grid.
> - Add one budgeted LMD run per dev cell at λ\*, and F_ref at λ\* (LMD 500 iterations × 3 restarts). Estimated cost about 0.5 CPU-h.
> - The criterion is the amended V-pass: GEO and LMD each with ≥95% of dev cells at s ≤ 0.1 within budget at λ\*.
>
> If the check fails in a K layer:
> - Q2 in that K layer is INCONCLUSIVE (= JOINT-NOT-MATTERS for ADVANCE), labelled "budget calibrated at λ=1e-3 insufficient at λ\*".
> - The Q1 labels in that K layer carry the same tag.
> - The caps are not changed.
>
> Report the stop-reason distribution (cap / converged / no_step / safety) of GEO at λ\* against λ=1e-3 per (condition, K).

---

## Q-g. #11 Phase L tolerance rule: ACCEPT-WITH-CHANGES

**The diagnosis is sound.** cond ≈ 3e6 for the augmented system, with η=κΛ_A negligible beside the AJ/σ_n scale. LSMR at tolerance 1e-6 then needs more than 20p iterations, so A2's 1e-6 is censored by construction, not by accident. A2 itself made censoring INCONCLUSIVE, so keeping A2 unchanged would fix Q3 = INCONCLUSIVE in advance. That is an uninformative experiment, so a change is justified.

**The intersection rule largely neutralises the exposure.**
- The two exposed sizes already imply steep two-point slopes, computed from the reported counts with Δlog K = log 4:

  | Tolerance | grid state | iteration-5 state |
  |---|---|---|
  | 1e-2 | 0.52 | 0.61 |
  | 1e-3 | 0.49 | 0.70 |
  | 1e-4 | 0.67 | 0.92 |

- All of these are well above 0.25. So the exposure says the small-size trend is steep at every tolerance.
- Requiring the criterion at all of {1e-2, 1e-3, 1e-4} is the most demanding reading, so it cannot be used to pick a favourable tolerance.
- LSMR makes ‖Ãᵀr_k‖ monotonically non-increasing, so "first hit" is well defined. Evaluating all thresholds in one run is exact.
- The decision now rests on the three unseen sizes, (80,225), (96,324) and (128,576), and on the leave-one-size-out slopes.

**Changes required (replacement text for #11's label rule):**
> **#11 Phase L tolerance (replaces A2's single 1e-6).** One LSMR run per (size, state, damping). It uses atol=btol=0 and maxiter=20p (unchanged), and records the first iteration at which the explicit relative normal-equation residual is ≤ tol, for tol ∈ {1e-2, 1e-3, 1e-4, 1e-6}.
> - 1e-6 is reported only.
> - 1e-3 is the *reported headline* tolerance. It has **no extra role** in any label.
>
> **INCONCLUSIVE** (= FLAT for ADVANCE) if, at η=0, any of tol 1e-2, 1e-3, 1e-4 is censored at **any** of the 5 sizes, in either state. The slope uses all 5 sizes, so censoring at a small size biases it too. The two largest sizes are not special here.
>
> **BOTTLENECK-OPTIMISABLE** iff, at η=0:
> - (a) the (aj + solve) share is ≥ 50% at the two largest sizes; and
> - (b) at **each** of 1e-2, 1e-3 and 1e-4, all of the following hold: the OLS slope of the per-size mean of log-iterations (mean over the 2 states) against log K is ≥ 0.25; its 95% t-interval (df=3) excludes 0; and all 5 leave-one-size-out slopes are > 0.
>
> Otherwise **ASSEMBLY-BOUND** if the jac share is ≥ 50% at the two largest sizes; otherwise **FLAT**.
>
> **Share (a)** is measured once per size, independent of tolerance. It comes from the LSMR arm's own outer-iteration settings (§3: atol=btol=1e-10, maxiter=p, conlim=1e12), median of 3 exclusive single-thread repeats.
> - It is **not** taken from the instrumented multi-tolerance run. The explicit residual test adds matrix-vector products and would inflate the solve share.
> - With cond ≈ 3e6, that arm will usually hit maxiter=p. This is the "ordinary implementation" by definition. Record the fraction of outer iterations that hit maxiter.
>
> **Reported descriptively:**
> - the per-tolerance slopes, the per-state slopes, the κ=1e-3 slopes (all three tolerances), and the 1e-6 censoring pattern;
> - the cond estimate of the augmented system per (size, state, damping);
> - the cost of the tolerance test, excluded from all timing.
>
> **Exposure disclosure** (verbatim in the freeze record):
> - Before this rule was fixed, the coordinator saw the η=0 first-hit counts at the formal instances (32,36) and (64,144) for both states and all four tolerances (the numbers as listed in #11), and the 1e-6 censoring.
> - The implied two-point slopes are 0.49-0.92, all above 0.25.
> - The thresholds (0.25, df=3, leave-one-out > 0, 50% share) were frozen before the exposure and are not changed.
> - The formal phase L reruns these two instances from scratch. They are deterministic and must reproduce the smoke counts exactly; any mismatch is a FAIL entry.
> - No count at (80,225), (96,324) or (128,576) may be looked at before this rule and the geo_L.py sha are frozen.

**Residual concerns (record, no further change):**
- The tolerance set {1e-2, 1e-3, 1e-4} was chosen after the exposure. Including 1e-4 makes the rule stricter, not looser, so I accept it.
- Censoring risk at 1e-4: at slope ≈ 0.8, about 1.2e4 iterations are expected at (128,576) against maxiter 20p = 69120. This leaves a margin of about 5×. Do not raise maxiter after seeing any larger-size count.
- At η=0 and a=λ/σ_n² the measurement is essentially the undamped Gauss-Newton system. The Q3 verdict therefore speaks to the conditioning of that system. It says nothing about a damped two-level solver in operation.

---

The dev runs I made for this review (3 cells, 200-iteration calibration mode only, in scratchpad/opus_k1_review/) are development evidence. They are not to be reused as phase-D data.

---

## Final check (Q-h, Q-i, Q-j)

Run 20261108T005204Z-opus-review-6dd4. Reviewer: Opus 5.5, self-reported claude-opus-5-5. Read-only: I read /home/claude/geo/K1_FINAL.md, experiments/geo_analyze.py, geo_run.py and geo_L.py, and ran nothing. Scope: only what changes a budget or a decision.

### Q-h. Clock: ACCEPT-WITH-CHANGES

Excluding the quota stall is acceptable:
- Nothing ran during it.
- No L, D or H result is visible.
- The 40 CPU-h ceiling is not changed, so the stall gains no compute and no information.

Keeping the old deadline would force compression with no cost reason behind it, which is worse.

Two changes:
- The plan call must be given the **compression** deadline (`deadline_utc=2026-11-09T18:15Z`), not 22:15Z.
- A rule for any later stall must be frozen now.

Wording to record (replaces the K1.6 bullet):
> **K1.6 clock.**
> - The 48 h clock counts active time only.
> - Used: 2026-11-06T06:38:08Z → 09:04Z = 2 h 26 min. This takes the later stall start, so it overstates the time used.
> - Quota stall: 2026-11-06T09:04Z → 2026-11-08T00:41Z. Excluded, because no job ran and no result existed.
> - Remaining at resume: 45 h 34 min.
> - Deadline 2026-11-09T22:15Z; compression deadline 2026-11-09T18:15Z. The latter is the value passed to `geo_analyze.py plan`.
>
> The compression plan is computed once, at the end of phase D, against this compression deadline, and is never recomputed.
>
> Any later stall (quota limit, or the host pump being down) extends both deadlines mechanically by its logged length. Start and end come from `date -u`, written at the time. Such an extension never triggers re-planning, never undoes a compression, and never adds runs.
>
> No other extension is permitted.

### Q-i. Faithfulness of K1_FINAL.md: ACCEPT-WITH-CHANGES

Must-fix (budget or decision):
1. **Rejection rate.** The C14 rates are not defined. My Q-a text says per trial: rejected trials / all trials. Append to #6: "Rejection rate = rej / trials; clamp rate = trials with ≥1 clamp / trials; all C14 ratios per trial." The code is also wrong here (Q-j item b).
2. **C14 consequence.** K1.4 #6 extends the C14 trigger but never says what a firing does. Add: "If C14 fires for tuned GEO on dev (λ=1e-3), Q2 in both K layers = JOINT-NOT-MATTERS ('GEO-specific failure mode; not Q2 evidence', contract §7). GEO-r8's C14 is information only."

Wording nits (no decision impact):
- K1.2 should say that PCG8P and PCG8D also hit the safety limit in the probe.
- K1.4 HIST/Tikhonov: call it "deviation: not implemented; descriptive rows reported as 'not run'", not compression "per the contract clause". That clause is cost-triggered.
- R5 / Q-d: report raw cell counts next to the fractions.
- `no_step_clamp` ("any trial in the dying sequence") is broader than my wording ("the last rejected trial"). Acceptable; keep as written.

Items 1-12 and R1-R6, Q-f, Q-d, Q-g and Addition (1) are otherwise recorded correctly.

### Q-j. Code readings

- **(1) Clause (a): ACCEPT.** All of BJ and BLK × n_A and W, statistic ≤ 0.5, ≥12 images. Matches R4.
- **(2) Clause (b): ACCEPT.** Per arm; A and W readings both required; GEO ≤ 10% at both; common level from `_pair_levels`. Matches R5 and R-censor.
- **(3) Wall-clock: ACCEPT.** "All three negative" is stricter than "same sign"; I accept it as the frozen reading. Both BJ and BLK are required. The fallback below 6 images is correct.
- **(4) R6: ACCEPT.** Uses θ at the last iterate with A_eff ≤ A_cap and W_eff ≤ W_cap. BJ decides; BLK is reported. The sign of H_interval is correct. For a safety-censored pair the W reading is the censored arm's final θ. That is acceptable, because >10% censoring already vetoes.
- **(5) No thinning: ACCEPT.** `thin_idx` returns every index.
- **(6) λ\* re-check: ACCEPT.** Per K layer, 48 cells; GEO from lamgrid, LMD from vpass_lam; F_ref keyed by (cell, λ) including the 3 restarts.
- **(7) Plan: ACCEPT-WITH-CHANGES.** Must-fix: `finish()` halves the whole projection, including the exclusive timing subset. Timing runs on one job, so its wall-clock time equals its CPU time. At K36 with the 20000 safety limit the timing subset is about 7-8 CPU-h, so the projected finish is optimistic by about 4 h. Minimal fix:

  `finish = now + (cpu_h − timing_h)/2 + timing_h + extra_h`

  `proj()` must return timing_h separately. `extra_h` must include phase L and the λ\* re-check if they run after the plan. Nit: F_ref for base 9202 is not in the projection (about 0.3 CPU-h). Add it while 9202 is kept.

Further must-fixes found in code, outside items 1-7:
- **(a) `load_q2` drops every run with `m['lam'] == 0.0`.** If λ\* = 0 for any (condition, K), all Q2 cells of that stratum are silently excluded. Fix: delete `or m['lam'] == 0.0`. F_0 arms live in GEO-H/q1, which is not loaded here.
- **(b) `reject_rate` is per outer iteration.** Fix: `m['rej'] / max(m['trials'], 1)`. Note that BJ rejections with α\* ≤ 0 add to `rej` without a trial; this does not affect the GEO and LMD C14 comparison.
- **(c) `cmd_q2_label` ignores `C14_flag_tuned_GEO`.** Fix: `if vd['C14_flag_tuned_GEO']: lab = 'JOINT-NOT-MATTERS (C14 GEO-specific failure mode; not Q2 evidence)'`. Check it before the clause tests.

With these 4 code fixes (plan finish, lam==0 filter, reject_rate, C14 in label) and the 2 text fixes, K1 can be frozen. Re-run the container tests and record the new shas before the host V re-run.

## K2 exposure-boundary check (Q-k1..Q-k5)

Self-reported model id: claude-opus-5-5 (run 20261108T031755Z-opus-review-cd1a). Read: OPUS_PACKET_K2_UNEXPOSED_20261108.md, K2_DRAFT.md, experiments/geo_analyze_unexp.py (sha256 721f7da0...), K1_FINAL.md, experiments/geo_analyze.py (sha256 c82382c4..., same as K1.9). No experiments run. The facts in the packet are taken as given. Where I could check them, they hold: geo_analyze.py is unchanged against K1.9, and the container has no outputs/GEO-H.

**Q-k1: ACCEPT-WITH-CHANGES.** The structure is right: the 24-image reading stays primary, the 20-image view is pre-registered, and there is a demote-only consistency rule. The wording "not fully unseen independent evidence" is necessary but not sufficient in two places:
1. The 20-image view is a subset of the same sample, so it is not an independent replication. Agreement between the two readings shows only that the 4 exposed images do not drive the label. It is not confirmation. K2.2 item 3 or 4 must say this.
2. "The 24 images" needs a positive description, not only a negation, so that later reports cannot drift. Required: "24 图留出集, 其中 4 图 (201–204) 有干跑分析暴露 (FAIL-0029); 唯一全程未见的读数是 205–224 的 20 图读数。"
Also state that the 20-image view can never raise a label. It can only demote one, through item 4.

**Q-k2: ACCEPT.** MIN_IMG_A = 12/24 and MIN_IMG_T = 6/12 are coverage floors: at least half the images must have jointly reached cells. Clause (a) compares a point estimate (≤ 0.5) and does not use an interval, so the absolute count has no separate statistical role. Scaling to the same 50% keeps the meaning. Keeping 12 of 20 (60%) would add a stricter threshold and would be the actual change. The n_t < 4 → NOT EVALUABLE rule is acceptable. Implementation fix: derive n_img and n_t from the design, not from whichever files exist. Use n_img = 20, and n_t = the unexposed images in plan['timing_imgs']: 8 for h12, 2 for h6. If the observed count is below the design count, the view is NOT EVALUABLE. Otherwise a run that is missing in one view lowers that view's floor without anyone noticing.

**Q-k3: ACCEPT-WITH-CHANGES.** I find no code path from the dry-run values on 201–204 to caps, λ\*, τ\*, arm or rcond tuning, or the compression plan. select_geo, caps, select_arms, select_lam, vpass and vpass_lam read only GEO-D (dev, base 9101). cmd_plan reads dev medians plus len(TEST_IMGS) and a deadline. The remaining path is human: rule text written after the outputs were seen. geo_analyze.py's sha equals K1.9, and K1.9 already lists the dry-run. So the dry-run happened before the K1 freeze, not after it. Required disclosure in K2.1, mechanical and with date -u:
- the UTC times of the dry-run(s) that printed values on 201–204;
- the time of the K1 freeze/sha record (01:21Z) and of Opus final check 6dd4;
- a statement that every K1 rule change after 6dd4 implements a 6dd4 must-fix verbatim (plan finish, lam==0 filter, reject_rate, C14 in label, 2 text fixes), and that none was prompted by a dry-run value.
If any K1 rule text was changed for another reason between the first value-printing dry-run and 01:21Z, list it in K2.1. Also disclose this new coupling now, before cmd_plan runs. If compression step (4) fires (timing → 201–206), the unexposed timing set has n_t = 2, the 20-image view is NOT EVALUABLE, and **no Q2 ADVANCE is possible**. Do not change the plan rule (item 7). Write the consequence into K2 before the plan is computed, so the plan cannot be read as a choice made after the fact.

**Q-k4: ACCEPT-WITH-CHANGES.** The rule is demote-only. It costs power against a positive finding, and that is the correct direction: exposure can only inflate a positive claim. It cannot manufacture a negative one, because no decision used the exposed values. Keep the trigger on all labels as drafted. Restricting it to JOINT-MATTERS would be a post-hoc narrowing. Make the consequence precise: the flag blocks every positive or directional claim (Q2 JOINT-MATTERS/ADVANCE, Q1 REG-HELPS and REG-HURTS). For neutral or negative primary labels, the primary label is reported unchanged, both readings are shown, and the discrepancy is noted. Code must-fixes in geo_analyze_unexp.py:
- **(a) Q1 consistency is silently empty.** `cmd_h_q1()` returns a dict keyed by int K, while `k = str(K)`. So `k in q1` is always False, `cons['q1']` = {}, and `all([])` = True. Fix: `q1k = q1.get(K, q1.get(k))`, and if either side lacks K, set the view to NOT EVALUABLE (depends = True).
- **(b) Compare label categories, not full strings.** Map each label to JOINT-MATTERS / JOINT-NOT-MATTERS / INCONCLUSIVE by prefix before comparing. Reason suffixes such as "(>10% safety-censored...)" must not count as a label difference.
- **(c)** When timing is not evaluable, also mark each per-K 20-image Q2 label NOT EVALUABLE, not only `overall`.
- **(d)** Use design counts (see Q-k2).
After these fixes, rerun the dry test on the dry-run outputs. It must show non-empty `cons['q1']` for both K. Then record the new sha in K2.

**Q-k5: Before the first formal H result becomes visible:**
1. Append K2 (with @@DATE@@ from date -u and the Q-k3 timeline) and record the fixed geo_analyze_unexp.py sha before the first H job is launched, not only before the first analysis.
2. On the host, confirm that outputs/GEO-H is empty, so that no dry-run npz/json can be picked up by runs_in. Also confirm that choices.json comes from formal phase D, not from a dry-run.
3. Run geo_analyze_unexp.py in the same session as the primary q2_label/h_q1, and before any prose about H is written. Report CONSISTENCY.json next to Q2_LABEL.json.
4. Nobody re-opens the dry-run printouts for 201–204. Do nothing else; no new readings.

**Required text changes to K2_DRAFT.md**
- K2.1: append the timeline sentence from Q-k3 (UTC times of the dry-run and the freeze; "K1 post-6dd4 edits = 6dd4 must-fixes only; none prompted by dry-run values").
- K2.2 item 1: after "…独立证据\"", add "; 正式描述为: 24 图留出集, 其中 4 图 (201–204) 有干跑分析暴露 (FAIL-0029); 唯一全程未见的读数是 205–224 的 20 图读数".
- K2.2 item 2: replace "未暴露 Q2 图数" with "设计中的未暴露 Q2 图数 (=20)", and "n_t" with "按 plan['timing_imgs'] 的设计未暴露计时图数 (h12→8, h6→2)"; add "实际图数少于设计数 → 该读数 NOT EVALUABLE".
- K2.2 item 3: add "20 图读数是同一样本的子集, 不是独立重复; 一致只说明标签不依赖暴露的 4 图, 不构成确认。"
- K2.2 item 4: replace the last clause with "20 图读数只能降级, 不能升级任何标签; 不一致或不可评估时, 一切正向/有方向结论 (Q2 JOINT-MATTERS/ADVANCE, Q1 REG-HELPS/REG-HURTS) 不得写成 ADVANCE, 留待全新数据; 中性/负的主标签照原样报告, 并列出两读数与差异。标签按类别 (JOINT-MATTERS / JOINT-NOT-MATTERS / INCONCLUSIVE; REG-*) 比较。"
- New K2.2 item 6: "若阶段 D 末压缩步 (4) 触发 (计时 201–206), 未暴露计时图仅 2 张, 20 图 Q2 读数 NOT EVALUABLE, 因而 Q2 不可能 ADVANCE; 此后果在计划计算前登记, 计划规则不改。"
- K2.3: add the sha of the fixed geo_analyze_unexp.py.
