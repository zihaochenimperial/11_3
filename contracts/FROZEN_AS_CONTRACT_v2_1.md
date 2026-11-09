# AS 合同 v2.1 冻结记录 (FROZEN 2026-11-06T00:13Z)
冻结者: Sonnet 5.5 主会话 (run 20261105T230727Z-session-74ee)。科学门: 真实 Opus 5.5 两次 (v1: run 20261105T233836Z-opus-review-b1b8 = REVISE-AND-RESUBMIT; v2: run 20261106T000215Z-opus-review-b52f = FREEZE-WITH-EDITS; 服务模型仅有自报 + 任务日志 message.model=claude-opus-5-5, 未独立证实)。12 项编辑已逐项应用并记录 diff (contracts/AS_CONTRACT_v2_to_v2_1_DIFF.md); Opus 称无需再审。
**冻结对象**: contracts/AS_CONTRACT_CANDIDATE_v2_1.md (sha256 见下表; 冻结后不得修改文字; 任何变更须新版本 + 新 Opus 门 + 新冻结记录)。
**状态**: proposed; 0 已验证贡献; 本合同是预注册 kill test, GO 先验约 5-10% (Opus 判断); 结果只适用于合成 32x32、本候选族、已知核。
**尚未冻结 (须在运行 S2 前以追加方式补入本记录, 追加后即冻结)**: (1) 图像生成器与全部实验代码 (src/as_*.py, experiments/as_*.py) 的 sha256; (2) 冻结分析器 experiments/as_analyze.py 的 sha256; (3) S0 单测全通过记录。S1 Pilot 只读时间与 V 闸门, 不读质量结果。
**边界**: E41-58 封存不动; F0/H2 与 CF0 STOP 不复活; 不使用 F0/CF0 旧图; 无 GPU/付费云; 所有产物在 D:/Gaussian。

## 冻结时文件哈希
- `contracts/AS_CONTRACT_CANDIDATE_v1.md` sha256 f9708aa35d03fdfafccbf1a25b0b8ba42e64e2e65ba2513f9df13020e244e05f
- `contracts/AS_CONTRACT_CANDIDATE_v2.md` sha256 b92e7dad82c21aa4be61574c6fdca014b9cb6ad5b795d1423a80eee2b3c1b251
- `contracts/AS_CONTRACT_CANDIDATE_v2_1.md` sha256 4701d226441691af372235932cc8ff737186d83fd134c241c0ca492d6af45dcf
- `contracts/AS_CONTRACT_v2_to_v2_1_DIFF.md` sha256 e9cc5654f61c934870adbf5a21fb138cde592162137427bc22909a86cd06c441
- `research/notes/OPUS_REVIEW_AS_CONTRACT1_20261105.md` sha256 68d68c150117b467516ee78eced10d94a66748c7effc7ae7844d21b61380cb3c
- `research/notes/OPUS_REVIEW_AS_CONTRACT2_20261106.md` sha256 e6b9586c4622627257023007bf3460212a92f4d5afe524b72f20fc5cd5aba851
- `research/notes/AS_KA_RESULT_20261105.md` sha256 7948bb87d8fb3b588793d1b15db46c16fede3808d598cc07449a6b729b3a2f2c
- `research/notes/AS_G0_SYNTHESIS_20261105.md` sha256 c9bbdb8bda5aa0375925692e91481e45ae0572309e798b2b7620c2937e0b5e4d
- `research/checks/as_ka_decision_agreement_20261105.py` sha256 5bce6d7457aada7127da856788bb3af2410f38e354c6aeb8a83a107397d73045
- `research/checks/as_ka_decision_agreement_v2_20261105.py` sha256 27e9da1a592aab849c61d7992f488c6dc94df1889f90b63432518de98e30b1a1
- `research/checks/as_ka_aggregate2_20261105.py` sha256 16a5ba678228d305afc017a9f375157d75fe60ca60657815532e291d1f3e0320


## 追加记录 A (append-only, 2026-11-06T00:33:48Z, run 20261106T003202Z-experiment-e1eb): S0 代码/分析器哈希与单测记录 -- 追加后冻结, S2 之前不再改
文件 sha256 (冻结; 任何改动须新追加记录并说明, S2 开始后不得改):
- `src/as_core.py` sha256 af9d525d7740022ebb423222f2b34e09b32bd949a810e3b412dcf503e74dc0f9
- `src/as_gen.py` sha256 e5d086786c0e042243f1466680d3e12188469dd0ad4ffc70b7e5aef670363d59
- `src/as_oracle_x.py` sha256 5f78f3f844c861e951dfcc767d9129dad7b91498da9036cf27311b02797cf746
- `experiments/as_run.py` sha256 06f2615ba62f3bcaacfbc9c44f2e8ddff0e30a880b099288b059cad21a7b9c8a
- `experiments/as_analyze.py` sha256 4f2d317b74bff64cf049c5b096a9545c40af057b758707e8c1076ed256183c2c
- `tests/as_test.py` sha256 bae36bcd1c730366a45911c7d66b62fe5dd5a8fe9c67466becd46d0e43f624c1

