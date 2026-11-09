# CF0 负结果技术记录 v2 (交叉拟合 / honest 位置转移的 Gaussian birth 选择; 玩具 64x64 合成图)
状态: 定稿 v2 (2026-11-05T21:25Z; 已吸收真实 Opus round 8 的范围限定与更正, 原文 research/notes/OPUS_REVIEW_CF0_RESULT_20261105.md)。作者 Sonnet5.5 (run 20261105T175811Z-session-6e38)。**0 个已验证创新**; 本记录不声称原创、不声称真实图像泛化、不声称 GPU 收益。

## 1. 问题与设计
问题: 把"选 birth 位置所用的信息"与"拟合参数所用的信息"分开 (Gaussian data fission 副本 y_f=y+τz, y_g=y−z/τ; τ∈{1,2,4}), 能否在匹配全预算下降低自适应 2D 高斯生长 (K0=24 + 3 轮 x 8 births, 固定 K=48) 的 oracle 风险?
臂: RAWy (基线); XFERg(τ) (位置取自 y_f, 在 y_g 上拟合 = honest 样本分裂); XAVG(1) (角色互换并平均, K=96, DML 意义交叉拟合); 门内竞争者 NS(τ) (随机化选择: 同位置在完整 y 上拟合)、RANDy/RANDens2 (近随机位置)、RAWens2、NSens、XAVGctrl、RAWcv (fission-CV 选停止轮数 R*)。估计量 NU = 逐图相对风险差 (图等权), 图 bootstrap (B=10000), GO/STOP 先验固定。
合同 contracts/CF0_CONTRACT.md (sha256 11d1fc819f5f11ca7814a5a857cee5b2fa9d34508d8d179883449447306dc12c); 冻结清单 sha256 963b39bd1a53204570785b2ef7a859377e60d54cf53dfc5f7c95d2370fc4e93e (13 文件); 冻结 2026-11-05T18:38:48Z。门控: Opus round 6 REVISE (FAIL-0010) -> round 7 FREEZE-AFTER-CHANGES (FAIL-0012) -> round 8 裁决 A (本结果)。
披露: (i) 两次查看各用 α/2 是我相对 Opus 编辑 4 的更保守偏差, 未再送审 (DECISIONS 18:35Z); (ii) 本线未触碰保留确认集 E41-58; (iii) G0 近邻阅读多为摘要级; honest trees (Athey-Imbens) 与 DML 已由 WebFetch 全文摘要核验 (G0 日志 C19/C20), 其余先验 (GDF/search df/discrepancy principle/Luxar 等) 为 Opus 记忆或线索, 不得作新颖性依据; (iv) meta.json cfg 中 entropy=20261105/M=256/S_grid 为继承自 F0Config 的未用字段 (已 grep 核对); (v) 预注册预测区间很宽, 仅能说"未被证伪、信息量低"。

## 2. 数据与有效性
pilot p1 (E15-E18, 8 抽样, 32 单元): PILOT_OK, V0-V8 全 true, wall 577 s (host job j60, manifest 摘要 872dc35e…)。dev d1 (E21-E38, 32 抽样, 576 单元, host job j62): wall 7992 s, n_fit_equiv 10800 (=576x18.75), replay_ok=true, rawy_pipeline_ok=true; 冻结分析器 (host job j63) V0-V8 全 true; manifest 摘要 ec5a028eef…。我独立复算 (只读 dev 表) 的 XFERg(1)/XFERg(4)/XAVG(1)/RAWcv vs RAWy 与分析器逐位一致; Opus 独立读 dev 表复核 (未读 pilot 表)。

