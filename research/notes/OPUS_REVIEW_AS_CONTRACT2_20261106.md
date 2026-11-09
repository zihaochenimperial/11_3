# OPUS 门复审原文: AS 合同候选 v2 (run 20261106T000215Z-opus-review-b52f)

> 来源: Agent(model=opus) 子代理最终报告, 逐字保存 (由 Sonnet 主会话从任务输出文件程序化提取, 未改写)。子代理自报: "My system prompt says I am Opus 5.5 (model ID claude-opus-5-5). I cannot verify this independently."; 任务输出日志 message.model 字段 = claude-opus-5-5 (日志字段, 仍非独立证实)。
> 审查对象: contracts/AS_CONTRACT_CANDIDATE_v2.md sha256 b92e7dad82c21aa4be61574c6fdca014b9cb6ad5b795d1423a80eee2b3c1b251。
> 裁决: FREEZE-WITH-EDITS (12 项编辑, 见 Q7)。子代理称若逐字应用并记录 diff 则无需再审。文献线索为 L1。

---

**Model self-report:** My system prompt says I am Opus 5.5 (model ID `claude-opus-5-5`). I cannot verify this independently.

**Scope (run 20261106T000215Z-opus-review-b52f):**
- **Read in full:** contract v2 (sha256 checked, matches b92e7dad…), AS_KA_RESULT, my v1 review, both K-a stdout files, the K-a v2 script and aggregator, and synthesis §5.
- **Ran:** a scratch copy of the K-a v2 script, patched to log three things per candidate: the realised value under the raw-OMP initialisation and under the best of two initialisations (so v1 and v2 definitions are compared on the same seeds), and the clean-image MSE after refit.
  - K0=3, σ_n=0.02: cells (σ_b, spacing) = (0.3,7), (1.5,4), (1.5,7), (3.0,7), 12 seeds each, n=48.
  - K0=6, σ_n=0.03: cells (1.5,7), (3.0,4), 8 seeds each, n=16.
  - Files are in `/tmp/claude-0/-home-claude/c30445bf-b91f-5725-a565-964b312260f4/scratchpad/ka/` (ka2.py, pool.py, k3_*.json, k6_*.json). No uploaded file was modified.
- **L1 (background knowledge, not checked here):** the compute timings per LM step and per SVD on the i7-12700H, and all literature leads.

---

**1. Status of my 8 mandatory changes**

1. **Realisable split scores: ADDRESSED.** c=1, mass-preserving split, shared execution.
   - Residual 1: birth execution is not rule-neutral. Every chosen birth starts at c0 = OMP-raw's own coefficient. That favours OMP-raw's ranking, which is the same confound K-a found in its v1 realised value. **Fix:** execute every chosen birth from both {c0, c*_OLS}, refit each for T_r steps, and keep the one with lower training loss. This applies to all rules and costs one extra refit per step.
   - Residual 2: JOINT_FREE is two-sided for splits, (r·P⊥v)². It rewards candidates that would need c<0, which a c=1 split makes worse. **Fix:** use max(r·P⊥v, 0)².
   - **On JOINT_FREE as a secondary arm: legitimate.** It does not reintroduce the mismatch, because all rules execute the same edit and JOINT_FREE is only another ranking heuristic. Conditions:
     - it stays outside every gate;
     - "JOINT fails but JOINT_FREE would pass" is reported as hypothesis-generating only.
   - **On a d-grid: do not add one now.** α∈{0.4, 0.7} already gives a two-point grid. K-a's weak split Spearman reflects the nonlinear refit moving the children, which no linearised d-optimisation fixes. Also, the split Spearman is computed over only 6 split candidates per scenario, so it is very noisy.
2. **ORACLE_y-full as primary complete joint reference: PARTIAL.** It is run only on a 12-unit subset and is not primary.
   - This is acceptable for budget reasons if the contract states that the human-authorised "complete joint reference" is tested only on that subset.
   - Also add ORACLE_ys: the legal shortlist oracle (same union shortlist as ORACLE_xs, selected by training loss, T_o=T_r). See Q4.
3. **Birth-only/split-only variants and logs: ADDRESSED.** Residual: there is no frozen rule for reading a type-mix effect (K-e). **Add:** "If JOINT beats a cheap rule in the mixed pool but not within either the birth-only or the split-only variant, the effect is reported as a type-mix effect, not as compensation."
4. **Gates: ADDRESSED in structure.** Residuals are listed under Q4 (sign-flip definition, ORACLE procedure, power text).
5. **Dose-response: PARTIAL.** Missing definitions:
   - H_J is undefined. **Define:** H_J(σ_b) = 1 − exp(mean_i log(M_JOINT/M_cheap)), with cheap as frozen in Gate 0.
   - The arms run at σ_b=0.3 are not listed.
   - It is not stated whether σ_b=1.0/2.0 at σ_n=0.03, seed 9001, reuse the C3/C4 runs.
