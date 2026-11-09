# G1.1 理论笔记 v0 (Sonnet5.5 自推导, 2026-11-05T08:02:43Z)  状态: DRAFT — 未经 Opus 审查, 未验证; 引用的文献事实多为工具摘要级(见 G0 日志), Ye1998/Efron2004 未读
符号: y=x+e, e~N(0,s^2 I_N), 管线 f_w(y) (w=初始化/采样的内部随机性, 含全部 birth/冻结/优化), 最终 K 与步数预算固定。df_s(f) := sum_i Cov(f_i(y), y_i)/s^2 (对 e 与 w 取协方差)。

## T1 风险恒等式 (协方差形, 无需光滑)
E||f-x||^2 = E||f-y||^2 + 2 s^2 df - N s^2 。 (展开 ||f-x||^2=||f-y||^2+2<f-y,e>+||e||^2, E<f,e>=s^2 df。) 对不连续/选择型管线同样成立; 难点只在 df 怎么估。

## T2 分解 df = p_eff + sdf [**SUPERSEDED 2026-11-05 by v1-revisions block below + contracts F0_CONTRACT v2: 主量不再是 GN 迹 p_eff, 而是 df_frozen (冻结选择回放的连续散度); GN 迹仅为次要诊断; 本段保留作历史**] (Tibshirani 2015 的类比, 其 best-subset 形式 sdf=df-E|A| 来自摘要级阅读)
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

## v1 修订 (Opus 门, 08:17Z)
- **T2 修订**: p_eff = GN 迹 对本管线是错量 (固定 600 步 Adam 不收敛; 早停轨迹的 df 可偏离 GN 迹)。**主估计对象改为 df_frozen**: 对每个噪声抽样 m, 记下在 y^m 下选出的 birth 索引 I^m, 构造"冻结选择管线" g_{I^m}(.) (birth 位置固定为 I^m, 其余流程不变; 新高斯的初值对 y 仍连续依赖); df_frozen := E_y E_b[ b^T (g_I(y+eps b) - g_I(y)) / eps ] (eps 小, 因已去掉跳变); 搜索自由度 sdf := df_oracle - df_frozen (类比 Tibshirani 的 df - E|A|; 即"跳变/选择项"的总和)。GN 迹与数值秩仅作次要诊断。
- **T3 状态**: 结果正确, 但**已发表**: Oliveira-Lei-Tibshirani (coupled bootstrap, arXiv 2111.09447) 对任意估计器无偏, 目标为噪声方差被抬高的问题; Breiman 1992 little bootstrap、Ye 1998 GDF 为近亲 (后两者未读)。T3 须补全: E[u|y'] = eps^2/(s^2+eps^2)(y'-x) => E[b^T f(y')]/eps = sum Cov(f_i(y'),y'_i)/(s^2+eps^2) = df_{s'}; 前置条件 (i) omega 与 (e,b) 独立且两次拟合用同一 omega; (ii) f 不以 s 为输入 (否则得到 s-调参管线在 s' 处的 df); 只在对 y 取期望后成立 (单图上 E_b[div_hat|y] = div(f*phi_eps)(y), 不是 df); 基线项 E_b[b^T f(y)]=0 是控制变量; omega 每样本重抽(两次拟合共用)时期望为 df^rand_{s'} = E_omega[df^fix_{s'}(omega)]; 方差启发式 ~J^2/eps 加上连续部分与 eps 无关的 ~2||grad f||_F^2 项。
- **T6 修订**: rand 族的 SE 被 omega 引起的 f 波动放大约 sum_i Var_omega(f_i)/(M s^2); 用 bootstrap SE + 功效 pilot, 不用 sqrt(df/M)。
- **失败机制 (Opus)**: 候选分数来自 1.5px 平滑残差, 翻转只移动新高斯 ~1px, 后续 150 步 Adam 会重新优化位置, 连续优化吸收离散选择 => sdf 可能可忽略 (K1)。N0(无 birth) 对照检测"优化器轨迹敏感性"。
- **渲染器**: 去掉 top-k 与 sum w + 1e-8 归一化 (它们引入与搜索无关的跳变/病态); 改为对全部 K 个高斯的**加性**混合 f = sum_k val_k w_k (K=48, 64x64 很便宜)。须在范围声明里承认: 这与 Image-GS 的归一化 top-k 渲染不同, F0 结论不外推。