S0 单测: 宿主 py job j70-as-s0-tests (runs/pump/j70-as-s0-tests/stdout.log): V1,V2,V3,V4,V5,V6,V8,V10-V17 + SMOKE 共 16 项 0 失败 (VM numpy 上同样通过; 宿主与 VM 的 V3 误差量级 1e-12, Jacobian 相对误差 9e-11)。分析器合成自检: j71-as-s0-analyzer-selftest 全通过 (精确符号翻转对暴力枚举逐项一致; 判定表各分支 GO/STOP-Q1/STOP-growth/STOP-selection/PENDING/INCONCLUSIVE-{shortlist,unexplained,numerics,type-mix}/INCOMPLETE; Gate 1 (iii) 伤害拦截; cheap 规则一次性固定)。

**对合同文本的实现层更正/补充 (均不改变任何判定规则、阈值或终点):**
1. V12 前提更正: 合同称 "反射边界下 B 不对称"; 实测半样本反射 + 对称核得到的 B 是**对称的** (max|B-B^T|=0)。伴随 A^T 仍按 B^T 实现; V12 额外加了一个人为构造的非对称 B 的伴随检验 (误差 3.7e-16) 以真正检验 B^T 路径。
2. K-c 补充: GCV-Tikhonov 在本强病态算子上系统性欠正则 (S0 实测: 条件 (1.0,0.01) 下 GCV MSE 4.7e-3, 网格最优 λ 的 MSE 1.5e-3, 模糊观测本身 2.4e-3)。K-c 标志**仍按预注册的 GCV 口径**; 另报评测器侧最优 λ 的 Tikhonov MSE 作更强情境数 (用到干净图, 非合法方法, 不影响标志与任何判定)。
3. 分析器对合同未细化情形的约定: (a) Gate 0 在 192 单元未达 10% 且 ORACLE_x-full 未跑 -> 'PENDING-gate0-full' (先跑条件计划 oracle_x_full, 不做决定); (b) 192 单元 <10% 但 12 单元上 x-full 与 xs 均 >=10% -> 合同未覆盖, 标 INCONCLUSIVE-gate0-unspecified, 不放行, 报 Opus; (c) 必需臂/单元缺失 -> INCOMPLETE (基础设施失败, 不出判定); (d) V16 候选哈希在同一单元各臂第 1 步不一致 -> INVALID-V16; (e) INCONCLUSIVE 标记并存时取 unexplained > numerics > type-mix 的顺序作主标签并列出全部; (f) 类型混合检验仅对 (i)(ii) 已过的便宜规则 R 做, '胜出' = 变体级 mean D<0 且精确单侧 p<0.10; (g) H_Oys 相对同一固定 cheap 在 seed 9001 的 96 单元上算; (h) 符号翻转计数的浮点容差 1e-10 (相对); (i) 偏差原理 K 取轨迹中首个 ||y-Ax||^2 <= tau N^2 sigma_n^2 的索引 (无则 K_max); (j) K-c 的 '最优 Gaussian 臂' = 条件级几何均值 MSE 最低的 {RAND,OMP,BLOCK,JOINT,JOINT_FREE,FIXED}; (k) FIXED-K 3 个预设仅按最终训练损失选, 不看 MSE。
4. 披露: 为测分析器 I/O 管线, 对单个单元 (图 1, C1, seed 9001) 跑过全部臂, 并把其输出复制成假 S2 树; 只检查管线与诊断字段, **没有读质量结论**。顺带看到的计数型诊断 (非质量): 该单元路径上被 log-ell 钳边的父 Gaussian 随 K 增长到约 12/35、低于 1e-3 地板的候选约 14-16/116; 这些是合同内已预注册计数 (V14/V10), 不据此调参。该单元数值输出未用于任何选择。
5. 预算实测 (VM, 单核): 规则臂 ~3-6 s/单元 (JOINT 含 top-5 诊断与 V10 稳定性约 30 s), ORACLE_ys ~74 s, ORACLE_xs ~41 s, ORACLE_y-full 小 K 时 ~1.7 s/步 (K=36 时单步估计 ~30 s, 单元 ~10-15 min, 由 S1 实测)。预计全量远低于 20 CPU-h; 预算调整顺序 (见合同 §5) 暂不触发。
6. Runner: experiments/as_run.py (多进程 spawn Pool, BLAS=1, 每单元一个 JSON, 可续跑, ORACLE_x 写到 <out>-ORX 独立目录 (V17), oracle 单元每步检查点)。S1/S2 job 以该 runner + 宿主 pump 提交, 每个 job 有 run_id。pilot 单元顺序为 ORACLE_y_full 在前。


