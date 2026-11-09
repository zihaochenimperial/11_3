# 一手原文阅读收据 (2026-11-05, run 20261105T212439Z-session-2c28)

方法: 云端 shell 与本机 shell 访问 arxiv.org 均被策略 403 (agent proxy status: connect_rejected, host arxiv.org:443), 未绕过。PDF 页签无文本层。改用 Claude 桌面内置浏览器打开 `https://ar5iv.labs.arxiv.org/html/<arXiv id>` (arXiv 预印本的 HTML 渲染), 用页面脚本抽取 body.innerText 并按节标题切片阅读。性质: 阅读的是预印本渲染文本, 非期刊终稿, 非 PDF 页码; 编号为 arXiv 版编号。抽取文本未整体落盘 (版权/体积), 此处只记录位置与我的转述。

| id | 论文 | URL | 等级 | 实际读到的节/式 | 备注 |
|---|---|---|---|---|---|
| R1 | Tibshirani, Degrees of Freedom and Model Search (Statistica Sinica 2015) | https://ar5iv.labs.arxiv.org/html/1402.1920 | L4 (正文约 74k 字符; 读 §1, §1.2, §1.3, §1.4, §2.1, §2.2 开头, §3, §3.1 开头, §5, §5.1–5.3, §6) | 式(1),(2) df 定义; 式(5) 乐观度; 式(10),(11) sdf; 式(15),(16) sdf 一般定义; Lemma 2,3 (Stein 1981 转述), 式(18),(19); Lemma 5 与式(22); 式(23) 正性充分条件; §6 讨论 | 未读: §3.2–3.3 ridge/lasso, §4 一般 X 的模拟, 附录证明 (仅 A.1 开头). Ye 1998 与 Stein 1981 内容为该文转述 (二手, L3) |
| R2 | Oliveira, Lei, Tibshirani, Unbiased Risk Estimation in the Normal Means Problem via Coupled Bootstrap Techniques | https://ar5iv.labs.arxiv.org/html/2111.09447 | L4 (约 106k 字符; 读 摘要, §1 前部, §1.1, §1.5, §1.6, §2.1, §5.3 开头) | 式(1)-(4); 式(18) Risk_α; 式(19) 抽样; 式(20) CB_α; Prop.1 式(21),(22); Cor.1 (无偏); §3 声明 (SURE 极限); §5.3 图像去噪 (2D fused lasso, CB 与 SURE 最小点接近) | 未读: §1.3 (Efron/Breiman/Ye 比较), §3 证明, §4 偏差方差, §6; 定理编号 (Thm 2) 依附录标题判断, 未逐行核对 |
| R3 | Leiner, Duan, Wasserman, Ramdas, Data fission: splitting a single data point | https://ar5iv.labs.arxiv.org/html/2112.11079 | L4 (约 158k 字符; 读 §2 开头, §2.2 (Gaussian), §2.3 (信息恒等式, Remark 2 开头), §6, §6.1 (trend filtering 流程, Cor.1)) | Gaussian 分解 f=X+τZ, g=X−Z/τ, 方差 (1+τ²)Σ, (1+τ⁻²)Σ, 独立; 信息恒等式 I_X=I_f+E[I_{g|f}]; §6 Cor.1 (选基用 f, 回归用 g); §6.1 末: 已知方差假设, 估计方差情形保证留待未来 | 未读: §3–§5 应用, 附录 |

L1/L2 (未读原文, 不得写成已读): Efron 2004 JASA; Ye 1998 JASA; Stein 1981 Ann.Stat. 原文; Janson–Fithian–Hastie 2015; Tian–Taylor 2018; Rasines–Young 2022; Pang 等 Recorrupted-to-Recorrupted (CVPR 2021); Ramani–Blu–Unser 2008; Athey–Imbens/DML (L3 工具抽取级, 见 G0_reading_log C19/C20)。


