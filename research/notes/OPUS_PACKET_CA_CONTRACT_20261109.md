# Opus 科学门审查包: CA 合同候选 v0 (JR 失败的独立因果归因) — 只读审查 (runlog 20261109T044837Z-model-call-dd02)

请只读审查: 不写文件、不运行实验、不读/生成任何 CONFIRM 图 (811–826) 或 VERIFY2 (701–712)。回复请先自报模型, 再列出实际读过的文件, 然后逐问给判词 (PASS / PASS-WITH-CHANGES / BLOCK), 并给出可执行的阻断修改清单 (编号 R1.. )。

## 背景 (均可在 D:/Gaussian 核对)
- 真人最新授权 (经 Codex 转交原话, memory/AUTHORIZATIONS.md 末尾): 首节点用全新 CPU 小图做独立失败归因合同: 无噪/有噪 × 同 K 可精确表示/有表示误差, 配对控制并测真实组级有限歧义; 真实 Opus 审合同、对照、判据和数据隔离后冻结并运行; 每个原因区分证据、推测和未排除项; JR 原 STOP 与旧确认边界保留, 不重跑旧 VERIFY, 不降画质或强基线标准。总目标 P1817 不变。
- 待归因观测: JR 终态 STOP (memory/FAILURES.md FAIL-0035; 你已审过): OBS-J 的 Q-AUC 23.54 dB 低于 RND-J 24.40 / OBS-I 24.00 / IND1 23.82, 但 F 口径更好; 所有臂 PSNR 先升后降。
- 合同候选: contracts/CA_CONTRACT_CANDIDATE_v0.md (全文, 请先读 §2 设计、§6 统计、§7 判定表、§4 数据边界、§8 证据层级与未排除项、§9 E-B)。近邻读取深度: research/notes/G0_reading_log_CA_20261109.md (只有 BUQO 全文读过, 其余已如实标为摘要/经 Codex)。
- 代码: src/ca_gen.py (评测侧生成/K 拟合/闸门)、src/ca_diag.py、experiments/ca_run.py、ca_reduce.py (含判定函数 verdict())、ca_diag_run.py、ca_freeze_check.py; tests/test_ca.py (14 项过); 复用 src/jr_core.py、jr_op.py (JR 冻结版 sha 1f369045…/406ee2c8…)、geo_core.py。
- 开发期证据 (DEV 801–808 / SMOKE 890–892 / CAL 851–870; 全部不是证据, 见合同 §15): 
  * DEV 先导块 P (801–808: 2 lo + 6 hi; 640 次运行, 全部 stop=cap; outputs/CA/dev_REDUCE_P.txt/.json, 原始 JSON 640 个在 outputs/CA/dev/runs): OBS-J−RND-J 的 Q-AUC 缺口 (dB): 无噪 R0 +0.13 / R1 −0.02; 有噪 R0 −0.38 / R1 −0.44 (n=8 下标签: E / I / I / D); N_effect −0.47 [−0.59,−0.36], 8/8 图为负; R_effect −0.11; 交互 +0.09 (SD 0.39)。OBS-J−IND1 四格皆负 (−0.29/−0.24/−0.46/−0.33)。分解对 RND-J−IND1: 无噪 −0.42/−0.43, 有噪 +0.15/+0.11。机制诊断 (关联): OBS-J 终点 PSNR 在有噪格比 RND-J 低 0.58–0.67 dB 而峰值仅低 0.07–0.13; nf 差仅 +0.011/+0.015。无噪格峰值≈终点 (预算受限)。
  * 先导 SD → n=16 的 MDE80 ≈ N 0.13、R 0.12、交互 0.24、单格 ≈0.25 dB; 墙钟 640 次 63 min (2 核), 全规模 P+S ≈ 3.5 h。
  * 先导促成的规则细节改动 (均在 CONFIRM 之前; 阈值/n/对照集未依据先导方向调整): V-NONE 改为四格全 E; 增分解对与匹配报告; 实例级合并仅取正权重对 (一次崩溃: 带符号权重对矩匹配协方差非正定, 已修并加单测)。
  * E-B 设计表 (outputs/CA/EB_design.txt): 432 个线对中仅 16 个歧义 (AG 15, MO 1, G15/DK 0); 断续边 80 对 0; 纹理取向对 7/48 (AG 6); 参数重排对照 D_img=d=0; Φ(−d/2) 与 MC 一致。实例级合并负荷 (DEV R0 真值) AG 最多 (如 8/84)。
  * hi 层生成器曾调难 (初版 K=36 表示 PSNR 35–40 dB → 现中位≈31 dB, 范围≈25–39 dB; 依据 CAL 851–870 与 DEV 的拟合 PSNR, 未看方法结果)。