## 追加记录 B (append-only, 2026-11-06T00:48:45Z): S1 pilot 读数 (仅时间/V 闸门) 与 S2 启动记录
S1 pilot: job j72-as-s1-pilot (host py, nproc=5, run 20261106T003357Z-host-py-d932), 16 单元 (图 1 与 9 × C1,C4 × seed 9001 × {OMP-raw, BLOCK, JOINT, ORACLE_y-full}), 墙钟 800 s, exit 0。读数脚本 research/checks/as_pilot_readout.py (sha256 9753f979c1634a2613a4aff0f4af71106e42ceb62f086d91a77a7461a9f31283; 只读耗时/哈希/计数, 不读轨迹和任何质量量), 输出 research/checks/AS_S1_PILOT_READOUT_20261106.json (sha256 b332ad456875ebb0c34c28d7dee4cdd3888fa80d62463529883efd6a2566b64c)。
- V 闸门 (实测): V16 候选集哈希在 4 个 (图,条件) 单元内各臂第 1 步一致 (不一致 0); V10 JOINT top-1 对 rcond ∈ {1e-8,1e-12} 的稳定率 0.967 (n=120 步, >=0.90); LM 拒绝步上限触发 0 次; 驻点比均有限。计数型 (V14/V10): 每单元约 150 次父 Gaussian 钳边排除 (约每步 5 个) 与约 280 个低于 1e-3 地板的候选 -- 合同内预注册计数, 不据此调参。
- 耗时 (host, 5 进程并行): OMP 10.8 s, BLOCK 13.5 s, JOINT 82.5 s (含 seed 9001 的 top-5 诊断 + V10 稳定性), ORACLE_y-full 737 s (695-800 s)/单元。预算投影 (CPU-h): 原始 22.1; 把 top-5 诊断只计 seed 9001 修正后约 19-20; 6 进程墙钟约 3.4 h (<=4 h); 故合同 §5 的预算削减顺序**不触发**, S2 全量执行 (ORACLE_x-full 与 ORACLE_y-full 扩至 12 单元保持条件执行)。
- Pilot 单元**不并入 S2**: 为遵守 '不进 Gate', S2 对这 16 单元重新计算 (约 1 CPU-h); 之后仅做逐位复现性比对 (轨迹哈希相等, 不读质量)。
- S2 job (host py, 各 nproc=3, 每次至多 2 个 job 并行 => 总进程<=6; 输出 outputs\AS-S2 与 outputs\AS-S2-ORX; runner 可续跑): j73-as-s2-a-rules (RAND,OMP,BLOCK,JOINT,JOINT_FREE), j74-as-s2-b-orc1 / j75-as-s2-c-orc2 (plan=oracle_s 分 2 片 shard=0of2/1of2: ORACLE_ys 96 + ORACLE_xs 192), j76-as-s2-d-variants (6 个 birth-only/split-only 变体), j77-as-s2-e-full (ORACLE_y-full 6 单元), j78-as-s2-f-fixedk, j79-as-s2-g-initn, j80-as-s2-h-dose。S2 全部完成后才运行冻结分析器 (一次): `experiments\as_analyze.py root=outputs\AS-S2 out=outputs\AS-S2-report`。若分析器报 PENDING-gate0-full 才提交条件计划 oracle_x_full。


## 追加记录 C (append-only, 2026-11-06T01:01:30Z): S2 预算削减 (合同 §5 (3)(4)(5)) 与由此产生的两处代码变更 -- 均在读取任何 S2 结果之前
**触发 (只基于耗时)**: S2 启动后 4 分钟内实测单元墙钟高于 pilot 投影: 规则臂 OMP 16.1 s (pilot, 5 进程: 10.8 s), ORACLE_ys 209 s (投影 146 s); 6 进程并发使宿主降速。按实测外推, 全量约 25 CPU-h / 墙钟约 4.3-4.8 h, 超过合同 '<=4 h 墙钟'。按合同 §5 顺序: (1) ORACLE_x-full 已是条件执行; (2) ORACLE_y-full 已只排 6 单元 (扩 12 单元和 x-full 仍条件执行); 故依序采用 (3)(4)(5):
- **(3) 短名单 top-8 -> top-5**: 作用于 ORACLE_ys 与 ORACLE_xs (合同文本中的 '各 top-8' 一律改为 top-5; 其余设置不变)。已用 top-8 起跑的 job j74 (shard 0of2, 首批 6 个真实单元, 其余为占位) 被排空并**整体隔离**到 outputs/AS-S2-ABORTED-top8/ (未被分析器读取; 不得混用); 排队未启动的 j75 移到 queue/cancelled/ (run 20261106T004847Z-host-py-1b56 记 aborted)。top-5 重提为 4 个 shard job: j74a..j74d-as-s2-orc-top5-s{0..3}of4 (topk=5, nproc=3)。
- **(4) birth-only/split-only 只保留 JOINT 与 OMP-raw**: BLOCK_b/BLOCK_s 不跑 (占位文件使正在运行的 j76 跳过; 占位将在 S2 完成后整体 mv 到 outputs/AS-S2-CUT/)。BLOCK 的 birth 得分等同 OMP-raw 的 (无父), 实测 BLOCK_b 与 OMP_b 轨迹**逐位相同** (S0 额外检查: 图 1/C1, 图 9/C4, 图 17/C2); 故类型混合检验里 BLOCK 的 birth-only 用 OMP_b 代入, BLOCK 的 split-only 缺失 -> 若 BLOCK 对比通过 (i)(ii) 且 birth 变体未胜出, 记为 '未评估', 并按保守原则降为 INCONCLUSIVE-type-mix (不放行)。
- **(5) INIT-N 只做 C1, C4**: INITN_* 的 C2/C3 单元以占位跳过 (INIT-N 非 gate, 分析器容忍缺失)。
**代码变更 (实现上述削减的唯一改动; 不改任何判定阈值/规则):**
1. 新增 experiments/as_run_k.py (sha256 1d9d7d6d451e102c49e762716441410b974e5165588a71f7f879b21f8b7c0771): 与 as_run.py 仅差 `topk=` 透传与记录进每个单元 JSON; 原 as_run.py (06f2615b...) 未改动 (正被 j73/j76/... 使用)。
2. experiments/as_analyze.py 修补 (新 sha256 717b4b228fd6a8a7475fb4fe932e17a868cd332f2441aa20006093334c7a9f56; 修补前版本存为 research/checks/as_analyze.v1_frozenA_20261106.py, sha256 4f2d317b... = 追加 A 记录的版本): (a) REQUIRED 去掉 BLOCK_b/BLOCK_s; (b) 类型混合检验的 variant() 回退 (BLOCK_b := OMP_b; BLOCK_s 缺失 -> unassessed -> INCONCLUSIVE-type-mix); (c) 加载器跳过占位文件; (d) 记录并检查 ORACLE_ys/xs 的 topk 值, 若出现多个不同值 -> INVALID-topk-mix。合成自检在补丁后全通过 (含两个 cut (4) 新用例) 且在假 S2 树上重跑管线通过。分析器**从未在任何真实 S2 数据上运行过**。
**披露**: (i) pilot 的 5 进程耗时低估了 6 进程并发下的单元耗时约 1.45-1.5 倍 (宿主降速), 预算投影因此偏低; (ii) j74 的 top-8 工作约 8 CPU-分钟被丢弃; (iii) 预计实际墙钟仍接近 4 h 上限, 若中途再显示超出, 只可再按合同 §5 无可用项 (列表已用尽) -> 届时如实延长并披露, 不得再删臂。

