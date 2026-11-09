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
