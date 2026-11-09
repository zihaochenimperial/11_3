<!-- GEO-MAINLINE-BLOCK (置顶; 2026-11-06T05:51:19Z; run 20261106T054959Z-experiment-80ab) -->
> ## 【当前主线 -- 真人 2026-11-06 授权 + Astra high 最终决定; 取代下方所有"等待真人从 C/D/A'/AS-STOP 菜单选路"的旧状态】
> **唯一主线 (GEO)**: 固定 K、同一持续图像空间正则目标 F_alpha = 1/2||W(Ax-y)||^2 + alpha/2||x - x_ref||^2 (x_ref=0) 下的 Gaussian **联合几何求解及效率**。alpha 是真正的任务正则 (开发选择程序定), 与每步信赖域阻尼 eta 分开。首任务: 已知核单图去模糊。
> **授权与回执**: memory/AUTHORIZATIONS.md (逐字); research/sources/astra_geo_20261106/ASTRA_GEO_READ_RECEIPT_20261106.md; Astra 文件 runs/codex-monitor/20261106-astra-geometry-auto/{CLAUDE_EXECUTE_NOW_ZH,ASTRA_FINAL_DECISION_ZH}.md 与 20261106-astra-post-as-review/ASTRA_POST_AS_ORIGINAL_ZH.md。
> **节点链 (见 tasks/TASKS.md GEO-*)**: GEO-0 节点 R (只读, 准备+计算合计 <= 30 min, 一次, 不新拟合, 不作路线闸门) -> GEO-1 写 48h 合同 -> 真实 Opus 核数学/公平性/数据预算 (修具体阻断) -> 冻结 -> GEO-2 有界 CPU 实现与验证 (完整图像基参考 U/AU; 参数最小范数回映 + 真实下降接受; 对照: 同目标充分调定正则 LM / 逐 Gaussian 块 / 完整参考 / matrix-free PCG 或 LSMR / 像素域 Tikhonov-TV / INR 准备) -> GEO-3 48h 决定 (继续/一次修正/停止候选; 三个问题分开报告: 正则效应、联合效应、真实算法瓶颈) -> 通过则直接进 7 天局部算法 (退化后耦合邻域 + 共享粗空间), 不常规再问真人。
> **旧线**: JOINT 排序 STOP (FAIL-0024/0025 及勘误保留); F0/H2 (FAIL-0001)、CF0 (FAIL-0013) 不复活; E41-58 确认图封存; 旧 C/D-headroom/D-rescope 菜单、AS_DECISION_MEMO、AS_NODE_R_PROPOSAL 仅为历史/输入。Opus 方向咨询中的"新合同前置清单"属审阅者建议, **不是项目硬规则**: 新假设可源于开发数据 (须标来源并在新数据检验); 有近邻不禁止拟议贡献; 领域迁移逐项判断, 不一律算 benchmark。
> **边界不变**: Sonnet 主任务; 真实 Opus 科学门 (Agent model=opus, 记自报模型与 run_id); OpenCode GLM 窄只读/Kimi 隔离补丁, 默认 2 最多 5 不递归; 每个模型调用/实验先写 run; 失败 append FAILURES/DECISIONS/LESSONS; 保留原报告与勘误; 新图新 seed; CPU/8GB 优先, 最多 1 GPU 须检查锁, 不付费/ExtraUsage; 不碰 FATE/P1901/MOE_OPD; 不保证原创或分数, 主张只分 proposed/validated; 负结果精确到实现/条件/主张, 非显著不证明零效应, 开发诊断不冒充确认。
> **恢复路径 (任何新会话/唤醒)**: 读本块 -> `python3 scripts/runlog.py lock status` (BUSY 且心跳在 50 min 内则只读监控, 不抢锁) -> 查 queue/running、queue/inbox、runs/pump/heartbeat.json -> 读 tasks/TASKS.md 的 GEO-* 找第一个依赖已满足且未完成的节点 -> 执行; 每次唤醒结束必须写 memory/WAKES.md 并再 send_later 续链 (每 4h 监控 trig_<redacted> 已授权, 先查真实状态; 2h 任务 trig_<redacted> 为真人停用, 不得恢复)。
<!-- /GEO-MAINLINE-BLOCK -->

# Gaussian：明确目标与长程验收

## 当前目标更新 (2026-11-05T23:26Z, run 20261105T230727Z-session-74ee; 真人 23:04 London 授权)
真人 2026-11-05 23:04 London 在聊天中授权: 按 Astra high 意见完整交付, 开始新一轮 auto, 解除旧'等待选路'状态。新候选主线(proposed, 0 已验证贡献): 退化观测下, 面向可恢复细节的 Gaussian 容量与几何控制; 首任务=已知模糊核单图去模糊。思路(待检验, 非结论): 联合考虑邻居补偿, 识别观测支持的新图像变化, 用低成本局部近似控制 split/merge 几何更新。s(q)=||(I-P_AJ)Aq||^2/||q||^2 仅为经典投影结构的解释量, 不是新公式也不是完整 birth 规则; Fisher/Schur/谱正则换名不算创新。回执: research/sources/astra_handoff_20261105/ASTRA_HANDOFF_READ_RECEIPT_20261105.md; 交接: runs/codex-monitor/20261105-astra-topic-consultation/ (CLAUDE_AUTO_HANDOFF_ZH.md 等, sha 见回执; Astra 服务端模型未证实, ADVICE 为 Codex 整理版非逐字)。
推进顺序: AS-1 G0 最近邻反证 -> AS-2 最小合同(完整小规模联合参考有无余量)+真实Opus+冻结 -> AS-3 机制检查 -> AS-4 完整参考 vs 强基线改进余量 -> AS-5 仅有余量才做局部近似+split/merge -> AS-6 冻结确认(新图/新退化)。
验收原则: 事前只选一个主张 (a)同总时间实质质量收益 或 (b)近联合参考质量时明显更便宜; 不保证原创或分数; 完整联合谱正则化/IRGNM 是必须实施的最强反驳, 若同样便宜有效或仅 Schur 换名则停。下方旧目标(搜索风险/birth)为历史。


