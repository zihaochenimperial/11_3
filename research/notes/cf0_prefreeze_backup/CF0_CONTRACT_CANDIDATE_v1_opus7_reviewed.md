# CF0 合同候选 v1 (位置轴实证边界研究; 未冻结; 冻结前需真实 Opus round 7 通过)
作者: Sonnet5.5 (run 20261105T175811Z-session-6e38)。依据: 真人 2026-11-05 17:57 London 批准新主线; G0 research/nearest_work/G0_CF_BIRTH_NEAREST_WORK_20261105.md; 设计说明 research/notes/CF_BIRTH_DESIGN_20261105.md (v1, 已被 Opus round 6 判 REVISE; 原文 research/notes/OPUS_REVIEW_CF0_DESIGN_20261105.md); 本合同吸收其硬要求 1-10 (对照见 research/notes/CF0_RESPONSE_TO_OPUS6_20261105.md)。
冻结方式: 通过后 `cp CF0_CONTRACT_CANDIDATE.md CF0_CONTRACT.md` 并写 CF0_CONTRACT.sha256; runner 拒绝在哈希不符时运行。冻结后任何偏离 = 偏差条目 (FAILURES.md) + 再审。

## 0. 边界声明
- 这是**玩具 64x64 合成图上的实证边界研究**, 不是方法声明。0 个已验证创新; 不保证原创性或分数; 任何 GO 仅表示"值得写确认合同并在未触碰图像上再测", 不是有效性/原创结论。
- 最近先验 (均未声称新): honest trees/forests 的"分割位置与叶值分别用不同子样本"(Athey-Imbens; Wager-Athey [记忆+摘要页未见 honest 字样]); data fission §6.1 (结点选自 f(Y), 在 g(Y) 上回归; 摘要级已读); Wasserman-Roeder 三段分裂 (摘要级已读); Tian-Taylor 随机化响应选择 (摘要级已读; 本文 NS 臂); RandOMP 随机化贪心+平均 (摘要级已读; 本文 RAWens2 臂); DML cross-fitting (记忆)。**命名**: XFER = honest 位置转移 (样本分裂); 仅 XAVG (角色互换并平均) 才对应 DML 意义的交叉拟合。
- 机制陈述 (如实): 贪心 birth 的"位置"只是新 Gaussian 的**初始位置**; 之后 xy 经每阶段 150 步 Adam 自由优化, 因此位置选择偏倚只通过起点/吸引盆作用; 大部分过拟合来自 K=48 的自由参数 (K 轴)。故 K 轴基线 (RAWcv) 与"近随机 births"(RANDy) 是门内竞争者。

## 1. 管线 (不变量; 与 F3 冻结管线一致)
H=W=64, N=4096, sigma0=0.08, K0=24, 3 轮 x 8 births, 每阶段 150 步 Adam (lr: xy 5e-3, logscale 2e-2, rot 2e-2, val 5e-2), 候选 = ω 置换前 S 个像素, S=1024 (RANDy: S=8, 即无选择), 分数 = 高斯平滑(1.5px)|y_fit - f|, 新 Gaussian 尺度 2px、初值 f + 平滑残差 (取自**拟合所用数据**)。实现: src/gsfast.py (冻结文件, 不改) + src/cf_fit.py (新, 轨迹快照/强制 births; 测试证明 R=3 快照与 gsfast.fit_pipeline 逐位相等)。float64, 无裁剪。

