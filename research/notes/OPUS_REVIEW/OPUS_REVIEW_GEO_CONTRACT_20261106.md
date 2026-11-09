claude-opus-5-5

# Opus scientific gate: GEO 48h contract candidate v1

Reviewer: Opus 5.5 (self-reported model id on line 1). Read-only review. I read only the packet and GEO_CONTRACT_CANDIDATE_v1.md. I ran nothing. Validated contributions so far: 0.

## VERDICT: FREEZE-WITH-CHANGES

The core algebra in §1 is correct: the normal equations, their signs, the z-system, the back-map and the augmented LSMR right-hand side all check out. The design can still produce a trivial or misleading readout in four places:
(i) The claimed equivalence of the parameter steps is false for PCG/Jacobi, and it is fragile under rank truncation. Because θ' = θ + δ depends on the parameter step δ, not on the image step Jδ, the arms follow different paths.
(ii) Box clamps break the pred/ρ_gain/guard logic.
(iii) Q1 compares a λ tuned on clean dev images against a DP stop with a fixed τ, using a different solver. This favours REG-HELPS.
(iv) Q3's "slope ≥ 1.5" is mostly a readout of whether J is stored dense. That makes BOTTLENECK-OPTIMISABLE true by implementation choice, and Q3 is what ADVANCE-7D depends on.
None of these needs a new experiment. The required changes C1-C14 are listed at the end.

---

## 1. MATH (§1)

**Normal equations P.** The linearised data residual is W(A(x+Jδ) − y) = −W(r − AJδ). The gradient of the subproblem is
−JᵀAᵀW²(r − AJδ) + aJᵀ(x + Jδ) + ηJᵀJδ = 0,
which gives (JᵀAᵀW²AJ + (a+η)JᵀJ)δ = JᵀAᵀW²r − aJᵀx. The sign of the −aJᵀx term is **correct**.

**Solution set.** P = JᵀMJ with M = AᵀW²A + (a+η)I ≻ 0. This gives null(JᵀMJ) = null(J) and range(JᵀMJ) = range(Jᵀ), and the right-hand side Jᵀ(AᵀW²r − ax) lies in range(Jᵀ). So the system is consistent, the solution set is δ_min + null(J), and Jδ is unique. **Correct.** M ≻ 0 holds even with η = 0 as long as a > 0.

**z-system.** With U having orthonormal columns, ||Uz|| = ||z||. Minimising ½||W(r−AUz)||² + (a/2)||x+Uz||² + (η/2)||z||² gives (BᵀB + (a+η)I)z = BᵀWr − aUᵀx with B = WAU. **Correct.** Because W is a scalar, BᵀWr = UᵀAᵀW²r.

**Back-map.** δ = VΣ⁻¹z gives Jδ = Uz, and δ lies in range(V) = range(Jᵀ), so δ is the minimum-norm preimage. **Correct, with a serious caveat.** The cutoff σ_i ≤ 1e-10·σ_1 keeps directions whose amplification 1/σ_i reaches 1e10. Image-metric damping η shrinks z uniformly. It does **not** bound the parameter step along weak directions. Each δ_i = z_i/σ_i, so increasing κ shrinks all of δ but leaves the relative blow-up unchanged.

Weak directions are expected, not exotic. Examples are geometry columns of a Gaussian with amplitude near 0 (every geometry column scales with amplitude), wide Gaussians with σ up to 12 px on a 32-pixel image (nearly collinear), and Gaussians partly outside the image (positions are allowed in [−4, N+4]). In these cases GEO proposes huge parameter jumps. The clamp or the guard then rejects them, κ climbs, and GEO can stall or hit κ_max for a reason that has nothing to do with the joint-versus-block question. LMD's diag(H_a) damping acts in parameter space and does not share this failure. **This is the real algorithmic difference between GEO and LMD and must be named (C2, C3).**

