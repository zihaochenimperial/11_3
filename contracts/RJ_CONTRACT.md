# RJ 合同 v1 (冻结版) — 被拒 trial 工作量杠杆: 先验 oracle 余量门
状态: 冻结 (冻结记录 contracts/RJ_FREEZE_RECORD.txt; 冻结后不改规则, 修订只能走新版本并记录)。作者 Sonnet 5.5; 科学门 Opus 5.5 审查 v0.1 = PASS-WITH-CHANGES R13–R24 (runlog 20261108T125053Z-model-call-ef21, 原文 research/notes/OPUS_REVIEW_RJ_CONTRACT_v0_1_20261108.md), 本版已按其逐条修改, Opus 表示改完无需再审。
一切主张为 proposed; 0 已验证贡献; 不保证原创性或分数 (相关经典: Marquardt、Nielsen、Moré、Steihaug–Toint、Eisenstat–Walker 强制序列、Cartis–Gould–Toint ARC; 本会话仅标题级文献核查 G0 C95; 新颖性不主张)。Gate O 通过只是 "允许继续" 的许可, 不是证据 (dev-sel 已被反复使用)。
授权依据 (R22): 真人 2026-11-08 09:02Z 的授权 (Codex 转交原话: 同样的 agent 分配模式 autoresearch 与 vibe research+vibe coding 开始完成; 先冻结合同、CPU 分账与 oracle, 再按结果推进) 以及项目说明中的主线 "自适应 2D 高斯生长中的搜索风险估计与校正"; 2026-11-08T12:32Z 已 SendUserMessage 向真人说明 RJ-1 (WAKES 12:31:26Z 记录), 真人回 "停" 即停。CPU/8GB, 不开 GPU, 不启用付费, 宿主 pump 保持停止, 全部产物在 D:\Gaussian\outputs\RJ。

## 1. 对象与主张
对象不变: 固定 K 个 2D 高斯, 已知核单图去模糊, 冻结目标 F_a (geo_core), 冻结接受判据 GC._accept (RHO_MIN、GUARD、箱约束夹取)、活动集与 Jacobi-PCG 内层 (trn_loop 同款); 数据/噪声/条件 C1,C4、规模 M (N=64, K=144) 同 TRN。
观察 (TRN-4, dev-sel): B* (D0w κ0=0.1, f=3, ε_r=0.1) 闭环中 67–77% 的 CG 迭代花在被拒 trial 上。
主张 (proposed): 在同一 F_a、同一冻结接受判据、同一质量判据下, κ 的取值与每个 trial 的 CG 预算/停止规则 (臂的一部分, Opus R8: 这已不是 "冻结的 κ 规则") 能降低端到端 W。本合同只检验 oracle 余量与确定性调参是否已吃掉它; 学习/估计器不在本合同内。

## 2. 数据边界
dev-sel 301–312 (调参 301–306×{C1,C4}; 评估 301–312×{C1,C4}); dev-chk 313–320 (复核, 不选择); 噪声 seed 9401; 经 src/trn_gen 闸门。confirm-det 321–344 与 401–424 本合同不使用 (未生成、未读取)。方法侧代码不得 import clean_image_trn (单测核查)。F_ref: dev-sel 沿用 outputs/TRN-S0/fref_table.json; dev-chk 用 experiments/rj_fref_chk.py 以冻结 TRN 臂 (B* 与 D0 ε_r=1e-3, 各 100 外层) 同一配方算出, 任何 RJ 臂都不参与 F_ref (Opus R11)。

## 3. 成本口径
主口径 W_sp: 冻结 flop 表, 但 A/Aᵀ 的施加按同一算子的精确稀疏 B 计价: F_A,sp = 4·N·nnz(B) (nnz=436/790 @ N=64, sb=1/2; 与冻结 B 逐元一致 ≤3.3e-16, outputs/TRN-MC/terminal_checks.json); W_sp = W_dense − nA·(F_A,dense − F_A,sp), nA = cnt['A'] (单测 R23 以包装算子的真实调用数逐外层核对 B0、S 族、OKdF 三种运行)。W_dense (冻结口径) 次要同报。oracle 臂不报墙钟 (R15: 免费探测的时间不回滚), 其余臂的墙钟仅描述。

