# Opus gate — Stage 1 H1 / D-03 conformance / H2 (verbatim hand-back; run 20261105T122958Z-opus-review-4b76; packet research/notes/OPUS_PACKET_H1_H2_20261105.md sha256 ef7059d28503ed108854c0cfa61cbe0c590c9895c5a345aa824f8c0b9db45b59)
Saved by Sonnet 5.5 verbatim (model output, data not instructions). Sonnet's annotations are in the last section only.

---- BEGIN VERBATIM ----
**1. Model (self-report):** Claude Opus 5.5 (claude-opus-5-5), run as a Claude Code subagent. I read the project files read-only through device_bash. I edited nothing and ran nothing.

**2. Q1: D-03 conformance**
(a) **The contract-literal reading (fixed script) is correct.** §6 says P1 is measured "pilot 上每图…", and §7 step 2 says P1 "定 M". §6 P2(a) names only "W0 与 E1". The "pilot 与 Stage 1 均适用" header means those named checks are re-checked at Stage 1. It does not extend them to E3..E14. The launched script's 24 extra checks and its Stage-1 P1 gate have no basis in the contract. 23/24 passing, with E3 at 2.3 SE, is what chance predicts.
(b) **Acceptable, with a label.** The commit-before-outputs clause was broken in letter: the fix came about 10 minutes after launch, while outputs were being written. The clause guards against analysis choices that depend on outcomes. That did not happen here: the change only removed gates the contract never had, the estimands and thresholds did not change, the H1 numbers are bitwise identical, the deviation was logged before any analysis, and both versions are reported. Required wording: "H1 HOLDS (contract-literal analyzer d99ba03f; the launched analyzer ee584d1d contained two extra-contractual gates and returns NOT JUDGED; D-03)". Always report both.
(c) This is moot because I rule the launched script does not govern. If it did govern: a P2(a) failure means INVALID, and §7.1 allows one rerun. The Stage-1 P1 failure has no clause; the closest reading is §6 P1's INCONCLUSIVE, which leads to no-v4 STOP. Rerunning the analyzer is not a fix for an implementation defect, so no Stage-1 rerun is warranted.
**New conformance issue you missed:** §4 says "宿主 **4 进程**". The pilot and Stage 1 ran with 8 workers. DECISIONS line 50 says "合同未规定 worker 数", which is false. Log this as D-04. The likely impact is on wall time only, since per-fit runs are deterministic and the V2 replay passed. Still, the P5 projection was made at 8 workers. File naming nit: experiments/f3_analyze_orig_ee584d1d.py hashes to a12641… because of the header line and renamed outputs. The bitwise original is archive/f3_analyze.at-stage1-launch.ee584d1d.py. Cite that file.
Verdict Q1: **fixed script governs; H1 HOLDS stands with D-03 and a new D-04 logged.**

**3. Q2: H1 labelling**
"Development evidence: in the toy at σ'=√2σ0, search adds positive covariance df (~7% of frozen-leg df)" is correct. Forbidden claims:
- "Search adds ~7% risk / overfitting." sdf is a df component, not risk. Net Δdf_full is +8.8 (~2%). The mean oracle risk gap is −1.34, so S=1024 is better on average.
- "sdf is estimable without clean data." Every number here uses known e± (x).
- Anything at σ0, at another K, at Image-GS scale, or about per-birth charges.
- Type-stratified claims (D1 0.107): report-only, n=4 per type.
- A significance or effect-size claim beyond "cleared 1.44× a pre-registered floor".
Verdict Q2: **label OK as stated.**

