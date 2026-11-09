claude-opus-5-5

# Opus narrow review: 5 self-chosen deviations in GEO contract v2 (before any formal D/H result)

Reviewer: Opus 5.5 (self-reported model id on line 1). Read-only. I read the packet, GEO_CONTRACT_CANDIDATE_v2.md and my earlier review. I ran nothing and changed nothing. Validated contributions: 0. Scope: items 1-5 only.

**Overall verdict: ACCEPT-WITH-CHANGES on all 5.** Three changes affect decisions (items 1, 2, 5) and must go into an append-only addendum before any formal D/H number is visible. Items 3 and 4 change descriptive rows only.

---

## Item 1. A-application count cap: ACCEPT-WITH-CHANGES (affects the budget and Q2)

Using a count instead of wall-clock for reproducibility is the right call. As written, though, the cap misreads Q2 in two ways.

**(a) The A-count leaves out the cost that separates GEO from BJ.**
- Per outer iteration, GEO and BJ both form AJ, which is p A-applications. So the A-count puts them at identical cost per iteration.
- Their solves differ by more than an order of magnitude. Rough flops at N=32, K=36, p=216, m=1024:
  - GEO thin SVD: 4mp² + 8p³ ≈ 2.7e8.
  - BJ batched 6×6 blocks: K·(4m·36 + 8·216) ≈ 5e6.
  - AJ: about 1e7 to 1.3e7, depending on how Op is implemented.
- So GEO's SVD dominates its own per-iteration cost. Under flops, GEO costs roughly 10-15× BJ per iteration, while the A-count says 1×.
- Clause (a) of JOINT-MATTERS ("GEO ≤ 0.5× BJ work") can therefore pass in A-count purely because the dominant cost is uncounted.
- The same omission affects LSMR and PCG. With dense J at N=32, one Jv or Jᵀv costs 2mp ≈ 4.4e5 flops, which is several times one A-application. Their A-count understates their cost too, just in a different proportion.
- The wall-clock "same direction" check catches only the sign of the comparison, not the 0.5× size. At N=32 wall-clock is also dominated by overhead.

**(b) The 200-iteration stop binds before A_cap for cheap-per-iteration arms.**
- A_cap is 5× the median GEO count at GEO's own stop.
- BJ costs the same per iteration as GEO, so it runs into the 200-iteration limit before it reaches A_cap whenever GEO's median stop is above 40 iterations.
- PCG8P costs about 17 A-applications per iteration, compared with about p for GEO. It is cut off at 200 iterations, which is roughly 1/10 of its budget or less.
- Clause (b) of Q2 then measures "fails within 200 iterations", not "fails under a common work budget". The arms whose strength is many cheap iterations lose most from this.

