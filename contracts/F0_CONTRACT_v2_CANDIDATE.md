# F0 CPU 合同 v2 (候选, 2026-11-05T08:3xZ, Sonnet5.5) — 逐条落实 Opus 门 round-2 (run 20261105T081922Z-opus-review-d440, ACCEPT-WITH-CHANGES) 的 R1-R9
状态: **候选, 未冻结**。冻结 = (a) 真实 Opus 对"R1-R9 是否被精确落实、解释登记 I1-I10 是否可接受"回一致性确认, (b) 本文件 sha256 写入 contracts/F0_CONTRACT.sha256。冻结后任何改动 = 登记修订 (见 §9), 阈值/判据改动须再次 Opus 审查。历史: v0 contracts/F0_CONTRACT_DRAFT.md, v1 contracts/F0_CONTRACT_DRAFT_v1.md (均保留)。

## 0 范围声明 (先于实验)
sigma0=0.08、K=48、64x64 灰度、加性高斯混合渲染是**玩具**; F0 的阴性/阳性结果都不外推到 Image-GS 规模系统 (归一化 top-k 渲染 + 按误差比例抽样, 选择机制不同)。F0 只判断: 最干净情形下 (a) 搜索自由度 sdf 是否存在并随搜索规模 S 增长, (b) 移植的全管线 MC 散度估计是否已足够。证据级别 = development (合成)。F0 只用开发图 D1-D3 (+ P-lin 专用的 W0/W1); 保留图 TE1-TE3 冻结前不得运行或查看。sdf 是**操作性定义** (见 §3), 不声称满足分段光滑正则条件。

## 1 数据与噪声
64x64, [0,1], 加性白高斯 sigma0=0.08 不裁剪, float64。D1 平滑斑块+边缘, D2 多尺度纹理, D3 分段常数+细线。**W0: x=0 (纯噪声); W1: x=0.1*D1** (仅 P-lin 使用, 弱信号, 见 R3)。T3 水平 sigma'^2 = sigma0^2 + eps^2, eps 网格 {0.01,0.03,0.1,0.3,1.0}*sigma0 (eps=sigma0 时 sigma'=sqrt2*sigma0)。

## 2 管线 P(S) (唯一变量 S) 与控制
- 渲染: 对全部 K 个高斯加性混合 f(p)=sum_k val_k exp(-0.5 d^T Sigma^-1 d) (无 top-k、无归一化)。每高斯参数: 位置2、log尺度2、旋转1、值1。float64。
- P(S): K0=24 随机初始化 (与 y 无关), Adam(lr 位置5e-3 尺度2e-2 旋转2e-2 值5e-2) 150 步; 3 轮 birth (b=8/轮) 各接 150 步; 最终 K=48, 共 600 步。birth 候选: **每轮对 4096 像素取一个随机排列 pi_r (由 omega 决定, 与 S 无关), 候选 = pi_r 的前 S 个** (S 间嵌套; 边缘分布仍是无放回均匀抽样); 分数 = 高斯平滑(1.5px) 后的 |y-f| 在候选处的值, 取 top-b (稳定排序); 新高斯 位置=像素中心, 尺度 2px, 值 = 当前渲染 + 该处**带符号**平滑残差; 重建 Adam。S ∈ {8,16,64,256,1024}; S=b=8 时选择与 y 无关 (零搜索对照)。
- **单一代码路径 (R1)**: `fit_pipeline(y, omega, S, cfg, forced_idx=None)`; forced_idx 给定 = 冻结选择管线 g_I (各轮 birth 位置取外部给定的像素索引, 其余运算与顺序完全相同, 值初始化仍用当前渲染与残差, 即连续依赖 y)。
- omega = (init 流, 每轮排列流), 种子见 §5, **与 S 无关** (R9: 同一 (图, m) 在所有 S 臂共用 omega)。
- N0 (控制): 无 birth, K=48 随机初始化, 600 步。
- **P-lin (线性化正控制, R3)**: 固定字典 **1024 个**各向同性高斯原子 = 16x16 位置网格 x 尺度 {1.5,2.5,4,6}px (列范数归一); 前向逐步回归: 每轮取 omega 排列的前 S 个原子, 按 |<atom, 残差>| 取 top-b=8, 对全部已选原子最小二乘重拟合; 3 轮, 最终 24 原子; S∈{8,...,1024}, S=1024 即全字典。P-lin 图: D1, D2, D3, **W0, W1**。给定 I, 最终拟合 = 在 24 个原子张成空间上的正交投影, 故 df_frozen = 秩 (=24 若原子线性无关); sdf>0 **不是**定理 (Kaufman-Rosset; Janson-Fithian-Hastie), 由 V3 在弱信号臂上实证。

