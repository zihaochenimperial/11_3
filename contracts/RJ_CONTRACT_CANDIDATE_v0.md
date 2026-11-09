# RJ 合同候选 v0 — 被拒 trial 工作量杠杆 (先验 oracle 上界门优先)
状态: 候选, 未冻结。草拟 2026-11-08 (Sonnet 5.5); 待真实 Opus 审查 → 冻结记录 contracts/RJ_FREEZE_RECORD.txt。一切主张为 proposed; 0 已验证贡献; 不保证原创性或分数 (相关经典: Marquardt、Nielsen、Moré、Steihaug–Toint、Eisenstat–Walker 强制序列、inexact LM; 高斯泼溅二阶优化 2504.12905 等, 本会话仅标题级 G0 C95, 新颖性不主张)。
来源: TRN-4 终态 (FAIL-0032) 与 Opus 终态门 (research/notes/OPUS_REVIEW_TRN_TERMINAL_20261108.md, R7–R12)。授权: 以项目设定的当前主线 "自适应 2D 高斯生长中的搜索风险估计与校正" 为据, 2026-11-08T12:32Z 已 SendUserMessage 向真人说明, 真人回 "停" 即停。CPU/8GB, 不开 GPU/付费。

## 1. 对象与主张
对象不变: 固定 K 个 2D 高斯, 已知核单图去模糊, 冻结目标 F_a (geo_core), 冻结接受判据 `_accept` (RHO_MIN、guard、箱约束夹取) 与活动集; 数据/噪声/条件 C1,C4、规模 M (N=64, K=144) 同 TRN。
观察 (TRN-4, dev-sel): B* (D0w κ0=0.1,f=3,ε_r=0.1) 闭环中 67–77% 的 CG 迭代花在被拒 trial 上, 被拒 trial 平均 139/177 次 CG (C1/C4) 对被接受 66/40, 触及 maxcg=400 的比例 5–23% (被拒 trial 内)。
主张 (proposed): 在**同一 F_a、同一冻结接受判据、同一质量判据**下, 改变 κ 的取值与每个 trial 的 CG 预算 (臂的一部分) 能降低端到端 ΣW。本合同只检验**上界 (oracle) 余量**; 估计器/学习不在本合同内 (需 Gate O 通过后另立附录并再审)。

