# FROZEN GEO 48h CONTRACT v2 -- 冻结记录 (append-only)

冻结时间: 2026-11-06T06:38:08Z (date -u). 冻结文本: contracts/GEO_CONTRACT_CANDIDATE_v2.md, sha256 = 18aa67b432a6c0f1cc94f634fd98045752f0d854240e3ab65beaada907a84818。
流程: 真人 2026-11-06 ≈05:47Z 授权 (memory/AUTHORIZATIONS.md) -> v1 合同候选 (sha256 7259a4cd1f9743e7e6e36dcc8562410f89a49a983c08d5f3081f3342cdca1efb) -> 真实 Opus 复核 FREEZE-WITH-CHANGES (自报 claude-opus-5-5, run 20261106T063046Z-opus-review-ea2a, 全文 research/notes/OPUS_REVIEW/OPUS_REVIEW_GEO_CONTRACT_20261106.md; 14 项必改 C1-C14) -> v2 吸收 C1-C14 (v2 §11 逐条对应, 并如实标出 5 项我的偏离/自选) -> 本冻结。
冻结只覆盖合同文本 (v2)。实现代码 (src/geo_core.py, src/geo_gen.py, tests/test_geo_core.py, experiments/geo_run.py, experiments/geo_analyze.py) 在阶段 V 全过后另记 sha256 冻结 (追加)。
边界: E41-58 封存; S2 图 1-24 不用; 旧 JOINT 排序 STOP / F0/H2 / CF0 不复活; 无 GPU/付费; 8GB CPU; 方法侧代码不读干净图; 产物在 D:\Gaussian。
未经 Opus 逐条审、需在 GEO-3 的 Opus 门复核的偏离: (1) 公共预算用 A-作用计数 A_cap 而非墙钟 (2) Q3 斜率区间用 OLS t 区间(df=3)+留一斜率代替 bootstrap (3) PCG8D 的 diag(H_a) 由 AJ 列范数精确形成 (4) y-only 配对 λ_DP 的定义 (5) BLK 块内回溯 ≤4 次、BJ 单一全局 κ。
本节点不含任何拟合/结果; 0 个已验证贡献。48h 计时从本冻结起算 (截止 2026-11-06T+2d 同一时刻, 即 2026-11-08 ≈同钟点)。

---

# 追加冻结记录 K1 (预 D, 最终版; 追加于 FROZEN_GEO_CONTRACT_v2.md 之后, append-only)