## 3 估计对象
- **df_oracle^rand(S)** (主): M 个独立噪声抽样 e^m (m=0..M-1), y^m=x+e^m, 每个用独立 omega^m; df = (1/(M sigma0^2)) sum_i sum_m (f_i^m - fbar_i) e_i^m, bootstrap SE (B=1000, 对 m 重采样)。
- **df_frozen(S)** (连续散度部分; R1): 对每个 m 记录 I^m (f(y^m;omega^m) 所用的各轮 birth 索引)。(1) **回放**: 用同一 omega^m、同一 I^m 跑 g_{I^m}(y^m; omega^m), 对**每个 m** 断言 与 f(y^m; omega^m) **逐位相等** (全图数组 np.array_equal, 失败即 INVALID); 该回放结果即基项。(2) 扰动: b^m 独立 N(0,I), FD_m = b^T (g_{I^m}(y^m + eps_f b^m; omega^m) - f(y^m; omega^m)) / eps_f。df_frozen = mean_m FD_m。eps_f 候选 {0.003,0.01,0.03}*sigma0, 缺省 0.01*sigma0, 在 pilot 的 R7 检查通过后由修订 A1 冻结 (§9)。
- **sdf(S) := df_oracle^rand(S) - df_frozen(S)** (操作性定义; 对应 Tibshirani 2015 扩展 Stein 公式的跳变/选择项)。S 间对比 (如 sdf(1024)-sdf(8)) 用**同一 m 联合重采样的配对 bootstrap** (噪声流与 omega 流跨 S 共用)。
- **次要估计 (R9) 反对称**: df_anti = (1/M') sum_{m<M'} <f(x+e^m; omega^m) - f(x-e^m; omega^m), e^m>/(2 sigma0^2) (无偏, 抵消仅依赖 omega 的方差), M'=128 (前 128 个样本), 同 omega^m。报告 df_anti 及 sdf_anti, 不入判定。
- df_oracle^fix: >=4 个固定 omega_k (跨 m、S 共用) 各自估计 (128 个噪声抽样), 报告 omega 间散布; MC 对比只与同 omega 的 fix 配对。
- 次要诊断 (非主量, 已被 df_frozen 取代): GN 迹/数值秩 (damping 1e-6); birth 位置稳定性 (跨噪声重抽, 匹配 birth 的优化后位移)。
- **移植 MC (G-b)**: div_hat_j(eps) = b_j^T [f(y+eps b_j; omega) - f(y; omega)] / eps, **omega 每样本重抽, f(y) 与 f(y+eps b) 共用同一 omega** (基项复用主 rand 样本的 (y^m, omega^m)); J 个独立探针取平均 (J=2 => 每样本 2 次额外拟合, 总 3 次拟合/样本)。**sd_1^2(S,eps)** := 所有 (m,j) 单探针 div_hat 的样本方差; **SE_J2** := J=2 平均估计量在 M_mc 个样本上的标准误 (= sd_J2/sqrt(M_mc), 见解释 I2)。
- 参考评测器: 仅 src/reference_eval.py 用 clean; 拟合器 (gsfit/plin) 只接受 (y, omega, S/I, cfg), 不 import synth/reference_eval。

