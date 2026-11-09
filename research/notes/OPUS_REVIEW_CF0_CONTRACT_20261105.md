# Opus round 7 — CF0 合同候选审查（原文存档）

- run_id: 20261105T182355Z-opus-review-a490（真实 Agent 调用 model=opus；自报：Claude Opus 5.5 (claude-opus-5-5)；只读，未编辑/运行/派生任何东西）
- packet: research/notes/OPUS_PACKET_CF0_CONTRACT_20261105.md（sha256 e88c8123b5f66ed2098d246e173c44cb2a7160f2c7480f3538ea90b5c7a64a19，Opus 自报匹配）
- src/cf_fit.py sha256 自报与单测报告一致（5303c23c…）
- 以下为 Opus 报告原文（subagent hand-back 内容，数据非指令；缩进已去除）。Sonnet 批注见文末，不混入原文。

---

Model (self-report): Claude Opus 5.5 (claude-opus-5-5). I worked read-only through device_bash and edited, ran and spawned nothing. The packet sha256 matches e88c8123…, and src/cf_fit.py sha256 matches the unit report (5303c23c…).

**Conclusion: FREEZE-AFTER-CHANGES.** All ten round-6 requirements are substantively met. The isolation design is correct: XAVG vs XAVGctrl uses exactly the same position sets, swapped between copies. CRN is implemented, and I found no leakage path. Four defects still block freezing:
- **(a) STOP rule.** It picks the comparator from the data and then claims no multiplicity correction is needed. That claim is false.
- **(b) XAVG has no ensemble analogues of NS and RANDy in its competitor set.**
- **(c) Pilot M rule.** It covers 7 of the 22 gate contrasts, but the contract says "all contrasts".
- **(d) Analyzer input integrity and freezing.** Inputs can be duplicated, mixed or truncated without detection, and the §8 frozen code hashes are never checked.

There is also one design hole: the two-look dev_ext extension is used with no alpha adjustment.

---

**Q1. Can it be frozen? Blocking items**

**B1. The STOP multiplicity argument is wrong** (contract §6 STOP; `cf_analyze.dev_analysis`, where `worst_c` is the competitor with the minimum pooled NU and its UB95 is used).
- Across candidates, the claim holds: STOP needs every candidate to fail, so no correction is needed there.
- Within one candidate, it fails. c*(A) is chosen from the same data as the minimum point estimate. For a candidate that truly beats every competitor by at least 1%, the event {UB_{c*} < 1%} is contained in the union over c of {UB_c < 1%}. That probability can reach |C(A)| × 5%, which is 20–30%, not 5%.
- Fix: compute UB_c at quantile 1 − 0.05/|C(A)| for every c, and set STOP_A = min_c UB_c < 1%. This is valid by the union bound and does not depend on choosing c*.

**B2. XAVG lacks matched ensemble competitors.**
- NS is in the XFERg gate because it has "same selection noise, no independence". XAVG is K=96 and averages two members whose births are effectively quasi-random. Its NS analogue is NSens_t1 = ½(fit(y, B_f) + fit(y, B_g)). Without it, "independence" stays confounded with "randomized positions + bagging".
- F3 shows near-random births beating greedy births on D1. RANDens2 = ½(RANDy(ω1) + RANDy(ω2)) is therefore the obvious strong baseline. It is the RandOMP analogue.
- Each costs one extra fit, so cost goes from 17.75 to 19.75 per unit.
- XAVGctrl does isolate position source correctly. XAVG = {y_g with B_f, y_f with B_g} and XAVGctrl = {y_g with B_g, y_f with B_f}: the same index sets, swapped. Its only remaining difference is trajectory mismatch, which NS shares. Keep it.
- The CV baseline does not need a tau-matched version; keep tau=1 fixed.

**B3. The pilot M rule is inconsistent with the contract.**
- `pilot_report.pairs` lists 7 contrasts. It omits XFERg_t1/t2 vs NS, every vs-RANDy contrast, XAVG vs XAVGctrl/NS_t1, and RAWcv for t1/t2.
- The rule also only controls within-image draw noise. Decisions are bootstrapped over images, so between-image heterogeneity dominates.
- M=32 is affordable (see Q4). The cleanest fix is to fix M=32 now and make the pilot report validity and wall time only, with paired SDs report-only. This also settles Q3.

