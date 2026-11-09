# 真人要求的只读进度审计

时间2026-11-05 07:46 Europe/London。作者Codex，仅本次审计，不恢复研究执行/调度，不修改Claude代码或打断现有任务。快照会继续变化。

## 结论

执行方向符合主线，接管/基础设施部分已有真实证据；尚未完成项目重构、G0文献对照、G1Opus合同或CPU科学实验。不能称已经端到端自主研究。

## 可核查证据

- runs/20261105T073330Z-takeover-b7d3/status.json：十个必读文件路径/哈希、起止时间、输入与结果指针。实际包含MISSION、STATE、LITERATURE_IMPORT；因此已取得前期摘要及文献索引。文件读取日志不是逐篇深入理解证明。
- 两次OpenCode成功输出在runs/worker-47e99ab657e04070a06338f648fba9f0/output.jsonl(GLM)与worker-4d643f6e286040c98bb4ca358cadce16/output.jsonl(Kimi)。实际有服务响应/token数据；模型名字在响应文本中属于自报，输出事件不提供实际服务模型字段，configured-vs-actual尚有边界。
- queue/done/j03-contention6.result.json：六个并发slotprobe，五个占用不同slot、一个被拒，保持25秒。验证的是launcher槽位上限，不等于五个真实模型并发/负载实验。
- 首轮ProtectedData错误已保存，Claude修复并重试成功；不是模型配额问题。tasks/ledger保留contention误判与纠正记录。
- memory/DECISIONS和WAKES记录Claude原生trigger已配置/读回，下次08:38UTC，真实唤醒PENDING。未从当前审计独立调用Claude调度API核对；只确认应用卡片与记录相符。
- 尚无src/tests/contracts新产物；research仍主要为迁入文件，没有新的最近邻方法矩阵/新全文阅读证据；没有Opus审查输出或科学试验结果。

## 与预期的偏差和待补项

1. 统一记忆未同步：STATE/NEXT/HANDOFF_STATUS仍称等待目录授权，CHECKLIST仍未勾接管；实际run已完成接管。恢复时会误读旧状态，应由Sonnet立即修正。
2. 前期摘要已知，但详细P1817_PHD_NOVELTY_FEASIBILITY、PRIMARY_SOURCE_DIGEST、RABBIT、LITERATURE_COLLISION等全文精读未在本轮输入记录中确认。应把这些列为G0必读并输出机制/最近邻/未证实点的短证据回执。
3. Claude实际通过Linux VM的挂载目录读写D盘，但VM不能直接调用宿主WindowsDPAPI/OpenCode/GPU。它编写host-pump队列桥接，属于必要基础设施。不能误把VM的GPU unavailable当宿主无8GB显卡。
4. 最新infra日志07:46:15：已放置queue/STOP让v1退出，需要真人启动scripts/start-pump-loop.cmd以换v2。审计末尾旧heartbeat的PID已查不到，v2尚未实测运行。此项是当前具体执行依赖，不应声称后续宿主任务会自动执行。审计不擅自启动宿主进程。
5. 每run开始/结束记录在改进；部分host记录是事后ingest，不能说每个模型调用开始前都已有完整log。后续应在派发时建run并归并token/输入来源，保留后补标记。

## 下一节点验收建议

Sonnet先同步统一memory与检查表，完成hostv2启动验收；随后并行开展可独立进行的文献反证与CPU合同设计，避免基础设施无限扩张。真实Opus审核合同后再执行科学实验。继续保持默认2workers、最多5、一次1GPU，Codex不回退。