(追加记录 C 注, 2026-11-06T01:01:55Z): 修补后分析器的第一次设备提交与本地复制并行执行, 设备上短暂保留旧版 (4f2d317b...); 2026-11-06T01:01:55Z 重新提交并核对设备端 sha256 = 717b4b22... 与上文一致。该期间无任何 job 使用分析器 (它只在 S2 全部完成后运行)。


## 追加记录 D (append-only, 2026-11-06T01:40:29Z): FAIL-0023 -- 变体臂受限候选集为空 (合同缺口) 的处置; 均在读取任何 S2 质量结果之前
**触发**: j76 (变体) 在 OMP_s 的图 15 单元上 argmax 作用于空序列而崩溃 (exit 1, 01:21:29Z)。容器内复现 (只数候选, 不读质量): split 候选只对未夹紧的父 Gaussian 生成; K0=6 个初始 Gaussian 经 LM 后若全部落在 LMIN/LMAX 夹紧, 则 split-only 的候选集为空 (与规则无关)。图 15-24 的 80 个 OMP_s 单元中 7 个不可行 (6 个 step 0, 1 个 step 2: 见 FAIL-0023 与 research/checks/AS_FEAS_split_only_OMP_15_24_20261106.json); 图 1-14 的 112 个单元已完成。合同只写'候选集限制', 未规定受限集为空时的处理 -- 这是合同缺口。
**代码变更 (不改任何判定阈值/规则; as_core.py / as_run.py / as_run_k.py 均未改动, 因 j73/j74 等的 spawn worker 会从磁盘重导入):**
1. 新增 experiments/as_run_var.py (sha256 56aa6be7700efa0bb968b5a0cfdc701dce231fc7e19079800aaf38fc745d8ba6): 与 as_run.py (06f2615b...) 的差异仅为 (a) 变体臂 (VAR_ARMS) 对 as_core.mask_for 的只读包装, 受限集为空时写 status=infeasible_restricted_set 标记文件 (含 empty_step, 无轨迹) 而不崩溃; (b) 单元级异常被捕获、记录并跳过, 不再让 imap 的第一个异常中止整批 (结束时若有错误则 exit 1)。可行单元的数值与 as_core.run_path 直接调用逐位一致 (research/checks/as_run_var_test_20261106.py: OMP_s/OMP_b/JOINT_s/JOINT_b 四个臂在图 14 C2 上整条轨迹逐位相等; 空集标记 step 0 与 step 2 两种情形均验证; 跳过已存在文件; 坏臂名只产生 ERROR 元组)。
2. experiments/as_analyze.py 补丁 (新 sha256 0dbb17879531f41051ec948f39b37cf1cbaaabacf9948e921360f7e769835951; 补丁前版本 = 追加 C 的 717b4b22... 存为 research/checks/as_analyze.v2_frozenC_20261106.py): (a) load_all 把 infeasible 标记记入 aux['infeasible'] 并从 M 中排除; (b) REQUIRED 完整性: 被标记不可行的单元视为已交代 (不再算缺失); 未标记也未完成的单元仍 -> INCOMPLETE; (c) variant() 同样把已标记的单元视为已交代; (d) 类型混合检验的配对: per_image_D 本就只用两臂都存在的单元, 现在对没有任何可配对单元的图 (D=NaN) 予以剔除; 若剩余图数 < MIN_VAR_IMGS=20 (共 24 图) 则该变体判 unassessed (None), 沿用原有规则 (JOINT 的 birth 或 split 变体任一胜出则不是类型混合; 两者都未胜出且有一个 unassessed -> INCONCLUSIVE-type-mix; 绝不放行 GO); (e) 报告增加 infeasible_counts 与各变体的 n_images / n_paired_units; (f) 自检新增 5 条 D 检查 (7 个不可行单元仍评估 24 图并保持 GO; 单图全不可行被剔除仍评估 (23 图); 19 图 -> split 变体 unassessed 但 birth 胜出则 GO 不变; birth 不胜且 split unassessed -> INCONCLUSIVE-type-mix; 单元缺失且无标记 -> INCOMPLETE)。自检全部 PASS (SELFTEST OK)。另在合成 S2 目录 (含 6 个标记) 上跑通完整 I/O 路径 (读文件 -> 分析 -> 报告), 报告含 infeasible_counts。
**预先写明 (读取任何质量数据之前)**: 阈值 20/24 与剔除规则在此一次写明, 不随结果改动; 该规则只影响类型混合标志, 且只会使判定更保守。
**披露**: (i) 容器内的可行性检查重跑了图 15-24 的 OMP_s 路径 (只计数/记录空集步骤, 未计算任何 MSE 或质量量); (ii) 分析器仍未在真实数据上运行; (iii) 续跑作业 j81a/j81b (as_run_var.py plan=variants shard 0of2/1of2, nproc=3, 提交于 2026-11-06T01:40:29Z 之前, 已存在文件跳过) 补 OMP_s 余下单元与 JOINT_b/JOINT_s (约 384 单元); 排在队列末尾 (按作业名顺序); (iv) 合同 §5 五项削减均已用尽, 本追加不再削减任何臂, 如超 4 h 墙钟只能如实延长并披露; (v) 本追加的分析规则待真实 Opus 复核, 复核前不运行分析器。


