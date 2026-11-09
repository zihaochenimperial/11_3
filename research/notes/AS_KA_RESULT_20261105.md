# AS-3 前置: K-a 无合同小尺度决策一致性自检 (2026-11-06T00:01Z 前后; 非实验、非证据、非冻结代码)

run: 20261105T230727Z-session-74ee (主会话); 触发: Opus 门 (run 20261105T233836Z-opus-review-b1b8) 的 K-a / 交接文 step 4。
代码: research/checks/as_ka_decision_agreement_20261105.py (sha256 5bce6d74...), 变体 v2 (rule-neutral 实现值) research/checks/as_ka_decision_agreement_v2_20261105.py (sha256 27e9da1a...), 汇总 research/checks/as_ka_aggregate2_20261105.py (sha256 16a5ba67...)。
输出: research/checks/ka_out/ (v1 实现值, 270 个场景, 30 种子/格), research/checks/ka_out2/ (v2 中性实现值, 108 个场景, 12 种子/格); 汇总 stdout 存 KA_AGG2_*_stdout.txt。

## 设置 (小尺度, 单步贪心)
- 32x32, 已知高斯模糊 σ_b ∈ {0.3, 1.5, 3.0}, 噪声 0.02; 真值 5 个各向异性重叠 Gaussian (环间距 4/7/10); 当前模型 K0=3 并 LM 回拟到近平稳 (|J'r|/(σmax|r|) 中位数 1e-9..1e-4)。
- 候选 78 个: 6 个保质量保矩对称分裂 (3 父 × α∈{0.5,0.8}) + 72 个出生 (σ∈{1.5,3.0}, 6×6 网格)。
- 实现值 (realised) = 插入候选后全参数 LM 回拟 (v1: 10 步; v2: 14 步, 出生取 raw-OMP 与 OLS 两种振幅初始化中较好者, 使其与规则无关) 的 ½(|r|²-|r_new|²)。
- 规则: raw_free / joint_free (v1 自由系数), raw_c1 / block_c1 / joint_c1 (Opus 要求的可执行分裂 c=1 补偿增益; 出生用 OLS 自由振幅)。
- 指标: 相对遗憾 = (最佳实现值 - 所选实现值)/(½|r|²); top-1 一致率; Spearman(得分, 实现值)。仅描述性, 场景间非独立图像, 不作推断。

## 结果 (描述性; 小玩具, 单步, 3 个当前 Gaussian)
1. 决策确有分歧: raw_c1 与 joint_c1 top-1 一致率 0.03–0.30 (v1 集), 故 Opus 的 K-a 一致率>=90% 杀死条件 **未触发**。
2. 但分歧不转化为更好的实现值: v2 中性实现值下 (n=108) 合并相对遗憾 raw_c1=0.046, joint_c1=0.043, block_c1=0.071, raw_free=0.054, joint_free=0.038; joint_c1-raw_c1 = -0.004 (p~0.66, sd 0.086)。v1 集 (n=270) 曾出现 joint_c1 比 raw 差 (+0.024), **与**实现值初始化偏向 raw-OMP 的混淆**一致** (出生用 raw 振幅初始化), 换成中性实现值后消失; 但 Opus 同种子复核显示换定义本身只解释约 -0.009 的遗憾变化, 其余来自样本不同 (n=270 vs n=108), 故只能说 '部分解释', 不是 '确认'。结论只能是: 无证据显示 joint 补偿比 raw OMP 选得更好; 对 BLOCK 有 -0.028 (p~0.025, 仅描述)。
3. 观测空间 (y-空间) 残差能量的余量很小: 78 个候选全回拟 oracle 的单步 **残差能量** 下降比例 0.503, raw_c1 0.457, joint_c1 0.460 (来源: research/checks/as_ka_headroom_provenance_20261106.py, 输出 research/checks/ka_out2/KA_HEADROOM_PROVENANCE_stdout.txt; v1 集 n=270 为 0.502/0.447/0.423)。**这是 y 空间残差能量比 (含噪声底), 不是干净图 MSE**; 原稿把它写成 '约 8.5% MSE' 是错误措辞, 已更正 (Opus 复审 Flaw 1)。
4. 局部线性得分对实现值的排序力弱: 分裂内 Spearman raw_c1 0.09 / block_c1 0.22 / joint_c1 0.31, 而自由系数版 0.46-0.47; 出生 0.55。按 Opus 的 K-d (Spearman<0.3) 判据, 可执行 c=1 分裂得分对 raw/block 触发。自由系数 (沿 P⊥v 方向的价值) 比 c=1 更会排名, 因为实际回拟会自由移动子代 (c* 中位数 0.24–3.9, 远离 1)。
5. 局限: 一步而非整条路径; K0=3; 5 个真值; σ_n 固定; 实现值只用 10-14 步 LM; 只 12–30 个种子/格; 场景由我设计 (tailoring 风险, 偏向 joint 的设计也未显示 joint 优势)。
## 读法 (已按 Opus 复审更正, 2026-11-06T00:11Z)
这**不是** '无余量' 的证据, 也不是 STOP 判据。它只说明: 在单步、K0=3、y 空间 (残差能量) 的小玩具里, joint 补偿相对 raw OMP 的选择没有可测优势。Opus 同种子复核 (research/notes/OPUS_REVIEW_AS_CONTRACT2_20261106.md Q2): (a) 以干净图 MSE 为准, 一步合法全回拟 oracle 相对 raw_c1 约有 9% 余量, ORACLE_x 约 17%, 而同一批的 y 空间余量约 5%; joint_c1−raw_c1 在干净 MSE 上为 −0.023 log (噪声很大, p≈0.67), '在 gate 指标上是否有优势' 未解决; (b) K0=6、σ_n=0.03 时, y 余量约 0.6%, 合法 oracle 的干净 MSE 比 raw_c1 约差 31% (拟合噪声), 而 ORACLE_x 仍有约 29% 余量 -> 读数会随容量/噪声翻转。故 K-a 的恰当表述是: '单步 y 空间自检没有区分力; 在 gate 指标 (干净 MSE) 上未检验'。
## 对 v2 的含义
- 本合同的 kill test 值得做 (Opus 评估 GO 先验约 5-10%, 但可给出预注册的诚实结论)。
- 出生的编辑执行须规则中性 (同时试 raw 与 OLS 振幅初值, 取训练损失较低者)。
- 分裂得分: c=1 可执行得分为主; 自由系数 (单侧) 为次级描述臂; 'JOINT 失败而 JOINT_FREE 通过' 只作假设生成。
- 预注册空结果处置: Gate 0/1 未通过 -> STOP 选择线 (不复活); '未检验' 与 '负结果' 须区分措辞。
