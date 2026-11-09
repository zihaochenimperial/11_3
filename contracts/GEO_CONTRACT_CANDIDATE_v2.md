# GEO 48h 合同候选 v2 (proposed; 吸收真实 Opus 复核 C1-C14 后的待冻结文本; 未实现; 0 个已验证贡献)

起草: Sonnet 5.5 (run 20261106T054959Z-experiment-80ab), 2026-11-06 ≈06:40Z。上游: 真人 2026-11-06 ≈05:47Z 授权 (memory/AUTHORIZATIONS.md) 采纳的 Astra 最终决定; v1 (contracts/GEO_CONTRACT_CANDIDATE_v1.md sha256 7259a4cd...); 真实 Opus 复核 FREEZE-WITH-CHANGES (自报 claude-opus-5-5, run 20261106T063046Z-opus-review-ea2a, 全文 research/notes/OPUS_REVIEW/OPUS_REVIEW_GEO_CONTRACT_20261106.md)。
边界: E41-58 封存; S2 图 1-24 不用; JOINT 排序 STOP、F0/H2、CF0 不复活; 8GB CPU; 无 GPU/付费; 产物全在 D:\Gaussian; 方法侧代码不得读取干净图。

## 0. 回答什么、不回答什么
固定 K 个 2D 高斯 (K 不增长), 对同一个持续的图像空间正则目标
  F_a(θ) = 1/(2σ_n²) ||y − A x(θ)||² + (a/2) ||x(θ)||²   (x_ref = 0; W = σ_n⁻¹ I; a = λ/σ_n²)
求 θ ∈ R^p, p = 6K, θ_k = (w_k, mx_k, my_k, l11_k, l21_k, l22_k) (w_k 为振幅)。a 是目标的一部分 (对所有求解器相同); η 只是逐步阻尼, 不属于目标。
三个问题**分别报告, 不做分解**:
- Q1 正则项作用: 同一求解器 (GEO) 下 F_a(λ*) 的解 vs F_0 + 偏差原理早停 (τ* 同等预算调定) 的质量。
- Q2 联合计算作用: GEO vs 向量化块雅可比 BJ 与 Gauss-Seidel BLK, 在相同 A-作用预算上的目标缺口/质量/代价。**先验预期**: 重叠模糊高斯上联合 Gauss-Newton 优于坐标式是预期结果, JOINT-MATTERS 是前置核对, 不是发现。
- Q3 真实瓶颈: 以稀疏 4σ 截断 J 的普通实现 (LSMR) 测每步时间构成与内部 Krylov 迭代数随规模的增长; 只服务于“局部两级求解器”是否有可攻之处, 本合同不实现它。
**不声称**: 原创性/求解器新颖性 (GEO 一步 = 图像度量阻尼的正则化 Gauss-Newton/LM 的 Euclidean 最小范数写法; matrix-free PCG-LM 已发表于 3DGS-LM arXiv 2409.12892, G0 行 C76)、跨数据泛化、对增长/选择的结论。**GEO vs LMD 只检验“阻尼度量” (图像度量 JᵀJ vs 参数空间 diag(H_a)) 这一差别**, 不是联合计算的检验。一切标 proposed。

