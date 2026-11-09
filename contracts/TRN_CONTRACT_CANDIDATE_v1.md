# TRN 合同候选 v1 — 观测+正则度量下的跨步子空间输运 (候选, 未冻结; 吸收 Opus 审 v0 的 REVISE 必改项 M1–M5 与建议项)
起草: Sonnet 5.5, 2026-11-08 (run 20261108T090408Z-experiment-f602)。v0 sha256 7b14f4a5…c5fc; Opus 原文 research/notes/OPUS_REVIEW_TRN_CONTRACT_v0_20261108.md (自报 Claude Opus 5.5, run 20261108T090948Z-model-call-4034)。v0→v1 对照: contracts/TRN_CONTRACT_v0_to_v1_DIFF.md。
地位: 一切主张均为 proposed; 0 已验证贡献; 不保证原创性或分数。数值阈值已改为**先验固定** (来自 Astra 的提议值经 Opus 审阅后固定), dev 只能选 k、r、n_tr、ε_r。

## 0. 研究问题与主张边界
固定数量 K 的 2D Gaussian、已知核 A、持续图像正则目标 F_a 不变 (继承 GEO)。问题: 在 GN/LM 外层迭代之间, 内层线性化问题的有效求解子空间能否 (i) 便宜地跨步输运、(ii) 用少量学习修补补齐剩余耦合, 使**同等画质与目标**下的端到端成本下降? 主张只可能是: "在预注册条件下, 方法 X 相对最强确定性对照 Y 的端到端工作量(及墙钟)净比为 R (CI), 画质与目标等价"。**不**主张: 通用性、原创性、全空间谱界 (Feng–Kao 2602.09415 已撤回, 不作依据)。
三个分开的问题: Q-A 成本结构 (Amdahl); Q-B 同状态子空间输运价值 (含理想上界与隔离链); Q-C 闭环端到端净收益。学习修补 (TRN-5) 只在 §7 终态表指向 TRN-5 时开启。

## 1. 固定对象 (继承, 不改)
- 目标: F_a(θ)=1/(2σ²)||y−A x(θ)||²+a/2||x||², x_ref=0, a=lam/σ² (主 lam=1e-3; lam 敏感性延后), x(θ)=Σ_k w_k exp(−½(u−m_k)ᵀΣ_k⁻¹(u−m_k)), Σ=LLᵀ, θ_k=(w,mx,my,l11,l21,l22), K 固定; A=B⊗B (可分离反射边界高斯模糊, 已知)。冻结代码: src/geo_core.py (e92732df…15fbc4)、src/geo_flops.py (076a0a61…bd7d), 只读 import。新代码只放 src/trn_*.py、experiments/trn_*.py、tests/test_trn_*.py。
- 条件 C1–C4 = (sb,σ) ∈ {(1,0.01),(1,0.03),(2,0.01),(2,0.03)}。
- 内层问题 (状态 θ, 阻尼 κ): Λ_A=‖A‖₂²/σ² (代码 LamA=normA²/σ², normA=‖B‖₂²=‖A‖₂; **v0 笔误 ‖A‖₂⁴ 已更正**), η=κΛ_A, c=a+η; J=截断 (Mahalanobis 半径 4) 稀疏图像 Jacobian (geo_core.render_jac_sparse; 所有 arm 共用同一算子, 截断误差 ~e⁻⁸ 量级); H=Jᵀ(AᵀA/σ²+cI)J, g=Jᵀ(Aᵀr/σ²−a x); 二次模型增益 Δq(δ)=gᵀδ−½δᵀHδ **含 η**。注: 冻结接受器 _accept 的 pred 用**不含 η** 的模型 (仅 a) — 两者不同, 报告时分开, 闭环以冻结接受器为准。
- 受界 ε-active 集 (geo_core.bound_active, 下降方向取 −g) 上的坐标冻结 (向量在自由坐标上, 全 p 向量带掩码); 活动比例 >10% 的状态单独标记报告。J 的零列坐标 (‖J_i‖²<1e-12·max) 同样视为冻结并披露。
- 步接受/回溯/κ 规则沿用 geo_core._accept/_finish (冻结) — 所有闭环 arm 共用同一接受器。κ 取法: 同状态研究中, 状态 θ_t 的内层问题用**由 θ_t 走出的被接受 trial 的 κ** (评测侧重放冻结 GEO 步, 通过包装 geo_core._finish 记录 ok 时的 kap, 不改冻结代码); 不使用 _finish 更新后的 S['kappa'] (=κ/3)。