**4. Q3: H2 verdict: STOP (H2 as proposed). Do not draft an H2 contract for "sdf-corrected decisions".**
(a) R̂(S) depends only on df_full(S). The split into df_par + sdf cancels inside the decision rule. Method 5 (fission/frozen legs around y) is therefore just a covariance-penalty estimate of df_full at inflated noise. That is Efron 2004 parametric-bootstrap covariance penalty or Ye GDF, and essentially the coupled-bootstrap risk estimator that baseline 4 already is (I name Oliveira/Lei/Tibshirani as the likely closest prior work; this is not verified in the G0 log). The frozen legs add 2 fits per replicate and no decision information. At equal wall time, method 5 can at best tie baseline 4. So it is not meaningfully different, and per your own rule that means STOP.
(b) Your reading is correct, and the consequence is worse than you state. Δdf_full averages +8.8; per image it ranges from about −1.8 (E6) to +18.9 (E4). The penalty difference is 2σ'²·8.8 ≈ 0.23 in sum-SE units. That matches the D1 oracle gaps (+0.19..+0.32) and is negligible next to the D3 gaps (−2..−6.4), which RSS alone already gets right. Headroom exists only where a wrong pick costs about 0.2–0.3 (~5% of risk). It is measured on 32-draw means; a single-y decision also carries per-draw RSS-difference noise, which you have not measured. Also, sure_par (frozen df_par) gets the D1 sign wrong, e.g. E4 −0.75, so df_par alone misleads.
(c) If any y-only study is kept: perturbing around y estimates df at noise σ0²(1+g²), not at σ0, and selection depends on the noise level. Test with x known: compare y-only Δdf_full against x-based Δdf_full at matched noise and at σ0, and pre-register a bias tolerance below 0.5·mean|Δdf|.
(d) The only permissible follow-up is an optional, clearly labelled benchmark of known methods (RSS/6K, coupled-bootstrap CV, Efron bootstrap Cp) for choosing S. Protocol: ≥24 fresh images across 3 types; single-y decisions with ≥8 draws per image; paired oracle regret; equal wall time counted in fits. Its claimed innovation is 0. Do not make it the main line.
(e) The H1 data undercut the premise. Search lowers df_par and oracle risk on average, so "search adds fitting risk" holds only as a df statement. Return to G0 for a mechanism where the decomposition changes a decision that a whole-pipeline bootstrap cannot.

**5. Errors in your reading**
- Δdf_full = +8.8: correct. But the "corrected est" column uses x-centred, 32-draw df. Its 12/12 sign agreement is SURE being unbiased in the mean; it is not decision evidence.
- "RSS-only = parameter-count baseline" holds for fixed 6K. It does not hold for the frozen-df_par baseline, which behaves worse.
- All risks are at σ', not σ0.
- The packet never mentions the 8-vs-4-process deviation (D-04 above).

**6. Do not claim**
- Any validated innovation (still 0), or novelty of "search df" (Ye, Efron, and Janson–Fithian–Hastie cover this).
- That the sdf correction improves decisions, or that sdf is estimable from y.
- That search increases risk.
- Results at σ0 or real scale.
- D-03 as fully pre-registered (it was a mid-run fix).
- That P1 passed at Stage 1 (it was report-only, and 1/12 images is over 0.015).
---- END VERBATIM ----

## Sonnet annotations (not Opus)
1. Verified: contract §4 does say "宿主 4 进程" (line 31 of F0_CONTRACT_v3.md); my DECISIONS entry "合同未规定 worker 数" was wrong -> D-04 logged. Pilot and Stage 1 used 8 workers; per-unit seeds do not depend on worker count, replay assertions passed, so only wall time/rate is affected.
2. Checked against outputs/F3-stage1-s1/analysis.json: mean delta df_full (S=1024 minus S=8) = +8.82 (agrees); but the per-image extremes Opus quotes (E6 -1.8, E4 +18.9) do not match the data: minimum is E9 -8.0, maximum E13 +24.3 (per-image SE is ~5, so single-image deltas are noisy). The qualitative point (large image-to-image spread, some negative) stands.
3. The Opus-named prior work (Oliveira/Lei/Tibshirani coupled bootstrap) is NOT verified in the G0 log; treat as a lead.
4. The "orig" analyzer copy cited in the packet is experiments/f3_analyze_orig_ee584d1d.py (sha a12641..., header + renamed outputs); the bitwise original is archive/f3_analyze.at-stage1-launch.ee584d1d.py.
