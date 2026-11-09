# RJ 合同 v1 修订 A1 (R25–R29)
提出于调参 (516 次运行, 1.24 CPU·h) 完成之后、任何 eval / oracle 运行之前; 咨询 Opus 5.5: runlog 20261108T134717Z-model-call-bdce, 判词 ACCEPT-A1 + 必改项 R25–R29 (原文 research/notes/OPUS_CONSULT_RJ_A1_20261108.md)。RJ_CONTRACT.md 原文 (sha 876b6114…a35b) 保持不动; 本文件逐条覆盖相应条款。
## A1 (R25)
所有臂、所有阶段的外层上限 200 → 400。动机: 调参后发现 516 次中 90 次因 200 外层上限停止; D 族最佳配置 (Δq 停滞截断 CG, 每次很便宜) 的 4 个删失都停在 200 外层且与目标只差 1.1e-3–7.9e-3, 即删失是外层上限过短的人为产物。选择规则、门限、删失规则 (含 R19)、CPU 上限结构均不变。承认这是在看到调参结果之后提出的 (偏差方向: 使被截断的 "便宜但外层多" 臂更强, SC 更强, 对 Gate O 更严、对 Gate T 更容易判 "确定性即可")。
## R26 (一致性核对)
重跑只针对 stop=max_iter 的 90 次运行 (旧文件移入 outputs/RJ/runs_cap200/ 保留披露); 其余运行在更大上限下逐位不变 (rj_solve 的外层上限仅决定 range 长度; 已用 2 个命中运行重跑核对 trajF/trajW 逐位一致)。另取 2 个被重跑的 max_iter 运行核对 400 上限重跑的前 200 外层与原运行逐位一致 (trajF, trajWsp, trajA), 并记录哪些族的最佳配置因重跑发生变化 (outputs/RJ/tune_REDUCE_cap200.json 为改前, tune_REDUCE.json 为改后)。
## R27 (reuse 维度)
原 C_c{2,4,8}_r1 与 X3、X4 的 reuse 配置因 "cc 预算同样卡住重试 trial" 全部 no_step 死亡 (12/12), 与紧预算完全混杂, reuse 未被有效检验。替换: cfg 新增 cc_first_only (cc 预算只作用于首个 trial, 重试 trial 用 maxcg=400); C 族 = {c∈{2,4,8}, 无 reuse} ∪ {c∈{2,4,8}, reuse, cc_first_only} (C_c*_r1f), X3f、X4f 同样改为 cc_first_only。旧配置的 60 次运行移入 outputs/RJ/runs_failed_reuse/ 作为 "已失败配置" 披露, 不参与选择。每族仍至多 6 配置。
## R28 (CPU 上限)
eval_orc ≤ 6 CPU·h (超限判 INCONCLUSIVE, 不得追加); 其余: 调参 (含 A1 重跑) ≤4.5, eval_det ≤1.5, chk (含 fref_chk) ≤3; 合计 ≤15。
## R29 (披露与读数)
族内选择用 "删失=∞ 的中位数", 删失不超过 5/12 仍可当选; 与 Gate O 的 >10% INCONCLUSIVE 规则口径不同, 二者都已预注册、不再修改。评估阶段报告每个臂 "停于外层上限时与目标的相对差距" (cap_gap_median) 以区分近目标截断与真实失败。Q2: 不加入 A2 (SC 资格≤10% 删失); 400 外层后若 SC 删失仍 >10% 按冻结规则判 INCONCLUSIVE, 同时报告描述性 "Gate O-elig" (门臂@SC 对 "删失≤10% 的最强确定性臂" 的比值, 不入裁决), 之后不得再追加修订。
## 代码变更 (须在任何 eval 运行之前登记新 sha)
src/rj_loop.py (cc_first_only), experiments/rj_run.py (MAXOUT=400, C/X 族), experiments/rj_reduce.py (cap_gap_median, Gate O-elig), tests/test_rj_loop.py (+test_cc_first_only; 10 项通过)。