## 追加记录 E (append-only, 2026-11-06T01:48:33Z): 真实 Opus 对追加 D 的复核结论与据此的分析器再补丁 -- 仍在读取任何 S2 质量结果之前
**Opus 复核** (run 20261106T014118Z-opus-review-1558; 自报模型 Opus 5.5 / claude-opus-5-5; 全文 research/notes/OPUS_REVIEW_AS_ADDENDUM_D_20261106.md): APPROVE-WITH-CHANGES。同意: 排除不可行单元可接受 (step 0 的空集与规则无关, 配对无偏; 不回退混合池/不空转); 图 16 仅剩 1 个配对单元仍等权计入可接受; 阈值 20 与'一个变体胜出则不触发类型混合'符合 K-e 的字面与精神; 该缺口不影响 Gate 0/1/F (它们只用规则臂/FIXED/ORACLE)。必须在运行分析器之前完成 M1-M4:
- **M1 标记校验 (已实现)**: 标记只允许出现在 OMP_s/JOINT_s/BLOCK_s 臂且 only='s'、empty_step 为非负整数; OMP_s 与 JOINT_s 中 empty_step==0 的 key 集合必须完全相同 -- 违反任一条判 INCOMPLETE (infrastructure)。
- **M2 后期步骤不对称不可行 (已实现)**: 某 key 只在一臂不可行, 或两臂不可行但步数不同 -> 报告 n_asym, 主分析仍用交集; 变体判 True 必须在最坏情形下仍满足 mean D<0 且 p<0.10, 否则判 None (unassessed); 最坏情形: 每个不对称单元的 log 比取 max(0, 所有配对单元 log 比的最大值), 并入所在图的均值 (没有配对单元的图因此恢复); 判 False 不受影响。
- **Q2 替换文本 (已实现)**: 某 R 的一个变体 unassessed 时, 该 R 的类型混合检查只由另一变体决定; 另一变体胜出则不触发类型混合, 但报告与 GO 结论必须附注 'TYPE-MIX CHECK PARTIAL: variant(s) unassessed ...; 后续新合同必须单独重新评估类型内比较, 不得把本次结果当作类型内证据' (BLOCK_s 因 §5 削减 (4) 未跑, 故 BLOCK 的检查总是 partial)。
- **M3**: 新分析器 sha256 9adc5b04612c234dab2ba4cc35972b5b27bd6fe573ee636db6951a5e5d7f8168 (supersedes 追加 D 的 0dbb1787...; 追加 D 版本存为 research/checks/as_analyze.v3_addD_20261106.py); 自检全部 PASS (含 5 条新检查: M1 两条、M2 两条、Q2 一条); 合成 S2 目录 I/O 路径复测通过; 仍只运行一次。
- **M4 + 披露 (Opus Q4)**: (a) 可行性脚本对可行单元把 run_path 跑完, 轨迹随即丢弃, 未算 MSE; (b) 为测试 as_run_var.py 在容器暂存目录写下了图 14/C2/9001 的 OMP_s/OMP_b/JOINT_s/JOINT_b 四条真实轨迹, 另有 41+40 个单元的崩溃冒烟轨迹 (FIXED-K/INIT-N/D03; 81 单元 0 异常, 仅查异常与耗时); 这些轨迹**未读取、未算质量**, 已整体隔离到容器暂存的 quarantine/ (不在设备上, 不在分析器 root 下, 不进任何分析); (c) 阈值 20 是在已知 OMP_s 全部可行性计数之后选定的 (按这些计数它不会约束 OMP_s, 只可能被 JOINT_s 的后期不可行触发)。
- **次要记录/建议 (已实现或将记录)**: 报告含各变体 n_asym、n_images、n_paired_units、每图 >=4 配对单元的敏感性 (无判定权重); 各臂单元的 run_id 来源列表 (aux['run_ids']; OMP_s 图 1-14 来自 as_run.py 的 j76, 其余来自 as_run_var.py 的 j81, 二者对可行单元逐位等价); 图 16 的初始化饱和 (K0 夹紧 6/6) 将作为次级诊断报告; JOINT_s 在 split 分数全低于 floor 时回退 OMP 打分的步数不另加代码, 如需要在次级报告中补。


