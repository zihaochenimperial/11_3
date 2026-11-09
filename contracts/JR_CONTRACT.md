# JR 合同候选 v1 — 观测混淆分组 + 组内有限幅度联合 Gaussian 几何修复 (CPU 机制验证)
状态: v1 = v0 + Opus R1–R9 (research/notes/OPUS_REVIEW_JR_CONTRACT_v0_20261108.md; runlog 20261108T215538Z-model-call-2985; Opus 明示 "R1–R9 落实后即可冻结, 无需再审"); 冻结后不改规则, 修订只能走新版本并记录; 冻结记录 contracts/JR_FREEZE_RECORD.txt。作者 Sonnet 5.5 (主研); 科学门 Opus 5.5。
一切主张为 proposed; 0 已验证贡献; 不保证原创性或分数。**新颖性 (§0)**: 分组-by-耦合在数值优化与天文/显微测光中属经典; 本线不主张该机制本身新。
授权 (逐字摘自真人经 Codex 转交, memory/AUTHORIZATIONS.md): "用已知模糊核造成的观测混淆来分组, 做组内有限幅度的联合 Gaussian 几何修复 … 新 CPU 合同经真实 Opus 审定并冻结后，直接运行真实更新的小图对照 … 首轮对照是按模糊响应分组 vs 空间邻居分组 vs 独立更新加线性投影，费用全计。旧 TRN/RJ 不重开。" 真人回 "停" 即停。CPU/8GB, 不开 GPU, 不启用付费, 宿主 pump 保持停止, 产物在 D:\Gaussian\outputs\JR。

## 0. 近邻与新颖性 (R8)
读取深度见 research/notes/G0_reading_log_JR_20261108.md (含声明)。机制 (a) "由当前离散化白化模糊响应 (脊 = 相对 10% 标定扰动的噪声尺度) 的耦合分组" 的**最近经典对照是 PSF 重叠分组同时拟合**: Stetson 1987 DAOPHOT/NSTAR (按剖面延伸的临界间距分组, 组内联合线性化最小二乘)、3D-DAOSTORM 的相邻发射体分组 (Babcock–Sigal–Zhuang 2012); 另有加性/重叠 Schwarz 块法、Nutini–Laradji–Schmidt 的贪心块选择与 message passing 块更新。该对照由 **OVL-J 臂**直接检验 (不白化、不加脊); 若 OBS 不优于 OVL, 则 "白化响应 + 噪声尺度脊" 不具备增量。CPU 阶段只回答固定 K、已知 PSF、真实更新下有没有净增量。

## 1. 对象与假设
对象: 固定 K 个各向异性 2D Gaussian θ_k=(w,mx,my,l11,l21,l22) (Σ=LLᵀ, L=[[e^l11,0],[l21,e^l22]]), 单张观测 y=A x_true+σ ξ, A 为已知 PSF 精确稀疏算子 (半样本反射边界), σ=0.02; 目标 F_a(θ)=1/(2σ²)‖y−A x(θ)‖²+(a/2)‖x(θ)‖², a=1e-3/σ² (同 geo_core)。不出生、不合并、K 固定; 每个有限更新均以完整真实前向核验 (增量前向与完整重渲染逐元等价, 单测)。共同初始化 GC.grid_init (按 y 的最小二乘幅度, 36 次渲染+施加) 对所有臂相同, 不计入 W。
假设 H: 由观测混淆分组 + 组内联合有限更新, 在同一费用 (含分组构建) 下比 (a) 空间邻居分组 (SPA)、(b) 独立更新+线性投影 (OBS-I)、(c) 去掉模糊的同构耦合分组 (OBS0)、(d) 随机分组 (RND)、(e) PSF 重叠分组 (OVL, DAOPHOT 式)、(f) 单原语 Gauss–Seidel (IND1) 得到更好的重建质量, **且** F 间隙不劣 (R1: 排除 "欠拟合式隐式正则")。H 可能为假; 合同按此设计决策。

