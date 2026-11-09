# TRN 合同 v1.1→v1.2 对照 (2026-11-08; Opus v1.1 差异项确认 C1–C8/S1–S4)
C1 §3/§4: "上一状态的求解"在同状态研究中 = (θ_{t−1},κ_{t−1}) 上 D0 冷启动 oracle 停于 ρ=0.1; D0w x0 取其解; 闭环 D2/D3p 收割本臂上一外层被接受 trial 的实际 CG; 状态取自 trn_loop 日志; trn_study 已删除 GEO ref_states (单测断言)。
C2 §7 G-A: B* 每个规模只选一个 (M 上 12 图×{C1,C4} 合并 W 中位数 argmin, 平局 D0<D0w<D0b、larger ε_r), L 继承 M; B* 只用闭环 W; 同状态"最强确定性对照"是另一对象, 报告 κ 分布与二者不同臂比例。
C3 §6: 所有臂 (含方法臂) 只调 (κ0,f,ε_r), 同网格, C1/C4 合并每臂一个配置; 方法臂 k/n_tr/r 取同状态 dev-sel 选择。
C4 §6: 同 θ 回溯 trial 间任何臂不得复用解/子空间/Lanczos (D0w 仅首 trial); D2b 须先实现并入对照集否则不得冻结。
C5 §6: F_ref = min{B* 长跑 100 外层末值, D0(ε_r=1e-3, B* κ0,f) 长跑 100 外层末值}; "F_ref 未收敛"标记与剔除读数; PSNR 在各臂首次达标迭代比较; 终值 F<F_ref 比例。(实现细节补充: 选 B* 用 F_ref^sel=三基线臂长跑末值最小值, 仅选 B* 用; 此后一切评估用 C5 的 F_ref。)
C6 §2/§8: 门控 (4) 所有已加载 src/trn_*.py 模块 sha 须与 FREEZE_RECORD "MODULE_SHA256" 登记相符; 门控测试用哑索引 9999 (不合成 321–344 任何图)。
C7 §3/§8: M 每轨迹≤12 状态等距, 图像/条件固定顺序; 任一阶段超 CPU 小时 → INCONCLUSIVE, 终态表按失败分支, 不得用已完成子集判定。
C8 代码: D0w x0 成本只记一次 (删 x0_cost), 单测 (x0=0 时 W=D0; 非零 x0 恰计一次 H x0)。
S1 GEO/LMD 稠密直解同 150 外层/W_cap, 标注冻结配置未调参; S2 报 B* κ 分布; S3 静态检查方法侧/分析器不绕过门控 (clean_image_trn/_tile/rng_of); S4 transport_wcost_rhs 改为每列 F_matvec(nnz_{t−1})+2F_A+F_matvec(nnz_t) (已改, 单测)。
代码附带新增: study_state 加 D46_r{r} 臂 (G-B 主读数: D4λ + r 个 oracle 修补方向, 成本 0); 聚合/分析器 experiments/trn_same_state_reduce.py; trn_s0.py 加 fref 阶段、bstar 与平局规则 (W_median, 删失率, 终值差, D0<D0w<D0b, larger ε_r)。单测 13 项通过。
