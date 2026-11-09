# TRN 合同 v1→v1.1 对照 (2026-11-08)
A. Opus v1 复审 N1–N9 逐条: N1 (§4 D2 收割源=上一状态 D0 在主 ρ=0.1 的实际求解; 不得额外加长) ✓; N2 (§5 主张限 ρ=0.1; 剔除 301 的稳健读数, 结论不同→INCONCLUSIVE) ✓; N3 (§7 G-B 数据/统计: M 12 图符号≥9/12+BCa 下界, L 4 张图 302–305×C1,C4 仅中位数+≥3/4, dev-chk 复核, B✓/B-marginal/B✗ 判定) ✓; N4 (G-E-det 数值门限 1.2 / BCa 下界>1.0, 墙钟方向) ✓; N5 (终态表按 A→B→(C,D) 顺序, 重叠/缺失分支消除; §3 末句) ✓; N6 (D0c: 冻结前未实现→FREEZE_RECORD 声明, 主张限定; 不得冻结后增删对照) ✓ (选"未实现"分支); N7 (G-A 基线 = {D0,D0w,D0b}×ε_r∈{1e-1,1e-2,1e-3} 调参后 W 中位数最小; D0c 因未实现而不在集合) ✓; N8 (confirm 门控代码+单测: 运行时分析器 sha、CONFIRM_CONSUMED 单次、noisy 门控、401–424 无条件封存、313–320 合法、seed_keys 全覆盖; dense() 已改广义谱) ✓ (代码与 9 项单测已通过, 已同步设备 src/ 与 tests/); N9 (CPU 小时上限与执行顺序: M 上 B✗ 即终止) ✓。建议项 S1 (先验盈亏式), S2 (严格口径入闸), S3 (MC 附录自带 Amdahl 门/允许 STOP), S4 (活动集不一致比例), S5 (r_eff 口径变更) 均已写入。
B. 本方新发现并修正 (FAIL-0031), 需 Opus 对差异项确认:
 B1 状态源: v1 §3 用冻结 GEO 精确步轨迹+重放 κ; 重放后发现 GEO 路径 κ 为 O(1)–O(500), 内层条件好 (PCG-J 达 ρ=0.1 仅 3–9 次), 而 matrix-free 闭环 (κ0≤1e-2, 回溯) 的 κ 轨迹完全不同 (S/C4≈0.03–0.7, M/C4≈0.1–0.8, M/C1≈2–7, 每外层含 25–100 次 CG)。v1.1 改为用 B* 闭环轨迹 (含被接受 trial 的 κ 与实际 CG) 作同状态问题来源。
 B2 F_ref: v1 §6 用 GEO 40 次末值; 冒烟显示 C1 上 GEO 末值≈1.0e4 而 matrix-free 可达≈1.4e3, 作参照退化。v1.1 改为 B* 长跑 100 外层末值 (与被测方法无关), GEO 不再作参照。
 B3 主 ρ=0.1 的理由改为先验 (inexact-Newton 常用宽松水平), pilot 依据删除。
 B4 新增 §6 调参协议 (两阶段网格, 调参集 301–306×C1,C4@M), §8 CPU 小时上限, D0w 仅第一 trial 热启动 (冒烟显示回溯 trial 也热启动会使 D0w 在 C4 提前停滞), D2b 暂不含。
C. 代码状态 (设备 D:\Gaussian\src): trn_core/trn_gen/trn_flops/trn_loop/trn_study + tests/test_trn_core.py (9 项通过)。冻结文件未改 (geo_core e92732df…15fbc4, geo_flops 076a0a61…bd7d)。
