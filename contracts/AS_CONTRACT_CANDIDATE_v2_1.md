# AS 合同候选 v2.1 (CANDIDATE, 待冻结; 应用 Opus 复审 12 项编辑, 见 contracts/AS_CONTRACT_v2_to_v2_1_DIFF.md) -- 退化观测下 Gaussian 容量编辑: "联合补偿选择"的预注册 kill test
状态: proposed; 0 已验证贡献。起草 run 20261105T230727Z-session-74ee (Sonnet 5.5)。修订链: v1 (sha256 f9708aa3..., 作废为草案; FAIL-0020) -> v2 (sha256 b92e7dad...) -> v2.1 (本文件; Opus 复审 run 20261106T000215Z-opus-review-b52f 裁决 FREEZE-WITH-EDITS, 原文 research/notes/OPUS_REVIEW_AS_CONTRACT2_20261106.md sha256 e6b9586c...)。Opus 称若 12 项编辑逐字应用并记录 diff 则无需再审; 冻结 (sha256 + 冻结记录) 后才可写实验代码/运行。
依据: 真人 2026-11-05 23:04 London 授权; Astra high 交接 (research/sources/astra_handoff_20261105/); G0: research/notes/G0_reading_log_20261105.md C41-C55, research/notes/AS_G0_SYNTHESIS_20261105.md; Opus 门原文 research/notes/OPUS_REVIEW_AS_CONTRACT1_20261105.md (sha256 68d68c15...); 冻结前小尺度自检 research/notes/AS_KA_RESULT_20261105.md。
先验披露 (见 §8): 单步 y 空间自检 K-a 没有区分力 (不是"无余量"证据, 也不是"有余量"证据); Opus 估计 GO 先验约 5-10%。本合同是预注册的**廉价 kill test**, 空结果概率高, 空结果按判定表 STOP。

## 0. 本合同只回答一个问题 (Q1)
已知模糊核单图去模糊, Gaussian 和表示, 容量逐步增加 (birth/split) 到 K_max, 在**完全相同的候选集、相同的编辑执行与相同的回拟**下, 补偿型选择规则 (JOINT) 是否比便宜规则 (OMP-raw, BLOCK) 给出实质更低的最终重建 MSE? 并回答两个先决问题: (Gate 0) 选择本身是否有余量 (作弊型 ORACLE_x 相对便宜规则是否有 >=10% 优势); (Gate F) 增长控制相对固定容量是否有独立意义。
不在本合同内: 强基线 (同表示 Adam/LM+正则/早停、完整谱正则化 IRGNM、SteepGS 适配、经典像素域反卷积全面比较、调参充分 INR); 局部近似算法; 自然图; GPU; 任何贡献/原创声称。属 AS-4/5/6, 各需新合同 + 新 Opus 门。结果只适用于本合成基准与本候选族, 不是整个方向的上界。

## 1. 数据 (开发集)
- 32x32 灰度, 峰值归一化为 1。程序化生成 (非 Gaussian 渲染, 避免同分布偏置) 三族各 8 张共 24 张: G_edge (3-6 个随机多边形/半平面, 抗锯齿, 分段常数+缓变), G_tex (带限随机纹理: 随机方向正弦光栅叠加 × 平滑包络), G_mix (边缘+局部纹理)。生成器 seed 7101..7124 (新; 不用 F0/CF0 旧图; E41-58 不动); 生成器 hash 入冻结记录。
- 干净图只在评测器路径出现。规则/回拟/候选函数的输入仅 (y, A, sigma_n, theta, 候选参数), 以函数签名与单测机械检查。**ORACLE_x 例外**: 它是单独的评测器侧进程, 可读干净图, 只写诊断输出, 不得被任何方法路径调用; 合同在此显式豁免。
- 本合同内无独立确认集 (AS-6 另建, 新 seed 封存)。K-a 自检用的是随机真值 Gaussian 场景, 与本数据不重叠。