**Replacement text (addendum A1):**
> A1.1 Work proxy. Each run logs, per outer iteration, n_A (as defined in §3) and the deterministic flop proxy W = n_A·F_A + Σ F_solve + Σ F_J + Σ F_mv. All terms come from a frozen formula table, written into the addendum before phase D runs:
> - F_A: the flops of the implemented Op (4N³ if B is dense N×N; 4·L·N² if separable with kernel length L).
> - Thin SVD of m×p: 4mp² + 8p³.
> - Gram formation: 2mp².
> - Dense p×p solve or eigh: 9p³ for eigh, p³/3 for Cholesky.
> - Batched block SVD: K·(4m·36 + 8·216).
> - Jv and Jᵀv: 2·nnz(J) each.
> - J build: 30·nnz(J), for full J or per block.
> - Vector ops: ignored.
>
> W_cap(K) = 5 × the dev median of GEO's W at its stop. W_cap is frozen together with A_cap at the end of phase D.
>
> A1.2 Budgeted runs (phase H and the dev tuning runs for every arm) stop only when both n_A ≥ A_cap and W ≥ W_cap, or on convergence (3 consecutive accepted steps with relative decrease < 1e-9), or when κ/λ_LM reaches its upper limit, or at a safety limit of 5000 outer iterations, which is logged and reported if hit. The 200-iteration limit is used only to calibrate A_cap and W_cap from GEO.
>
> A1.3 Q2 JOINT-MATTERS must hold under both accountings:
> - clause (a) holds in n_A and in W;
> - clause (b) holds with final s read at A_cap and read at W_cap;
> - the exclusive-subset wall-clock ratio points the same way as both.
>
> If the result differs between the two accountings, the label is JOINT-NOT-MATTERS and both readings are reported.
>
> A1.4 Counting conventions. When GEO, BJ or LMD obtain A·jv_c as (AJ)δ_c, it costs 0 A-applications. For LSMR and PCG it costs 1. Every trial evaluation of F_a(θ') costs 1. BLK block trials each cost 1. These conventions are logged per arm.

## Item 2. Q3 slope interval: ACCEPT-WITH-CHANGES (affects the decision; Q3 gates ADVANCE)

Replacing the bootstrap with an OLS t-interval (df=3) plus leave-one-size-out slopes is acceptable, and better than a bootstrap with n=5. Using one value per size (the mean of log-iterations over the 2 states) is correct, and df=3 is honest. Iteration counts are deterministic, so the interval measures how well the power law fits, not sampling noise. Say that in the report. The thresholds are sensible: slope 0.25 means about a 2× growth over a 16× range in K, and t₀.₉₇₅,₃ = 3.18 is strict.

The contract leaves three quantities unfixed that drive the result:
- **Damping during the inner-iteration measurement.** The Krylov count depends strongly on (a+η). A large κ flattens the slope by construction. Phase L runs before phase D, so κ₀ has not been tuned yet.
- **Censoring.** maxiter = p grows with K, so a run that hits the cap biases the slope.
- **Stopping definition.** "Relative normal-equation residual" has to map onto LSMR's own test explicitly.

**Replacement text (addendum A2):**
> In phase L, the inner-iteration measurement uses λ=1e-3 (a=λ/σ_n²) and two fixed damping levels: η=0 (primary) and κ=1e-3 (secondary). Both are frozen now. The iteration-5 state is generated by LSMR outer iterations with κ₀=1e-3 and f=10.
>
> The stopping test is ||Ã^T(b̃ − Ãδ_k)|| ≤ 1e-6·||Ã^T b̃|| on the augmented system, computed explicitly. LSMR atol and btol are set to 0 so that only this test stops the run, with maxiter = 20p.
>
> Any censored run at the two largest sizes makes Q3 INCONCLUSIVE, which is treated like FLAT for ADVANCE.
>
> BOTTLENECK-OPTIMISABLE is judged on the primary damping (η=0) only.
>
> Per-state slopes and the κ=1e-3 slope are reported descriptively. If the two per-state slopes differ in sign, that is flagged in the report.

## Item 3. PCG8D diagonal from AJ column norms: ACCEPT-WITH-CHANGES (descriptive only; Q2's decision uses BJ and BLK)

As a stand-in for the math, diag((AJ)ᵀAJ) + a·diag(JᵀJ) is the faithful analogue. In 3DGS-LM, diag(JᵀJ) is exact for that paper's full forward model, and here the forward model is A∘render. As a stand-in for the cost, it is not faithful. Paying p A-applications per outer iteration for the diagonal makes PCG8D cost as much per iteration as GEO plus about 16. That throws away the cheapness of the matrix-free method, which is the reason to include it. Under A1.2 this matters less, but it still misstates PCG8D's position.

**Replacement text (addendum A3):**
> PCG8D keeps the exact diagonal. It logs two counts:
> - n_A^strict: diagonal included, p A-applications per outer iteration;
> - n_A^cached: diagonal excluded, the analogue of 3DGS-LM's cached per-pixel gradients.
>
> W is logged the same way, in strict and cached forms. The run continues until the cached accounting crosses A_cap and W_cap (A1.2). Final s is reported at both readings.
>
> PCG8D is not part of any decision rule.

## Item 4. y-only pairing with λ_DP: ACCEPT-WITH-CHANGES (descriptive only; Q1's decision uses λ* vs τ*)

"Largest grid λ whose solution satisfies ||y − Ax||² ≤ N²σ_n²" is standard discrete Morozov, and comparing it with τ=1 is the right untuned counterpart. Three points need fixing:
- **"Converged" is undefined under a budget.** It should mean the same endpoint as the λ* runs.
- **Non-monotone residuals.** The model is nonconvex, so the residual need not be monotone in λ, and local minima are possible.
- **Infeasibility is likely.** At K=16, model misfit on edge images will often keep the residual above N²σ_n² for every λ. The same applies to the τ=1 early-stop arm, which then never stops early.

**Replacement text (addendum A4):**
> The GEO solution for λ_DP is the GEO endpoint under the same budget and stopping rules as the λ* runs (A1.2), from the same initialisation, computed per held-out cell from y only.
>
> λ_DP = the largest λ in {1e-6, 1e-5, …, 1e-1} that satisfies the inequality.
>
> If no grid λ satisfies it, the cell is marked DP-infeasible and λ_DP = 1e-6.
>
> Cells where the satisfying set is not contiguous in λ are reported as non-monotone.
>
> The DP-infeasible rate and the non-monotone rate are reported per (K, condition). For the τ=1 arm, the trigger rate is reported.
>
> Any (K, condition) stratum with more than 50% DP-infeasible cells in either arm is labelled "y-only pair uninformative (model-misfit floor)" for that stratum.

## Item 5. BLK retries ≤ 4 and a single global κ for BJ: ACCEPT-WITH-CHANGES (affects the Q2 decision)

**BJ.** A single global κ is the right way to isolate coupling, because GEO also has one κ and one acceptance test. Per-block κ has no meaning inside one joint acceptance. The real bias is somewhere else: an unrelaxed block-Jacobi sum Σ_k J_kδ_k overshoots wherever Gaussians overlap, because each block counts the shared residual again. The global κ then has to grow to tame the overshoot, so BJ loses for a reason that is a known weakness of plain Jacobi without relaxation, not evidence that coupling matters. The standard strong form of BJ (additive Schwarz with an optimal step) fixes this at no extra A-applications.

**BLK.** The limit of 4 retries is smaller than GEO's 10, and the contract does not say whether κ_k carries over between sweeps. If κ_k resets every sweep, BLK wastes trials. Retries are counted under A1, so making the rules uniform is cheap.

**Replacement text (addendum A5):**
> A5.1 The BJ step is δ = α*·Σ_k δ_k, where α* = argmin over α > 0 of the undamped quadratic model m(α·Jδ). This has a closed form from AJ and r with 0 extra A-applications. The step is then clamped and goes through the unified acceptance test. α* is logged per step. GEO is unchanged.
>
> A5.2 BLK uses up to 10 backtracks per block, the same as GEO's per-iteration limit, and each one is counted. κ_k carries over across sweeps under the §1 rule. A block that is still rejected after 10 backtracks is skipped for that sweep, and the skip rate is logged.
>
> A5.3 V7 is extended: BJ with α* at K=1 must match GEO up to the scaling α*. It must match exactly when α*=1 is forced.

---

## Changes to record in the append-only addendum before the first formal D/H result is visible

1. **A1.1-A1.4:** the flop proxy W and W_cap; the 200-iteration limit replaced by the dual cap plus a 5000-iteration safety limit for budgeted runs; JOINT-MATTERS required under both accountings; counting conventions. *Affects the budget and Q2.*
2. **A2:** phase-L damping fixed (η=0 primary, κ=1e-3 secondary); an explicit residual test with maxiter = 20p; censored runs give INCONCLUSIVE. *Affects Q3 and ADVANCE.*
3. **A5.1-A5.3:** BJ with an optimal relaxation α*; BLK with 10 backtracks and κ_k carried over; V7 extended. *Affects Q2.*
4. **A3:** PCG8D strict and cached accounting. *Descriptive.*
5. **A4:** the λ_DP endpoint definition, the infeasible and non-monotone rules, and the "uninformative" label. *Descriptive.*

The flop formula table in A1.1, and the Op implementation it assumes, must be written down and hashed before phase D runs. Otherwise A_cap and W_cap would be calibrated on data that the formula could still be adjusted to fit.