## 请你判 (每问先给 PASS/PASS-WITH-CHANGES/BLOCK)
Q1 **因果识别**: R0 = 锐利 tile 的 K=36 Gaussian 投影 (逐元精确可表示), R1 = 锐利 tile (有表示误差, psnr_rep 报告), 噪声 ε 在 R0/R1 间共享, 无噪格保留同一数值尺度 SN 与同一 a=1e-3/SN²。这个 2×2 能否把 "噪声" 与 "表示误差" 两个因子分开? U3 混杂 (R0 比 R1 平滑, 边宽/高频含量也变) 是否使表示因子不可解释, 需要怎样的补充匹配或降级措辞? K 拟合是上界估计 (非凸), 影响是否可接受?
Q2 **对照与臂**: 主对照 RND-J 加并列次对照 IND1/OBS-I/SPA-J、分解对 (RND-J−IND1 等)、块 S (JR 调参配置) 与可选块 X (10× 预算) 是否足以区分 N / R / OPT / CFG? 是否缺关键对照 (如 OBS0-J、OVL-J、带早停的 IND1)? 共同固定配置 (κ0=0.1, gs=2) 是否构成不公平 (应否设 κ0 小网格)?
Q3 **判据与统计**: δ_D=0.25 dB、BCa 单侧 95% 上下界、D/E/I 标签、判定表优先级、STRONG 规则 (规则要求非 D 的格都须标 E)、多重性处理 (不做逐格校正, 披露联合假阳性)、n=16 基底图、MDE80 的使用是否站得住? V-OPT 在无噪格因预算受限而出现时的解释是否合适? V-INS 是否过保守 (例如 n0=D 而 n1=I)?
Q4 **数据隔离**: 闸门 (行首匹配、分析器/模块 sha 登记含 as_gen/geo_core/geo_flops、CONSUMED/RESUME_OK、冻结前在记录副本上演练)、CAL 851–870 与 DEV 的使用、hi 层生成器参数是依据 K 拟合 PSNR 而非方法结果调整的 (§15) —— 是否构成对 CONFIRM 的泄漏或自由度? CONFIRM 全为 hi 层且 psnr_rep 范围 ≈25–39 dB 是否可接受?
Q5 **E-B 诊断**: 定义 (D_img、d、Φ(−d/2)、rel≥0.15 且 d≤3)、规范方向剔除、固定邻居 vs 邻居重拟合、线性 vs 有限、实例级合并负荷 (探索性) 是否正确, 解读限制是否充分? 它不进入判定, 这一安排是否合适?
Q6 **INR 参考与桥接设计 (§10, 本节点不运行)** 是否不弱化对照, 缺什么?
Q7 **预算/运行**: 块 P 1280 + 块 S 768 次运行 (约 3–4 CPU·h, 2 核), P→S 同进程一次闸门消耗、K 拟合并行缓存、续跑规则、X 块是否进入冻结范围。
Q8 其他阻断或你认为必须在冻结前改的地方; 以及你认为我最可能犯的未被察觉的错误 (请直接指出)。
