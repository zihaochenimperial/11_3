# AS 阶段阅读回执 (run 20261105T230727Z-session-74ee, 2026-11-05T23:32Z)
通道: 内置浏览器 (mcp__remote-devices__Claude_Browser__*) 打开 arxiv.org/html 或 ar5iv.arxiv.org, 用 javascript_tool 取 document.body.innerText 切片 = 页面原文文本 (非模型摘要), 属 L4(含节/式号)。shell 到 arXiv 403 未绕过。WebFetch 摘要=L3, 仅标题/搜索片段=L2, 记忆=L1。
| 回执 | 对象 | 读到的位置 | 备注 |
|---|---|---|---|
| R-AS1 | PUP-3DGS 2406.10219v3 | §4 全部 (式5-10), §7, 附录 A.6, A.7; 页面 55k 字符, 其余节(实验/消融/A.1)未读 | 证实: 块对角+log-det+(x,s)+4x4 patch+N×36 内存 |
| R-AS2 | SteepGS 2505.05587v1 | §4.1-4.4 (定理1,2; 式5-7), §6; 页面 90k 字符, 附录 C 证明未读, §5 实验未读 | 证实: 逐点 S^(i), λ_min<0, m=2, ±v_min; §4.4 '无交叉项'声明 |
| R-AS3 | IRGNM 自适应离散化 1707.07589v1 | 摘要, §1 开头, §3 开头(式30-33), §6; §2 收敛证明/§4-5 未读 | PDE 网格 DWR 估计器 |
| R-AS4 | ADCG 1507.01562 | 摘要, §1 开头, §3 算法1-3, §4 开头, §6.1 开头; §5 理论, §6.2-6.3 未读 | Alg.3 选源=∇ℓ 相关(OMP型), 回拟=全体联合 |
| R-AS5 | OMP/OLS 1111.0522 | 摘要, §II-B, §II-C; §III 恢复条件/§IV 实验/附录未读 | OLS 式(2): argmax⟨r,b̃⟩² |
| R-AS6 | Dehaze-GaussianImage / LL-GaussianImage / Unified Loss-Aware DC | WebFetch 摘要 (L3) | 正文未读 |
| R-AS7 | 3DGS-LM 2409.12892v2 | §1 引言段, §3.2 式3-5 (内置浏览器 DOM 原文, 2026-11-05T23:43Z); 页面 68k 字符, §3.3 CUDA 并行/§4 实验大部分未读 | 全参数联合正规方程+matrix-free PCG |
未取得/待办: GaussianSR 2407.18046, GSASR 2501.06838 的 densify 判据; 2DGS 逆问题其他工作; Unified Loss-Aware DC 正文; SIREN/WIRE 去模糊实现; 经典 OLS 原始文献 (Chen-Billings-Luo) 与快速递推实现; 稀疏 Gauss-Newton/Schur 成本文献; 联合谱正则化(TSVD/Tikhonov-GN) 经典教材级原文。