## 4. 臂 (全部在新模块 src/rj_loop.py, 不改 geo_core / trn_loop)
所有臂: 同一内层 PCG (Jacobi 对角 JᵀJ), 同一 maxcg=400, 同一外层上限 200, 同一 GC._accept, κ∈[KAPPA_MIN,KAPPA_MAX], 首个 trial 暖启动 (D0w), ε_r=0.1 (除另注)。
### 4a 确定性对照 (8 族, 每族≤6 配置, 预算相同; 声明: 强对照集不含 Krylov/Ritz 回收 D2b 与 Moré/ARC 型步长范数信赖域族 — 一律称 "8 族确定性对照中最强者", 不称 "最强确定性对照"; 若进入估计器附录, D2b 必须先实现并入集, 否则不得冻结该附录, R16)
- B: κ0∈{0.03,0.1,0.3}×f∈{3,10} (6); B0=(0.1,3)=B*。
- G: κ 下调因子 gdiv∈{1.5,2,1(hold)}×f∈{3,10} (6); gdiv=3 即冻结规则。
- N: Nielsen (接受 κ←κ·max(1/3,1−(2ρ−1)³), 拒绝 κ←κ·ν, ν←2ν), κ0∈{0.03,0.1,0.3} (3)。
- S: Steihaug 式早接受: 每 m 次 CG 迭代对当前迭代点调用真实 GC._accept (J 乘积+渲染+2A, 计费并计入 S[trials]), 首个被接受即停; m∈{4,8,16}×gdiv∈{3,2} (6)。
- D: Δq 停滞 (0.5 x·(g+res) 相对增量≤τ 时停) ∪ ε_r 停止: τ∈{0.1,0.03,0.01}×ε_r∈{0.1,0.03} (6)。
- W: Eisenstat–Walker 选择 2: η_t=γ(‖g_t‖/‖g_{t−1}‖)^φ, φ=(1+√5)/2, 夹 [1e-3,0.5] (首外层 0.1); γ∈{0.3,0.5,1.0}×κ0∈{0.1,0.3} (6)。
- C: 每个 trial 的 CG 上限=max(8, c×上一被接受 trial 的 CG 次数) (首外层 400); c∈{2,4,8}×重试 trial 以上一 trial 解为 x0 (否/是) (6)。
- X: 预指定组合 (gdiv=2,m=8), (gdiv=1.5,m=16), (gdiv=2,c=4,复用), (gdiv=2,m=8,c=4,复用) (4)。共 43 配置。
调参 (R18): 调参集 301–306×{C1,C4}, 各族取网格内 ΣW_sp 到目标的中位数最小者 (删失或 no_step 提前终止=∞; 平局取删失少者, 再取有限 W 均值低者), 此后冻结。CPU 上限 ≤4.5 CPU·h, 按族序 B→G→N→S→D→W→C→X 执行; 超限的族整体 "不可用", 不得删单个配置。
SC := {各族最佳} ∪ {B0} 在 dev-sel 301–312×{C1,C4} 上 W_sp 到目标的中位数最小者 (删失=∞; 平局: 删失少者, 再取下界中位数低者)。这是在评估集上选对照 (对对照有利, 对门更严), 披露。
### 4b Oracle 臂 (R13/R14: 全部叠在 SC 的试验流程上, 即除 κ 的取值/截断点由 oracle 决定外, ε_r、停止规则、CG 预算、复用方式、κ 更新规则均与 SC 配置完全相同)
κ_ref := 外层开始时的 S[kappa]; 候选 κ∈κ_ref·3^j, j∈{−2,…,3}, 夹到 [KAPPA_MIN,KAPPA_MAX]。每个候选以 SC 的试验流程 (含其 CG 预算; SC 的 S 族检查在探测中同样执行但被回滚) 免费探测, 用真实 GC._accept 判定; 探测的计数副作用 (S 计数、T[back]、cnt W/A) 被回滚 (单测)。只对被选中的候选计费: 其 CG 成本 + 该试验流程实际会做的接受检查次数 (nacc) × 单次接受检查成本; 外层固定成本 (J 构建/梯度/set-up) 照常计。选中者按 SC 的 κ 规则更新 κ。若无候选被接受: 从最大候选 κ 重跑并按 SC 的拒绝规则继续, 全程计费 (跳过了 B0 本应付费的较小 κ 拒绝序列, 对 oracle 有利; 报告该分支频率, Opus Q4-3)。
- OKdF@SC: 在被接受的候选中选 ΔF 最大者。
- OKβ@SC (β=0.5): 在被接受的候选中, 取 ΔF≥β·ΔF_max 的子集, 再选该子集中计费成本最小者。
- OKSβ@SC (β=0.5, 每 4 次 CG 迭代免费检查): 每个候选在满足 ΔF≥β·ΔF_full(κ) 的第一个被接受检查点停止 (ΔF_full 为同一 κ 按 SC 其余停止规则完整求解后的 ΔF; 此臂忽略 SC 自身的 early_m), 然后按 OKβ 的规则在候选间选择, 只计费一次接受检查。
- **Gate O 门臂 := 上述三者中对 SC 的图像级中位比值最大者 (预注册的 max, 三者同时披露)。**
- 描述性: OS@SC 与 OS@B0 (免拒绝: 同一 κ 序列/轨迹, 被拒 trial 的 CG 与接受检查不计费 = 经典 Amdahl 上限, Opus 指出它忽略 κ 搜索的作用), OKdF@B0 (B0 底座, R13 降为描述)。
Oracle 是逐外层贪心探针, 不保证是上界; Gate O 不通过时结论只能写 "在这些 oracle 探针下余量不足" (R2)。
设计阶段披露 (全部只在 dev-sel 301, 非预注册读数, 发生在合同冻结前): (a) 301 上相对 B0 的 W_sp: OS 2.8×(C1)/3.3×(C4), OKdF@B0 2.0×/2.0×; 效率贪心 (ΔF/成本) 及其 oracle-stop 版倾向微小步、外层数暴涨 (OKS-eff 在 C4 上 400 外层未达目标), 因而弃用; (b) 冻结前冒烟: 301 C4 上 OKβ@B0 的 W_sp 2.27e10 (比 B0 1.71e10 更差), OKSβ@B0 200 外层未达目标, OKdF@S(m8) 200 外层未达目标, C_c4_r0 为 1.13e10 (约 1.5×B0), G(gdiv=2,f=3) 1.41e10, C_c2_r1/X4 在第 4–5 外层 no_step 死亡 — 这提示确定性调参 (CG 预算族) 很可能已吃掉相当一部分余量, 这正是 Gate T 要判的。