## 2. 数据边界
dev-sel 301–312 (调参 301–306×C1,C4; 评估 12 图×C1,C4)、dev-chk 313–320 (复核, 不选择), 噪声 seed 9401; 经 src/trn_gen 的闸门。confirm-det 321–344 与 401–424 **本合同版本不使用**, 如 Gate O 通过需另立附录 (含新的 ANALYZER 登记) 才可能使用; 方法侧代码不得 import clean_image_trn。F_ref 沿用 outputs/TRN-S0/fref_table.json (sha 登记在冻结记录; 不用任何 RJ 臂重算, Opus R11)。
## 3. 成本口径 (Opus R11)
主口径 W_sp: 冻结 flop 表, 但把 A/Aᵀ 的施加按**同一算子的精确稀疏 B** 计价: F_A,sp = 4·N·nnz(B) (nnz(B)=436/790 @ N=64, sb=1/2; 与冻结 B 逐元一致, 最大差 ≤3.3e-16, 见 outputs/TRN-MC/terminal_checks.json)。实现: W_sp = W_dense − nA_total·(F_A,dense − F_A,sp), 其中 nA_total 为 RJ 循环自己记录的 A 施加次数 (矩阵乘 2 次/H 乘积, 梯度 1 次, 每次接受检查 1 次)。次口径 W_dense (冻结口径) 同报。方向不一致时按 W_sp 判, 并如实报告。
## 4. 臂
所有臂: 同一内层 PCG (Jacobi 对角 JᵀJ 预条件)、同一 maxcg=400、同一外层上限 150 (删失按 §5)、同一 `_accept`; κ 取值范围 [KAPPA_MIN, KAPPA_MAX] 同冻结。新臂在新模块 src/rj_loop.py 注册 (GC.ITER['RJ'], geo_core 不编辑); **κ 更新规则是臂的一部分 (各臂自由度相同, 不再是 "冻结的 κ 规则", Opus R8)**。
### 4a 确定性对照 (Opus R7)
- **B0 = B***: D0w κ0=0.1,f=3,ε_r=0.1, κ 规则 `_finish` (拒绝×f, 接受且比值≥0.75 → /3) — 即 TRN 的 B*, 在本模块里按 150 外层重跑一次。
- **CG**: κ 下调因子 g∈{1.5, 2, hold(=1)} × f∈{3,10}, κ0=0.1 (6 配置; g=3 即 B0)。
- **CN**: Nielsen 更新 (接受: κ←κ·max(1/3, 1−(2ρ−1)³), ν←2; 拒绝: κ←κ·ν, ν←2ν), κ0∈{0.03,0.1,0.3} (3)。
- **CS**: Steihaug 式截断早接受: 每 m 次 CG 迭代对当前迭代点调用**真实** `_accept` (计费: 渲染+A+J 乘积, 接受检查的实际成本), 第一个被接受的迭代点即停; m∈{4,8,16}, κ0=0.1, 下调 g=3 (3)。
- **CD**: Δq 停滞停止: Δq_j=½ x_j·(g+res_j), 当 (Δq_j−Δq_{j−1}) ≤ τ·Δq_j 或相对残差 ≤0.1 时停; τ∈{1e-1,3e-2,1e-2} (3)。
- **CW**: Eisenstat–Walker 选择 2 的强制序列 η_t=γ(‖g_t‖/‖g_{t−1}‖)^α, α=(1+√5)/2, 夹到 [1e-3,0.5], γ∈{0.5,1.0} (2)。
- **CC**: 被拒 trial 的 CG 上限 = max(8, c×上一被接受 trial 的 CG 次数), c∈{2,4} (2)。
- **CR**: 拒绝后同 θ 的重试以前一 trial 的解为 x0 (x0 复用; Ritz/Krylov 回收型 D2b **未实现**, 声明: 主张相对集合不含 D2b-Ritz) (1)。
- **CX**: 预先指定的组合 g∈{1.5,2}×m∈{8,16}, 外加 CR 与 CC(c=4) (4)。
调参: 每个确定性对照族在调参集 (301–306×C1,C4, M) 上取其配置网格内**合并 ΣW_sp 到目标中位数最小者**为该族的唯一配置 (平局取较便宜者); 调参预算相同; 此后不改。**最强确定性对照 SC** := {B0, 各族最佳} 在 dev-sel 全部 12 图×{C1,C4} 上合并 ΣW_sp 中位数最小者 (不事后换)。
### 4b Oracle 臂 (免费探测; 只记被执行 trial 的成本, 轨迹真实演化)
- **OK (oracle-κ)**: 每个外层, 候选 κ ∈ κ_ref·3^j, j∈{−2,…,3}∩[KAPPA_MIN,KAPPA_MAX] (κ_ref=上一次被接受的 κ; 首外层为 κ0=0.1), 每个候选各跑一次 CG (停止规则同 B0, 首个 trial 暖启动 x0=上次接受步) 并用真实 `_accept` 判定 (探测的成本、`_accept` 的计数副作用在临时计数器中丢弃并恢复), 在被接受的候选中选 **ΔF/(W_固定+W_cg+W_acc)** 最大者 (W_固定=本外层 J 构建+梯度+预条件 setup), 只对该候选计费 (CG+一次接受检查); 若无候选被接受, 计费最大 κ 候选 (被拒) 后转入 B0 的拒绝序列 (×f, 真实计费)。
- **OKS (oracle-κ + oracle-stop)**: 在 OK 的每个候选内, 每 4 次 CG 迭代**免费**检查迭代点是否被接受, 取第一个被接受的迭代点为该候选的解 (CG 计费到该迭代); 其余同 OK。**Gate O 的门臂 = OKS** (最慷慨的上界); OK 作描述性。
Oracle 是贪心的逐外层上界, 不是全局最优, 也不代表可实现。
## 5. 目标、删失、读数
目标 F ≤ F_ref + 1e-3·(F_0 − F_ref) (F_ref 来自 fref_table); W 取到目标首次命中的累计 W_sp; 外层上限 150, 未命中为删失, 删失 W 取该运行 150 外层的累计 W (真 W 的下界)。每臂报告删失率 (含 B0: TRN 的 100 外层下 B* 删失 0.208, 本合同 150 外层下重算), 删失 >10% 的臂/对照在结论中标 "下界读数", **若 SC 删失>10% 则 Gate O 判 INCONCLUSIVE 而不是 PASS**。比值 R=W_SC/W_arm 逐 (图,条件), 图内取条件的几何平均, 图像级中位数 + 图像簇 BCa 95% (B=4000, seed 20261108, 复用 experiments/trn_same_state_reduce.bca)。PSNR 判据本阶段**仅描述性**报告 (C4 噪声主导, TRN-4 披露), 不入 Gate O。另报: 被拒 trial 占 CG 迭代比例、触顶 maxcg 比例、每外层试探数、κ 分布。
## 6. 闸门
- **Gate O (oracle 余量)**: OKS 相对 SC 的 R: 图像级中位数 ≥1.5 且 BCa 下界 ≥1.3, dev-sel 12 图; 符号 ≥9/12; dev-chk 313–320 上同配置复核中位数 ≥1.3。通过 → 进入 Gate T; 不通过 (含 B-marginal) → **STOP, 记 FAILURES, 不写估计器**。
- **Gate T (调参假象)**: 对 B0 的 ΣW_sp 比, 计 L_SC=ln R(SC vs B0) 与 L_OKS=ln R(OKS vs B0); 若 L_SC ≥ ⅔·L_OKS → 结论 "确定性调参即可", 不做估计器; 否则才可另立 "风险估计器" 附录 (需新合同、新 Opus 审)。
- **终态表**: O✗ → STOP; O✓T✗(确定性已吃掉) → STOP (记为 "确定性调参即可", 把 SC 作为对 GEO 基线的改进如实报告); O✓T✓ → 估计器附录草案 (不在本合同内, 先审先冻)。
## 7. CPU·h 上限 (超限该阶段判 INCONCLUSIVE, 不得追加)
实现+单测 ≤0.5; 调参 (约 24 配置×12 问题) ≤6; SC 选择 12 图 (各族最佳) ≤2; OK/OKS 12 图 ×2 条件 ≤8; dev-chk 复核 ≤2; 合计 ≤20。
## 8. 单测与记录
tests/test_rj_loop.py: B0 臂与 TRN 'TRN' 臂在同 cfg 下逐位一致 (150 外层前 20 外层的 θ 轨迹); κ 规则 g=3 等价冻结 `_finish`; CS 的检查被计费而 OKS 的检查不计费; 探测不改变 S 计数 (S['trials'] 等恢复); W_sp 重算与手工一致; 门控不绕过 (无 confirm 访问)。每个运行用唯一 run_id; 失败当场追加 FAILURES。
## 9. 已知风险
R1 调参假象 (Gate T); R2 oracle 贪心不等于上界且可能偏低 (标注); R3 B0 自身删失; R4 maxcg 触顶使 CC 臂受益 (各臂 maxcg 同, 报告触顶率); R5 κ 序列的路径依赖使 W 比方差大 (图像簇 BCa); R6 W_sp 与实际墙钟可能不一致 (小 N 解释器开销, 墙钟次要); R7 近邻文献只读到标题级。
