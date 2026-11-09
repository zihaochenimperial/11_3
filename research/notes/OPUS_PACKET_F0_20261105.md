# OPUS REVIEW PACKET — F0 CPU falsification contract for "search-risk" in adaptive 2D Gaussian fitting
(You are the scientific gate reviewer. Read this single file. Everything below was written by a Sonnet-class model; none of it has been independently reviewed or run. No experiments exist yet. Be adversarial and specific.)

## What I need from you
Return a verdict **ACCEPT / ACCEPT-WITH-CHANGES / REVISE / REJECT** for contracts/F0_CONTRACT_DRAFT (section C below), with:
1. A correctness check of the derivations T1-T3 in section B (especially T3: E[div_hat(eps)] = df at noise level sqrt(s^2+eps^2), no smoothness needed). Say whether the proof steps are right, wrong or incomplete; give a corrected statement if needed.
2. Numbered required changes to the contract (design confounds, thresholds, estimands, sample sizes, missing controls, anything that could make H1/H2 pass or fail for the wrong reason, e.g. optimisation non-convergence creating fake df, top-k/normalisation effects, S=b null not truly y-independent, evaluating df with random vs fixed omega).
3. Whether the gap statement (A) is honest about what is classical; flag any claim you know to be wrong or that I cannot have verified. Mark clearly what is from your own knowledge vs. something you verified now (you may use web tools; say what you actually retrieved).
4. Your single most likely failure mode of the whole project and the earliest cheap signal for STOP.
Do not write code. Do not suggest GPU work. Keep the answer under ~1200 words, plain prose + numbered lists. State your actual model identifier if you can see it.

Reading-level caveats for the literature: Tibshirani 2015, Ramani 2008, Image-GS, GaussianImage++, Jo 2021, Gao&Jojic 2016 were read only as tool-generated summaries; Ye 1998, Efron 2004, Friedman 1991, Janson 2015, DIP-SURE are NOT read. Feng&Kao 2602.09415 has an unresolved version/erratum question.

# A. G0 gap statement
# G0.3 缺口陈述 v0 (2026-11-05T08:12:46Z, Sonnet5.5) — DRAFT; 未经 Opus; 文献依据的阅读级别见 research/notes/G0_reading_log_20261105.md 与 PRIOR_RESEARCH_RECEIPT
结论先行: 这不是"空白领域"声明, 也不主张优先权。已被经典/邻近工作占据的部分必须作基线; 只有下面 G-a..G-d 可能是增量, 且很可能以"负结果/适用边界"收场。

## 1. 已被占据 (不可当创新)
| 论点 | 占据者 (阅读级别) | 含义 |
|---|---|---|
| 搜索/选择要付自由度: sdf = df - E|A| (best subset), 不连续 Stein 推广 | Tibshirani 2015 (摘要+部分), Ye 1998 GDF (未读) , Janson-Fithian-Hastie 2015 (未读) | "搜索风险存在"是已知方向, 需要的是 Gaussian 生长里的量级与估计 |
| 全流程扰动+重训估 df (公共随机数, 小 eps) | Gao&Jojic 2016 神经网络 (摘要级); Ye 1998 (未读); Ramani 2008 MC-SURE | "对整条管线扰动再拟合"已有先例, 不新 |
| 单图迭代拟合器的 df/SURE 早停 | Jo 2021 DIP (摘要级), DIP-SURE/eSURE (线索) | 单图停止准则已有; 其在非光滑区的失效(Fig3c)是 worker 的未核实说法 |
| 留出/盲点/验证选高斯数 | Luxar, VGNC, Noise2Self (摘要级) | 强基线(全局K/区域预算) |
| 残差驱动 2D 高斯 birth | Image-GS, GaussianImage++, LocoADC (摘要/节选级) | 基础系统; 均无风险感知准则(依据所读部分) |
| 随机化贪心改变 df | 2506.15643 (仅 worker 报告的摘要) | 随机化 birth 的理论线索, 未核实 |

