# G0 近邻核对记录 — JR 路线（观测混淆分组 + 组内有限幅度联合 Gaussian 几何修复）
run: 20261108T213141Z-experiment-7986 · 2026-11-08 · 作者 Sonnet 5.5（主研）· 未使用 GLM scout（host pump 停用，不启动）

## 0. 阅读深度声明（只记真实读到的层级）
| 来源 | 层级 | 备注 |
|---|---|---|
| Boink et al. 数据一致性（fiber projection）非线性重建网络 | WebFetch HTML 全文摘要，章节级 | 未逐行核对证明；只用于确认“无耦合分组” |
| AIR（Gaussian 残差驱动预测，Adaptive/Iterative Residual 类） | WebFetch 摘要，章节级 | 不含 PSF，无分组 |
| Ceres Solver 预条件器（cluster Jacobi / visibility-based） | 仅头文件注释/文档级 | 聚类依据：相机-点共视图，非观测混淆 |
| Kushal & Agarwal（visibility-based BA 预条件） | 摘要级 | 同上 |
| Nutini et al. 贪心块坐标下降 | 仅摘要 | 选块规则：梯度/Lipschitz 分数，不是联合几何响应 |
| 3DGS-LM（Levenberg–Marquardt 训练 3DGS） | 旧 G0（C76–C78）已读 | 全局稀疏 LM，不分块，不含已知 PSF 模糊 |
| Stetson 1987, DAOPHOT: A Computer Program for Crowded-Field Stellar Photometry (PASP 99, 191) | WebFetch 全文前 100k 字符，读到 §III.D（分组判据）；公式/实现细节未读 | NSTAR：按临界间距（剖面半径+拟合半径）把相互重叠的星分组，组内联合迭代线性化最小二乘；孤立星单独拟合。最近经典对照（R8） |
| Babcock, Sigal, Zhuang 2012, 3D-DAOSTORM (Optical Nanoscopy 1, 6) | WebFetch 摘要/引言级；方法节仅扫读 | 引言称对相邻发射体分组并同时拟合；方法节实现为逐发射体迭代，非联合解（工具摘要如此转述，未逐行核实）。ThunderSTORM 多发射体拟合：仅按 Opus 提示列名，未读 |
| 加性/重叠 Schwarz 区域分解（Toselli–Widlund 类） | 仅按 Opus 提示列名，未读 | 经典块分解；子域按空间重叠 |
| Nutini, Laradji, Schmidt, Let's Make Block Coordinate Descent Converge Faster (arXiv 1712.08859 / JMLR 2022) | WebFetch 摘要级 | 贪心块选择规则、message passing 块更新；摘要未指明按 Hessian 图划分（工具转述，未核实正文） |
| DPIR / Deep Wiener / DeblurGS / BAGS | 线索，未重读 | 作为 stage-2 强基线名单，非机制近邻 |
| 仓库内 GEO BLK/BJ（geo_core._iter_blk） | 代码级 | JR 的 |g|=1 退化即 BLK（单元测试要验证） |

## 1. 近邻矩阵（机制四要素：分组依据 / 组内更新 / 已知 PSF / 固定 K 几何）
| 近邻 | 分组依据 | 组内更新 | 用到已知模糊 | 参数化 |
|---|---|---|---|---|
| 经典块 Gauss–Seidel / 块 Jacobi / Schwarz | 空间子域或变量块（按坐标/邻接） | 子问题近似解 | 无关 | 通用 |
| Ceres cluster-Jacobi、Kushal–Agarwal | 共视图（结构性稀疏图） | 预条件 | 否 | BA |
| Nutini 贪心 BCD | 梯度/步长分数 | 单块 | 否 | 通用 |
| 3DGS-LM | 无分块（全局稀疏 PCG） | 联合 LM | 否 | 3DGS |
| Boink 等 | 无 | 神经网络 + 数据一致性投影 | 前向算子 | 像素/参数 |
| AIR | 无 | 残差驱动网络预测 | 否 | Gaussian |
| DAOPHOT/NSTAR、3D-DAOSTORM | PSF 剖面/支撑重叠（间距准则） | 组内联合线性化最小二乘（DAOSTORM 方法节为逐发射体迭代） | 是（PSF 剖面） | 点源位置+亮度 |
| 加性/重叠 Schwarz | 空间子域重叠 | 子问题解 | 无关 | 通用 |
| 本 JR | **当前离散化白化模糊响应的耦合（脊=相对 10% 标定扰动的噪声尺度）** | 组内有限幅联合 GN + 全前向验收 | 是（精确稀疏 A） | 固定 K 的 2D Gaussian |

## 2. 区分实验（本线必须自己证明，不靠新颖性断言）
1. OBS vs SPA：同耦合预算下，观测混淆分组 vs 几何邻近分组（空间邻居）。
1b. **OBS vs OVL-J**（R3，最关键）：白化响应+噪声尺度脊 vs DAOPHOT 式 PSF 支撑重叠面积；不优于 OVL 则 (a) 无增量。
2. OBS vs OBS0：同样的耦合构造但去掉模糊 → 区分“blur-aware”与一般 Jacobian 耦合。
3. OBS 联合 vs OBS 独立+线性投影：区分“组内联合有限更新”与“独立步 + 线性组合”。
4. RND、IND1(|g|=1)、FULL(全联合 LM) 作参照。
5. 跨 PSF 的组变化（ARI）与补偿比 ‖AJ_gδ‖/Σ‖AJ_iδ_i‖ 作机制诊断（不计入主指标）。

## 3. 诚实的新颖性状态
- 优化角度：“按耦合分组做块更新”在数值优化中属经典/近经典；**本线不声称该机制本身新**。
- 可能新的部分只有：(a) 以已知 PSF 的白化响应（脊=相对 10% 标定扰动的噪声尺度）区分弱可辨识与严格零空间并据此分组 —— 其最近经典对照是 DAOPHOT/NSTAR 的 PSF 重叠分组同时拟合，由 OVL-J 臂检验；(b) 学习式联合提案 + 跨未见模糊核泛化 — CPU 阶段**无法**检验 (b)。
- 因此 CPU 阶段只判“机制是否有净增量”；没有净增量 → 记失败并停止，不进入网络阶段。
- 未保证原创或分数。

## 4. 更新记录
2026-11-08 R8（Opus 审 v0）：补入 Stetson 1987、3D-DAOSTORM/ThunderSTORM、Schwarz、Nutini 近邻；新增 OVL-J 区分实验；阅读深度如上（均不超过摘要/节级）。
