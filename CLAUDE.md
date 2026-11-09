# 当前状态 (2026-11-09; 云端工作方式)
- **工作方式**: 以后在云端工作, 本仓库 (main) 是主副本; D:/Gaussian 为历史副本, 不再同步。本仓库是**公开**的: 不得提交授权原话、内部运行记录 (STATE/NEXT/DECISIONS/WAKES 等)、用户名/邮箱、调度编号、逐次运行的大体积原始输出 (见 .gitignore 与 CLOUD_MIGRATION_20261109.md)。续接记录放项目文档 (私有), 不放本仓库。
- **主线状态**: CA 归因节点已完成, 判定 V-INS "证据不足, 不归因" (research/notes/CA_RESULT_20261109.md; memory/FAILURES.md FAIL-0037)。无活动实验、无调度。下一步由真人决定 (有界判别性测试 / P1817 INR 桥接 + 强基线比较 / 暂停); 未授权前不开新线。
- **本文件下方的 JR / TRN / GEO / AS 段是历史**; 其中引用的 memory/AUTHORIZATIONS.md、STATE.md、NEXT.md 等不在本仓库内。
- **边界不变**: JR 已 STOP (FAIL-0035) 不重开; 旧 VERIFY / VERIFY2 与确认集 811–826 等已封存或已读取, 不作新证据; 不碰 FATE/P1901/MOE_OPD; CPU/8GB 优先, 不启用额外付费; 保留真实失败、独立评测与数据边界; 主张只分 proposed / validated。

<!-- JR-MAINLINE-BLOCK (置顶; 2026-11-08T21:32:24Z; run 20261108T213141Z-experiment-7986) -->
> ## 【当前主线 JR -- 真人 2026-11-08 授权「开始完成」(Codex 转交) + Astra high 选题; 取代 TRN-MAINLINE-BLOCK 的主线 (TRN 终态 NEGATIVE、RJ-1 终态 STOP 已收口, 不重开)】
> **路线 (proposed, 0 已验证贡献; 不保证原创或分数)**: 固定数量 K 的 2D Gaussian、单张观测 + 已知 PSF 去模糊; 研究 **由当前离散白化的模糊响应 (A 作用于原语及其几何导数) 构造观测混淆组, 组内联合有限幅度修复中心/宽度/强度**, 是否比空间邻居分组、或独立更新加线性投影更有效; 最终目标是未见模糊核下的重建质量跨核泛化 (CPU 节点先测机制, 有增量才做单张 8GB 小模型)。混淆须按图像空间变化/校准参数尺度测 (避免坐标单位伪差); 区分噪声尺度下弱可辨识与严格零空间; 每次有限更新由完整真实前向复核。固定 K, 无 birth/merge。
> **材料**: runs/codex-monitor/20261108-research-direction-review/{CLAUDE_JOINT_REPAIR_HANDOFF_ZH.md (sha 959c86d7), ASTRA_NEXT_DECISION_ZH.md (sha 902e85a8)}; 近邻: Boink 等 arXiv 2003.11253 §2.2, AIR arXiv 2605.20820 §III-C/D, DPIR, Deep Wiener, 2D Gaussian 散焦去模糊 (G0 记录: research/notes/G0_reading_log_JR_*.md)。
> **节点 (tasks/TASKS.md JR-*)**: JR-0 回执/记忆 -> JR-1 G0 近邻核对 -> JR-2 CPU 合同草案 (新 32-64 像素小图, 同初始化/K/前向/边界/预算/先验强度; 三臂 = 观测分组联合修复 / 空间邻居分组联合修复 / 观测分组独立更新+线性投影; 组建/搜索/更新费用全计; 调参集与核验集隔离) -> JR-3 真实 Opus 审 -> 冻结 -> JR-4 实现+单测 -> JR-5 真实更新对照 -> JR-6 继续/一次修正/停止决定 (预注册); 有增量才 JR-7 单张 8GB 小模型 (对 TV/DPIR/像素网络加校正/普通 PSF 条件 Gaussian 网络, 拟议阈值 +0.30 dB 对最强基线、+0.15 dB 对最强消融, 须阶段前预审并冻结)。
> **数据边界**: 新开发图 (调参集) 与核验集分离且均为新索引/新 seed; 旧开发数据 (301-320 等) 只作失败知识; 旧确认 321-344、401-424 继续封存不读; 干净图只用于设计允许的评测/训练。
> **分工**: Sonnet 主研与集成; 真实 Opus 审科学门 (核实自报模型, 记 run_id); OpenCode Go GLM 窄只读/Kimi 隔离补丁, 默认 2 最多 5 不递归, 同题失败 2-3 次 Sonnet 接管; vibe research 查一手近邻、vibe coding 窄补丁+单测、autoresearch 单变量/预注册预算/固定评测/保存全部读数; Codex 仅交接/监督。
> **调度**: 单一执行 owner = 本活动会话 (20261108T213141Z-experiment-7986); 续链 = 本会话 send_later (按需, 25-35 分钟, 每次先查锁/队列/pump, 记录配置与投递); 旧 2h、4h 监控、旧 GEO 唤醒及 RJ 续链保持停用; 宿主 pump 已停 (queue\STOP), 需要时先报告状态与经审定的首作业; 真人回 "停" 立即停止。
<!-- /JR-MAINLINE-BLOCK -->