## 2. 臂 (每个 (图 k, 抽样 m) 单位; 共同随机数 CRN: 同一 e, z, ω1(ω2 仅用于 RAWy2); 所有臂共享)
y = x + e, e~N(0, s0^2 I); z~N(0, s0^2 I) 独立; 副本 y_f(tau) = y + tau z (选择副本, 噪声方差 s0^2 (1+tau^2)), y_g(tau) = y - z/tau (拟合副本, 噪声 s0^2 (1+tau^-2)); 两副本独立 (Gaussian fission, Leiner 等 §2.2)。tau in {1,2,4}。
基础臂 (sigma0, 全信息): RAWy = 在 y 上用 y 自身残差选位置 (K=48, R=3); RAWy_R0..R4 = 同一轨迹各阶段快照 (K=24..56); RANDy (S=8); RAWy2 (第二 ω) 与 RAWens2 = 1/2 (RAWy + RAWy2) (渲染平均, K=96, 等成本集成对照)。
副本臂: RAWg(tau)/RAWf(tau) = 在 y_g / y_f 上用各自残差选位置 (等噪声对照); XFERg(tau) = 位置 B_f 取自在 y_f 上跑完整贪心生长得到的 births, 在 y_g 上以 forced_idx 拟合 (birth 初值只用 y_g); NS(tau) = 位置 B_f, 在**完整 y** 上拟合 (随机化选择; 与 y 部分相关 corr=1/sqrt(1+tau^2), 无信息损失); 仅 tau=1: XFERf (位置 B_g, 在 y_f 上拟合), XAVG(1) = 1/2 (XFERg + XFERf) 渲染平均 (K=96), XAVGctrl(1) = 1/2 (RAWg + RAWf) (同样用两副本且同样 K=96 平均、但位置来自各自数据 = "仅位置来源不同"的匹配对照)。
K 轴基线: fission-CV (tau=1 固定, 两方向): cv_R = 1/2 (||f_R^g - y_f||^2 + ||f_R^f - y_g||^2), R in 0..4; R*cv = argmin (逐单元); RAWcv = RAWy_R{R*cv} (在 y 上生长到 R*)。**警告 (已声明)**: CV 在噪声 (1+tau^-2)s0^2 的副本上校准, 却用于 s0^2 的拟合; tau 固定为 1 以免被被测臂调参。RAWoracleR (评测器选最优 R) 仅作不可实现上界报告。
成本 (拟合当量; 单阶段 150 步=1 步长单位, 轨迹 R<=4 记 1.25): 每单元约 17.75; 总成本与 K 随臂报告 (RAW 系 K=48; 集成/平均臂 K=96, 成本 >=2 拟合)。数据损失用 (1+tau^-2) 方差因子报告。

## 3. 数据与种子 (拟冻结)
- 图: E_k, k=15..18 为 pilot (4 张, 每型含; 仅验有效性/成本/配对 SD, **不入证据, 风险差在分析器中被屏蔽**); k=21..38 为开发集 (18 张, 每型 6; 型=TYPES[(k-1)%3], 生成 synth.make_clean(type, 3000+k)); k=41..58 为确认集, **本合同下不得生成/查看** (runner 对 k 范围断言)。与 F3 的 E1-E14/W0/W1 零重叠。
- ENTROPY=20261107; 流: e 键 (21, 100+k, m); z 键 (23, 100+k, m); ω 键 (22, 100+k, m, 0|1); bootstrap 键 (24, 0)。
- 评测: risk = sum_i (f_i - x_i)^2, 仅 runner 在合成/评分处使用干净图; 拟合器只收到 (y 副本, ω, S, cfg, forced_idx)。分析器只读风险表。
- Worker 数固定 6; 墙钟上限 3 h (runner cap_seconds=10800)。

## 4. 估计量 (冻结)
NU(A vs B)_i = (mean_m risk_B,i - mean_m risk_A,i) / mean_m risk_B,i (每图相对差, 先对抽样取均值); pooled NU = 图间等权均值; **不使用风险比的合并均值**。CI = 对图做 bootstrap (B=2000, 键 (24,0)), 百分位法。

## 5. 候选与竞争者 (家族 4 个候选)
| 候选 A | 竞争者集合 C(A) |
|---|---|
| XFERg(1) | RAWy, NS(1), RANDy, RAWcv |
| XFERg(2) | RAWy, NS(2), RANDy, RAWcv |
| XFERg(4) | RAWy, NS(4), RANDy, RAWcv |
| XAVG(1) | RAWy, RAWens2, XAVGctrl(1), NS(1), RANDy, RAWcv |

