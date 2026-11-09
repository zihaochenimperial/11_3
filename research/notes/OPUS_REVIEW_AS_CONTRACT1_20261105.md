# OPUS 门审查原文: AS 合同候选 v1 (run 20261105T233836Z-opus-review-b1b8)

> 来源: Agent(model=opus) 子代理最终报告, 逐字保存 (由 Sonnet 主会话从任务输出文件程序化提取, 未改写)。子代理自报: "The system prompt says I am Claude Opus 5.5 (model ID claude-opus-5-5) ... cannot verify independently."; 任务输出日志 message.model 字段 = claude-opus-5-5 (日志字段, 仍非独立证实)。
> 审查对象: contracts/AS_CONTRACT_CANDIDATE_v1.md sha256 f9708aa35d03fdfafccbf1a25b0b8ba42e64e2e65ba2513f9df13020e244e05f。
> 子代理声明其文献碰撞 (Ho-Nguyen 2016, Chen-Cowan-Grant 1991, NOMP, Tractor 等) 来自背景知识 (L1), 须读原文后方可依赖。

---

**Model self-report:** The system prompt says I am Claude Opus 5.5 (model ID `claude-opus-5-5`). I am highly confident that is what the prompt says, but I cannot verify it independently.

**Scope:** run_id 20261105T233836Z-opus-review-b1b8. I read all the listed files in full, including the whole G0 reading log. I ran one scratch numpy check myself: `/tmp/claude-0/-home-claude/c30445bf-b91f-5725-a565-964b312260f4/scratchpad/chk.py`, which uses the same 1-D toy, seed and fit as your check script. I did not modify any uploaded file. I did not re-read any paper. The literature collisions I name in section 3 come from my own background knowledge (L1) and must be read in the original before anyone relies on them.

---

## 1. Verdict: REVISE-AND-RESUBMIT

This should be a short v2 followed by a light re-review, not a new direction.

**Is Q1 worth asking?** Yes, but as a cheap kill test, not as a route to a contribution.
- The prior that a publishable method comes out of this is low. Section 3 lists strong uncited neighbours, including a direct theoretical collision with claim (c).
- Q1 is cheap: a few CPU-hours if A is applied separably.
- A clean "no headroom" answer would close the line honestly.

**Is v1 scientifically decisive for Q1?** No, for six reasons.
1. **Split scores do not match the edit that is applied.** JOINT and OMP-raw score every candidate with a free coefficient, but a split is applied at c=1. For splits, the free-coefficient JOINT score is almost independent of d and measures a 4th-derivative "atom". In my check the best coefficient c* was 0.49 at d=0.7s with the contract's split, 2 at 0.5s and 668 at 0.125s. With the same-width split it was −0.9 to −5e4, a sign no split can produce. So the scores rank edits that cannot be carried out (§2d).
2. **The "complete joint reference" the human authorised is not what Q1 tests.** The handoff (step 3) and synthesis §3 define it as inserting the candidate and then doing a real joint refit. In v1 that is ORACLE_y, which is only an auxiliary arm and only searches a shortlist chosen by the very rules being compared. Q1 instead tests a linearised OLS score.
3. **The JOINT vs OMP-raw contrast is mostly "births vs splits".** Near a stationary point, OMP-raw's numerator only sees the part of Aq outside the current model's range, while its denominator includes all of it. In my toy, OMP-raw split scores were 400–10⁵ times smaller than JOINT's, so OMP-raw will almost never pick a split. Any "headroom" could be a split-prior effect that a trivial rule would also capture.
4. **The negative control N cannot be interpreted as written** (§4f).
5. **The gate is likely underpowered** (§4a, §4d).
6. **The handoff's mechanism stage was skipped.** Step 4 (2–3 overlapping Gaussians, decision-agreement check) is cheaper than the 12-image benchmark and was meant to come first.

---

## 2. Algebra check (synthesis §2)

**(a) Δ_comp and Δ_unc: correct, under conditions that need stating.**
- Δ_unc = ½‖r‖² − ½‖r−Aq‖² = r·Aq − ½‖Aq‖².
- With a linearised refit δθ: min over δθ of ½‖r−Aq−AJδθ‖² = ½‖P⊥(r−Aq)‖². Using P⊥r = r, Δ_comp = r·Aq − ½‖P⊥Aq‖², and the difference is ½‖PAq‖².