## 1. 记号与精确的一步
x(θ) = Σ_k g_k ∈ R^m (m = N²); J = ∂x/∂θ ∈ R^{m×p}; A = B⊗B (S2 的 Op); r = y − A x。Λ_A := ||WA||₂² = ||B||₂⁴/σ_n² (数值由一维模糊矩阵 B 的谱范数得到, ≤ σ_n⁻²; 所有臂共用)。η_t := κ_t Λ_A (C5)。
单步子问题: min_δ ½||W(r − AJδ)||² + (a/2)||x + Jδ||² + (η/2)||Jδ||²
正规方程 P: (JᵀAᵀW²AJ + (a+η) JᵀJ) δ = JᵀAᵀW² r − a Jᵀ x。(Opus 核对符号正确; M = AᵀW²A + (a+η)I ≻ 0 ⇒ 解集 = δ_min + null(J), 图像步 Jδ 唯一。)
GEO: J = U Σ Vᵀ (约化 SVD; **丢弃 σ_i ≤ 1e-8 σ_1 的方向, rcond=1e-8, GEO/BJ/V2 稠密参考共用 (C2)**), z = ΣVᵀδ, B = W A U = W (AJ) V Σ⁻¹, (BᵀB + (a+η)I) z = BᵀW r − a Uᵀ x, δ = V Σ⁻¹ z (参数空间 Euclidean 最小范数原像, 坐标 S = I)。
**等价性的准确说法 (C2)**: GEO、同截断的稠密伪逆、收敛的 LSMR 给出**相同的图像步 Jδ**; 参数步 δ 因原像度量不同而不同 (GEO/稠密: Euclidean 最小范数 + 截断; LSMR: 隐式截断; Jacobi-PCG: D-范数最小), θ' = clamp(θ+δ) 依赖 δ, 故各臂轨迹可以不同, 这本身是被比较的内容。**弱方向警示**: δ_i = z_i/σ_i, 图像度量 η 只均匀缩小 z, 不限制弱方向上的参数放大 (≤ 1e8); 振幅≈0、宽高斯 (σ 至多 12 px)、部分出界的高斯会使 GEO 提出巨大参数步, 被箱约束或守卫拒绝, κ 上升甚至停滞。LMD 的参数空间 diag(H_a) 阻尼没有此失效。这是 GEO 与 LMD 的实质差别, 必须记录 (C14)。
接受准则 (所有臂统一, C3): 步 δ → θ' = clamp(θ+δ) (S2 箱约束: 位置 [−4,N+4]; log-Cholesky 对角 ∈ [log0.6, log12]; l21 ∈ [−12,12]; 振幅无界), δ_c := θ' − θ, jv_c := J δ_c;
  pred := ⟨A jv_c, r⟩/σ_n² − a⟨jv_c, x⟩ − ½(||A jv_c||²/σ_n² + a||jv_c||²) (在**截箱后**的步上取模型下降), 必须 > 0;
  act := F_a(θ) − F_a(θ'); 接受当且仅当 act > 0 且 act/pred ≥ 1e-4 且 ||x(θ') − x(θ) − jv_c|| ≤ 0.5 ||jv_c|| (线性化守卫, 全体臂统一)。记录每步箱约束触发的参数个数 (clamp 率)。
κ 规则 (C6): κ_0 ∈ {1e-4,1e-3,1e-2} 调定; 拒绝: κ ← f κ (f ∈ {3,10} 调定, 全体臂同一规则); 接受且 act/pred ≥ 0.75: κ ← κ/3; 接受且 1e-4 ≤ act/pred < 0.75: κ 不变; κ ∈ [1e-12, 1e4]; 每外迭代至多 10 次回溯, 回溯复用该迭代的 J、AJ、SVD/Gram (只重解)。LMD 的 Marquardt 参数 λ_LM 用同一 f 与同一接受/调度规则 (增 ×f, 良好接受 ×0.3)。
停止: A-作用预算耗尽 (见 §3), 或外迭代 ≥ 200, 或连续 3 次接受步相对下降 < 1e-9, 或 κ 达上限。

## 2. 数据与种子 (全新, 与 S2 图 1-24、E41-58 不相交; C10)
- 图: dev 101-112 (每家族 4 张: 家族 = (i−1) mod 3 → 0 edge / 1 tex / 2 mix), held-out 201-224 (每家族 8 张); 干净图 rng = SeedSequence([0, i]); 配方复制自 as_gen.clean_image 的三类。
- 噪声: ξ_i = default_rng(SeedSequence([1, base, i])).standard_normal(N,N), base: dev 9101, held-out 9201/9202 (不加性相加, 避免 9101+112=9213=9201+12 之类碰撞); 同一图同一 base 下四个条件共用 ξ (按 sn 缩放; 与 S2 约定一致)。扰动重启 (F_ref) 用 SeedSequence([2, base, i, restart])。合成标尺目标用 SeedSequence([3, N, K])。
- V5 断言: 所有 (tag, base, i) 键两两不相交; 图集合与 {1..24}∪{41..58} 不相交; dev/held-out 图不相交。
- 条件 C1-C4 同 S2: (sb, sn) = (1,0.01), (1,0.03), (2,0.01), (2,0.03)。K 层: 16 (4×4), 36 (6×6); 初值 = 规则网格中心, 各向同性 σ_g = 间距/2, 振幅由 y 做 LS (lstsq rcond=None, 只用 y); 所有臂同一初值。
- 单元: dev 12 图 × 4 条件 × 1 噪声 base × 2 K = 96; held-out 24 × 4 × 2 base × 2 K = 384。统计独立单位 = 图像 (每图单元的 log 比的均值), df=23 t 区间 (对 log 均值构造后变换) + 精确符号翻转 p (仅描述, 不做多重校正)。
- Phase L 合成目标 (§5) 与图像质量无关, 只用于代价结构。