**Equivalence with CG/LSMR from 0.**
- LSMR on the augmented system [WAJ; √(a+η)J]δ ≈ [Wr; −ax/√(a+η)]. Its normal equations reproduce P exactly (√(a+η)·(−a/√(a+η)) = −a), so **the right-hand side is correct**. LSMR started at 0 converges in exact arithmetic to the minimum-norm least-squares solution, which is the same set as for P. **Correct in exact arithmetic.** With maxiter = p and atol = btol = 1e-10 on an ill-conditioned J, though, LSMR truncates implicitly in exactly the weak directions where GEO amplifies by up to 1e10. The image steps agree to tolerance. The parameter δ, and therefore θ', does not.
- PCG8 with a Jacobi preconditioner D = diag(P), started at 0, is CG on D^{-1/2}PD^{-1/2}. Converged, it gives the **minimum-D-norm** δ, not the minimum-Euclidean-norm δ. The image step is the same, but the parameter step is different, and §1's claim "PCG(→converged) agrees" is **false at the level that matters** (θ' = clamp(θ+δ)). §1 says S = I for all arms. PCG with a Jacobi preconditioner effectively uses S = D^{-1/2}.
- Consequence: V2 checks only the image step, so it can pass while the arms' trajectories diverge. The statement in §1/§9 that the arms differ only by truncation, tolerance or cost is too strong. They also differ in the implied parameter metric of the preimage, which affects nonlinear progress. Fix: C2.

**PCG8 as "3DGS-LM style".** 3DGS-LM damps with diag(JᵀJ) in parameter space. PCG8 as written solves P, which has image-metric damping (a+η)JᵀJ. It is therefore a truncated GEO, not 3DGS-LM. The faithful comparator is PCG8 on the LMD system (C4).

**η = κ·λ_max(BᵀB).** The scaling is sensible: λ_max(BᵀB) ≤ ||WA||² ≈ σ_n⁻² for a normalised blur, and a = λ/σ_n², so η/a ≈ κ/λ is dimensionless and consistent. It is **not computable cheaply matrix-free**, because for LSMR/PCG8 it is a generalised eigenvalue of (JᵀAᵀW²AJ, JᵀJ). Replace it with η = κ·||WA||₂², which is known in closed form and identical for all arms (C5).

**pred / ρ_gain.** pred = m(0) − m(z) with m excluding η. Since z minimises m + (η/2)||z||², pred ≥ (η/2)||z||² ≥ 0. **Correct for an unclamped step.** The κ rule leaves two things open. First, nothing says what happens to κ when a step is accepted with 1e-4 ≤ ρ < 0.75 (presumably κ is unchanged; say so). Second, §1 fixes the rejection factor at 4κ while §3 tunes a "backtracking factor ∈ {3, 10}". These contradict each other (C6).

**Non-linearity guard.** ||x(θ') − x(θ) − Uz|| ≤ ||Uz|| tolerates a 100% relative linearisation error. That is very loose and nearly redundant with "F decreases and ρ ≥ 1e-4". It is also written only in terms of Uz, so it is not obviously applied to LMD, LSMR or PCG8, which contradicts "acceptance identical for all arms". Either drop it, or apply it to every arm as ||x(θ') − x(θ) − Jδ_c|| ≤ c·||Jδ_c||, where δ_c is the clamped step and c is fixed (for example 0.5) (C3).

**Box clamps.** θ' = clamp(θ+δ), but pred and the guard are evaluated at the unclamped z.
(a) The guard fires because of the clamp, not because of nonlinearity.
(b) ρ_gain uses a model reduction that was never taken. Once the model is evaluated at the clamped step, pred can be small or negative, and the ratio becomes meaningless or flips sign.
(c) GEO hits the clamp more often than LMD because of the weak-direction blow-up above. GEO is penalised for something other than joint computation.
Fix: compute pred = m(0) − m(Jδ_c) at the clamped step, reject when pred ≤ 0, record the clamp rate per arm, and run the optimality test in V4 on the projected gradient (C3).

