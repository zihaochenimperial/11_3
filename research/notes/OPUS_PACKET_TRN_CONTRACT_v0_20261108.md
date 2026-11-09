# Opus 科学门 packet — TRN 合同候选 v0 (2026-11-08)
你是真实 Opus 5.5 科学门 (只读审查, 不改任何文件)。请先说明自报模型名。审对象: contracts/TRN_CONTRACT_CANDIDATE_v0.md (D:/Gaussian = 设备 VM 的 ~/mnt/Gaussian; 经 mcp__remote-devices__device_bash 读取, 只读)。
背景材料 (按需读): runs/codex-monitor/20261108-research-direction-review/{CLAUDE_TRANSPORT_AUTO_HANDOFF_ZH,ASTRA_FRESH_REVIEW_ZH,MECHANISM_DECK,PRIMARY_SOURCE_MATRIX_ZH}.md; 冻结代码 src/geo_core.py (重点 _accept 195-210, _iter_pcg/_iter_pcgd/_cg 355-415, Op/Prob, solve 510-548), src/geo_flops.py, src/geo_gen.py; research/notes/GEO_L_RESULT_20261108.md; memory/FAILURES.md 末段 (FAIL-0026..0030, 尤其 FAIL-0029 干跑暴露正式留出图的教训)。
范围声明: 只审合同的科学/数学/公平性/数据边界/成本判据; 此为 CPU 小规模首合同; 学习修补网络 (TRN-5) 的合同附录以后另审。
请逐条回答 (给出 具体、可执行 的修改, 不要泛泛):
Q1 数学: H_t=M_tᵀM_t、g_t、Δq、能量 e_i=(v_iᵀg)²/λ_i、同质量准则 ‖e‖_H²≤ρ‖δ*‖_H²、deflated PCG 在秩亏 H (活动集冻结) 下的定义是否正确/自洽? D1e 的"有效方向"定义是否合理? 输运 U'=argmin‖M_tZ−M_{t−1}U‖_F 是否合理 (为何/何时有效、何时退化), D3x/D3p/D4 的区分是否有效隔离"提取误差 vs 映射误差 vs 实现成本"?
Q2 公平性: arm 集 (D0,D0b,D1,D1e,D2,D3x,D3p,D4,D5,D6) 是否缺少关键强对照 (例如 GCRO-DR/harmonic Ritz、AMG/两层预条件、解析近场块预条件、冷启动 vs 热启动初值 x0=上一步 δ)? 同秩/同预算/同调参网格是否真公平? D6 oracle 是否会让 G-D 虚假通过; D5 共判是否足够?
Q3 Amdahl 与成本记账: f_iter、S_max、W 口径 (A-施加、J 乘、投影、RR、LS 输运迭代) 是否完整、无重复/遗漏; 小 N (32-96) 的 numpy 解释器开销是否使"以 W 为准、墙钟方向一致"的做法站得住; 阈值 G-A (f_iter≥0.5, CG 迭代≥10) 合理否?
Q4 闸门: G-A…G-E 与分支 (→MC) 的逻辑是否闭合、可证伪、无多重比较或事后选择空间 (k、r、n_tr 的选择规则); 阈值 1.5/1.3/1.2/20%/50% 如何预注册最稳妥 (先验固定 vs dev 校准); CI/自助法设计 (图像簇) 是否合适。
Q5 画质/目标等价: F ≤ F_ref_final(1+1e-3) 且 PSNR 差 ≤0.05 dB 是否合适; 对未达标/删失的处理是否诚实。
Q6 数据与泄漏: dev 301-312 / confirm 321-344 (seeds 9411,9412) / train 351-398 / 核族 KF-A,KF-B 的隔离与图像生成配方复用 (as_gen 同族配方, 新 tag 段) 是否足够; 需不需要更多/更少图像; 干跑规则是否足以避免 FAIL-0029 重演。
Q7 失效模式: 秩突变、近重合原语、活动集、κ 变化对输运与回退设计的影响; "回退计入分母"是否足够; 是否有未被合同覆盖的致命失效 (如 H 谱在小 λ 下近奇异使 oracle 能量度量被噪声方向支配)。
Q8 MC 备选路线: 触发规则是否合理, 是否有更好的预注册判据区分"算子构建/应用成本主导"与"迭代数主导"。
Q9 可行性: 在 CPU/8GB、1-2 天活动时间内按本合同能否完成 dev 阶段 (S0 分账 + 同状态 oracle)? 哪些部分应砍/延后?
输出格式: (1) 自报模型; (2) 总体裁决 ACCEPT / ACCEPT-WITH-CHANGES / REVISE / REJECT; (3) 必改项 (编号, 引用合同章节, 给出替换文本或具体规则); (4) 建议项; (5) 你自己核对过的数学/代码事实 (标明读了哪些文件的哪几行); (6) 你不确定、需要实测的点。篇幅 ≤ 1800 汉字等价, 但数学要具体。