## 追加回执 R4–R9（2026-11-05 ~22:15Z；Opus round 9 指出候选简报的 L4 标签缺回执，此处补并**下调**）
等级沿用项目表：L4=自读正文（此处全部为 ar5iv HTML 渲染，非 PDF 页码）；摘要级=L2；"部分 L4"=只读了所列节/式，其余未读，不得据此断言"论文没有做 X"。
| id | 论文 | 等级 | 实际读到 | 不得据此断言 |
|---|---|---|---|---|
| R4 | GaussianImage 2403.08551 | 部分 L4 | 摘要；方法节（累加求和渲染、2D 高斯 8–9 参数、协方差 Cholesky/旋转缩放两种分解，式(1)–(3)） | 其拟合/致密化细节、实验节 |
| R5 | Denoyelle–Duval–Peyré–Soubies SFW 1811.06416 | 部分 L4 | 摘要；§1.1；§4.1–4.2；Def.6–7；Thm 1/3 的位置；式(36) 同形的 BLASSO；Algorithm 1 停止步 | 其核/参数化是否覆盖各向异性；完整证明；实验节细节 |
| R6 | VGNC 2504.14548 | **L2（仅摘要）** | 摘要 | 任何方法/实验细节 |
| R7a | Lockhart 等 1301.7161 | 部分 L4 | 摘要；Thm 1（正交 X 下进入变量协方差统计量的 Exp(1) 极限） | 一般设计的结果、证明 |
| R7b | Taylor–Loftus–Tibshirani 1308.3020 | **L2+（摘要+引言+目录）** | 摘要、引言、目录 | 定理陈述与条件 |
| R8 | Image-GS 2407.01866 | 部分 L4 | 摘要；§3.3 式(6)(7)（梯度引导初始化、误差幅度采样渐进加点）；§4.2–4.3 段落；§5.2；§6 | 其他节；"没有证书/校准停止"仅是对已读节的观察 |
| R9 | Duval–Peyré 1306.6909 | **L3（WebFetch 摘要级）** | 摘要（ar5iv 429 退避） | 非退化条件的具体假设、核类型 |
| —— | Azaïs–De Castro–Mourareau 1706.00679；Butucea–Delmas–Dutfoy–Hardy 2207.00171；Lazzaretti 等 2404.00810；Bénard–Traonmilin–Aujol (EUSIPCO 2022) | **Opus 报告的 L3/摘要级；Sonnet 未读** | —— | 不得写成"已读"；M0 由 Sonnet 精读 |
| —— | ADCG (Boyd 等)；Keriven 等 CL-OMPR；Cai–Wang OMP 噪声停止；discrepancy principle；Shahram–Milanfar | **L1（记忆）** | —— | 不得写成"已读" |


## 追加回执 R10–R11（Sonnet 自读，2026-11-05 ~22:17Z；ar5iv HTML 渲染，非 PDF 页码）
| id | 论文 | 等级 | 实际读到 | 读到的事实（据此可写） | 不得据此断言 |
|---|---|---|---|---|---|
| R10 | Azaïs–De Castro–Mourareau 1706.00679 | 部分 L4（约 10.2 万字符；读 摘要、§1.1–1.3、§2.1、§3.1–3.2、§5 开头与 §5.1 开头） | 摘要；§1.3 贡献；§2.1 Cameron–Martin 型假设；§3.1 设定；§3.2；§5/5.1 Rice 方法开头 | 检验对象是**指标集为一维环面 [0,2π) 的平稳复高斯过程**（相位 θ 另成 2 维环面），**相关函数 Γ 已知**、C² 路径；检验"Z 是否中心化"的全局原假设；基于"连续 LARS"的**前两个结点 λ1,λ2**与 Hessian（S_Rice）；方差未知时可 studentize（Thm 2、8）；Rice 方法的条件分布推导用到平稳性 | §2 声明不要求平稳，但 §5 Rice 检验依赖平稳性；**未读**：Thm 1/4/8 证明、§6 超分辨数值研究的细节；不得说它"不适用于任何高维/非平稳字典"——只能说**读到的定理设定是一维平稳** |
| R11 | Butucea–Delmas–Dutfoy–Hardy 2207.00171 | 部分 L4（约 18 万字符；读 摘要、§1.1、§1.3–1.4、§2 Main Results 含 Thm 2.1、§3.2.3–3.2.4、§4.1 开头、参考文献 [12][41][47]） | 同左 | 特征**先 L2 归一化**（式(2)）；参数集 Θ⊆ℝ **一维区间**；Thm 2.1：调参 κ ≥ C1 σ √Δ_T log τ ⇒ 预测误差 ≤ C0 s κ（以概率 1−C2(|Θ_T|_{d_T}/(τ√log τ) ∨ 1/τ)），**前提是存在插值证书**，证书存在需在**核诱导黎曼度量 d_T** 下参数分离；"平移 + 变尺度"例（§3.2.3）里的尺度 σ̄_T 是**已知的全局尺度（随 T 变化）**，不是每原子未知尺度；§3.2.4 尺度指数模型的未知参数是衰减率 θ（一维）。引言称多维结果以前只覆盖平移不变字典，最一般框架见 [41]=Poon–Keriven–Peyré, *The geometry of off-the-grid compressed sensing*, FoCM 2021 | **未读**：§6–§9 证明与证书构造细节；[41] 与 [12]=Boyer–De Castro–Salmon (2017, "Adapting to unknown noise level in sparse deconvolution") 仅见参考文献条目（L2 级），内容未读 |
**对 Opus 描述的更正**：Opus 把 Butucea 的"translation-with-varying-scale example"当作变尺度原子的证据；我读到的是**已知全局尺度**，未知参数仍是一维。故 Butucea 等**并不覆盖**"每原子未知位置+尺度/各向异性"的多维尺度嵌套字典。**新增近邻**：Poon–Keriven–Peyré 2021（黎曼/Fisher 型核度量、一般字典、多维参数）——候选 C′"几何不变量"在文献中已有对应物，必须 M0 精读。