**V4 optimality.** "Residual ≤ 1e-6" is an absolute threshold. With W = 1/σ_n ≈ 33-100, gradients are of order 1e3-1e4, so the threshold is meaningless. Use a relative projected-gradient norm, ||P_box(∇F_a)|| / ||∇F_a(θ_0)|| ≤ 1e-6, with active bounds excluded (C7).

**Notation clash.** "a" is the regularisation weight and also the amplitude in θ = (a, mx, my, …). "α" appears in V4 and §9, and λ appears in §5 (a = λ/σ_n²). Rename: amplitude → w_k, regulariser → a = λ/σ_n² only, and drop α (C1).

## 2. FAIRNESS (§3, §4, §7)

- **Same footing.** Objective, initialisation, feasible set and acceptance are the same on paper. In practice they differ through (i) the preimage metric (GEO uses a Euclidean minimum-norm δ with a 1e-10 cutoff, PCG uses a minimum-D-norm δ, LSMR truncates implicitly), (ii) the clamp interaction, and (iii) the guard being written only for GEO. Fixes: C2-C4.
- **LMD versus image metric.** The single real algorithmic difference between LMD and the GEO family is the damping metric: parameter-space diag(H_a) versus image-space JᵀJ. The contract should state that this is the only difference, and that "GEO vs LMD" is therefore a test of the damping metric, not of joint computation (C4).
- **BLK budget.** "Iterations counted in sweeps" compares 60 sweeps with 60 joint outer iterations. One sweep costs K block renders and solves, roughly one full Jacobian or more. BLK is also a Python loop over K, so at K = 36 interpreter overhead can dominate wall-clock. That makes JOINT-MATTERS (a), "≤ 0.5× wall-clock", close to trivially true. Fix:
  (1) Set the per-cell budget as a common wall-clock cap, for example 5× the dev median time-to-converge of GEO, applied identically to every arm.
  (2) Make counts co-primary with wall-clock: full-image-equivalent renders, A-applications and flops.
  (3) Add a **block-Jacobi** arm, BJ. BJ is the joint step with the Gram matrix made block-diagonal per Gaussian, solved in one vectorised step. GEO versus BJ isolates the effect of the coupling with no interpreter confound. BLK (Gauss-Seidel) stays as a second contrast. (C8)
- **F_ref adequacy and gaming.** F_ref is the minimum over all runs plus 3 perturbed LMD-500 restarts. It is fine as a heuristic. Its weakness is that s ≤ 1e-2 mixes speed with which basin an arm lands in. An arm that converges fast to a slightly worse local minimum counts as a "failure" in the Q2 25%/90% rule. Fix: report (a) the final s at the budget, (b) time-to-own-plateau, and (c) time-to-s ≤ 1e-2 only on cells where both arms reach it. The failure rule should use (a) under the common wall-clock cap (C9).
  There is a gaming route: the arm that defines F_ref gets s = 0 by construction. This is benign as long as the restarts are LMD-only and identical across arms. Also report how often each arm is the F_ref holder.
- **Trivial wins and losses.**
  - At N = 32 and p ≤ 216, dense SVD costs about a millisecond, so GEO's wall-clock is overhead-dominated and Q2 timing at small sizes is uninformative. Use counts.
  - Q3 at large sizes depends on dense versus truncated J (see §4 below).
  - State that backtracking retries reuse the SVD, so it is computed once per outer iteration (C6).

## 3. DATA and LEAKAGE (§2, V5)

