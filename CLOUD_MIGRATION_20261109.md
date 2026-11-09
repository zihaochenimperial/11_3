# Gaussian 项目云端迁移记录 (2026-11-09)

- 来源: D:/Gaussian 快照 (冻结合同、冻结记录、实验与分析脚本、测试、研究笔记、tasks/、各节点的顶层结果摘要)。导出包 `runs/cloud_export_20261109.tgz` (D 盘, sha256 f75c457f837e5710d5fb2c450698937d26acc59b1ccba83221f59fe52a6a4976)。D 盘原样保留 (含完整 memory/)。
- 本仓库是公开的, 所以做了脱敏, 与 D 盘导出相比:
  - 去掉 `memory/` 里的授权与内部运行记录 (AUTHORIZATIONS、CODEX_MONITOR、HANDOFF_STATUS、HUMAN_PAUSE、SYNC_GAPS、WAKES、FAIL_APPEND、STATE、NEXT、INDEX、DECISIONS) 以及 `archive/` 里这些文件的旧副本; 保留 `memory/FAILURES.md` 与 `memory/LESSONS.md` (失败与教训是科研记录)。
  - 本机用户名 (路径中的用户目录名) 替换为 `USER`; 定时任务编号替换为 `trig_<redacted>`。归档里个别文件的内容因此与原始 sha 不同; 冻结合同、`src/`、`experiments/`、`tests/` 未改动 (与 D 盘导出逐字一致, `contracts/CA_CONTRACT.md` sha256 仍为 5873c208bc7950df28e42490ae23866b2c07836ebf833f2596af1364c44979e1)。
  - 提交作者使用 GitHub noreply 邮箱。
- 已知残留 (未改, 因为改了会破坏冻结合同的 sha256 或属于项目指令文件): 冻结合同与候选合同、OPUS 审查包、根目录的 AGENTS/CLAUDE/PLAN/CHECKLIST 里仍有引用真人授权的文字。
- 未包含 (留在 D 盘, 体积大且可由冻结代码重算): 各节点逐次运行 JSON / 拟合缓存 (`outputs/*/runs`, `outputs/*/fits`, `outputs/CA/confirm`), `runs/` 下的备份包 (如 `runs/ca_confirm_runs.tgz` sha256 5a1f5f30…2a, CA 密封 CONFIRM 的 2112 次原始运行), `queue/`, `data/`。结果摘要 (如 `outputs/CA/confirm_REDUCE_{P,S,X}.{txt,json}`) 已包含。
- 当前状态: CA 归因节点已完成, 判定 V-INS (见 `research/notes/CA_RESULT_20261109.md`, `memory/FAILURES.md` FAIL-0037); 待真人决定下一步。
- 之后的工作方式: 在云端工作, 改动提交到本仓库; 不再往 D 盘同步。边界不变: JR STOP、旧 VERIFY / VERIFY2 与 811–826 封存、不碰 FATE/P1901/MOE_OPD、不启用额外付费。
