# Opus review (round 9): failure causal audit + re-idea candidates A/C
- Run: 20261105T220104Z-opus-review-f8b0 (Agent model=opus; self-reported model ID: claude-opus-5-5). Hand-back received 2026-11-05 ~22:1xZ. Saved VERBATIM below (the harness-indentation removed; content unchanged). Sonnet annotations are in a separate section after the verbatim block.
- Model boundary: the reviewer worked read-only on staged copies; it reports L3 (WebFetch extraction of ar5iv HTML) for the primary papers and L1 (memory) for the rest; it did not reach L4 for any source.

----- BEGIN VERBATIM OPUS REPORT -----
I am Claude Opus 5.5 (self-reported model ID: claude-opus-5-5). Run 20261105T220104Z-opus-review-f8b0. I worked read-only on the staged files and wrote nothing to disk.

**Reading levels for this review.**
- **L3 (WebFetch extraction from the ar5iv HTML):**
  - Tibshirani 1402.1920: §2.1, §3 eq.(15)/(16), Lemma 5, eq.(22), end of §5.2, §5.3 eq.(23).
  - Oliveira–Lei–Tibshirani 2111.09447: eqs.(18)–(20), Prop.1, Cor.1, Thm 2 in §3, §5.3.
  - Leiner–Duan–Wasserman–Ramdas 2112.11079: authors, §2.2, §2.3, end of §6.1.
  - Azaïs–De Castro–Mourareau 1706.00679: abstract and summary.
  - Butucea–Delmas–Dutfoy–Hardy 2207.00171: abstract and summary.
  - Lazzaretti et al. 2404.00810 and Bénard–Traonmilin–Aujol (EUSIPCO 2022): abstracts.
- **L1 (my memory only):** everything else. This includes ADCG, Keriven et al. compressive GMM (CL-OMPR), Shahram–Milanfar / Smith on resolution limits, and OMP noise-stopping (Cai–Wang).
- I did not reach L4 for any source.

---

## Q1. Failure attribution

**(a) F0/H2 as "predictable from literature/formulae + design-level decision invariance": I agree, with corrections.**

These parts of the paraphrase check out at L3:
- Tibshirani eq.(15): sdf = df(f̃) − E rank(X_A).
- Lemma 5 and eq.(22): divergence term plus a discontinuity term, under Gaussian noise and the regularity condition (21).
- eq.(23): a sufficient (not necessary) condition for positivity.
- Oliveira Cor.1: CB_α is unbiased for Risk_α for any g, with the Gaussian assumption needed for independence.
- Oliveira Thm 2 in §3: the SURE limit as α→0.
- Oliveira §5.3: image denoising with a 2D fused lasso on the parrot image, where the CB minimiser is close to the SURE minimiser.

Errors and overstatements:
1. **Wrong citation site and scope.** The sentence "the second term exactly coincides with the search degrees of freedom" is at the **end of §5.2, not §5.3**. It is stated **only for subset selection and the relaxed lasso**, which are locally linear projection maps. Audit §0 presents it as a general statement.
2. **"就是同一个分解" (§0) is too strong.** F0's split is df_full = df(G frozen-structure leg) + sdf. That is neither Tibshirani's divergence + jump split nor df − E|A|. For a smooth nonlinear renderer, the divergence of F is not the df of an independently-structured leg. "Same concept family" is defensible; "identical decomposition" is not.
3. **§2.2 小结 also overstates.** "df_full estimator 就是 … Oliveira 的 CB 构造" should read "uses the same coupled-noise construction". CB targets Risk_α at inflated noise, not a covariance df.
4. **Wrong author list.** Audit §1 and §2.2 name "Leiner–Ramdas–Wasserman–Fithian". The authors are Leiner, **Duan**, Wasserman, Ramdas. The receipts file has this right. An L4-tagged citation with the wrong authors undermines the L4 label.

The decision-invariance argument (R̂ depends only on df_full) is the real reason for the STOP. It stands on algebra alone.

**(b) CF0 as a conditional empirical negative: I agree.**
- The information-allocation identity is verified (§2.3: I_X = I_f + E[I_{g|f}]).
- It is indeed an accounting identity and cannot imply "must fail". The algebra 1/(1+τ²) + τ²/(1+τ²) = 1 is correct.
- "Fixed K=48 biases toward no gain" is a fair scope limit. It is not evidence against the STOP.

