# Opus 科学门审查：JR CPU 合同候选 v0（只读）

(逐字存档: Opus 子代理 ad6a4001e0d9591b6 的 hand-back 报告, 收到时间 ≈2026-11-08T22:2xZ, runlog 20261108T215538Z-model-call-2985; 自报 Claude Opus 5.5 (claude-opus-5-5)。以下为其原文, 仅去掉 hand-back 框架的统一缩进。)

# Opus 科学门审查：JR CPU 合同候选 v0（runlog 20261108T215538Z-model-call-2985）

**自报模型：Claude Opus 5.5（claude-opus-5-5）。**

本次只读了：包全文、`contracts/JR_CONTRACT_CANDIDATE_v0.md`（L1–66）、`src/jr_core.py`（L1–205）、`src/jr_op.py`（L1–61）、`src/jr_gen.py`（L1–58）、`research/notes/G0_reading_log_JR_20261108.md`、`outputs/JR/design_smoke/tables_auc.txt`。我没有写文件、没有运行任何东西，也没有读或生成任何 confirm 图。另外我核实了一件事：`tests/` 目录下**没有 test_jr_core.py**。

**总判词：暂不可冻结。** "冻结前必改"的 R1–R9 按下面的文本改完、单测文件真实存在并全部通过之后，即可冻结，不需要再审。Q4 判 FAIL，但 R4 给出了替代方案，按 R4 改即可，不需要另开版本。

---

## Q1 主指标：PASS-WITH-CHANGES
- 冒烟表本身就说明了问题：PSNR 更好的臂，往往是 F 优化得更差的臂。
  - RND：OBS 的 F 更好（dGap −0.129），PSNR 却低 0.94 dB。
  - OBS-I：OBS 的 F 更好（−0.194），PSNR 却低 0.72 dB。
- 在模型失配区，只用 Q-AUC 做决策，会奖励"拟合不足、相当于提前停止的隐式正则"，而不是在检验"联合几何修复"这个机制。机制主张本身是 F 的修复效率，所以决策口径必须同时看 F。
- "匹配费用"的定义（log 网格 1e9–3e10、状态向后沿用、cap）可以接受：它对所有臂相同，也全额计入了费用。但网格范围来自冒烟，必须冻结，不得再动。

**冻结前必改**
- **R1（§9，PASS 定义）**：将 "PASS_X ⇔ mean ΔQ(X)≥δ_X 且 LB>0" 替换为：
  > PASS_X ⇔ (i) mean ΔQ(X) ≥ δ_X 且 ΔQ 的 BCa 95% 单侧下界 > 0；(ii) O-AUC 非劣：mean[O-AUC(OBS) − O-AUC(X)] 的 BCa 95% 单侧上界 ≤ +0.05（log10 单位）。只满足 (i) 而 (ii) 不成立时，记为"正则效应，非机制增量"，按不 PASS 处理。

  §7 同时追加：
  > 每臂另报"轨迹 PSNR 峰值及其所在 W"与终点 PSNR，用于识别 PSNR 先升后降（过拟合）的情形。F_ref 在 VERIFY 中按题取全部臂访问级最小 F；它对所有臂相同，O-AUC 的差值可比。

**建议**
- 另报"匹配 F 的 PSNR"（各臂首次达到同一 F 水平时的 PSNR），作为描述性读数。

## Q2 对照集与阈值：PASS-WITH-CHANGES
- 把 RND 和 IND1 设为必须击败的对照是合理的，不算过严：它们最便宜，冒烟显示它们恰恰最强（−0.94 / −0.88 dB）。要主张"按观测混淆分组"有价值，就必须赢过"随便分组"和"不分组"。
- 阈值取 Astra 的阶段量级而不是功效计算，可以接受，但须如实标注。
- 功效：冒烟中配对差的 SE 约为 0.05–0.19 dB（SPA 约 0.17）。δ=0.15 加上 LB>0，对 SPA 的功效偏低，要写明 INCONCLUSIVE 的可能。另外 n=12 时百分位 bootstrap 会覆盖不足。
- 近邻缺口：DAOPHOT/NSTAR 与多发射体拟合（DAOSTORM、ThunderSTORM 的 multi-emitter）早就"按 PSF 展宽后的支撑重叠分组、组内联合拟合"。这正是新颖性 (a)"白化响应 + 噪声尺度脊"最近的经典对照，当前臂集里缺这一项。