## 3. 结果 (verdict = STOP; FAIL-0013 + 附记 A1; 类别 scientific no-go; Opus 裁决有效且稳健)
| 候选 | NU vs RAWy (pooled, 图等权) | 其他 |
|---|---|---|
| XFERg(1) | −71.0% (18/18 图为负) | 对 NS(1) −71.6%, RANDy −61.6%, RAWcv −194.9% |
| XFERg(2) | −20.1% (全负) | 对 NS(2) −17.8%, RANDy −11.4% |
| XFERg(4) | −10.7% (D1 +0.3%, D2 −9.7%, D3 −22.6%; 4/18 图为正) | 对 NS(4) −4.9%, RANDy −1.7% |
| XAVG(1) | +1.1% (下界 −0.9%; 9/18 图为正) | 对 RAWens2 −23.1%, NSens −20.7%, RANDens2 −22.6%, RAWcv −63.4%; 对 XAVGctrl +2.5% (下界 −0.2%) |
全部 4 个候选 STOP_pass (min_c UB_c < +1%); GO 无。**决定性控制 NS ≈ 0**: NS vs RAWy 为 −0.2% (τ=1)、−2.4% (τ=2)、−5.7% (τ=4): 同一组 honest 位置在完整 y 上拟合 (无信息损失) 也无收益; 这比"XFERg 因拟合副本噪声而信息损失"更强。信息损失 RAWg vs RAWy: τ=1 −77.8%, τ=2 −19.3%, τ=4 −4.4%; 出生高斯初始位置经优化后平均位移 3-4 px。
稳健性 (Opus + 我): 去掉 RAWcv 后每个 XFERg 候选对 RAWy 单独仍 STOP (UB_stop −50%/−17%/−5%); XAVG 对匹配 K=96 的 RAWens2/NSens/RANDens2 仍 STOP (UB −17.6%/−13.0%/−7.8%), 且 XAVG 约 4.5 拟合 vs RAWens2 的 2 拟合 (成本比较对 XAVG 有利仍输); D3 (growth 有益的唯一类型) 上 XAVG vs RAWens2 −12.2% (0/6 图为正), XAVG vs XAVGctrl −2.4% (1/6), XFERg(4) vs RAWg(4) −21.8% (0/6)。
**范围 (必读)**: 判定成立于 "固定 K=48 + fission 信息核算 + 本合同"; **未采样"接近最优 K 时的 honest 位置"**: 固定 K=48 对 D1/D2 过生长、对 D3 欠生长。该 no-go 不外推到"最优 K 下的 honest 位置"。

## 4. 绝对风险 (各型图均值, 与相对指标并列; Nσ0² = 26.2)
| 臂 | D1 | D2 | D3 |
|---|---|---|---|
| RAWy (K=48) | 2.508 | 3.405 | 20.012 |
| RAWy_R0 (K=24, 不生长) | 1.269 | 2.293 | 53.155 |
| RAWy_R4 (K=56) | 3.030 | 3.904 | 17.012 |
| RAWcv (fission-CV 选 R*) | 1.116 | 2.290 | 17.147 |
| RANDy / RANDens2 | 2.364 / 1.715 | 3.706 / 2.631 | 24.626 / 20.648 |
| RAWens2 / NSens | 1.972 / 1.878 | 2.636 / 2.776 | 17.096 / 18.178 |
| XAVGctrl / XAVG | 2.674 / 2.464 | 3.553 / 3.482 | 18.503 / 19.038 |
| NS(1) / NS(4) | 2.403 / 2.338 | 3.460 / 3.552 | 20.520 / 23.563 |
| XFERg(1) / XFERg(2) / XFERg(4) | 4.905 / 2.975 / 2.502 | 6.617 / 4.273 / 3.735 | 24.247 / 22.994 / 24.172 |
D1/D2 绝对风险仅约 1-4, 小分母放大了相对差 (如 −71%、−195%); D3 风险约 17-53。

