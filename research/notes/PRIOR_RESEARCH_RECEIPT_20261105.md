# 前期调研接收回执 (prior-research receipt)
作者: Sonnet5.5 (配置id claude-sonnet-5-5; 实际服务模型以 run 记录为准) | run: 20261105T074518Z-infra-0001 | 2026-11-05T07:55:19Z
性质: 回执 = 我读了什么、读到什么程度、据此接受/不接受什么。不是 G0 完成, 不是新颖性结论, 不含任何新实验。

## 1. 阅读分级 (三类不混用)
**A. 本地文档, 我用 cat 读了全文 (逐行读过, 但它们本身是二手转述):**
- 5 份补迁原始审查 archive/legacy-reviews/: claude-opus-phd-review-v1.md, claude-opus-phd-review-v2.md, claude-opus-original-preflight.md, codex-integrated-review.md, codex-original-preflight.md (import-manifest.json 源/目标 sha256 逐条一致)
- research/P1817_PHD_NOVELTY_FEASIBILITY_20261105_ZH.md, P1817_PHD_PRIMARY_SOURCE_DIGEST, RABBIT_P1817_PHD_AUDIT, LITERATURE_COLLISION_AUDIT_20261104, P1817_HOLDOUT_BIRTH_PILOT_CONTRACT, P1817_PILOT_AMENDMENT, P1817_REPAIR_LOG, P1817_CODE_MAP, CODEX_READONLY_HANDOFF_AUDIT, archive/theory/P1817.md, memory/SYNC_GAPS_ZH.md
- (v1/v2 与 digest/RABBIT/collision 在本会话压缩前读全文; 本次对 v1 头部、v2 全文、feasibility 头部做了复核)
**B. 一手论文, 工具摘要级 (WebFetch 小模型转述, 非逐行精读):** Image-GS, GaussianImage++, Tibshirani 1402.1920(摘要+部分), Ramani/Blu/Unser MC-SURE, VGNC, SUGAR, Noise2Self。仅摘要: LocoADC, AIR, SAD(SAD 是 SoftAnisotropicDiagrams, 不是高斯方法)。Opus 两轮自述的一手阅读同样是 WebFetch 摘要转述, 且 v2 的检索摘要含辅助 Haiku (见 FEASIBILITY 文)。
**C. 未读/被拦 (线索, 不得当作已核验):** Jo/Chun/Choi ICCV2021 (arXiv 限流), Ye 1998 GDF (付费墙), Efron 2004, Friedman 1991 MARS/GCV, Feng/Kao 2602.09415 附录 H (v2 也未读到), Jia 2607.05522 / PUP / Papantonakis / FisherRF (仅协调者先前读过, 我未重读), DIP-SURE 原文, Metzler 2018。
(所有 B/C 级条目在 G0_reading_log_20261105.md 逐条记状态; 该文件只追加, 不覆盖。)

## 2. 当前主线 (待验证问题, 非已观测缺陷)
"自适应2D高斯生长中的搜索风险估计与校正": 在相同最终 K 与相同优化/总墙钟预算下, 候选搜索 (birth 提案/选择、几何冻结) 是否引入超出参数个数的额外拟合风险 (搜索自由度)? 若有, 能否不看干净图地估计并校正, 使 birth/冻结/停止决策在含搜索与探针开销的等总预算下优于 固定K、残差birth、全局K留出/盲点校准(Luxar式)、直接移植的全流程 MC-SURE/DIP-DF?
Opus v2 的结论我接受并沿用: 目前**不是**三项独立博士贡献, 只有一个可能新颖、未证实的首贡献 (A) + 两个条件分支 (B 几何解锁可识别性理论, C 值域内校准); 三者共享机制, 拆分是凑数。