- **Family mapping.** For dev, i = 101 gives (100 mod 3) = 1, so the order is tex, mix, edge, and each family gets 4 images. For held-out (201-224), each family gets 8. The arithmetic is correct.
- **Seed collision risk.** Clean images use seed 8000+i, and noise uses base seeds 9101, 9201 and 9202 "per the as_gen.noisy_obs rule". If that rule is additive (base + i or base + i + cond), the dev and held-out noise streams can overlap: for example, 9101 + 112 = 9213 = 9201 + 12. The scale-ladder seed 9301 sits nearby. Fix: derive every stream as np.random.SeedSequence((tag, base, i, cond, seed_idx)). V5 should assert that the seed sets are pairwise disjoint from each other, from S2 (images 1-24) and from the E41-58 generator seeds (C10).
- **Tuning λ\* with clean dev MSE.** This is legitimate hyperparameter tuning on dev, and §9 discloses it. It is **unfair inside Q1**, though. F_a\* gets 7 values per (condition, K) chosen with the clean image, while F_0+DP uses a fixed τ = 1. Fix: tune τ on dev with the same budget and criterion, τ ∈ {0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0}. Additionally report the untuned principled pair: λ chosen y-only by DP or GCV, versus τ = 1 (C11).
- **Other leakage paths.** The grid initialisation and the amplitude least-squares use only y. F_ref is computed on the evaluation side, and V5 checks the dev logs. I see no held-out leak beyond the seed issue. Note that the generator distribution is the same one used to design S2, so held-out data is independent in samples but not in distribution. Say so in §9.

## 4. THRESHOLDS (§7)

- **REG-HELPS / REG-HURTS.** H ≥ 0.05, a t-interval excluding 0, and at least 3 of 4 conditions with H ≥ 0 are reasonable. Make three points explicit: (a) the CI is computed on the mean log-ratio over images and then transformed; (b) the comparison uses the **same solver**, since §0 says "same solver" but §4/§5 run the DP arm with LMD; (c) Q1 is reported separately per K, because with p = 96 or 216 against m = 1024, DP with τ = 1 may never trigger. Report the DP trigger rate. If it is below 50%, Q1 is effectively "F_a\* vs converged F_0" and must be labelled that way (C11).
- **JOINT-MATTERS.** (a) is ambiguous: does "on both K tiers" also bind the 25%/90% clause? It also depends on wall-clock, which the Python loop distorts.
  Replacement: JOINT-MATTERS holds if, on both K tiers, GEO needs ≤ 0.5× the work of **BJ** (and of BLK) to reach the common target on jointly-reached cells, OR BJ/BLK has final s > 1e-2 on ≥ 25% of cells under the common wall-clock cap while GEO has it on ≤ 10%. In addition, the GEO-vs-BJ quality H must have a CI lower bound ≥ −0.02. Work is measured as full-image-equivalent renders plus A-applications.
  Wall-clock is reported, and its ratio must point the same way (C8, C9).
  Also add a caveat: for overlapping blurred Gaussians, joint Gauss-Newton beating coordinate descent is the prior expectation, so JOINT-MATTERS is a precondition check, not a finding.
- **BOTTLENECK-OPTIMISABLE: ill-posed. This is the main blocker.**
  1. With K/N² held fixed (36/1024 ≈ 324/9216 ≈ 0.035), m grows like K. A matvec with a dense J costs m·p, which grows like K². Any implementation with dense J therefore shows a slope of about 2, above the 1.5 threshold, by construction. Every practical Gaussian renderer truncates support to 3-4σ, which gives a slope near 1. So the label reads the implementation, not the problem.
  2. "Fastest arm per size" can switch arms between sizes, so the slope mixes arms.
  3. A slope from 2 or 3 points is unstable.
  4. With at most 10 outer iterations, s ≤ 1e-2 on the scale ladder may never be reached, and the time-to-target is then undefined.
  5. Gram coupling ≤ 0.3 at the largest size is almost certainly true for local Gaussians at K = 576, so it does not discriminate.
  **Replacement (C12).**
  - Require the "strongest ordinary implementation" to use J truncated to 4σ support and stored sparse. A dense J is reported only as a reference.
  - Fix a single arm, the one fastest per iteration at the largest common size, for every size.
  - Use OLS log-log fits over all runnable sizes. Add one size, (80, 225), to give 4-5 points.
  - Primary quantity: the **number of inner Krylov iterations** (LSMR, and PCG on the LMD system) needed to reach a fixed relative residual of 1e-6 on the linearised step, measured at the same θ (initialisation and iteration 5). This is the quantity a coarse space or two-level method attacks.
  - BOTTLENECK-OPTIMISABLE holds if (a) linear solve plus A-application is ≥ 50% of per-iteration time at the largest two sizes under sparse J, **and** (b) the log-log slope of inner iterations against K is ≥ 0.25 and its 4-point bootstrap interval excludes 0.
  - ASSEMBLY-BOUND holds if render plus J assembly is ≥ 50%. Otherwise the label is FLAT.
  - Gram coupling sparsity is reported descriptively, not as a gate.
  - Report per-iteration time, not time-to-s.