## 3. 求解器臂与预算
所有臂: 同一目标 F_a、同一初值、同一箱约束、同一接受准则 (§1)、同一 η = κ Λ_A (LMD 用 λ_LM)。
- HIST: S2 的 as_core.lm (目标 0.5||r||²+1e-6Σw², Marquardt diag); 历史对照, 不参与 Q2/Q3 判定。
- LMD: 参数空间密集解, 阻尼 λ_LM · diag(H_a), H_a = JᵀAᵀW²AJ + a JᵀJ。
- GEO: §1。
- BJ (新, C8): 块雅可比: 同一次 J、AJ 下, 把 Gram 取成按高斯分块对角 (K 个 6×6 块, 图像度量阻尼, 各块 SVD/最小范数同 GEO, rcond=1e-8), 所有块同时求解 (向量化批量 SVD/eigh), 合成一个联合步 (图像步 = Σ_k J_k δ_k), 用单个 κ 与统一接受准则。GEO vs BJ 隔离“耦合”这一因素, 无解释器开销混杂。
- BLK: Gauss-Seidel 逐高斯: 固定顺序 k=1..K, 每块用当前残差、块内 SVD/最小范数、块内 κ_k 与回溯 ≤4 次, 按真实 F_a 下降接受 (统一准则), 接受后更新残差/图像; 一次扫描 = 一次迭代。
- LSMR: matrix-free, 对 P 的增广最小二乘 [WAJ; √(a+η)J]δ ≈ [W r; −a x/√(a+η)] (scipy lsmr, δ0=0, atol=btol=1e-10, maxiter=p, conlim=1e12)。
- PCG8P: 对 P 的 Jacobi(diag(JᵀJ)) 预条件 CG, δ0=0, ≤8 内迭代; 标注为“截断的 GEO 型步”, 不是 3DGS-LM (C4)。
- PCG8D (新, C4): 3DGS-LM 式: 对 LMD 系统 (H_a + λ_LM diag(H_a)) 的 Jacobi 预条件 CG, ≤8 内迭代; diag(H_a) 由 AJ 的列范数精确形成 (p 次 A 作用, 记入计数)。
- 像素域背景: Tikhonov-SVD (λ 用 GCV; 另一行 λ 在 dev 上调); TV、INR 本合同不做。
- 预算 (C8, C13): 每格公共 **A-作用预算** A_cap(K) = 5 × (dev 上 GEO 在其停止规则 {收敛/200 迭代} 下 A-作用次数的中位数), 按 K 层在阶段 D 末冻结, 对所有臂相同; 计数单位: 对单幅图像的一次 A 或 Aᵀ 作用为 1 (块/批量操作按图像数计), 并同时记录 J 构造次数、乘法次数 mv、flops 估计、箱约束触发数。选用 A-作用计数而非墙钟做公共预算, 是因为 2 个并发作业下墙钟不确定性会破坏复现 (偏离 Opus 的“墙钟”建议, 见 §11); 墙钟另在独占子集上测 (§5)。
- 调优公平性: 各臂的控制超参 (GEO/BJ/BLK/LSMR/PCG8P: κ_0 ∈ {1e-4,1e-3,1e-2} × f ∈ {3,10}; LMD/PCG8D: λ_LM,0 ∈ {1e-4,1e-3,1e-2} × f ∈ {3,10}), 6 组合, 在 dev 上以“A-作用预算内最终几何均值 s (见 §4)”最小选出并冻结, held-out 不再调。

