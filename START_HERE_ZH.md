<!-- GEO-MAINLINE-BLOCK (置顶; 2026-11-06T05:51:19Z; run 20261106T054959Z-experiment-80ab) -->
> ## 【当前主线 -- 真人 2026-11-06 授权 + Astra high 最终决定; 取代下方所有"等待真人从 C/D/A'/AS-STOP 菜单选路"的旧状态】
> **唯一主线 (GEO)**: 固定 K、同一持续图像空间正则目标 F_alpha = 1/2||W(Ax-y)||^2 + alpha/2||x - x_ref||^2 (x_ref=0) 下的 Gaussian **联合几何求解及效率**。alpha 是真正的任务正则 (开发选择程序定), 与每步信赖域阻尼 eta 分开。首任务: 已知核单图去模糊。
> **授权与回执**: memory/AUTHORIZATIONS.md (逐字); research/sources/astra_geo_20261106/ASTRA_GEO_READ_RECEIPT_20261106.md; Astra 文件 runs/codex-monitor/20261106-astra-geometry-auto/{CLAUDE_EXECUTE_NOW_ZH,ASTRA_FINAL_DECISION_ZH}.md 与 20261106-astra-post-as-review/ASTRA_POST_AS_ORIGINAL_ZH.md。
> **节点链 (见 tasks/TASKS.md GEO-*)**: GEO-0 节点 R (只读, 准备+计算合计 <= 30 min, 一次, 不新拟合, 不作路线闸门) -> GEO-1 写 48h 合同 -> 真实 Opus 核数学/公平性/数据预算 (修具体阻断) -> 冻结 -> GEO-2 有界 CPU 实现与验证 (完整图像基参考 U/AU; 参数最小范数回映 + 真实下降接受; 对照: 同目标充分调定正则 LM / 逐 Gaussian 块 / 完整参考 / matrix-free PCG 或 LSMR / 像素域 Tikhonov-TV / INR 准备) -> GEO-3 48h 决定 (继续/一次修正/停止候选; 三个问题分开报告: 正则效应、联合效应、真实算法瓶颈) -> 通过则直接进 7 天局部算法 (退化后耦合邻域 + 共享粗空间), 不常规再问真人。
> **旧线**: JOINT 排序 STOP (FAIL-0024/0025 及勘误保留); F0/H2 (FAIL-0001)、CF0 (FAIL-0013) 不复活; E41-58 确认图封存; 旧 C/D-headroom/D-rescope 菜单、AS_DECISION_MEMO、AS_NODE_R_PROPOSAL 仅为历史/输入。Opus 方向咨询中的"新合同前置清单"属审阅者建议, **不是项目硬规则**: 新假设可源于开发数据 (须标来源并在新数据检验); 有近邻不禁止拟议贡献; 领域迁移逐项判断, 不一律算 benchmark。
> **边界不变**: Sonnet 主任务; 真实 Opus 科学门 (Agent model=opus, 记自报模型与 run_id); OpenCode GLM 窄只读/Kimi 隔离补丁, 默认 2 最多 5 不递归; 每个模型调用/实验先写 run; 失败 append FAILURES/DECISIONS/LESSONS; 保留原报告与勘误; 新图新 seed; CPU/8GB 优先, 最多 1 GPU 须检查锁, 不付费/ExtraUsage; 不碰 FATE/P1901/MOE_OPD; 不保证原创或分数, 主张只分 proposed/validated; 负结果精确到实现/条件/主张, 非显著不证明零效应, 开发诊断不冒充确认。
> **恢复路径 (任何新会话/唤醒)**: 读本块 -> `python3 scripts/runlog.py lock status` (BUSY 且心跳在 50 min 内则只读监控, 不抢锁) -> 查 queue/running、queue/inbox、runs/pump/heartbeat.json -> 读 tasks/TASKS.md 的 GEO-* 找第一个依赖已满足且未完成的节点 -> 执行; 每次唤醒结束必须写 memory/WAKES.md 并再 send_later 续链 (每 4h 监控 trig_<redacted> 已授权, 先查真实状态; 2h 任务 trig_<redacted> 为真人停用, 不得恢复)。
<!-- /GEO-MAINLINE-BLOCK -->

# Gaussian 入口 (Sonnet5.5 重构版 2026-11-05; Codex 交接版归档在 archive/pre-restructure-20261105/)
新会话/定时唤醒: 读 memory/INDEX.md 的顺序 -> 先 `python3 scripts/runlog.py lock status` 防重复 -> 按 memory/NEXT.md 执行第一个依赖满足的节点。
目标与假设见 PLAN.md; 任务依赖见 tasks/TASKS.md; 证据在 runs/ 与 queue/。
宿主命令(OpenCode/GPU/Python)只能走 queue/inbox -> host pump; pump 需真人双击 scripts/start-pump-loop.cmd 启动(重启代码用 queue\RESTART)。

2026-11-05T18:01:53Z 更新: 现在也读 memory/FAILURES.md (永久失败日志: 任何失败/INVALID/INCONCLUSIVE/否决/限额当场追加) 。主线 = 交叉拟合 Gaussian birth/增长选择 (候选, 真人 17:57 London 批准; F0/H2 已 STOP=FAIL-0001)。不再有"等待真人选路"状态。