写于 2026-11-08T01:21Z (date -u)。**此刻没有任何阶段 L/D/H 的正式结果可见。** 可见的只有: (a) 阶段 V 测试; (b) 开发期基准 (dev 图 101/C1/K36, 102/C2/K16, 103/C4/K36, base 9101, λ=1e-3, 200 外迭代校准模式; 无 F_ref、无质量指标, 不进任何判定; 另在 K1.8 的暴露披露中列出); (c) 阶段 L 在 (32,36) 与 (64,144) 两个正式实例上的冒烟计数 (见 K1.7 暴露披露)。0 个已验证贡献。
本记录吸收: 窄审 8d02 的 A1-A5; 窄审 f553 (K1 草稿) 对 Q-a…Q-f 与两条补充问题 (λ=1e-3 标定的 caps、阶段 L 容差规则 #11) 的 ACCEPT-WITH-CHANGES 全部必改项。真实 Opus 自报模型均为 claude-opus-5-5 (run 见 K1.10)。Opus 原文: research/notes/ (OPUS_REVIEW_GEO_PRED_ADDENDUM_20261106.md 与 OPUS_PACKET_GEO_PRED_ADDENDUM_20261106.md)OPUS_REVIEW_GEO_DEVIATIONS_20261106.md 与 OPUS_REVIEW_GEO_PRED_ADDENDUM_20261106.md。

## K1.1 V 阶段与代码版本
- 主机 j85 (run 20261106T064250Z-host-py-3e80) exit 0, 12 passed, 完成 2026-11-06T06:42:56Z。当时代码 geo_core.py sha256 1044a3f8… (core-v0), geo_gen.py 93f42252…, test_geo_core.py 3943c5a5…, as_core af9d525d…, as_gen e5d08678…。j85 只证明 core-v0 的基础有效性, **不**证明可用于正式实验 (见 FAIL-0026)。
- core-v0 之后的所有改动 (K1.3-K1.6) 都发生在任何 L/D/H 正式结果可见之前。改动后版本见 K1.9; 其容器内 pytest 为 18 项通过; 主机重跑见 K1.10 (须先于任何 L/D 作业)。

## K1.2 开发期基准发现的问题 (FAIL-0026; 实现/设计问题, 非科学结论)
1. 停止/回溯逻辑缺陷: 一次外迭代 10 次回溯全拒绝即终止, κ 极限从未被试。已修: 失败迭代把已升高的阻尼带入下一轮; 仅当 κ (LMD/PCG8D: λ_LM) 已在极限被试且失败 ≥2 次后停止 (BLK: 连续 3 次扫描无任何被接受块)。
2. 箱约束夹取破坏下降性: 单个贴界坐标被夹取使阻尼步 pred<0。2b (Opus 对 core-v1 的发现, 本节新增): 绝对容差 1e-12 对"贴界 1e-6 内"的坐标无效, 103/C4/K36 上 GEO(rcond 1e-4) 在第 65 次迭代 `no_step` (F=633.46), 改 ε=1e-3 后 200 次迭代到 F=630.66。修复见 #6。
3. BJ 的 α\*>0 无上界会抵消阻尼 (α\*∝κ, 0.2→1.6e3)。修复见 #7。
4. GEO 在 rcond=1e-8 弱方向放大 (δ_i=z_i/σ_i; 102/C2/K16 上 cond(J)≈6e4, |δ|≈1.5e3, 停滞 F=2206 vs F_init 2207, LMD 548; rcond=1e-4 同格 584)。修复见 #8。
5. LSMR maxiter 代码为 2p, 合同为 p; 已对齐合同 (非偏离)。
- 安全上限绑定 (新): 开发期 5000 外迭代上限使 BJ/BLK 在预算下只用到约 45% 的 W_cap (probe), 会使分句 (b) 偏向 JOINT-MATTERS; 同一 probe 中 PCG8P (约 16%) 与 PCG8D (约 41%) 也触及该安全上限。见 #10 与 R-censor。
- 开发读数 (非结果): 101/C1/K36 200 迭代 LMD 2096, GEO(rc1e-4) 2102, GEO(rc1e-8) 2210, LSMR 2107, PCG8P 2151, PCG8D 2153, BLK 2239, BJ 2679。ε=1e-3 修复后冒烟重跑 (本日, 同三格): 103/C4/K36 GEO(rc1e-4) 630.66 (200 its, 与 Opus 副本一致), 102/C2/K16 GEO(rc1e-8) 仍 9 its `no_step` F=2206 (冻结规格的弱方向放大, 见 #8)。这些都是开发诊断。

## K1.3 A1-A5 (窄审 8d02) 的采纳与实现 (含 f553 指出的遗漏)
- A1 工作代理: n_A 与确定性 flop 代理 W (公式表 src/geo_flops.py; F_A=4N³; 渲染 F_render=10·K·N²; LMD 稠密解按 Cholesky p³/3)。A·jv_c 通过 (AJ)δ_c 对 GEO/BJ/LMD/BLK 计 0, 对 LSMR/PCG 计 1; 每次试探 F_a 求值计 1; BLK 每块试探计 1; PCG8D 记严格与缓存两种。A_cap(K)/W_cap(K) = 5× 调参后 GEO 在 96 个 dev 单元 (按 K 层 48 个) 上校准运行 (≤200 迭代或收敛) 的 A / W 中位数, **所有停止原因都计入且逐层报告** (R2)。预算运行仅当 n_A≥A_cap **且** W≥W_cap、收敛 (连续 3 个被接受步相对下降 ≤1e-9)、κ/λ_LM 极限已试且失败、或安全上限时停止。安全上限 (替换草稿的 5000): **GEO, LMD, BJ, BLK = 20000 外迭代**; LSMR, PCG8P, PCG8D = 5000 并标 "safety-censored"。
- A2 (Q3): **容差规则由 #11 取代** (原 1e-6 对本系统按构造被删失); 其余保留 (λ=1e-3, η=0 主 / κ=1e-3 副, 第 5 次外迭代状态由 κ0=1e-3, f=10 的 LSMR 外迭代生成, 显式增广系统残差测试, atol=btol=0, maxiter=20p)。**补记 (f553 Q-e)**: 每个状态的 η=0 逐状态斜率描述性报告, 状态间符号相反则标注。
- A3 (PCG8D): 严格与缓存两种 n_A 与 W; 运行到缓存计量越过 A_cap 与 W_cap; 终值在两读数下都报; 不进任何判定。
- A4 (y-only 配对): **逐字补记: λ_DP 在每个 held-out 单元上仅由 y 计算** (与 λ\* 运行同预算同停止规则的 GEO 终点, 同一初值; λ_DP=网格 {1e-6,…,1e-1} 内满足 ‖y−Ax‖²≤N²σ_n² 的最大 λ; 无格满足 → "DP-infeasible", λ_DP=1e-6; 满足集合在 λ 上不连续 → "non-monotone"; 按 (K,条件) 报 infeasible 率、non-monotone 率、τ=1 臂触发率; 任一分层 infeasible>50% → "y-only pair uninformative (model-misfit floor)")。仅描述; Q1 判定用 λ\* vs τ\*。
- A5: BJ 步 δ=α·Σδ_k, α 见 #7, α\* 与 α 逐步记录并报告 α\*>1 的比例; BLK 每块至多 10 次回溯 (均计数), κ_k 跨扫描携带, 仍拒绝的块本扫描跳过 (skip 率记录)。**A5.3 被取代**: K=1 时 BJ (含 min(1,·) 上限) 与 BLK 须与 GEO 在 20 次外迭代内相对差 ≤1e-12 精确一致 (测试 V7); 另保留 α_one 变体测试。新增 V8 (计数约定与 W 确定性)。

## K1.4 偏离/自选 (最终形式; f553 审定)
- **#6 ε-活动集冻结 (所有臂)**: 每次外迭代开始时, 对距箱界 ≤ε=1e-3 (参数单位) 且下降方向 −∇F 指向界外的坐标 (下界处 ∇F_i>0, 上界处 ∇F_i<0; 幅度 w 无界) 冻结: Jacobian 与 AJ 对应列置零, 步分量置零, 其余坐标照常求步、夹取、接受。取代草稿的 1e-12 绝对容差。日志: 每迭代 |I| (act)、每迭代被夹取坐标数 (clamp_it, 此时必不在 I 内)、stop 标签 `no_step_clamp` (死亡连串内任一试探有夹取坐标时用此标签, 否则 `no_step`)。HIST 不改。C14 的 GEO 特有失效模式触发扩展为: 调参后 GEO 的拒绝率或箱触发率 ≥3×LMD, **或** 平均 |I| ≥3×LMD, **或** `no_step_clamp` 率 ≥3×LMD (且 >0)。**C14 各比率均按每次试探定义: 拒绝率 = 被拒试探数/全部试探数; 箱触发率 = 含 ≥1 个被夹取坐标的试探数/全部试探数。若 C14 在 dev (λ=1e-3) 上对调参后 GEO 触发, 则两个 K 层的 Q2 均为 JOINT-NOT-MATTERS (GEO-specific failure mode; not Q2 evidence, 合同 §7); GEO-r8 的 C14 仅作信息。**V3 子测试: 距界 1e-6 内且下降方向向外的坐标必须被冻结且步被接受。
- **#7 BJ 松弛 α=min(1,α\*)**: α\*=未阻尼二次模型沿 J(Σδ_k) 的闭式最优标度 (0 次额外 A)。α\*≤0 或非有限 = 被拒试探 (κ←fκ, 0 次 A, 不求 F)。K=1 时 α≡1, BJ 与 GEO 一致 (测试精确到 1e-12)。
- **#8 rcond 调参 (GEO 族) + GEO-r8 + 双 V-pass**: GEO, BJ, BLK **各自独立**选 (rcond∈{1e-8,1e-4,1e-2})×(f∈{3,10}), κ0=1e-3 固定; 预算相等 (6 组合)。GEO 在**校准模式** (≤200 迭代/收敛; 披露与预算运行的视界差异) 下调参, 先于 caps; BJ 与 BLK 在 caps 冻结**之后**以**预算模式**调参。LMD/LSMR/PCG8P/PCG8D 用 κ0∈{1e-4,1e-3,1e-2}×f∈{3,10}。GEO-r8 = 合同原规格 rcond=1e-8 (f 取 rcond=1e-8 组合中 dev 较优者), 描述性 (C14 仅信息)。V2 测试须在三个 rcond 值上各跑一次。**V-pass 为双重**: (i) 冻结规格: GEO-r8 与 LMD 在 96 个 dev 单元 (λ=1e-3, 预算内) ≥95% s≤0.1; 若 GEO-r8 不达标, 立即写 FAIL "STOP-GEO-V under the frozen spec (rcond=1e-8): Euclidean minimum-norm back-substitution amplifies weak directions", 且不被 (ii) 抹去; (ii) 修订: 调参后 GEO 与 LMD ≥95% — (ii) 通过才放行阶段 H。此后所有 Q2/ADVANCE 标签附注 **"[amended-V; GEO = rcond-tuned, not the frozen §1 step]"**。
- **#9 代码选择 (记录)**: LMD/PCG8D 的 λ_LM 极限 1e8, 其余 κ 极限 1e4; 停止规则 `κ≥极限 且 连续失败≥2` (BLK: 连续 3 次扫描无被接受块); LMD 稠密解 LinAlgError 回退: λ←fλ, 记一次拒绝, 不求 F; LSMR maxiter=p。
- **#10 计算方案** (只依赖实测成本): (i) 调参子集 S_tune = 图 101-106 × 条件 {C1,C4} × K {16,36} = 24 单元, 准则 = 预算终点 s 的几何均值 (F_ref 在评估端由该单元全部 dev 运行取最小, 含 LMD-500×3 重启)。(ii) λ 网格 {0,1e-6,…,1e-1} 与 τ 网格在 96 dev 单元上跑。(iii) 阶段 H: Q2 臂 (LMD, GEO, GEO-r8, BJ, BLK, LSMR, PCG8P, PCG8D) 在 F_a(λ\*) 上, base 9201, 24 图×4 条件×2 K; Q1 臂 (GEO@λ\*, F_0+GEO 收敛/DP(τ\*), F_0+LMD+DP) 跑 9201 与 9202; F_ref 重启每单元都做。(iv) y-only 配对 (图 201-212, 9201); (v) 独占墙钟子集 (图 201-212 × 4 条件 × 2 K × 9201 = 96 单元, GEO/BJ/BLK/LMD, 2 次重复取均值, 单线程独占); (vi) **压缩次序 (新, 取代草稿)**: 在阶段 D 末**一次性**计算 (在任何 H 作业前, H 内不再改): 投影 = Σ (dev 单元中位 CPU 秒 per cell per arm 与 K) × 单元数 × 1.2; 若投影 >40 CPU-h **或** 推算完成时刻 (now + 投影/2 并发 + 独占阶段时长) 晚于压缩截止时刻 (K1.6), 依次: (1) 描述性臂 LSMR/PCG8P/PCG8D 只跑图 201-212; (2) HIST 只跑 201-212 (HIST 未实现, 见下); (3) y-only 配对减半至 201-206; (4) 计时子集减半至 48 单元 (201-206); (5) Q1 臂去掉 base 9202。F_ref 重启与 V 测试永不削减; 每一步及其投影记录在 choices.json['plan'] 并追加到 STATE; 压缩截止时刻取 K1.6 的值。(vii) 并发 ≤2 作业, 单线程 BLAS; 计时子集在其余作业全部结束后独占运行。**阶段 D 的 CPU 用量如实记录。**
- **偏离: HIST 与 Tikhonov 行未实现**。合同把二者列为描述性/历史对照, 不进任何判定。截至本记录均**未实现**, 这是对合同文本的一项偏离 (不是成本触发的压缩); 它们在报告中写作 not run; 仅当主流程全部完成且有余量时才补做 (补做需另行追加记录, 且不得影响任何已冻结判定)。
- **#11 阶段 L 容差规则 (取代 A2 的单一 1e-6)**: 每 (规模, 状态, 阻尼) 一次 LSMR 运行 (atol=btol=0, maxiter=20p 不变), 记录显式相对法方程残差首次 ≤tol 的迭代数, tol∈{1e-2,1e-3,1e-4,1e-6}; 1e-6 仅报告; 1e-3 为报告的头条容差, **在任何标签里无额外作用**。**INCONCLUSIVE (=ADVANCE 的 FLAT)** 若 η=0 时 1e-2/1e-3/1e-4 任一在 5 个规模、2 个状态中的**任何一处**被删失 (斜率用全部 5 个规模)。**BOTTLENECK-OPTIMISABLE** 当且仅当 η=0 时: (a) (aj+solve) 时间份额在两个最大规模均 ≥50%; 且 (b) 在 1e-2、1e-3、1e-4 **每一个**容差下: 各规模 (两状态平均) log 迭代数对 log K 的 OLS 斜率 ≥0.25, 其 95% t 区间 (df=3) 不含 0, 且 5 个留一规模斜率均 >0。否则 jac 份额 ≥50% (两个最大规模) → ASSEMBLY-BOUND, 否则 FLAT。份额 (a) 每规模测一次, 与容差无关, 取 LSMR 臂自身的外迭代设置 (atol=btol=1e-10, maxiter=p, conlim=1e12), 3 次独占重复 × 2 状态共 6 次的逐阶段中位数, **不得**取自带额外残差测试的多容差运行; 记录外迭代触及 maxiter 的比例。描述性报告: 逐容差/逐状态/κ=1e-3 斜率、1e-6 删失图样、增广系统 cond 估计 (LSMR 内部 Fong-Saunders 估计, 仅描述)、残差测试的开销 (不计入任何计时)。maxiter 在看到任何更大规模的计数后**永不上调**。
- **λ\* 预算充分性检查 (Opus 补充 (1))**: 超参与 A_cap(K), W_cap(K) 在固定目标 λ=1e-3 下调参/标定, **不**对 λ\* 重新标定。λ\* 与 τ\* 冻结后, 在 96 dev 单元上各按其 (条件,K) 的 λ\* 做检查: 复用 λ 网格中已有的 GEO 预算运行, 另加每单元一个 LMD 预算运行与 λ\* 下的 F_ref (LMD-500×3 重启), 约 0.5 CPU-h; 判据 = 修订 V-pass (GEO 与 LMD 各 ≥95% 单元 s≤0.1)。若某 K 层不过: 该层 Q2 = INCONCLUSIVE (对 ADVANCE 等同 JOINT-NOT-MATTERS), 标注 "budget calibrated at λ=1e-3 insufficient at λ\*", 该层 Q1 带同标注, caps 不改。同时报告 GEO 在 λ\* 与 λ=1e-3 下按 (条件,K) 的停止原因分布 (cap/converged/no_step/no_step_clamp/safety)。

## K1.5 判定读数 R1-R6 与审定的补充规则 (阶段 H 判定前冻结)
- R1: s 在 A_cap/W_cap 处 = 工作计数 ≤ 上限的**最后一个已存迭代**的 s (不插值); 提前停止 (收敛/no_step) 的臂把终值 s 向前携带; PCG8D 取缓存计量。**每个迭代都存** (无稀疏化)。
- R2: A_cap/W_cap = 每个 K 层 48 个 dev 单元上调参后 GEO 校准运行的中位数的 5 倍, 所有停止原因计入并报告。
- R3: s 的几何均值用 max(s,1e-6)。
- R4: 分句 (a) 统计量 = exp( 图像级均值 ( 每图在共同达到 s≤1e-2 的单元上 log(GEO 功/他臂功) 的均值 ) ) ≤0.5, 对 BJ、BLK **分别**且对 n_A、W **分别**, 即 4 个条件须**全**成立; 一个 K 层内需 ≥12/24 幅图有共同达到的单元, 否则 (a) 为假; 报告 df=n_img−1 的 t 区间。
- R5: 分句 (b) 逐臂: (s_BJ>1e-2 的单元比例 ≥25%) 或 (s_BLK>1e-2 的比例 ≥25%), 且 GEO 的比例 ≤10%; 在 A 读数与 W 读数下**均**须成立; 比例按各 K 层单元计; 报告比例的同时报告原始单元计数。
- R6: 质量条件 H(GEO vs BJ) 的 95% t 区间下界 ≥−0.02 须在 A_cap 与 W_cap 两个读数迭代处**都**成立 (运行时存这两处的 θ); 对 BJ, BLK 仅报告。
- R-censor (Q-f): 处于安全上限的单元在两臂配对比较中按**共同水平** W_c=min(W_cap, 任一被安全截断臂的 W_end) (A 同理) 读数; 收敛/no_step 的臂向前携带终值 s; 逐臂逐 K 层报告删失率; 任一决策臂 (GEO, BJ, BLK) 在某 K 层删失率 >10% → 该层 Q2 = JOINT-NOT-MATTERS。
- Q2 = JOINT-MATTERS 当且仅当两个 K 层各自: λ\* 预算检查通过 ∧ 无删失否决 ∧ (分句 (a) ∨ 分句 (b)) ∧ R6 ∧ 墙钟同向。
- **墙钟 "同向" 的数值定义 (新, 取代草稿)**: 在计时子集的每个 K 层, 对 (GEO, X), X∈{BJ,BLK} **分别**: 取 GEO 与 X 共同达到 s≤1e-2 的单元; 对 t(计时重复均值)、n_A、W 三个量, 取首次 s≤1e-2 迭代处的 log(GEO/X), 先在图内平均再在图间平均; 三个均值**同号且均为负 (GEO 更省)** 才算同向。若共同达到的图 <6 幅, 改用墙钟版分句 (b): t\* = GEO 到 s≤1e-2 的时间; X 在 t\* 处 s>1e-2 的单元比例 ≥25% 且 GEO 未达 1e-2 的比例 ≤10%。两次重复取均值。
- Q1: 判定规则不变 (合同 §7); 图 201-212 之外与 base 9202 若被压缩则按 K1.4 #10(vi) 执行并如实标注。

## K1.6 计算方案、时钟与压缩截止 (Opus 终审 6dd4 ACCEPT-WITH-CHANGES, 措辞按其审定)
- **K1.6 时钟 (Opus 终审 6dd4 审定措辞)**: 48 h 时钟只计主动时间。已用: 2026-11-06T06:38:08Z → 09:04Z = 2 h 26 min (取较晚的停摆起点, 因而高估已用时间)。限额停摆: 2026-11-06T09:04Z → 2026-11-08T00:41Z, 不计入 (期间没有作业运行、没有任何结果可见)。恢复时剩余 45 h 34 min。截止 2026-11-09T22:15Z; **压缩截止 2026-11-09T18:15Z** (=截止-4 h, 沿用原规则), 即传给 geo_analyze.py plan 的值。压缩计划只在阶段 D 末、对该压缩截止计算一次, 之后**永不重算**。此后任何停摆 (限额, 或宿主 pump 停机) 按其 date -u 实时记录的起止长度**机械地**把两个截止都顺延同样长度; 这样的顺延**不触发**重新规划、**不撤销**已作的压缩、**不增加**任何运行; 不允许其它任何形式的延期。这是预算/时钟决策, 不依赖任何结果。
- 推算完成时刻 (压缩判据): finish = now + (cpu_h - timing_h)/2 + timing_h + extra_h (两个并发作业, 独占计时子集单独占墙钟); extra_h = 计划计算之后仍要运行的阶段 (L 与 λ* 复查) 的墙钟小时数; 投影含 base 9202 的 F_ref (保留 9202 时)。
- 若限额再次耗尽或宿主 pump 无法恢复, 如实暂停并记录 (按上条机械顺延), 不静默延期、不付费、不开 ExtraUsage。
- 宿主 pump 需真人双击 scripts\start-pump-loop.cmd 启动; 在其恢复前, 宿主作业 (V 重跑、L、D、H 正式运行) 一概不开始; 与宿主无关的收尾 (代码/记录同步、容器内测试、干跑) 可先做。

## K1.7 阶段 L 暴露披露 (逐字, 来自 Opus 要求)
- 在本规则定稿之前, 协调者在正式实例 (32,36) 与 (64,144) 上看到了 η=0 的首次命中计数 (两个状态、四个容差) 与 1e-6 的删失: tol 1e-2: (32,36) grid 88 / iter5 49; (64,144) grid 182 / iter5 114。tol 1e-3: 320/237 与 635/623。tol 1e-4: 1533/1094 与 3886/3919。tol 1e-6: (32,36) 删失。
- 由此推出的两点斜率 (Δlog K=log 4) 在 0.49-0.92 之间, 全高于 0.25 (grid/iter5: 1e-2 0.52/0.61, 1e-3 0.49/0.70, 1e-4 0.67/0.92)。
- 阈值 (0.25, df=3, 留一斜率>0, 50% 份额) 在暴露之前已冻结, 未改变; 容差集合 {1e-2,1e-3,1e-4} 在暴露之后选定, 但要求三者全过是更严的读法。
- 本日在改后代码上重跑了这两个实例 (冒烟, 容器): **计数与上述完全一致**。正式阶段 L 从头重跑这两个实例, 计数须与此一致, 任何不符记 FAIL。(80,225)、(96,324)、(128,576) 的任何计数在本规则与 geo_L.py sha 冻结前未被查看。

## K1.8 开发期暴露清单
开发期 dev 基准 (K1.2) 看过 dev 图 101、102、103 上各臂 200 迭代的 F 终值 (无 F_ref、无 s、无质量); 窄审 Opus 副本另看过 3 格 200 迭代校准模式结果, 不作阶段 D 数据。冒烟 (K1.2 末) 同上。

## K1.9 冻结清单 (sha256; 该时刻容器版本 = 提交到 D:\Gaussian 的版本)
- src/geo_core.py e92732df923456bb8def96978304184752a00d58b897e4545abd43210c15fbc4 (core-v2; core-v0 = 设备上原文件 sha 1044a3f84093a9faa94d331b25f1d7dc0edf7fdb0ca045d98c95f37308d5983b, 归档于 research/frozen/geo_core.core-v0.py)
- src/geo_flops.py 076a0a61a5711df93236e04217114631747d43ade2713778a11cab4fa55d7bd3
- src/geo_gen.py 93f42252e3377a11e538d5361b7225ed766422b267d2019eb18bcce8d8eefeda
- src/as_core.py af9d525d7740022ebb423222f2b34e09b32bd949a810e3b412dcf503e74dc0f9
- src/as_gen.py e5d086786c0e042243f1466680d3e12188469dd0ad4ffc70b7e5aef670363d59
- tests/test_geo_core.py 67e33353eff1e06f7e7fdda059bd0dc732c7873ddcf9a5e5fa857f53bfebc1ca (18 项)
- experiments/geo_run.py 55a75a860bf5f87a2e6ab90707a94d33eab9ebda330e93c1270cb1cf1114151b
- experiments/geo_analyze.py c82382c4ac09ca501f381492cfa55cfc92cee03f7dc5ac6c719fd32fc3b4d6f7
- experiments/geo_L.py 5726d9b790470d9ee0aecd0be252eafccc4f4fe024f4622738c0ff8caf43c98e
- experiments/geo_vtests.py abfd33eca49e8859bcf4a242774de59fba5a22b3e60bc340e0f587a7d5c959d8
- 干跑 (缩小配置, 容器, 非正式): D 与 H 全流程及全部分析命令 (select_geo/caps/select_arms/vpass/vpass_lam/select_lam/plan/h_q2/q2_quality/h_timing/q2_label/h_q1) 与 cmd_l_report (合成 5 尺寸记录) 无报错; 干跑数值不作任何科研判定。
- 冻结顺序: 先本记录与 sha → (K1.6 的 pump 恢复) → 主机 V 重跑 (K1.10) → L → D → H。**src/geo_flops.py 的 sha 在任何阶段 D 作业开始前即在此记录** (公式表冻结)。

## K1.10 运行与审查登记
- 真实 Opus 窄审: run 20261106T064027Z-opus-review-8d02 (A1-A5); run 20261106T070937Z-opus-review-f553 (K1 草稿 Q-a…Q-f + 补充 (1)(2); 自报 claude-opus-5-5; 本日已按其返回结果补关该 run, 状态 ok)。 真实 Opus 终检: run 20261108T005204Z-opus-review-6dd4 (自报 claude-opus-5-5; ACCEPT-WITH-CHANGES; 其必改项已全部落实于 K1.1-K1.9 与代码; 审查与问答文本归档于 research/notes/ (OPUS_REVIEW_GEO_PRED_ADDENDUM_20261106.md 与 OPUS_PACKET_GEO_PRED_ADDENDUM_20261106.md))。
- 主机 V 重跑 (K1.1 所述), 待做, run id 见后续追加。
- 失败登记: FAIL-0026 (含 2b 与安全上限绑定); 如发生新的失败当场追加。

## K1.10 追加 (2026-11-08T02:40Z, date -u): 宿主 V 重跑完成
- pump 已由真人恢复 (新 PID 24768, heartbeat 2026-11-08T02:39:40Z); 宿主 V 重跑 job j86-geo-vtests-k1 (runlog run 20261108T023951Z-host-py-2af0), 02:39:52Z-02:40:07Z, exit_code 0, **18 passed** (python 3.12.10, numpy 2.5.4, scipy 1.18.1, pytest 9.2.0); 记录 outputs/GEO-V/V_RESULT_K1.txt, 其中 10 个冻结文件 sha 与 K1.9 清单逐一一致。
- 下一步: 阶段 L (独占, 单 job, 不与任何其它 job 并发), 然后 D、H。

## K1.11 追加 (2026-11-08T02:40Z, date -u; 写于任何阶段 L/D/H 正式结果可见之前): 干跑暴露披露
- 容器内两次缩小配置干跑 (K=16: tune/dev 图 101,102, H 图 201-204, 条件 C1/C4; K=36: tune 图 101, dev 图 101,102, H 图 201-203, 条件 C1; 安全上限降为 300-1500/150-500 以求快) 在**真实 H 图 201-204 上**运行了各臂并打印了分析输出 (删失率、clause 布尔值、质量 H 与区间、wall-clock 比值、Q2/Q1 标签等)。这些数值来自被大幅缩小且人为删失的配置 (多数决策臂被 safety 删失), **不作任何科研判定**, 正式 H 仍在冻结选择与全部 24 图上一次性运行。
- 干跑之后没有基于其输出修改任何判定规则或阈值; 干跑发现的唯一代码改动是 cmd_plan 中图像数 min(12, len(TEST_IMGS)) 的健壮性修正, 对正式配置 (24 图) 行为不变。冻结 sha 清单 (K1.9) 在该改动之后计算。
- 干跑看到的定性现象 (非证据): 冻结规格 GEO-r8 (rcond=1e-8) 在缩小 V-pass 上未通过而 rcond 调参后的 GEO 通过, 与开发期已知的 GEO-r8 停滞一致 (FAIL-0026 路径); H 图 201-204 的 BJ/BLK/GEO 数值不得用于调参。

---

# 追加冻结记录 K2 (预 H; 追加于 K1.11 之后, append-only) — 干跑暴露后的解读边界

写于 2026-11-08T03:24Z (date -u); 此刻没有任何阶段 H 的正式结果可见 (阶段 D 进行中: tune_geo、F_ref(tune)、select_geo、calib_caps、caps 已完成, tune_arms 在跑)。

## K2.1 事实与时间线 (见 FAIL-0029 与 K1.11; 时间取文件时间戳与 date -u 记录)
- 容器干跑 #1 (K=16, 图 201–204, 条件 C1/C4, 缩小配置): 约 00:59:13Z 起, H 阶段作业 01:03–01:20Z, 分析值于约 01:20:47Z 打印。此前 00:55Z/00:59Z 的两次更早干跑没有到达 H 阶段。
- 真实 Opus 终检 6dd4: 00:52:04Z 启动, 回执在约 01:10Z 前已取得 (run 状态 01:22:55Z 才补关); K1 冻结记录 (K1_FINAL 占位符填写 01:21:52Z, 设备 sha 记录 01:22Z) 晚于干跑 #1 的打印。
- 容器干跑 #2 (K=36, 图 201–203, 条件 C1): 01:27:35Z–01:38:30Z, **晚于 K1 冻结记录**; 此后冻结文件未变 (宿主 V 重跑 j86 于 02:39–02:40Z 记录的 10 个 sha 与 K1.9 清单逐一一致)。
- 6dd4 回执之后对代码/文本的改动: 6dd4 的必改项 (reject_rate 按试探次数归一、load_q2 保留 λ=0 运行、q2_label 先查 C14、cmd_plan 完工公式与 F_ref 基数、配对原始计数、K1_FINAL 文字) , 另加两处由干跑的**执行错误** (非打印数值) 触发的稳健性修正: select_arms 的 round(v,4) 打印 TypeError, 以及 cmd_plan 中 min(12, len(TEST_IMGS)) (对 24 图配置无影响)。没有任何改动由干跑打印的数值/标签/区间触发; 无判定规则或阈值改动。
- 图 205–224 (20 张) 的任何分析值均未被看到; 其 H 作业尚未运行。

## K2.2 解读边界 (不改任何指标、阈值、配置; 不重跑已完成阶段)
1. **主读数**: 冻结的全 24 图指标与判据 (K1 R1–R6、Q-f 及其余) 不变, 仍是 Q2/Q1 的正式读数。**全 24 图不得称为 "全程未见的独立证据"**; 正式描述为: 24 图留出集, 其中 4 图 (201–204) 有干跑分析暴露 (FAIL-0029); 唯一全程未见的读数是 205–224 的 20 图读数。任何报告在首次出现 H 结果的位置必须附带该披露。
2. **预先登记的 "未暴露 20 图 (205–224)" 读数** (仅报告, 同口径): 同一冻结读数 (h_q2/q2_quality/h_timing/q2_label/h_q1) 仅在图 205–224 上重算, 由 experiments/geo_analyze_unexp.py (导入未改的 geo_analyze.py; sha 见 K2.3) 实现。图像数下限按同一 50% 比例、按**设计**数 (非实际存在的文件数) 缩放: MIN_IMG_A = ceil(0.5×设计中的未暴露 Q2 图数 (=20)) = 10 (冻结的是 12/24); 计时: 按 plan['timing_imgs'] 的设计未暴露计时图数 (h12→8, h6→2), 该设计数 ≥4 时 MIN_IMG_T = ceil(0.5×设计数) (冻结的是 6/12), 否则计时分量不可评估。实际图数少于设计数 → 该读数 NOT EVALUABLE (各 K 层标签与总体均记 NOT EVALUABLE)。其余数值阈值 (0.5、25%、10%、−0.02、1e-2、10% 删失等) 一律不变。
3. **公开区别**: 每份报告同时给出 24 图 (主) 与 20 图读数, 并写明: 图 201–204 的干跑分析值曾被看到 (缩小/删失配置), 图 205–224 未被看到; 两读数的差异 (若有) 须明示。**20 图读数是同一样本的子集, 不是独立重复**; 一致只说明标签不依赖暴露的 4 图, 不构成确认。
4. **一致性规则**: 20 图读数只能降级, 不能升级任何标签。标签按类别比较 (JOINT-MATTERS / JOINT-NOT-MATTERS / INCONCLUSIVE; REG-HELPS / REG-HURTS / REG-NEUTRAL), 忽略原因后缀。若任一 K 层的 Q2 标签类别或 Q1 标签类别在两读数间不一致, 或 20 图读数 NOT EVALUABLE, 则判定 "结论依赖已暴露的 4 图": 一切正向/有方向结论 (Q2 JOINT-MATTERS/ADVANCE, Q1 REG-HELPS/REG-HURTS) 不得写成 ADVANCE, 留待全新数据确认; 中性/负的主标签照原样报告, 并列出两读数与差异。
5. 阶段 D 的全部选择 (caps、λ*/τ*、臂与 rcond 调参、压缩方案) 只用开发图 (101–112) 与基 9101 决定, 与图 201–204 的干跑输出无因果路径; 若仍有人认为存在路径, 以第 4 条为保险。
6. 若阶段 D 末压缩步 (4) 触发 (计时子集降为 201–206), 未暴露计时图仅 205–206 两张, 20 图 Q2 读数 NOT EVALUABLE, 因而 Q2 不可能 ADVANCE; 此后果在计划计算前登记, 计划规则本身不改。
7. 操作约束: 首个正式 H 作业提交之前, 本 K2 与 geo_analyze_unexp.py 的 sha 已追加并提交; 提交前在宿主确认 outputs/GEO-H 为空且 choices.json 来自正式阶段 D; 20 图脚本与主读数 q2_label/h_q1 在同一会话内先于任何 H 文字运行, CONSISTENCY.json 与 Q2_LABEL.json 并列报告; 不再翻看 201–204 的干跑打印输出 (/tmp 下的干跑日志与输出不再打开)。

## K2.3 登记
- geo_analyze_unexp.py sha256 30602d09dff634cc919b776e6f8297e827a8a4075ed91abf57938bc5a6d0666a (geo_analyze.py 仍为 K1.9 的 c82382c4…, 未改)。
- FAIL-0029 已记 (处理与上同); FAIL-0030 (caps 在 calib 未完成时提交, 使用前已更正) 同日记。
- 真实 Opus 审查 run 20261108T031755Z-opus-review-cd1a (自报 claude-opus-5-5): 见 K2.4。

## K2.4 Opus 确认 (摘要; 全文见 research/notes/OPUS_REVIEW_GEO_PRED_ADDENDUM_20261106.md 末节 "K2 exposure-boundary check")
- Q-k1 ACCEPT-WITH-CHANGES (加入: 20 图是同一样本子集非独立重复; 正向描述 24 图集合; 20 图读数只能降级); Q-k2 ACCEPT (同 50% 比例换算合法; 图数取设计数); Q-k3 ACCEPT-WITH-CHANGES (加入时间线、"6dd4 后改动仅为必改项"、压缩步 (4) 的后果); Q-k4 ACCEPT-WITH-CHANGES (规则保持作用于全部标签; 修 Q1 一致性检查的键类型 bug、按类别比较、计时不可评估时逐 K 标记、用设计图数); Q-k5 四项操作约束 (见 K2.2 第 7 条)。以上必改项已全部落实于本 K2 与 geo_analyze_unexp.py。