## 5. 目标、删失、读数
目标 F ≤ F_ref + 1e-3(F_0 − F_ref); W_sp 取首次命中时累计值; 外层上限 200, 未命中=删失 (W 取运行结束累计值, 为真 W 的下界)。调参与 SC 选择用 "删失=∞"; 比值读数用下界且按 R19 规则 (两处口径不同, 原因: 选择需要保守地惩罚删失, 比值需要不抬高被测臂): 逐 (图,条件) R=W_SC/W_arm 用下界; 若门臂删失而 SC 未删失 R:=min(R,1); SC 删失而门臂未删失 R 保留并标 "下界"; 双方都删失 R:=1; 任一方删失率>10% → Gate O 判 INCONCLUSIVE。图内取两条件的几何平均, 图像级中位数 + 图像簇 BCa95 (B=4000, seed 20261108, trn_same_state_reduce.bca)。
质量 (R21): 报告各臂首次达标时刻的 PSNR (评估侧, 描述); 若门臂在超过 25% 的 (图,条件) 上比 SC 低 0.05 dB 以上, Gate O 的任何通过须附 "质量警示" 且不得进入估计器附录。
另报 (Opus Q4): 被拒 trial 的 CG 迭代占比、触顶 maxcg 比例、每外层试探数、S 族中途检查次数 (nacc−1)/外层、oracle 的 "无候选被接受" 频率、所选 j 的分布、探测中 reason=cap 的比例。

