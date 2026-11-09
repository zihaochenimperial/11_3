<!-- JR-MAINLINE-BLOCK (置顶; 2026-11-08T21:32:24Z; run 20261108T213141Z-experiment-7986) -->
> ## 【当前主线 JR -- 真人 2026-11-08 授权「开始完成」(Codex 转交) + Astra high 选题; 取代 TRN-MAINLINE-BLOCK 的主线 (TRN 终态 NEGATIVE、RJ-1 终态 STOP 已收口, 不重开)】
> **路线 (proposed, 0 已验证贡献; 不保证原创或分数)**: 固定数量 K 的 2D Gaussian、单张观测 + 已知 PSF 去模糊; 研究 **由当前离散白化的模糊响应 (A 作用于原语及其几何导数) 构造观测混淆组, 组内联合有限幅度修复中心/宽度/强度**, 是否比空间邻居分组、或独立更新加线性投影更有效; 最终目标是未见模糊核下的重建质量跨核泛化 (CPU 节点先测机制, 有增量才做单张 8GB 小模型)。混淆须按图像空间变化/校准参数尺度测 (避免坐标单位伪差); 区分噪声尺度下弱可辨识与严格零空间; 每次有限更新由完整真实前向复核。固定 K, 无 birth/merge。
> **材料**: runs/codex-monitor/20261108-research-direction-review/{CLAUDE_JOINT_REPAIR_HANDOFF_ZH.md (sha 959c86d7), ASTRA_NEXT_DECISION_ZH.md (sha 902e85a8)}; 近邻: Boink 等 arXiv 2003.11253 §2.2, AIR arXiv 2605.20820 §III-C/D, DPIR, Deep Wiener, 2D Gaussian 散焦去模糊 (G0 记录: research/notes/G0_reading_log_JR_*.md)。
> **节点 (tasks/TASKS.md JR-*)**: JR-0 回执/记忆 -> JR-1 G0 近邻核对 -> JR-2 CPU 合同草案 (新 32-64 像素小图, 同初始化/K/前向/边界/预算/先验强度; 三臂 = 观测分组联合修复 / 空间邻居分组联合修复 / 观测分组独立更新+线性投影; 组建/搜索/更新费用全计; 调参集与核验集隔离) -> JR-3 真实 Opus 审 -> 冻结 -> JR-4 实现+单测 -> JR-5 真实更新对照 -> JR-6 继续/一次修正/停止决定 (预注册); 有增量才 JR-7 单张 8GB 小模型 (对 TV/DPIR/像素网络加校正/普通 PSF 条件 Gaussian 网络, 拟议阈值 +0.30 dB 对最强基线、+0.15 dB 对最强消融, 须阶段前预审并冻结)。
> **数据边界**: 新开发图 (调参集) 与核验集分离且均为新索引/新 seed; 旧开发数据 (301-320 等) 只作失败知识; 旧确认 321-344、401-424 继续封存不读; 干净图只用于设计允许的评测/训练。
> **分工**: Sonnet 主研与集成; 真实 Opus 审科学门 (核实自报模型, 记 run_id); OpenCode Go GLM 窄只读/Kimi 隔离补丁, 默认 2 最多 5 不递归, 同题失败 2-3 次 Sonnet 接管; vibe research 查一手近邻、vibe coding 窄补丁+单测、autoresearch 单变量/预注册预算/固定评测/保存全部读数; Codex 仅交接/监督。
> **调度**: 单一执行 owner = 本活动会话 (20261108T213141Z-experiment-7986); 续链 = 本会话 send_later (按需, 25-35 分钟, 每次先查锁/队列/pump, 记录配置与投递); 旧 2h、4h 监控、旧 GEO 唤醒及 RJ 续链保持停用; 宿主 pump 已停 (queue\STOP), 需要时先报告状态与经审定的首作业; 真人回 "停" 立即停止。
<!-- /JR-MAINLINE-BLOCK -->

