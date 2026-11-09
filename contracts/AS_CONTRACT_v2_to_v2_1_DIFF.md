# AS 合同 v2 -> v2.1 变更日志 (逐项对应 Opus 复审 Q7 的 12 项编辑; 复审原文 research/notes/OPUS_REVIEW_AS_CONTRACT2_20261106.md sha256 e6b9586c...)
v2 sha256 b92e7dad82c21aa4be61574c6fdca014b9cb6ad5b795d1423a80eee2b3c1b251; v2.1 文件 contracts/AS_CONTRACT_CANDIDATE_v2_1.md (冻结后 sha256 记入 contracts/FROZEN_AS_CONTRACT_v2_1.md)。
所有改动为 Opus 所列文字/小设计编辑, 无自行新增设计; 如有不同处在下面标 [注]。
(a) 出生执行规则中性: §3 编辑执行段 — 所有规则的被选出生同时从 {c0, c*_OLS} 两初值各回拟 T_r 步, 保留训练损失较低者。
(b) JOINT_FREE 单侧: §3 — max(r·P⊥v,0)²/(2‖P⊥v‖²); 'JOINT 失败而 JOINT_FREE 通过' 只作假设生成。
(c) 新增 ORACLE_ys (seed 9001, 96 单元) 与 H_Oys 报告规则; H_Oys<=0 且 Gate 1 通过 -> INCONCLUSIVE-unexplained: §3, §4。[注] 短名单取 4 个规则各 top-8 并集 (<=32), 与 Opus 预算估计一致; 削减顺序第 3 项允许降为 top-5。
(d) ORACLE_xs 选定后重做 T_r=15 步回拟; 短名单由 oracle 自身路径状态生成; ORACLE_x-full 的 T_o=8, 条件执行 (仅当 ORACLE_xs<10% 时), 与 ORACLE_xs 在同一 12 单元比较: §3, §4 Gate 0。
(e) 单侧精确符号翻转检验 (2^24 全枚举, p=#{mean(sD)<=mean(D)}/2^24): §4 Gate 1 (ii)。
(f) 功效文字更正 (准则 (i) 对真 5% 效应单独约 50%; 可靠检出约 >=8%): §4 末。
(g) 判定表增加 INCONCLUSIVE (短名单限制)、INCONCLUSIVE-numerics (V10 稳定率<90%)、INCONCLUSIVE-unexplained、INCONCLUSIVE-type-mix; 类型混合规则 ('胜出' = 变体内 mean D<0 且同一检验单侧 p<0.10 —— [注] 阈值 0.10 为我补充的操作化, Opus 只给了定性规则): §4。
(h) 过拟合诊断预注册 (K_max 处训练损失与干净 MSE; 偏差原理 K 处重算 Gate 1 统计量): §4。
(i) 定义 H_X; 条件 C1..C4 显式; 剂量-响应臂与复用 (σ_b=1.0/2.0 复用 C2/C4 seed 9001; σ_b=0.3 新跑 3 规则): §4。
(j) V3 重写 (基线 ½‖P⊥r‖²、无权 LS、split c=1、birth c* 或裁剪值); V4 限定原候选集; 新增 V16 (第 1 步相同 C_1 与执行函数) 与 V17 (ORACLE 输出不被方法进程读取): §5。
(k) 预算单位明确 (<=4 h 墙钟, <=6 进程, 约 20 CPU-h), 完整 oracle 单元每单元一 job + 检查点, 豁免 20 min 上限, 唯一允许的预算调整及其顺序: §5。
(l) §8 更正 K-a 措辞 (y 空间残差能量非 MSE; 混淆只是 '一致且部分解释'; 披露 Opus 同种子干净 MSE 复核与 K0=6 翻转; gate 只可靠检出约 >=8%) 并更正 research/notes/AS_KA_RESULT_20261105.md, 为 0.503/0.457/0.460 补来源脚本 (research/checks/as_ka_headroom_provenance_20261106.py)。
其它 [注]: ORACLE_y-full 子集改为 6 单元起步 (每族第 1 张 × C1,C4 × seed 9001), 预算允许扩至 12 (Opus 削减顺序第 2 项的初始应用; 与 Opus '12 单元' 预算估计相比更保守)。
[注] §7 近邻阅读状态按 G0 日志 C59-C63 (L4 自读) 更新, 属文档更新, 不改变任何设计/判定。