## 追加记录 F (append-only, 2026-11-06T04:51:19Z): S2 全部作业完成与冻结分析器的唯一一次运行 -- 运行前记录 (prospective)
- S2 作业 j73, j74a-d, j77, j78, j79, j80, j81a, j81b 全部 exit 0 (j76 为 FAIL-0023, 已由 D/E 处置); 最后一个 j81b 结束于 04:47:18Z。
- 运行前核对: (1) 轨迹哈希复现性 (S1 pilot vs S2, 仅查相等性): 16/16 EQUAL (OMP/BLOCK/JOINT/ORACLE_y_full 各 4 个 pilot 单元); (2) 占位文件 528 个 (BLOCK_b 192, BLOCK_s 192, INITN_{OMP,BLOCK,JOINT} 各 48) 已 mv 到 outputs/AS-S2-CUT/ (infeasible 标记 13 个原地保留); (3) 结构完整性检查 (research/checks/as_prerun_structure.py, 不计算任何 MSE/质量量): 每个 REQUIRED 臂的 192 个键 (ORACLE_ys 为 96) 均被真实单元文件或有效 infeasible 标记覆盖, 无缺失、无无效文件、无占位; OMP_s 标记 7 个 (step 0: 6 个, step 2: 1 个 = (16,C3,9002)), JOINT_s 标记 6 个 (均 step 0); 两臂 step-0 键集合相同 (M1 通过); 不对称单元 n_asym=1 ((16,C3,9002) 只在 OMP_s 不可行) 将由分析器的 M2 规则处理。
- 分析器: experiments/as_analyze.py sha256 9adc5b04612c234dab2ba4cc35972b5b27bd6fe573ee636db6951a5e5d7f8168 (= 追加 E), 自检 OK; outputs/AS-S2-report 尚不存在。将以宿主 py job j82-as-s2-analyze 运行**一次**: experiments\as_analyze.py root=outputs\AS-S2 out=outputs\AS-S2-report。若该 job 因基础设施原因 (崩溃/超时) 未产出 AS_S2_REPORT.json, 属于基础设施故障 (记 FAILURES), 修复须再追加记录后才可重跑; 若产出报告则不得再跑, 一切判定按报告机械执行。
- 数据边界披露不变: 至本记录前, 除一个 I/O 测试种子单元与容器内 FAIL-0023 单元 (均已披露) 外, 未读取任何 S2 质量量。


## 追加记录 G (append-only, 2026-11-06T04:56:11Z): 冻结分析器唯一一次运行的结果与一处操作失误的更正
- j82-as-s2-analyze (run 20261106T045120Z-host-py-4b59) exit 0, 04:51:22Z-04:51:55Z; 报告 sha256: AS_S2_REPORT.json 163c79153bef1f3b7b15eb49187263cd51fe40f65c21fffff51655f1cfb0c751, AS_S2_REPORT.md ed3ffd7cbbcd9e6c57f08a4d6d80f84fa06061d9aa0eeb2baffeb9625f22dd33; 报告内记录的分析器 sha256 = 9adc5b04... (与追加 E/F 一致); 判定 **STOP-Q1** (细节见 research/notes/AS_S2_RESULT_STOP_Q1_20261106.md, FAILURES FAIL-0024)。分析器不再运行。
- 操作失误 (我的): 提交结果记录到设备时误把结果记录的暂存文件同时映射到 research/checks/as_prerun_structure.py, 覆盖了该结构检查脚本 (非冻结、非证据文件; 分析已完成)。发现后立即用原脚本全文重写, 重跑得 STRUCTURE OK, 输出与分析前一致 (所有臂完整, 标记 OMP_s 7 / JOINT_s 6)。该脚本不进入任何判定。


## 追加记录 H (append-only, 2026-11-06T05:27:16Z): 分析器缺陷 FAIL-0025 的勘误计划 (先于任何勘误计算写下)
- 原冻结分析器 experiments/as_analyze.py (sha256 9adc5b04612c234dab2ba4cc35972b5b27bd6fe573ee636db6951a5e5d7f8168) 与唯一报告 outputs/AS-S2-report/AS_S2_REPORT.{json,md} (json sha256 163c79153bef1f3b7b15eb49187263cd51fe40f65c21fffff51655f1cfb0c751) **不改动、不重写、不删除**; 其数字作为 '原统计' 全部保留。
- 勘误计算 (只读, 不是对冻结分析器的重跑, 不启动任何新拟合, 只读取 outputs/AS-S2 与 AS-S2-ORX 里已有的单元 JSON): 新脚本 research/checks/as_erratum_192.py 先校验分析器与原报告的 sha256 (运行前后各一次), 以 import 方式调用冻结分析器的 load_all/analyze/diagnostics 函数本体 (不复制逻辑), 做两次: (a) 复现检查: 对未受限的 M 调 analyze(), 其 Gate 1/H/Gate F 数字须与原报告逐位一致 (|差| < 1e-9), 否则勘误作废并记失败; (b) 勘误: 把每个臂的 M、extra、aux.infeasible 一律限制到合同主集 KEYS (24 图 x C1-C4 x seeds 9001/9002 = 192), 重跑同样的 analyze() 与 diagnostics() (后者含合同要求的偏差原理停止 K 处 Gate 1 重算)。
- 承诺: 主集固定为合同 KEYS, 不选择有利的条件/子集/种子; 所有数字 (含不利者) 全部报告; 原统计与勘误统计并列; 机械比较 '勘误后的判定字符串/Gate 1 的 (i)-(iv) 通过标志' 是否与原报告相同, 不由我解释; 无论结果如何都不自动释放 GO/不自动改判定, 勘误结果连同原报告一起交真实 Opus 科学门确认其对判定的影响; 勘误输出写到 outputs/AS-S2-erratum192/ (新目录), 不写 outputs/AS-S2-report。
- 措辞更正与范围区分见 FAILURES FAIL-0025。此记录不构成新合同或新实验许可; 新方向仍需新 G0 + 新合同 + 真实 Opus 门 + 冻结。