<!-- HUMAN-PAUSE-BLOCK (置顶; 2026-11-08T05:33:20Z) -->
> ## 【人工暂停生效 -- 真人 2026-11-08 明确要求; 优先于下方一切"继续/续链"指令, 直到真人另行授权恢复】
> 不得: 启动文献研究/新实验/新调度、恢复 j95、恢复 2h/4h/一次性唤醒。4h 监控 trig_<redacted> 与一次性 trig_<redacted> 已停用; queue\STOP 已写; j95 两个分片 (pid 9932/13232) 标记"人工暂停(未完成)", tune_arms 已保留 172/864 个 .npz (BJ 144 全部 + BLK 部分)。
> 更正 2026-11-08T05:33:53Z: j95 两分片已于 05:32:36Z/05:32:39Z 结束 (exit=1, 人工暂停非失败); pump 已因 STOP 于 05:32:39Z 退出, queue\running 为空; 无需再 taskkill。已保留 172 个 .npz (完整性通过)。完整记录与恢复清单: memory/HUMAN_PAUSE_20261108.md。
> **[2026-11-08T09:04:51Z] 已由真人恢复授权取代 (见 memory/AUTHORIZATIONS.md 与 TRANSPORT-MAINLINE-BLOCK; 暂停记录保留)。queue\STOP 仍在, 直到需要宿主 pump 时按状态报告处理; j95 不重提。**
<!-- /HUMAN-PAUSE-BLOCK -->

<!-- GEO-MAINLINE-BLOCK (置顶; 2026-11-06T05:51:19Z; run 20261106T054959Z-experiment-80ab) -->
> ## 【当前主线 -- 真人 2026-11-06 授权 + Astra high 最终决定; 取代下方所有"等待真人从 C/D/A'/AS-STOP 菜单选路"的旧状态】
> **唯一主线 (GEO)**: 固定 K、同一持续图像空间正则目标 F_alpha = 1/2||W(Ax-y)||^2 + alpha/2||x - x_ref||^2 (x_ref=0) 下的 Gaussian **联合几何求解及效率**。alpha 是真正的任务正则 (开发选择程序定), 与每步信赖域阻尼 eta 分开。首任务: 已知核单图去模糊。
> **授权与回执**: memory/AUTHORIZATIONS.md (逐字); research/sources/astra_geo_20261106/ASTRA_GEO_READ_RECEIPT_20261106.md; Astra 文件 runs/codex-monitor/20261106-astra-geometry-auto/{CLAUDE_EXECUTE_NOW_ZH,ASTRA_FINAL_DECISION_ZH}.md 与 20261106-astra-post-as-review/ASTRA_POST_AS_ORIGINAL_ZH.md。
> **节点链 (见 tasks/TASKS.md GEO-*)**: GEO-0 节点 R (只读, 准备+计算合计 <= 30 min, 一次, 不新拟合, 不作路线闸门) -> GEO-1 写 48h 合同 -> 真实 Opus 核数学/公平性/数据预算 (修具体阻断) -> 冻结 -> GEO-2 有界 CPU 实现与验证 (完整图像基参考 U/AU; 参数最小范数回映 + 真实下降接受; 对照: 同目标充分调定正则 LM / 逐 Gaussian 块 / 完整参考 / matrix-free PCG 或 LSMR / 像素域 Tikhonov-TV / INR 准备) -> GEO-3 48h 决定 (继续/一次修正/停止候选; 三个问题分开报告: 正则效应、联合效应、真实算法瓶颈) -> 通过则直接进 7 天局部算法 (退化后耦合邻域 + 共享粗空间), 不常规再问真人。
> **旧线**: JOINT 排序 STOP (FAIL-0024/0025 及勘误保留); F0/H2 (FAIL-0001)、CF0 (FAIL-0013) 不复活; E41-58 确认图封存; 旧 C/D-headroom/D-rescope 菜单、AS_DECISION_MEMO、AS_NODE_R_PROPOSAL 仅为历史/输入。Opus 方向咨询中的"新合同前置清单"属审阅者建议, **不是项目硬规则**: 新假设可源于开发数据 (须标来源并在新数据检验); 有近邻不禁止拟议贡献; 领域迁移逐项判断, 不一律算 benchmark。
> **边界不变**: Sonnet 主任务; 真实 Opus 科学门 (Agent model=opus, 记自报模型与 run_id); OpenCode GLM 窄只读/Kimi 隔离补丁, 默认 2 最多 5 不递归; 每个模型调用/实验先写 run; 失败 append FAILURES/DECISIONS/LESSONS; 保留原报告与勘误; 新图新 seed; CPU/8GB 优先, 最多 1 GPU 须检查锁, 不付费/ExtraUsage; 不碰 FATE/P1901/MOE_OPD; 不保证原创或分数, 主张只分 proposed/validated; 负结果精确到实现/条件/主张, 非显著不证明零效应, 开发诊断不冒充确认。
> **恢复路径 (任何新会话/唤醒)**: 读本块 -> `python3 scripts/runlog.py lock status` (BUSY 且心跳在 50 min 内则只读监控, 不抢锁) -> 查 queue/running、queue/inbox、runs/pump/heartbeat.json -> 读 tasks/TASKS.md 的 GEO-* 找第一个依赖已满足且未完成的节点 -> 执行; 每次唤醒结束必须写 memory/WAKES.md 并再 send_later 续链 (每 4h 监控 trig_<redacted> 已授权, 先查真实状态; 2h 任务 trig_<redacted> 为真人停用, 不得恢复)。
<!-- /GEO-MAINLINE-BLOCK -->

