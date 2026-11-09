# JR 合同候选 v0 — 观测混淆分组 + 组内有限幅度联合 Gaussian 几何修复 (CPU 机制验证)
状态: 候选, 待真实 Opus 审 → 修具体阻断 → 冻结 (记 sha 到 contracts/JR_FREEZE_RECORD.txt)。作者 Sonnet 5.5 (主研); 科学门 Opus 5.5。
一切主张为 proposed; 0 已验证贡献; 不保证原创性或分数。分组-by-耦合在数值优化中属经典/近经典 (见 research/notes/G0_reading_log_JR_20261108.md), 本线不主张该机制本身新; CPU 阶段只回答 "这一机制在固定 K、已知 PSF、真实更新下有没有净增量"。
授权 (逐字摘自真人经 Codex 转交, memory/AUTHORIZATIONS.md): "用已知模糊核造成的观测混淆来分组, 做组内有限幅度的联合 Gaussian 几何修复 … 新 CPU 合同经真实 Opus 审定并冻结后，直接运行真实更新的小图对照 … 首轮对照是按模糊响应分组 vs 空间邻居分组 vs 独立更新加线性投影，费用全计。旧 TRN/RJ 不重开。" 真人回 "停" 即停。CPU/8GB, 不开 GPU, 不启用付费, 宿主 pump 保持停止, 产物在 D:\Gaussian\outputs\JR 与 runs 下。

## 1. 对象与假设
对象: 固定 K 个各向异性 2D Gaussian θ_k=(w,mx,my,l11,l21,l22) (Σ=LLᵀ, L=[[e^l11,0],[l21,e^l22]]), 单张观测 y=A x_true+σ ξ, A 为已知 PSF 精确稀疏算子 (半样本反射边界), σ=0.02; 目标 F_a(θ)=1/(2σ²)‖y−A x(θ)‖²+(a/2)‖x(θ)‖², a=1e-3/σ² (同 geo_core)。不出生、不合并、K 固定; 每个有限更新均以完整真实前向核验 (增量前向 r₂=r−A(x_g,new−x_g,old) 与完整重渲染逐元等价, 单测)。
假设 H: 由当前离散化白化模糊响应得到的 "观测混淆" 分组 (组内 Gaussian 的几何参数被同一观测混淆, 弱可辨识量以噪声尺度为界), 配合组内有限幅度联合更新, 在同一费用 (含分组构建费用) 下比 (a) 空间邻居分组、(b) 独立更新+线性投影、(c) 去掉模糊的同构耦合分组 (OBS0)、(d) 随机分组 (RND)、(e) 单原语 Gauss–Seidel (IND1) 得到更好的重建质量。H 也可能为假; 合同按此设计决策。

## 2. 数据边界 (新建, 与旧 TRN/RJ 数据分离)
- 生成: src/jr_gen.py (评测侧, 方法侧 jr_core/jr_op 禁止 import, 单测核查)。图像 = 32×32 as_gen 配方 tile (种子标签 20, 噪声标签 21), 与 geo_gen/as_gen/trn_gen 种子空间不相交。
- 设计冒烟 590–592 (base 9501): 仅用于定网格/预算, 不作证据, 不进调参集/核验集。
- 调参集 TUNE 501–506 (base 9511) × 4 核 = 24 题。核验集 VERIFY 511–522 (base 9521) × 4 核 = 48 题。
- VERIFY-2 701–712 (base 9531): 封存; 仅当 §9 判为 CORRECT-ONCE 且冻结记录出现 VERIFY2_UNSEALED 行时可读, 单次使用。
- 旧集合 1..24、41..58、101..112、201..224、301..344、351..398、401..424 一律拒绝; 预留不生成: 训练池 531..578 (阶段 2), 未来确认 601..624 (无条件封存)。
- PSF (方法已知): G15 = 各向同性 Gaussian s=1.5 (与 geo_core 的可分离 B 逐元一致, 单测); AG = 各向异性 Gaussian (σmaj=3, σmin=1, 30°); MO = 运动线 (L=11, 30°, 16 倍亚采样双线性); DK = 圆盘 (r=3, 8×8 亚采样)。N=32, K=36 (GC.grid_init 同初值), 所有臂同一初值 θ0。
- 阶段 2 才有的 "未见核族/留出" 不在 CPU 阶段 (方法本身不学习)。