**冻结前必改**
- **R2（§8）**：
  > 单侧 95% 下界改用 BCa（图重采样 10000，seed 20261108，复用 trn_same_state_reduce.bca）；另要求符号计数 ≥ 8/12。
- **R3（§3 与 §9）**：增加门控对照 OVL-J：
  > 亲和 = PSF 膨胀支撑盒的重叠面积（DAOPHOT 式，不白化、不加脊），使用同一 agglomeration，费用按真实计；δ=0.10 dB 进入 PASS 集。

  理由：没有 OVL，就无法区分"白化与噪声尺度脊"和"PSF 重叠"这两种分组依据。

## Q3 调参公平：PASS-WITH-CHANGES
冒烟时已经知道的、对 OBS 不利的固定选择：
- 每个 sweep 都重新分组：分组费用约为线性化费用的 50%。
- 脊=1、10% 标定、平均连接、4σ 候选盒。

其中重分组间隔是一个已知的大成本项，冻结前就知道，应当放进调参，而不是留作事后修正（见 Q4）。脊和标定定义了假设本身（"噪声尺度"），可以固定，但要做敏感性报告。另外 "脊=1 即噪声尺度" 的说法依赖 10% 标定，应改为 "相对 10% 标定扰动的噪声尺度"。IND1 只有 3 个配置，比其它臂少，偏向对 IND1 不利，是反保守的。

**冻结前必改**
- **R4（§5，替换 T1/T2）**：
  > 所有分组臂（OBS、OBS0、SPA、RND、OVL、OBS-I）：T1 gs∈{2,4,9} @κ0=0.1, R=1；T2 R∈{1,4} @T1 最佳 gs；T3 κ0∈{0.03,0.3} @最佳 (gs,R)。每臂 ≤7 个配置。IND1：κ0∈{0.01,0.03,0.1,0.3,1}（5 个）。R = 分组复用间隔（每 R 个 sweep 重建一次分组；费用全计，复用期间不计 grp）。

**建议**
- 在 TUNE 上对 OBS 做 ridge∈{0.1,1,10} 的敏感性检查，只描述，不进入选择。

## Q4 CORRECT-ONCE：FAIL（按现写法）
- 冒烟时已经知道分组费用占 50%，却把唯一修正预先设计成"分组复用间隔"。这等于给 OBS 预留了第二次机会，而且触发诊断（W_free）是在 VERIFY 上读的，属于分叉路径。
- 把 R 放进调参（R4）后，这条规则就多余了。

**冻结前必改**
- **R5（§9）**：删除 CORRECT-ONCE 分支，终态只剩 CONTINUE 和 STOP。VERIFY-2 701–712 保持封存；只有在 CONTINUE 时，才能作为阶段 1b 的独立复现，并且须另立附录、经 Opus 同意。

## Q5 费用口径：PASS-WITH-CHANGES
- SPA、RND、IND1 只计它们真实的小分组费用，OBS 计 Gram 块、逆平方根和 agglomeration，这是公平的：费用就应当是各臂实际要付的。
- Jacobian 和 AJ 在 lin 类别中对所有臂都全额计入，这一点正确。
- `make_groups` L93 按支撑盒和交叠区计 Gram 费用，这是"高效稀疏实现"的代理价。但代码实际算的是全图 Gram（L64 的 `R.T @ R`，规模 m×6K）。墙钟会偏离 W，须披露。
- agglomeration 实际是 O(K³) 的循环（L73–79），只计了 20K²，计少了。由于所有分组臂都一样，而且相对 lin 很小，这只算次要问题。
- 2·nnz(A) 的计价与 SOp 的存储矩阵乘法一致。