## 2. 数据与边界 (新; 与旧 GEO/AS/F0/CF0 完全不相交)
- 禁用: 1–24, 41–58 (旧/封存); 101–112 与 201–224 (旧 GEO dev/测试, 其中 201–204 因 FAIL-0029 已暴露)。图像由 as_gen 同族配方的 32×32 瓦片 (edge/tex/mix, family=(i−1) mod 3) 镶嵌到 N=32·q (保持局部统计、Gaussian 密度 K/N² 与 sb(像素) 不变); 种子键 tag 10 (瓦片) 与 11 (噪声), 与 geo_gen tag 0–3、as_gen 7100+i 不相交 (V5 式断言, 已在 src/trn_gen.py)。
- **dev-sel** 301–312 (噪声 seed 9401): 全部超参选择 (k、r、n_tr、ε_r) 与 S0 分账; **dev-chk** 313–320 (seed 9401): 选择偏差复核, 不用于选择; 二者不出现在 confirm 结论里。
- **confirm-det** 321–344 (seeds 9411, 9412): 仅用于确定性主张 (G-C, G-E-det), **只用一次**, 冻结全部代码/分析器/判据之后。加载器 (src/trn_gen.py) 在冻结前拒绝读取; 冻结后解锁条件 = 环境变量 TRN_CONFIRM_UNLOCK=1 **且** contracts/TRN_FREEZE_RECORD.txt 含分析器 sha **且**含冻结后追加的 CONFIRM_UNSEALED 行 (缺任一项拒绝)。所有干跑只允许 dev-sel/dev-chk 或 ladder 合成目标; 不得打印任何 confirm 图的值 (FAIL-0029)。
- **train-pool** 351–398 (seed 9451; 仅 TRN-5); **confirm-TRN5** 401–424 (seeds 9461,9462; 现在就预留、封存, 代码断言禁读, 与 321–344 不共用); held-out 核族 KF-B (各向异性可分离高斯 (sbx,sby)∈{(1,2.5),(2.5,1)}, 可分离盒核宽 5) 在 TRN-5 合同附录冻结前不打开。
- 规模: S=(N=32,K=36,p=216), M=(64,144,864), L=(96,324,1944)。评测器 (含干净图的 PSNR) 只在评测侧; 方法侧不得 import trn_gen.clean_image_trn (V5)。

## 3. 状态来源
参考轨迹: 冻结 GEO 精确步 (geo_core.solve('GEO',…,keep_theta=True), rcond=1e-4, f=3, kappa0=1e-3, max_iter=40) 自 grid_init 出发。同状态研究取相邻对 (t−1→t), t≥1; **晚期状态剔除规则**: Δq(δ*)<1e-6·F_t 的状态单独列表, 不进主中位数。L 规模裁剪 (Opus Q9): 4 张图×(C1,C4)×每 4 个状态取 1 个; M 全量; S 全量。同状态研究内部用稠密 H 完成数值乘积 (与矩阵无关乘积数值等价), 工作量 W 仍按公式记。
闭环: 各 arm 沿自己的轨迹 (§6)。

