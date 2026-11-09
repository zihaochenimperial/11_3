# CF-birth 设计说明 (proposed, 非 validated) — 最小可证伪机制、强基线、廉价 CPU 拒绝实验
作者: Sonnet5.5 (run 20261105T175811Z-session-6e38); 时间 2026-11-05T18:10:31Z。依据: 真人 17:57 London 批准新主线; G0-CF 结论见 research/nearest_work/G0_CF_BIRTH_NEAREST_WORK_20261105.md (统计机制不新, 价值只可能是 Gaussian birth 位置轴的实证边界+全预算核算)。本文件是合同草案前的设计, 阈值在冻结合同 (contracts/CF0_CONTRACT.md) 之前不具约束力。不得复用 E1-E14/W0/W1 做确认; F3 事后 9/12 仅为线索。

## 1. 要检验的最小机制 (一句话)
在现有 2D 高斯贪心 birth 管线 (K0=24 + 3 轮×8 births, 每阶段 150 步 Adam, 候选=ω 置换前 S=1024 个像素, 分数=高斯平滑(1.5px)|y-f|) 中, **只改一个变量: 选 birth 位置所用的信息来自哪里**。
- RAW: 位置由拟合所用同一份数据 y 的残差选出 (基系统)。
- XFER(tau) = 位置转移型交叉拟合: 用独立噪声副本 y_f = y + tau z 把整套贪心生长跑一遍得到 birth 位置 B_f (只用 y_f), 再用 y_g = y - z/tau (z~N(0,sigma0^2), 与 y_f 独立) 在这些位置上拟合 (forced_idx; birth 初值只用 y_g, 与 F3 的 G 腿同)。拟合副本噪声方差 sigma0^2 (1+tau^-2), 选择副本 sigma0^2 (1+tau^2)。
- NS(tau) (探索性, 不入 GO 门): 位置同样来自 y_f, 但在**完整 y** 上拟合——无信息损失, 但选择与拟合噪声仅部分独立 (相关系数 1/sqrt(1+tau^2)); 它不是交叉拟合, 属"选择随机化"(Tian-Taylor 类), 只作机制谱的另一端。
为何只用"位置转移"而不用"每轮在 f 上取对 g 拟合当前残差"的交错版: 后者的选择分数含 g 的噪声 (f - fit(g)), 条件独立性被破坏, 正是旧审计指出的 B-复用问题; 若以后要研究交错版须单独合同并做泄漏检验。

## 2. 可证伪主张 (前瞻; 阈值待合同冻结)
- CF-1 选择效应存在: 等噪声对照 (RAWg(tau) vs XFERg(tau), 同样在 y_g 上拟合, 仅位置来源不同) 的相对风险差 SE_tau 在新图上稳定为正。(事后线索: F3 的 D1/D2 类 8/8 正, D3 类 0/4 负。) 仅作机制诊断, **不是 GO 门**。
- CF-2 净效用 (GO 的唯一主门): 与实际可用的基线 RAWy (全数据 sigma0 上直接生长, K=48) 比, 计入信息损失: NU(tau) = (risk_RAWy - risk_XFERg(tau)) / risk_RAWy, 每图对 M 个噪声抽样取均值。预测 tau=1 为负 (拟合噪声翻倍), tau=4 拟合副本仅多 6% 方差、选择副本很噪但平滑残差仍能定位大结构 -> 可能转正; 这正是要试的。
- CF-3 对 K 轴强基线的增益: 对 RAW_R*cv (用 fission-CV 在 R∈{0..4} 即 K∈{24,32,40,48,56} 中选 K, 在 y 上生长到 R*) 的 NU 也须为正; 对 oracle-R (评测器选, 不可实现) 仅作上界报告。
- 失败条件 (STOP): 所有 tau 的 NU 上界 <+1% (可排除 >=1% 的净收益) -> scientific no-go, 记 FAILURES.md; 仅 CF-1 成立而 CF-2 不成立 -> 写成"选择偏倚存在但被信息损失吃掉"的负/边界结果, 不声称方法。

