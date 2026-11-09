模型自报：Opus 5.5（claude-opus-5-5）

# Opus 科学门评审：冻结追加 D（FAIL-0023，split-only 受限候选集为空）2026-11-06

只读了以下文件：新旧 as_analyze.py 的 diff、as_run_var.py 及其测试、FEAS json 和生成它的脚本、as_core.py 的 gen_candidates/choose/mask_for/run_path/initial_state。没有运行任何东西，也没有读到任何质量量。

## Q1 排除不可行单元：可接受
- 结论：可以接受。
- step 0 的情况：initial_state(y, op, sn, 6.0, 30) 与规则、seed 都无关；gen_candidates 是否生成 split 只看夹紧状态。所以 step 0 为空的 6 个单元在 OMP_s 和 JOINT_s 中必然完全相同。按这种处理前协变量剔除，配对比较本身无偏，只是把估计对象改成"split 可行的单元总体"。报告中要写明这一点。
- 回退到混合池不可取，因为那样就不再是 split-only。空转也不可取，因为会在不同 K 下比较。
- step>0 的情况（如 (16,C3,9002)）不同：空集出现在规则自己走出的路径上，属于处理后变量。只用"两臂都可行"的单元做配对，等于对处理后结果做条件化，可能有选择偏倚，方向未知。这一项必须处理，见 M2。
- 图 16 只剩 1 个配对单元仍等权计入：可以接受。图级符号翻转检验的有效性只要求原假设下 D_i 关于 0 对称，与图内单元数无关；单元少只会降低功效，不会使检验失效。不要求每图最少单元数。建议另报一个"剔除配对单元数 < 4 的图"的敏感性结果，不赋予判定权重。

## Q2 MIN_VAR_IMGS=20 与"birth 胜出即非类型混合"：与 K-e 一致
- 结论：一致。K-e 的触发条件是两个变体内都未胜出。只要 birth-only 胜出，这个条件就不成立，与 split 变体能否评估无关。这和追加 C 对 BLOCK_s=unassessed 的处理一致。
- 精神上也说得通：变体内胜出说明 JOINT 的补偿优势不只是挑对了编辑类型。
- 阈值 20 是在已知 OMP_s 全部可行性图谱（非质量量）之后定的。按已知计数，只有图 16 接近被剔，所以这个阈值不会约束 OMP_s，只可能被 JOINT_s 在中途步骤的不可行触发。要披露这一点（见 Q4）。
- 更保守、同样可行的写法，建议采用，替换追加 D 中对应句：
  > "若某 R 的一个变体判 unassessed（图数 < MIN_VAR_IMGS，或依 M2 判 None），则该 R 的类型混合检查只由另一变体决定。另一变体胜出时不触发类型混合，但报告必须写明 'type-mix check partial: <t> unassessed (n_images=…, n_asym=…)'，GO 结论附带同一注记；后续新合同必须单独重新评估该类型内的比较，不得把本次结果当作该类型内的证据。"

## Q3 runner 与分析器：主体正确，有两处遗漏
- 已核对无误的部分：
  - 包装器的步数计数正确：run_path 每步只调用一次 mask_for；tops 用 np.ones，V10 复用 mask，都不经过 mask_for。
  - finally 中恢复了 mask_for。
  - 标记文件经 res.update 写入了 unit 字段，分析器能读到。
  - ERROR 单元不写文件，分析器会判 INCOMPLETE，不会被掩盖。
  - .tmp 和 .ckpt 文件被忽略。
  - birth 候选总非空（NMS 至少取到 1 个极大值），所以只有 _s 变体可能不可行。
  - BLOCK_b 用 OMP_b 替代、BLOCK_s 为 None，这些逻辑未受影响。
  - 剔除后的图级 signflip 是精确检验。
  - 合成自检覆盖了"只有一臂有标记而另一臂缺失 → INCOMPLETE"。