Table check:
- I could not open analysis.json, so I cross-checked the per-type NU values against the absolute-risk table in the CF0 record §4. They agree to within image-weighting differences:
  - NS(4), D1: 2.338 vs 2.508, which gives +6.8% ✓
  - RAWcv, D1: about +55% ✓
  - RAWens2, D3: about +14.6% ✓
  - NS(1), D3: −2.5% by ratio of means, against the audit's −3.2%. This is plausible under equal image weights.
- The NS per-type values are otherwise unverified.

Two issues with the table and its framing:
- **The tested arms are missing.** The table omits XFERg(τ) and XAVG, the arms the contract actually tested (−71%, −20%, −10.7%, +1.1%). Add them so the table cannot be read as a story about NS and the K axis alone.
- **Some "theoretically expected" claims are hindsight** (§3.1/§3.3). The XFERg loss was predicted (round 6). NS ≈ 0 was not derived from any theory beforehand. Label it "consistent with", not "expected".

**(c) "No implementation or theory error that overturns the STOPs": I partly agree; the claim is premature on "wrong question" grounds.**

The no-bug claim is fine. The audit misses four framing risks:
1. **The mainline itself may be exhausted, not just the two routes.** With known σ and Gaussian noise, whole-pipeline risk estimation is already solved for decision purposes: CB, SURE and Cp with search-aware df. Both failures say "the decision only needs total risk, and that is available". The audit should state plainly that "search-risk *estimation*" has no remaining gap in this regime. It should not imply only that "the axis is crowded".
2. **"K is the lever" was shown only against fixed K and fission-CV.** It was never compared with the trivial known-σ rules: the discrepancy principle ‖r‖² ≈ Nσ², Cp, and best-fixed-R. Round 8 already required these as entry baselines. If those rules capture most of the oracle-R gain, there is little headroom left for any new stopping rule, including candidate A. That is the most important unasked question.
3. **Optimizer non-convergence.** The schedule is 150 Adam steps per stage, 8 births per round. The audit treats Adam only as a source of variance. If fits are not near stationary points, the "positions are washed out" mechanism and every df statement describe the optimizer, not the model.
4. **Generator specification.** If the D1–D3 images are Gaussian sums, the true K is known and the model is well specified. If not, misspecification drives K. The audit does not say which, and candidate A depends on it.

---

## Q2. Candidate A (convex lifting + dual certificate): partly agree that it is the best lead. In its current form the differentiation is weak and the kill criteria are too lax.

**Nearest-work coverage is not honest enough.** Missing prior work:
- **Azaïs–De Castro–Mourareau 1706.00679 (L3).** They give exact Rice and spacing tests for the maxima of the Gaussian process of the residual correlation over a continuous dictionary in BLASSO/super-resolution. They use the first two knots of continuous LARS, and the tests also cover unknown variance. This directly occupies A's "look-elsewhere λ calibration", and B entirely.
- **Butucea et al. 2207.00171 (L3).** Off-the-grid ℓ1 over continuous dictionaries, certificate-based prediction and estimation bounds, κ ≳ σ√log tuning, and a translation-with-varying-scale example. It is univariate θ; the authors say multivariate is "highly technical".
- **Keriven et al. CL-OMPR (L1).** Greedy plus joint refinement over a continuous dictionary of Gaussians with covariance.
- **ADCG (L1).** Already listed, but not read.

**One defensible method difference exists, but it is not the one claimed.** It is the Gaussian semigroup, which is my own derivation (not yet in any receipt):
- For Σ ⪰ Σ₁, g_Σ = g_{Σ₁} * g_{Σ−Σ₁}. So a wide atom is exactly a positive continuous mixture of narrower, shifted atoms.
- **With L1-normalised atoms**, the TV-norm of every positive representation equals ∫x. The scale-augmented BLASSO then has no sparsity preference at all.
- **With L2-normalised atoms**, the penalty scales like Σ a_k/s_k. The normalisation is then an implicit scale prior that determines K_cert.
- Scale-nested atoms also break the minimum-separation and non-degenerate-certificate assumptions (Duval–Peyré type). That theory does not transfer.
- So the claim that A "精确落入 BLASSO 框架" is false in the sense that matters.
- This is either the fatal flaw or the real research question. It is the only angle I see that goes beyond "SFW with anisotropic Gaussians".

