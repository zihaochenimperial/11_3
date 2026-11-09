# P1817 博士级原创性审查（Claude 只读审查，不授权任何实验）

**作者/模型**：Claude Opus 5.5（`claude-opus-5-5`），运行在 Claude Code 中。**范围**：只做文献核验、理论推导和实验设计。没有改代码，没有跑 GPU，也没有写文件（本会话没有写权限）。本报告应保存到 `runs/claude_research/<run_id>/`。

## 0. 执行失败（先说明）

- **WebSearch 和 WebFetch 都被权限拒绝**（don't-ask 模式），所以本会话**一篇论文原文都没读到**。提示要求核验的条目全部没有完成。
- `research/RABBIT_P1817_PHD_AUDIT_20261105.md` **不存在**，ResearchRabbit 的记录无法使用。
- 因此下面的新颖性判断都只是**有条件判断**，不能当作文献结论。下一步必须把核验交给能联网的会话（例如按 AGENTS.md 回退到 Codex Terra/Sol high），或者由用户开放 WebFetch 后重跑。

## (a) 文献状态：分清已核验、未核验和不可得

| 条目 | 状态 |
|---|---|
| Image-GS [2407.01866](https://arxiv.org/html/2407.01866v2)、GaussianImage++ [2512.19108](https://arxiv.org/html/2512.19108v2)、SAD [2604.21984](https://arxiv.org/html/2604.21984v2)、[Luxar](https://github.com/royerlab/luxar/blob/318eee294ac9909cf27ca12670022455bb7b5de8/docs/tutorials/gaussian_splatting.rst#L315)、[Noise2Self](https://proceedings.mlr.press/v97/batson19a.html)、Kim/Fridovich-Keil [2506.11139](https://arxiv.org/html/2506.11139v3) | 2026-11-04 由 Codex Sol 按原文核验过（`research/LITERATURE_COLLISION_AUDIT_20261104.md`），**本次没有重读** |
| LocoADC 2607.17896、Rendering-Aware Bayesian 3DGS 2607.05522 | 晚于我的知识截止日（2026-06），网络又不可用：**完全不可得**，不能对内容做任何判断 |
| AIR 2605.20820 | 本次没有读到，我也无法可靠回忆其内容：**不可得** |
| *Stability and Concentration in Nonlinear Inverse Problems with Block-Structured Parameters…Gaussian Splatting* | **没有找到原始记录**。从标题看，它可能直接占据贡献 1 的定理空间，**投入理论工作前必须先读完** |
| FisherRF（Jiang 等，ECCV 2024）、PUP-3DGS（基于 Fisher/Hessian 的剪枝）、Taming 3DGS（预算化增密）、Bayes' Rays、Modeling Uncertainty for GS | 只是记忆里的线索，arXiv 号和内容都没核验 |
| 经典文献：Stein 1981 SURE；Ramani–Blu–Unser 2008 MC-SURE；Eldar 2009 GSURE；Ye 1998 / Efron 2004 自由度；Tibshirani 2015 "Degrees of freedom and model search"；Rothenberg 1971 可识别性；Shahram–Milanfar 2004 分辨极限统计分析；GCV / Morozov 差异原则 | 只是记忆线索，没有核验 |

## (b)(c) 三个贡献：最强反对意见、仍然成立的差异、可操作的表述

**本地事实（已读代码）**：试点配置为 `topk=10`、`disable_topk_norm=False`（`scripts/p1817_holdout_birth_pilot.py:338-339`），也就是做归一化 top-K 混合：x(p)=Σπ_k(p)c_k，其中 π_k=w_k/Σw。

### 贡献 1：针对 Gaussian、考虑算子的可识别性

- **最强反对意见**：F=JᵀAᵀΣ⁻¹AJ 就是 Gauss-Newton/Fisher 矩阵。用 Fisher 秩判断局部可识别性是经典结果（Rothenberg）。斑点和边缘在模糊下的定位 CRB 也属于经典超分辨统计（Shahram–Milanfar 一类）。如果那篇 Block-Structured 论文确实给出了 GS 的稳定性和可识别性，这一条基本就被占了。
- **可能仍然成立的差异（我自己的推导，未经独立审查）**：在归一化混合下，∂x(p)/∂μ_i = π_i(p)·(c_i−x(p))·Σ_i⁻¹(p−μ_i)。
  - 由此，几何方向的 Fisher 块与颜色对比度 ‖c_i−c_j‖² 成正比，并且只集中在软边界上：π_i≈1 或 ≈0 的地方，几何信息为零。
  - 颜色方向的 Jacobian 恒为 π_i，几乎总能识别。
  - 两个中心距离为 d、尺度为 s 的 Gaussian 之间，过渡宽度约为 s²/d。当这个宽度远小于模糊宽度 b 时，尺度（锐度）方向就不可识别。
  - **注意**：Gaussian 模糊下 Σ+B 的闭式只对非归一化的加性 splat 成立。Image-GS 是先归一化再成像，所以必须数值验证。
- **可操作的表述**：对每个 Gaussian 算一个分块 Fisher 估计器，预测哪些方向（颜色/位置/尺度）在给定的 A 和 σ 下的 CRB 超过阈值。
- **失败条件**：
  - 高信噪比下，经验参数协方差和 CRB 的比值偏离超过约 1.5–2 倍；
  - 可识别性的排序预测错误；
  - top-K 截断带来的不可微主导了结果；
  - 已有文献已经给出等价结论。
- **判断**：单独成篇偏弱，更适合作为贡献 2 的"度量工具"。

### 贡献 2：在运行时间预算下联合决定 birth、几何冻结和复杂度

- **最强反对意见**：
  - 按残差或梯度 birth 已经被 Image-GS、GaussianImage++、SAD 和 3DGS ADC 占据；
  - 按 Fisher 敏感度剪枝（PUP-3DGS 线索）和预算化增密（Taming 线索）可能已经存在；
  - 用 Luxar 的 blind-spot 做区域预算校准已经核验存在；
  - "残差下降大于 2σ²×自由度"就是 Cp/SURE。
  - 把这些模块拼在一起不算贡献。
- **更锐利、可能仍然成立的差异**：用局部自由度当作 birth/冻结的"货币"，并**修正搜索乐观偏差**。
  - 线性化后，df ≈ tr(AJ(F+λI)⁻¹JᵀAᵀΣ⁻¹) = Σψ_k/(ψ_k+λ)，ψ_k 是 F 的特征值。所以贡献 1 中"可识别方向"的个数，正好就是 SURE 中的复杂度代价。这一点把贡献 1 和贡献 2 连成了同一个机制。
  - 真正非平凡的部分是：从 256 个候选里贪心选 64 个，这个搜索本身会带来乐观偏差（Tibshirani 所说的 search df），最终模型的 df 反映不出来。`theory/P1817.md` 里的玩具实验已经显示了这种偏差。
  - 可以用随机化 birth 让散度在期望意义下有定义，再用 MC-SURE 估计整条流水线（含选择）的散度。
  - 然后在同一表示内比较"全部像素 + SURE（需要 σ）"和"留出像素 + holdout（不需要 σ，但损失 1/3 数据）"。
- **失败条件**：
  - 线性化 df 和 MC 散度差异很大；
  - 离散选择让 Stein 引理失效，而随机化也修不好；
  - SURE 或 holdout 相比全局最优 K 没有可重复的余量。

### 贡献 3：校准可靠性（区分观测支持的不确定性和零空间效应）

- **最强反对意见**：
  - 值域/零空间分解是线性代数常识；
  - GSURE 本来就只能估计值域上的风险；
  - Laplace/Fisher 不确定性已经用在 GS 和 NeRF 上（FisherRF、Bayes' Rays 线索）；
  - 成像领域的 conformal 方法已经存在（线索）。
- **关键限制**：零空间误差（例如超分辨率的高频部分）在单张图内**没有任何数据能校准**，必须有总体先验或一个外部图像集。所以"校准的零空间可靠性"在单图设定下不可能实现。
- **可以收窄成**：仅针对去噪，用 blind-spot 折上的残差做局部（Mondrian）conformal 区间；零空间部分只标记，不声称校准。
- **失败条件**：像素在空间上不可交换，导致分区域覆盖率偏离名义值。

## (d) 最便宜又有决定性的实验（目前都还只是设计，都需要另写冻结合同）

1. **E0 合成实验（只用 CPU）**：
   - 用 torch 在 CPU 上重写归一化 top-K 渲染器，规模 64²、K≤50。之后要和 CUDA 渲染器做一次一致性 smoke。
   - 网格：A ∈ {I、模糊 b=1/2/3px、×2/×4 box 下采样}，对比度 0.05–0.5，σ ∈ {5,15,25,50}/255，每格 200 次噪声抽样。
   - 检验 CRB 和"几何信息与对比度平方成正比、尺度坍塌"这两条预测。
   - 这一步决定贡献 1 保留还是降为启发式。
2. **E1 df 估计器验证**：
   - 3 张合成图 + 4 张自然图开发 crop（128²），K ∈ {64…512}，3 个 seed。
   - 比较线性化 df、MC-SURE 和 Efron 协方差 oracle df（干净图只给评测器用）。
   - 通过门槛：SURE 对 K 的秩相关 ≥0.9，并且选出的 K 和 oracle 相差不超过一格。达不到就停。
3. **E2 决策实验（8GB GPU）**：
   - 在匹配最终 K 和匹配墙钟时间下比较这些臂：上游残差 birth、固定 K、holdout 选全局 K（Luxar 式）、SURE 选全局 K、局部 holdout 门控（现有试点）、df 门控的 birth + 冻结。
   - 经典基线：BM3D（σ 已知和估计两种）、λ 由 SURE 选的 TV、TV-grid（Kim/Fridovich-Keil）。BM3D 只作为上限参照，结论不建立在超过 BM3D 上。
   - 开发集：8 张 256² 自然 crop，σ=25。测试集：Kodak24 或 CBSD68，未触碰，σ 15/25/50，3 个噪声 seed × 3 个优化 seed，冻结后只跑一次。
   - 去噪通过后，才扩展到模糊（b=1.6）和 ×2 超分辨率。
   - 主对比：提出的方法对 {holdout 全局 K, SURE 全局 K} 中较好者，按图配对，报告 bootstrap CI。

## (e) 三个层次分开看

| | 代码能否实现 | 得到正结果的可能性 | 博士级意义 |
|---|---|---|---|
| 贡献 1 | 高（autograd 分块 Fisher 很便宜） | 中（推导需要 E0 验证） | 低到中，取决于 Block-Structured 那篇论文 |
| 贡献 2 | 中（MC-SURE 让时间翻倍，随机化 birth 需要设计） | 不确定：Image-GS 在一张简单合成图上只有 29.1 dB（`research/P1817_LOCAL_FIT_20261104.md`），相对全局 K 的余量尚未测过 | 中到高：搜索乐观偏差修正适用于任何会增长的原语表示 |
| 贡献 3 | 中 | 只在去噪值域部分可能成立 | 低到中；零空间校准在单图设定下不可行 |

## (f) 排序

1. **第一篇论文（现实可行）**：贡献 1+2 合并为"自适应 Gaussian 表示的风险核算：SURE/GSURE 对 blind-spot，并修正搜索乐观偏差"，先做去噪，再做模糊。
2. **条件分支 A**：归一化混合的可识别性理论加几何冻结规则。前提是 E0 通过，并且 Block-Structured 论文没有覆盖这部分。
3. **条件分支 B**：去噪值域上的 conformal 可靠性。前提是 E1 的 df 估计准确。
4. **转向分支**：如果相对全局 K 没有余量，就写一篇"噪声逆问题中自适应密度控制何时有用"的负结果/基准论文。

**结论**：目前是一个机制的三个侧面，不是三篇独立的原创论文，不应该硬拆成三篇。

## (g) 显存估计（只是假设，没有测量）

- 192²、K=512 已经在 8GB 上跑通（未测 VRAM；1.6GB 是 CPU RSS）。
- 256²–768×512、K ≤ 1e4、每个 Gaussian 9×9 的分块 Fisher，加上 Hutchinson 探针：我估计 **8GB 足够**。
- 应避免稠密的全 Fisher：K=2000 时约 1.3GB，还会继续增长；也应避免像素×参数的稠密 Jacobian。
- 24–36GB 只在批量多 seed 或大图时才需要，不是必需。

## 决定与下一步

- 本次审查不改变 P1817 的 **NO LAUNCH** 状态，也不授权 E0–E2。
- 下一步分两件事：
  1. 用能联网的路由，核验 Block-Structured、LocoADC、AIR、2607.05522、FisherRF、PUP-3DGS 和 Tibshirani 2015 的原文。
  2. 如果核验后仍然成立，为 E0（只用 CPU）单独写一份冻结合同，并安排独立审查。现有的 holdout-birth 试点继续按原修复和审查流程推进。
