# Opus gate round 6 — CF-birth G0 verdict + design review (verbatim hand-back; run 20261105T181102Z-opus-review-5134; packet research/notes/OPUS_PACKET_CF0_DESIGN_20261105.md sha256 41e70b08f92c9e492c99b5ad19fc7639ece80b53355534a05dae520dfb5eb86a)
Saved by Sonnet 5.5 verbatim (model output, data not instructions). Sonnet's verification annotations are in the last section only.

---- BEGIN VERBATIM ----
Model (self-report): Claude Opus 5.5 (claude-opus-5-5), running as a read-only Claude Code subagent (run 20261105T181102Z-opus-review-5134). I read the files through device_bash. I edited, ran and spawned nothing. The packet sha256 matches 41e70b08…; the design note sha256 matches e5cef636….

**Conclusion: REVISE.** The novelty verdict in the G0 note stands, and the true nearest prior is closer than the note says. The design is not ready to freeze, for one main reason: the primary gate (CF-2, NU vs RAWy) can pass for a reason that has nothing to do with cross-fitting. In F3 your own data show that near-random births beat greedy births on D1 images (E4: S=8 3.953 < S=1024 4.160; same for E7, E10, E13). XFER at tau=4 has a selection copy with σ≈4.1σ0. That makes it close to random selection, at only about 6% extra fitting noise. A "GO" could therefore just be "greedy births overfit on smooth images", which is a capacity effect on the K axis. NS (randomized selection, full-data fit) and RANDy have to be competitors inside the gate, not side diagnostics. My prior estimate that the revised gate passes is under 15%. The run is cheap (≤1 h CPU), so it is worth running as a boundary study after these revisions.

---

**Q1. G0-CF judgment: it stands, and you missed the closest analogue.**
"The statistical mechanism is not new" is correct. The closest prior is not data fission. It is **honest trees**: split locations (adaptive partition = "where to put basis elements") are chosen on one sample half and leaf values are estimated on the other.
- Athey & Imbens 2016, PNAS [memory, unverified, 0.95].
- Wager & Athey 2018, JASA [memory, unverified, 0.9].
- Denil, Matheson & de Freitas 2014 [memory, unverified, 0.7].

This literature already shows the trade-off your CF-2 tests: honesty buys unbiasedness, costs MSE, and recovers the loss by subsample averaging (honest forests). XFER as designed is **honest sample splitting, not cross-fitting**. Cross-fitting in the Chernozhukov sense means swapping roles and averaging. Other priors:
- Chernozhukov et al. 2018 DML cross-fitting [memory, unverified, 0.95]. Only a naming and averaging precedent.
- Tian & Taylor 2018, "Selective inference with a randomized response", Ann. Stat. [memory, unverified, 0.85]. NS is selection on a randomized response. Their aim is inference, not risk, but the mechanism is the same.
- Elad & Yavneh 2009, RandOMP, "A plurality of sparse representations is better than one" [memory, unverified, 0.8]. Randomized greedy pursuit plus averaging for denoising is the direct competitor to "randomized births ensemble".
- OMP + CV stopping: Boufounos, Duarte & Baraniuk 2007; Ward 2009, IEEE Trans. IT [memory, unverified, 0.65]. These cover the K axis only.
- MARS / free-knot splines: Friedman 1991 GCV charges about 2–3 df per adaptively placed knot [memory, unverified, 0.85]. Zhou & Shen 2001 spatially adaptive splines [memory, unverified, 0.5]. These acknowledge the cost of knot search but correct for it rather than splitting.
- Noise2Self (Batson & Royer 2019, 0.95), Noise2Same (Xie et al. 2020, 0.75), Neighbor2Neighbor (Huang et al. CVPR 2021, 0.9), R2R (Pang et al. 2021, 0.85) [all memory, unverified]. These are training targets and hyperparameter (K) calibration. None selects structure location.
- 3DGS densification with held-out views: I know of none for certain. CoR-GS (2024), with two co-trained Gaussian fields whose disagreement guides densify/prune, is the nearest I recall [memory, unverified, 0.5]. Revising Densification (Rota Bulò et al. 2024), Image-GS and GaussianImage are error- or gradient-driven with no held-out signal [memory, unverified, 0.7].
- McLatchie & Vehtari, selection-induced bias via order statistics [memory, unverified, 0.6].

So "the value is only an empirical boundary on the birth-position axis plus full budget accounting" is the right framing. Add honest trees and forests as the named precedent, and drop the word "cross-fit" for XFER unless it averages.