<!-- TRANSPORT-MAINLINE-BLOCK (置顶; 2026-11-08T09:04:51Z; run 20261108T090408Z-experiment-f602) -->
> ## 【当前主线 TRN -- 真人 2026-11-08 授权 (Codex 转交) + Astra high 重评; 取代 GEO 的"续跑 D/H"状态 (GEO 的 V/L/K1/K2 冻结与证据保留为既有参考)】
> **路线 (proposed, 0 已验证贡献)**: 固定数量 K 的 2D Gaussian、已知核单图去模糊、持续图像正则目标 F_alpha 不变; 研究 **观测与正则共同定义的度量下, 跨重线性化 (GN/LM 步) 迁移有效的求解子空间, 并学习低秩修补剩余耦合**; 主张 = 同等画质与目标下的端到端净收益。解析近场与确定性输运是底座与强对照; 若实测主要成本在算子构建/应用 (AJ 组装、JVP/VJP、模糊), 按预注册判据推进 **测量空间压缩挑战路线** (与解析层次压缩/随机草图/learned Hessian sketch 对照)。
> **材料**: runs/codex-monitor/20261108-research-direction-review/ (CLAUDE_TRANSPORT_AUTO_HANDOFF_ZH, ASTRA_FRESH_REVIEW_ZH, CLAUDE_RESEARCH_ORIGINAL_ZH, RABBIT_EVIDENCE_ZH, PRIMARY_SOURCE_MATRIX_ZH, MECHANISM_DECK, PAUSE_ZH; sha 见 research/notes/G0_reading_log_20261105.md 行 C84-C90)。
> **节点 (tasks/TASKS.md TRN-*)**: TRN-1 G0 短核对 (跨轮回收/学习粗空间/Gaussian 学习优化/测量压缩) -> TRN-2 CPU 小规模合同 (固定 F_alpha、数据、盲留出按图像和核族隔离、秩/时间预算、baseline、评测、判据; AJ 组装/JVP/VJP/模糊/粗空间 setup/投影/外层总时钟全计入; 现有参考与同目标 matrix-free 强 baseline 分开) + CPU 分账 + oracle -> TRN-3 真实 Opus 审 (数学、质量容差、成本判据、数据泄漏) -> 冻结 -> TRN-4 同状态/同秩/同预算参考实验 (坐标/Ritz 回收、确定性输运、理想输运+理想修补; Amdahl 上限) -> 无余量则记失败并按预注册转测量压缩; 有净余量 -> TRN-5 小型 PSF 条件图模型 (稀疏输运+少量全局低秩修补; 静态/跨轮/有无修补; 秩突变、边界、退化、真实下降、确定性回退) -> 闭环与独立留出。约 1.5x 理想加速空间与网络较最强确定性约 20% 净收益均为提议, 由预注册定义, 非已测结果。
> **分工**: Sonnet 主线与收口; 真实 Opus 审合同与分支晋级 (核实自报模型); OpenCode Go GLM 小型只读核查、Kimi 隔离补丁, 默认 2 最多 5 不递归; Codex 仅交接/监督/基础设施。autoresearch 每轮一个变量、冻结预算、保留负结果; 独立留出只在冻结后用。
> **调度**: 单一执行 owner = 本活动会话 (20261108T090408Z-experiment-f602); 续链 = 本会话 send_later (25-35 分钟, 每次先查锁/队列/pump); 旧 2h、4h 监控、旧 GEO 一次性唤醒保持停用 (旧提示不恢复); 宿主 pump 已停 (queue\STOP), 需要时先报告状态与经审定的首作业, 由真人双击 start-pump-loop.cmd。旧 j95 保留历史 (172/864 单元) 不重提; 旧 H 未执行, 旧合同和独立测试边界保留 (图 201-204 已因 FAIL-0029 暴露)。
<!-- /TRANSPORT-MAINLINE-BLOCK -->