## 2. 退化算子与噪声
- A = B⊗B, B 为 32x32 反射边界一维高斯模糊 (核半径 ceil(3σ_b), 和为 1)。**实现: 可分离应用 A x = B X B^T (X 为 32x32 图), 并保留稠密 1024x1024 构造仅用于单测。** 反射边界下 B 不对称, 伴随 A^T 用 B^T 实现并单测。
- 4 条件 C1..C4: σ_b∈{1.0, 2.0} × σ_n∈{0.01, 0.03}; 噪声在模糊后加, σ_n 已知; 每格 2 个噪声 seed (9001, 9002), 在每张图内先平均。
- **剂量-响应对照 (取代 v1 的负对照 N)**: σ_b∈{0.3, 1.0, 2.0} × σ_n=0.03, 24 图 × 1 噪声 seed (9001); 预注册报告 H_J(0.3) <= H_J(1.0) <= H_J(2.0) 是否成立 (报告, 不作 gate; 不成立须记录)。Gaussian 间自身重叠使 A=I 也有 P⊥ 效应, 故不再声称"近恒等应零优势"。

## 3. 表示、优化与容量编辑
- 表示: x(θ)=Σ_k a_k exp(−½ (u−m_k)^T Σ_k^{-1} (u−m_k)), Σ=L L^T; θ_k=(a, m_x, m_y, log ℓ11, ℓ21, log ℓ22) (峰值振幅参数化, a 有符号), u=(i+0.5, j+0.5), 稠密渲染, K<=36, log ℓ 钳在 [log 0.6, log 12] px。
- 训练损失 L=½‖(y−Ax)/σ_n‖² + 1e-6 Σ a²。
- 初始: K0=6 个 Gaussian 3x2 网格, 各向同性 σ=6 px, a 由线性 LS, 然后 LM T0=30 步。**中性初始化次级臂 INIT-N**: K0=6 网格 σ=3 (只在 C1..C4 × seed 9001 上对三规则做)。
- 回拟 (所有规则/臂相同): 解析 Jacobian + LM, λ0=1e-3 成功×0.3 失败×10 上限 1e6; **每次编辑后 T_r=15 步; 每次回拟拒绝步数上限 20 (超出则记录并停止该次回拟)**; λ 每次编辑后重置为 λ0。单测: 解析 Jacobian 对中心差分相对误差<1e-5; 接受步 L 不增。
- 容量步 S=30, K_max=36。每步候选集 C_t (**所有规则共享同一 C_t**):
  (a) birth: g=A^T r 的 3x3 非极大抑制极大点前 B=12 个 (最小间距 2 px) × 形状 σ∈{1.5, 3.0} = 24 个; 候选形状 ĝ (单位峰值), 振幅系数 c 在 [−1.5, 1.5] 内有界;
  (b) split: 对每个 Gaussian 沿 Σ 主轴与次轴各一个方向 e, α∈{0.4, 0.7}: d=α s_e, 子代协方差 Σ'=Σ−d² e e^T, **子代峰值振幅 (a/2)·sqrt(detΣ/detΣ') (保质量)**, 位置 m±d e; 每个父 4 个候选 (K<=35 时最多 140 个)。**对处于 log ℓ 钳边的父, 其候选被排除并计数记录。**
  图像增量 q_c = 编辑后精确图像 − 当前图像 (非 Taylor); 记 v_c = A q_c; birth 的 v_c = A ĝ (单位振幅)。