真人指令2026-11-05，Europe/London：完全交给Claude App执行，Sonnet主任务、Opus高级决策，OpenCode GLM/Kimi既定分工、最多5个worker；Codex仅本次交接。当前只有本机8GBGPU，不等待大GPU。

## 科学目标

判断自适应2D Gaussian表示的候选搜索是否引入最终K不能解释的额外拟合风险；若存在，研究可计算的估计/校正能否改善birth、几何冻结或停止决策。先比较直接移植的完整流水线MC-SURE/DIP-DF。新方法的价值可以是更准确、更省时的决策，或有实质意义的适用/失败边界；不能以换表示或更名充当原创。

## 本阶段应交付的结果

1. 一手文献矩阵与方法级最近邻反证，记录已读/仅摘要/仅线索及日期。
2. 新项目结构与统一记忆：真实软件/数据/环境清单；可见任务依赖、每次运行日志和恢复指令。
3. 经真实Opus审查的CPU理论/机制合同，独立噪声与优化seed、固定评测和总预算。
4. CPU最小复现与机制试验：参数计数、固定拓扑近似、全流程MC风险估计和真实参考风险比较；准确区分基础设施与科学结果。
5. 有余量才做单个8GBGPU小图验证，并测峰值显存、全流程时间。不能假定既有环境/草稿可直接使用。
6. 明确go/revise/stop结论、可复现实验包与下一步。失败保留，不为了正结果回溯改门槛。

## 重构要求

Sonnet先审查现状，再重构本项目，保留archive和导入哈希。只改D:/Gaussian；不复用旧合同为新研究背书。建议结构research/{sources,notes,nearest_work}、src、tests、contracts、data/{dev,test}、runs、outputs、memory、tasks。目录可以调整，但必须更新入口与引用，旧证据不能覆盖。

## 长程推进与日志

每次会话/定时恢复：先读AGENTS、CLAUDE、MISSION、PLAN、CHECKLIST、memory/INDEX与STATE、上次日志；检查现有进程/锁和产物，防止重复。结束一个已验收节点立即执行下一个依赖满足的任务，按配额和运行上限停止；上下文即将耗尽先落盘恢复信息。

每次调用/实验建立唯一run_id，开始前写runs/<run_id>/status.json和输入任务，运行中保存stdout/stderr或工具证据，结束/失败均写日志；任务表必须指向结果。每次模型调用记录实际provider/model、角色、开始结束UTC与伦敦时间、任务/文件所有权、exit/status、token/费用(服务返回才记录，否则unknown)、结果证据路径、失败原因、下一步。缺日志视为未完成，不把进程存在当结果。

项目记忆以D:/Gaussian/memory为唯一事实入口：INDEX索引，STATE当前状态，DECISIONS追加决策，LESSONS可复用失败经验，NEXT恢复步骤。聊天仅摘要，不成为唯一记忆。文献与run产物放对应目录，由记忆引用；不得把长篇原始日志塞进常驻上下文。

每轮autoresearch前冻结数据、评测器、预算和变量；一轮只改一个变量；记录所有尝试，选择只用开发集；不触碰独立测试。一次最多1GPU实验，包括旧进程。OOM先降分辨率/K/探针数量并记录合同变化，不能静默改指标。未知错误先诊断；额度不足checkpoint等待，不启用ExtraUsage、不回退Codex。

需要定时恢复时用Claude原生定时任务，先查重复；每2小时继续同一项目，静默处理无变化，完成/失败/需要真人操作才通知。配置与实际唤醒验证分别记录，不声称应用退出后持续运行。


## 主线变更 (真人 2026-11-05 17:57 London 批准; run 20261105T175811Z-session-6e38)
原"搜索自由度风险估计/校正"路线 F0/H2 已按 FAIL-0001 STOP (H1 合同字面成立=仅开发证据; H2 无独立方法贡献), 0 个已验证创新。新主线 (候选, 未验证): **交叉拟合的 Gaussian birth/增长选择**——研究把"选 birth 位置所用信息"与"拟合参数所用信息"分开后, 能否在同等预算下减少噪声驱动的错误生长并保留真实细节, 且相对 raw 残差生长、Noise2Self/blind-spot 式留出、fission-CV/K 折验证等既有信息分离/验证方法有可测收益或实质适用边界。
验收顺序: 失败日志 (memory/FAILURES.md) -> 新 G0 一手最近邻反证 (标注 原文/摘要/线索) -> 廉价 CPU 证伪设计 -> 新冻结合同 -> 真实 Opus 审查 -> 有界 CPU 预实验 (新图/新 seed, 不得用 E1-E14 做确认; 事后 9/12 仅线索) -> go/revise/stop。全部失败按 FAILURES.md 规则当场追加。不保证原创性或分数。