## 6. 判定 (开发集; 先验固定)
有效性闸门 (任一失败 -> INVALID, 记 FAILURES.md, 不解读): V0 合同哈希匹配且非 debug; V1 宿主单测通过且 src/cf_fit.py 哈希与测试报告一致; V2 重放逐位复现 (每图 m=0 全单元重跑, hashes 与 risks 全等); V3 完成且未中止; V4 CRN: ω 键模式正确且 ω1/ω2 共享 (图, m); V5 独立性: 各 tau 的噪声副本经验相关汇总 z<4; V6 墙钟 <=3h; V7 有限性与 RAWy==RAWy_R3。
Pilot (k=15..18, M=8): 只输出有效性、墙钟、各对比的逐图配对 SD (屏蔽任何 NU/风险差)。M_dev = {8,16,32} 中使"所有对比的逐图 SD 中位数 / sqrt(M) <= 1%"的最小者, 否则 32 且标 LIMITED_POWER (pilot 前固定此规则; 此后 M 不再调整)。
GO-dev (候选 A 通过当且仅当): (i) NU(A vs RAWy) >= +2%, 其 bootstrap 下界 (分位 0.0125 = Bonferroni 0.05/4) > 0, 且 >=2/3 的图 NU_i>0 (这等于要求 D1/D2 类基本全胜, D3 类可输); (ii) 对 C(A) 中每个竞争者 c != RAWy: NU(A vs c) 的下界 (同 Bonferroni 分位) > 0; (iii) 对 c=RAWcv 另需点估计 NU >= +1%。任一候选通过 -> GO-dev。
STOP: 对**每个**候选 A, NU(A vs c*(A)) 的单侧 95% bootstrap 上界 < +1%, 其中 c*(A) = C(A) 中使 pooled NU(A vs c) 最小者 (最强竞争者; 全局而非逐图选择)。(任一真实 NU>=1% 的候选使"全部 UB<1%"的概率 <=5%, 故无需多重校正。)
其余 -> INCONCLUSIVE; 允许**一次**扩展: `--stage=dev_ext --M=<同 M>` 追加抽样 m=M..2M-1 (同图), 合并后重判; 仍 INCONCLUSIVE -> 终态 INCONCLUSIVE, 不再升级。
预注册数值预测 (报告, 不改闸门; Opus 与我的先验): NU(XFERg(1) vs RAWy) pooled 在 [-100%, -25%] 内 (拟合噪声方差翻倍); NU(XFERg(4) vs RAWy) 在 D1/D2 上位于 [-10%, +5%], pooled < 0; 我对 GO 的先验概率 ~10% (Opus <15%)。
报告-only 诊断: CF-1 选择效应 (XFERg vs RAWg 等噪声); XFERg vs NS 每个 tau; 信息损失 RAWg vs RAWy; RANDy vs RAWy; RAWcv/oracle-R vs RAWy; RAWens2 vs RAWy; 按型 (D1/D2/D3) 分层; 出生高斯最终位移 (px)、拟合副本在强制位置的残差、|B_f∩B_g| 与 |B_f∩B_y| 重叠; R* 直方图; 每臂 K 与成本。

## 7. 失败与日志规则
所有失败/INVALID/INCONCLUSIVE/中止/基础设施故障当场追加 memory/FAILURES.md (见该文件头); 任何偏离本合同 (含分析器/代码/种子/阈值/M) 在运行前登记, 不得事后调参; 不得把基础设施失败写成科学结论。Pilot 的风险差不得在分析器之外被计算并用于调参; 若发生须登记。
一次 M 扩展之外不得追加抽样; 不得换 tau 网格、不得换图集合、不得用 E1-E14/W0/W1/pilot 图做确认。

## 8. 冻结物与哈希 (冻结时写入): 合同、experiments/cf_run.py、experiments/cf_analyze.py、src/cf_fit.py、tests/test_cf_units.py、tests/test_cf_analyze.py、scripts/run_cf_unit_tests.py。分析器带夹具 (GO/STOP/INCONCLUSIVE/比较者支配/K 轴/pilot 屏蔽/INVALID/确定性), 随合同冻结 (FAIL-0004 教训)。
## 9. 未声称
不声称原创; 不声称真实图像泛化; 不声称 GPU 收益; 不声称交叉拟合有效 (除非 XAVG 通过全部条件, 且仍仅为玩具边界结果)。