- **所有规则 (含 ORACLE) 一律使用同一编辑执行函数**: 被选 split 以 c=1 执行 (精确保质量分裂) 后 T_r 回拟; 被选 birth **同时从两个振幅初值** c0=clip(r·v/‖v‖², ±1.5) 与 c*_OLS=clip(r·P⊥v/‖P⊥v‖², ±1.5) (若 ‖P⊥v‖/‖v‖<1e-3 则只用 c0) 各回拟 T_r 步, 保留最终训练损失较低者 (规则中性; 对每个规则相同; 每步多一次回拟)。规则只决定"选哪个候选"。 [Opus 编辑 a]
- 得分 (r=y−Ax(θ) 当前残差, 不假设驻点; P=A J 值域的正交投影, SVD rcond=1e-10; P_b=父 Gaussian 自身 6 列的投影; P⊥=I−P; 单位=线性化回拟后 ½‖·‖² 的下降):
  RAND (固定 seed 控制);
  OMP-raw: split Δ=r·v−½‖v‖²; birth c*=clip(r·v/‖v‖², ±1.5), Δ=c* r·v−½ c*²‖v‖²;
  BLOCK: split Δ=r·P⊥_b v−½‖P⊥_b v‖²; birth 同 OMP-raw (无父);
  JOINT: split Δ=r·P⊥v−½‖P⊥v‖²; birth c*=clip(r·P⊥v/‖P⊥v‖², ±1.5), Δ=c* r·P⊥v−½ c*²‖P⊥v‖²。**‖P⊥v‖/‖v‖ < 1e-3 的候选排除出 JOINT 排序并计数记录;**
  JOINT_FREE (次级描述性臂, 不入 gate): split 与 birth 都用单侧自由系数 max(r·P⊥v, 0)²/(2‖P⊥v‖²) (c<0 的候选得分为 0), 同样的 1e-3 下限; 'JOINT 未过而 JOINT_FREE 会过' 只作假设生成, 不改任何判定; [Opus 编辑 b]
  FIXED-K: 不增长, K_max=36 个 Gaussian, 3 个预设初始化 (6x6 网格 σ=3; 6x6 网格 σ=2; 抖动网格 σ=2.5, 抖动 seed 1), 各给与增长臂相同的总 LM 步数 (T0+S·T_r), 取 **预设 3 个中最终训练损失最小者** (不看干净 MSE);
  ORACLE_y-full: 候选集 C_t 全部各自编辑后 (出生取 {c0, c*_OLS} 两初值较好者) 回拟 T_o=T_r=15 步, 选**训练损失**最低者, 沿其自身路径继续 (在其自身状态下重新生成 C_t); 只跑 §6 子集。这是真人授权的 '完整联合参考' 在本合同内的唯一完整实现, **只在该子集上被检验**。 [Opus 编辑 c/d]
  ORACLE_ys (合法短名单 oracle, 仅 seed 9001 的 96 单元): 在 oracle 自身路径状态下取 {OMP-raw, BLOCK, JOINT, JOINT_FREE} 各自 top-8 的并集 (<=32 个), 每个回拟 T_o=T_r=15 步 (出生取较好初值), 选训练损失最低者; 报告 H_Oys。 [Opus 编辑 c]
  ORACLE_x (评测器侧, 诊断/作弊上界; 豁免 V6, 见 §1): ORACLE_xs = 在 **oracle 自身路径状态**下取上述同一并集短名单 (4 个规则各 top-8, <=32 个), 每个回拟 T_o=8 步, 选对干净图 MSE 最低者; **选定后用标准编辑执行函数对该编辑重做 T_r=15 步回拟再继续** (与各规则路径同参); 全 192 单元。ORACLE_x-full = 全候选, T_o=8, 同样选定后重做 T_r=15 步; **条件执行**: 仅当 ORACLE_xs 的 Gate 0 未达 10% 时才运行, 在 §6 的 12 单元上与 ORACLE_xs 于**同一 12 单元**比较。 [Opus 编辑 d]
- 变体: 每个 R∈{OMP-raw, BLOCK, JOINT} 另跑 birth-only 与 split-only (候选集限制) 变体 (次级, 用于解读 births-vs-splits)。
- 无 K 自适应停止; 记录每步: K, 训练损失, 对干净 MSE (评测器侧事后算, 不回流), 候选类型 (birth/split), 被选候选的 top-1 一致与各规则得分的 Spearman, 驻点比 ‖(AJ)^T r‖/(σmax(AJ)‖r‖), 线性化预测增益 vs 实现增益 (每步对被选候选与 top-5, 诊断量, 不是 gate), 排除计数, 打分耗时与回拟耗时。
- 次级读出 (零额外计算或秒级): 偏差原理停止 K (首个 ‖y−Ax‖²<=τ N σ_n², τ=1.0) 处的 MSE; Tikhonov/Wiener 反卷积 (GCV 选 λ, 同 A, 同噪声) 的 MSE 作情境数 (K-c)。

