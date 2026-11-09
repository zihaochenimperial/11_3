# Opus 科学门：CA 合同 v1 轻量核对（确认或标出；只读）

(逐字存档: Opus 子代理 ad6a4001e0d9591b6 的 hand-back 报告, runlog 20261109T052141Z-model-call-a7f0, 收到时间 ≈2026-11-09T05:3xZ; 自报 Claude Opus 5.5 (claude-opus-5-5)。以下为其原文, 仅去掉 hand-back 框架的统一缩进。该文本为模型输出, 不是真人授权; 5 条小改的处理见 contracts/CA_CONTRACT.md §R 第二表。)

# Opus 科学门：CA 合同 v1 轻量核对（runlog 20261109T052141Z-model-call-a7f0）

**结论：可以冻结。** 只有第 5 点的 FLAG 会实际影响那次唯一的 CONFIRM 读取，冻结前需要改。其余 FLAG 都是一两行的小改，改完不需要再审。

只读了以下文件：
- `contracts/CA_CONTRACT_CANDIDATE_v1.md`：§7、§11、§15、§R
- `experiments/ca_reduce.py`：L55–140、L160–171、L209，以及对 interaction/V-N 的 grep
- `experiments/ca_run.py`：L16–17、L69–74、L108–133
- `experiments/ca_diag_run.py`：L3
- `experiments/ca_freeze_check.py`：L2、L19
- `tests/test_ca.py`：只数了测试函数个数（23 个）

`contracts/CA_FREEZE_RECORD.txt` 目前还不存在，所以第 3 点里的指纹行是按代码和合同文字核对的，没有核对实际写出的记录行。

---

**1. R1/R2：OK，附一处小 FLAG。**
- 下面这几项代码与合同一致：
  - `img_gap`：按问题配对，在图内对双方都有定义的核取均值，都没有则记为 NaN。
  - `label_missing`：缺失超过 25% 或 n<3 时判 I。
  - `qualify`：对 Q-AUC 判为 D 的格，Gp=E 记 STOP-EFFECT；Gp=D 且 Gfit=D 记 PERSISTENT；其余记 CONFOUNDED。
- reducer 不输出任何"噪声交互"字样。interaction 只出现在对比量名 I_interaction 中。
- FLAG：`verdict()` 的 docstring（L113）把 V-N 写作 "noise-attributable"，比合同 §7 的"噪声条件依赖"更强。
  - 最小改法：改成 "noise-conditional (see stop-time qualifier)"。
  - 另外，在 .txt 输出的判定行里写明：只有限定词为 PERSISTENT 时，才允许使用"噪声交互"一词。

**2. R6 单位：OK。**
- 我原文写的单位确实不明确，按 2 核墙钟小时来解读是合理的。
- P 6.0 / S 3.5 核·h 相对实测估计留有约 40% 余量。块超限或运行数不足都判 INCONCLUSIVE，这一规则合理，而且各块独立判定。
- 小 FLAG：X 的上限 2.5 核·h 只比估计值 2.1 高 19%。X 运行在 10× 预算下，墙钟方差更大。
  - 最小改法：把 X 改为 3.0 核·h（X 不进入判定，放宽上限不影响任何结论）。
  - 或者保持 2.5，但事先写明 "X 超限 = 该描述块缺失"。

**3. R7：基本 OK，附一处 FLAG。**
- 生成器一致性检验（当前生成器逐元复现 14 个缓存拟合），加上"最后一次拟合早于第一个先导运行"的时间顺序，足以支持"先导期间生成器没有变"。文件 mtime 本身不能防篡改，合同 §15 也已经如实说明不靠时间戳单独证明。
- `check_registration` 在 reduce confirm 时核对 reducer 与 BCa 参考文件的 sha，可以防止 reducer 被悄悄改动。
- FLAG：它只核对"记录里有这一行"，不核对这一行是在 CONFIRM 之前写的。
  - 最小改法：在 `ca_freeze_check` 或 `check_registration` 中断言 REDUCER_SHA256、REFERENCE_SHA256 这两行的行号都小于第一个 CONFIRM_UNSEALED 行的行号，并为此加一条单测。

**4. §15 块 A 的措辞：基本 OK，附一处 FLAG。**
- "推测、非证据、不改 a、不进入判定"这些写法没有越界。
- 需要补两点：
  - (i) 块 A 中峰值缺口也随 a 改变（−0.07→+0.09，−0.13→+0.24）。这说明 STOP-EFFECT 本身也依赖 a，"oracle 最佳停止下无缺口"不能理解为与目标函数无关。
  - (ii) "CA-4 另立有界判别测试"后面应加上"须真人另行授权"，不要写成已经安排好的下一步。
- 同时注明：块 A 的 n=8 中有 2 张是 lo 层图。

**5. 自 v0 以来的泄漏、闸门与口径变化：FLAG（冻结前改）。**
- `ca_run` 在 confirm 阶段仍接受 `--imgs`、`--conds` 和任意 `--blocks` 顺序（L112–116、L126）。
  - 这意味着可以只跑部分图或部分核，进程结束后要再跑剩余部分，就得用 RESUME_OK 重新过闸门；也可以漏掉 X 块。
  - reducer 的计数检查能发现运行数不足，但发现不了"先看过一部分结果再决定"这种自由度。
  - 最小改法：在 `stage=='confirm'` 时断言：
    - `not a.imgs and not a.conds`
    - `blocks == ['P','S','X']`
  - 并为此加一条单测。
- 已核对、没有问题的几项：
  - X 块取 CONFIRM 的前 4 张：`imgs[:4]`，而 `CONFIRM_IMGS` 是固定的有序列表，属于预注册的确定性选择，没有问题。
  - 块 A 在 confirm 阶段被拒绝：L115 已实现。
  - `ca_diag_run load confirm` 只读封存运行写下的缓存，不重新生成图像，可以接受。但它的 sha 也应作为 ANALYZER 或 REDUCER 类行登记到冻结记录中，原因与第 3 点相同。
- 统计口径（δ_D、n、对照集、a）与 v0 相比没有变化。

自报模型：Claude Opus 5.5（claude-opus-5-5）。