Caveats:
- This is a Gauss–Newton (linearised) refit, not the true nonlinear refit.
- The stationarity used here ignores the 1e-6·Σa² term and the clamps on log ℓ.
- After only T_r=15 LM steps the fit is generally not stationary. The correct general form is then Δ_comp = ½‖Pr‖² + r·P⊥Aq − ½‖P⊥Aq‖². The constant ½‖Pr‖² does not affect ranking, but r·Aq ≠ r·P⊥Aq.
- OMP-raw's numerator r·Aq therefore rewards candidates that line up with the unconverged part of the residual. This should be logged: record ‖(AJ)ᵀr‖/(‖AJ‖‖r‖) before each scoring.

**(b) OLS gain: correct.** Maximising c·r·P⊥a − ½c²‖P⊥a‖² over c gives ⟨r,P⊥a⟩²/(2‖P⊥a‖²), with a = Aq̂ in observation space. This is the Soussen eq. 2 quantity (C45).

Consequence: at a stationary point the JOINT and OMP-raw numerators are identical. The two rules differ only through the factor ‖Aq̂‖²/‖P⊥Aq̂‖². That makes JOINT numerically fragile. When ‖P⊥a‖ is near zero, the direction of P⊥a is dominated by rounding error (rcond=1e-10), and the score becomes ⟨r, near-random unit vector⟩². A frozen floor such as ‖P⊥Aq‖/‖Aq‖ ≥ 1e-3, plus a test that scores are stable when rcond varies, is mandatory.

**(c) Symmetric split, q₂ ∈ range(J): correct, with one correction and one serious collision.**
- *Correction.* The heat identity ∂G/∂Σ = ½∇²G holds for normalised Gaussians. Your parametrisation uses peak amplitude, so q₂ lies in span{covariance columns, amplitude column}. In 1-D, ∂²_m g = (1/s)∂_s g − (a/s²)∂_a g. The claim fails for a parent sitting at a log ℓ clamp, where its covariance column is not a feasible direction.
- *Verified numerically.* At the toy's stationary point, the SteepGS-type position split matrix S = Σ_p (∂ℓ/∂x_p)·∂²_m G was 1.6e-14, against a scale reference of 2e-4. So for an additive Gaussian at a stationary point with free covariance and amplitude, λ_min(S)=0 exactly and the SteepGS test is vacuous. That is a sharp and possibly useful remark.
- *Collision.* This is the weak-identifiability phenomenon of location-scale Gaussian mixtures. The PDE ∂²f/∂μ² = 2∂f/∂σ² is the core of Ho & Nguyen (Ann. Statist. 2016), with Chen (1995) on over-fitted mixtures and Heinrich & Kahn (2018). Do not present it as your observation.
- *Order of terms.* The "same order" claim is right: r·Aq = r·Aq₄ = O(d⁴), ½‖Aq‖² ≈ ½‖Aq₂‖² = O(d⁴), and ½‖P⊥Aq‖² = O(d⁸).

**(d) The contract's moment-preserving split. Two problems.**
- *It does not preserve mass.* Children have amplitude a/2 and covariance Σ−d²eeᵀ, but amplitude here is peak height. Total mass scales by √(1−α²) = √0.51 ≈ 0.714 (I measured 0.714). So q is O(1), dominated by a −29% amplitude change, and q₂ ≠ 0. For a normalised (mass-preserving) moment split, q₂ = 0 exactly and q = −(d⁴/12)∂⁴_e N + O(d⁶), from the fourth cumulant −2d⁴.
- *It does not matter for JOINT.* The unnormalised and normalised increments differ by a multiple of the parent, which lies in range(J), so the JOINT scores were identical in my run (1.783e-4 for both). It matters a lot for OMP-raw and for the edit actually applied.
- *There is no small parameter.* At α=0.7 the d-expansion is not asymptotic; ‖PAq‖/‖Aq‖ ≈ 0.90 here. The O(d⁴) picture is not what the contract tests.