## 4. 终点与判定 (全部冻结后才跑; 不得事后改)
- 条件: C1=(σ_b=1.0, σ_n=0.01), C2=(1.0, 0.03), C3=(2.0, 0.01), C4=(2.0, 0.03)。评测: MSE(x(θ), x_clean) 在 K_max=36; 单元 u=(图 i, 条件 c, 噪声 seed s); 图为簇: D_i^R = 该图 4 条件×2 seed 的 log(M_JOINT/M_R) 平均。图族: 图序 1-8=G_edge, 9-16=G_tex, 17-24=G_mix。
- cheap = OMP-raw 与 BLOCK 中全体 192 单元几何均值 MSE 较小者 (一次性固定, 不在任何重采样内重选)。**H_X := 1 − exp(mean_u log(M_X/M_cheap))** (正=X 的几何均值 MSE 更低); H_J 即 X=JOINT, H_Oxs, H_Oys 同理。[Opus 编辑 i]
- **Gate 0 (选择是否有余量; 必要条件, 非充分)**: H_Oxs >= 10% 才通过 (全 192 单元)。否则运行 ORACLE_x-full (12 单元) 与 ORACLE_xs 在同 12 单元比较: 若 ORACLE_x-full >= 10% 而 ORACLE_xs 不足 -> INCONCLUSIVE (短名单限制), 需新合同再扩展, 不自行放行; 若两者都 <10% -> STOP (瓶颈不在选择)。ORACLE_x 的优势可能来自避免拟合噪声 (任何基于 y 的规则不可得), 故另报 H_Oys (seed 9001 的 96 单元): **若 H_Oys <= 0 而 Gate 1 通过, 标记 INCONCLUSIVE-unexplained**, 不放行。[Opus 编辑 c/d]
- **Gate 1 (主检验)**: 对 R∈{OMP-raw, BLOCK} 分别 (交并检验, 两者都须通过, 无需多重校正): (i) mean_i D_i^R <= log 0.95; (ii) **单侧精确符号翻转检验**: 对 24 个 D_i^R 枚举全部 2^24 个符号向量 s ∈ {±1}^24 (确定性, 无随机数), p = #{s : mean_i(s_i D_i^R) <= mean_i(D_i^R)} / 2^24, 要求 p < 0.05; (iii) 4 个条件各自的条件级均值 (对图平均) 都 <= log 1.02 (无伤害); (iv) 三个图族中至少 2 族的族级均值 <= 0。另报 JOINT vs ORACLE_y-full (子集) 与 JOINT vs JOINT_FREE。符号一致率只报告。[Opus 编辑 e]
- **Gate F (独立)**: 若 FIXED-K (3 个预设初始化取训练损失最小者) 的几何均值 MSE <= 1.02 × JOINT 的, 则 STOP 增长线, 不论 Gate 1。
- **类型混合规则 (K-e)**: 若 JOINT 在混合池胜过某便宜规则 (按 Gate 1 的 (i)(ii)), 但对应的 birth-only 变体与 split-only 变体内都未胜出 ('胜出' = 变体内 mean D < 0 且同一精确检验单侧 p < 0.10), 则报告为 '类型混合效应', 不记为补偿优势, 记 INCONCLUSIVE-type-mix, 不放行。[Opus 编辑 g]
- **判定表**: (1) Gate 0 失败 (ORACLE_xs 与 ORACLE_x-full 都 <10%) -> STOP; (2) Gate 0 INCONCLUSIVE (短名单限制) -> 不放行, 需新合同; (3) Gate 0 过 且 Gate 1 失败 -> STOP Q1 (JOINT 补偿无优势); (4) Gate F 失败 -> STOP 增长线; (5) Gate 0, Gate 1, Gate F 皆过 且 H_Oys > 0 且 V10 稳定率 >= 90% 且非类型混合 -> GO (仍需 AS-4 新合同 + Opus: 强基线、等时比较); (6) 三者皆过但 H_Oys <= 0 -> INCONCLUSIVE-unexplained; V10 稳定率 < 90% -> INCONCLUSIVE-numerics; 类型混合 -> INCONCLUSIVE-type-mix; 均不放行。5%/2%/10% 是我与 Opus 共同设的示例门槛, 非任何原创性判据。[Opus 编辑 g]
- **过拟合诊断 (预注册, 非 gate)**: 每规则报告 K_max 处训练损失与干净 MSE; 另在偏差原理 K (τ=1.0) 处重算 Gate 1 的统计量。若 JOINT 训练损失更低而干净 MSE 更高, 读作过拟合, 不读作选择失败。[Opus 编辑 h]
- **剂量-响应 (非 gate)**: H_J(σ_b) 在 σ_b∈{0.3, 1.0, 2.0}, σ_n=0.03, seed 9001, 24 图; σ_b=1.0 与 2.0 复用 C2 与 C4 的 seed 9001 运行; σ_b=0.3 为新跑 {OMP-raw, BLOCK, JOINT}。报告 H_J(0.3) <= H_J(1.0) <= H_J(2.0) 是否成立, 不成立须记录。[Opus 编辑 i]
- **K-c 标志 (非 gate)**: 若 Tikhonov/Wiener (GCV) 的 MSE 在 >=3 个条件上比最优 Gaussian 臂低 >1 dB, 标 '本尺度下 Gaussian 容量无任务价值', 供下一轮 idea 参考。
- 空结果/STOP 后: 如实记录为负结果 (本合成基准、本候选族、该规则); '未检验' 与 '负结果' 措辞须区分; 不事后改基准; 不复活 F0/H2/CF0; 下一步须新 G0/新 idea/新合同/新 Opus 门。
- **功效披露 (更正)**: 假设图间 log 比标准差约 0.08 (未测), 标准误约 0.016。准则 (i) 要求点估计 <= log 0.95: 对真 5% 效应它单独约 50% 概率满足, 与 (iii)(iv) 联合更低; 本 gate 只在真效应约 >=8% 时才可靠检出 (功效约 0.98)。故空结果不能排除 3-6% 的效应; 报告须给出实测标准差。[Opus 编辑 f]

