# F0 CPU 合同 v3 (FROZEN, 2026-11-05, Sonnet5.5) — 逐条落实 Opus 门 round-4 (run 20261105T100558Z-opus-review-66bb, REVISE-v3; 全文 research/notes/OPUS_REVIEW_F0_pilot_20261105.md), 并逐字落实 round-5 一致性确认 (run 20261105T101239Z-opus-review-5c5a, FREEZE-AFTER-CHANGES C1-C4; 全文 research/notes/OPUS_REVIEW_F0_v3_20261105.md)
状态: **冻结**。候选稿 contracts/F0_CONTRACT_v3_CANDIDATE.md (sha256 6973930a...) 与本文件的差异仅为 C1-C4 与本头部/§9 的登记; 本文件 sha256 记于 contracts/F0_CONTRACT_v3.sha256。v2 (contracts/F0_CONTRACT.md, sha256 8c563f02...) 保持原样留档: v2 的 pilot p1 因 1800s 墙钟中止、p2 判 INVALID(R7), 二者都不是对假说的判决。v3 的唯一变化是**估计量** (弃有限差分, 改 fission+协方差) 与实验规模; 管线 P(S) (§2) 与 v2 相同。
**no-v4 条款 (Opus)**: 若 v3 失败 (INVALID 无法修复/INCONCLUSIVE/H1 不成立), 估计器这条线 **STOP**, 不再重新定义估计量; 项目只保留描述性结果 (oracle df 随 S 的变化、P-lin 正控制)。

## 0 范围声明
sigma0=0.08、K=48、64x64、加性高斯混合渲染是玩具; 结果不外推到 Image-GS 规模系统。v3 只回答 H1: 在 fission 噪声水平 sigma'=sqrt2*sigma0 下, 搜索 (S=1024 vs S=8) 是否带来超出"选择独立于数据的同法拟合"的额外 df (sdf)。H2 (无干净图估计 sdf, 与 MC-SURE/DIP-DF 比较) **推迟, 仅在 H1 成立后另立合同**。证据级别 = development (合成)。保留图 TE1-TE3 不得运行或查看。