## 5. BUDGET and FEASIBILITY (§5)

- **Phase L.** A dense SVD of 9216×1944 costs on the order of m·p² ≈ 3.5e10, times a constant of 4-6. That is about 5-15 s single-threaded per SVD. J and U are about 143 MB each, so 8 GB is fine. Skipping (128, 576) dense is right: that SVD would take about 1-2 min each and several GB. **Feasible.**
- **Phase H.** The F_ref restarts are 384 × 3 × 500 LMD iterations, at a few ms each at N = 32, so tens of minutes. BLK, vectorised or not, is the main Python cost. About 5 CPU-h is plausible **only if** wall-clock timing is not repeated 3 times on all 384 cells × all arms. §4 asks for medians of 3 repeats, and §5 runs 2 concurrent jobs, which contaminates timing. Fix: quality comes from the full concurrent run, with counts logged. Wall-clock comes from a dedicated exclusive single-thread subset (24 images × 4 conditions × seed 1 × 2 K = 192 cells, 3 repeats, GEO/BJ/BLK/LMD/LSMR/PCG only) (C13).
- **Order for a decision within 48h.** Run V, then L (exclusive, about 1 h, independent of dev, and it may already settle Q3), then D, then H. A Q3 that fails early tells you ADVANCE-7D is off the table regardless.
- **Cuts if time runs short (in this order):** drop the dev-tuned Tikhonov row and keep only GCV; drop HIST from timing; drop the K = 16 tier from Phase L. Never drop F_ref restarts or V-tests.

## 6. NOVELTY and CLAIM HYGIENE

The contract is mostly honest. It says a single-SVD regularised GN/LM step is not novel, cites 3DGS-LM for matrix-free PCG-LM, labels everything proposed, and keeps Q1/Q2/Q3 separate without decomposition. Corrections:
- Remove "PCG(→converged) agrees" and "the only differences are truncation, tolerance, cost" (§1, §9). Replace them with: "same image step; different parameter preimage (Euclidean minimum-norm with cutoff / D-norm / implicit truncation)" (C2).
- Do not call PCG8-on-P "3DGS-LM style" (C4).
- State that JOINT-MATTERS is expected a priori and that ADVANCE-7D requires a measured Krylov-iteration growth, not a cost exponent from a dense implementation (C12).
- Q1 labels must name the solver and whether DP actually triggered.
- In §10 (G0), add Levenberg-Marquardt with geodesic acceleration / pullback-metric LM, the Hanke regularising LM and IRGN (unread, L2), and block-Jacobi / additive-Schwarz preconditioning for Gauss-Newton. The last one is the direct neighbour of the future "coupled neighbourhood + shared coarse space" idea and should be read before ADVANCE.

## 7. MISSING before freeze

- The damping-metric difference between LMD and GEO is the only algorithmic difference. Say it (C4).
- Jacobian truncation (support radius) must be fixed in the contract for every arm. The value of J at x matters for V1 at 1e-12 against as_core, so use the same truncation as as_core, or none at N = 32, and 4σ sparse in Phase L (C12).
- Amplitude sign and near-zero amplitudes create rank deficiency. Log per step: cond(J) = σ_1/σ_ρ, the rank ρ, the count of |w_k| < 1e-3·max|w|, and the clamp rate (C14).
- Conditioning of U for K = 36 on 32×32: J is 1024×216 and well within dense range, but cond(J) can exceed 1e8 with wide Gaussians. Use the same rcond = 1e-8·σ_1 pseudo-inverse truncation in GEO, in the V2 dense reference, and as the recorded effective truncation for LSMR (C2).
- x_ref = 0 makes the regulariser pure image shrinkage. Disclose in §9 that REG-HELPS may simply reflect intensity shrinkage. Optionally report the mean intensity bias of x̂ − x_true.
- V2 must use the same rcond on both sides. Otherwise 1e-8 agreement with np.linalg.pinv (default rcond 1e-15) can fail spuriously.

