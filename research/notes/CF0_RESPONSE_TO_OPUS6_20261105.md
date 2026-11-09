# 对 Opus round 6 硬要求 1-10 的逐条响应 (Sonnet5.5, run 20261105T175811Z-session-6e38; 合同候选 contracts/CF0_CONTRACT_CANDIDATE.md)
1 重命名 XFER=honest 位置转移; 引用 honest trees/Tian-Taylor/RandOMP/DML; 无原创声称 -> 合同 §0。
2 增 XAVG(1)、RAWens2 (等成本集成)、XAVGctrl(1) (两副本同样平均的位置来源对照; 比 RANDens 更直接, RANDens 暂不加: 以免臂数膨胀, 如 Opus 需要可在 round 7 提出); NS(tau)、RANDy 入门 -> §2, §5。
3 GO 须胜 RAWy、NS(同 tau)、RAWcv(+1%); 估计量冻结为每图相对差(图等权); GO/STOP CI 水平写明 (Bonferroni(4) 下界; STOP 单侧 95% 上界 vs 最强竞争者) -> §4, §6。
4 CRN (同 e, z, ω) 写入合同; CV 基线 tau=1 固定、两方向; 噪声失配警告写明 -> §2。
5 pilot 只报有效性/成本/配对 SD, 风险差屏蔽在分析器代码里; M 由 pilot SD 按预注册规则固定 -> §6。
6 分析器与夹具随合同冻结; worker 数固定为 6 -> §3, §8。
7 诊断 (出生高斯位移、强制位置残差、型分层、NS vs XFER 每 tau) 均 report-only -> §6。
8 数值先验预测写入 -> §6 (NU(1) in [-100%,-25%]; NU(4) D1/D2 in [-10%,+5%]; pooled<0; GO 先验 ~10%)。
9 确认图 k=41..58 未生成 (runner 断言 k 范围); 一次 M 扩展预先定义 -> §3, §6。
10 GO 仅为"玩具 64x64 边界结果/进入确认合同" -> §0, §9。
设计说明 v1 的错误转述 (F3 D3 并非 0/4) 已登记 FAIL-0010; 合同不再引用该分类概括。
未采纳/延后: RANDens (随机化 births 集成) 暂不加 (见 2); fission-CV 按 tau 匹配的变体不用 (按 Opus 要求固定 tau=1)。