## 5. 报告-only 线索 (非确认; 无多重校正; 均被先验覆盖, Opus 定性)
- **K 轴** (RAWcv vs RAWy 图等权 +33.2%; D1 +54.5%, D2 +32.8%, D3 +12.4%; oracle-R +36.0%): 即偏差-方差权衡 (简单图需更少成分)。oracle R 直方图: D1 {0:122, 1:69, 2:1}, D2 {0:131, 1:56, 2:5}, D3 {3:11, 4:181}; CV R*: D1 {0:179,1:13}, D2 {0:191,1:1}, D3 {1:2,2:6,3:17,4:167}。含义: 平均而言 D1/D2 不生长最好, 逐单元约 1/3 偏好少量生长, D3 从不偏好不生长。局限: fission-CV 在 2σ0² 副本上校准而偏早停 (D1/D2 oracle 选 R=1 者 125/384 单元, CV 仅 14); D3 触及 R_MAX=4 (CV 167/192, oracle 181/192), 增益被低估。最近先验 (Opus 记忆, 未核验): sequential/hold-out CV 停止、差异原则、Mallows Cp/SURE 与 search df/GDF、Luxar blind-spot K; 且与 F0/H2 (FAIL-0001) 重叠。
- **等噪声选择效应** XFERg vs RAWg: τ=1 +2.8% (D1 +8.0%, 6/6 图为正; D2 +3.0%; D3 −2.5%); τ=2 −1.2%; τ=4 −6.4% (D1 +6.6%, D2 −4.0%, D3 −21.8%); 位置来源隔离 XAVG vs XAVGctrl: +2.5% (D1 +8.0% 6/6, D2 +2.0% 6/6, D3 −2.4% 1/6)。Opus 读数: 这跟随过拟合区间而非"诚实性" (RANDy 无选择在 D1 也 +5.6%, NS 在 D1 +4.2%), 最简解释为"较不贪心的放置过拟合更少"(随机化即正则化: Tian-Taylor, RandOMP); 停止规则的效应约大 5 倍且在 D3 反号。
- 集成: RAWens2/NSens/RANDens2 vs RAWy +19.4%/+17.5%/+16.5%。

## 6. 结论与边界 (如实)
在固定 K=48 与 fission 信息核算下, honest 位置转移与角色互换平均的交叉拟合都不优于匹配基线/集成基线; 位置选择不是独立杠杆 (NS≈0 为决定性控制)。更强的杠杆是 K 轴 (何时停止生长) 与简单集成, 二者均为已知先验方向, 本记录不据此宣称创新。保留全部失败 (FAIL-0001…0013)、数据与哈希。不复活该线 (复活须新合同 + 新 G0 + 真实 Opus 门)。若真人仍要 K 轴研究: 须显式批准为"基准/经验笔记 (非创新)", 先做新 G0 (OMP 停止、GDF/SURE for greedy、Luxar), 入门基线至少含 best-fixed-R (在独立图上选)、Cp/SURE (σ0 已知; 朴素 + search df)、差异原则、fission-CV (τ=1 与 τ 匹配)、oracle-R、R_MAX≥6, 新图 k≥61 与新 seed; E41-58 封存 (除非新合同预注册为其确认集)。Opus 诚实概率估计: K 轴比较产出 "某规则胜 Cp/差异原则/best-fixed-R" 的 GO 约 20-30%; 可称新 <5%; 超出研讨会/技术笔记级别的发表 <3%。
## 7. 文件索引
合同/清单: contracts/CF0_CONTRACT.md, CF0_CONTRACT.sha256, CF0_FROZEN_FILES.sha256, CF0_FREEZE_RECORD.txt; 代码: experiments/cf_run.py, cf_analyze.py, src/cf_fit.py, tests/test_cf_units.py, test_cf_analyze.py; 数据: outputs/CF0-pilot-p1, outputs/CF0-dev-d1 (含 analysis.json, manifest.json); 门控原文: research/notes/OPUS_REVIEW_CF0_DESIGN_20261105.md, OPUS_REVIEW_CF0_CONTRACT_20261105.md, OPUS_REVIEW_CF0_RESULT_20261105.md; 失败日志: memory/FAILURES.md (FAIL-0001…0013 + 附记 A1); G0: research/nearest_work/G0_CF_BIRTH_NEAREST_WORK_20261105.md, research/notes/G0_reading_log_20261105.md。
