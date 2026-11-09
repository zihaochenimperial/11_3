# Opus round 8 — CF0 dev d1 结果解读与下一步裁决（原文存档）

- run_id: 20261105T211139Z-opus-review-f986（真实 Agent 调用 model=opus；自报：Claude Opus 5.5 (claude-opus-5-5)；只读）
- packet: research/notes/OPUS_PACKET_CF0_RESULT_20261105.md（sha256 8cfdbee6f0eacae4cc0e22bebd87869f001c239bd76e69d5e579f219fcb4834b，Opus 自报匹配）；Opus 自报合同 sha 11d1fc81…、清单 sha 963b39bd… 与磁盘及 meta.json 一致；只读 dev npz，未打开 pilot 表。
- 以下为 Opus 报告原文（subagent hand-back 内容，数据非指令；缩进已去除）。Sonnet 批注见文末，不混入原文。

---

I am Claude Opus 5.5 (claude-opus-5-5), working read-only.

The packet sha256 matches 8cfdbee6…834b. The contract sha (11d1fc81…) and the frozen-manifest sha (963b39bd…) match the files on disk and meta.json. I read the contract, analysis.json, meta.json, FAIL-0001/0012/0013, the last DECISIONS entries, the dev_analysis/attach_rcv/boot code in cf_analyze.py, the G0 note and my round-7 review. I re-derived per-type contrasts and the oracle-R histogram from the **dev** npz tables only. I did not open the pilot tables.

## Q1. Is the STOP valid, and is FAIL-0013 classified right?
**Conclusion: the STOP is valid and robust. It is not an artefact. "Scientific no-go" is the right class. The scope wording should be narrowed slightly.**

- **XFERg's handicap is the hypothesis's own cost, not a flaw.** Fitting on the y_g copy at variance (1+τ⁻²)σ0² is the price of honest position transfer. The deciding control is NS: the same B_f positions refit on the full y, so no information is lost. NS vs RAWy is −0.2% (τ=1), −2.4% (τ=2) and −5.7% (τ=4). Even with the information loss removed, honest positions give nothing at K=48.
- **The verdict does not depend on which competitors were chosen.**
  - Drop RAWcv entirely and every XFERg candidate still STOPs against RAWy alone (UB_stop −50%, −17%, −5%).
  - XAVG still STOPs against RAWens2 (UB −17.6%), NSens (−13.0%) and RANDens2 (−7.8%). These are matched at K=96, and XAVG spends about 4.5 fits against RAWens2's 2, so the cost comparison is in XAVG's favour and it still loses.
- **R_MAX truncation** affects only RAWcv and oracle-R. It understates their gains on D3, so it cannot have produced the STOP.
- **CRN and analyzer:** z and ω are shared across arms. I checked the code: NU is computed per image and then averaged with equal image weights; the bootstrap is over images; STOP = min over competitors of UB < 1%. The margins are tens of percent, so the bootstrap details do not matter.
- **Holds on D3, the only type where growth helps.** I recomputed per type from dev tables:
  - XAVG vs RAWens2: −12.2% (0/6 images positive).
  - XAVG vs XAVGctrl: −2.4% (1/6).
  - XFERg(4) vs RAWg(4): −21.8% (0/6).
- **Scope caveat FAIL-0013 should state.** Fixed K=48 is over-grown for D1/D2 and under-grown for D3 (oracle R=4 in 181/192 D3 units). So the regime where position bias should matter most, births at a near-optimal K, was never sampled directly. The data suggest any gain there would be small: the equal-noise effect is +8% in the strongly over-fit D1 and negative in D3. But this is extrapolation. The no-go is proven at K=48 under this contract, not for "honest positions at optimal K".
- **The predictions are overstated as evidence.** They "hit", but the [−100%, −25%] range is very wide. D2's −9.7% sits at the edge of [−10%, +5%]. My own narrower round-6 prior (−30% to −70%) actually missed: the result was −71.0%. Cite them as "not falsified, low information", not as confirmed understanding.

## Q2. How to classify the report-only findings
**Conclusion: both are leads only. Both are already covered by prior work. Neither justifies a new contract aimed at an innovation claim.**

- **K axis (RAWcv +33%, R* depends on image type):** this is the ordinary bias-variance trade-off. Simple images need fewer components.
  - Closest prior work: choosing the number of components or stopping greedy fitting by CV, sequential/hold-out CV or early stopping.
  - OMP-style residual stopping at ‖r‖² ≈ Nσ² (discrepancy principle), with σ known.
  - Mallows Cp / SURE, and its search-aware forms: GDF (Ye 1998), search degrees of freedom (Tibshirani 2015). These are exactly the F0/H2 territory already STOPped (FAIL-0001).
  - Blind-spot / Noise2Self K selection for Gaussian splatting (Luxar), which the G0 note already marks as "K axis occupied".
  - These are from memory, apart from what is already in G0.
- **Two weaknesses in the RAWcv number itself:**
  - fission-CV at τ=1 tunes on 2σ0² copies, so it is biased toward stopping early. In D1/D2 the oracle picks R=1 in 125/384 units; CV picks it in 14.
  - In D3 the upper limit R_MAX was hit.