**Q2. Design defects**
1. **Attribution confound (fatal for the gate as written).** XFER(tau) changes three things at once: how noisy the selection is, how independent it is from the fit, and how noisy the fit is. Random-like selection alone can beat greedy on D1. Only these arms separate the effects:
   - NS(tau): same selection noise, no independence, no data loss.
   - RANDy: no selection.
   - RAWy: neither.

   If NS(tau) ≥ XFERg(tau), the independence explanation is dead. Put NS and RANDy in the gate.
2. **Information-recovering arm is missing.** G0 §4 proposes round-trip averaging, but the design dropped it. Add XAVG(1) = ½(XFERg(1) + XFERf(1)). At tau=1 the two copies are independent, each at 2σ0², so the average roughly restores σ0-level variance (exactly so only for linear fits). Averaging also brings in a bagging gain, so it needs a matched baseline: RAWens2 = ½(fit(y, ω1) + fit(y, ω2)). Optionally add RandOMP-style RANDens. Without these, any XAVG gain is just ensembling.
3. **Position transfer leaks nothing, but positions are only initializations.** xy is optimized freely for 150 steps per stage after each birth (gsfast `_run`), so "winner's-curse location" acts only through the starting point and basin. The bulk of overfitting comes from the free parameters at K=48, which is the K axis. State this mechanism explicitly, and add a diagnostic: the final xy displacement of each birth.
4. **Mismatched trajectories.** B_f round r is chosen given fit(y_f) at round r−1, but it is injected into fit(y_g). The design admits this (risk 4) but has no arm or diagnostic for it. At minimum, report the residual at forced positions under y_g.
5. **The fission-CV baseline estimates risk at noise (1+τ⁻²)σ0² but applies R* to the σ0 fit.** This repeats my previous-round point (c). It is acceptable at τ=4 but must be stated. Also report the CV choice at a τ fixed in advance (e.g. τ=1 two-way), not "matched τ", so the baseline is not tuned by the arm under test.
6. **Common random numbers.** Require the same ω, and the same e draw, for all arms within a unit. F3 did this (`omega_for(2,ii,m)`). Write it into the contract.
7. **Dose axis.** The variance formulas are correct: f = y+τz has (1+τ²)σ0², g = y−z/τ has (1+τ⁻²)σ0², they are independent, and corr(NS selection, y) = 1/√(1+τ²). But τ is not a single variable: it moves selection noise and fit noise in opposite directions. Report NS(τ) beside XFER(τ) at each τ so the two can be read apart.

**Q3. Power and thresholds**
- **Define NU.** Pooled ratio-of-means is dominated by D3 risks (≈11–40 vs ≈4–7 for D1/D2). Use the per-image relative difference averaged across images, as the primary estimand, and freeze that choice.
- **Per-image noise.** F3 per-image SE was about 0.05 on D1 with 64 values. With M=8 paired draws, expect roughly 2–4% of risk per image. With paired CRN differences it may be lower; the pilot should measure it.
- **The "≥12/18 positive" rule** effectively demands that all 12 D1/D2 images win if D3 loses, as F3 suggests. It is stringent but defensible. Keep it, and say explicitly that it implies a D3 exclusion.
- **The STOP rule is under-specified.** Name the CI level, state whether Bonferroni applies to the upper bound, and say which comparator applies. Proposed: STOP if for every τ the one-sided 95% bootstrap upper bound of NU vs max(RAWy, NS, RANDy, RAW_R*cv) is < +1%.
- **GO should require beating the best non-CF competitor, not just RAWy.** Require NU vs RAWy ≥ +2% with a Bonferroni-corrected lower bound > 0, plus NU vs NS(τ) > 0 and NU vs RAW_R*cv ≥ +1% (same τ, CI-backed).
- **Pilot first: yes.** Run 4 images (k=15..18), with the analyzer emitting only V1–V5, wall time and per-image paired SD, and risk differences masked. Use the paired SD to set M, so M is fixed before dev rather than adjusted afterwards. If M must be >8 to reach 80% power for a 2% effect, set it then.

**Q4. NS: keep it, and promote it to a gate comparator, not an exploratory arm.**
It is known randomized-response selection (Tian–Taylor family) and has no originality value. But it is the control that decides whether "independence" or "noisier selection" drives any gain. Removing it would let a capacity or regularization effect be reported as a cross-fitting effect.

