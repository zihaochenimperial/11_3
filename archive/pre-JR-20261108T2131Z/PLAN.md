<!-- GEO-MAINLINE-BLOCK (置顶; 2026-11-06T05:51:19Z; run 20261106T054959Z-experiment-80ab) -->
> ## 【当前主线 -- 真人 2026-11-06 授权 + Astra high 最终决定; 取代下方所有"等待真人从 C/D/A'/AS-STOP 菜单选路"的旧状态】
> **唯一主线 (GEO)**: 固定 K、同一持续图像空间正则目标 F_alpha = 1/2||W(Ax-y)||^2 + alpha/2||x - x_ref||^2 (x_ref=0) 下的 Gaussian **联合几何求解及效率**。alpha 是真正的任务正则 (开发选择程序定), 与每步信赖域阻尼 eta 分开。首任务: 已知核单图去模糊。
> **授权与回执**: memory/AUTHORIZATIONS.md (逐字); research/sources/astra_geo_20261106/ASTRA_GEO_READ_RECEIPT_20261106.md; Astra 文件 runs/codex-monitor/20261106-astra-geometry-auto/{CLAUDE_EXECUTE_NOW_ZH,ASTRA_FINAL_DECISION_ZH}.md 与 20261106-astra-post-as-review/ASTRA_POST_AS_ORIGINAL_ZH.md。
> **节点链 (见 tasks/TASKS.md GEO-*)**: GEO-0 节点 R (只读, 准备+计算合计 <= 30 min, 一次, 不新拟合, 不作路线闸门) -> GEO-1 写 48h 合同 -> 真实 Opus 核数学/公平性/数据预算 (修具体阻断) -> 冻结 -> GEO-2 有界 CPU 实现与验证 (完整图像基参考 U/AU; 参数最小范数回映 + 真实下降接受; 对照: 同目标充分调定正则 LM / 逐 Gaussian 块 / 完整参考 / matrix-free PCG 或 LSMR / 像素域 Tikhonov-TV / INR 准备) -> GEO-3 48h 决定 (继续/一次修正/停止候选; 三个问题分开报告: 正则效应、联合效应、真实算法瓶颈) -> 通过则直接进 7 天局部算法 (退化后耦合邻域 + 共享粗空间), 不常规再问真人。
> **旧线**: JOINT 排序 STOP (FAIL-0024/0025 及勘误保留); F0/H2 (FAIL-0001)、CF0 (FAIL-0013) 不复活; E41-58 确认图封存; 旧 C/D-headroom/D-rescope 菜单、AS_DECISION_MEMO、AS_NODE_R_PROPOSAL 仅为历史/输入。Opus 方向咨询中的"新合同前置清单"属审阅者建议, **不是项目硬规则**: 新假设可源于开发数据 (须标来源并在新数据检验); 有近邻不禁止拟议贡献; 领域迁移逐项判断, 不一律算 benchmark。
> **边界不变**: Sonnet 主任务; 真实 Opus 科学门 (Agent model=opus, 记自报模型与 run_id); OpenCode GLM 窄只读/Kimi 隔离补丁, 默认 2 最多 5 不递归; 每个模型调用/实验先写 run; 失败 append FAILURES/DECISIONS/LESSONS; 保留原报告与勘误; 新图新 seed; CPU/8GB 优先, 最多 1 GPU 须检查锁, 不付费/ExtraUsage; 不碰 FATE/P1901/MOE_OPD; 不保证原创或分数, 主张只分 proposed/validated; 负结果精确到实现/条件/主张, 非显著不证明零效应, 开发诊断不冒充确认。
> **恢复路径 (任何新会话/唤醒)**: 读本块 -> `python3 scripts/runlog.py lock status` (BUSY 且心跳在 50 min 内则只读监控, 不抢锁) -> 查 queue/running、queue/inbox、runs/pump/heartbeat.json -> 读 tasks/TASKS.md 的 GEO-* 找第一个依赖已满足且未完成的节点 -> 执行; 每次唤醒结束必须写 memory/WAKES.md 并再 send_later 续链 (每 4h 监控 trig_<redacted> 已授权, 先查真实状态; 2h 任务 trig_<redacted> 为真人停用, 不得恢复)。
<!-- /GEO-MAINLINE-BLOCK -->

# Gaussian plan (Sonnet5.5 重构版, 2026-11-05)  [旧版: archive/pre-restructure-20261105/PLAN.md]