**Are the two named risks fatal?**
- **Universal-threshold conservativeness** is not fatal in itself, because it is measurable. Combined with the semigroup point, though, the supremum over θ on pure noise will be dominated by the smallest scales. λ may then sit near the pixel-level universal threshold, so K_cert ≈ 0 for smooth content.
- **Model misspecification** is fatal for the "stopping certificate" claim on natural images. It is not fatal on well-specified synthetic images.

**K1–K3 do not falsify the contribution.**
- **K1 passes by construction.** It calibrates on pure noise and tests on pure noise from the same distribution. The real test is the post-fit null: on well-specified images at the true K, after sliding, the residual is not white.
- **K2/H-A1 set the bar below an existing baseline.** "≥50% of the (oracle − RAWy) gain" is below what RAWcv already achieves (33.2 of 36.0, about 92%). "≤10% worse than RAWcv" allows a loss to pass.
- **K2 omits the required baselines:** Cp with σ known (naive and search-df), the discrepancy principle, and best-fixed-R. It also needs R_MAX ≥ 6.

**Leakage and post-hoc choices to remove:**
- "残差结构化时再按需下调 λ" is a data-dependent knob.
- The filter grid (6 scales × 8 orientations × 3 aspect ratios) and the normalisation must be frozen before any dev image is seen.

**Originality: low-to-medium.** As written it is low (SFW, ADCG, CL-OMPR, Butucea, Azaïs). It is medium only if the semigroup and normalisation problem is resolved with a calibrated, testable stopping rule that beats the trivial known-σ rules.

---

## Q3. Candidate C (projected Fisher): partly agree that it is useful. It is not a standalone line.

- **H-C1 is close to a unit test.** Starting from the truth with high SNR and well-separated atoms, CRB agreement within [0.5, 2] is almost guaranteed by asymptotic efficiency. It mainly checks that the Jacobian is right and Adam converges. To be informative it needs pre-registered stress strata: overlapping atoms, a separation sweep, and low-SNR cells. The prediction should be that the ratio leaves [0.5, 2] in a specific region.
- **The "reparameterisation-invariant" claim is false as stated.** The eigenvalues of J_kᵀ(I−P_{−k})J_k change with the θ parameterisation (Cholesky vs rotation-scale). Thresholds in "half a pixel / half a scale" are parameter units. The invariant object is geometric: the principal angles between atom k's tangent space and the span of its neighbours (or the image-space norm of the projected perturbation).
- **Biggest gap:** there is no evidence that merge/freeze is a bottleneck in this project. The data say the K axis is. H-C2 has no strong baseline: it should face existing pruning-to-the-same-K under a K-axis stopping rule.
- **Link to A:** genuine, and stronger than the brief says. The semigroup near-collinearity (a wide atom vs nearby narrow atoms) is exactly a small principal angle. C works as the identifiability diagnostic inside A, not as a second contribution.

---

## Q4. Recommendation: NARROW (A's core, with C's tool absorbed)

**Narrowed question:** In scale- and anisotropy-augmented 2D Gaussian dictionaries, the Gaussian semigroup makes the BLASSO penalty and certificate depend on atom normalisation. Does some normalisation and noise calibration give a certificate-based birth/stop rule that is (i) calibrated after fitting and (ii) non-inferior to trivial known-σ rules at ≤1.2 fit-equivalents?

| Milestone | Content | Kill criterion |
|---|---|---|
| M0 G0 (paper only) | Read in priority order: SFW 1811.06416 in full; Duval–Peyré (non-degenerate source condition); Azaïs–De Castro–Mourareau 1706.00679; Butucea et al. 2207.00171; ADCG; Keriven et al. CL-OMPR; Image-GS body (densification and stopping); Taylor–Loftus–Tibshirani 1308.3020; OMP noise stopping / discrepancy principle | Kill A as a method if prior work already does noise-calibrated certificate stopping over scale/anisotropy-augmented Gaussian atoms |
| M1 derivation | Write out the semigroup degeneracy; derive the pure-noise sup-|η| law over scale for L1, L2 and peak normalisation | Kill if every normalisation is either degenerate or puts λ at pixel scale (predicted K_cert ≈ 0 on D1–D3-like content) |
| M2 headroom (descriptive) | Only if per-round RSS was logged: zero-fit post-hoc discrepancy/Cp vs RAWcv vs oracle-R on existing dev tables. Descriptive only, not confirmation | If trivial rules reach ≥90% of the oracle gain, drop the stopping claim; keep at most the diagnostic |
| M3 calibration | Well-specified Gaussian-sum images at the true K; post-fit null | False-birth rate > 2α after sliding |
| M4 dev | New images k ≥ 61, new seeds, R_MAX ≥ 6, frozen grid and normalisation | Not non-inferior (2% margin) to the best of {Cp naive and search-df, discrepancy, best-fixed-R, fission-CV τ-matched, RAWcv}, or cost > 1.2 fits |
| M5 | Independent sealed confirmation | Pre-registered |