## 3. 臂 (同一引擎 src/jr_core.py, 同一冻结接受判据: pred>0、act>0、act/pred≥RHO_MIN、线性化 guard、箱约束夹取、投影梯度活动集)
一次外层 SWEEP = 线性化(全体 J, AJ) → 分组 → 按组质心栅格序的 Gauss–Seidel 访问 (每组用当前残差做有限幅度更新, 经精确增量前向核验, 最多 10 次回溯, per-primitive κ_k, 组 κ=max, 接受且 ratio≥0.75 则 /3, 拒绝则 ×3) → 完整刷新。
| 臂 | 分组依据 | 组内更新 |
|---|---|---|
| OBS-J (主) | 白化标定响应耦合 a_kl=‖(R_kᵀR_k+I)^-1/2 R_kᵀR_l (R_lᵀR_l+I)^-1/2‖₂, R=AJ·d/σ, d_kj 使未模糊像效应为 ‖x_k‖ 的 10% (单位无关: 参数坐标重标度不变, 单测); 脊=1 即噪声尺度: 严格零空间贡献 0, 弱可辨识方向被压低; 候选对=膨胀 4σ 支撑盒重叠; 平均连接 agglomeration, 组大小≤gs | 联合 6|g| 参数阻尼 GN (像度量阻尼 κΛ_A, SVD 像基) |
| SPA-J | 质心距离 (−距离) 同一 agglomeration | 同上 |
| OBS-I | 同 OBS-J | 各原语独立 6 参步 (同一残差), 再在其张成空间上取最优 |g| 维步长缩放 (无阻尼二次模型线性投影) |
| OBS0-J (对照) | 同 OBS-J 但 R=J d/σ (去掉模糊) | 联合 |
| RND-J (对照) | 随机亲和 (seed 固定) 同一 agglomeration | 联合 |
| IND1 (对照) | gs=1 (单原语 GS, = geo_core BLK) | 同一 |
| FULL (参照, 不调参) | 单组 36 原语 | 联合 (冻结接受+夹取在 216 参数下常 no_step, 仅作弱参照, 不进决策) |
超参: gs∈{2,3,4,6,9} 子集, κ0, f=3 固定, rcond=GC.RCOND。

## 4. 费用口径 ("费用全计")
W = flop 代理 (geo_flops 冻结公式 + 稀疏算子每次施加 2·nnz(A)); 类别 lin(J 构建+A 施加到 6K 个 J 列)、grp(分组: 候选对 Gram 块、6×6 逆平方根、范数、agglomeration; SPA/RND/IND1 同口径计其真实小费用)、solve、check(增量前向+预测增益)、refresh。诊断量 (奇异值/补偿比/ARI/弱-零空间计数) 不影响轨迹, 不计费, 标 diag。主指标全部以 W 为横轴; 墙钟 (perf_counter) 同报作次要 (单进程独占核, 另报 CPU 总小时)。调参的 CPU 小时单独报告 (开发成本), 不进 W。

## 5. 调参协议 (每臂同等对待, 仅用调参集, 准则 = 调参集 Q-AUC 均值)
坐标式: T1: gs∈{2,4,9} @κ0=0.1; T2: κ0∈{0.03,0.3} @T1 最佳 gs。IND1: κ0∈{0.03,0.1,0.3}。FULL 不调 (κ0=0.1)。每臂共 ≤5 个配置 × 24 题。平局 (|ΔQ|<0.02 dB) 取平均 W 小者。最佳在网格边缘时仅记录, 不外延。选出的单一配置 (跨 4 核池化, 不按核分别调) 冻结后用于 VERIFY。

## 6. 运行协议
每个 (臂,题) 运行: max_sweeps=600, W_cap=3.0e10 (在 sweep 末检查, 首个 W≥cap 的 sweep 末停); 提前 stop('converged' 连续 3 sweep 相对降幅≤1e-9; 'no_step' 连续 3 个 sweep 无接受) 则状态向后沿用。W 网格 GRID=geomspace(1e9, 3e10, 8); 网格点 B 的状态 = W≤B 的最后一个完成 sweep 的 θ (无则 θ0)。同一 (题,臂) 无重复种子 (RND 用固定 seed 0)。

## 7. 指标 (评测侧, 对干净图)
- Q-AUC (主): 对 8 个网格点取 PSNR(x(θ_B), x_clean) 的均值 (峰值 1)。
- O-AUC (次): 对网格点取 log10 max((F_B−F_ref)/(F0−F_ref), 1e-4) 的均值 (越低越好); F_ref = 该题全部臂访问级最小 F (仅 VERIFY, 描述用)。
- 终点: Q_end=cap 时 PSNR, F_end; cost-to-target: 首个 F≤F_ref+ρ(F0−F_ref) 的 W, ρ∈{0.1,0.03}, 未达则按 cap 计 (删失); 每臂拒绝率、回溯数、被夹取比例、停止原因。
- 机制诊断 (diag, 不计费): 组补偿比 ‖AJ_gδ‖/Σ_i‖AJ_iδ_i‖; OBS 组的 ARI (跨 PSF、OBS vs SPA、相邻 sweep); R_k 奇异值中 >1 (可辨识)、(0,1] (弱可辨识)、=0 (严格零空间) 的个数; 邻居变化随 PSF; 有限更新后观测一致性 (残差范数/σ 随组大小)。