| R12 | SFW 1811.06416 补读（Sonnet，~22:18Z） | 部分 L4（累计：摘要、§1.1、§1.4、§2.2 开头、§4.1–4.2、Def.6–8、§5.1 前向算子、§5.3.2–5.3.3；共约 11.5 万字符，其余未读） | §1.4：对**正测度**的 Laplace 算子可**无最小分离**稳定反演；§5.1：X⊆ℝ³ 是**分子位置**，PSF 为**固定、可标定**的高斯（散光模型的方差随 z 按标定函数 (45) 变化），即未知量是位置而非每原子自由协方差；§5.3.2：**λ 由训练帧上最大化 Jaccard 指数选定（监督式），不是噪声校准**；§1.1：λ"应适配噪声水平 ‖w‖" | 不得断言 SFW"没有任何噪声校准分析"——§2 引用的稳定性结果把 λ 取为 ‖w‖/C 量级；**未读**：§3、§4.2 证明、附录 |

| R13 | Poon–Keriven–Peyré, *The geometry of off-the-grid compressed sensing* (arXiv 1802.08464; FoCM 2021)（Sonnet，~22:18Z） | 部分 L4（约 19.1 万字符；读 摘要、§1.1–1.3 片段、§2 Examples 全部） | 摘要：以 **Fisher 测地距离**作为参数空间上与重参数化无关的规范度量，覆盖**非平移不变**算子（Laplace 反演、高斯混合估计、单隐层 MLP）；稳定恢复条件=Fisher 距离大于 Rayleigh 分离常数，测量数 ∝ 狄拉克数（至多 log 因子）；§2：高斯混合示例是**已知固定协方差、估计均值与权重**；**"同时恢复均值与协方差矩阵是值得未来研究的方向"（原文），仅描述了一元情形**：x=(m,u) 位置+尺度，L2 归一化原子，核 K0=2uv/(u²+v²)·exp(−(m−n)²/(2(u²+v²)))，度量 g_x=Id₂/(2u²)，Fisher–Rao 距离=Poincaré 半平面距离 | **未读**：§3–§6 证明与条件；不得断言"多元各向异性协方差已被后续工作解决/未解决"——只能说**该论文自述为开放**；是否有后续工作需 M0 检索 |
**对候选 A′/C′ 的含义（事实→推论）**：事实——(i) 一元位置+尺度的 Fisher 几何已知（双曲半平面）；(ii) 该论文明确把多元协方差估计列为未来方向。推论——A′ 的"5 维各向异性字典"落在该论文自述的开放区，**但这只说明理论层面的空白，不说明有人没做/没做出来**；C′ 的"重参数化不变几何量"**不是新对象**（Fisher 度量即是）；Opus 的"尺度嵌套破坏最小分离"论断应放进 Fisher 几何里重述：L2 归一化时嵌套是曲率/双曲几何现象，而非简单失效，**其理论是否迁移仍未核验**。