## 2. 数据边界 (新建, 与旧 TRN/RJ 数据分离; R7 闸门)
- 生成: src/jr_gen.py (评测侧, 方法侧 jr_core/jr_op 禁止 import, 单测核查)。图像 = 32×32 as_gen 配方 tile (种子标签 20, 噪声标签 21), 与 geo_gen/as_gen/trn_gen 种子空间不相交。
- 设计冒烟 590–592 (base 9501): 仅用于定网格/预算与流程干跑 (stage dry), 不作证据。
- TUNE 501–506 (base 9511) × 4 核 = 24 题, 可自由读取。
- **VERIFY 511–522 (base 9521) × 4 核 = 48 题: 封存闸门 (jr_gen._sealed_gate)**: 读取须同时满足 (1) 环境变量 JR_VERIFY_UNLOCK=1; (2) 冻结记录含 TUNE_DONE 与 VERIFY_UNSEALED 行; (3) 运行中的分析器 (__main__ = experiments/jr_run.py) 的 sha256 与所有已加载 src/jr_*.py 的 sha256 均已登记 (ANALYZER_SHA256 / MODULE_SHA256 行); (4) 首次成功读取由父进程追加 VERIFY_CONSUMED 行, fork 出的 worker 继承会话; 之后任何新进程读取必须先有一行显式的 VERIFY_RESUME_OK (崩溃恢复; 须在冻结记录与终态报告中披露)。干跑只允许 TUNE 或 590–592。单测只用哑索引/临时记录文件测试门控逻辑, 不合成任何 VERIFY 图。
- VERIFY-2 701–712 (base 9531): 同样闸门 (VERIFY2_UNSEALED / VERIFY2_CONSUMED); 仅在 VERIFY 判为 CONTINUE 且 Opus 另行同意的阶段 1b 附录中作为独立复现使用 (R5)。
- 旧集合 1..24、41..58、101..112、201..224、301..344、351..398、401..424 一律拒绝; 预留不生成: 训练池 531..578 (阶段 2), 未来确认 601..624 (无条件封存)。
- PSF (方法已知): G15 = 各向同性 Gaussian s=1.5 (与 geo_core 的可分离 B 逐元一致, 单测); AG = 各向异性 Gaussian (σmaj=3, σmin=1, 30°); MO = 运动线 (L=11, 30°, 16 倍亚采样双线性); DK = 圆盘 (r=3, 8×8 亚采样)。N=32, K=36, 所有臂同一初值 θ0。阶段 2 才有 "未见核族" 的留出, CPU 阶段方法本身不学习。