- 遗漏 1：标记文件没有做来源校验。任何臂目录里只要有 status=infeasible 的文件，就会被当作"已交代"，理论上能掩盖真正缺失的单元。修正见 M1。
- 遗漏 2：没有处理 JOINT_s 和 OMP_s 在后期步骤上不可行集合不一致的情况，见 Q1 和 M2。
- 次要：JOINT_s 中若某步所有 split 的 JOINT 分数都在 floor 以下，choose 会回退到 OMP 分数，此时 JOINT_s 退化为 OMP_s，会稀释差异。这是原有行为，不需要修改，但建议在次级报告中给出回退步数（可从 pred_joint is None 统计）。
- 次要：OMP_s 的图 1–14 由 as_run.py 生成，其余由 as_run_var.py 生成。两者对可行单元逐位等价（已测），但报告应按 run_id 列出每个单元的来源。

## Q4 过程：基本清白，需补充三项披露
- 整个流程是：崩溃（非质量信号）→ 只统计空集 → 在读取质量量之前写好规则 → 打补丁。这个顺序是合规的。
- 需要补充披露的三项：
  - (a) 可行性脚本对可行单元把 run_path 完整跑完了。轨迹在内存中算出后丢弃，未计算 MSE。应写明。
  - (b) run_var 测试在 outputs/vartest/AS 写入了图 14/C2/9001 的四条真实 S2 轨迹（OMP_s/OMP_b/JOINT_s/JOINT_b），这些可以直接算出 MSE。应声明未读取其质量，把该目录隔离或删除，并确认它不在分析器 root 之下。
  - (c) MIN_VAR_IMGS 是在已知 OMP_s 全部可行性计数之后选定的（见 Q2）。
- 另有一个科学注记，不涉及数据边界：图 16 的 K0 几乎全部夹紧，所有臂（包括规则臂）的初始 split 候选都为空。这反映初始化在该纹理图上饱和，应作为次级诊断报告。

## Q5 总判定：APPROVE-WITH-CHANGES

以下各项必须在运行分析器之前完成。

- M1 标记校验（写在 load_all/analyze 中；违反任一条即判 INCOMPLETE，原因记为 infrastructure）：
  - 标记只允许出现在 OMP_s、JOINT_s（及 BLOCK_s）中，且 r['only']=='s'；
  - empty_step 必须是非负整数；
  - 同一 key 上，OMP_s 中 empty_step==0 的标记集合必须与 JOINT_s 中 empty_step==0 的标记集合完全相等（step 0 与规则无关，所以必须一致）。
- M2 后期步骤的不对称不可行（某 key 只在一臂中不可行，或两臂都不可行但 empty_step>0 且步数不同）：
  - 报告 n_asym；
  - 主分析仍用交集；
  - 但该变体只有在下述最坏情形界下仍满足"mean D<0 且 p<0.10"时才判 True，否则判 None（unassessed）。最坏情形界的构造：每个不对称单元的 log 比赋为 max(0, 所有配对单元 log(M_J/M_R) 的最大值)，并入其所在图的均值；该图若原先被剔除，则恢复该图。
  - 判 False 的结果不受此规则影响。
  - 新增两条合成自检：一条验证 M1 的 step 0 集合不一致时判 INCOMPLETE；另一条构造一个不对称单元，使原本的 True 在最坏情形下翻转为 None。
- M3 在追加 D 中记录新分析器的 sha256、上述规则原文和 Q2 的替换文本；selftest 全部通过后才能运行（仍只运行一次）。
- M4 隔离 outputs/vartest，并按 Q4(b) 披露。
- 建议项（非必须）：每图配对单元数、图内单元数 ≥4 的敏感性结果、JOINT_s 回退到 OMP 的步数、按 run_id 列出单元来源。

**对 S2 总体结论的影响（核对后同意你的判断）：** Gate 0/1/F 只用 OMP、BLOCK、JOINT、FIXED、ORACLE_xs/ys，不读取任何变体臂。规则臂在 step 0 split 为空时仍有 birth 候选可选，不会崩溃。所以这个缺口不影响 Gate 0/1/F；它最多只能改变 Gate 都通过之后的 GO 与 INCONCLUSIVE-type-mix 之间的判定，并且按 M2 和 Q2 的写法，只会更难放行 GO。
