# Opus review (round 10): post-M0 decision gate on A′
- Run: 20261105T222118Z-opus-review-8d5e (Agent model=opus; self-reported model ID: claude-opus-5-5). Hand-back received 2026-11-05 ~22:25Z. Saved verbatim between the markers (harness indentation removed). Sonnet annotations are after the block.
- This is reviewer advice, not user authority. The reviewer worked read-only.

----- BEGIN VERBATIM OPUS REPORT -----
**Reviewer:** Claude Opus 5.5, self-reported model ID `claude-opus-5-5`. Run label `20261105T222118Z-opus-review-8d5e`. I worked read-only: I wrote no files, ran no experiments and used no credentials.

**What I read.** The packet; REIDEA_CANDIDATES v2; REIDEA_M1_M2_CHECKS; READING_RECEIPTS R1–R14; my own round-9 review. I re-did the arithmetic in M2 and §C by hand. I did not open the .py/.json files or the full FAILURE_CAUSAL_AUDIT v2, so I make no compliance claim about the audit.

**My own reading levels**
- **Giard–De Castro–Marteau 2509.12889 v1: L3.** WebFetch extraction from arxiv.org/html, first 100k of 274k characters, covering the abstract, §1.1, §2.2 and §7. Versions v2 and v3 exist; I did not read them.
- **Shafie–Sigal–Siegmund–Worsley, "Rotation space random fields" (Ann. Stat. 2003): L2.** Abstract page only. The claim that its filters are full-covariance anisotropic Gaussians is L1 (my memory).
- **Siegmund–Worsley 1995, "Testing for a signal with unknown location and scale": L1.**
- **Bénard–Traonmilin–Aujol 2202.13757: L2.** Listing only.
- **Schiebinger–Robeva–Recht ("superresolution without separation") and Denoyelle et al. (positive measures): L1.**
- **I re-read nothing else.** Poon–Keriven–Peyré, SFW, Azaïs and Butucea rest on Sonnet's receipts; I have not verified them.

---

## Q1. Is the theory gap now only "rotated anisotropy + additive pixel noise"? — Partly agree

**Your §7 paraphrase is mostly right (my L3).**
- The paper uses i.i.d. samples smoothed with a Gaussian kernel τ² Id, with τ ≤ u_min.
- Diagonal covariances satisfy u ∈ [u_min, ∞)^d.
- General covariances with varying or unknown orientation "are not yet handled". Fisher–Rao is hard to use mainly because compatibility with the semi-distance is hard to prove.
- The authors do not know how to solve the problem over the whole measure space.
- The separation cannot shrink to zero.

**Three corrections:**
1. **You left out a sentence that matters.** §7 says the extension to covariances with a **known common orientation is straightforward**. So the open case is per-atom *varying, unknown* orientation, not "anisotropy" in general.
2. **The algorithm remark is slightly off.** §7 points to Hardy (2023), a parametrized non-convex BLASSO over K-sparse measures. It names SFW (Denoyelle et al.) and CPGD (Chizat 2022) as algorithms. What it proposes as future work is adapting CPGD. "SFW/CPGD both left as future work" overstates this a little.
3. **"Additive pixel noise" is a thin gap.** BLASSO with additive Gaussian noise is the standard deconvolution setting (Duval–Peyré, Butucea, Azaïs). Moving a diagonal-covariance analysis from KDE-smoothed samples to a linear operator plus white noise is plausibly routine for specialists, though I have not verified this. In practice the gap is **varying unknown orientation only**.

**Is that gap realistic for a master's thesis? No.** The authors say Fisher–Rao compatibility is the obstacle. A non-specialist will not close it in a master's timeframe.

**Originality: low.** There is a further problem that Sonnet did not raise. The pure-noise law of the supremum of L2-normalised Gaussian-filtered noise over location × scale × rotation is a classical object in scale-space and rotation-space random fields (Siegmund–Worsley 1995; Shafie et al. 2003; Euler-characteristic and tube approximations). So M1's "derive the pure-noise sup law for orientation and aspect ratio" is not a contribution; it is a lookup. That source is L2 + L1 for me, so it needs M0 verification. If it holds, both the λ-calibration piece and candidate B are occupied, in addition to Azaïs.

## Q2. Is the empirical/algorithmic claim still worth doing? — Partly agree with "narrow to a scoped empirical note", for a different reason than headroom

**Downgrading vs. honest narrowing.**
- *Downgrading* would mean replacing the research question by default with a benchmark of known methods, without evidence that the question is answered. I do not recommend that.
- *Honest narrowing* means stating only the claim the evidence can support. My basis is three facts:
  - (a) **The theory is occupied** (Q1).
  - (b) **The sup-law calibration is classical** (Q1).
  - (c) **Known σ makes calibration a Monte Carlo exercise.** With σ known, a parametric bootstrap of the whole fit → slide → sup pipeline calibrates any stopping statistic numerically, post-fit and post-selection included. An analytic certificate calibration then has no practical advantage, only possibly a cost one. **This is the strongest objection to A′ as a method, and it applies on any benchmark.** The 2.8 pp headroom is a separate, benchmark-specific problem.

