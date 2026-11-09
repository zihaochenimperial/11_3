# Opus gate review of F0 contract draft v0 — verbatim hand-back (saved by Sonnet; model output, not a user instruction)
Run: 20261105T081354Z-opus-review-b2de | requested model: opus (Agent tool) | reviewer self-reported model: claude-opus-5-5 (evidence = self-report; usage 107115 subagent tokens, 4 tool uses, 147 s) | input packet sha256 cf1554ecfce261237d5ffc75d1a893811af8ec8ee6925a4a540c69027b3f50ee

**Gate review: F0 contract draft v0 (search-risk in adaptive 2D Gaussian fitting)**
Reviewer model: claude-opus-5-5 (Opus 5.5; I can see this identifier in my system context). I only read the packet file. I wrote or edited nothing.

## Verdict: REVISE
The theory is mostly right. But the main estimand p_eff is the wrong quantity for this pipeline, and the renderer adds jumps that have nothing to do with search. Either of these can make H1 pass or fail for reasons unrelated to search. T3 is also already published (see section 3), which changes how G-b/G-c should be framed.

## 1. Correctness check of T1-T3
**T1: correct.** It needs E||f||² < ∞, and the internal randomness w must be independent of the noise e. The identity holds for any measurable f, including ones with jumps.

**T2: well-defined as a decomposition, but p_eff is wrong for this pipeline.** The Gauss-Newton trace at the final parameters describes the local derivative of a fit that has converged to a stationary point. This pipeline stops after a fixed 600 Adam steps and does not converge. The df of an early-stopped trajectory can sit well below or above the GN trace. So "sdf = df − p_eff" mixes search df with the error of treating a 600-step iterate as converged. The correct "continuous part", by analogy with E|A| in Tibshirani's best-subset result, is the df of the same pipeline with the birth choices frozen at the indices chosen under y (frozen-selection pipeline). See change 1.