## 3. 臂 (同一引擎 src/jr_core.py, 同一冻结接受判据: pred>0、act>0、act/pred≥RHO_MIN、线性化 guard、箱约束夹取、投影梯度活动集)
一次外层 SWEEP = 线性化 (全体 J, AJ) → 分组 (每 R 个 sweep 重建; 复用期间不计 grp) → 按组质心栅格序的 Gauss–Seidel 访问 (每组用当前残差做有限幅度更新, 经精确增量前向核验, 最多 10 次回溯, per-primitive κ_k, 组 κ=max, 接受且 ratio≥0.75 则 /3, 拒绝则 ×3) → 完整刷新。
| 臂 | 分组依据 | 组内更新 |
|---|---|---|
| OBS-J (主) | 白化标定响应耦合 a_kl=‖(R_kᵀR_k+I)^-1/2 R_kᵀR_l (R_lᵀR_l+I)^-1/2‖₂, R=AJ·d/σ, d_kj 使未模糊像效应为 ‖x_k‖ 的 10% (单位无关, 参数坐标重标度不变, 单测); 脊=1 是**相对该 10% 标定扰动的噪声尺度**: 严格零空间贡献 0, 弱可辨识方向被压低; 候选对=PSF 膨胀 4σ 支撑盒重叠; 平均连接 agglomeration, 组大小≤gs | 联合 6|g| 参数阻尼 GN (像度量阻尼 κΛ_A, SVD 像基) |
| SPA-J | 质心距离 (−距离) 同一 agglomeration | 同上 |
| OBS-I | 同 OBS-J | 各原语独立 6 参步 (同一残差), 再在其张成空间上取最优 |g| 维步长缩放 (无阻尼二次模型线性投影) |
| OBS0-J (对照) | 同 OBS-J 但 R=J d/σ (去掉模糊) | 联合 |
| RND-J (对照) | 随机亲和 (seed 固定) 同一 agglomeration | 联合 |
| **OVL-J (对照, R3)** | PSF 膨胀 4σ 支撑盒的重叠面积 (DAOPHOT 式, 不白化、不加脊) 同一 agglomeration | 联合 |
| IND1 (对照) | gs=1 (单原语 GS, = geo_core BLK 同一访问序, 单测) | 同一 |
| FULL (参照, 不调参, 不进决策) | 单组 36 原语 | 联合 (冻结接受+夹取在 216 参数下常 no_step, 弱参照) |
超参: gs, κ0, R 见 §5; f=3 固定, rcond=GC.RCOND。

## 4. 费用口径 ("费用全计")
W = flop 代理 (geo_flops 冻结公式 + 稀疏算子每次施加 2·nnz(A)); 类别 lin(J 构建+A 施加到 6K 个 J 列)、grp(分组)、solve、check(增量前向+预测增益)、refresh(含初始状态评估)。grp: OBS/OBS0 = 候选对 Gram 块 + 6×6 逆平方根 + 范数 (按支撑稀疏实现计价; **代码实现为稠密 Gram, 墙钟偏高, W 为准**), SPA = 6K²+距离, OVL = 12K², RND = 2K²; 所有分组臂另加 agglomeration 10·K³ (R6); IND1/FULL = 0。诊断量 (奇异值/补偿比/ARI/弱-零空间计数) 不影响轨迹, 不计费, 标 diag。墙钟 (perf_counter) 同报作次要。调参的 CPU 小时单独报告 (开发成本), 不进 W。

## 5. 调参协议 (R4; 每臂同等对待, 仅用 TUNE, 准则 = TUNE 上 Q-AUC 均值)
分组臂 (OBS-J、SPA-J、OBS-I、OBS0-J、RND-J、OVL-J): T1 gs∈{2,4,9} @κ0=0.1, R=1; T2 R∈{1,4} @T1 最佳 gs; T3 κ0∈{0.03,0.3} @最佳 (gs,R) (连同 κ0=0.1 共 3 选 1); 每臂 6 个配置。IND1: κ0∈{0.01,0.03,0.1,0.3,1} (5 个)。FULL 不调 (κ0=0.1)。平局 (|ΔQ|<0.02 dB) 取平均 W 小者, 再取小 gs、小 R、小 κ0。网格边缘最佳仅记录, 不外延。R = 分组复用间隔 (每 R 个 sweep 重建一次, 其余复用上一分组)。选出的单一配置 (跨 4 核池化) 冻结后用于 VERIFY。描述性 (不进选择): TUNE 上对 OBS-J 的亲和脊 ∈{0.1,1,10} 敏感性。

## 6. 运行协议
每个 (臂,题): max_sweeps=1500 (使最便宜的臂也能触及 W_cap; 干跑显示 IND1 在 600 时尚未到 cap), W_cap=3.0e10 (sweep 末检查, 首个 W≥cap 的 sweep 末停); 提前 stop ('converged' 连续 3 sweep 相对降幅≤1e-9; 'no_step' 连续 3 个 sweep 无接受) 则状态向后沿用。W 网格 GRID=geomspace(1e9, 3e10, 8) **冻结, 不再动**; 网格点 B 的状态 = W≤B 的最后一个完成 sweep 的 θ (无则 θ0)。RND 用固定 seed 0。