## 4 阶段与算力
- 宿主 18 进程 x 1 torch 线程; **总墙钟上限 4 小时** (pilot 上限 30 分钟); 无 GPU; 超限即停并报告; 输出目录原子预留; 计时覆盖全部阶段含落盘。
- **Stage 0 pilot (~830 次拟合 + P-lin 若干)**: 仅 D1。S∈{8,1024}: 真实管线 M=32 配对样本 (rand 64) + N0 M=32; 回放断言 64 次; **R7: eps_f∈{0.003,0.01,0.03}*sigma0 各做 FD (每样本每 eps_f 1 次, 共 192 次)**; N0 FD 32 次; 反对称 y⁻ 拟合 64 次; MC: eps∈{0.3,1.0}*sigma0, J=2, 臂 {S=8, S=1024, N0} x 32 样本 (384 次)。P-lin (廉价) 在 D1, W0 做**完整 M=256**; V7 做精确 FD。pilot 同时实测单次拟合耗时并外推 Stage 1 墙钟。
- **Stage 1 完整 F0 (~39k 次 float64 拟合, 以 pilot 实测耗时为准)**: 
  - rand: 3 图 x 5 S x M=256 (3840)
  - 回放+扰动 df_frozen: 每 m 2 次 (7680)
  - 反对称: 3 图 x 5 S x 128 (1920)
  - fix 族: 4 omega x 3 图 x 5 S x 128 (7680)
  - 主 MC: 3 图 x 5 S x Mmc=64 x (5 eps x J=2) (9600)
  - **T3 验证 (R5)**: 仅 eps∈{0.3,1.0}*sigma0, S∈{8,256}, 3 图; div_hat 侧 256 样本 (J=1, 复用 rand 基项, 3072) 与 sigma'-重模拟侧 256 样本 (3072); 其余 eps 报告不闸控, 对比直接用 df_oracle^rand
  - N0: 每图 256 (rand + FD, 1536)
  - R6 报告: D1, S∈{8,1024}, 步数 x2, rand+回放+扰动 (M=256, 约 1536 次 x2 耗时)
  - P-lin: D1,D2,D3,W0,W1 x 5S x M=256 (+V7); 廉价, 不计入拟合预算
  Stage 1 仅在 pilot 判定 PROCEED 且 §6 有效性门全过后启动。

## 5 种子与边界
SeedSequence(entropy=20261105) 分叉互相独立的流 (spawn_key 首元素为流号): 1 噪声[图,m]; 2 omega[图,m, 0=init / 1+r=第 r 轮排列]; 3 df_frozen 探针 b[图,m]; 4 T3 重模拟噪声[图,eps_idx,m] (与 S 无关); 5 T3 omega; 6 MC 探针[图,m,j,eps]; 7 N0 omega; 8 fix omega_k[图,k]; 9 N0 探针; 10 P-lin omega; 11 P-lin 探针。**1,2 与 S 无关 (R9)**。拟合器只接受 (y, omega, S/I, 超参); 任何非有限值立即失败, 不裁剪/不 nan_to_num。确定性: 单线程 CPU 下 f(y;omega) 重复运行逐位相同, 且 f(y+eps_min b; omega) 重复逐位相同 (否则舍入噪声冒充散度)。评测/分析脚本先于任何输出提交并记录 sha256。