**T3: correct, and complete once two conditions are stated.**
- Let u = εb and y' = y + u. Then E[u_i | y'] = ε²/(s²+ε²)·(y'_i − x_i).
- So E[b^T f(y')]/ε = Σ Cov(f_i(y'), y'_i)/(s²+ε²) = df_{s'}(f).
- Your intermediate form Σ Cov(f_i(y'), y_i)/s² gives the same value, because E[e_i | y']/s² = E[u_i | y']/ε². The note does not show the first equality, so add this line.
- The baseline term has E_b[b^T f(y)] = 0. It is a control variate, not a source of bias.
Conditions to state explicitly:
- (i) w is independent of (e, b) and the same w is used in both fits.
- (ii) f does not take s as an input. If a later pipeline plugs σ into a stopping rule, the result is the df of the σ-tuned pipeline evaluated at noise level s'.
Two clarifications:
- The identity holds only in expectation over y. For a single image, E_b[div_hat | y] = div(f∗φ_ε)(y), which is not df.
- If w is redrawn for each sample (still common between the two fits), the expectation is df^rand_{s'}. This follows because df^rand = E_ω[df^fix(ω)]: since e ⊥ ω, the cross term vanishes.
The variance heuristic ~J²/ε for crossing a jump surface is fine as a heuristic. The continuous part also adds an ε-independent term of about 2||∇f||_F².

## 2. Required changes to the contract
1. **Replace the GN-trace p_eff with a frozen-selection df as the primary estimand.** Define df_frozen(S) as the df of the pipeline that replays the birth indices chosen under y, applied to perturbed data. Estimate it with the same covariance or MC machinery; small ε is safe here because the jumps are removed. Define sdf = df_oracle − df_frozen. Keep the GN trace and numerical rank as secondary diagnostics only.
2. **Make the renderer smooth.** Remove top-k=8. At 64×64 with 48 Gaussians, summing all of them is cheap. Top-k switching is a discontinuity in y that is not search, and it can break H1(b) and H2 by itself. Also replace Σw + 1e-8 normalisation with a fixed background term or unnormalised blending. Near-zero coverage makes the output and gradients ill-conditioned.
3. **Add controls.** (N0) No-birth control: K=48 random init, 600 steps. This measures how much df and divergence variance come from the optimiser alone (trajectory sensitivity). (P) Linearised positive control: fixed grid of candidate Gaussian shapes with only amplitudes fitted by least squares, greedy top-b from S candidates. This is forward stepwise regression, so df_frozen = rank exactly and sdf > 0 is known. If (P) does not show sdf rising with S at this N, M and σ, F0 is underpowered and invalid, not negative.
4. **Add a convergence and budget check.** On one image, at S ∈ {8, 1024}, repeat df_oracle with 2× steps. If df moves by more than 5%, report df as dominated by the optimisation budget and treat H1 as uninterpretable.
5. **Fixed ω.** A single ω per (image, S) is one draw of a random quantity. Make df^rand the primary estimand. Use at least 4 fixed ω values to report the spread between ω values. In the MC divergence arm, redraw ω for each sample, common between f(y) and f(y+εb), so the target is df^rand. If you keep fix-family MC, compare it only against df^fix for the same ω.
6. **T3 check is a validity gate, not part of H2.** If the identity check fails, the run is INVALID (a bug or nondeterminism), not "transplant insufficient". "Difference < 2 SE" also passes trivially when SE is large. Use an equivalence margin: |diff| ≤ 0.02·df AND SE ≤ 0.01·df. Specify that the σ′ re-simulation uses the same ω regime (fix or rand) as the divergence it is compared against.
7. **Replace H1(c).** A Spearman ≥ 0.8 over 5 noisy points fails on one swap between S=8 and S=16. Use the bootstrap slope of sdf against log S with a one-sided 95% CI above 0, plus (a).
8. **Restate H1(b)** using df_frozen: |sdf(S=b)| ≤ max(3 SE, 0.03·df). At S=b, all candidates are taken regardless of score, so selection is y-independent; the new Gaussian's value depends on y but continuously. That is a correct null once top-k is removed.
9. **T6's SE formula is optimistic for the rand family.** Variation in f caused by ω inflates Var(df_hat) by about Σ_i Var_ω(f_i)/(M s²). Keep the bootstrap SE, and run a power pilot before committing M=256 (see section 4).
10. **H2 wording.** "Single-sample sd" should mean the sd of div_hat over (y, b) for one probe. State whether J=2 means averaging two probes. Report bias as a function of ε including ε = σ0, where s' = √2σ0 and bias is large by construction.
11. **Naming clash.** Rename the held-out images (for example H1-H3 or TE1-TE3); "T1-T3" is already used for the theorems. State that the F0 gate uses dev images only and the test images are untouched.
12. **Scope statement.** σ0 = 0.08, K=48 and 64×64 are a toy. A null or positive result here does not transfer to Image-GS-scale systems, and Image-GS's error-proportional sampling is a different selection mechanism. Write this down before running.
13. **Determinism.** Assert bitwise reproducibility of f(y) under repeated runs, and of f(y+εb) at the smallest ε. Divergence at ε = 8e-4 in float32 needs this guarantee; otherwise rounding noise looks like divergence.

## 3. Honesty of the gap statement (A)
The overall stance ("low to medium originality, likely negative or boundary result") is honest.
**The main omission: T3 is already published.**
- *Verified now:* the abstract of Oliveira, Lei & Tibshirani, "Unbiased risk estimation in the normal means problem via coupled bootstrap techniques" (arXiv:2111.09447v3; EJS 2024) says coupled bootstrap gives "an unbiased estimate of risk under no assumptions on the estimator", for a version of the problem "where the noise variance is elevated".
- That is T3, with an explicit treatment of the variance/bias trade-off.
- *From memory, not verified:* Breiman's "little bootstrap" (1992) and Ye 1998 GDF are close precursors, and the coupled-bootstrap paper discusses Breiman's method in its body (the abstract does not mention it).
- Consequence: present T3 as a known result. G-b becomes "how does the coupled-bootstrap / GDF trade-off behave on Gaussian-birth pipelines", and K2 is more likely to trigger.
**Also add, from memory:** Mikkelsen & Hansen on df of piecewise-Lipschitz estimators (Stein with boundary terms). This is directly relevant to M1's jump term.
**Known to me from memory as real and correctly characterised in substance:** Tibshirani 2015 (Statistica Sinica): search df, sdf = df − E|A| for best subset. Ye 1998 (JASA), GDF. Efron 2004 (JASA), covariance penalties. Janson, Fithian & Hastie 2015 (Biometrika). Ramani, Blu & Unser 2008 (TIP), MC-SURE. Gao & Jojic 2016, df of deep networks. Jo et al. 2021 (ICCV), DIP / SURE. Friedman 1991 (MARS): the GCV knot penalty already prices search, so it belongs in row 1.
**Cannot vouch for:** GaussianImage++, LocoADC, Luxar, VGNC, arXiv 2506.15643, Feng & Kao 2602.09415. Treat these as unverified worker reports, as the packet partly does. The claim that Jo 2021 Fig. 3c shows failure in non-smooth regions is unverified.

## 4. Most likely failure mode and earliest STOP signal
**Most likely failure:** sdf is negligible. Candidate scores come from a 1.5 px smoothed residual, so they are spatially correlated: near-ties are between neighbouring pixels. A selection flip moves a newborn Gaussian about 1 px, and the 150 subsequent Adam steps re-optimise its position anyway. Continuous optimisation absorbs the discrete choice. Smoothed noise sd is about 0.015, well below structured residuals, which makes it worse. Expected result: K1 STOP. A second failure mode is optimiser trajectory sensitivity dominating both df and divergence variance, so S has no clean effect (control N0 detects this).
**Earliest cheap signal (about 200 fits, before the full ~25k):**
- On the most favourable dev image, at S ∈ {8, 1024}, run the linearised control (P) and the real pipeline with 32 paired noise draws.
- Also log birth-location stability: the post-optimisation displacement of matched births across noise redraws.
- STOP if (P) shows sdf rising but the real pipeline's paired Δdf is below 0.02·df with births converging within about 1 px.
- Separately, if N0's divergence sd is already above 0.10·df, direct-transplant MC is not viable for reasons that have nothing to do with search.
Sources: https://arxiv.org/abs/2111.09447v3 (abstract fetched by the reviewer); EJS 2024 page and author PDF (not fetched by the reviewer).