<!-- GEO-MAINLINE-BLOCK (置顶; 2026-11-06T05:51:19Z; run 20261106T054959Z-experiment-80ab) -->
> ## 【当前主线 -- 真人 2026-11-06 授权 + Astra high 最终决定; 取代下方所有"等待真人从 C/D/A'/AS-STOP 菜单选路"的旧状态】
> **唯一主线 (GEO)**: 固定 K、同一持续图像空间正则目标 F_alpha = 1/2||W(Ax-y)||^2 + alpha/2||x - x_ref||^2 (x_ref=0) 下的 Gaussian **联合几何求解及效率**。alpha 是真正的任务正则 (开发选择程序定), 与每步信赖域阻尼 eta 分开。首任务: 已知核单图去模糊。
> **授权与回执**: memory/AUTHORIZATIONS.md (逐字); research/sources/astra_geo_20261106/ASTRA_GEO_READ_RECEIPT_20261106.md; Astra 文件 runs/codex-monitor/20261106-astra-geometry-auto/{CLAUDE_EXECUTE_NOW_ZH,ASTRA_FINAL_DECISION_ZH}.md 与 20261106-astra-post-as-review/ASTRA_POST_AS_ORIGINAL_ZH.md。
> **节点链 (见 tasks/TASKS.md GEO-*)**: GEO-0 节点 R (只读, 准备+计算合计 <= 30 min, 一次, 不新拟合, 不作路线闸门) -> GEO-1 写 48h 合同 -> 真实 Opus 核数学/公平性/数据预算 (修具体阻断) -> 冻结 -> GEO-2 有界 CPU 实现与验证 (完整图像基参考 U/AU; 参数最小范数回映 + 真实下降接受; 对照: 同目标充分调定正则 LM / 逐 Gaussian 块 / 完整参考 / matrix-free PCG 或 LSMR / 像素域 Tikhonov-TV / INR 准备) -> GEO-3 48h 决定 (继续/一次修正/停止候选; 三个问题分开报告: 正则效应、联合效应、真实算法瓶颈) -> 通过则直接进 7 天局部算法 (退化后耦合邻域 + 共享粗空间), 不常规再问真人。
> **旧线**: JOINT 排序 STOP (FAIL-0024/0025 及勘误保留); F0/H2 (FAIL-0001)、CF0 (FAIL-0013) 不复活; E41-58 确认图封存; 旧 C/D-headroom/D-rescope 菜单、AS_DECISION_MEMO、AS_NODE_R_PROPOSAL 仅为历史/输入。Opus 方向咨询中的"新合同前置清单"属审阅者建议, **不是项目硬规则**: 新假设可源于开发数据 (须标来源并在新数据检验); 有近邻不禁止拟议贡献; 领域迁移逐项判断, 不一律算 benchmark。
> **边界不变**: Sonnet 主任务; 真实 Opus 科学门 (Agent model=opus, 记自报模型与 run_id); OpenCode GLM 窄只读/Kimi 隔离补丁, 默认 2 最多 5 不递归; 每个模型调用/实验先写 run; 失败 append FAILURES/DECISIONS/LESSONS; 保留原报告与勘误; 新图新 seed; CPU/8GB 优先, 最多 1 GPU 须检查锁, 不付费/ExtraUsage; 不碰 FATE/P1901/MOE_OPD; 不保证原创或分数, 主张只分 proposed/validated; 负结果精确到实现/条件/主张, 非显著不证明零效应, 开发诊断不冒充确认。
> **恢复路径 (任何新会话/唤醒)**: 读本块 -> `python3 scripts/runlog.py lock status` (BUSY 且心跳在 50 min 内则只读监控, 不抢锁) -> 查 queue/running、queue/inbox、runs/pump/heartbeat.json -> 读 tasks/TASKS.md 的 GEO-* 找第一个依赖已满足且未完成的节点 -> 执行; 每次唤醒结束必须写 memory/WAKES.md 并再 send_later 续链 (每 4h 监控 trig_<redacted> 已授权, 先查真实状态; 2h 任务 trig_<redacted> 为真人停用, 不得恢复)。
<!-- /GEO-MAINLINE-BLOCK -->