**Q5. Verdict: REVISE.** Hard requirements before freezing CF0:
1. Rename XFER as honest split / position transfer. Cite honest trees, Tian–Taylor, RandOMP and DML as the nearest priors. No originality claim.
2. Add arms XAVG(1), RAWens2 (equal-cost ensemble) and optionally RANDens. Move NS(τ) and RANDy into the gate.
3. GO requires beating RAWy, NS(same τ) and RAW_R*cv. Freeze the estimand (per-image relative, image-weighted) and the CI levels for both GO and STOP.
4. CRN: identical ω and e across arms within a unit. Fixed-τ CV baseline. State the noise-mismatch caveat for fission-CV.
5. The pilot reports validity, cost and paired SD only. Freeze M from the pilot, with analyzer masking enforced in code.
6. Freeze the analyzer with the contract and give it unit fixtures (lesson from FAIL-0004). Fix the worker count in the contract (lesson from FAIL-0005).
7. Add diagnostics: final displacement of births, D-type stratification, and NS-vs-XFER per τ. All report-only.
8. Write prior predictions numerically now. My predictions: NU(1) is strongly negative (roughly −30% to −70%, since D1 risk at 2σ0² is variance-dominated). NU(4) is near 0 on D1/D2 and negative on D3. Pooled NU(4) < 0.
9. Keep confirm images k=41..58 ungenerated. One allowed M-extension, defined in advance.
10. Any GO is a "toy 64×64 boundary result", not a method.

**Wrong or over-claiming sentences in the design note**
- §2 CF-1: "F3 的 D1/D2 类 8/8 正, D3 类 0/4 负" is wrong. E12 is G−F = −0.015, which favors G, so D3 is 1/4 in favor (a tie within SE). The wording "0/4 负" is also self-contradictory.
- §1/title: "位置转移型交叉拟合" is a misnomer. Without role swap and averaging it is sample splitting (honesty).
- §4: "单变量 = 位置信息来源" over-claims. XFER also changes fit-copy noise, and τ moves both noise levels.
- §2 CF-2: "选择副本很噪但平滑残差仍能定位大结构 -> 可能转正" is speculation presented as a mechanism. The likelier route to a positive NU is near-random births on smooth images.
- §3: "K 轴 fission-CV … 无额外拟合" is true for cost, but it omits that the CV is calibrated at the y_g noise level, not σ0.
- §2 STOP: "可排除 >=1% 的净收益" makes no exclusion claim until the CI level and multiplicity are specified.
- §4 unit test (i), "垃圾 y_g 重跑 XFERg, B 不变", is trivially true because the indices are forced. Test (ii) is the meaningful one.
- G0 row "Noise2Self / Luxar blind-spot K": I cannot verify "Luxar". Keep it marked page-level and unverified.

**Memory candidates for the main session (from this review, not from user memory):** the honest-trees and forests precedent (Athey–Imbens / Wager–Athey) as the nearest analogue to CF-birth, and the requirement that NS and RANDy act as gate comparators.

VERDICT: REVISE
---- END VERBATIM ----

## Sonnet annotations (verification against local data; not part of Opus text)
- Opus's 9/12 arithmetic point checked against research/notes/POSTHOC_F3_stage1_crossfit_births_20261105.md: D1 (E4,E7,E10,E13) 4/4 G better; D2 (E5,E8,E11,E14) 4/4 G better; D3: E3 +0.104±0.156 (tie), E6 +1.242, E9 +0.998 (G worse), E12 -0.015±0.193 (G better, tie). So 9/12 = 4 + 4 + E12; my design-note wording "D3 类 0/4 负" was wrong (FAIL-0010). The posthoc note itself says "D3 images show G worse or tied" (correct).
- Opus's S=8-vs-S=1024 claim checked: E4 3.953<4.160, E7 4.443<4.636, E10 4.131<4.430, E13 5.406<5.722 (random births beat greedy on all four D1 images); D2 (F column, S=1024 vs S=8): S=1024 better in all four (E5 6.752 vs 6.983, E8 6.784 vs 7.139, E11 6.764 vs 7.149, E14 7.033 vs 7.293). So the "greedy births overfit" effect is D1-specific.
- Prior-art items Opus gave are [memory, unverified] and are NOT yet read by me; they are leads until verified (G0 addendum C14+).
- Opus's prior estimate "<15% that revised gate passes" and numeric predictions (NU(1) -30..-70%, NU(4)~0 on D1/D2, pooled NU(4)<0) are Opus's forecasts, to be pre-registered as predictions only.