## 3. 臂与全预算核算 (每 (图, 抽样) 单位; 单位=拟合当量, 一轨迹 R<=4 记 1.25)
| 臂 | 数据 | 拟合当量 | 备注 |
|---|---|---|---|
| RAWy | y (sigma0) | 1.25 (R=0..4 轨迹, R=3 为 K=48 基线; 兼供 oracle-R / CV-R* 取值) | 主基线 |
| RANDy | y, S=8 (无选择) | 1 | 选择本身是否有益 |
| GROWf(tau) | y_f | 1.25 | 产生 B_f; 兼供 CV |
| GROWg(tau) | y_g | 1.25 | RAWg 等噪声对照 (R=3 端点); 兼供 CV |
| XFERg(tau) | y_g + forced B_f | 1 | CF-2 主臂 |
| XFERf(1) | y_f(1) + forced B_g(1) | 1 | 仅 tau=1, 第二个等噪声观测 |
| NS(tau) | y + forced B_f | 1 | 探索性 |
tau 网格 {1,2,4}: 共约 15.75 拟合当量/单位; 18 张开发图 x M=8 = 144 单位 ≈ 2270 当量 ≈ 30-65 min (按已测 0.6-1.3 拟合/s, 8 workers)。CF 的总成本 (GROWf+XFERg = 约 2.25-3.5 当量) 对 RAW 的 1.25 当量要如实报告; 数据损失以 (1+tau^-2) 方差因子报告。
K 轴 fission-CV: tau 下用 g 轨迹对 y_f 做留出 (cv_R = ||f_R^g - y_f||^2, 与 risk_R 相差常数 N sigma_f^2) (tau=1 时两方向平均), R*cv = argmin; 成本为已含轨迹, 无额外拟合。

## 4. 数据、种子与隔离 (拟冻结)
- 新图: E_k, k=15..18 为 pilot (4 张, 探索, 不入证据); k=21..38 为开发集 (18 张, 每型 6; 型=TYPES[(k-1)%3], gen_seed=3000+k, 与 E1-E14/W0/W1 零重叠); k=41..58 为确认集 **冻结前不得生成/查看**。
- 新 ENTROPY (拟 20261107, 待合同定), 新流编号 (e:21, omega:22, z:23, 自举:24); 图索引 img_index(E_k)=100+k 沿用。
- sigma0=0.08, N=4096, S=1024 固定; 单变量 = 位置信息来源 (及 tau 作为剂量轴); 其他 (steps, K 调度, lr) 不变。
- 隔离: 拟合器只接收 (y 副本, omega, S, cfg, forced_idx); 干净图仅在 runner 合成数据与评测器 risk(f,x) 中出现; XFERg 的 forced_idx 只由 y_f 生成。单测: (i) 用垃圾 y_g 重跑 XFERg, B 不变; (ii) 变更 y_g 噪声, GROWf 的 B_f 位逐位不变; (iii) 轨迹快照 R=3 与单独 R=3 管线逐位相等 (轨迹复用的正确性); (iv) e_f, e_g 经验独立 (z 检验); (v) forced 回放逐位复现。新代码放 src/cf_fit.py (复用 gsfast 私有函数, 不改冻结文件), 并加等价测试。
- 评测: risk = sum (f - x)^2 (src/reference_eval.py), 每图对 M 个抽样取均值, 图间 bootstrap CI (B=1000, 独立流)。

## 5. GO / REVISE / STOP (草案, 待 Opus 审)
- 有效性闸门: V1 单测全过; V2 逐位确定性与 forced 回放; V3 独立性 z 检验; V4 轨迹快照等价; V5 墙钟 <= 3 h; 任一失败 -> INVALID (记 FAILURES.md, 不解读)。
- GO-dev (进入确认合同, 非有效性/原创结论): 存在 tau in {1,2,4} 使 pooled NU(tau) >= +2%, 其 Bonferroni(3) 单侧 bootstrap 下界 > 0, >= 12/18 图为正, 且对 RAW_R*cv(tau) 的 NU >= +1%。
- STOP: 所有 tau 的 NU 上界 < +1%。
- 其余 -> INCONCLUSIVE: 至多一次 M 扩到 16, 仍不明朗 -> 写成边界结果, 不升级。
- CF-1/NS/类型分层 (D1/D2/D3) 只作诊断, 不改闸门。

## 6. 已知风险与先验预测 (提前写下以防事后合理化)
1. 预测 tau=1 的 NU<0 (信息损失主导); 若 tau=1 为正则异常, 须查泄漏。
2. D3 (高复杂度) 类图上 XFER 可能更差 (F3 线索: E6 +1.24, E9 +1.00)。
3. K 轴基线可能解释大部分 D1 上的"错误生长" (smooth 图最佳 K 可能 <48)。
4. 贪心位置的转移要求 f 与 g 上的生长轨迹共享 omega 候选集; 若 B_f 与 y_g 的结构不匹配 (初值 val 取自 y_g) 可能产生非最优拟合。
5. 此为 64x64 合成玩具, 不外推真实图像; 无 GPU, 无分数承诺; 没有原创性声称。

## 7. 需要真实 Opus 回答
Q1 G0-CF 的"机制不新、价值=实证边界"判断与标注是否站得住? Q2 设计中的泄漏/估计量/基线缺口 (含: 是否漏了 data-thinning-CV / randomized-greedy 集成 / selection-bias 校正等强基线)? Q3 NU 主门、tau 网格、M=8、18 图、阈值是否合理, 功效是否足够? Q4 NS 是否应保留/移出? Q5 go/revise/stop: 是否值得冻结合同并跑 pilot?