6. **Validity gates: ADDRESSED.** V3 needs fixing (Q6).
7. **Secondary readouts: ADDRESSED.** Optionally, state K-c (Tikhonov beating all growth arms by more than 1 dB) as a pre-registered "no task value" flag.
8. **K-a, L1 leads, synthesis correction: ADDRESSED.** Synthesis §5.2 has the correct non-stationary form. The K-a write-up has interpretation errors (Q2).

**2. Is the K-a interpretation defensible? Partly. One item is mislabelled, and the conclusion does not transfer to the gate metric.**
- **Numbers match the stdout files:**
  - v2 regrets: raw_c1 0.046, joint_c1 0.043, block 0.071, joint_free 0.038.
  - joint_c1 − raw_c1 = −0.0036 (p ~0.66); joint_c1 − block_c1 = −0.028 (p ~0.025).
  - v1: +0.0238.
- **The regret normalisation and the descriptive sign-flip use are fine.** The regret denominator ½|r|² includes the noise floor.
- **Flaw 1: "headroom about 8.5% MSE per step, joint captures about 6%" is a residual-energy ratio in observation space, not an MSE ratio.** The figures 0.503/0.457/0.460 are not in either staged stdout file, so their provenance is missing.
- **Flaw 2: the gates use clean-image MSE, and that changes the picture.** My same-seed check (K0=3, n=48):
  - One-step clean-MSE headroom over raw_c1 is about 9.4% for the legal full-refit oracle and about 17% for ORACLE_x. The y-residual headroom in the same runs is about 5%.
  - In clean-MSE terms, joint_c1 − raw_c1 is −0.023 log (sd 0.14–0.52 per cell, p ~0.67). That is about 23% of the legal headroom captured, but it is pure noise.
  - So "no realised-value advantage" holds only in y-space. In clean MSE the reading is unresolved, not "no headroom".
- **Flaw 3: the confound attribution is only partly supported.**
  - On identical seeds, switching from the v1 to the v2 realised-value definition moves joint_c1 − raw_c1 by about −0.009 regret.
  - The rest of the +0.024 → −0.004 change comes from comparing different samples (n=270 vs n=108).
  - Say "consistent with", not "confirmed".
- **Flaw 4: the reading can reverse when the model is near or over capacity.** With K0=6 and σ_n=0.03:
  - y-headroom is about 0.6%;
  - the legal oracle is about 31% *worse* than raw_c1 in clean MSE (it fits noise);
  - ORACLE_x still shows 29% headroom.