## 3. 最近邻与强基线 (G0.3 要逐条给方法级差异)
Image-GS / GaussianImage++ (残差驱动 birth); Luxar (盲点高斯数标定, 区域预算); VGNC (验证引导高斯数控制); Noise2Self (J-不变); Kim/Fridovich-Keil (GS 逆问题对比); Tibshirani 2015 search df (best subset, 不连续 Stein 推广); Ramani MC-SURE / SUGAR (黑盒有限差分散度, 非光滑); Ye 1998 GDF (未读, 全流程数据扰动 df, 很可能是"全流程MC扰动"的经典前身); Jo 2021 / DIP-SURE (单图自由度早停); Jia NIW Bayesian GS (复杂度决策最近竞争者, 须当基线); PUP/FisherRF (3D, 决策对象不同); Feng/Kao (算子级稳定性, 仅加性无A); Papantonakis (逐高斯SH自适应)。
我的判断 (预备): "搜索要付自由度"、"黑盒扰动估风险"、"全流程扰动估 df"都是经典; 本项目只可能新在 (a) 对 birth 不连续真正有效的估计/校正或显著更便宜的算法, (b) 实质的适用/失败边界。

## 4. 反证与停止条件 (先于实验写下)
- F0: 若朴素估计 (参数个数/冻结拓扑近似/全流程 MC-SURE) 已落在 oracle 协方差 df 的 MC 误差内 -> 首贡献核心不存在, 立即停止并报告, 不声称新校正。
- 全流程 MC-SURE 本身是已有方法, 必须作强基线; 若直接移植同样有效 -> 缩小声明。
- 不连续 (top-K/硬选择) 下 MC-SURE 随 eps->0 方差爆炸; 随机化后 Stein 引理是否成立 = 未验证。
- 搜索偏差若小到不影响决策 (H3 不成立) -> 无 GPU 理由。
- 所有阈值/倍数 (如 1.5–2x CRB、s^2/d 过渡宽度) 是 Opus 的建议, **不是合同**; 须在 F0 合同中冻结。

## 5. 数据与证据边界
- 唯一"结果": 合成 192x192 K512 5000步 Image-GS: 噪声输入 20.339398 dB, 拟合 29.135178 dB (vs 干净), clean-fit 48.147683 dB, upstream 03088368d42684fb54225c981cfd94b58cc0393a; 仅开发、历史导入, 不作证据。
- 旧 holdout-birth 草稿 NO LAUNCH: Codex 8 项 P1/P2 阻断 (GPU 排他锁位于调用方目录/无空闲检查; 复现性检查过晚; invariance 证据未绑定实际 holdout; prefix/RNG 校验不足; 数据/实现 provenance 未绑评测; 非有限值被 clamp 掩盖; 总时间低估; 输出保留在评测之后) + Opus preflight 7 阻断 + 问题 A–F (C 值在训练器内存、invariance 无法分离泄漏与 GPU atomicAdd 噪声、配对池需 fork 而非共享 seed、scorer 局限、选择后 B 噪声 MSE 有偏、未来图像模糊混折)。61 个 CPU 测试为历史, 未被本项目接受; 旧 WSL 环境/源码仅为指针, 不是本项目环境。
- 这些阻断对新 F0 合同的可迁移教训 (写进合同要求): 共享设备锁与独立于输出目录; 非有限值先于 clamp/更新拒绝; 总墙钟含全部阶段与落盘; 评测器绑定实际输入/产物哈希; 输出目录先原子预留再评测; 测试/干净数据不进入拟合器内存; 配对用 fork 前缀而非共享 seed; 同输入重复得到噪声底 (floor) 才能判断差异。
- P1901 no-go 与 FATE 不接入; 未触碰任何测试数据; 无 GPU 作业。
- 玩具演示 (theory/P1817.md, 非高斯): 21 候选用 B 选, 表观 B 增益 +0.06342 而独立 C 增益 -0.06099、干净 -0.05937 — 只说明选择乐观性, 与 F0 前提同向, 不是高斯去噪结果。
- 模型来源: Opus 两轮报告自述 claude-opus-5-5; 我未独立验证其服务模型。本项目新的 Opus 门必须经 Agent(model=opus) 真实调用并记录实际模型, 不得由我替写。

## 6. 回执后立即执行
1) 合并 Codex 07:50 同步内容到 STATE/NEXT/INDEX/CHECKLIST/PLAN; 2) 追加时间更正; 3) 检查 pump v2 心跳; 4) G0.3 缺口陈述。