**冻结前必改**
- **R6（§4 与 jr_core L93/L97/L99）**：
  > agglomeration 按 c·K³ 计费（c=10，对所有分组臂相同）；§4 注明 "grp 按支撑稀疏实现计价，实现为稠密 Gram，墙钟偏高，W 为准"。

## Q6 数据边界与泄漏：PASS-WITH-CHANGES
- 种子标签 20/21 与旧标签不相交。601–624 和 531–578 不在 ALLOWED 中，会被拒绝。方法侧不 import 评测侧。这些都正确。
- 漏洞（FAIL-0029 的教训）：
  - VERIFY 511–522 在代码层面完全没有门控（jr_gen L33 只检查 ALLOWED），任何干跑都可以在 VERIFY 上算出读数。
  - VERIFY-2 的门控没有检查分析器 sha，也没有单次消费。
- 设计冒烟 590–592 的使用边界写得干净。

**冻结前必改**
- **R7（jr_gen._gate 与 §2）**：VERIFY 和 VERIFY-2 都改为 TRN 式门控：
  > 环境变量 + FREEZE_RECORD 含 TUNE_DONE 与 VERIFY_UNSEALED（VERIFY-2 为 VERIFY2_UNSEALED）+ 运行中分析器（`__main__`）与已加载 jr_*.py 的 sha256 均已登记 + 首次成功读取后追加 *_CONSUMED，此后拒绝。干跑只允许 TUNE 或 590–592。单测必须用哑索引测试门控，不得合成任何 VERIFY 图。

## Q7 近邻与诚实度：PASS-WITH-CHANGES
- 阅读深度声明是诚实的。"机制不新"的表述也够诚实。
- 但 (a)"以白化响应区分弱可辨识与严格零空间并据此分组"有一个更近的经典对照没有列出：天文与显微测光中按 PSF 重叠分组的同时拟合。

**冻结前必改**
- **R8（G0 日志 §1 与合同 §0）**：补入以下近邻（至少到摘要级），并在 §0 写明 "(a) 的最近经典对照为 PSF 重叠分组同时拟合，由 OVL 臂检验"：
  - Stetson 1987，DAOPHOT/NSTAR 分组同时拟合。
  - 3D-DAOSTORM / ThunderSTORM 的多发射体拟合。
  - 重叠 Schwarz / 加性 Schwarz 块方法。
  - 基于 Hessian 图划分的块坐标下降（Gauss–Southwell–Lipschitz 选块）。

**建议**
- 补读块 Gauss–Seidel 中按残差更新的文献，以及 Jacobian 列相关聚类（BA 中的 visibility clustering 已列）。

## Q8 阻断冻结的缺陷
- **R9（§10，阻断）**：`tests/test_jr_core.py` 不存在，§10 的 9 项单测不得冻结前缺席。另加三项：
  - (10) OVL 亲和单测。
  - (11) 门控的哑索引测试（R7）。
  - (12) 分组复用间隔 R 的费用计数测试：复用的 sweep 不计 grp，重建的 sweep 计入。

  单测全部通过后，把各模块 sha 写入冻结记录。

- 不需要拆分合同。设计冒烟已经给出强烈的 STOP 先兆（对 RND、IND1、OBS-I 都落后 0.7–0.9 dB），但这正是要预注册检验的内容，不构成提前终止的理由。

**其余建议**
- O-AUC 的 F_ref 若改为"所有确定性臂中的最小值"，则须预先固定。
- 报告每臂的 no_step 比例。
- FULL 仅作弱参照的说法保留。

---

## 冻结结论
R1–R9 全部落实（合同文本、jr_gen 门控、jr_core 计费、新增 OVL 臂、单测文件存在并通过）后，即可冻结，无需再审。若不加 OVL（R3），则须删去 G0 日志和合同中关于新颖性 (a) 的任何表述。

自报模型：Claude Opus 5.5（claude-opus-5-5）。

---
注 (Sonnet, 存档时): Opus 阅读时 tests/test_jr_core.py 尚未落盘 (我在其审阅期间才写完; 现已存在, 10 项通过); 其"目录下没有"的核实属实于其读取时刻。