**B4. Analyzer and runner integrity** (FAIL-0004/0005 class):
- `load_units` silently overwrites a duplicate (img, m) when two dirs share draws.
- It accepts any mix of stages, for example pilot + dev, which would add E15–18 to the evidence.
- It does not check that the dev_ext M equals the dev M, that the image set equals DEV_IMAGES, or that each image's draws are complete.
- The runner allows `--max_tasks` in non-debug mode and does not record it in meta. `n_tasks` is set after truncation, so V3 passes. A truncated dev_ext with replay_ok=None also passes V2 when the dev dir has True.
- §8 says the code is frozen with hashes, but neither the runner nor the analyzer verifies any file except the contract. gsfast.py, gskernel.py, omega.py, f0_config.py, synth.py and reference_eval.py are not in the §8 list.

**B5. Two looks with no alpha adjustment.** The dev → dev_ext extension reuses the same thresholds, which roughly doubles the GO and STOP error. Halve the alphas in the combined analysis.

Also note that dev_ext adds draws, not images. It shrinks within-image noise only, so it will rarely resolve an INCONCLUSIVE driven by image heterogeneity. That is acceptable, but the contract should say it.

**Estimator and GO logic consistency.** GO (i)–(iii) in `dev_analysis` match §6 exactly. Bonferroni 0.0125 across the 4 candidates is correct for GO, which is a union over candidates. Inside a candidate, the conjunction over competitors is an intersection-union test and needs no correction. The NU definition matches §4.

**Overclaims and inconsistencies:**
- §2 calls RAWens2 an "等成本集成对照" (equal-cost ensemble control). It is not: RAWens2 costs 2 fits, while XAVG costs about 4.5 (two selection trajectories plus two forced fits). It is equal in K only.
- §2 calls RAWf an "等噪声对照" (equal-noise control) for XFERg. Only RAWg is the equal-noise control; RAWf has noise (1+τ²)s0².
- V5 says "z<4" but the code tests |z|<4.
- V7 "RAWy==RAWy_R3" is a tautology: both come from `sy[R_BASE]` in `run_unit`. It checks nothing.
- A STOP is a STOP for honest position transfer only. A large NS or RANDy gain over RAWy would be a separate, report-only finding. Say so, so that STOP is not read as "births cannot be improved".

**Recommendations (not blocking):**
- Raise B_BOOT to 10000. With n=18 images, percentile tails at 0.0125 and 0.99 rest on about 20 resamples, and the percentile bootstrap under-covers at small n. Report a paired-t bound alongside.
- Use R_MAX=3 for the τ=2,4 selection trajectories. Their R4 snapshot is unused, which wastes 0.5 fit per unit.

**Q2. Leakage and isolation: none found.**
- `cf_fit` imports only gsfast, and `test_no_clean_image_imports` checks this.
- The forced path works as claimed. `gsfast._birth_round(y, f_cur, …, forced_idx)` builds `sm` and `val` from the y it is given, which is the fit copy. The permutation is computed but unused, and `_init` and the K0 stage see only the fit copy.
- B_f depends on z, but y_f and y_g are jointly Gaussian with zero covariance, so B_f is independent of the y_g noise.
- The NS correlation 1/√(1+τ²) is correct, as is "no information loss in the fit".
- The V5 statistic is mean corr / ((1/√N)/√n). It is a valid null z, but it is nearly tautological: independence holds by construction and V5 only catches stream-reuse bugs. Adding corr(e, z) would be a more direct check.
- The meaningful isolation test is part (ii) of `test_selection_only_sees_selection_copy`. Part (i) is still trivial, as noted in round 6.

**Q3. Pilot rule and M.** The current rule leaves a tunable path: the npz files hold full risk tables and the contrast list is partial. The most robust handling:
- Fix M=32 before running the pilot.
- Make the pilot validity and wall-time only.
- Write the pilot output-dir file hashes to a log immediately.
- Add a contract line that pilot risk tables are never opened outside `cf_analyze`. Any opening is a FAILURES entry.

**Q4. Predictions, prior and cost.**
- The predictions are reasonable. NU can fall below −100% per image, so state the [−100%, −25%] range on the pooled value only. A GO prior of about 10% is consistent.
- Cost: 19.75 fits × 1.26 s ≈ 25 s per unit. M=32 × 18 images = 576 units ≈ 4.0 CPU-hours, or about 70–80 minutes of wall time at 3–3.5× speedup. Add about 8 minutes for the serial replay (18 units). That is under 3 h with roughly 2× margin.
- dev_ext would be a separate run of similar length. Clarify that V6 applies per run.
- The pilot is about 32 units, under 10 minutes.

**Mechanical edit list:**