**What is misleading in the toy check:**
1. Its model is well specified (K = true 4) and converged, so r is pure noise and every gain is noise-level. The contract's setting is mis-specified and not converged.
2. It uses a same-width split with c=1. The contract uses the moment split with a free coefficient, so the toy does not exercise the contract's score.
3. "Δ_comp ≈ 0 at d=4" is a linearised quantity and says nothing about the realised refit.
4. Consequently V9 as written either fails (on the contract's split, q₂ ≠ 0) or tests an object the experiment never uses.

---

## 3. Novelty and collisions

**(i) Finite-split / higher-order treatment: largely occupied.**
- Weak identifiability: Ho–Nguyen 2016 and related work.
- Moment-preserving split/merge is classical: Richardson & Green (1997) RJMCMC; Ueda et al. SMEM (2000); Gaussian-mixture filter splitting (Huber et al. 2008; DeMars, Bishop & Jah 2013; Faubel et al. 2009); mixture reduction (Salmond 1990; Runnalls 2007).
- In GS: Rota Bulò et al., "Revising Densification" (2404.06109, already in your C29 hit list, unread), and Kheradmand et al., "3DGS as MCMC" (2024).
- What remains is little more than the remark that "the SteepGS criterion degenerates at a stationary point for additive Gaussians".

**(ii) Low-cost local joint projection maintained across split/merge under blur: thin.**
- RBF networks with OLS selection of Gaussian centres: Chen, Cowan & Grant (IEEE TNN 1991) is close to a direct collision. Also resource-allocating and growing/pruning RBF networks (Platt 1991; Huang et al. 2004/05) and kernel matching pursuit with back-fitting (Vincent & Bengio 2002).
- Continuous-parameter greedy fitting with joint refinement: Newtonized OMP (Mamandipoor, Ramasamy & Madhow 2016), Continuous Basis Pursuit (Ekanadham et al. 2011), ADCG local steps.
- Astronomy deconvolution with a known PSF, greedy component birth and joint refit of overlapping groups: CLEAN and multiscale CLEAN (Högbom 1974; Cornwell 2008), DAOPHOT/ALLSTAR (Stetson 1987), and The Tractor with mixture-of-Gaussians galaxy profiles convolved analytically with the PSF (Hogg & Lang 2013).
- High-density localisation microscopy: DAOSTORM (Holden 2011) and similar.
- Incremental factorisation and Schur maintenance as variables are added: iSAM2 (Kaess 2012), bundle-adjustment Schur (Triggs 2000), fast recursive OLS and OOMP (Rebollo-Neira & Lowe 2002).
- In GS itself: 3DGS² local Newton systems (C50).

A defensible contribution here would at most be engineering plus an empirical result, unless something specific to blur-widened coupling survives these.

**(iii) Equal-time empirical results:** Always possible in principle. At 32×32 on synthetic images they carry no publishable weight without strong pixel-domain and INR baselines.

**Rows that must be raised to a raw read (L4) before any claim:**
- C47 Unified Loss-Aware DC: does it include cross terms or a joint treatment? It is the closest recent split neighbour.
- C42 SteepGS: Appendix C proof and §5. Verify the "no cross terms" claim and whether 3DGS alpha compositing breaks the heat identity.
- C48 Dehaze-GaussianImage, and C46 GaussianSR / GSASR / 2509.01964 (currently L2): their densification criteria.
- C50 3DGS²: the local system construction.
- C44 ADCG §5 and the local-step details.
- Plus first reads of Ho–Nguyen 2016, Chen–Cowan–Grant 1991, NOMP, Rota Bulò 2404.06109, and The Tractor / Hogg–Lang.

---

## 4. Contract design critique

**(a) Is Q1 well posed, and does the benchmark have power?**
- Not well posed as written, for the score/edit mismatch in §1.
- Power is doubtful. Thirty greedy steps, each followed by a 15-step LM refit of everything, give a path-dependent result; per-image log-MSE differences between greedy rules are plausibly 5–15%. With 12 image clusters, a 2% lower bound needs a per-image standard deviation of roughly ≤5% for a true 5% effect.
- Edits are likely to diverge rather than coincide, but mainly by type (birth vs split), as explained in §1.
- BLOCK will probably be close to JOINT for splits, because the parent's own columns hold most of PAq (‖PAq‖/‖Aq‖ ≈ 0.9). BLOCK equals OMP-raw for births. So the contrasts split as JOINT−BLOCK ≈ neighbour compensation (births and overlapping splits) and BLOCK−OMP ≈ own-parent compensation (splits).
- Required: log the type mix, add birth-only and split-only variants of each rule, and log the top-1 agreement and rank correlation of scores per step.

**(b) Confounds.**
- *FIXED-K:* one initialisation is a weak comparator. It is also folded into G1 as a conjunction, which mixes two questions.
- *Refit budget:* specify whether λ resets after each edit, and the cap on rejected steps.
- *ORACLE_y:* the shortlist restriction defeats its purpose. A full candidate set (about 84) is affordable if A is applied separably as B·X·Bᵀ (exact, about 100× cheaper than a dense 1024² matrix). T_o=5 vs T_r=15 is a further mismatch. Because it selects on training loss, it will fit noise at σ_n=0.03; that is acceptable only if this is stated as a property of the rule.
- *cheap*:* choosing it by clean MSE is conservative, but the choice must be redone inside every bootstrap replicate. Better: an intersection–union test requiring JOINT to beat both cheap rules. That needs no data-dependent choice and no multiplicity correction.
- *Bootstrap:* a percentile cluster bootstrap with 12 clusters under-covers. Use a sign-flip permutation test on image-level means, or t/BCa intervals.
- *Noise seeds:* 2 seeds is fine if they are averaged within each image.
- *Stopping:* fixing K_max=36 without stopping penalises whichever rule fits faster when σ_n=0.03. Training-loss-greedy rules (JOINT, ORACLE_y) may lose on clean MSE because of overfitting, not worse selection.

**(c) Leakage and data boundary.**
- ORACLE_x needs clean images inside selection code, which contradicts V6. Run it as a separate evaluator-side process that writes only diagnostic outputs, and state an explicit exemption in the contract.
- S1 pilot images are a subset of the dev set. That is acceptable only if absolutely nothing except timing is read from them.
- Design choices (K0=6, σ=6, so the initial grid overlaps heavily; α=0.7; birth σ=1.5) were made by someone who already expects JOINT to win. This is a tailoring risk rather than leakage (see h).

**(d) Thresholds.** The five-way conjunction (5%, lower bound >2%, 3 of 4 conditions, 70% sign agreement, FIXED-K) is arbitrary and low-powered; it will mostly produce STOP through noise. Replace with these, all frozen before running:
- **Gate 0 (selection matters at all):** H_Ox = geometric-mean MSE reduction of ORACLE_x vs the better cheap rule ≥ 10%. Otherwise STOP: the bottleneck is not selection.
- **Gate 1 (primary):** pooled over C1–C4, the image-level mean of log(MSE_JOINT/MSE_rule), tested against OMP-raw and BLOCK separately (intersection–union):
  - point estimate ≤ log(0.95), i.e. at least a 5% (≈0.22 dB) reduction;
  - one-sided 95% sign-flip upper bound < 0;
  - no single condition with a point estimate worse than +2% (no harm);
  - effect present in at least 2 of 3 image families.
- Run the same test with ORACLE_y-full as the reference (headroom of the complete reference) and with JOINT vs ORACLE_y (does the linearisation capture it).
- **Gate F (separate):** if FIXED-K (best of 3 pre-set initialisations, same LM budget) has an MSE no more than 2% above JOINT's, STOP the growth line, whatever Gate 1 says.
- Drop the 70% sign agreement as a gate and report it instead.
- Raise the image count to 24–36 (8–12 per family). Images are the clusters and they are cheap.

**(e) Validity gates.**

Add:
- a floor on ‖P⊥Aq‖/‖Aq‖ and a test that rankings are stable for rcond ∈ {1e-8, 1e-12};
- a check that applying A separably matches the dense A, and an adjoint test that the code for Aᵀ really is the transpose (reflective-boundary B is not symmetric);
- a stationarity log before each scoring;
- clamp handling for parents at the log ℓ limits;
- a cap on LM rejected steps;
- logged per-candidate correlation between linearised predicted gain and realised refit gain (a diagnostic, not a gate).

Drop or redefine:
- V9 (wrong object; see §2);
- V7 (true by construction).

**(f) The negative control N is not informative as specified.** P⊥ effects arise from Gaussians overlapping in the image itself even when A = I. With 36 Gaussians on 32×32 they overlap heavily, so a large H_J under N would not mean "the refit fits noise". The INCONCLUSIVE rule is therefore wrong. Replace it with a pre-registered dose-response check: H_J(σ_b=0.3) ≤ H_J(1.0) ≤ H_J(2.0), reported, with failure noted. If a clean null is wanted, add a well-separated-Gaussian synthetic case.

**(g) FIXED-K and discrepancy stopping.**
- Keep FIXED-K, but as the separate Gate F with 3 initialisations.
- Add discrepancy-principle stopping (first K where ‖y−Ax‖² ≤ τNσ², τ frozen, for example 1.0) as a secondary readout from the trajectories already logged, at no extra compute.
- Add a Tikhonov/Wiener deconvolution with GCV-chosen λ as a context number; it takes seconds.
- Defer everything else (AS-4).

**(h) Tailoring risk.** Mitigations, all frozen now:
- add a pre-registered neutral-initialisation arm (K0 grid with σ=3);
- report results per image family;
- state in advance that only the pre-registered configuration counts;
- ideally, have a blind worker (GLM) generate images from a spec without seeing any rule output.

---

## 5. What would make this a dead end (kill criteria not yet written down)

- **K-a (tiny numeric, before any freeze, uses no images):** on 2–3 overlapping Gaussians under blur, measure top-1 agreement and rank correlation of JOINT vs BLOCK vs OMP-raw over a sweep of overlap and σ_b. If decisions agree in ≥90% of cases where the scores are realisable, there is no headroom. This is the handoff's step 4.
- **K-b:** Gate 0. If even the cheating ORACLE_x gives less than 10% over the cheap rules, selection is not the bottleneck.
- **K-c:** a Tikhonov/Wiener deconvolution with GCV beats FIXED-K and all growth rules by more than about 1 dB at this scale. Then Gaussian capacity control has no task value here. Seconds to run.
- **K-d:** Spearman correlation between linearised gain and realised refit gain below 0.3. Then local approximations of JOINT are pointless.
- **K-e:** after the realisability fix, JOINT's advantage disappears once a "births vs splits" prior is given to OMP-raw.

None of these has been run, so none yet suggests STOP. The Ho–Nguyen and RBF-OLS / NOMP / Tractor collisions do lower the expected value of continuing.

---

## 6. Mandatory changes

1. **Split scores must be realisable.** Score each split by the c=1 linearised Δ_comp = r·P⊥Aq − ½‖P⊥Aq‖², or optimise over d within the split family. Births keep a free amplitude. Use a mass-preserving split: child amplitudes (a/2)·√(detΣ/detΣ′).
2. **Make ORACLE_y over the full candidate set the primary "complete joint reference",** with JOINT as the linearised proxy. Apply A separably (exact) to keep this within budget.
3. **Add birth-only and split-only variants,** and log type mix, top-1 agreement and rank correlation.
4. **Replace §4 with the gates in §4d** (Gate 0, intersection–union Gate 1, separate Gate F, sign-flip inference, harm and family conditions, 24–36 images).
5. **Replace the N rule with the dose-response test** (§4f).
6. **Validity gates:** add the P⊥ floor, rcond-stability, separable-vs-dense, adjoint and LM-cap tests; drop V9 and V7. Give ORACLE_x an explicit evaluator-side exemption.
7. **Secondary readouts:** discrepancy-principle stopping K, the Tikhonov/GCV context number, FIXED-K with 3 initialisations, and the neutral-initialisation arm.
8. **Before freezing:** run K-a as a contract-free unit-scale self-check and fix the specification if it shows problems. Cite Ho–Nguyen 2016 and Chen–Cowan–Grant 1991 as leads to read (at L1 until read), and correct synthesis §2 (amplitude column, clamp edge case, non-stationary form of the formula).

---

## 7. Summary for the human (≤120 words)

The proposed small test asks whether a smarter, "joint" rule for adding Gaussians during deblurring beats cheaper rules. Nothing has been validated; only paper algebra and a 1-D toy exist. The core algebra is correct, but the key "split" observation matches a known result on Gaussian mixtures (Ho & Nguyen 2016). Several close older methods (OLS selection of radial basis functions, astronomy deconvolution codes) were not yet considered. The current contract has a design flaw: it scores splits that cannot actually be carried out. Its pass rules are arbitrary and probably too weak to detect a real effect. Fix and re-review it (about a day), then run it as a cheap stop/go test. Chances of a publishable method from this line look low.

---

**For the main session, not saved to memory:** the Ho–Nguyen weak-identifiability collision and the missing RBF-OLS / NOMP / Tractor neighbours come from my background knowledge, not from the project files. They are leads to read, not facts.