- **Other limits that remain:** K0, the single step, the coarse 6×6 birth grid, 14 LM steps, and the near-stationary start (the contract's states will not be stationary).

**3. Value of information.** My recommendation is to run it, cut down (Q5), rather than close now. Uncertainty is moderate.
- **Why not close now:** K-a does not show "no headroom" in the gate metric. In clean MSE, one-step headroom is non-trivial but noisy. Closing now would honestly be "not tested", not a negative result.
- **Rough priors (my judgement):**
  - Gate 0 passes (ORACLE_xs): about 0.7.
  - Gate 1 passes against both cheap rules: about 0.1–0.2.
  - GO overall: about 5–10%.
  - Even a GO gives only a narrow empirical claim, given the L1 collisions.
- **Main value:** a pre-registered, honest closure, plus reusable deblurring/LM infrastructure.
- **If the user's time is the binding constraint:** closing now is defensible, but it must be worded "untested at path level; unit-scale y-space self-check uninformative for clean MSE".
- This is the user's decision.

**4. Gate logic**
- **(a) Gate 0 on ORACLE_x is a necessary condition only.** A pass can come entirely from avoiding noise-fitting, which no y-based rule can access (K0=6 result above).
  - Keep STOP when ORACLE_xs < 10%.
  - Add ORACLE_ys and report H_Oys.
  - Pre-register: if H_Oys ≤ 0, a Gate-1 pass is flagged as unexplained.
- **(b) Oracle procedures are underspecified.**
  - After an ORACLE_xs pick from the T_o=8 trial refits, does the path continue from the 8-step state or from a fresh T_r=15 refit? It must be the latter, for parity with the rules.
  - The ORACLE_x-full T_o is unspecified.
  - The shortlist must be computed from the oracle's own path state.
- **(c) The INCONCLUSIVE branch must compare ORACLE_xs and ORACLE_x-full on the same 12 units.** Also make ORACLE_x-full conditional: run it only if ORACLE_xs fails. This also saves budget.
- **(d) Gate 1 (ii) "upper bound" is undefined.** **Define:** one-sided p = (1 + #{flipped means ≤ observed})/(1 + B) < 0.05. Better, enumerate all 2^24 sign vectors exactly, which is cheap and deterministic.
- **(e) Null misread risk.** The fixed K_max=36 endpoint at σ_n=0.03 penalises rules that are more faithful to training loss.
  - Pre-register: report training loss per rule at K_max.
  - Report the Gate-1 statistics at the discrepancy-principle K as a secondary (non-gating) readout.
  - If JOINT has lower training loss but higher clean MSE, read it as overfitting, not as a selection failure.
- **(f) The decision table lacks rows** for: Gate 0 INCONCLUSIVE; the V10 "numerically fragile" flag (a GO becomes INCONCLUSIVE-numerics); and the type-mix rule (1.3).
- **(g) The power text is wrong.** Criterion (i) requires the point estimate to be ≤ log 0.95. For a true 5% effect, that criterion alone passes about 50% of the time, and less under the intersection with (iii)/(iv). With SE 0.016 the gate reliably detects only effects of about 8% or more (≈0.98). Replace the ">0.9" claim.
- **(h)** Everything else can be computed from the listed logs, provided the image family and the cheap choice are logged.

**5. Feasibility (L1 estimates)**
- Analytic J at 1024×216, JᵀJ and solve: roughly 5–10 ms per LM trial. SVD per step: about 30 ms.
- Rule arms: about 10 s per unit, 14 arm-types × 192 units ≈ 7–8 CPU-h.
- ORACLE_xs: about 2 min per unit, ≈ 6 CPU-h.
- ORACLE_y-full and ORACLE_x-full: each about 15–20 min per unit, close to the 20-min single-run cap; about 3.5 CPU-h each for 12 units.
- **Total: about 20 CPU-h**, so 3.5–4 h wall with 6 processes. Plausible if "≤4 h" means wall time; over budget if it means CPU-hours. **State which.**
- **Cut order:**
  1. ORACLE_x-full made conditional.
  2. ORACLE_y-full cut to 6 units.
  3. ORACLE_xs/ys shortlist cut to top-5 per rule.
  4. Birth-only/split-only kept for JOINT and OMP-raw only.
  5. INIT-N restricted to C1 and C4.
- Pre-register the 20-min cap exemption, or chunking, for full-oracle units.

**6. Validity gates**
- **V3 is mis-specified for non-stationary states.** The brute-force decrease measured from ½‖r‖² equals Δ_JOINT + ½‖Pr‖², so V3 will fail after 15-step refits. **Specify:**
  - baseline = linearised refit without the edit, ½‖P⊥r‖²;
  - unweighted LS, ignoring the 1e-6 a² term;
  - births: free c, or fixed at the clip value when the clip is active;
  - splits: c=1.
- **V4:** state which candidate set must keep its ranking (duplication adds split candidates).
- **Add V16:** at step 1, all arms receive an identical C_1 (hash) and the same execution function.
- **Add V17:** ORACLE outputs are never read by method processes (file permission or logging check).

**7. Must-fix edits before freeze**
- (a) Birth execution: best of {c0, c*_OLS} after T_r refit, for all rules.
- (b) JOINT_FREE one-sided.
- (c) Add ORACLE_ys (all units, or seed 9001 only), with the H_Oys reporting rule.
- (d) ORACLE_xs continues from a fresh T_r=15 refit; specify the ORACLE_x-full T_o; make ORACLE_x-full conditional; compare on the same 12 units.
- (e) Define the sign-flip p (exact enumeration).
- (f) Correct the power text.
- (g) Add decision-table rows: INCONCLUSIVE, fragile numerics, type-mix.
- (h) Pre-register the training-loss and discrepancy-K secondary readouts as overfitting diagnostics.
- (i) Define H_J and the dose-response arms and reuse.
- (j) Fix V3; add V16 and V17.
- (k) State the budget unit and the cut order.
- (l) Fix §8 and AS_KA_RESULT: "y-residual energy" not MSE; give provenance for 0.503/0.457/0.460; "consistent with" a confound.

All of these are textual or small design changes. If they are applied verbatim with a logged diff, no further Opus gate is needed.

**8. What not to claim, and what to disclose**
- Do not say K-a shows "about 8.5% MSE headroom" or "no headroom". It is a unit-scale, one-step, y-space residual figure.
- Disclose my same-seed clean-MSE check: legal one-step headroom of about 9%, with a JOINT advantage that is unresolved and noisy.
- The confound is "partly accounted for", not "confirmed".
- Disclose that the gate detects effects of about 8% or more, not 5%.
- No contribution has been validated. All literature collisions are L1.
- The reviewer's model identity is self-reported and unverifiable.
- The thresholds are arbitrary.
- Possible memory-derived context for the main session: the user's memory lists an MSc project choice involving "2D Gaussian inverse problems" (P1817). It may bear on how much infrastructure value the user places on this line.

**Verdict: FREEZE-WITH-EDITS** (the 12 edits listed in Q7).

**Summary for the human (≤120 words):** The revised test design fixes most earlier problems and can be frozen after about 12 small, specific edits. The main one: new Gaussians must start from a rule-neutral amplitude, otherwise the design quietly favours the cheap rule. The earlier small self-check was summarised too strongly. Its "≈8.5% headroom" measures fit to the blurred data, not image error. Measured as image error, my rerun finds about 9% one-step headroom, and whether the "joint" rule captures it is unresolved. Running the full test costs about a day plus 3–4 hours of computation. The chance of a positive result is low (about 5–10%), but it would close this line properly. Closing now is acceptable only if described as "not tested".