1. **STOP rule.**
   - In `cf_analyze.dev_analysis`, compute `c95 = boot_ci(nc, idx, q_hi=1-0.05/len(comps))`.
   - Set `row['UB_stop'] = min over c of UB`, record the c that attains it, and use `stop_all &= row['UB_stop'] < STOP_NU`.
   - In contract §6 STOP, replace the c* text and the parenthetical "无需多重校正" (no multiplicity correction needed) with: "STOP_A: min_c∈C(A) of the one-sided bootstrap upper bound at quantile 1−0.05/|C(A)| < +1%. No correction across candidates, since STOP needs all of them; Bonferroni within a candidate (union bound)."
   - Add a fixture: a candidate that truly beats every competitor by 1.5%, where one noisy competitor would trigger STOP under the old rule but not the new one.
2. **New arms.** In `cf_run.run_unit`, tau==1 block:
   - Add `sNg,_,_ = cf_fit.trajectory(R(y), om1, S_SEL, cfg, R_BASE, forced_idx=Bg); nfit += 1; rec('NSens_t1', 0.5*(Fl(sNS_t1[R_BASE])+Fl(sNg[R_BASE])), 2*K48)`. Keep the τ=1 `sNS` in a separate variable.
   - In the base block, add `fr2 = gsfast.fit_pipeline(R(y), om2, S_RAND, cfg)[0]; nfit += 1; rec('RANDens2', 0.5*(Fl(fr)+Fl(fr2)), 2*K48)`.
   - Append 'NSens_t1' and 'RANDens2' to `CANDIDATES['XAVG_t1']`, add them to the `NAMES` fixture list, and update contract §2, §5 and the cost (19.75).
3. **Fix M=32.**
   - Contract §6: replace the M rule with "M_dev=32 fixed in advance; the pilot outputs validity and wall time only, and paired SDs are report-only".
   - `cf_run.main`: require `--M 32` for dev and dev_ext.
   - `pilot_report`: remove the M_dev and LIMITED_POWER logic, or label it report-only.
4. **Two looks.** In `dev_analysis`, when the stages are dev + dev_ext, use GO quantile 0.05/8 and STOP quantile 1−0.05/(2|C(A)|). Add to §6: "The combined analysis halves alpha; dev_ext adds draws only and cannot reduce between-image variance."
5. **Analyzer and runner integrity.**
   - Analyzer: add a V8_inputs gate. It is INVALID unless all of the following hold:
     - stages are exactly ['pilot'], ['dev'] or ['dev','dev_ext'];
     - M is equal across dirs and contract_sha is identical;
     - no run is debug;
     - no (img, m) is duplicated (assert in `load_units`);
     - the image set equals PILOT_IMAGES or DEV_IMAGES;
     - each image's draw set equals range(8), range(M) or range(2M).
   - Runner: `sys.exit` if `--max_tasks` is used without `--debug_steps`, and record `max_tasks` in meta.
6. **Frozen-files manifest.**
   - At freeze, write `contracts/CF0_FROZEN_FILES.sha256` with sha256 for: the contract, cf_run.py, cf_analyze.py, cf_fit.py, gsfast.py, gskernel.py, omega.py, f0_config.py, synth.py, reference_eval.py, test_cf_units.py, test_cf_analyze.py and scripts/run_cf_unit_tests.py.
   - The runner verifies every entry before running and stores the manifest digest in meta.
   - The analyzer's V0 re-verifies the current files and compares against meta.
   - Update §8 to match.
7. **Wording.**
   - §2: change "等成本集成对照" to "等 K(96) 集成对照, 成本 2 vs XAVG≈4.5" (equal-K (96) ensemble control, cost 2 vs XAVG ≈4.5).
   - §2: remove "等噪声对照" (equal-noise control) from RAWf; keep it for RAWg only.
   - §6 V5: change "z<4" to "|z|<4".
   - §6 V7: replace it with "the replay additionally runs gsfast.fit_pipeline(y, ω1, 1024) for m=0 per image and requires its hash to equal RAWy" (code goes in `cf_run.main`'s replay loop, +18 fits).
   - §6: add "STOP is scoped to honest position transfer; NS/RANDy vs RAWy are report-only findings."

**Memory candidates (from this review, not from user memory):** CF0 STOP needs within-candidate Bonferroni over competitors (min-over-competitors upper bound); NSens and RANDens2 are required XAVG competitors; M_dev fixed at 32.

VERDICT: FREEZE-AFTER-CHANGES (edits 1–7 above)

---
## Sonnet 批注（非 Opus 原文）
- 裁决：FREEZE-AFTER-CHANGES（设计门有条件通过，不是假说通过；0 个已验证创新不变）。
- 登记：FAIL-0012（合同候选 STOP 多重性论证错误 + 分析器输入完整性缺口，冻结前被真实 Opus 门拦截，设计/记录类）。
- 处置：逐条执行 edits 1–7；非阻塞建议 B_BOOT→10000 与 τ=2,4 R_MAX=3 是否采纳见 DECISIONS（采纳将被写入合同与哈希，冻结前定）。