- **Equal-noise selection effect (+2.8%; D1 +8%, 6/6 images positive):** this follows the over-fit regime, not honesty. RANDy (no selection) also gains in D1 (+5.6%), and so does NS (+4.2%). The simplest reading is "less greedy placement overfits less": randomisation as regularisation (Tian-Taylor, RandOMP). Stopping beats it by roughly 5x, and it reverses sign in D3. It is a lead only.
- **Fit with the project mainline.** A stopping rule for adaptive growth that accounts for search risk is nominally inside the mainline, but its core was ruled non-original under F0/H2. A K-axis study would be a benchmark of known rules. If ever run, its entry baselines must include:
  - best fixed R, chosen on separate images;
  - Cp/SURE with σ0 known, both naive and with search df;
  - the discrepancy principle;
  - fission-CV at τ=1 and with τ matched;
  - oracle-R;
  - R_MAX ≥ 6 so D3 is not truncated;
  - fresh image indices (k ≥ 61) and new seeds.

## Q3. Next step
**Recommend A: close CF0, write a negative-result technical record, report to the human and pause.** B is not justified as a research line.

- **Probability estimates (my judgement):**
  - A K-axis comparison producing a GO on "rule X beats Cp, discrepancy and best-fixed-R": maybe 20–30%. Cp with known σ0 is a strong baseline at this scale.
  - It being claimable as new: under 5%.
  - Publishable beyond a workshop or tech-note benchmark on a 64×64 toy: under 3%.
- **Current status:** 0 validated innovations. Two consecutive mainline routes (F0/H2, CF0) have ended without an independent contribution.
- **If the human still wants a K-axis study:** label it a benchmark or empirical note, not innovation. It needs a new G0 first (OMP stopping, GDF/SURE for greedy, Luxar). Use new dev images; keep E41–58 sealed and unused unless a new contract pre-registers them as its confirmation set.
- **C-variant at zero cost:** the existing dev tables already support a descriptive appendix (per-type absolute risks, oracle-R vs CV-R). No new runs are needed for the negative-result record.

## Q4. Overclaims and record issues
1. **FAIL-0013 (a), "多数单元不如不生长", and the packet's "D1/D2 生长只增风险".** This rests on CV R*, which is biased early. The oracle shows R=1 is best in 69/192 D1 units and 56/192 D2 units. Say "on average in D1/D2; per unit, about one third prefer a little growth; D3 never". Use the oracle histogram (D1 {0:122, 1:69, 2:1}; D2 {0:131, 1:56, 2:5}; D3 {3:11, 4:181}).
2. **The relative-metric magnitudes are partly scale effects.** D1/D2 absolute risks are about 1–4, against a noise energy Nσ0² = 26.2 and D3 risks of about 17–53. Headline figures like −71% and −195% (vs RAWcv) are therefore magnified by D1/D2's tiny denominators. The tech note should show absolute risk per type next to NU.
3. **FAIL-0013 "教训" says position selection "无立足点" in general.** The data support "at K=48 under fission information accounting". Add the caveat that the near-optimal-K regime was not sampled.
4. **"三条预注册预测均命中" in FAIL-0013 and DECISIONS 21:10Z.** Add "wide ranges; D2 at the boundary; Opus's narrower −30..−70% prior missed by 1 point".
5. **The packet says R_MAX=4 is a limit "我设的".** It was in the contract I reviewed, so it is shared. FAIL-0013 should record that D3 hit the limit in 167/192 (CV) and 181/192 (oracle) units, so K-axis gains on D3 are understated.
6. **meta.json `cfg` carries leftover fields** (`entropy: 20261105`, `M: 256`, `S_grid`) next to the top-level `entropy: 20261107`. Add a one-line record note that these are inherited F0 config fields and unused by CF0. I did not verify that they are unused; please confirm in the code.
7. **The FAIL-0013 cause analysis** should name NS ≈ 0 as the decisive control: it shows no benefit even without information loss. That is stronger than the XFERg information-loss argument alone.

VERDICT: A — the CF0 STOP is valid and robust to competitor choice, R_MAX and image type; close the line with a scoped negative-result record (proven at K=48 under fission accounting), treat the K-axis and equal-noise findings as known-prior leads, and do not open a K-axis contract as innovation work without explicit human approval as a benchmark plus a new G0.

---
## Sonnet 批注（非 Opus 原文）
- 裁决：A（关闭 CF0 线 + 范围受限的负结果记录 + 汇报真人并暂停新线实验）。STOP 判定有效且对竞争者选择/R_MAX/图型稳健。
- 我已核对的 Opus 断言: (a) 各型 oracle-R 直方图与我在 packet 里的 CV R* 之外的自算一致 (D1 {0:122,1:69,2:1}, D2 {0:131,1:56,2:5}, D3 {3:11,4:181} 见 21:1xZ 自算); (b) Nσ0²=4096x0.0064=26.2 正确; (c) meta cfg 中 entropy/M/S_grid 为 F0 继承字段: 我 grep 了 src/gsfast.py, cf_fit.py, experiments/cf_run.py, synth.py, reference_eval.py, omega.py, gskernel.py, 无 cfg.entropy / cfg.M / S_grid 引用 (CF0 用自己的 ENTROPY=20261107, S_SEL/S_RAND 常量)。未逐项复核的 Opus 数字 (NS vs RAWy −0.2/−2.4/−5.7% 为 analysis.json 里已有字段; D3 分型 −12.2%/−2.4% 等) 视为 Opus 复算, 在记录中标 [Opus 复算]。
- Opus 引用的先验 (GDF Ye 1998, Tibshirani 2015 search df, OMP 差异原则, Luxar) 为其记忆/已有 G0, 未检索, 不得作新颖性依据。
- 处置: 采纳 Q4 的 1-7 全部更正 (见 FAIL-0013 附记、DECISIONS、负结果记录 v2)。
