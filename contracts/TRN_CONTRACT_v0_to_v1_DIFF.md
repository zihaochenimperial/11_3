# TRN 合同 v0→v1 对照 (吸收 Opus REVISE 必改项; 2026-11-08)
M1 Λ_A=‖A‖₂²/σ² (v0 误写 ‖A‖₂⁴); Δq 含 η vs 冻结 _accept 的 pred 不含 η, 分开报告 — v1 §1。
M2 秩亏: 全部量改在 Jacobi 广义谱 Hv=λDv (D=diag JᵀJ, τ=1e-8·λ_max), δ*_τ 截断; D1/D1e 只取 λ>τ; deflation 用 A-DEF2/初值投影、HU 一次计算; 绝对地板 max(ρ‖δ*‖², 2e-6F_t); κ 用被接受 trial 的 κ (重放, 不用 κ/3); GEO 参考用 rcond 截断 SVD 故 δ*_GEO≠H†g — v1 §1/§3/§4/§5。
M3 输运热启动 Z0=U_{t−1}, n_tr∈{0,3,8} (n_tr=0≡D2), 报告 LS 残差比; D4 拆 D4λ/D4e, G-B 主读数 D4λ+D6; 隔离链按迭代数 — v1 §4。
M4 新增对照 D0w (热启动)、D0c (解析块, 须先验证)、D0s (固定粗空间紧缩); D2 重命名为 Ritz 回收型 deflated CG (Saad 2000; Parks 2006); 最强对照 = dev 上预注册网格取最优; 稠密 GEO/LMD 直解入闭环 — v1 §4/§6。
M5 S0=D0b 等闭环分账仅用于 G-A; Amdahl 一致性 f≥(1−1/R)/(1−1/s); G-A=f_iter≥0.5 且每外层 H 乘积中位数≥24 (删 "f<0.3"); G-B CI 下界在 [1.3,1.5) → 不可达 G-E → MC; 阈值先验固定, dev 只选 k,r,n_tr,ε_r; dev 分 dev-sel 301–312 / dev-chk 313–320; confirm-det 321–344 一次; TRN-5 confirm 401–424 预留封存; 终态表 — v1 §2/§5/§7。
建议项: D6n (cos=0.7) 入 G-D(iii); 聚合=轨迹ΣW 比→图像级中位数→图像簇 bootstrap, dev 符号计数 ≥9/12; 画质等价用超额形式 F−F_ref≤1e-3(F0−F_ref) + 单侧 PSNR; 删失>10% 失败; 回退触发仅方法侧廉价量并计已花成本; MC 触发 f_asm (v1 以装配/几何访问份额, 原 f_meas); 回退/回溯复用作 D2b; confirm 加载器查 TRN_FREEZE_RECORD + CONFIRM_UNSEALED; 干跑仅 dev/ladder; 输运恒等单测; L 规模裁剪 — v1 §2–§8。
本次起草新增 (非 Opus 要求): 主 ρ 由 0.01/1e-4 改为 **0.1** (依据 dev 图 301 一次性探索, 见 TRN_PILOT_DEV_NOTE); 披露探索; MC 路线在 G-A 失败且 f_asm≥0.5 时触发 (原 f_meas 名称改 f_asm, 含 c_jac+装配, 以与 Opus 建议的 f_meas 同义但口径明确)。