## 4. 度量 (事前固定)
- 目标缺口: F_ref(单元) = 该单元所有求解器所有运行与 LMD 500 迭代 × 3 次扰动重启 (θ 位置高斯 ±0.5 px 扰动, SeedSequence 固定) 的最小 F_a; s(F) = (F − F_ref)/(F_init − F_ref)。F_ref 只在评估端计算; 报告每臂成为 F_ref 持有者的比例 (基准重启为 LMD 且各臂相同)。
- 报告三项 (C9): (a) 预算 A_cap 处的终值 s; (b) 达到自身平台 (F 与其终值相对差 ≤ 1e-6 的首个计数) 的 A-作用数; (c) 达到 s ≤ 1e-2 的 A-作用数——**仅在两臂都达到的单元上**比较; 失败规则基于 (a)。
- 质量 (评估端读干净图): M = mean((x(θ̂) − x_true)²); H_X = 1 − exp(mean_i log(M_X/M_ref))。另报 x̂ 相对 x_true 的平均强度偏差 (x_ref=0 的正则会收缩强度, REG-HELPS 可能只是收缩的结果, 见 §9)。
- 有效性: 接受步 F 单调下降率 (须 100%)、拒绝步/回溯数、箱约束触发率; 每步 (GEO/LMD/BJ) 记录 cond(J)=σ_1/σ_ρ、秩 ρ、|w_k| < 1e-3 max|w| 的个数与中心出界 [0,N] 的高斯个数 (C14)。
- 墙钟: 仅取自独占单线程子集 (§5), 3 次重复取中位数; 并发主运行只记录计数。

## 5. 阶段与顺序 (V → L → D → H; C13)
- 阶段 V: 单元测试 (§6)。
- 阶段 L (独占作业, 约 1 h; 独立于 dev): (N,K) ∈ {(32,36),(64,144),(80,225),(96,324),(128,576)} (K = N²/28.4 近似, 每 28 px² 一个高斯), 合成混合目标 (SeedSequence([3,N,K]); 高斯 σ 取 1.5-4 px 固定像素尺度, 模糊 sb=1.5, sn=0.01, λ=1e-3 固定)。**普通实现 = LSMR + 稀疏 J**: 渲染与 J 都在 Mahalanobis 半径 4 内截断并以 CSR 存储 (该阶段的前向模型是截断模型, 自洽); 固定同一臂 (LSMR) 跑所有规模。每规模取两个状态 θ: 网格初值与 LSMR 外迭代 5 次后。量: (i) 每外迭代分阶段时间 (jac / aj / solve / back) 与份额, 中位数 of 3 次重复, 单线程独占; (ii) 在固定 θ 上使线性化步的法方程相对残差 ≤ 1e-6 所需的 **LSMR 内迭代数**; (iii) 稠密 GEO/LMD 的每迭代时间作参考 (≤ (96,324); (128,576) 稠密标“超限”); (iv) Gram 耦合稀疏度 (描述性, 不判定)。
- 阶段 D (dev): (i) λ 网格 {0, 1e-6,…,1e-1} × (条件, K) → λ* (GEO 解的 dev 几何均值干净图 MSE 最小; a = λ/σ_n²); (ii) τ 网格 {0.8,0.9,1.0,1.1,1.25,1.5,2.0} × (条件, K) → τ* (F_0+GEO+DP 的 dev 几何均值 MSE 最小, 与 λ* 同预算同准则); (iii) 各臂控制超参选择; (iv) A_cap(K) 标定; (v) 也跑 y-only 配对: λ_DP = 使 GEO 收敛解满足 ||y−Ax||² ≤ N²σ_n² 的最大 λ (网格内), 与 τ=1。阶段 D 末冻结所有选择 (JSON 表 + sha)。
- 阶段 H (held-out, 一次): 384 单元 × {HIST, LMD, GEO, BJ, BLK, LSMR, PCG8P, PCG8D (均在 F_{a(λ*)} 上, A_cap 预算)} + F_0+GEO+DP(τ*) + F_0+GEO 收敛 + F_0+LMD+DP (交叉核对) + y-only 配对 + Tikhonov 两行 + F_ref。
- 独占墙钟子集: 24 图 × 4 条件 × base 9201 × 2 K = 192 单元, 臂 GEO/BJ/BLK/LMD/LSMR/PCG8P/PCG8D, 3 次重复, 单线程、其他作业不并发。
- 线程: 作业内固定 OMP/MKL/OPENBLAS 线程=1 (导入 numpy 前设置); 并发主运行最多 2 个作业。
- 预算: 约 5 CPU-h; 压缩次序: 先删 dev 调参的 Tikhonov 行 → HIST 计时 → Phase L 的 K=16; 不删 F_ref 重启与 V 测试。

