# F0 CPU 合同 DRAFT v1 (2026-11-05T08:18:54Z, Sonnet5.5) — 按 Opus 门审查(REVISE, 13 条)修订; **未冻结**。冻结 = 真实 Opus 对 v1 回 ACCEPT + 记录 sha256。v0: contracts/F0_CONTRACT_DRAFT.md (保留作历史)。
## 0 范围声明 (先于实验)
sigma0=0.08、K=48、64x64 灰度、加性高斯混合渲染是**玩具**: F0 的任何阴性或阳性结果都不外推到 Image-GS 规模系统 (其为归一化 top-k 渲染且按误差比例随机抽样, 选择机制不同)。F0 只判断"在最干净的情形下, 搜索自由度是否存在且移植的 MC 估计是否足够"。证据级别: development (合成)。F0 闸门只用开发图 D1-D3; 保留图 TE1-TE3 (同生成器, 不同生成种子) 冻结前不得运行或查看。
## 1 数据与噪声
同 v0: 64x64, [0,1], 加性白高斯 sigma0=0.08 不裁剪, float64 拟合。D1 平滑斑块+边缘, D2 多尺度纹理, D3 分段常数+细线。T3 验证用噪声水平 sigma' (sigma'^2 = sigma0^2 + eps^2, eps ∈ {0.01,0.03,0.1,0.3,1.0}*sigma0; 注意 eps=sigma0 时 sigma'=sqrt2*sigma0, 偏差按构造较大)。
## 2 管线 P(S) (唯一变量 S) 与控制
- 渲染: 对全部 K 个高斯加性混合 f(p) = sum_k val_k * exp(-0.5 d^T Sigma^-1 d) (无 top-k、无归一化)。参数: 位置2、log尺度2、旋转1、值1。float64。
- P(S): K0=24 随机初始化 (与 y 无关), Adam(lr 位置5e-3 尺度2e-2 旋转2e-2 值5e-2) 150 步; 3 轮 birth (b=8/轮) 每轮 150 步; 最终 K=48, 600 步。候选: 均匀无放回抽 S 个像素, 分数 = 高斯平滑(1.5px)残差 |y-f| 在候选处的值, 取 top-b (稳定排序); 新高斯 位置=像素中心, 尺度 2px, 值=当前渲染+该处平滑残差; 重建 Adam。S ∈ {8,16,64,256,1024}; S=b=8 为选择与 y 无关的零搜索对照。
- 冻结选择管线 g_I: 与 P(S) 相同, 但各轮 birth 位置取外部给定的索引集 I (不再依据数据选择)。
- 控制 N0: 无 birth, K=48 随机初始化, 600 步 (度量优化器轨迹敏感性)。
- 控制 P-lin (线性化正控制): 固定候选字典 (位置 16x16 网格 x 尺度{2,4}px, 共 512 个固定高斯形状), 前向逐步回归: 每轮从 S 个随机字典原子中按 |与残差的相关| 取 top-b, 对全部已选原子用最小二乘重拟合振幅; 3 轮, 最终 24 个原子。该控制的 df_frozen = 选中原子数(秩), sdf>0 已知。
## 3 估计对象
- **df_oracle^rand(S)** (主): M 个独立噪声抽样, 每个用独立 omega; (1/(M s^2)) sum_i sum_m (f_i^m - fbar_i) e_i^m; bootstrap SE (B=1000, 对 m)。
- **df_frozen(S)**: 对每个 m, 记录 I^m, 用公共 omega 与同一 b: (1/M) sum_m b^T (g_{I^m}(y^m + eps_f b) - g_{I^m}(y^m))/eps_f, eps_f=0.01*sigma0。sdf = df_oracle^rand - df_frozen (配对 bootstrap SE)。
- df_oracle^fix: >=4 个固定 omega 值各自估计 (每个 128 个噪声抽样), 报告 omega 间的散布; MC 比较只与同 omega 的 df^fix 配对。
- 次要诊断: GN 迹与数值秩 (damping 1e-6), birth 位置稳定性 (跨噪声重抽, 匹配 birth 的优化后位移)。
- 移植 MC (G-b): div_hat(eps) = b^T [f_w(y+eps b) - f_w(y)]/eps, **omega 每样本重抽、f(y) 与 f(y+eps b) 共用同一 omega**, eps 网格 {0.01,0.03,0.1,0.3,1.0}*sigma0; 单探针 sd 定义为 div_hat 在 (y,b) 上的标准差; "J=2" 指同一抽样用 2 个独立 b 取平均 (成本 = 2 次额外拟合)。取 Mmc=64 个噪声抽样。
- 参考评测器: 仅在 src/reference_eval.py 用 clean。
## 4 阶段与算力
- **Stage 0 pilot (~200-400 次拟合, 开发数据 D1)**: S∈{8,1024}, 真实管线与 P-lin 各 32 个配对噪声抽样 (+N0 32 个)。目的: 早停信号与功效。STOP 规则: (i) P-lin 的 sdf(1024)-sdf(8) <= 4 SE (功效不足) -> F0 INVALID/重设计, 不算阴性; (ii) P-lin 显示 sdf 随 S 升高 但真实管线的配对 delta-df < 0.02*df 且 birth 位移 <~1px -> **STOP (K1)**; (iii) N0 的 div_hat sd > 0.10*df -> 移植 MC 因非搜索原因不可行, 记录并继续 H1。通过才进入 Stage 1。
- **Stage 1 完整 F0**: 3图 x 5S x 256 (rand) ; fix 族 4 omega x 3图 x 5S x 128; df_frozen 每 m 一次额外拟合; MC 3图 x 5S x 64 x (5 eps x J=2); T3 验证 3图 x S{8,256} x 5 sigma' x 256 重模拟; N0 与 P-lin 每图 256; 收敛检查 D1, S∈{8,1024}, 步数 x2 重做 oracle。总计约 35k 次 float64 拟合 (单次耗时 pilot 实测)。
- 宿主 18 进程 x 1 torch 线程; **总墙钟上限 4 小时**; 无 GPU; 超限即停报告。输出目录原子预留; 计时覆盖全部阶段含落盘。
## 5 种子与边界
SeedSequence(20261105) 分叉互相独立的流: 噪声[image][m] (所有估计量共用同一噪声流, 与 omega 流独立)、omega[...]、探针 b[...]。拟合器只接受 (y, omega, S/I, 超参), clean 只在 reference_eval; 测试 = 静态检查+运行期断言。任何非有限值立即失败, 不裁剪/不 nan_to_num。**确定性**: 单线程 CPU 下 f(y) 重复运行逐位相同, 且在最小 eps 处 f(y+eps b) 重复逐位相同 (否则舍入噪声会冒充散度); 评测脚本先于任何输出提交并记录 sha256。
## 6 预先登记判定 (阈值待 Opus 再审)
有效性门 (任一不过 => run INVALID, 不是阴性): V1 单元测试 (硬阈值玩具: 协方差 df 与数值积分一致且 E[div_hat(eps)] = df_{sigma'}; 渲染器梯度 vs 有限差分; 泄漏静态检查; 逐位可复现; 线性模型 GN 迹=秩); V2 确定性断言; V3 P-lin 在全规模下 sdf(1024)-sdf(8) > 4 SE; V4 T3 恒等式检查: 与 df_{sigma'} 的差 |diff| <= 0.02*df 且 SE <= 0.01*df, 且 sigma' 重模拟使用与散度相同的 omega 体制; V5 收敛检查: D1 上 S∈{8,1024}, 2x 步数的 df_oracle 与 1x 相差 <=5%, 否则"df 受优化预算主导, H1 不可解读"(交 Opus)。
- **H1 (G-a)**: 对 3 张开发图中至少 2 张: (a) sdf(S=1024) - sdf(S=8) > 4*SE_diff 且 > 0.05*df_oracle(S=1024); (b) |sdf(S=8)| <= max(3 SE, 0.03*df); (c) sdf 对 log2 S 的 bootstrap 斜率的单侧 95% CI 下界 > 0。否 -> **STOP (K1)**。
- **H2 (G-b)**, 仅当 H1 通过: "移植足够" 当且仅当 对 >=2 张图存在 eps* 使 |E[div_hat(eps*)] - df_oracle^rand| / df <= 0.05 且 单探针 sd / df <= 0.10 (J<=2, S=1024) 且 成本 <= 3 次拟合/抽样。成立 -> **K2: 不声称新校正, 提交 Opus 判 revise/stop** (T3 已是已知结果, K2 比预期更可能)。不成立 -> 立 F1 合同 (分解式估计 M1)。同时报告偏差随 eps 的整条曲线 (含 eps=sigma0) 与对 df_{sigma'} 的偏差。
## 7 报告
全部结果(含负结果)落 outputs/F0-*/, 开发/保留分开, 记录输入/代码/环境哈希、种子、墙钟; 不跨级别混合; 保留图只在冻结后运行一次。
## 8 仍待 Opus 回答
(1) v1 的 df_frozen 定义与 Tibshirani 的 df - E|A| 是否严格对应; (2) 阈值 0.05/0.03/0.02/0.10 与 4SE 是否合理; (3) P-lin 是否严格线性且 sdf 已知; (4) pilot 的 STOP 规则是否过严/过松; (5) 是否还有会让 H1 因非搜索原因通过的混淆 (例如加性渲染 + 值初始化对残差的连续依赖)。