## 1 数据与噪声 (fission)
64x64, [0,1], float64, 不裁剪。每个 (图, 抽样 m): e~N(0,sigma0^2 I) (流1), z~N(0,sigma0^2 I) (流12); y+ = x+e+z, y- = x+e-z; 噪声 e+ = e+z, e- = e-z 是**独立**的 N(0,2 sigma0^2 I) (sigma' = sqrt2*sigma0 = 0.11314)。所有拟合 (含两个副本) 用同一 omega^m (流2)。
图: **E1..E14** = 开发图, 类型循环 D1,D2,D3 (E_k 类型 = D[(k-1)%3+1]), 生成种子 3000+k (synth.make_clean(类型名, 3000+k)); D1-D3 (v2 用过) 与 TE1-TE3 不用。pilot 用 E1(D1型), E2(D2型); **Stage 1 只用 E3..E14 (12 张新图)**。P-lin 控制图: W0 (x=0), W1 (x=0.1*E1), E1。

## 2 管线 P(S) 与控制 (与 v2 §2 相同, 摘要)
加性高斯混合渲染, 每高斯 6 参数 (位置2、log尺度2、旋转1、值1), K0=24 随机初始化 + 3 轮 birth (b=8) 各 150 步 Adam, 共 600 步, 最终 K=48。birth 候选 = 每轮 omega 排列的前 S 个像素; 分数 = 高斯平滑(1.5px) |y-f| 在候选处的值取 top-b (稳定排序), 选中像素按索引升序加入; 新高斯 位置=像素中心, 尺度2px, 值=当前渲染+带符号平滑残差。**S ∈ {8,1024}** (v2 的中间 S 取消)。S=8=b 时选择与 y 无关。`fit_pipeline(y, omega, S, cfg, forced_idx=None)` 单一代码路径; forced_idx 给定 = 冻结选择管线 g_I。实现: 快速 numpy 解析梯度路径 (src/gsfast.py, src/gskernel.py; D-02, 已被 Opus 接受) 为主, torch 路径 (src/gsfit.py) 为参考。N0 取消 (fission 下 sdf 恒为 0, 仅留作单元测试)。
**P-lin** (线性化正控制, 同 v2): 1024 个各向同性高斯原子 (16x16 网格 x 尺度 {1.5,2.5,4,6}px), 前向逐步回归 3 轮取 24 原子; 给定 I 拟合 = 24 维子空间正交投影, df_frozen = 秩 = 24。

## 3 估计对象 (无导数)
对每个 (图, S, m): 
- 全管线: F+ = f(y+; omega), F- = f(y-; omega), 记录各轮 birth 索引 I+, I-。
- 冻结腿 (选择取自**独立副本**): G+ = g_{I-}(y+; omega), G- = g_{I+}(y-; omega) (forced_idx = 另一副本的 I; 值初始化仍用被拟合数据自己的当前渲染与残差)。
- 单元 = 抽样 m (两个副本合并为一个单元, 不当作两个独立样本)。
- **C1 (Opus, 逐字)**: "For df_full, sdf, df_par, df_cov (P3) and P-lin covariance df, replace mean_m[.]/(2 sigma'^2) by Sum_m[.]/((M-1)*2 sigma'^2) (unbiased sample covariance; e has known mean 0). Within each bootstrap resample, recompute Fbar/Dbar and apply the same formula. df_anti is unchanged (uncentered, divided by M)." 下面各式中的 mean_m[.]/(2 sigma'^2) 一律按此改读为 Sum_m[.]/((M-1)*2 sigma'^2)。
- **df_full(S)** = mean_m [ (F+ - Fbar+).e+ + (F- - Fbar-).e- ] / (2 sigma'^2) [按 C1: Sum_m/((M-1)*2 sigma'^2)] (Fbar = 该 (图,S) 对 m 的均值, 与 v2 同形式; 用已知干净图得 e±)。
- **sdf(S)** = mean_m [ (F+ - G+ - Dbar+).e+ + (F- - G- - Dbar-).e- ] / (2 sigma'^2) (D = F-G, Dbar 为对 m 的均值); **df_par(S) = df_full(S) - sdf(S)** (冻结腿的协方差 df)。SE = 对 m 的 bootstrap (B=1000, 重采样取自独立流 13: SeedSequence(entropy=20261106, spawn_key=(13,)); **C4**)。
- 次要 **df_anti(S)** (仅 pilot, 闸 P3): A = f(x - e+; omega), df_anti = mean_m <F+ - A, e+> / (2 sigma'^2)。
- S=8: 选择与 y 无关 => I+ = I- (**每个抽样断言索引逐元素相等**) => G± = F± 恒成立 => sdf(8) 恒为 0。pilot 对每个抽样仍实际跑 G± 并断言与 F± **逐位相等** (数值零检验); Stage 1 对前 8 个抽样/格做同样断言。
- **回放断言 (R1')**: 每个 (图,S) 格的前 4 个抽样, 断言 g_{I+}(y+; omega) 与 F+ 逐位相等 (forced 路径 = 自由路径)。
- P-lin 同型: f±=plin(y±), I± = 支持集, G+ = plin_frozen(y+, I-), G- = plin_frozen(y-, I+); P-lin 的所有 df/sdf 用同一公式。M=256 抽样, S ∈ {8,16,64,256,1024}。
- 参考评测器: 仅 src/reference_eval.py 与 runner 的 e± 协方差计算用干净图; 拟合器只接受 (y, omega, S/I, cfg), 不 import synth/reference_eval; 非有限值立即失败。

## 4 阶段与算力
- 宿主 **4 进程** (吞吐在 ~4 进程饱和); 总墙钟上限 4 小时 (pilot 上限 30 分钟); 无 GPU。
- **Stage 0 pilot (v3-pilot)**: E1, E2 x S∈{8,1024} x M=32 抽样; 每抽样拟合: S=1024: F+,F-,G+,G-,A (5); S=8: F+,F-,G+,G-,A (5); 回放 +1 x 前4个/格; 共约 700 次。P-lin: W0, W1, E1, M=256, 5 个 S。**torch 子集 (P4)**: E1, S=1024, M=32, 只做 F+,F- (64 次, torch 路径)。
- **Stage 1**: 图 E3..E14 (12), S=1024: F±,G± (4/抽样); S=8: F± (2/抽样); M 取 {32,64,128} 中使"外推每图 SE(sdf(1024)) <= 0.015 df_par"的**最小值** (外推 = pilot SE*sqrt(32/M); **只按精度定 M, 不按 pilot 效应量**); 约 12*M*6 次拟合 (M=32: 2304; M=64: 4608; M=128: 9216); 回放前4个/格; P-lin 同 pilot 图集, E3..E14 上加 P-lin 各一份。Stage 1 仅在 pilot 全过后启动。
- **P1 重跑 (C2)**: E1, E2 x 仅 S=1024 x M=128 x 仅 F+,F-,G+,G- (无 A、无 S=8、无 torch 子集、无 P-lin), 自有 60 分钟上限, 不计入 Stage 1 预算。
- **回退 (C2)**: P5 不过时 (a) 去掉 Stage 1 的 S=8 拟合; (b) 仍超 3.5 h 则 Stage 1 只用 E3..E10 且 H1 符号规则 >=6/8 图; (c) 仍超 => INCONCLUSIVE, STOP。
- 墙钟外推 = (Stage 1 拟合数) / (pilot 实测拟合速率; pilot 墙钟 < 600 s 时速率打 80% 折扣); 必须 <= 3.5 h。

## 5 种子
SeedSequence(entropy=**20261106**) 分叉互相独立流 (spawn_key 首元素为流号): 1 噪声e[图,m]; 2 omega[图,m, 0=init/1+r=第r轮排列]; 12 噪声z[图,m]; 10 P-lin omega[图,m]; **13 bootstrap 重采样 (C4)**。图索引: E_k -> 100+k, W0 -> 90, W1 -> 91。**流 1,2,12 与 S 无关**。v2 的流 3-9,11 在 v3 不使用 (D-01 流6问题随 FD/MC 一并消失)。确定性: 单线程下同输入逐位可复现。评测/分析脚本先于任何输出提交并记录 sha256。

## 6 预先登记判定
**有效性门 (pilot 与 Stage 1 均适用; 任一不过 => INVALID, 非阴性)**:
- V1 单元测试 (含: fission 两副本噪声独立且方差 2 sigma0^2; 线性平滑器 H 上协方差 df = tr H; S=8 时 I+=I-; forced 回放逐位; P-lin 冻结 df=秩; 渲染器梯度 vs torch autograd; 泄漏静态检查含负控制; **C4**: 断言 v3 使用的任何 SeedSequence (流号, 图索引) 键都不在 v2 的键集合中, bootstrap 取自独立流 13)。
- V2 确定性 + 回放断言 R1' + S=8 的 I+=I- 与 G=F 断言。
- **P1 精度**: pilot 上每图 SE(sdf(1024)) <= 0.015 df_par(1024) 或按 §4 外推在 M<=128 内达到; 否则 pilot 重跑一次 (M=128), 仍不达 => INCONCLUSIVE, no-v4 条款 (STOP 估计器线)。
- **P2 P-lin 控制 (fission)**: (a) 冻结腿 df_par 在 W0 与 E1 上与 24 相差 <= 2 SE; (b) W0 上 sdf(1024)-sdf(8) 与 65.6 相差 <= 3*sqrt(SE^2+0.83^2) (65.6±0.83 为 v2 pilot 探索性读数, 作为 P-lin 无尺度搜索 df 的参照, 解释 I6)。
- **P3 估计器一致**: 全管线腿的 df_cov (F+ 的随机协方差) 与 df_anti 在两个 S 上配对差 <= 2 SE。
- **P4 快慢路径分布等价 (D-02 条件)**: E1, S=1024, M=32: df_full(fast) 与 df_full(torch) 的逐抽样配对差均值 <= 2.5 SE (SE=配对差 sd/sqrt(32))。**只验分布, 不要求逐位**。
- **P5 墙钟**: 外推 Stage 1 <= 3.5 h。
**H1 (Stage 1, 12 图)**: 仅在 V1,V2,P1-P5 全过时判。pooled = 各图 sdf(1024) 的无权均值 (sdf(8)≡0); SE_pooled = 图间标准误 (sd_img/sqrt(12), 随机效应, 解释 I5); 阈值 df_par* = 各图 df_par(1024) 的均值。**H1 成立当且仅当** pooled >= max(3*SE_pooled, 0.05*df_par*) **且** (**C3**) "The H1 sign rule is >=9 of 12 images with sdf(1024) point estimate > 0." (回退 C2(b) 的 8 图版本: >=6 of 8)。否 => **STOP (K1-v3): 估计器线停止, 不再改估计量**。H1 成立 => 记"development 证据: 玩具中搜索带来 sdf>0", 另立 H2 合同, 提交 Opus 判 go/revise/stop; 不上 GPU (GPU 门条件不变)。
同时报告 (不入判定): 各图 sdf(1024)/df_par、图型 (D1/D2/D3 型) 分层、df_anti。

## 7 Pilot 决策规则 (含 Opus C2, 逐字)
**C2 (Opus, 逐字)**: "Decision order: validity gates (V1, V2, P2, P3, P4) -> P1 (fixes M) -> P5 evaluated at that M. A P5 failure, including a pilot wall-cap abort, is not INVALID and is handled only by this pre-registered fallback: (a) drop the Stage-1 S=8 fits; (b) if still over 3.5 h, restrict Stage 1 to E3..E10 with the H1 sign rule >=6 of 8 images; (c) if still over 3.5 h, INCONCLUSIVE -> STOP. No other redesign is allowed. The P1 rerun at M=128 runs E1, E2 at S=1024 with F+-, G+- only, under its own 60-minute cap, outside the Stage-1 budget. An INVALID in that rerun counts as the second INVALID -> STOP."
1. 先判有效性门 V1, V2, P2, P3, P4 (任一不过 => INVALID: 只允许修实现缺陷后**重跑一次**, 估计量与阈值不变; 第二次仍 INVALID => STOP 估计器线)。
2. 再判 P1 (定 M; 不过 => 按 §6 P1: 以 C2 规定的 M=128 重跑[E1,E2, 仅 S=1024, 仅 F±,G±, 自有 60 分钟上限, 不计入 Stage 1 预算]; 重跑中的 INVALID 计作第二次 INVALID => STOP; 仍精度不足 => INCONCLUSIVE, STOP)。
3. 最后在 P1 选定的 M 上评 P5。P5 不过 (含 pilot 触墙钟上限) **不是 INVALID**, 只走 C2 的预登记回退 (a)->(b)->(c), 不得有其他重设计。
4. 全过 => 按 §4 定 Stage 1 的 M 并 PROCEED。**pilot 数据不得并入 Stage 1 的任何统计**; pilot 的 sdf 点估计只作"预期量级"记录, 不参与 M 的选择。

## 8 报告
全部结果 (含 INVALID/阴性) 落 outputs/F3-*/ (v3 运行用 F3 前缀), 记录输入/代码/环境哈希、种子、墙钟; 开发/保留分开; 不删 run; 事后探索性分析须明示"非预注册"。v2 的 pilot (p1/p2) 与事后诊断 (outputs/DIAG_R7_response_p2*.json) 按 Opus 标签引用: p2 的 P-lin 与 V7 读数 = [pre-registered validity, passed]; oracle df 对比 = [pilot, exploratory]; 响应噪声底表与 full-minus-frozen = [post-hoc]。V6 在 v2 中仅因 SE 巨大而过, 不得引为通过。

## 9 追溯与解释登记 (供 Opus 一致性确认)
| Opus round-4 | 落实 |
|---|---|
| fission tau=1, y±=y±z, 全/冻结腿 + 协方差 df, 无 FD | §1, §3 |
| 闸1 S=8 null + SE<=0.015 df | §3 (S=8 恒等断言), §6 P1 (精度) |
| 闸2 P-lin fission: 冻结=24, W0 ~65 | §6 P2 |
| 闸3 反对称与随机协方差一致 | §6 P3 |
| 闸4 快/torch df 2.5 SE | §6 P4 |
| 闸5 墙钟 <=3.5h | §4, §6 P5 |
| H1: >=max(3SE,0.05 df_frozen) 且 >=75% 图为正; 否则 STOP, 无 v4 | §6 H1, 开头 no-v4 |
| Stage 1 新图/新种子; S∈{8,1024}; >=8 图; M>=32; 4 进程; 砍 FD/eps/N0/V3/MC | §1, §4, §5 |
| H2 推迟 | §0 |
| D-01 接受并随 FD/MC 取消; D-02 接受+分布等价 | §5, P4 |
| pilot 2图x{8,1024}xM16x4 拟合 + P-lin + torch 子集 | §4 (我扩为 M=32、每抽样 5 拟合、含 A 与 S=8 的 G, 见 I3, I7) |
解释登记 (Sonnet 的选择; 请 OK/CHANGE):
- I1 噪声水平 sigma'=sqrt2*sigma0 直接用于所有拟合, 超参不变。
- I2 "S=8 null" 实现为**恒等断言** (索引相等 + G=F 逐位), 不是统计检验; "SE<=0.015 df" 的精度要求放在 S=1024 的 sdf 上 (P1)。
- I3 回放断言 R1' 每格前4个抽样 (非每个 m); S=8 的 I+=I- 对每个抽样断言。pilot 每抽样 5 拟合 (多了 A 与 S=8 的 G)。
- I4 单元=抽样 (副本对合并), 比 Opus 的"每腿 64 样本"保守。
- I5 H1 汇总: 各图 sdf(1024) 无权均值, 图间标准误, 符号比例看点估计; 阈值用 df_par* 均值。
- I6 P2(b) 的 65.6±0.83 来自 v2 pilot 的探索性读数。
- I7 P3 的反对称用 A=f(x-e+; omega) (同 omega), 仅 pilot。
- I8 P4 用 E1, S=1024, M=32, 仅 F+,F-, 配对差 sd 定 SE (配对仅为降方差, 不影响有效性)。
- I9 墙钟速率 pilot<600s 打 80% 折扣。
- I10 Stage 1 的 M 只由精度外推定 (30/64/128), 不看效应量。
- I11 图 E1..E14 用 D 类型生成器 + 种子 3001..3014, entropy 20261106; pilot=E1,E2, Stage 1=E3..E14。
- I12 INVALID 允许修实现后重跑一次; P1 不过允许 M=128 重跑一次; 仍不过 => STOP 估计器线。
round-5 追溯: C1 -> §3 (M-1 无偏协方差; bootstrap 内重算 Fbar/Dbar; df_anti 不变); C2 -> §4, §7; C3 -> §6 H1; C4 -> §5, §6 V1。Opus 推荐项 (非必需): P4 额外报告 |mean|/df_full(fast) (仅报告, 不入闸; 解释 I13)。
- I13 P4 附加量 |mean diff|/df_full(fast) 只记录; P1 重跑不含回放断言 (沿用 pilot 已验的同一代码路径; 解释 I14), 其余 V2 恒等断言照旧适用于其数据。
修订机制: 任何阈值/判据/估计量改动 = 须再审的合同修订; 实现缺陷修复须登记 (DECISIONS) 且不得改变 §3/§6。