## 研究问题 (一个候选机制, 0 个已验证创新)
自适应2D高斯在固定最终 K 与固定优化预算下, **候选搜索(birth 提议与选择, 几何冻结)** 是否带来 K 解释不了的额外拟合风险?
若有, 能否在不知道干净图时估计它, 并用来改进 birth/冻结/停止决策, 且在**含全部搜索/探针开销的总墙钟时间**下优于: 固定K、残差birth、全局K留出(blind-spot)、直接移植的全流程 MC-SURE/DIP-DF。

## 前瞻假设与杀死条件 (阈值在 F0 合同里冻结后才可用; 此处只固定逻辑)
- H1 存在性: oracle(协方差)自由度 df_oracle 减去参数有效维数 p_eff 的"搜索过量" > 合同容限, 且随搜索规模单调变化。否 -> 机制不成立, STOP, 保留负结果。
- H2 移植不足: 全流程 MC-SURE (扫 eps, 探针数J) 在 birth 不连续处偏差/方差超容限或成本过高。否(移植已足够) -> 不声称新校正; 退为适用边界/复现结论。
- H3 决策价值: 校正后的决策在开发集, 同总预算, 对强基线有可重复收益。否 -> 不进入GPU。
- 证据分级: smoke / imported history / development / independent test 四类不混用; 独立测试只在冻结后跑一次。

## 阶段 (详见 tasks/TASKS.md)
G0 文献最近邻 + 缺口陈述 -> G1 冻结CPU理论与合同 -> 真实Opus审查 -> G2 实现/审计/有界CPU预实验 -> headroom 决策 -> G3(仅有余量) -> 单个8GB GPU小图 -> G4 独立测试(远程大卡由真人安排)。
完成一个已验收节点立即做下一个依赖满足的节点; 额度/权限阻断则写 checkpoint(memory/NEXT.md) 等待, 不回退 Codex, 不开额外付费。

## 计算与环境事实 (2026-11-05 实测)
- 桥接 shell = Linux VM (2核/3.9GB, 无GPU, 无 pytorch 源, 不能 unlink)。宿主 Windows: i7-12700H 20线程, 31.8GB, D:剩 228GB, RTX 3070 Ti Laptop 8GB (桌面占 ~1.5GB), 驱动 546.30 (CUDA<=12.3 -> torch cu121)。
- 宿主命令只能经 queue/ 文件队列 + scripts/host-pump.ps1 (白名单); GPU 单实验+锁; 不写 D:/Gaussian 以外。

## Checkpoint 2026-11-05T07:56:56Z (merged Codex 07:50 sync + human 07:55 message)
- 执行 trigger (2h) 保持; Codex 90min 监督仅审计, 不接管研究, 不重复调度 (memory/CODEX_MONITOR_ZH.md)。
- 前期调研回执完成 (research/notes/PRIOR_RESEARCH_RECEIPT_20261105.md); 主线 = 用户同意进入验证的候选机制, **不是**已证贡献、不是3篇成果。
- 下一个依赖满足节点: pump v2 验收(等真人) 与 G0.3/G1 并行; 真实 Opus 审查在 G1.2 冻结合同之后。
- Codex 终审条件: 大GPU前约定节点有证据 + 清晰 go/revise/stop。