# Gaussian checkpoints (证据 = runs/ 或 queue/ 路径; [x]=已验收, [~]=部分, [ ]=未做)  更新 2026-11-05T11:06:39Z
- [x] D:/Gaussian 建立; 12 份研究记录带导入哈希 (archive/import-manifest.json); 旧草稿归档
- [x] 补迁 5 份原始 Claude/Codex 审查, 源/目标 sha256 一致 (archive/legacy-reviews/import-manifest.json)
- [x] Sonnet/Opus/OpenCode 角色与 no-Codex-research 规则 (AGENTS.md); 真人升级规则已写入; Codex 仅有真人授权的只读监督例外 (memory/CODEX_MONITOR_ZH.md)
- [x] Claude App 目录绑定, 首任务接受, 读写实测 (runs/20261105T073330Z-takeover-b7d3); 勿重复
- [x] OpenCode 真实连接: GLM-5.3-Flash 与 Kimi K2.7 Code 经 run-worker.ps1 真实回复 (首败=启动器缺陷 PS5.1 ProtectedData, 已修, 原件在 archive/codex-originals/); serving-model 无权威字段, 仅"配置+响应自述"
- [x] 五槽启动器争用: 6个同时探测 -> 恰好5个拿槽, 第6个被拒 (queue/done/j03-contention6.result.json); 注意: 不是5个并发研究 agent 的验证
- [~] "默认2/不递归": 默认2由 pump -MaxConcurrent 2 实现; 不递归仅靠提示+权限, 无机械证明 (限制已记录)
- [~] 执行定时任务 trig_<redacted>: 配置 PASS; **真实唤醒 PENDING** (首次 2026-11-05T08:38Z; 验收 = list_triggers.last_run + memory/WAKES.md run_id 行)
- [~] Codex 监督 heartbeat gaussian-claude-90 (真人授权, 每90分钟, 只读): 已创建; 首次自动审计未验证; 不重复创建
- [x] 前期调研接收回执: research/notes/PRIOR_RESEARCH_RECEIPT_20261105.md (本地全文已读 / 一手论文工具摘要级 / 未读 分级; 主线=候选, 非已证贡献) + run 20261105T074518Z-infra-0001 事件
- [x] 项目重构第一轮 + 统一 memory (INDEX/STATE/DECISIONS/NEXT) + 文献导入; Codex 07:50 同步内容已并入 (本次)
- [x] pump v2 功能验收 (heartbeat v2 + startup.log + hostinfo j08, 08:00Z) 并已升级 v3 (加 pyinstall, 08:05Z 经 queue/RESTART 自动重启, 心跳 v3 pid 44664); 备份 archive/pump-versions/host-pump.v2.ps1
- [x] 宿主 Python 3.12.10 (python.org 安装包 26964224 B, sha256 67B5635E..., Authenticode Valid/PSF, 装至 D:\\Gaussian\\.tools\\python312, 无 PATH/启动器/关联改动; 真人 08:03Z 授权此类安装由我执行) + .venv: numpy 2.5.4, scipy 1.18.1, pytest 9.2.0, pillow, matplotlib 3.11.2, pandas 3.1.1, torch 2.15.0+cpu (14线程, 无CUDA); 证据 runs/*host-pyinstall-8b4c, *host-venv-3ddf, *host-pip-*, *host-py-2dc5
- [ ] GPU 版 torch (cu121) — 仅在 GPU 门前, 需另建 venv 或经 pump 扩展; 现 .venv 为 CPU 版
- [ ] 完整的逐调用前瞻日志 (派发前建 run; 现有宿主记录为事后 ingest)
- [~] G0 最近邻矩阵: S1-S7 摘要级; 新增 Jo2021(摘要级)、Gao&Jojic 2016(全流程扰动+重训, 摘要级); Janson2015 前半(工具摘要级, S10)、Friedman1991 仅二手(pyMARS 文档, 原文未读, S11) 已追加; Ye1998(仅二手: Hauenstein2018 复述, S12)/Efron2004(仅讨论+答辩开头, 主文未取到, S13) 已追加但原文均未读; Feng/Kao 版本存疑; GLM 侦察 002b 完成(抽查属实)、001b exit1 但有报告(部分核对)
- [x] G0.3 缺口陈述 v0->v1 (research/nearest_work/G0_GAP_STATEMENT.md; T3 已是已知结果, 原创性判断下调为"低"); 阅读未完的文献按"有先例"保守处理
- [x] G1 理论 v1 + F0 合同 **v2 冻结** (2026-11-05T08:33:33Z): contracts/F0_CONTRACT.md, sha256 8c563f0296376d41e2ca47608bbc9208873f3cb4a809316002d52feb37ff7f25 (contracts/F0_CONTRACT.sha256); 依据 Opus round-3 FREEZE-AFTER-CHANGES(C1-C3) 已逐字落实。注意: 这只冻结了**预注册合同**, 没有任何实验结果, 0 个已验证创新
- [x] 真实 Opus5.5 合同门 3 轮 (Agent model=opus, 自报 claude-opus-5-5): r1 REVISE (b2de), r2 ACCEPT-WITH-CHANGES R1-R9 (d440), r3 一致性确认 FREEZE-AFTER-CHANGES C1-C3 (ccde); 全文 research/notes/OPUS_REVIEW_F0_v0/v1/v2_20261105.md。**未完成**: 实验结果出来后的 go/revise/stop 门 (需再次 Opus) 与 headroom 决定
- [~] G2 CPU 代码/独立评测器 (2026-11-05T08:41:06Z): runner experiments/f0_run.py 与分析 experiments/f0_analyze.py 已按冻结合同写成并用玩具模型自测(experiments/f0_analyze_selftest.py, 非证据); 宿主单测脚本 scripts/run_unit_tests.py; Kimi src+tests (task 003c) 运行中 (run 20261105T084012Z-opencode-worker-9421, j18; j17 因启动器命令行过长失败, 非模型失败); 待: 宿主单测(V1) -> GLM 审计(tasks/004) -> pilot。尚无任何真实实验结果
- [x] G2 代码+宿主单测 (V1): 18 passed (outputs/unit_tests_status.json, run 20261105T094452Z-host-py-d13b); GLM 窄审计 004c 6 项 ok + 偏差 D-01 已登记 (research/notes/scout_004c_audit_raw.md)
- [x] v2 pilot: p1 (torch) 1800s 墙钟中止 (成本证据); p2 (fast) 完成, 判 INVALID(R7) (估计量不可识别, 非假说判决; outputs/F0-pilot-p2fast)
- [x] Opus 门 round 4 REVISE-v3 (66bb) + round 5 FREEZE-AFTER-CHANGES C1-C4 (5c5a): 合同 **v3 冻结** sha256 85328d4e9c20b41af3aabfd329d6dd4f561f95a1335357e5788c19294bb699d3 (contracts/F0_CONTRACT_v3.md); 全文 research/notes/OPUS_REVIEW_F0_pilot_20261105.md / OPUS_REVIEW_F0_v3_20261105.md
- [x] v3 代码+V1: f3_run.py/f3_analyze.py/tests/test_f3_units.py; 宿主单测 39 passed (outputs/unit_tests_status.json, run 20261105T102339Z-host-py-b2af); 变异检查通过; GLM 窄审计 004e 7/7 ok (research/notes/scout_004e_audit_raw.md)
- [x] v3 debug smoke (非证据, DEBUG-F3-pilot-smoke1) 走通 runner+分析全路径
- [x] **v3 pilot p1 完成**: 全部有效性闸门+P1+P5 通过 -> PROCEED Stage 1 --M=32 (j41/j42; outputs/F3-pilot-p1/ANALYSIS.md); pilot sdf 数仅为探索量级 (E1 35.6±3.2, E2 31.2±3.8), 不是 H1 证据
- [x] **v3 Stage 1 完成** (j44; outputs/F3-stage1-s1): 合同字面分析 (j46) H1 HOLDS (pooled sdf(1024)=27.6, 阈值 19.1, 12/12 正); 启动版分析 (j47) NOT JUDGED (D-03 两道合同外闸) -> 待 Opus 一致性裁决。H1 成立=development 证据, 不是原创性结论
- [x] Opus 门 (run 20261105T122958Z-opus-review-4b76, claude-opus-5-5): D-03 -> 合同字面版为准 (H1 HOLDS 须带 D-03 标注); **H2 (sdf 修正决策) = STOP, 不起草 H2 合同**; 新增 D-04 (8 workers vs 合同 4 进程, 只影响墙钟)。采纳: 估计量/修正主线 STOP, 保留 development 证据与可选已知方法基准
- [x] 真人决定 (17:57 London, 已落盘 2026-11-05T18:02:24Z, run 20261105T175811Z-session-6e38): 选 (3) 以"交叉拟合 birth 选择"重开 G0 作新主线; 要求所有失败写 log。旧"等待真人选路"状态已取消 (历史保留于 memory/DECISIONS.md)
- [x] M0 新 run {RUN} + 会话锁 + 授权/读取回执; memory/FAILURES.md 建立 (FAIL-0001..0009, 含 F0/H2 STOP 与长期规则)
- [x] M1 同步 AGENTS/CLAUDE/MISSION/PLAN/START_HERE/CHECKLIST/STATE/NEXT/TASKS/ledger 完成 (2026-11-05T18:04:00Z); 两小时 trigger prompt 已更新为读新主线+FAILURES.md (只更新, 无新建; 18:38Z 唤醒行为待核对)
- [x] M2 新 G0 v1 完成 (2026-11-05T18:11:35Z): research/nearest_work/G0_CF_BIRTH_NEAREST_WORK_20261105.md + 阅读日志 C1-C13 (摘要级居多, 标注); 结论=方法级不新, 价值=位置轴实证边界
- [x] M3 设计完成 (2026-11-05T18:11:35Z): research/notes/CF_BIRTH_DESIGN_20261105.md (proposed)
- [x] M4a 真实 Opus 审查 round 6 (run 20261105T181102Z-opus-review-5134) = REVISE (2026-11-05T18:15:51Z); 原文 research/notes/OPUS_REVIEW_CF0_DESIGN_20261105.md; FAIL-0010
- [x] M4b 真实 Opus round 7 (run 20261105T182355Z-opus-review-a490, 自报 claude-opus-5-5) = FREEZE-AFTER-CHANGES (2026-11-05T18:30Z; 非假说通过); 原文 research/notes/OPUS_REVIEW_CF0_CONTRACT_20261105.md; FAIL-0012; edits 1-7 已吸收 (偏差: 两次查看各 alpha/2, 已登记 DECISIONS)
- [x] M5 冻结 2026-11-05T18:38:48Z: 合同 contracts/CF0_CONTRACT.md sha256 11d1fc81…; 冻结文件清单 contracts/CF0_FROZEN_FILES.sha256 (13 文件) sha256 963b39bd…; 记录 contracts/CF0_FREEZE_RECORD.txt; 宿主单测 j54 32 passed; 新图 E15-18 (pilot) / E21-38 (dev) / E41-58 确认集保留未触; 不得用 E1-E14/W0/W1 做确认
- [x] M6 (完成, 结果 STOP / FAIL-0013) 有界 CPU 预实验 (单变量 autoresearch) -> go/revise/stop; GPU 仅 headroom+空闲检查+合同之后。M6a pilot p1 完成 (PILOT_OK, V0-V8 全 true; manifest 摘要 872dc35e…) -> M6b dev --M=32 (host job j62 于 18:49:18Z 起; 实测 6 worker 每单元中位 82 s, 预计总墙钟 ~2.4 h < 3 h 上限) -> 判定 GO-dev/STOP/INCONCLUSIVE (一次 dev_ext)
- [ ] 新主线机制 headroom 的 go/revise/stop 决定 (Codex 监督结束条件之一; F0/H2 的 STOP 已有: FAIL-0001)
- [ ] GPU 门 (空闲检查+单卡锁+合同+headroom) 之前不做任何 GPU 试验
- [x] M6c 真实 Opus round 8 (run 20261105T211139Z-opus-review-f986) = A (关闭 CF0; STOP 有效稳健); FAIL-0013 附记 A1; 负结果记录 v2
- [ ] M7 汇报真人 + 等待方向决定 (暂停新线实验; K 轴基准须真人批准 + 新 G0 + 新图 k>=61)

## RE (重新 vibe idea, 2026-11-05T21:34Z, run 20261105T212439Z-session-2c28)
- [x] RE-0 新 run + 解除旧"等待选路"状态 (真人 21:24 London 授权)
- [x] RE-1 一手原文取文通道测试 (shell->arXiv 403 缺口; 内置浏览器读 ar5iv HTML 可用; L4: Tibshirani 2015, Oliveira-Lei-Tibshirani, Leiner et al.)
- [x] RE-2 FAILURE_CAUSAL_AUDIT_20261105.md 交付真人 (Sonnet 起草; 待 Opus)
- [x] RE-3 候选简报 v2 REIDEA_CANDIDATES_20261105.md (A'/C'/B/D/E; 最近邻等级已按 Opus 下调; Rabbit 记缺口; 22:15Z)
- [x] RE-4 真实 Opus round 9 (claude-opus-5-5, run 20261105T220104Z-opus-review-f8b0) verdict NARROW; 原文 OPUS_REVIEW_REIDEA_20261105.md; 审计 v2/候选 v2 已并入; FAIL-0016
- [~] RE-5 唯一推荐 A' (NARROW) + M0-M5 已写; 进行: M0 精读 / M1 补全 (纸面); 实验类步骤 (M2b/M3/M4/M5) 须新合同+Opus+冻结; E41-58 封存
- [x] RE-6 (部分) memory/TASKS/INDEX/DECISIONS/NEXT/STATE + 既有 trigger prompt 已更新 (enabled=false 未动); PLAN 末节待写
- [x] RE-7 自核验 (非实验, 22:13Z): 半群数值成立; M2 描述性 (RAWcv=92.2% oracle 增益, oracle 仅多 2.8pp, K 轴=类型识别); research/notes/REIDEA_M1_M2_CHECKS_20261105.md
- [ ] RE-8 M0 精读 (SFW 全文/Duval-Peyre/Azais/Butucea/ADCG/CL-OMPR/Image-GS/Kac-Rice/OMP-discrepancy) -> 回执+G0 追加
- [x] RE-9 M0 部分精读 R10-R14 (Azais/Butucea/SFW补/PKP/Giard 2025) + 粗算 §C (22:21Z)
- [~] RE-10 Opus round 10 决策门 (run 20261105T222118Z-opus-review-8d5e) 进行中
- [x] RE-10 Opus round 10 决策门完成 (建议: 如实报告缺乏新意; 条件 A''); 简报 v3; FAIL-0017
- [ ] RE-11 真人决定: 关闭 A' / 继续 A'' / 另选问题空间 (未回复前不启动 M2b)

## AS 阶段 (2026-11-05T23:26Z, run 20261105T230727Z-session-74ee)
- [x] AS-0a 读取 Astra 三份交接文件全文 + 哈希回执 (research/sources/astra_handoff_20261105/ASTRA_HANDOFF_READ_RECEIPT_20261105.md)
- [x] AS-0b 新 run 20261105T230727Z-session-74ee + 会话锁; 旧陈旧锁 release
- [x] AS-0c 统一 memory/AGENTS/CLAUDE/MISSION/PLAN/CHECKLIST/TASKS 更新到新主线 (备份 archive/pre-AS-20261105T2326Z/)
- [~] AS-0d trigger trig_<redacted>: 重新启用 + prompt 更新 **配置 PASS**; **投递 PASS** (00:38:53Z last_run SUCCEEDED); **行为未证实** (无 skips/WAKES 行, FAIL-0021); 02:38Z 再核
- [~] AS-1 新 G0: 首批完成 2026-11-05T23:43Z (PUP/SteepGS/IRGNM/ADCG/OLS/3DGS-LM/3DGS² L4; 2D-GS 退化任务 L3; INR L2); 缺口见 AS_G0_SYNTHESIS §4
- [x] AS-2 (已冻结 v2.1 见下): v1 经真实 Opus = REVISE (FAIL-0020); K-a 自检完成; v2 候选已写 (2026-11-06T00:02Z), 待 Opus 轻量复审 -> 冻结
- [ ] AS-3 机制检查 | [ ] AS-4 完整参考 vs 强基线 | [ ] AS-5 局部近似+split/merge (有余量才做) | [ ] AS-6 冻结确认

- [x] AS-2 冻结 2026-11-06T00:13Z: contracts/FROZEN_AS_CONTRACT_v2_1.md (v2.1 sha256 4701d226...)
- [x] AS-3/S0: src/as_*.py + 单测 V1-V17 + 冻结分析器 (done 2026-11-06T00:34Z; 宿主 16/16 通过 j70; 分析器自检 j71; sha256 见冻结记录追加 A)
- [x] AS-3/S1: 计时 pilot (2 图 × C1,C4, 只读时间/闸门) -- j72 完成 (V16/V10/LM 上限均过; 预算未超)  [原:已提交 2026-11-06T00:34Z, 运行中
- [~] AS-3/S2: dev 全量 (宿主 py job j73-j80, 已提交 2026-11-06T00:49Z, 运行中)
- [~] AS-3/S2 补充: FAIL-0023 变体续跑 j81a/b (as_run_var.py) 运行/排队; Opus 复核追加 D 分析规则 (进行中); 分析器一次性运行待二者完成 [2026-11-06T01:40:48Z]
- [x] AS-3/S2: 完成, 机械判定 STOP-Q1 (2026-11-06T04:56:11Z); 冻结分析器已一次性运行; AS-4/AS-5 (JOINT 的完整参考强基线/低成本近似) 不满足前提 -> 不做; 新方向待新 G0/idea/合同/真实 Opus
- [x] AS-STOP: G0 第二轮 + 真实 Opus 方向咨询 (裁决 C) (2026-11-06T05:02:14Z); [ ] 等真人选 C/D-headroom/D-rescope; [ ] 四篇引用文献 L4 自读 (可选, 自主)
- [x] FAIL-0025: 核验 + 勘误 (j83b) + 真实 Opus 复核 (2026-11-06T05:35:45Z); [ ] 等 Astra 方向 / 真人决定; [ ] (条件) 节点 R 追加 I
- [x] GEO-2 K1 冻结+代码提交+干跑 (2026-11-08T01:23Z); [ ] pump 恢复 (需真人); [ ] 宿主 V 重跑; [ ] L; [ ] D; [ ] H; [ ] GEO-3 决定