**The one claim I think survives is local vs. global.**
- The discrepancy principle and Cp are global RSS statistics. A sup-|η| certificate is a *local* statistic.
- A non-tailored, pre-registrable hypothesis: *when misfit is spatially concentrated (an under-fit region in an otherwise well-fit image), global RSS rules stop too early, and a local sup statistic does not.*
- The direction of that prediction follows from theory (dilution of χ² vs. extreme value), not from the method. It also predicts where the certificate should *lose*: under diffuse misspecification, local statistics fire on structured residuals.

**A benchmark that tests this rather than tailoring it**
- It must use a generator family fixed before any method is run:
  - Gaussian-sum images with K* log-uniform on {4…64}.
  - Per-atom SNR set as multiples {0.5, 1, 2, 4} of the *pre-computed* null-sup quantile, not the mean.
  - Rotation and aspect ratio drawn freely.
  - An overlap sweep.
  - **A spatial-heterogeneity factor**: fraction of total K* concentrated in a sub-window.
  - One misspecified class (edges or textures).
  - R_MAX ≥ 6.
- It must state, for each cell before running, which baseline is expected to win.
- Baselines:
  - Bootstrap-calibrated discrepancy principle (mandatory new baseline).
  - Cp naive and search-df.
  - Best-fixed-R.
  - RAWcv.
  - A **windowed** discrepancy principle (local RSS per tile, with Bonferroni). This is the trivial local baseline. **If it matches the certificate, the certificate has no value.**

## Q3. Directions with more originality potential that use existing assets

I can support only two candidates with evidence. I will not invent a third.

**Q3-1. Local-vs-global stopping (A″, a narrowing of A′, not a new line)**
- Hypothesis as in Q2.
- Nearest work:
  - Shafie et al. 2003 / Siegmund–Worsley (L2/L1): the null law.
  - Azaïs 1706.00679 (Sonnet partial L4): spacing tests.
  - Image-GS error-weighted sampling (Sonnet partial L4): a local heuristic without calibration.
- Strongest rebuttal: a windowed discrepancy rule plus parametric bootstrap probably does the same job at trivial cost. In that case the result is a useful negative, not a method.

**Q3-2. Semigroup reformulation: multiscale Gaussian image = g_{Σmin} ∗ (positive measure)**
- The model becomes positive deconvolution with a known PSF. For positive measures, stability without minimum separation is known (SFW §1.4, Sonnet partial L4; Schiebinger–Robeva–Recht and Denoyelle et al., L1).
- Strongest rebuttal, and in my view decisive: the formulation makes **K non-identifiable**, since any wide atom is an infinite mixture of narrow ones. So it cannot select K. Turning it into a K rule needs a description-length or rate criterion, which is candidate E: low originality (Wolf–Ziv separation).
- **I do not recommend pursuing it.**

**What I examined and rejected**
- **Type identification ("should it grow?")** is a goodness-of-fit test of the K0 residual. That is the discrepancy principle under another name.
- **Sup tests on non-stationary processes** are covered by Euler-characteristic theory for non-stationary fields (Worsley / Taylor–Adler; L1 for me).

## Q4. Recommendation (single): honestly report that the current routes lack sufficient novelty for an originality-bearing contribution

**Reasons**
- The theory gap (varying-orientation BLASSO certificates) is beyond master's scope.
- The calibration is classical, and at known σ it can be replaced by a bootstrap.
- The certificate/algorithm skeleton is in SFW/ADCG/CL-OMPR.
- On the existing benchmark the K-axis gain is mostly the RAWcv-type identification. That last point is only partly verified (see Q5).

**What the report should say**
- A′ is closed as a *method-originality* route; A′'s theory gap is now one of the stopped/closed routes.
- What is kept is a *documented boundary result*:
  - Under known σ, 2D Gaussian-splat K selection on these benchmarks is captured by cheap global rules / RAWcv (once M2b is run).
  - The open theory question is varying-orientation certificates, attributed to Giard et al. §7.

**If a human chooses to continue anyway**, the only version I would accept is A″ (Q3-1) under these conditions. This is not my recommendation.
- **M0 (paper only) must be done first:**
  - Shafie et al. 2003 to L4.
  - Siegmund–Worsley 1995.
  - Azaïs §6.
  - Giard v3 §3–§5, to check whether v2/v3 added orientation.
  - Hardy 2023.
  - ADCG.
  - CL-OMPR.
  - Elvira et al. on OMP with continuous dictionaries.
- **First executable milestone: M2b.** Re-run the existing dev design with per-round RSS logged. Then evaluate on the existing tables: the bootstrap-calibrated global discrepancy rule, the windowed discrepancy rule, and the certificate.
- **Kill criteria:**
  - (i) M0 finds that location/scale/rotation sup calibration combined with greedy Gaussian birth already exists.
  - (ii) At M4 on the pre-registered heterogeneity benchmark, the certificate is not better than the *windowed* discrepancy rule by more than 2% NU in the concentrated-misfit cells.
  - (iii) The certificate costs more than 1.2 fit-equivalents.
  - (iv) The post-fit false-birth rate is above 2α at M3.