---

## Required changes (each fixable without new experiments)

1. **C1. Notation.** Amplitude becomes w_k. The regulariser is a = λ/σ_n² only. Remove α.
2. **C2. Preimage and truncation.**
   - Set one rcond = 1e-8·σ_1 for GEO and the V2 dense reference.
   - Correct the §1/§9 equivalence wording to "image step equal; parameter step differs (PCG gives a D-norm minimiser; LSMR truncates implicitly)".
   - Extend V2 to report the parameter-δ difference, descriptively.
3. **C3. Clamps and acceptance.**
   - pred = m(0) − m(Jδ_c) at the clamped step; reject when pred ≤ 0.
   - Either drop the guard or apply it uniformly as ||x(θ') − x(θ) − Jδ_c|| ≤ 0.5·||Jδ_c||.
   - Log the clamp rate per arm.
4. **C4. PCG8 and the LMD contrast.**
   - Add PCG8 on the LMD (diag-damped) system as the faithful 3DGS-LM arm. Keep PCG8 on P labelled "truncated GEO".
   - State that GEO vs LMD tests the damping metric only.
5. **C5. η rule.** η = κ·||WA||₂² (closed form) for every arm.
6. **C6. κ rule.** Unify the rejection factor (the tuned factor ∈ {3, 10} replaces the fixed 4). On acceptance with 1e-4 ≤ ρ < 0.75, κ is unchanged. Backtracking retries reuse the SVD/J.
7. **C7. V4 optimality.** Use a relative projected-gradient norm ≤ 1e-6, with active bounds excluded.
8. **C8. Q2 arms and metric.**
   - Add the vectorised block-Jacobi arm BJ.
   - Use a common per-cell wall-clock cap (5× the dev GEO median).
   - Make work counts co-primary with wall-clock.
   - Use the JOINT-MATTERS replacement in §4 above, with explicit scoping of "on both K tiers".
9. **C9. Gap reporting.** Report final s at the cap, time-to-own-plateau, and time-to-s ≤ 1e-2 only on jointly-reached cells; base the failure rule on final s. Report how often each arm holds F_ref.
10. **C10. Seeds.** Derive every stream with SeedSequence((tag, base, i, cond, k)). V5 asserts disjointness from S2 and E41-58.
11. **C11. Q1 fairness.**
    - Use the same solver (GEO) for F_a\* and F_0+DP, with an LMD cross-check row.
    - Tune τ on dev with the same budget and criterion as λ, and also report the untuned y-only pair (DP/GCV λ vs τ = 1).
    - Report the DP trigger rate and per-K results. Below 50% triggering, relabel the comparison as against converged F_0.
12. **C12. Q3 redefinition.**
    - Sparse 4σ-truncated J for the ordinary arms.
    - One fixed arm across sizes; OLS over at least 4 sizes, adding (80, 225).
    - Primary quantity: inner Krylov iterations to a 1e-6 relative residual at fixed θ.
    - BOTTLENECK-OPTIMISABLE = (solve + A-application ≥ 50% under sparse J) ∧ (inner-iteration slope against K ≥ 0.25, with a bootstrap interval excluding 0).
    - Coupling sparsity is descriptive only.
13. **C13. Timing protocol.** Quality comes from the full concurrent run. Wall-clock comes from an exclusive single-thread 192-cell subset with 3 repeats. Phase order is V → L → D → H.
14. **C14. Diagnostics.** Log per step cond(J), rank ρ, the count of near-zero amplitudes and boundary-located Gaussians, and the clamp rate. If GEO rejects or clamps ≥ 3× more often than LMD on dev, report that as a GEO-specific failure mode, not as Q2 evidence.