## 2. 可能的增量 (须实验证伪)
- G-a (存在性): 在固定最终 K 与优化预算下, 自适应 2D 高斯 birth 的**搜索自由度** sdf = df_oracle - p_eff 是否显著 > 0, 且随搜索规模 S 单调增加 (S=n_birth 为无搜索零对照)。
- G-b (移植失效域): 理论 T3 指出全流程 MC 扰动在 eps 处期望等于噪声水平 sqrt(s^2+eps^2) 的 df, 方差随 birth 翻转 ~ 1/eps。问题: 在 Gaussian birth 管线上, 是否存在 eps 使 偏差<=容限 且 sd<=容限 且 成本可接受? 若存在 -> "直接移植已足够", 不声称新校正。
- G-c (更便宜/更稳的估计): 分解式估计 M1 (连续部分用冻结拓扑导数/GN迹; 跳变部分由候选分数 margin 近似) 是否在同等精度下用更少拟合次数。
- G-d (决策价值): 用 SURE/Cp 型准则 (含各 df 估计) 选 K/停止, 在等总墙钟 (含搜索与探针) 下是否比 固定K、残差birth、全局K留出/盲点、直接移植 MC-SURE 在参考评测器上有可重复的干净 MSE 收益。

## 3. 杀死/收缩条件 (先于实验写下; 数值阈值在 F0/F1 合同冻结)
- K1: G-a 失败 (sdf 在 MC 误差内且与 S 无关) -> 机制不成立, STOP, 保留负结果与适用边界说明。
- K2: G-b 的"移植足够"成立 -> 不声称新校正; 项目收缩为"移植评估+边界", 由 Opus 决定 revise 还是 stop。
- K3: G-a 成立、G-b 不足, 但 M1 无法在容限内逼近 oracle (G-c 失败) -> 仅保留"问题与基准"贡献, 无方法贡献。
- K4: G-d 失败 (等总墙钟无收益) -> 不进 GPU, 不写方法声明。
## 4. 对原创性的诚实判断 (预备)
低到中: 关键理论件(搜索 df、全流程扰动、SURE早停)均有先例。可能的价值 = 把它们在自适应 2D 高斯生长这一具体管线上量化, 并给出可靠性边界或廉价估计。最可能结果: 负结果/边界结果。不保证原创, 不保证分数。
## 5. 仍待读 (影响 K2 的判断)
Ye 1998 §GDF 的估计器与 eps 权衡、Efron 2004、Janson 2015、DIP-SURE/Soltanayev、Jo2021 Sec4.2/Fig3、Luxar/VGNC 细节、Feng/Kao 最新版本。这些未读前, "全流程扰动已知"一条按"有先例"处理 (保守)。

# B. Theory note (draft)
# G1.1 理论笔记 v0 (Sonnet5.5 自推导, 2026-11-05T08:02:43Z)  状态: DRAFT — 未经 Opus 审查, 未验证; 引用的文献事实多为工具摘要级(见 G0 日志), Ye1998/Efron2004 未读
符号: y=x+e, e~N(0,s^2 I_N), 管线 f_w(y) (w=初始化/采样的内部随机性, 含全部 birth/冻结/优化), 最终 K 与步数预算固定。df_s(f) := sum_i Cov(f_i(y), y_i)/s^2 (对 e 与 w 取协方差)。

## T1 风险恒等式 (协方差形, 无需光滑)
E||f-x||^2 = E||f-y||^2 + 2 s^2 df - N s^2 。 (展开 ||f-x||^2=||f-y||^2+2<f-y,e>+||e||^2, E<f,e>=s^2 df。) 对不连续/选择型管线同样成立; 难点只在 df 怎么估。

## T2 分解 df = p_eff + sdf (Tibshirani 2015 的类比, 其 best-subset 形式 sdf=df-E|A| 来自摘要级阅读)
p_eff := E[ 最终结构固定后局部线性化的有效维数 ], 取 Gauss-Newton 帽矩阵迹 tr(J (J^T J + lam I)^+ J^T) 或数值秩 (<= 每高斯参数数 x K, 重叠/近退化方向使其小于参数个数: 见 Opus v2 对可识别性的更正)。sdf := df - p_eff = "搜索自由度"。F0 的 H1 即: sdf 是否 > 容限, 且随搜索规模 S 增大。

