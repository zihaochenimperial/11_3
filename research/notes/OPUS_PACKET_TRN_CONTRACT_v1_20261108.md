# Opus 科学门 packet — TRN 合同候选 v1 轻量复审 (2026-11-08)
你是真实 Opus 5.5 科学门 (只读, 不改任何文件)。先自报模型名。D:/Gaussian = 设备 VM 的 ~/mnt/Gaussian (经 mcp__remote-devices__device_bash 只读读取; 这是一个只读审查, 不得写文件, 不得执行实验)。
审对象: contracts/TRN_CONTRACT_CANDIDATE_v1.md; 对照: contracts/TRN_CONTRACT_v0_to_v1_DIFF.md、你(上一轮)的审查原文 research/notes/OPUS_REVIEW_TRN_CONTRACT_v0_20261108.md、dev 探索披露 research/notes/TRN_PILOT_DEV_NOTE_20261108.md。冻结代码 src/geo_core.py 等只读核对 (src/trn_core.py、src/trn_gen.py 为候选代码, 可读)。
任务 (轻量, ≤1200 汉字等价): 
R1 逐项核对 M1–M5 是否被 v1 正确、可执行地吸收 (每项给 ✓/部分/✗ 与一句话理由; 不要重复上轮已吸收的内容)。
R2 v1 新引入/仍存的错误或矛盾 (数学、阈值互相不一致、预注册漏洞、分析自由度、数据边界)。特别: (a) 主 ρ 改为 0.1 是否合理, 该改动由 dev 图 301 一次性探索驱动, 是否构成"按结果调阈值"; 如何披露/限定最稳妥? (b) Amdahl 一致性、G-A 的 24 次 H 乘积门限在 ρ=0.1 下是否仍有意义 (pilot: M 规模 PCG-J 达 ρ=0.1 约 49–63 次迭代); (c) D0c 解析块的"须先验证否则丢弃"规则是否产生事后选择; (d) §3 κ 重放法与 §1 同状态定义是否自洽; (e) 终态表是否覆盖全部 (A,B,C,D) 组合、有无不可达/重叠分支; (f) confirm 解锁条件三要素 (环境变量 + 分析器 sha + CONFIRM_UNSEALED 行) 是否足以避免 FAIL-0029 重演。
R3 pilot 提示 M 规模理想 deflation 迭代增益仅约 1.0–1.3× 而块 Jacobi 严格构建成本约为 PCG-J 到 ρ=0.1 总成本的 7×: 在这一先兆下, v1 的 TRN-4 实验顺序是否应调整 (例如先做廉价的 S0/G-A 与 D6 理想上界并按终态表尽早停止, 以免过度投入), 是否有任何必须在冻结前补的预注册项; 并明确你对 "按预注册结果可能 STOP/转 MC, 且这是可接受的科学结论" 的看法。
R4 裁决: ACCEPT (可冻结) / ACCEPT-WITH-CHANGES (列出必改的具体替换文本, 改完即可冻结无需再审) / REVISE (需再审)。
格式: (1) 自报模型 (2) 裁决 (3) 必改项 (编号+章节+替换文本) (4) 建议项 (5) 你核对过的文件/行。