## 5. 有效性闸门 (失败=INVALID, 非对假说的判决)
V1 解析 Jacobian 对中心差分<1e-5; V2 LM 确定性 (同输入逐位相同) 且接受步 L 不增; **V3 JOINT 得分与暴力线性化 LS 一致到 1e-8 (K<=6 小例, split 与 birth 各测): 基线 = 不含该编辑的线性化回拟 ½‖P⊥r‖² (不假设驻点); 暴力 = min_δ ½‖r − c·v − AJ δ‖² (无权 LS, 忽略 1e-6 a² 项); split 取 c=1; birth 取 JOINT 的 c* (裁剪未触发时) 或固定在裁剪值 (裁剪触发时); 两者之差对 JOINT 得分** [Opus 编辑 j]; V4 复制不变性 (任一 Gaussian 拆成两个同参数半振幅副本, **原候选集**里每个候选的 JOINT 得分与排序不变到 1e-8; 复制体新增的 split 候选不在检查范围) [Opus 编辑 j]; V5 重标定不变性 (振幅×10, log↔线性互换, JOINT 排序不变); V6 规则/回拟/候选签名不接受 x_clean (静态检查+单测; ORACLE_x 除外); V8 候选生成确定性; V10 ‖P⊥v‖/‖v‖ 下限 1e-3 有效, 且 rcond∈{1e-8, 1e-12} 下 JOINT top-1 的稳定率被记录 (<90% 标记 '数值脆弱', GO 降为 INCONCLUSIVE-numerics); V11 可分离 A 与稠密 A 相对误差<1e-12; V12 伴随检验 <Ax,z>=<x,A^T z> 到 1e-12 (含非对称 B); V13 每次打分前记录驻点比; V14 钳边父候选被排除并计数; V15 LM 拒绝步上限触发次数被记录; **V16 (新) 第 1 步所有臂得到相同的 C_1 (哈希) 并使用同一编辑执行函数; V17 (新) ORACLE 的输出文件不被任何方法进程读取 (独立输出目录 + 方法 job 无该路径参数 + 日志检查)** [Opus 编辑 j]。去掉 v1 的 V7、V9。
**预算 (单位明确)**: <=4 h **墙钟**, <=6 并行进程, 总计约 20 CPU-h (Opus L1 估计, S1 给实测); BLAS 线程每进程 1; 并行 job 经宿主 pump 以 py job 提交, 每个 job 有 run_id。完整 oracle 单元 (ORACLE_y-full / ORACLE_x-full, 估计 15-20 min) 每单元一个 job, 每步写检查点可续跑, **豁免 20 min 单跑上限**; 其余 job <=20 min。**唯一允许的预算调整, 按此顺序**: (1) ORACLE_x-full 保持条件执行; (2) ORACLE_y-full 由 12 单元减至 6 单元; (3) ORACLE_xs/ys 短名单 top-8 降为 top-5; (4) birth-only/split-only 只保留 JOINT 与 OMP-raw; (5) INIT-N 只做 C1, C4。 [Opus 编辑 k]