- 追加 H 补充 (2026-11-06T05:29:09Z): 勘误脚本因 host pump 白名单改放 experiments/as_erratum_192.py (与 research/checks/as_erratum_192.py 只差 ROOT 一行); 作业 j83 被拒 (未计算), 重提为 j83b-as-s2-erratum192。计划内容 (复现检查 + 固定 192 主集 + 并列报告 + 不自动改判 + 交 Opus 门) 不变。

- 追加 H 结果 (2026-11-06T05:30:05Z): 勘误结果 (j83b, run 20261106T052909Z-host-py-ea8b, exit 0, 05:29:10-05:29:25Z; 脚本 experiments/as_erratum_192.py sha256 9780ff37...; 勘误 JSON sha256 c7cf55028894f70c3022e0952d114ffff04d45ce0d773f798dfa679cf02e4e42, MD sha256 eee74d8ea4932b9f33ec0bd80a224cfc3a2f9dfaffe75942df5aeb4ff7c5cd2d): (1) 复现检查 ok=True (未受限数据逐位复现原报告); 原报告 sha 运行前后不变=True; 被移除单元: 三臂各 24 个 D03。(2) 固定 192 主集后判定字符串: 原 STOP-Q1 -> 勘误 STOP-Q1 (相同=True); H 与 Gate F 完全不变 (H same=True, Gate F 0.8162)。(3) Gate 1 vs OMP: meanD -0.0342->-0.0265 (比值 0.9663->0.9739), p 0.1304->0.2106, 族均值 edge -0.0097->0.0056; (i)(ii)(iii) 仍不过, (iv) 由 True 变 False (原 (iv) 通过是 D03 混入的产物); 条件均值 (iii) 完全不变 (C4 +0.1358)。Gate 1 vs BLOCK: meanD 0.0265->0.0390 (比值 1.0269->1.0397), p 0.7589->0.8255; 四项仍全不过。(4) 偏差原理停止诊断 (合同要求、原报告缺失; 无判定权重): 平均停止步 OMP 12.9/BLOCK 12.9/JOINT 13.5 (总 30 步); 该 K 处 JOINT vs OMP meanD -0.0224 (p 0.211), vs BLOCK -0.0291 (p 0.156), 均未过 (i)(ii)(iii)。(5) 结论 (机械): D03 混入是真实缺陷, 但对 STOP-Q1 判定、Gate 0、Gate F 与 H 无改变; 唯一改变的是原 Gate 1 vs OMP 的 (iv) 通过标志。该比较未选条件, 原统计仍保留。

- 追加 H 复核 (2026-11-06T05:35:45Z): 真实 Opus 复核 (claude-opus-5-5, run 20261106T053038Z-opus-review-6c95) 认定勘误忠实、STOP-Q1 成立; 要求注明: Gate 0/H/Gate F 原已用显式 192 键, 数值相同不是独立复现; 剂量-响应读数继承自原报告 (显式键, 不受缺陷影响); 本次是 '勘误' 不是 '重新分析', 不构成再次运行分析器的先例; 偏差原理诊断无判定权重。


## 追加记录 I (append-only, 2026-11-06T06:17:56Z): 节点 R 的计划 -- 只读、一次、闭合/描述权重, 不作新路线闸门 (依据: 真人 2026-11-06 授权 + Astra GEO 决定; Opus 勘误复核建议的节点 R)
- 目的: 说明 S2 在固定 K_max=36 终点的 ORACLE_xs 余量 (H_Oxs=0.4518) 在**另一种停止规则**下还剩多少。这不是选择/停止的精确因果分解; 结果不阻塞也不取消 GEO 新几何合同, 不引出另一轮停止规则主线。
- 输入: 已写的 S2 轨迹 (outputs/AS-S2, AS-S2-ORX), 合同主集 KEYS(192); 不新拟合、不新图; 脚本 experiments/as_node_r.py 以 import 方式用冻结分析器 as_analyze.py 的 load_all/signflip_p/常量 (sha256 9adc5b04... 运行前后校验), 不运行其 main/analyze。
- 读数 (只这四组, 不加其他切分; 便宜规则固定为 BLOCK, 与 S2 相同): (a) 每臂在**自己的偏差原理停止点** (第一个满足 ||y-Ax_j||^2 <= tau N^2 sigma_n^2 的轨迹索引 j, tau=1.0, 已知 sigma_n; 无则取末点) 的干净 MSE, ORACLE_xs 相对 BLOCK 的 H; (b) 每臂在**已生成路径上的干净图最佳步** (逐单元取 31 个轨迹点的最小干净 MSE) 的 H -- 仅是这些已生成路径的理想停止参考, 不是所有可能算法的上界; (c) RAND、JOINT_FREE (以及 OMP、JOINT 作对照) 相对 BLOCK 在 (a)/(b) 下的 H; FIXED 臂只有末点 theta、无轨迹 -> 标缺失, 不新拟合; (d) (a) 的分条件 C1-C4。另报终点 (j=30) 的 H 作复现校验 (ORACLE_xs 应为 0.4518)。
- 区间: 每图 D_i=该图 8 个单元 log(M_X/M_BLOCK) 的均值 (24 个), 报告均值、t 区间 (df=23) 与精确符号翻转 p。
- 表述约束 (Astra 修正): 不足 10% 或区间含 0 **不能**写成"普遍无余量"或"全部来自停止"; 只表示 '在该停止规则下、该组已生成路径上、该基准中' 余量如何; 若据此停止已测的排序路线, 说明是项目决策而非不可能性定理。事后诊断, 开发数据, 不验证任何东西。
- 时限: 准备+计算合计约 30 分钟 (自 06:17Z), 超时则记录未完成并转入主线; 只运行一次, 全部数字照报, 包括不利者。


