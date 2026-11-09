# Opus 科学门包: JR CPU 合同候选 v0 审查 (2026-11-08, runlog 20261108T215538Z-model-call-2985)

提交者: Sonnet 5.5 (主研究/编排)。请作为独立科学门 (Opus 5.5) 审查, 回复开头自报模型名。你不是执行者: 不写代码、不运行实验、不读 confirm 图 321–344 / 401–424 / 601–624 / 701–712 (本阶段从未生成)。全部主张 proposed, 0 已验证贡献, 不保证原创性或分数; CPU/8GB, 无付费。

## 背景
真人 (经 Codex) 在读完 Astra 新决策后回复 "开始完成", 授权新线 JR: 用已知模糊核造成的观测混淆来分组, 做组内有限幅度联合 Gaussian 几何修复 (固定 K, 无出生/合并); 首轮对照 = 按模糊响应分组 vs 空间邻居分组 vs 独立更新+线性投影, 费用全计; 新合同经你审定并冻结后直接跑真实更新的小图对照; 旧 TRN/RJ 不重开。交接文件: runs/codex-monitor/20261108-research-direction-review/{CLAUDE_JOINT_REPAIR_HANDOFF_ZH.md, ASTRA_NEXT_DECISION_ZH.md} (D:\Gaussian)。

## 需要你读的文件 (容器 /home/claude/geo, 同步 D:\Gaussian)
- contracts/JR_CONTRACT_CANDIDATE_v0.md (待审合同, 13 节)
- src/jr_core.py (方法侧引擎: 分组/亲和/联合与独立步/接受判据/费用计数), src/jr_op.py (稀疏已知 PSF 算子), src/jr_gen.py (评测侧生成器与闸门); 复用的冻结件 src/geo_core.py, src/geo_flops.py
- research/notes/G0_reading_log_JR_20261108.md (近邻核对, 含阅读深度声明; 未用 GLM scout)
- outputs/JR/design_smoke/{tables_auc.txt, tables_cost_to_target.txt, diag_groups_ari.txt} (设计冒烟: 590–592×4 核, 未调参, 仅用于定网格/预算)

## 设计冒烟读数 (n=12 题, gs=4, κ0=0.1, 未调参; 合同 §12 已先验记录)
ΔQ-AUC(OBS−X) dB: SPA +0.24±0.17; OBS-I −0.72±0.18; OBS0 −0.03±0.09; RND −0.94±0.10; IND1 −0.88±0.19。O-AUC(OBS−X) (正=OBS 更差): SPA +0.21, IND1 +0.14, RND −0.13, OBS-I −0.19, OBS0 +0.10。OBS vs SPA 分组 ARI≈0.21–0.32, 候选对 630/630, 分组费用≈线性化费用 50%。FULL (冻结接受+夹取) 在 5/12 题 no_step, 仅弱参照。→ 我的先验预期: 正式对照大概率 STOP。

## 请逐条给出判词 (PASS / PASS-WITH-CHANGES / FAIL, 附必改项编号 R1…)
Q1 主指标是否合适? Q-AUC (8 点 log 网格上的 PSNR 均值, 对干净图) 作决策指标, O-AUC (F 间隙) 仅同报。F 与 PSNR 在模型失配区脱钩 (低 F 的联合臂 PSNR 反而更低), 这是否意味着决策应改用别的口径? 有没有更少可被操纵的 "匹配费用" 定义 (网格范围 1e9–3e10、沿用终态、删失)?
Q2 对照集与阈值: 五个 PASS (SPA、OBS-I、RND、IND1 的 δ=0.15 dB, OBS0 的 δ=0.10 dB, LB>0, 核族守卫 −0.10 dB) 是否合理? RND 与 IND1 作为 "必须击败" 的门控对照是否过严/过松? n=12 图 (每图 4 核均值) 的 bootstrap 下界功效如何? 阈值取 Astra 的阶段量级而非功效计算, 是否可接受?
Q3 调参公平: 每臂坐标式调参 (gs∈{2,4,9}@κ0=0.1, 再 κ0∈{0.03,0.3}@最佳 gs; 池化跨核; 调参集 6 图×4 核; 准则=调参集 Q-AUC) 是否对各臂公平? 有无我漏掉的对 OBS 不利的固定选择 (如 agglomeration 的平均连接、脊=1、10% 标定、4σ 候选盒、每 sweep 重分组)? 这些是否应该进调参而不是固定?
Q4 CORRECT-ONCE 规则: 以 "分组免费" 诊断授权唯一修正 (分组复用间隔 R∈{2,4,8}, VERIFY-2 701–712 单次) 是否合理、是否构成事后改规则? 条件 PASS_SPA/RND/OBS0 且免费分组下 PASS_OBS-I/IND1 是否恰当?
Q5 费用口径: 对 SPA/RND/IND1 只计其真实小分组费用而 OBS 计全部 Gram 块/逆平方根/agglomeration, 是否公平? 稀疏算子 2·nnz(A) 的计价与 grp 公式 (jr_core.make_groups 中) 是否有明显偏差? "费用全计" 还缺什么 (如 Jacobian 对所有臂等价是否应计)?
Q6 数据边界与泄漏: jr_gen 闸门、种子标签 (20/21)、调参/核验/VERIFY-2 分离、方法侧不 import 评测侧, 有无漏洞? 设计冒烟 590–592 的使用边界是否足够干净?
Q7 近邻与诚实度: G0 记录的阅读深度声明与新颖性表述 (分组-by-耦合在优化中经典, 本线不主张机制新) 是否够诚实? 有哪些我应当补读/补比的近邻 (如 block-coordinate-descent with overlapping Schwarz, 表征相关性的 Jacobian 聚类, Gauss-Seidel 残差更新)? 区分实验是否足以区分?
Q8 任何阻断冻结的缺陷: 请列出必须在冻结前改的具体项 (合同、代码或单测需求), 其余留作建议。若你认为合同应拆分或先做更小的前置门, 请说明。