## 6. 阶段与预注册子集
S0 单测/有效性 (无数据判读) -> S1 Pilot: 2 图 × C1,C4 × seed 9001 × {OMP-raw, BLOCK, JOINT, ORACLE_y-full}, **仅读时间与 V 闸门, 不读质量结果, 不用于任何调参, 不进 Gate** -> 若时间预测使全量超预算, 唯一允许的调整是预先写明的: 按 §5 预算段写明的顺序调整; 其余臂不改 -> S2 Dev: 24 图 × 4 条件 × 2 seed 的 {RAND, OMP-raw, BLOCK, JOINT, JOINT_FREE, FIXED-K×3, ORACLE_xs; ORACLE_ys 仅 seed 9001} + 三规则 birth-only/split-only + INIT-N + 剂量-响应, 冻结分析器 (experiments/as_analyze.py, sha256 入冻结记录) 一次运行。
- ORACLE_y-full 子集: 每族第 1 张 (图序 1, 9, 17) × C1, C4 × seed 9001 = 6 单元; 预算允许时扩至每族第 2 张 (图序 2, 10, 18), 共 12 单元。ORACLE_x-full (条件执行) 用同 12 单元。ORACLE_ys: seed 9001 的 96 单元。
- 任一闸门失败: 先写 FAILURES (INVALID/infrastructure), 不无限重试, 仅一次瞬时故障重试。

## 7. 与近邻的关系 (L1 线索未读原文者已标注)
- JOINT = 线性字典 OLS 量 (Soussen 等 2013, §II-C, L4) 的参数化版本; ADCG 联合回拟 (L4); SteepGS 判据 (L4 §4.4) 与 PUP 块对角 Fisher (L4 §4.2) 为块/逐点基线类。3DGS-LM 说明联合法方程可 matrix-free PCG (L4)。
- 近邻阅读状态 (更新自 G0 日志; 仅文档, 非设计变更): L4 自读 = Ho & Nguyen arXiv:1501.02497 技术报告版局部 (C59: 位置-协方差 Gaussian 混合 ∂²f/∂θ²=2∂f/∂Σ, 过拟合 k−k0=1 时 r̄=4, 与我的 O(d⁴) 同源, 非新观察), Unified Loss-Aware DC arXiv 2611.02044 (C60: 联合位置-尺度逐 Gaussian 二阶分裂已被占, 作者自述未建模跨 Gaussian 效应), SteepGS 附录 C.2 (C63: 零均值偏移项与其它 Gaussian 解耦, 交叉项只经均值位移进入 -> 分裂决策的跨 Gaussian 补偿在 O(ε²) 无作用), NOMP arXiv 1509.01942 (C61: 原始相关选择 + Newton/循环细化 + LS, 即 OMP-raw+回拟 的经典形式), Rota Bulò arXiv 2404.06109 (C62: 误差驱动致密化)。仍为 L1 (未读): Chen-Cowan-Grant 1991, The Tractor/Hogg-Lang, CLEAN/DAOPHOT, 3DGS-MCMC, Ho-Nguyen Ann. Statist. 正式版。
- 贡献叙述收窄为 proposed 三项: (i) 有限分裂的高阶/可执行补偿 (大概率已被占据); (ii) 模糊下局部近似与 split/merge 维护 (薄); (iii) 等时实证。本合同只检验"补偿选择是否有余量", 不声称其中任何一项。

## 8. 披露与限制
- 先验 (已按 Opus 复审更正): 我有纸面推导 (非证据) 与 K-a 自检 (research/notes/AS_KA_RESULT_20261105.md)。K-a 是**单步、K0=3、y 空间 (残差能量)** 的小玩具: 规则决策分歧大 (top-1 一致率 0.03-0.30), 中性实现值下 joint_c1 与 raw_c1 的相对遗憾差 −0.004 (n=108, 噪声大), 'v1 集 joint 更差' 与初始化混淆一致但只部分解释; y 空间单步 oracle 余量很小。Opus 同种子复核显示: 以干净 MSE 计, 一步合法 oracle 余量约 9%、ORACLE_x 约 17%, JOINT 的优势未解决; K0=6/σ_n=0.03 时读数翻转 (合法 oracle 拟合噪声而更差)。故 K-a **不是 '无余量' 证据**; 本合同是预注册 kill test, Opus 估计 GO 先验约 5-10%, 且 gate 只能可靠检出约 >=8% 的效应。判定规则与分析器在运行前冻结。
- 设计由我选择 (K0, σ, α, birth 形状), 有 tailoring 风险; 缓解: INIT-N 臂, 分族报告, 仅预注册配置计数, 剂量-响应对照。理想缓解 (未做): 由盲 worker 按 spec 生成图像。
- K-a 发现: 局部线性得分对 split 实现值的排序力弱 (c=1 的 Spearman 0.09-0.31, 自由系数 0.46); 本合同把它作为每步诊断量 (K-d) 保留并报告, 不作 gate。
- 结果仅限合成 32x32、本候选族、已知核。依赖: numpy only (宿主 .venv 需 numpy); 无 torch/GPU/付费云。