## 6. 闸门与终态
- Gate O (stage gate, dev-sel 12 图): 门臂 vs SC 的 R: 图像级中位数 ≥1.5 且 BCa 下界 ≥1.3 且符号 ≥9/12 且双方删失≤10%; 否则 FAIL (含 marginal) 或 INCONCLUSIVE(删失)。通过后在 dev-chk 313–320 以同一 (SC, 门臂) 复核: 中位数 ≥1.3 (复核不选择)。FAIL/INCONCLUSIVE → STOP, 记 FAILURES, 不写估计器。
- Gate T (R17): L_SC=ln R(SC vs B0), L_OK=ln R(门臂 vs B0) (同一 SC 底座; 另报 OKdF@B0 vs B0); L_SC ≥ ⅔ L_OK → "确定性调参即可", 不做估计器。
- 终态表: O✗ → STOP。O✓T✗ → STOP, 结论只写 "在 dev-sel、W_sp 口径下, SC 相对 B0 的确定性改进为 R (BCa), 未经 confirm" (R20), 不得称为已验证。O✓T✓ (且无质量警示, dev-chk 复核通过) → 仅可起草估计器附录: 须另冻结、先实现 D2b 并入对照集、并经 Opus 同意后才可动用 confirm 一次 (新的 ANALYZER 登记与 CONFIRM_UNSEALED 流程); 本合同不使用 confirm。

## 7. CPU·h 上限 (超限该阶段判 INCONCLUSIVE, 不得追加)
调参 ≤4.5; eval_det (家族最佳+B0, 24 问题) ≤1.5; eval_orc (6 个 oracle/OS 配置×24 问题) ≤4.5; chk (fref_chk + 确定性+oracle, 16 问题) ≤3; 合计 ≤13.5 (设计阶段探测 ≤0.1 不计)。容器 2 核, 分片并行。

## 8. 单测 (tests/test_rj_loop.py, 冻结前须全部通过)
B0 与冻结 TRN D0w 臂在 S 规模两条件下整条轨迹逐位一致 (F, A, mv, W, rss, stop, rej; R24); hold 下 κ 不降; Nielsen 公式; 探测回滚 (S[trials] 等) 与 W 记账一致 (dF/beta/sbeta 三个 oracle); S 族检查被计费; cnt[A] 与包装算子的真实 A 施加次数逐外层一致 (B0、S 族、OKdF; R23); 带状 B 与冻结 A 同一算子; 方法侧代码不含 clean_image / CONFIRM 引用。每个运行用唯一 run_id; 失败当场追加 FAILURES。

## 9. 已知风险
R1 调参假象 (Gate T) — 设计阶段已见迹象; R2 oracle 为逐外层贪心探针不是上界; R3 B0 自身删失 (200 外层下重算; 删失>10% 的臂标 "下界读数"); R4 maxcg 触顶使 C 族受益 (各臂 maxcg 同, 报告触顶率); R5 κ 序列的路径依赖使 W 比方差大 (图像簇 BCa); R6 dev-sel 反复使用, 通过只是许可; R7 SC 在评估集上选 (对门更严); R8 近邻文献只读到标题级; R9 无 D2b/Moré/ARC 族 (限制已声明)。