## 7. 指标 (评测侧, 对干净图)
- Q-AUC (决策主指标): 8 个网格点 PSNR(x(θ_B), x_clean) 的均值 (峰值 1)。
- O-AUC (决策共同指标, R1): 8 个网格点 log10 max((F_B−F_ref)/(F0−F_ref), 1e-4) 的均值 (越低越好); F_ref 在 VERIFY 中按题取**全部 8 个臂**访问级最小 F (含 FULL); 它对所有臂相同, O-AUC 之差可比。
- 另报: 每臂 "轨迹 PSNR 峰值及其所在 W" 与终点 PSNR (识别 PSNR 先升后降/过拟合); Q_end、F_end; cost-to-target (ρ∈{0.1,0.03}, 删失按 cap); 每臂 stop 原因分布 (含 no_step 比例)、拒绝率、被夹取比例、grp 占 W 比例、墙钟; 描述性 "匹配 F 的 PSNR" 与 "分组免费" (W−grp_cum) 读数 (不进决策)。
- 机制诊断 (diag, 不计费): 组补偿比 ‖AJ_gδ‖/Σ_i‖AJ_iδ_i‖; OBS 组的 ARI (跨 PSF、OBS vs SPA、OBS vs OVL、相邻 sweep); R_k 奇异值中 >1 (可辨识)、(1e-6,1] (噪声尺度下弱可辨识)、≤1e-6 (严格零空间) 的个数; 有限更新后观测一致性。

## 8. 统计 (R2)
分析单位 = 图 (VERIFY 12 张, 每图对 4 核取均值) 的配对差。单侧 95% 界一律用 BCa (图重采样 10000, seed 20261108, 复用 experiments/trn_same_state_reduce.bca, alpha=0.10 取 5%/95% 分位); 另要求符号计数 ≥ 8/12。按核族另报 12 张图的配对差。功效声明: 冒烟中配对差 SE≈0.05–0.19 dB, n=12 对 SPA (SE≈0.17) 的功效偏低, 判 STOP 可能含 "INCONCLUSIVE" 成分, 终态报告须据区间如实标注; 阈值取 Astra 的阶段量级, 非功效计算。

## 9. 预注册决策 (VERIFY 一次读取, 之后不再改; R1/R5)
ΔQ(X)=Q-AUC(OBS-J)−Q-AUC(X) (dB); ΔO(X)=O-AUC(OBS-J)−O-AUC(X) (log10)。
PASS_X ⇔ (i) mean ΔQ(X) ≥ δ_X, BCa 单侧 95% 下界 > 0, 且符号计数 ≥ 8/12; **且** (ii) ΔO 的 BCa 单侧 95% 上界 ≤ +0.05 (O-AUC 非劣)。只满足 (i) 而 (ii) 不成立 → 记 "正则效应, 非机制增量", 不 PASS。
δ_X=0.15 dB 对 X∈{SPA-J, OBS-I, RND-J, IND1}; δ_X=0.10 dB 对 X∈{OBS0-J, OVL-J}。核族守卫: 对 Q-AUC 最强对照 X*, 任一核族的 mean ΔQ(X*) ≥ −0.10 dB。
- **CONTINUE**: 六个 PASS 全成立且守卫成立 → 先由 Opus 审定阶段 2 阈值并冻结 (Astra 建议: 对最强基线 +0.30 dB, 对最强消融 +0.15 dB, 配对区间下界>0, 任一留出核族不低于 −0.10 dB, 推理≤2× 最强重建对照, 噪声一致性), 才可开单张 8GB 小模型 vs 同容量/同数据普通 PSF 条件 Gaussian、像素网络+数据校正、调好的 TV、DPIR; 至少两个未见核族与按图留出。VERIFY-2 仅作阶段 1b 独立复现附录, 须另立附录并经 Opus 同意。本合同不冻结阶段 2 阈值。
- **STOP**: 其余一切情形 (含 OBS 显著劣于控制组)。唯一修正分支已删除 (R5): 分组复用间隔 R 已并入调参。记 FAILURES (FAIL-0035), 不开阶段 2, 不重开 TRN/RJ。负结果与数字全部保留。