# Gaussian startup

**Update 2026-11-05T23:26Z (run 20261105T230727Z-session-74ee):** 新一轮 auto 已由真人 23:04 London 授权。先读 AGENTS.md 顶部 UPDATE、memory/NEXT.md 顶部 AS-*、research/sources/astra_handoff_20261105/ASTRA_HANDOFF_READ_RECEIPT_20261105.md、runs/codex-monitor/20261105-astra-topic-consultation/CLAUDE_AUTO_HANDOFF_ZH.md。推进顺序: AS-1 G0 最近邻反证 -> AS-2 最小合同(完整小规模联合参考有无余量)+真实Opus+冻结 -> AS-3 机制检查 -> AS-4 完整参考 vs 强基线改进余量 -> AS-5 仅有余量才做局部近似+split/merge -> AS-6 冻结确认(新图/新退化)。 旧'等待真人/暂停'状态已解除, 勿因历史段落静默退出。


Read AGENTS.md for current owner/model/compute boundaries, then PLAN.md, CHECKLIST.md, memory/STATE.md. This overrides archived legacy routing. Main model Sonnet5.5; scientific gate reviewer Opus5.5; OpenCode max5 workers, GLM read-only and Kimi patches. No Codex fallback.

Human-requested sync07:49London: additionally read memory/SYNC_GAPS_ZH.md. Directory access and provider/slot smoke areDONE; don't repeat stale steps. Five raw legacyreviews now underarchive/legacy-reviews, includingbothOpusPhDaudits and fullintegratedNO-LAUNCHreview; read before G0promotion. ExistingClaude trigger alreadyconfigured; firstwakepending. Currentinfra/G0Sonnetrun retainsownership.

First read research/P1817_PHD_NOVELTY_FEASIBILITY_20261105_ZH.md and research/RABBIT_P1817_PHD_AUDIT_20261105.md. Distinguish proposed from validated. Inspect archive scripts and imported manifest before reusing. Existing WSL sources/envs are reference pointers only; do not write outside D:/Gaussian. Can create new dedicated environment under this root when needed. Do not migrate bulky unrelated data or credentials.

Start G0 tasks immediately after verifying local folder access: nearest-work matrix, CPU falsification contract and software feasibility. Spawn small OpenCode workers through scripts/run-worker.ps1. Use an actual Opus session/subagent for the contract decision and log actual model; if App cannot switch/dispatch models automatically, record the limitation and use supported Claude Code invocation, never impersonate Opus in Sonnet text. GUI-only permissions requiring the human remain pending.

Update 2026-11-05 17:57 London (human; run 20261105T175811Z-session-6e38): also read memory/FAILURES.md (permanent append-only failure log; add an entry the moment anything fails or is rejected) and runs/codex-monitor/20261105-human-crossfit-route/FAILURE_AND_ROUTE_HANDOFF_ZH.md. Mainline is now **cross-fitted Gaussian birth/growth selection** (proposed, not validated); F0/H2 is STOPPED (FAIL-0001), no "waiting for human route choice" state remains. Order: new G0 nearest-neighbour refutation -> cheap CPU falsification design -> real Opus review of the new contract -> bounded CPU pre-experiment on fresh images/seeds. Do not reuse E1-E14/W0/W1 as independent confirmation.