## Q5. Compliance

1. **Packet item 7 / REIDEA §2.4-2 overstate.** They say "Opus's K_cert≈0 prediction does not hold for D1". The §C calculation:
   - compares a **raw, pre-fit, isolated** blob's self-response to the **mean** of an **isotropic-only** null sup. Calibration would use a high quantile, and adding orientation and aspect ratio raises the sup.
   - My prediction concerned the certificate on **post-fit residuals** at K0 = 24, where D1 blobs are already absorbed.

   So §C neither confirms nor refutes the prediction. Rewrite as "not tested; the coarse pre-fit calculation is compatible with either outcome".

2. **Giard paraphrase (packet item 1, REIDEA §2.3, R14).**
   - Add the "known common orientation is straightforward" sentence.
   - Correct the SFW/CPGD wording (Q1).
   - Record which arXiv version was read (the ar5iv rendering dated August 2026 may be v2 or v3).
   - Also, "硕士级做不了" is a judgment, not a reading result; label it as such.

3. **M2 (packet item 6).**
   - The R*cv histograms total 192 per type, but there are only 18 images (6 per type). The units are replicates, not independent images, so "K-axis gain ≈ type identification" rests on 6 images per type, in-sample.
   - "Fixed R by type" (87.4%) uses the type labels; it is an oracle-type rule, not an implementable baseline.
   - The R_MAX = 4 truncation biases the D3 headroom downward.
   - "≈ type identification" should read "consistent with type identification on this 18-image in-sample table".

4. **REIDEA §2.3, Poon–Keriven–Peyré row.** "A′'s 5-D dictionary falls in the self-declared open zone" is correctly hedged. But after Giard, the open zone is only varying orientation. Update the row.

5. **The REIDEA §5 self-scores** ("master's-feasible: medium-high; PhD extension: medium") are unsupported. Drop them or label them as opinion.

6. **Levels.** I found no L1/L2 source labelled L4 in v2: "partial L4" rows list their sections, and ADCG/CL-OMPR are L1. **Missing nearest work:** the scale-/rotation-space random-field literature. Add it as L2/L1 pending M0.

7. **No pre-counted contribution remains.** "Proposed" is used consistently.

**Required edits**
- (a) Q5 items 1–5.
- (b) Add Siegmund–Worsley / Shafie et al. and the parametric-bootstrap baseline to A′'s nearest work and mandatory baselines.
- (c) Restate M1 as "verify the classical sup law", not as a derivation.
- (d) Record the recommendation and the conditional A″ path in STATE, with both STOPs (F0/H2, CF0) unchanged.

**Sources:**
- Giard et al. 2509.12889 (html v1); Giard et al. 2509.12889 (pdf); Rotation space random fields (abstract); Shafie et al., Ann. Stat. 2003; Bénard–Traonmilin–Aujol 2202.13757; Poon–Keriven–Peyré 1802.08464.

**For memory:** the project's A′ candidate now hinges on Giard et al. §7 (varying unknown orientation is open) and is challenged by the classical scale- and rotation-space sup-test literature.
----- END VERBATIM OPUS REPORT -----

## Sonnet annotations (not part of the verbatim report)
- Opus's recommendation (honestly report lack of novelty; A′ closed as a method-originality route) is **advice**, and it does **not** by itself close any route: only the human can decide to abandon the originality target; I do not auto-downgrade to a known-method benchmark either. I will report it, with the conditional A″ path, and let the human choose.
- Verified by Sonnet (L3, abstract-level WebFetch, 2026-11-05 ~22:25Z): Shafie–Sigal–Siegmund–Worsley, *Rotation space random fields with an application to fMRI data* (Ann. Statist. 31, 2003 per Opus; the McGill abstract page lists 31:1732-1771 and "(2002)") extends Siegmund–Worsley 1995 scale-space to rotation space, approximating the null distribution of the maximum via expected Euler characteristic/tube methods. The oriented-filter reading is an inference; formulas are not read (L3 abstract). This supports Opus's "classical object" claim at abstract level only.
- Sonnet checks on Opus's Q5: (1) accepted (§C is not a test of the post-fit certificate); (2) accepted — my own §7 extraction contained the known-common-orientation sentence and the "adapting CPGD could form the core of future work" sentence; I paraphrased them badly. arXiv listing (WebFetch): submitted 2025-09-16, latest v3 2026-01-08; the ar5iv text I read is labelled "version as of August 10, 2026" (so it is some later render; I cannot identify its version number; v3 abstract still says diagonal only); (3) accepted — 18 images × 32 units/image = 576 units; the 192 per type are replicates of 6 images; (4) accepted; (5) accepted; (6)–(7) accepted.