## T3 全流程 MC 扰动估计的精确期望 (我的推导, 可能已有先例: 对照 Ye1998 GDF 与 Ramani 的 eps 讨论, 均待核对)
定义 div_hat(eps) = b^T [ f_w(y+eps b) - f_w(y) ] / eps, b~N(0,I), 同一 w (公共随机数)。
(a) 对任意可测 f(含跳变): E_b[ b^T f(y+eps b) ]/eps = div f_eps(y), f_eps := f * phi_eps (高斯平滑, 光滑)。 证: E[u g(y+u)] = eps^2 grad (g*phi_eps)(y), u=eps b。
(b) E_y E_b[div_hat] = sum_i Cov( f_i(y'), y_i ) / s^2, y'=y+eps b。 因 y,y' 联合高斯, E[y_i|y'] = x_i + s^2/(s^2+eps^2) (y'_i - x_i) 且残差与 y' 独立, 得
    **E[div_hat(eps)] = df_{s'}(f), s'^2 = s^2 + eps^2** (即: 同一管线在更高噪声水平 s' 下的 oracle df)。
结论: MC-SURE/GDF 型估计在期望上不需要任何光滑性, 偏差 = df_{s'} - df_s (依赖 df 随噪声水平变化多快); 难处在**方差**: 若管线在 O(1) 尺度上跳变(birth 选择翻转), 单探针 div_hat 方差 ~ c J^2 / eps (J=跳变幅度, c~翻转密度), eps->0 发散; eps 大则偏差大。 => H2 的可测形式: 在 eps 网格上画 (E[div_hat]-df_s) 与 sd[div_hat]; 若存在 eps 使两者都在 MC 容限内 且 成本(J+1 次完整拟合)可接受, 则"直接移植已足够", 不声称新校正。
内置自检: 同一批仿真可直接估 df_{s'} (协方差法, 在噪声水平 s' 重跑), 用来检验实现是否满足 T3(b) —— 这是 G2 评测器的单元/集成测试。

## T4 候选机制 M1 (待检验, 非结论): 分解式 df 估计
df ~ E[continuous part] + E[jump part]。 连续部分 = 冻结拓扑下的导数 (隐函数/GN 迹, 一次拟合, 无需再拟合); 跳变部分 = sum over birth 事件 [ P(候选选择翻转) x 翻转导致的输出变化与噪声的相关 ], 其中翻转概率可由"最佳/次佳候选分数的间隔 margin / 分数对噪声的灵敏度"解析近似 (Tibshirani 硬阈值的 2*lam*phi(lam) 项的类比)。 成本 ~ 1 次拟合 + 每次 birth 的候选分数统计, 低于 J+1 次拟合。 失败条件: (i) 连续部分与 MC 全流程差异不由 jump 项解释; (ii) margin 近似的 jump 项与协方差 oracle 的 sdf 偏差 > 容限; (iii) 在等总墙钟下决策无收益。
## T5 决策用途 (H3)
Cp/SURE 型准则: SURE(K, 策略) = RSS + 2 s^2 df_hat - N s^2。 比较 df_hat 来源: [参数个数]、[GN 秩]、[MC 全流程]、[M1 分解式]、以及不用 df 的 [留出/盲点 全局K]、[固定K]、[残差birth]。 评价指标: 参考评测器上的干净 MSE/PSNR, 总墙钟含搜索/探针, 独立噪声与优化 seed。
## T6 oracle df 的 MC 误差 (用于合同容限)
df_hat = (1/(M s^2)) sum_m <f^m - fbar, e^m> 。 粗估 sd(df_hat) ~ sqrt(df/M) (f 的波动主要为噪声驱动时)。 例: df~300, M=200 -> sd~1.2 (<1%)。 若 w 独立随机化: 估计的是随机化管线的 df; 固定 w 则是该 w 下的确定性管线 df — 合同须声明估计对象, 两者都报告。
## 未决 / 需核对
- Tibshirani 的不连续 Stein 引理在含优化器的管线上的适用性 (管线非"分段 a.c. 且可显式刻画")。
- T3 与 Ye1998 GDF 的关系(GDF 对均值 mu 求导, 以扰动 y 的回归斜率估计; 预期与 T3 同形) — 待 GLM 取得原文。
- top-K 归一化混合在 birth 处是否连续 (新高斯初始权重/颜色选择会改变连续性)。
- 随机化选择 (Image-GS 按误差比例采样) 是否使 f_w 对 y 弱可导。

# C. F0 contract draft
# F0 CPU 合同 DRAFT v0 (2026-11-05T08:13:37Z, Sonnet5.5) — 未冻结。冻结 = 真实 Opus5.5 ACCEPT + 记录 sha256; 此后任何改动须开 amendment 版本。
目的: 检验 G0_GAP_STATEMENT 的 G-a(搜索自由度存在且随搜索规模增加) 与 G-b(直接移植的全流程 MC 扰动估计是否足够)。F0 只回答"机制是否有余量", 输出 go / revise / stop; 不涉及 GPU、不涉及真实自然图像。
证据级别: 全部为 development (合成数据); 冻结后的 test 图像 T1-T3 只跑一次。

## 1 数据 (全部由种子生成, 代码即数据, 无外部文件)
- 图像: 64x64 灰度, 值域[0,1]。D1 平滑斑块+边缘; D2 多尺度随机高斯斑块纹理; D3 分段常数+细线。T1-T3 同生成器、不同生成种子, **冻结前不得运行/查看**。
- 噪声: 加性白高斯, sigma0=0.08, 不裁剪(裁剪破坏高斯假设); 拟合输入为 y=x+e (float64 生成, float32 拟合)。
- 噪声水平检查 (T3): sigma' 使 sigma'^2 = sigma0^2 + eps^2, eps ∈ {0.01,0.03,0.1,0.3,1.0}*sigma0。

## 2 被测管线 P(S) (唯一被改变的变量 = 搜索规模 S; 其余全部固定)
- 表示: K 个 2D 高斯, 参数 = 位置(2, 归一化坐标), log尺度(2), 旋转(1), 灰度值(1) = 6 个/个。渲染: 逐像素对全部高斯算权重 w_k=exp(-0.5 d^T Sigma^-1 d), 取 top-k=8 后归一化 sum_k w_k c_k / (sum_k w_k + 1e-8); 输出不裁剪。
- 流程: 随机初始化 K0=24 (位置均匀, 尺度 3px, 颜色 0.5 +- 0.05 随机, 与 y 无关); Adam(lr: 位置 5e-3, 尺度 2e-2, 旋转 2e-2, 值 5e-2) 全像素 MSE, 150 步; 然后 R=3 轮 birth, 每轮加 b=8 个、再 150 步; 每轮 birth 重建 Adam。最终 K=48, 总步数 600 (固定)。
- birth 候选: 均匀无放回抽取 S 个像素位置 (RNG 仅依赖 omega); 分数 = 高斯平滑(1.5px)残差 |y-f| 在候选处的值; 取 top-b。S=b=8 时选择与 y 无关 (零搜索对照); S 越大越贪心。新高斯: 位置=像素中心, 尺度 2px, 旋转 0, 值=该处平滑残差+当前渲染值。
- S 网格: {8, 16, 64, 256, 1024}。

## 3 估计对象 (均对独立噪声抽样 m=1..M 计算; M=256)
- df_oracle^rand(S) = (1/(M s^2)) sum_i sum_m (f_i^m - fbar_i) e_i^m, 每个 m 使用独立 omega (随机化管线)。df_oracle^fix(S): 所有 m 用同一 omega (固定种子管线)。SE 用对 m 的 bootstrap (B=1000)。
- p_eff(S) = mean_m tr( J (J^T J + lam I)^-1 J^T ), J=最终参数处渲染图对全部参数的雅可比, lam=1e-6*tr(J^TJ)/dim; 同时报告数值秩(相对阈值1e-6)。sdf = df_oracle - p_eff。
- MC 全流程扰动: div_hat(eps) = b^T [f_w(y+eps b) - f_w(y)]/eps, b~N(0,I), **同一 omega 与同一 y 抽样(公共随机数)**, eps 网格 {0.01,0.03,0.1,0.3,1.0}*sigma0, 探针数 J ∈ {1,2}; 取 fix 族的前 Mmc=64 个噪声抽样; 每个 (抽样, eps, 探针) 需 1 次完整重拟合 (基准拟合复用)。
- 参考评测器: 对每个输出 f 计算 ||f-x||^2 (clean 仅在此处使用)。

## 4 规模与算力上限
- 拟合次数估算: oracle 3图x5S x (256 rand + 256 fix) = 7680; MC 3x5x64x(5 eps x 2 J)=9600 (+基准复用); T3 噪声水平重模拟: 3图 x 2个S{8,256} x 5 sigma' x 256 = 7680; 合计约 25k 次拟合。单次拟合耗时在 smoke 中实测 (预期 1-3 s)。
- 宿主 20 线程: 18 个进程 x 1 个 torch 线程; **总墙钟上限 3 小时**, 超限即停并报告; 无 GPU。每个输出目录由单进程原子预留。

## 5 种子与边界
- SeedSequence(20261105) 分叉出互相独立的流: 噪声[image][m] (所有估计量共享同一噪声流以便对比时可配对; 噪声流与 omega 流独立), omega[image][S][m] (rand 族) / omega_fix[image][S] (fix 族), 探针 b[image][S][m][j]。全部种子写入输出元数据。
- 拟合器函数签名只接受 (y, omega, S, 超参); clean x 仅在 src/reference_eval.py, 由分析脚本导入; 测试用静态检查+运行期断言保证拟合模块不导入 reference_eval。
- 任何非有限值: 立即失败, 不裁剪、不静默替换; 计时覆盖全部阶段含落盘; 评测脚本在任何输出存在之前提交并记录 sha256。

## 6 预先登记的判定 (阈值待 Opus 审查; 冻结后不得改)
- H1 (G-a) 通过, 当且仅当对 3 张开发图中至少 2 张: (a) [sdf(S=1024) - sdf(S=8)] > 4*SE_diff 且 > 0.05*df_oracle(S=1024); (b) 零搜索对照 sdf(S=8)/df_oracle(S=8) <= 0.05; (c) sdf 随 S 的 Spearman >= 0.8。不通过 -> **STOP (K1)**。
- H2 (G-b), 仅当 H1 通过: "移植足够" 当且仅当 对 >=2 张图存在 eps* 使 |bias|/df_oracle^fix <= 0.05 且 单抽样 sd/df_oracle^fix <= 0.10 (J<=2, S=1024), 且 T3 恒等式检查通过 (E[div_hat(eps)] 与 df_{sigma'} 的差 < 2 SE)。成立 -> **K2: 不声称新校正, 提交 Opus 判 revise/stop**。不成立 -> 进入 M1 (分解式估计) 开发 (F1 另立合同)。
- 实现单元测试门 (任一不过则不得开跑 F0): (i) 硬阈值玩具: 协方差 df 与闭式一致, 且 E[div_hat(eps)] = df_{sigma'}; (ii) 渲染器解析梯度 vs 有限差分; (iii) 泄漏测试(拟合模块不导入 clean); (iv) 同 y+omega 逐位可复现 (单线程 CPU); (v) 线性模型上 GN 迹 = 秩。
## 7 报告
全部结果(含负结果)落 outputs/F0-*/, 开发与 test 分开; 记录输入/代码/环境哈希、种子、墙钟; 不跨级别混合。
## 8 给 Opus 的待决问题
(1) sd(df_hat)~sqrt(df/M) 与 M=256 是否足够; (2) S 作为"搜索规模"是否恰当, S=b 零对照是否严格无 y 依赖; (3) 64x64 灰度/K=48/top-k 渲染是否保真到足以代表 Image-GS 类 birth; (4) 阈值(0.05/0.10/4SE/Spearman0.8)是否合理, 有无遗漏的混淆(如优化未收敛造成的伪 df); (5) rand vs fix 两个估计对象的解释; (6) T3 恒等式推导是否正确 (research/notes/G1_theory.md T3); (7) 是否应加入 sigma 变化或 K 变化作为第二变量(F0 只允许一个变量); (8) 任何应当 STOP 的更早信号。