## 4. 同状态 arm 集与定义 (统一在 (H_t,g_t) 上)
**谱量 (M2)**: 全部特征量在 Jacobi 广义谱上: H v=λ D v, D=diag(JᵀJ) (自由坐标), VᵀDV=I, τ=1e-8·λ_max; δ*_τ=Σ_{λ_i>τ} v_i(v_iᵀg)/λ_i; 误差只在该子空间上按 H 范数度量 (‖e‖_H²=eᵀHe, Δq(δ*)−Δq(δ)=½‖δ−δ*‖_H² 已数值核对)。能量 e_i=(v_iᵀg)²/λ_i, Σe_i=‖δ*_τ‖_H²。D1 = λ_i>τ 中最小的 k 个; D1e = λ_i>τ 中能量最大的 k 个 (区分"真正影响当前解的方向 r_eff(95%)"与"参数冗余")。
**求解器**: A-DEF2/初值投影型 deflated PCG: x0=U E⁻¹Uᵀg, 预条件残差作 z←(I−U E⁻¹(HU)ᵀ)P r; U 先在 H 内积下正交化, E 中特征值<1e-12·max 的列丢弃; HU 只算一次 (k 次 H 乘积, RR 与 deflation 共用); 每迭代附加 4pk+2k² flops。预条件 P_J=diag(JᵀJ)⁻¹ (无 A 施加)。秩预算 k∈{8,16}; (k=32 延后)。
**Arms**:
- 无子空间/预条件类: D0 PCG-J; **D0w** 热启动 (x0=上一步 δ 限制到当前自由坐标, 秩 0, 零成本); D0b 6×6 块 Jacobi (块由 AJ 列组严格构建, 成本 p 次 A 施加 + Gram 全计); **D0c** 解析块预条件 (Gaussian 模糊的 Gaussian 闭式 Σ_k+sb²I 给出 AJ_k 的 6×6 块, 代价约一次 render; 须先有限差分验证数值一致否则丢弃并披露; KF-B 盒核无闭式则退回 D0b); **D0s** 固定结构粗空间紧缩 (每 Gaussian 的振幅列, 或每块前 1–2 个局部特征向量, 两层, 无输运)。
- 回收类: **D2** Ritz 回收型 deflated CG (Saad–Yeung–Erhel–Guyomarc'h 2000; Parks 等 2006 GCRO-DR 的 SPD 版本): 上一状态**朴素 PCG 一次完整求解** (到 ρ=0.03) 末端 Lanczos 得到的 k 个最小广义 Ritz 向量, 在 H_t 下 RR (k 次乘积); 子变体 **D2b** 同一 θ 内回溯 (只改 η, H(η)=H₀+ΔηJᵀJ) 复用同一子空间 (近零成本)。
- 输运类: **D3p** U'=argmin_Z‖M_tZ−M_{t−1}U‖_F, **热启动 Z0=U_{t−1}**, 块 PCG 共享 Krylov, n_tr∈{0,3,8}; **n_tr=0 恒等于 D2** (嵌套, 单变量); 报告 LS 残差比 ‖M_tZ−Y‖_F/‖Y‖_F (RR 副产品); **D3x** 同映射 LS 精确解 (成本不计, 诊断); **D4λ** 输运 t−1 的 D1 (谱子空间, 成本不计); **D4e** 输运 t−1 的 D1e (能量子空间, 描述性, Opus 预测较弱)。
- 修补类: **D5** 在 D3p 基上追加 r 个由当前残差短 Krylov 扩展得到的向量 (成本计入; 总秩 k=k_t+r, r∈{2,4}); **D6** oracle 修补 (成本 0, 上界): 追加 r 个补空间中剩余误差 H-能量最大的广义本征方向; **D6n** 同 D6 但方向混入噪声至与真方向 cos=0.7。D6/D6n 只作上界, 不得当作可达基线。
- 隔离链 (按迭代数比较, 不比 W): D1e_t → D4 (映射损失) → D3x (提取损失) → D3p (LS 不精确; 只有此臂记成本)。
- **最强确定性对照** := 在 dev-sel 上按预注册网格取 W 中位数最小者于 {D0, D0w, D0b, D0c, D0s, D2} (不事后换)。闭环另含 **GEO/LMD 稠密直解** 作参考对照。

## 5. 同状态准则、记账、统计
- 准则 (oracle 停止): ‖e_k‖_H² ≤ max(ρ‖δ*_τ‖_H², 2e-6·F_t); **主 ρ=0.1** (内层预测二次增益的短缺 ≤10%), 次 ρ∈{0.03, 0.01} 仅作稳健性报告 (ρ=1e-4 延后)。依据 (dev 图 301 一次性探索, 披露见 §8): plain PCG-J 在 min(p,400) 次迭代内, ρ=0.1 需 49–63 次 (M 规模), ρ=0.03 在 3 个设置中有 2 个未达 (删失), ρ=0.01 全部未达; 故 0.03/0.01 删失率高, 不能作主读数。主 ρ 的选择是可行性选择 (先验固定后不再改), 不是按 G-B/G-C 结果调参。迭代上限 safety=min(p,400); 未达者**删失**, 按 safety 计入并取最差秩, 报告删失率。实用停止 ε_r (相对残差) 仅 G-A 用 ε_r=1e-2, 同时报告达到的 ρ。
- W 口径沿用 geo_flops + 新 src/trn_flops.py (先冻结 sha 再分账): 提取 (O(p n k) + O(n³) 小特征分解)、LS 输运迭代、RR (k 次 H 乘积 + k³)、QR(p×k)、每迭代投影 (4pk+2k²)、Lanczos 扩展、块 Jacobi 构建 (p 次 A 施加 + Gram)、解析块 (≈一次 render)。H 乘积 = J + A + Aᵀ + Jᵀ (与 geo_core._iter_pcg matvec 同口径)。CG 在回溯循环内, c_iter 含被拒 trial 的 CG。
- 分账: 每外层迭代 c_jac、c_rhs、c_setup (含 AJ/块/输运构建)、c_iter、c_acc; f_iter=c_iter/W, f_asm=(c_jac+c_setup 中的算子装配)/W, S_max=1/(1−f_iter)。CPU 单线程墙钟 (min-of-3) 次要, 以 W 为准、方向须一致; 小 N 解释器开销已知, 只对 L 规模认真解读墙钟。
- 聚合与统计: 每条轨迹先算 ΣW_arm/ΣW_ref, 再取图像级中位数; dev 判据用符号计数 (≥9/12 张图比值>1) + 中位数; confirm 用图像簇 BCa 自助法 95% CI。只有 §7 列出的读数入闸门, 其余描述性。

## 6. 闭环 (Q-C)
- **S0 = D0 (PCG-J)/D0w/D0b/D0c 在 dev-sel 上的闭环分账, 只用于 G-A** (先于 G-B/G-C/G-E)。G-A 取其中 W 中位数最小的基线。
- 完整闭环 (G-C/G-E) 仅在 §7 终态表允许后运行: 外层 = 冻结接受器; 内层 = 各 arm + 前向 forcing (ε_r 网格 {1e-1,1e-2,1e-3}); 各 arm 在 dev-sel 上同等小网格调参 (κ0∈{1e-3,1e-2}, f∈{3,10}, k∈{8,16}, n_tr∈{0,3,8}, ε_r) — 同等网格大小与调参预算。
- 画质/目标等价: 运行至 F−F_ref ≤ 1e-3·(F_0−F_ref) (F_ref=精确 GEO 参考轨迹末值), 且 PSNR **不比参考差 0.05 dB 以上** (单侧, 仅评测侧)。未达者按 W_cap 计入并取最差秩; **任一方法臂删失率 >10% 则 G-E 失败** (沿用 K1 R-censor)。
- 报告: 冷启动端到端 W 与墙钟、迭代摊销、峰值内存、失效率 (no_step、秩突变回退率、被拒回溯)。训练成本 (TRN-5) 单列。

## 7. 预注册闸门 (阈值先验固定) 与终态表
- **G-A (Amdahl, dev-sel, S0)**: M 与 L 上, 最低-W 基线的 f_iter 中位数 ≥ 0.5 **且**其每外层迭代 H 乘积数中位数 ≥ 24 (=3·k_min, k_min=8)。一致性: 要得到端到端 R=1.2, 需 f ≥ (1−1/R)/(1−1/s); s=1.5 → f≥0.50, s=1.3 → f≥0.72。
- **f_asm 触发**: G-A 失败且 f_asm ≥ 0.5 → **MC 路线** (§9); G-A 失败且 f_asm<0.5 → **STOP** ("成本分散, 无可用杠杆")。
- **G-B (理想余量; 主读数 = D4λ+D6, k_t+r=k)**: 相对最强确定性对照, 迭代数比与 W 比中位数均 ≥ 1.5, CI 下界 ≥ 1.3 (在 M 与 L 均成立; k、r、n_tr 只按预注册网格在 dev-sel 取 W 比中位数最大者, 用 dev-chk 复核选择偏差); 若 CI 下界在 [1.3,1.5) → 标为"无法达到 G-E", 转 MC。
- **G-C (确定性输运价值)**: D3p 管线相对最强确定性对照的 W 比中位数 ≥ 1.2 且 CI 下界 >1.0。
- **G-D (学习余量)**: 同时 (i) D6 相对 D3p 的 W 节省 (按 f_iter 折算成端到端百分比后) ≥ 20%; (ii) D5 节省 < D6 节省的 50%; (iii) D6n (cos=0.7) 仍节省 ≥ 10%。
- **G-E (闭环)**: §6; 确定性管线用 confirm-det; TRN-5 网络的合同附录另定 (相对最强确定性对照净收益 ≥20%, held-out 图像与核族上不劣于 D5)。
- **终态表**: A✗ 且 f_asm≥0.5 → MC; A✗ 且 f_asm<0.5 → STOP; A✓B✗ → MC; B✓C✓D✗ → D3p 闭环 → confirm-det; C✗D✓ → TRN-5 (附录先审先冻); B✓C✗D✗ → STOP ("有理想余量但不可达", 如实报告)。任一闸门失败如实写 FAILURES (NEGATIVE/INCONCLUSIVE, 不改写), 不调阈值、不重跑已完成阶段、不放宽配置。
- **确定性回退触发 (仅方法侧廉价量)**: 活动集变化、LS 残差比 >0.5、cond(E)>1e10; 回退前已花的输运成本计入; 回退状态计入分母。oracle 量 (H 谱) 不得作触发。

## 8. 工程与记录
- 单测 tests/test_trn_core.py: 稀疏 J 与 render_jac 在截断误差内一致; Hmv=稠密 MᵀM (已在开发期核对 1e-15); deflation 初值投影与 A-DEF2 在 U=精确广义本征空间时迭代数下降; **输运恒等**: θ_t=θ_{t−1} 且 η 固定、U⊥null(M) 时 U'=U; **n_tr=0 的 D3p 与 D2 逐位一致**; 谱量核对 VᵀDV=I、Σe=‖δ*‖_H²; D1 在 λ≈0 空间不被选中; trn_gen 种子不相交与 confirm 锁; D0c 与 D0b 块数值一致 (若实现)。
- vibe coding: 小任务 (trn_flops、D0c 闭式及其单测) 可派 Kimi 隔离补丁, GLM 只读核查; Sonnet 复核后合并; 默认 2 最多 5 不递归 (需宿主 pump 恢复; 当前 pump 停); 记录 run_id/模型/输入哈希。
- 记录: 每个模型调用/实验写 run 记录; 产物 outputs/TRN-*; 冻结记录 contracts/TRN_FREEZE_RECORD.txt (含全部新文件 sha256); 失败当场追加 FAILURES.md; G0 阅读日志续写。
- 开发期探索披露: 合同起草期间在 dev 图像 301 上做了一次性 S/M 规模同状态探索 (见 research/notes/TRN_PILOT_DEV_NOTE_20261108.md), 仅 dev 数据, 未触碰 confirm; 其观察 (ρ≤0.03 对 plain PCG 大面积删失、r_eff(95%) 大 (S: 74/216; M: 236–284/864)、块 Jacobi 严格构建成本约为 PCG-J 达 ρ=0.1 所需 W 的 7 倍 (M: 9.9e8 vs 1.6e8)、M 规模 oracle 子空间 deflation 迭代增益仅 ≈1.0–1.3×) 已用于改 §5 ρ 设置 (主 ρ=0.1); 这些读数同时是低输运余量的先兆, 但闸门判定仍只用冻结后的 dev-sel/confirm 数据, 阈值本身仍为先验 (来自 Astra/Opus)。
- 算力: CPU/8GB; GPU 不用; 预算上限在 dev pilot 后写入冻结版。

## 9. 测量压缩 (MC) 备选路线 (触发规则见 §7; 细节待 MC 附录, 同样先审先冻)
对象: 在保持精确 F_a 接受检查的前提下压缩 Jacobian/Hessian 的**测量侧**访问 (行/列采样、局部块、随机/学习 sketch、解析层次近似); 对照: 精确 AJ、随机子采样/Newton sketch、解析/层次局部近似 (D0c 即其一个实例)、learned Hessian sketch; 成本计入全部原算子访问; 同样的画质/目标等价判据与 confirm 边界。

## 10. 风险
R1 输运 LS 映射在近重合/秩跳变处的稳定性; R2 小 N 下解释器开销; R3 D6 oracle 过松 (已加 D5、D6n 共判); R4 f_iter 阈值与 A-施加记账假设 (严格 vs 缓存) — 两种口径都报告; R5 D0c 解析闭式的数值一致性 (未验证前不入对照集); R6 dev-sel 仅 12 图, 选择偏差靠 dev-chk 复核。
