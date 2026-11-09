# Gaussian 任务依赖图 (单一事实表; 状态变更同时写 tasks/ledger.jsonl)
状态: done / active / blocked(原因) / todo。owner: S=Sonnet5.5, O=Opus5.5(真实subagent), GLM=只读worker, KIMI=补丁worker, H=真人。
每个节点结束必须有: runs/<run_id>/status.json + 证据路径; 缺日志视为未完成。

| ID | 节点 | owner | 依赖 | 状态 | 验收/证据 |
|---|---|---|---|---|---|
| N00 | 接管: 读文件、目录读写、接管日志 | S | - | done | runs/20261105T073330Z-takeover-b7d3 |
| N01 | 宿主桥: pump v1 + OpenCode GLM/Kimi 真实连接 + 5槽并发上限 | S | N00 | done | queue/done/j03..j07; runs/*-host-*, *-opencode-worker-* |
| N02 | 定时任务 trig_<redacted> (配置) | S | N00 | done(config) | list_triggers读回; DECISIONS 07:42Z |
| N02w | 定时任务真实唤醒验收 | S | N02, 08:38Z | todo | list_triggers.last_run + memory/WAKES.md 对应行 |
| N03 | 项目重构: 目标/目录/依赖/统一memory/文献导入 | S | N00 | done(第一轮, 07:51Z; Codex 07:50同步已并入) | 本文件; archive/pre-restructure-20261105/MANIFEST.sha256; memory/SYNC_GAPS_ZH.md |
| N03r | 前期调研接收回执 (5份原始审查+FEASIBILITY/DIGEST/RABBIT/COLLISION/theory; 读取分级) | S | N03 | done | research/notes/PRIOR_RESEARCH_RECEIPT_20261105.md + run event |
| N06 | 调度/监督去重: 2h执行trigger保持; Codex gaussian-claude-90 仅监督 | S | N02 | done | memory/CODEX_MONITOR_ZH.md; STATE调度节 |
| N04 | pump v2 上线 (py/venv/pip/GPU串行/RESTART) -> v3 (+pyinstall) | H(双击) -> S | N01 | done | heartbeat v3 pid 44664; runs/*host-hostinfo-808b |
| N05 | 宿主 Python+.venv (numpy/scipy/pytest/torch CPU) | S | N04 | done(CPU; GPU torch 待GPU门) | runs/*host-py-2dc5 (scripts/env_report.py) |
| G0.1 | 一手文献阅读 + 最近邻矩阵 | S+GLM(scout) | N03 (GLM需N04) | active | research/notes/G0_reading_log_*.md, research/nearest_work/ |
| G0.2 | CPU 可行性图: 渲染器/协方差oracle/topK不连续/seed与干净真值边界/最强MC-SURE对照 | S+GLM(code-mapper) | N03 | todo | research/notes/G0_cpu_feasibility.md |
| G0.3 | G0 结论: 尖锐可证伪缺口 + 杀死条件 | S | G0.1,G0.2 | done(v1 草案) | research/nearest_work/G0_GAP_STATEMENT.md |
| G1.1 | 理论笔记: df分解, estimand, 假设, 不连续点 | S | G0.3 | done(v1, 经 Opus 第1轮) | research/notes/G1_theory.md |
| G1.2 | 冻结 F0 合同 (数据/评测器/预算/seed/阈值/MC误差容限/算力上限) | S | G1.1 | done (2026-11-05T08:33:33Z, v2 FROZEN sha256 8c563f02...) | contracts/F0_CONTRACT.md, contracts/F0_CONTRACT.sha256 |
| G1.3 | 真实Opus5.5审查 -> ACCEPT/REVISE/REJECT | O | G1.2 | done (3 轮: REVISE -> ACCEPT-WITH-CHANGES -> FREEZE-AFTER-CHANGES C1-C3, 已落实) | runs/20261105T081354Z-opus-review-b2de, ...d440, 20261105T082923Z-opus-review-ccde |
| G2.1 | 实现 CPU 渲染器+oracle评测器+全流程MC (隔离src/, 带单测) | KIMI(S集成) | G1.2 | active (Kimi j16 按旧规格仍在跑; 新规格 tasks/003c-implement-f0-v2.md 待 j16 结束后派发; runner/analysis 由 Sonnet 写) | src/, tests/, experiments/ ; runs/20261105T081649Z-opencode-worker-930e |
| G2.2 | 独立审计 (泄漏/seed独立/评测器隔离) | GLM(result-auditor) | G2.1 | done (004c 窄审计 6项ok, D-01; 前2次失败后窄范围成功) / 004d fast 同构审计 running | research/notes/scout_004c_audit_raw.md; j33 |
| G2.3 | 有界 CPU 预实验 F0 (宿主) | S | G1.3=ACCEPT, G2.2, N05 | v2: p1 墙钟中止, p2 INVALID(R7); **v3 冻结 (sha 85328d4e..., Opus r4 REVISE-v3 + r5 FREEZE-AFTER-CHANGES)**; v3 代码+单测 39 passed; GLM 004e 7/7 ok; **v3 pilot p1 完成 -> PROCEED (j41/j42)**; **Stage 1 完成: H1 HOLDS (合同字面, Opus 4b76 确认) / H2 = STOP (Opus)** | outputs/F0-pilot-p1, outputs/F0-pilot-p2fast, contracts/F0_CONTRACT_v3.md |
| G2.4 | 分析+headroom 决策 (go/revise/stop) | S->O gate | G2.3 | superseded (F0/H2 STOP=FAIL-0001; 新线见 M1-M6) | research/notes/F0_ANALYSIS.md |
| G3 | 仅当headroom: 估计器/控制器 + 同预算强对照 | S/KIMI | G2.4=go | todo | - |
| GPU | 单个8GB GPU小图验证 (仅有余量) | S | G3或G2.4强证据, 门禁见AGENTS | todo | 峰值显存+全流程耗时 |
| F0-close | F0/H2 路线关闭 (STOP) 与失败登记 | S | G2.3 | done (2026-11-05T18:02:24Z) | memory/FAILURES.md FAIL-0001..0009; research/notes/F0_RESULT_SUMMARY_20261105.md; Opus 4b76 |
| M0 | 新主线授权/回执 + 新 run + 失败日志建立 | S | F0-close | done (2026-11-05T18:02:24Z) | run 20261105T175811Z-session-6e38; memory/FAILURES.md |
| M1 | 同步 AGENTS/CLAUDE/MISSION/PLAN/CHECKLIST/STATE/NEXT/tasks + trigger prompt 更新 (不新建) | S | M0 | done (2026-11-05T18:04:00Z) | 各文件末尾/首部更新; trigger 读回 |
| M2 | 新 G0: 交叉拟合/数据分裂/Noise2Self/交叉验证式生长/自适应选点 近邻反证 | S+GLM(scout) | M0 | done v1 (2026-11-05T18:11:35Z; 摘要级居多, 可深化) | research/notes/G0_reading_log_20261105.md (追加) |
| M3 | 最小可证伪机制 + 强基线 + 廉价拒绝实验设计 | S | M2 | done (2026-11-05T18:11:35Z) | research/notes/CF_BIRTH_DESIGN_*.md |
| M4 | 真实 Opus 审查 (缺口 + 新 CPU 合同) | O | M3 | active (run 20261105T181102Z-opus-review-5134 已派 2026-11-05T18:11:35Z) | research/notes/OPUS_REVIEW_CF0_*.md; run id |
| M5 | 冻结 CF0 合同 (新图/seed 区段, 评测器, 预算, go/revise/stop) + 单测 | S | M4 | done 2026-11-05T18:38:48Z (Opus round 7 FREEZE-AFTER-CHANGES; 合同 sha256 11d1fc81…; 清单 963b39bd…; 单测 32 passed) | contracts/CF0_CONTRACT.md + sha256 + CF0_FROZEN_FILES.sha256 + CF0_FREEZE_RECORD.txt |
| M6 | 有界 CPU 预实验 (单变量 autoresearch; 不用 E1-E14/W0/W1 做确认) | S | M5 | done: pilot p1 PILOT_OK; dev d1 M=32 = **STOP** (FAIL-0013; wall 7992 s; V0-V8 全 true; analysis.json) -> Opus round 8 裁决 A (关闭 CF0, 负结果记录 v2, 汇报真人并暂停新线) | outputs/CF0-* |
| M7 | 汇报真人 + 等待方向决定 (K 轴基准研究须真人显式批准, 标'基准/经验笔记'; 先新 G0) | S->human | M6 | waiting human 2026-11-05T21:25Z | research/notes/CF0_NEGATIVE_RESULT_RECORD_20261105.md |

## RE 重新 vibe idea (2026-11-05T21:34Z, run 20261105T212439Z-session-2c28)
- 完成: 失败归因审计 (待 Opus); FAIL-0014; 一手原文收据 (3 篇 L4)
- 进行: 候选简报; Opus 审; 推荐
- 约束: 不复活两条 STOP; E41-58 封存; 新实验=新 G0+合同+Opus+冻结; CPU 先; 不动 FATE/P1901/MOE_OPD

## RE 更新 (2026-11-05T22:17Z)
- 完成: Opus round 9 (verdict NARROW); 审计 v2 + 候选 v2; FAIL-0016; 回执 R4-R9; G0 C32; M1/M2 自核验笔记
- 进行: M0 精读 (纸面) -> M1 补全 (白噪声); 需合同的 M2b/M3/M4/M5 未启动

## RE 更新 (2026-11-05T22:21Z)
- 完成: M0 部分精读 R10-R14; 粗算 §C
- 进行: Opus round 10 决策门 (A' 继续/改道/如实报告)

## RE 更新 (2026-11-05T22:27Z)
- 完成: Opus r10; 简报 v3; FAIL-0017
- 等待: 真人对 A'/A''/另选空间的决定 (不启动合同类步骤)
| AS0 | 授权/回执/新run/统一文档/trigger 复核 | S | - | done(trigger 真实唤醒待验) | research/sources/astra_handoff_20261105/ASTRA_HANDOFF_READ_RECEIPT_20261105.md; run 20261105T230727Z-session-74ee |
| ASw | trigger 真实唤醒验收 (00:38Z) | S | AS0 | 投递 PASS (00:38:53Z SUCCEEDED); 行为 NOT verified (FAIL-0021); 02:38Z 再核 | list_triggers.last_run + WAKES.md/skips 行 |
| AS1 | 新 G0: PUP/SteepGS/谱正则化+IRGNM/直接Gaussian逆问题/INR 一手核对 | S(+GLM) | AS0 | active (C41-C62; 缺口见综合笔记 §4) | G0_reading_log C41+; 读取回执 |
| AS2 | 最小合同(联合参考余量) + 真实 Opus + 冻结 | S,O | AS1 | **done**: v2.1 冻结 (FROZEN_AS_CONTRACT_v2_1.md); Opus run 20261105T233836Z-opus-review-b1b8 (REVISE) + 20261106T000215Z-opus-review-b52f (FREEZE-WITH-EDITS) | contracts/AS_CONTRACT_*.md sha256; OPUS_REVIEW_AS_* |
| AS3 | 机制检查 CPU 小图 (S0 代码+单测 -> S1 pilot -> S2 dev) | S | AS2 done | active: S0/S1 done; S2 j73-j80 运行中 (2026-11-06T00:49Z) | outputs/AS-*; 分析器输出 |
| AS4 | 完整参考 vs 强基线 (新开发图) | S | AS3 | todo | 同上 |
| AS5 | 局部近似 + split/merge (仅 AS4 有余量) | S,KIMI | AS4 | conditional | 同上 |
| AS6 | 冻结确认 (新图/新退化) | S,O | AS5 | todo | 同上 |
| AS-STOP | S2 STOP-Q1 后: 负结果记录 + 候选方向 G0 (新主线需新 G0/idea/合同/Opus) | S,O | AS3 done | active (2026-11-06T04:56:11Z) | research/notes/AS_S2_RESULT_STOP_Q1_20261106.md |
| AS-STOP-1 | 真人决定 C / D-headroom / D-rescope | HUMAN | AS-STOP | waiting (2026-11-06T05:02:14Z) | research/notes/AS_DECISION_MEMO_20261106.md |
| AS-ERR | FAIL-0025 勘误 + Opus 复核 | S,O | AS3 done | done (2026-11-06T05:35:45Z) | research/notes/AS_S2_ERRATUM_NOTE_*.md |
| AS-R | 节点 R: 只读分解选择余量 vs 停止余量 (提议) | S,O | AS-ERR; HUMAN/Astra 方向 | proposed (未冻结) | research/notes/AS_NODE_R_PROPOSAL_20261106.md |

| GEO-0 | 节点 R: 只读收尾 (四组读数, 准备+计算 <= 30 min, 一次, 不新拟合, 不作路线闸门) | S,O(轻量) | 授权 | done (2026-11-06T06:25:12Z); 结果 research/notes/AS_NODE_R_RESULT_20261106.md; (a) ORACLE_xs H=+0.298 [0.228,0.362], 假设成立/杀死准则未触发; 事后诊断, 不作闸门 | research/notes/AS_NODE_R_PROPOSAL_20261106.md (历史输入); 追加 I |
| GEO-1 | 48h 合同: F_alpha、alpha/eta 分离、U/AU、回映/接受、数据、强对照、预算、判定 | S | 授权 | done (2026-11-06T06:40:51Z) | contracts/GEO_CONTRACT_CANDIDATE_v1.md -> v2 (FROZEN_GEO_CONTRACT_v2.md, sha256 18aa67b4...) |
| GEO-1b | 真实 Opus 核数学等价/公平性/数据预算 -> 修具体阻断 -> 冻结 | O | GEO-1 | done (2026-11-06T06:40:51Z) 主审 FREEZE-WITH-CHANGES, C1-C14 已吸收并冻结; 窄审 8d02 (A1-A5)、f553 (K1 草稿)、6dd4 (K1 终检, 自报 claude-opus-5-5, ACCEPT-WITH-CHANGES) 均已完成并吸收; K1 最终冻结记录已追加 (2026-11-08T01:23Z) contracts/K1_FINAL_20261108.md + contracts/GEO_K1_FREEZE_RECORD.txt | research/notes/OPUS_REVIEW/OPUS_REVIEW_GEO_CONTRACT_20261106.md |
| GEO-2 | 冻结后有界 CPU 实现: 完整图像基参考、正则 LM、块、matrix-free PCG/LSMR、Tikhonov/TV; INR 准备 | S (+KIMI 小补丁, GLM 只读) | GEO-1b | **PAUSED-BY-HUMAN (2026-11-08T05:33:20Z; 恢复须真人明确授权; 见 memory/HUMAN_PAUSE_20261108.md; j95 分片人工暂停(未完成), tune_arms 172/864)** 此前 active (2026-11-06T06:40:51Z; 限额停摆 2026-11-06T09:04Z→2026-11-08T00:41Z 不计入 48h 时钟; 剩余约 45h34m 起算 00:41Z, 截止 2026-11-09T22:15Z) 代码/测试/记录已冻结提交 (2026-11-08T01:23Z, K1_FINAL; 18 项 pytest; 全流程干跑通过); pump 已恢复 (02:39Z), V 重跑通过, L 完成 (03:04Z, Q3 BOTTLENECK-OPTIMISABLE) -> D 进行中 -> H; 顺序 V -> L -> D -> H | |
| GEO-3 | 48h 决定 (三个问题分开): 继续/一次修正/停止候选 | S,O | GEO-2 | todo | |
| GEO-4 | 7 天局部算法: 退化后耦合邻域 + 共享粗空间; 第 3-7 天与 INR/TV/强 LM 正式比较 | S,O | GEO-3 通过 | todo | |

| TRN-0 | 接收回执: 真人恢复授权, 新 run/锁, 记忆与任务同步, 旧调度停用 | S | 授权 | done (2026-11-08T09:04:51Z; run 20261108T090408Z-experiment-f602) | memory/AUTHORIZATIONS.md, memory/STATE.md |
| TRN-1 | G0 短核对: 跨轮回收 / 学习粗空间 / Gaussian 学习优化 / 测量压缩最近邻与区分实验 (Rabbit 可选) | S (+GLM 只读) | TRN-0 | done 2026-11-08T09:44Z (短核对, 阅读深度 L2–L3, 见 G0 行 C84–C94; **不作原创性主张**; 最近邻: Ritz/子空间回收 Krylov (Saad 2000, Parks 2006 GCRO-DR), 学习粗空间/预条件, Gaussian 学习优化; 若后续写作需更深 G0 另立任务) | research/notes/G0_reading_log_20261105.md |
| TRN-2 | CPU 小规模合同 + 分账 + oracle: 固定 F_alpha、数据/盲留出(按图像与核族)、秩/时间预算、baseline、评测、判据; AJ/JVP/VJP/模糊/粗空间/投影/外层总时钟 | S | TRN-0 | done 2026-11-08T09:32Z (v0 → Opus REVISE → v1 → Opus ACCEPT-WITH-CHANGES N1–N9 → v1.1 候选; 代码 src/trn_{core,gen,flops,loop,study}.py + tests 9 项通过) | contracts/TRN_CONTRACT_CANDIDATE_v0.md |
| TRN-3 | 真实 Opus 审合同 (数学、质量容差、成本判据、数据泄漏) -> 修具体阻断 -> 冻结 | O | TRN-2 | done 2026-11-08T09:41:55Z (Opus 三轮: v0 REVISE / v1 ACCEPT-WITH-CHANGES / v1.1 ACCEPT-WITH-CHANGES; 冻结 contracts/TRN_CONTRACT.md sha 9fb30498…07e8, contracts/TRN_FREEZE_RECORD.txt) | contracts/TRN_CONTRACT.md |
| TRN-4 | 同状态/同秩/同预算参考实验 (坐标·Ritz 回收、确定性输运、理想输运+理想修补; Amdahl) | S | TRN-3 | done 2026-11-08T12:31Z: G-A 通过 (M/L); G-B M 规模 B✗ (D46 W 比中位 1.095, 要求 ≥1.5) → FAIL-0032 NEGATIVE; MC 先验门不过 (STOP); Opus 终态门 CLOSE-NEGATIVE-WITH-CAVEATS (research/notes/OPUS_REVIEW_TRN_TERMINAL_20261108.md) | outputs/TRN-S0/, TRN-S0L/, TRN-SS/, TRN-SS-k16/, TRN-MC/ |
| TRN-5 | 有净余量: 小型 PSF 条件图模型 + 闭环 + 独立留出; 无余量: 记失败, 按预注册转测量压缩挑战 | S,O | TRN-4 | closed (不开): TRN-4 终态 A✓B✗ → MC (先验门 STOP); 小图网络未被终态表启用 | |
| RJ-1 | 被拒 trial 工作量杠杆 (B* 闭环 67–77% CG 迭代在被拒 trial 上): 文献核查 + 合同草案 (含 R7–R11 更强确定性对照集、R9 oracle 上界门先行) → Opus 审 → 冻结 → oracle 门 (dev-sel M); 过不了即 STOP | S,O | TRN-4 | done 2026-11-08T16:23Z: 终态 STOP — Gate O 形式 INCONCLUSIVE (SC 删失 16.7%), oracle 探针未给出有效上界 (不陈述余量不足), Gate T 确定性调参已足够, OS@SC 1.096; FAIL-0034 + 补记 A; Opus 终态审查 run 20261108T162109Z-model-call-a092 (STOP 正确, Q2=A); 不碰 confirm 图 | outputs/RJ-*/ |
| HUMAN-DEC-1 | 路线收口后的方向决策 (等真人): Opus 判 A, 不自主开新线; 选项见 Projects 文档 claude/ROUTE_CLOSURE_decision_memo_20261108.md — (i) 保持暂停; (ii) 批准 dev-chk 313–320 上一次预注册 D 对 B0 的 W_sp 工程复核 (<=1 CPU·h); (iii) 批准停止维度 oracle 新合同 (Opus: 经典工作换名, 不推荐); (iv) 换方向 | 真人 | RJ-1 | waiting (2026-11-08T16:23Z) | |