## 10. 单元测试 (tests/test_jr_core.py, 冻结前必须通过; 当前 13 项)
稀疏 A(G15)=B⊗B 逐元一致且伴随=转置; 增量前向与完整重渲染一致 (joint 与 ind_lp); IND1 首个 sweep 与 geo_core BLK 逐元一致; 亲和对参数坐标重标度不变; 非候选对耦合=0 且真实耦合可忽略; 费用计数 (类别和=W, A 调用数与算子真实调用一致); 方法侧模块不 import 评测侧; 数据闸门拒绝旧/封存/未知索引且不合成图; **封存闸门逻辑 (R7, 临时记录/哑文件)**; A=I 时 OBS 与 OBS0 亲和相等; 分组为大小受限的划分且确定性; **OVL 亲和 (R9-10)**; **复用间隔 R 的费用计数 (R9-12: 复用 sweep 不计 grp)**。

## 11. 声明的限制
无学习成分, 无法检验跨未见核泛化; 单一 N=32/K=36/σ=0.02、四种核、合成 tile; 模型失配区 (F_ref 对应残差>噪声), PSNR 与 F 脱钩, 故决策同时看 Q 与 O; FULL 弱, 不进决策; n=12 张图, 功效有限; 实现为稠密 Gram, 墙钟≠W; 近邻读取深度见 G0 记录。N=64 缩放检查仅在 CONTINUE 后另议。

## 12. 先验诚实记录 (设计冒烟, 590–592 × 4 核, N=32, 未调参 gs=4 κ0=0.1, n=12 题; 写在跑正式对照之前)
ΔQ-AUC(OBS−X): SPA +0.24±0.17 dB; OBS-I −0.72±0.18; OBS0 −0.03±0.09; RND −0.94±0.10; IND1 −0.88±0.19。O-AUC(OBS−X): SPA +0.21, IND1 +0.14, RND −0.13, OBS-I −0.19, OBS0 +0.10 (正=OBS 更差)。分组 ARI: OBS vs SPA≈0.21–0.32; OBS 随 PSF 0.59–1.00; 相邻 sweep 0.3–1.0。候选对 630/630。分组费用≈线性化费用的 50% (v0 口径)。预期 (未调参, 无 OVL): STOP。阈值不依据 VERIFY 调整。
流程干跑 (outputs/JR/dry, 590–592 × 4 核, 全部 8 臂含 OVL, gs=4 κ0=0.1 R=1 (OBS-I 为 R=2), 仅验证流水线, 非证据): ΔQ(OBS−X) SPA +0.23, OBS-I −0.80, OBS0 −0.02, RND −1.00, OVL −0.36, IND1 −0.83 dB; 机械判读 STOP。诊断: θ0 处 216 个标定响应方向中弱可辨识 (≤噪声尺度) 仅 G15=0, AG=4, MO=7, DK=0, 严格零空间 0 —— 在 10% 标定下 "弱/零空间" 区分在初始状态几乎为空 (记为诊断, 不改合同)。

## 13. 产物与回执
experiments/jr_run.py (分析器/运行器, fork 并行), experiments/jr_reduce.py; outputs/JR/{tune,verify,dry}/ 每题每臂 JSON; 冻结记录 contracts/JR_FREEZE_RECORD.txt 记合同 sha、模块 sha、ANALYZER_SHA256、MODULE_SHA256、TUNE_DONE、VERIFY_UNSEALED、VERIFY_CONSUMED 等行。runlog 事件与 Opus 审原文归档于 research/notes。