Keep E41–58 sealed.

---

## Q5. Compliance: level inflation and pre-committed contributions

1. **REIDEA §0/§2/§4 L4 tags without receipts.** GaussianImage, SFW, VGNC "(摘要) L4", Lockhart "(摘要+Thm 1)" and Kac–Rice "(摘要/引言)" are tagged L4. READING_RECEIPTS lists only R1–R3. Abstract-level reading is L2 by the project's own table. Either add receipts or downgrade.
2. **Audit §1/§2.2: wrong authors on an L4 source.** Fix to Leiner, Duan, Wasserman, Ramdas.
3. **Audit §0: "§5.3 作者明确说第二项恰好就是 search df".** Rewrite as: "end of §5.2: for subset selection and the relaxed lasso, the jump term coincides with sdf".
4. **Audit §0/§2.2: "就是同一个分解" and "就是 … CB 构造".** Rewrite as "same concept family / same coupled-noise construction; the decompositions differ".
5. **REIDEA H-A: "计为 1 个方法贡献 + 1 个条件诊断性质".** This pre-counts contributions. Rewrite as: "if confirmed independently, could support …".
6. **REIDEA C: "重参数化不变" stated as a property.** Mark it as unproven and use principal angles.
7. **REIDEA §0: "精确落入 BLASSO 框架".** Add the semigroup caveat.
8. **REIDEA §2: "不是 SFW 本身（各向同性/固定核的点源）".** This rests on partial reading. Mark it partial, and mark the ADCG comparison L1.
9. **Audit §3.2: per-type NS values.** Tag them "Sonnet computation from analysis.json, not independently re-run".

**VERDICT: NARROW.** Narrow to the noise-calibrated certificate under the Gaussian scale semigroup, with C as its identifiability diagnostic. The audit also needs the edits below, but they do not block.

**Required edits**
1. Audit: the four fixes in Q5 items 2–4, plus adding XFERg/XAVG to the §3.2 table.
2. Audit §4: add the four "wrong question" risks (mainline exhausted at known σ; K lever untested against the discrepancy principle, Cp and best-fixed-R; optimizer convergence; generator specification).
3. Relabel the hindsight "expected" claims in §3 as "consistent with".
4. REIDEA: downgrade the unreceipted L4 tags, remove the contribution counting, and remove the invariance claim.
5. REIDEA: add Azaïs–De Castro–Mourareau, Butucea et al., CL-OMPR and the discrepancy principle to the nearest-work table.
6. Replace H-A1, K1 and K2 with the M1–M4 criteria above. Make the trivial known-σ rules mandatory baselines. Freeze the normalisation, filter grid and λ rule (no on-demand lowering) before dev.
7. C's H-C1 needs stress strata with a directional prediction.
----- END VERBATIM OPUS REPORT -----

## Sonnet annotations (not part of the verbatim report)
- A1 (location of the "second term = sdf" sentence): my direct text extraction of the ar5iv page (L4) places "The second term, then, exactly coincides with the search degrees of freedom of these procedures" inside the §5.3 slice (heading "5.3 Potential insights from the multivariate Stein extension", after "the first term ... is simply E|A|"). Opus's L3 extraction put it at the end of §5.2. **Not adopted as a location correction (disagreement recorded; the ar5iv rendering is the common source, a re-check can be done in a browser).** **Adopted: the scope correction** — the statement is made only for best subset selection and the relaxed lasso (locally linear projection maps).
- A2: authors error (Leiner, Duan, Wasserman, Ramdas) — adopted; my receipts file already had it right, the audit text did not.
- A3..: the other required edits are applied in the revised audit/candidate files (see revision notes at the end of each file) and in FAIL-0016.
- Opus's semigroup argument is Opus's own derivation (reviewer says not in any receipt). Sonnet will check the algebra numerically/analytically before relying on it (see research/notes/REIDEA_SEMIGROUP_CHECK_20261105.md if produced).