## 6. 阶段 V 单元测试 (全过才进入 L/D/H; 失败修一次, 再失败 → 停并记 FAIL)
V1 geo_core 渲染/J 与 as_core 在 N=32 上 1e-12 一致; 有限差分 J (相对 1e-6)。
V2 GEO 步与同 rcond (1e-8σ_1) 的稠密伪逆步: 图像步相对差 ≤ 1e-6; 参数步差仅描述 (含秩亏例); LSMR(tol 1e-12) 图像步在 cond(J) ≤ 1e5 的良态例上与稠密一致 ≤ 1e-4, 病态例仅描述; PCG8 不判定。
V3 全体臂的接受迭代 F 单调不增 (100%), F 与独立暴力实现 1e-10 一致; 接受准则在截箱步上用 pred(δ_c) (构造一个触箱例核对)。
V4 一阶最优性: 小良态例 (K=4, 数据由 K=4 高斯生成并加 sn=0.01 噪声), GEO ≤300 迭代内达到 ||P_box ∇F|| / ||∇F(θ_0)|| ≤ 1e-6 (排除触箱参数)。失败则判 V4 不过 (修一次)。a=0, η→0 时 GEO 退化为无正则 GN 步 (与 V2 同检验)。
V5 方法侧源码扫描 (geo_core 不 import/读取 geo_gen、clean_image*、x_true); 种子键两两不相交 (§2); 图集合与 S2/E41-58 不相交; dev 日志中无 held-out 图。
V6 同一单元两次运行逐位一致 (固定迭代数、无预算截断路径)。
V7 BJ 在 K=1 时与 GEO 一致; BLK 在 K=1 时与 GEO 一致 (块退化为整体)。

## 7. 判定规则 (GEO-3; 事前固定)
- V-pass: V1-V7 全过, 且 dev 上 GEO 与 LMD 各有 ≥95% 单元在 A_cap 内 s ≤ 0.1; 否则 STOP-GEO-V (记 FAIL, 不解读质量)。若 dev 上 GEO 的拒绝率或箱触发率 ≥ 3× LMD, 则报告为“GEO 特有失效模式”, 不作为 Q2 证据 (C14)。
- Q1 (held-out; F_a(λ*) GEO 解 vs F_0+GEO+DP(τ*); 同一求解器, C11): REG-HELPS 若 H ≥ 0.05 且 t 区间不含 0 且 ≥3/4 条件 H ≥ 0; REG-HURTS 若 H ≤ −0.05 且区间不含 0; 否则 REG-NEUTRAL。分 K 层报告, 报告 DP 触发率 (首次满足 ||y−Ax_j||² ≤ τ*N²σ² 的比例); 若触发率 < 50%, 比较标为“F_a(λ*) vs 收敛的 F_0”。另报 LMD 交叉核对行与 y-only 配对 (λ_DP vs τ=1)、对 HIST 的 H。
- Q2: JOINT-MATTERS 当且仅当**两个 K 层都**满足: [GEO 达到共同目标 (s ≤ 1e-2, 仅在联合达到的单元上) 所需 A-作用 ≤ 0.5× BJ 的**且** ≤ 0.5× BLK 的] **或** [在 A_cap 下 BJ 或 BLK 的终值 s > 1e-2 的单元 ≥ 25% 而 GEO ≤ 10%]; 且 GEO 对 BJ 的质量 H 的 t 区间下界 ≥ −0.02; 且独占子集上墙钟比与 A-作用比同向。否则 JOINT-NOT-MATTERS。另报 GEO 对 LMD/LSMR/PCG8P/PCG8D 的代价/质量比 (GEO vs LMD = 阻尼度量检验)。再次声明: 这是前置核对, 不是发现。
- Q3: 取阶段 L 的 LSMR+稀疏 J 臂。BOTTLENECK-OPTIMISABLE 当且仅当 (a) 在最大两个规模上 (aj + solve) 份额 ≥ 50%, 且 (b) 内迭代数对 K 的对数-对数 OLS 斜率 ≥ 0.25 且其 95% t 区间 (df=3, 5 个规模, 每规模取两状态的 log 均值) 不含 0, 且去掉任一规模的留一斜率均 > 0; ASSEMBLY-BOUND 当 (jac) 份额 ≥ 50%; 否则 FLAT。耦合稀疏度仅描述。
- 推进: ADVANCE-7D 仅当 V-pass ∧ JOINT-MATTERS ∧ BOTTLENECK-OPTIMISABLE ∧ G0 已读块雅可比/加性 Schwarz 预条件 Gauss-Newton 文献 (§10); REDIRECT-REG 若 REG-HELPS 但 Q2/Q3 任一不过 (保留正则目标协议, 加 TV/INR 对照, 不做求解器主张); 其余 STOP-GEO (记入 FAILURES, 保留全部数字)。ADVANCE 无需再问真人 (授权已含), 但需新 7 天合同 + 真实 Opus 门 + 冻结。
- 任何标签都不是“已验证贡献”: 单一合成基准、开发式调参、独立确认缺失。