## 6 预先登记判定
**有效性门 (任一不过 => run INVALID, 不是阴性, 不得据此下 K 结论)**:
- V1 单元测试: 硬阈值玩具 (协方差 df 与数值积分一致; E[div_hat(eps)]=df_{sigma'}); 渲染器梯度 vs 有限差分; 泄漏静态检查; 逐位可复现; 线性模型 GN 迹=秩。
- V2 确定性断言 (§5) + **R1 回放逐位断言 (每个 m)**。
- V3 **P-lin 在弱信号臂 W0 上**: 全规模 M=256, sdf(1024)-sdf(8) > 4 SE_diff (D1-D3, W1 报告不闸控)。
- V4 T3 恒等式 (**R5**): 仅 eps∈{0.3,1.0}*sigma0, S∈{8,256}, 每图每格: |mean div_hat(eps) - df_{sigma'}| <= 0.02 df 且 差值 SE <= 0.01 df, 两侧都用 256 样本, sigma' 重模拟使用与散度相同的 omega 体制。其余 eps 只报告。若某格仅因 SE 超限而不能判, 按修订 A2 增样本 (不改阈值)。
- ~~V5 收敛闸~~ 已降为 **R6 报告**: D1, S∈{8,1024} 在 2x 步数下报告 sdf (不是 df); 若 H1 结论翻转, 标注"受优化预算支配 (budget-dependent)"; 非收敛的固定预算管线仍有良定义的 df。
- **V6 (R2, 原 H1(b))**: S=8 与 N0 的 sdf 按构造应为 0 (两估计量同一对象): 对每图, |sdf(S=8)| <= max(3 SE, 0.03 df) 且 |sdf(N0)| <= max(3 SE, 0.03 df); 不过 => INVALID (估计量不一致), 不是 K1。
- **V7 (R2)**: P-lin 上 df_frozen 的**精确全坐标有限差分**散度 (4096 个坐标方向的 Jacobian 迹, 非 Hutchinson 探针; 解释 I4) 等于 24, 相对误差 <= 1e-6 (D1 与 W0 各 8 个 y)。
**H1 (G-a)** (仅在 V1-V4,V6,V7 全过时判): 对 3 张开发图中**至少 2 张**: (a) sdf(1024)-sdf(8) > 4*SE_diff 且 > 0.05*df_oracle^rand(1024); (c) sdf 对 log2 S 的 bootstrap 斜率单侧 95% CI 下界 > 0。否 -> **STOP (K1)**。同时报告 sdf(S) 全曲线、df_anti、2x 步数结果。
**H2 (G-b)** (仅 H1 通过): "移植足够" 当且仅当 对 >=2 张图存在 eps*∈ 网格, 使得 (i) |mean div_hat(eps*) - df_oracle^rand(1024)| / df <= 0.05; (ii) **超额方差** [sd_1^2(S=1024,eps*) - sd_1^2(S=8,eps*)] / df^2 <= 0.01 (R4; 线性平滑器的 Hutchinson 基线方差 ~2 df 不计入); (iii) SE_J2(S=1024,eps*) <= 0.05 df (R4); (iv) 成本 <= 3 次拟合/样本。成立 -> **K2: 不声称新校正, 提交 Opus 判 revise/stop** (T3 已是已知结果, K2 比预期更可能)。不成立 -> 立 F1 合同 (分解式估计 M1)。同时报告偏差随 eps 整条曲线 (含 eps=sigma0) 与对 df_{sigma'} 的偏差。

## 7 Pilot 决策规则 (R7, R8, R4-(iii))
按顺序判:
1. **INVALID (修复后重跑 pilot, 无科学结论)**: V1/V2/V7 任一不过; V3 (P-lin W0, M=256) 不过; 回放断言失败; **R7: eps_f∈{0.003,0.01,0.03}*sigma0 在 S∈{8,1024} 上的配对 FD df_frozen (同 (y,omega,b)) 的两两差均值 <= 1% df, 否则 INVALID/重设计**; V6 在 pilot 样本量下严重违反 (同阈值 max(3SE,0.03df))。
2. 效应 Δ̂ = sdf(1024)-sdf(8) (D1, M=32, 配对 bootstrap), SE_32; **功效外推**: SE_256 = SE_32*sqrt(32/256), z_proj = Δ̂/SE_256。
3. **STOP (K1)** 当且仅当 [Δ̂ + 1.645 SE_32 (单侧 95% 上界)] < 0.02*df_oracle^rand(1024) **且** P-lin 通过 (V3 与 V7)。(R8 等价性检验; 用 sdf, 不用 df; 原"P-lin 升而真实管线 delta-df<0.02 df"规则作废。)
4. 否则若 z_proj < 4 => **REDESIGN** (功效不足, 不算阴性; 增 M/改 S 网格等属合同修订, 提交 Opus)。
5. 否则 **PROCEED** 到 Stage 1。
6. 若外推 Stage 1 墙钟 > 4 小时 => REDESIGN。
7. 仅记录项 (原规则 iii 重写, R4): (a) 超额方差 [sd_1^2(S=1024,eps) - sd_1^2(N0,eps)]/df^2 (eps∈{0.3,1.0}); (b) N0 的 SE_J2 外推到 M_mc=64 与 256 是否 <= 0.05 df。(b) 不过 => 记"移植 MC 因非搜索原因不可行", 继续 H1; (a) <= 0.01 且 (b) 过 => 记"H2 预期 K2", 不据此停。

## 8 报告
全部结果 (含负结果/INVALID) 落 outputs/F0-*/, 开发/保留分开, 记录输入/代码/环境哈希、种子、墙钟; 不跨级别混合; 保留图只在冻结后运行一次; 阴性/INVALID 如实报告, 不删 run。

## 9 Opus R1-R9 追溯表, 解释登记, 修订机制
| R | 落实位置 |
|---|---|
| R1 | §2 单一代码路径+omega; §3 df_frozen 回放+逐 m 逐位断言+复用基项; §6 V2 |
| R2 | §6 V6 (原 H1(b)), V7 |
| R3 | §2 P-lin 1024 原子, W0/W1; §6 V3 在 W0 上 |
| R4 | §6 H2 (ii)(iii); §7 第 7 条 (N0 基线) |
| R5 | §6 V4 仅 eps∈{0.3,1.0}, 256/256; §4 T3 单元 |
| R6 | §6 报告项 (2x 步数 sdf, budget-dependent 标注) |
| R7 | §3 eps_f 候选; §7 第 1 条检查; 修订 A1 |
| R8 | §7 第 2-5 条 |
| R9 | §2/§5 omega 跨 S 共用 (嵌套排列前缀); §3 反对称次要估计 |
解释登记 (我在 Opus 文字留有空间处作的选择, 请 Opus 确认):
- I1 (R3) "弱信号臂" := W0 (x=0) 闸控 V3; W1 (0.1*D1) 与 D1-D3 只报告 (W1 的原子级信噪比仍高, 选择可能稳定)。
- I2 (R4) "per-image SE of df-hat at J=2" := J=2 平均估计量在 M_mc 个噪声样本上的均值标准误 (实验精度条件), 不是单样本 sd (线性基线下 J=2 的单样本相对 sd ~ 1/sqrt(df) 约 0.07, 会无搜索效应也不过); 单样本相对 sd 另作报告。
- I3 (R7) "within 1% of df" := 同 (y,omega,b) 配对 FD 的 df_frozen 在三个 eps_f 间两两均值差 <= 0.01*df_oracle^rand。通过后缺省 eps_f=0.01*sigma0 由 A1 冻结; 失败则 INVALID 回 Opus。
- I4 (R2/V7) "FD df_frozen" := 精确全坐标有限差分散度 (Jacobian 迹), 因 Hutchinson 探针精度不可能到 1e-6。
- I5 (R9) "common omega" := init 与每轮排列流与 S 无关, 候选 = 排列前 S 个 (嵌套); 反对称为次要, M'=128。
- I6 (R1) 逐位断言对**每个** m 执行 (多 1 次拟合/样本, 已计入预算), 不抽样。
- I7 (R8) pilot "P-lin passes" := V3 (W0, M=256) 与 V7 通过; P-lin 在 pilot 中也用 M=256 (廉价)。
- I8 (R5) V4 的"差值 SE" := sqrt(SE_div^2 + SE_oracle'^2); 因 SE_oracle' 在 M=256 约 1-2% df, 可能超 0.01 df -> 修订 A2 (增样本到至多 1024 仅针对该格, 阈值不变)。
- I9 (R4) H2 的基线 df 用同图 df_oracle^rand(1024); 超额方差对同 eps 逐图计。
- I10 (R6) 2x 步数报告只涉 D1 的 S∈{8,1024}, 不闸控; 翻转定义 = H1(a) 在 D1 上的真假变化。
修订机制: A1 = 冻结 eps_f (pilot R7 通过后, 仅记录, 不改判据); A2 = 为满足 V4 的 SE 条件对个别格增样本; 其余任何改动 (阈值、判据、数据、S 网格、M 的实质变更) = 合同修订, 必须再次真实 Opus 审查并记新 sha256; 实验开始后不得改判据。