## 主线变更 2026-11-05T18:01:53Z (真人 17:57 London 批准; run 20261105T175811Z-session-6e38) — 本节取代上文"研究问题/H1-H3"的"当前"地位, 上文保留为 F0 历史
**F0 状态**: H1 (合同字面) HOLDS=开发证据; H2 STOP (FAIL-0001); 0 已验证创新。旧合同 v2/v3 不为新方法背书。
**新主线 (候选, 未验证) — 交叉拟合 Gaussian birth/增长选择 (CF-birth)**
问题: 自适应 2D 高斯在贪心 birth 时, 候选位置由同一份噪声数据的残差选出, 随后又在同一数据上拟合参数, 选择偏倚 (winner's curse) 可导致噪声驱动的错误生长。把"选位置的信息"与"拟合参数的信息"分开 (例如 fission/分裂副本、像素留出/blind-spot、K 折) 能否在**匹配 K、匹配总计算与数据损失**下降低相对干净参考的风险, 同时保留真实细节?
前瞻逻辑 (阈值在新合同冻结后才有效; 此处只固定杀死条件):
- C0 存在性: raw 残差 birth 相对"在独立噪声副本上选位置"的参考风险差 (噪声驱动错误生长) 不显著 -> 机制不成立, STOP。
- C1 机制: 交叉拟合 birth 在预注册开发集上相对 raw 生长有可重复的风险下降 (含全部拟合/探针/数据损失/墙钟); 否 -> STOP。
- C2 强基线: 相对既有信息分离/验证 (Noise2Self/blind-spot 式像素留出选位置、fission-CV 停止/选择、K 折) 无增益 -> 不声称新方法, 退为基准/适用边界。
- C3 数据成本: fission 副本噪声 σ'=√2σ0 (信息损失) 与真实交叉拟合的拟合副本更噪这一混杂必须显式核算; 不核算 -> 不得下结论。
证据隔离: 选位置/拟合/参考真值严格分离; 新图/新 seed 区段 (不得与 E1-E14, W0, W1, 图索引 100+k/90/91 重叠; 具体区段在新合同冻结); 事后 9/12 仅线索, 不选阈值、不当确认。
阶段: M0 授权+失败日志(done 2026-11-05T18:01:53Z) -> M1 同步记忆/指令/trigger -> M2 新 G0 最近邻反证 -> M3 最小可证伪机制+强基线+廉价拒绝实验设计 -> M4 真实 Opus 审查 (缺口+新 CPU 合同) -> M5 冻结 (数据/seed/评测器/预算/go-revise-stop 阈值) -> M6 有界 CPU 预实验 (单变量 autoresearch) -> go/revise/stop; GPU 仅在 headroom+空闲检查+合同之后。

## 重新 vibe idea 阶段 (2026-11-05T22:02Z, run 20261105T212439Z-session-2c28; 真人 21:24 London 授权)
- 阶段: RE-0..RE-6 (见 CHECKLIST RE 节). 失败归因审计 -> 候选简报 (A 证书式生长/停止, C 投影 Fisher 可辨识性, B/D/E) -> 真实 Opus (run 20261105T220104Z-opus-review-f8b0) -> 唯一推荐 + 验收里程碑 / 缩窄问题。
- 约束: 0 已验证创新; F0/H2 与 CF0 两条 STOP 不复活; E41-58 封存; 旧 holdout-birth 草案 NO LAUNCH; 新实验 = 新 G0 + 新合同 + 真实 Opus + 冻结, 发展/独立确认分离; CPU 先; 最多 1 GPU 且须合同+headroom+空闲检查; 不启用 ExtraUsage; 不自动降为已知方法基准。

## RE 阶段进展 (2026-11-05T22:17Z)
- Opus round 9 = NARROW; 推荐 A' (半群下噪声校准证书) + M0-M5 (见 research/notes/REIDEA_CANDIDATES_20261105.md §2.5)。M0/M1 纸面可自主; M2b/M3/M4/M5 须新合同+真实 Opus+冻结。K 轴余量小 (<=2.8pp vs RAWcv) -> 须换基准才能检验停止规则价值。

## RE 阶段 (2026-11-05T22:27Z)
- Opus r10 建议关闭 A' 作为方法原创性路线; 条件路径 A'' (局部 vs 全局停止) 需 M0 纸面 + M2b(新合同+Opus+冻结)。去留待真人。

## AS 阶段 (2026-11-05T23:26Z; run 20261105T230727Z-session-74ee) -- 退化观测下 Gaussian 容量与几何控制 (proposed)
- 问题: 把有限 Gaussian 容量用于观测可恢复的图像细节, 而非彼此补偿、观测上分不清的几何变化; 首任务已知核单图去模糊 y=A x(theta)+eps。
- 假设逻辑(阈值在合同冻结后才可用): H-A 完整小规模联合参考控制相对块/逐Gaussian 方法与强基线有可测重建余量; H-B 余量在多种重叠/模糊条件下一致且不依赖单核/单初始化; H-C 低成本局部近似保留大部分余量且总时间可竞争。任一失败 -> STOP 并如实记录。
- 节点 AS-1..AS-6 见 memory/NEXT.md; 强基线与停止条件见同处。杀死判据来自 Astra 建议并由我细化, 待真实 Opus 审。
- 证据分级: smoke / development / independent confirmation 不混用; 确认图须新选、封存、一次性使用; E41-58 不动。

- [2026-11-08T01:23Z] GEO-2 更新: K1 冻结 (见 contracts/K1_FINAL_20261108.md); 顺序 pump 恢复 → V 重跑 → L → D → H → GEO-3; 48h 时钟剩余 45h34m (停摆不计), 截止 2026-11-09T22:15Z。

- [2026-11-08T09:04:51Z] TRN 路线 (真人授权恢复; Astra high 重评): 见 memory/NEXT.md 顶部 TRANSPORT-MAINLINE-BLOCK; 先 G0 短核对 -> CPU 合同/分账/oracle -> 真实 Opus -> 冻结 -> 同状态参考实验 -> 按预注册: 小图网络或测量压缩。
