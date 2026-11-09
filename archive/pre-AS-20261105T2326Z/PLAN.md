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