## 追加 I-bis (节点 R 计划修订; 2026-11-06T06:21:01Z; 依据真实 Opus 轻量复核, 自报 claude-opus-5-5, run 20261106T061756Z-opus-review-dc0e; 复核 RUN-WITH-CHANGES, 全文 scratchpad/AS/OPUS_REVIEW_NODE_R_PLAN_20261106.md, 摘要入 research/notes)
状态: 计划修订, 运行前追加; R 仍是事后诊断 (开发数据, 已见端点结果), 只读, 不新拟合, 不新图, 不验证任何东西, 不作新主线闸门。
修改 (均不需要新拟合):
1. 读数 (b) 命名为 "已有路径上的干净图最佳步" (clean-image best step on existing paths): 每臂对自己每条路径的 31 个点用干净图选最小 MSE 的步; 仅诊断, 对所有臂对称; 不称 oracle 上界, 不称 ideal。
2. A x_j 的取得方式: 用冻结前向算子 (C.Op) 渲染已存 theta_j (C.render), 与拟合时相同的带噪 y (G.noisy_obs(op, clean, sn, 种子, 图号)); 只渲染不优化。运行时核对每臂 192 单元是否都有 31 个轨迹点; 缺失只报告, 不插补。
3. 对 (a)(b) 每臂 (总体与分条件) 报告: 回退到 j=30 的比例、停止 j 的均值与中位数 (K=6+j)、(b) 的平均最佳步 j*; BLOCK 自己的停止 K 并列报告。
4. 端点 (j=30) 复现检查扩展到所有有轨迹的臂, 对照 S2 H 表 (RAND 0.370, JOINT_FREE 0.314, OMP -0.068, JOINT -0.040, ORACLE_xs 0.4518; 对原报告 json 值 1e-6, 对四舍五入值 1e-3); 任一臂不过则报告并停止解读该臂。
5. 不做多重比较校正: 5 臂 x 2 读数 + 4 条件, p 值仅描述; 分条件时每图的 D_i 是 2 个单元 (2 种子) 的平均, 不是 8 个。tau=1.0 是预先固定的未调定选择, 看到结果后不改。各臂在各自的 K 比较 (有意为之)。
措辞规则: 不写 "选择是瓶颈" 或 "停止解释了 X%" (不同臂在不同 K 的 H 不是分解); 余量缩小只表示 "在这 192 条路径上、该停止规则下, K_max=36 端点处的差距更小", 不表示便宜规则足够; 余量保持只表示 "该差距不是固定端点的产物", 不表示仅用 y 的选择器能恢复它; <10% 或区间含 0 不得写成 "一般无余量"。


## 追加 J (节点 R 结果记录; 2026-11-06T06:25:12Z; 事后诊断, 无判定权重)
作业 j84b (run 20261106T062312Z-host-py-6355, exit 0); 脚本 experiments/as_node_r.py sha256 1967c998377456d894e74626a7c117543ca77e24eab14124b3f76953bb627eca; 输出 outputs/AS-S2-nodeR/NODE_R.json sha256 d344e8b736a32cd7d916c9b6ac3a0b858ea15eca00f7745965431edec80eaf3b, NODE_R.md sha256 28fed501c49894ac56b39c4c5fe914bfdde75dd266582255f43dc59b966c60bd。冻结分析器与原报告 sha 运行前后不变; 终点复现通过。全部数字与措辞限制见 research/notes/AS_NODE_R_RESULT_20261106.md。要点: (a) ORACLE_xs 相对 BLOCK 的 H=+0.298 [0.228, 0.362] (>=0.10, 杀死准则未触发); (b) 干净图最佳步 +0.315; 非 oracle 臂在停止点彼此接近 (JOINT +0.029 区间含 0; RAND -0.055); 固定 K_max=36 到偏差原理停止使 BLOCK 几何均值 MSE 0.00716 -> 0.00268。不称"选择是瓶颈", 不称分解, 不验证任何东西, 不作路线闸门。
前序: 作业 j84 (同脚本修订前版本) 因局部变量未绑定 (我把 i,c,s=k 并入了条件语句) 在 15 s 内 exit 1, 未完成任何计算; 修正后重提 j84b; 非科学结论。