| R14 | Giard–De Castro–Marteau, *Gaussian Mixture Model with unknown diagonal covariances via continuous sparse regularization*（arXiv 2509.12889；v1 2025-09-16；ar5iv 渲染标注 "version as of August 10, 2026"）（Sonnet，WebSearch 发现→WebFetch 摘要→ar5iv 部分自读） | 部分 L4（约 22.9 万字符；读 摘要、§1.2、§2.2、§7；章节标题已浏览） | 摘要；§1.2 贡献；§2.2 模型与估计量；§7 讨论与开放问题 | BLASSO 同时估计分量数与每分量**未知对角协方差**（参数 x=(t,u)∈ℝ^d×[u_min,∞)^d，u_min 为协方差对角元下界）；核**非平移不变**，通过加权重参数化（W(x)）得归一化核；证书存在需**半距离 d** 下的分离条件，分离随方差上界、稀疏度 s、维度 d、平滑参数 τ 增大（式(17)）；数据是 **i.i.d. 样本 + KDE 平滑**，不是图像上的加性像素噪声；§7 自述：**共享且已知方向的协方差可容易地推广（v1 回执漏记此句，Opus r10 指出）**；**方向各异/未知的一般协方差尚不能处理，Fisher–Rao 度量"似乎难以使用"，可能需要替代度量**；"我们不知道如何在整个测度空间上数值求解 (Pκ)"；§7 把 SFW（Denoyelle 等）与 CPGD（Chizat 2022）列为现有算法、引用 Hardy 2023（K-稀疏测度上的参数化非凸 BLASSO），**拟作未来工作的是适配 CPGD**（回执原写"SFW 与 CPGD 的适配留作未来工作"系转述不准，已更正）；分离条件不允许 Δ→0 | **未读**：§3–§6 证明与定理细节；不得断言其对图像渲染/加性噪声模型"不适用"，只能说读到的设定是 i.i.d. 密度估计 |
**对候选 A′ 的含义（事实→推论）**：事实——2025 年已有**每分量未知（对角）协方差**的 BLASSO 证书理论；方向未知（旋转）协方差被作者自述为开放；算法与噪声校准 λ 不在该文范围。推论——A′ 在**理论**上的白区缩到"旋转各向异性 + 加性噪声图像模型"，而作者自称这是难题（Fisher–Rao 不好用）；硕士级工作做不了这套理论。A′ 的可行贡献只可能在**经验/算法层**（噪声校准的证书停止在已知-σ 平凡规则之上是否非劣），这仍是**低到中**原创度；"尺度嵌套"在该文中通过 u_min 下界与分离条件处理，Opus 的"理论不迁移"论断需据此**降级为：对对角情形已有处理方案，旋转情形开放**。

| R15 | Shafie–Sigal–Siegmund–Worsley, *Rotation space random fields with an application to fMRI data*（McGill 作者页标 Ann. Statist. 31:1732–1771，页内写 (2002)；Opus 写 2003）（Sonnet，~22:25Z） | **L3（WebFetch 摘要级）** | 摘要页 | 把 Siegmund–Worsley 1995 的尺度空间结果（未知位置与平滑尺度的信号检测，期望 Euler 特征/管法近似最大值零分布）推广到二维**旋转空间**（对滤波器旋转与尺度取最大）；应用 fMRI | 滤波器是否为全协方差各向异性高斯、是否给出显式尾概率公式、能否直接套用到贪心 birth 后残差：**未读，不得断言**；年份/页码页内外不一致，需核 |
**版本记录（对 R14）**：arXiv 列表（WebFetch）显示首次提交 2025-09-16、v3 2026-01-08；我读的 ar5iv 渲染标注"version as of August 10, 2026"，**无法确认所读为第几版**；v3 摘要仍只谈对角协方差。