## 8. 统计
分析单位 = 图 (VERIFY 12 张, 每图对 4 核取均值) 的配对差; 配对 bootstrap (图重采样 10000, seed 20261108) 取 5 分位作单侧 95% 下界 LB; 另按核族报 12 张图的配对差与符号计数。

## 9. 预注册决策 (VERIFY 一次读取, 之后不再改)
ΔQ(X)=Q-AUC(OBS-J)−Q-AUC(X) (dB)。PASS_X ⇔ mean ΔQ(X)≥δ_X 且 LB>0; δ=0.15 dB 对 X∈{SPA-J, OBS-I, RND-J, IND1}, δ=0.10 dB 对 OBS0-J。核族守卫: 对 Q 最强对照 X*, 任一核族的 mean ΔQ(X*)≥−0.10 dB。
- CONTINUE: 五个 PASS 全成立且守卫成立 → 先由 Opus 审定阶段 2 阈值并冻结 (Astra 建议: 对最强基线 +0.30 dB, 对最强消融 +0.15 dB, 配对区间下界>0, 任一留出核族不低于 −0.10 dB, 推理≤2× 最强重建对照, 噪声一致性), 才可开单张 8GB 小模型对 同容量/同数据普通 PSF 条件 Gaussian、像素网络+数据校正、调好的 TV、DPIR; 至少两个未见核族与按图留出。本合同不冻结阶段 2 阈值。
- CORRECT-ONCE: 不满足 CONTINUE, 但 PASS_SPA、PASS_RND、PASS_OBS0 成立 (观测基分组被支持), 且 "分组免费" 诊断 (O 与 Q 由同一轨迹把分组费用从 W 中扣除: W_free=W−grp_cum) 使 PASS_OBS-I 与 PASS_IND1 成立 → 唯一修正 = 分组复用间隔 R∈{2,4,8} (在 TUNE 上按 Q-AUC 选, 代价全计), 在 VERIFY-2 用同一规则重判; 之后不再修正。
- STOP: 其余情形 (含 OBS 显著劣于 SPA/RND)。记 FAILURES (FAIL-0035), 不开阶段 2, 不重开 TRN/RJ。负结果与数字全部保留。

## 10. 单元测试 (tests/test_jr_core.py, 冻结前后必须通过)
1) 稀疏 A(G15)=B⊗B 逐元一致 ≤1e-12; 伴随=转置; 2) 增量前向的 F 与完整重渲染 ≤1e-9, 经多次访问仍成立; 3) IND1 前若干 sweep 与 geo_core._iter_blk 逐步一致; 4) 亲和在参数坐标重标度下不变 (≤1e-8); 5) 非候选对耦合=0; 6) 费用计数: 各类别和=W, A 调用数与 SOp 真实调用一致; 7) 方法侧模块不 import jr_gen/clean_image; 8) 闸门拒绝旧/封存/未解封索引; 9) 去模糊后 OBS0 与 OBS 在 A=I 时亲和相等。

## 11. 声明的限制
无学习成分, 无法检验跨未见核泛化; 单一 N=32/K=36/σ=0.02、四种核、合成 tile; 模型失配区 (Fref 对应残差>噪声), PSNR 与 F 脱钩, 故决策用 Q 并同报 O; FULL 因冻结接受+夹取而弱, 不进决策; n=12 张图, 功效有限 (δ 取 Astra 的阶段阈值量级, 非功效计算)。N=64 作为 "阶段 1b 缩放检查" 仅在 CONTINUE 之后另议, 不属本合同。

## 12. 先验诚实记录 (设计冒烟, 590–592 × 4 核, N=32, 未调参 gs=4 κ0=0.1, n=12 题)
ΔQ-AUC(OBS−X): SPA +0.24±0.17 dB; OBS-I −0.72±0.18; OBS0 −0.03±0.09; RND −0.94±0.10; IND1 −0.88±0.19; FULL +2.64±0.34。O-AUC(OBS−X): SPA +0.21, IND1 +0.14, RND −0.13, OBS-I −0.19, OBS0 +0.10 (正=OBS 更差)。分组: OBS vs SPA 的 ARI≈0.21–0.32; OBS 分组随 PSF 的 ARI 0.59–1.00; 相邻 sweep ARI 0.3–1.0。候选对 630/630 (初始网格无剪枝)。分组费用 ≈ 线性化费用的 50%。预期 (未调参): STOP。本节写在跑正式对照之前, 合同的阈值不根据 VERIFY 调整。

## 13. 产物与回执
experiments/jr_run.py (运行器, shard 化), experiments/jr_reduce.py (统计); outputs/JR/{tune,verify}/ 每题 JSON; 冻结记录 contracts/JR_FREEZE_RECORD.txt 记合同 sha、各模块 sha、TUNE_DONE/VERIFY_START/VERIFY_DONE 行。runlog 事件与 Opus 审原文归档于 research/notes。