## 8. 流程与记录
冻结后只允许“记录的偏差”(追加, 不改文)。角色: Sonnet 编排/实现; 真实 Opus 为科学门 (自报模型入日志); OpenCode 默认 2 (GLM 只读审源码泄漏/等价; Kimi 隔离补丁: 仅测试脚手架), 最多 5, 不递归; 不用 Codex 做研究。每个作业唯一 run_id 与 start/end/failure 日志; 失败即记 FAILURES.md (追加)。文件: src/geo_core.py, src/geo_gen.py, tests/test_geo_core.py, experiments/geo_run.py (L/D/H), experiments/geo_analyze.py (评估端), outputs/GEO-*/。

## 9. 已知局限
固定 K、小图、非高斯程序化图像, 不外推。held-out 与 S2 设计用的是同一生成器分布 (样本独立, 分布不独立)。λ*、τ* 用干净图 MSE 在 dev 调定 (合法调参), 依赖已知 σ_n/sb, 非 y-only 规则。F_ref 是启发式参考, 非全局最优。x_ref=0 使正则成为纯强度收缩, REG-HELPS 可能只反映收缩。计时仅本机 (i7-12700H, 单线程独占), 绝对数无外推意义。Phase L 用合成混合目标与截断模型, 只回答代价结构。JOINT-MATTERS 是先验预期的前置核对。

## 10. G0 条款 (完成前不得写“新颖”; ADVANCE 前必须读完)
已读 (L3): 3DGS-LM (C76)。待读: Hanke 型正则化 LM、IRGN; 2D Gaussian 图像拟合的二阶/GN 求解; LM 的几何加速/拉回度量 (pullback-metric) 变体; **块雅可比/加性 Schwarz 预条件 Gauss-Newton (将来“耦合邻域+共享粗空间”的直接近邻, ADVANCE 前必须读)**。

## 11. v1 → v2 修订记录 (对应 Opus 复核 C1-C14; 如实标注我的偏离)
C1 记号: 振幅 w_k, 正则 a=λ/σ_n², 去 α (§0-§1)。C2: rcond=1e-8σ_1 统一; 等价性改写为“图像步相同, 参数步不同”; V2 报参数步差 (§1, §6)。C3: 箱约束步上取 pred, pred≤0 拒绝, 守卫统一 0.5 比例, 记 clamp 率 (§1)。C4: 增 PCG8D (3DGS-LM 式), PCG8P 标“截断 GEO”, 声明 GEO vs LMD 仅检验阻尼度量 (§0, §3)。C5: η=κΛ_A (§1)。C6: κ 规则统一 (§1)。C7: V4 相对投影梯度 (§6)。C8: 增 BJ, 公共预算, 计数共同主要, JOINT-MATTERS 替换 (§3, §7)。C9: 终值 s / 自身平台 / 联合达到子集, F_ref 持有比例 (§4)。C10: SeedSequence 与 V5 不相交断言 (§2, §6)。C11: Q1 同一求解器, τ* 同预算调定, y-only 配对, DP 触发率 (§5, §7)。C12: Q3 重定义为稀疏 4σ J、固定 LSMR 臂、5 个规模、内迭代斜率 (§5, §7)。C13: 次序 V→L→D→H, 独占 192 单元墙钟子集 (§5)。C14: cond(J)/秩/近零振幅/出界/clamp 日志, GEO 特有失效报告 (§4, §7)。
**偏离/自选 (未经 Opus 逐条审, 需在 GEO-3 的 Opus 门复核)**: (1) 公共预算用 A-作用计数 A_cap 而非墙钟 (并发下墙钟破坏复现); 墙钟另测。(2) Q3 斜率区间用 5 个规模的 OLS t 区间 (df=3) + 留一斜率代替 Opus 提的“bootstrap”(n=5 时 bootstrap 不稳)。(3) PCG8D 的 diag(H_a) 由 AJ 列范数精确形成 (p 次 A 作用), 代价计入; 与 3DGS-LM 由缓存像素梯度得到 diag(JᵀJ) 不完全相同。(4) y-only 配对中 λ_DP 用 GEO 收敛解定义。(5) BLK 块内回溯 ≤4 次、BJ 的 κ 为全局单值, 属我的实现设定。
