# Lessons (可复用失败经验, 追加式)
- Windows PowerShell 5.1 默认不加载 System.Security: 使用 [System.Security.Cryptography.ProtectedData] 前必须 Add-Type -AssemblyName System.Security。
- PS5.1 的 Start-Process -RedirectStandard* 日志是 GBK/OEM 编码: 用 scripts/hostlog.py 或 ingest_host_results.py 解码, 先试 utf-8-sig 再 gbk, 别用 utf-16 兜底(会产生乱码而不报错)。
- 桥接 VM 不能 unlink/rm mount 内文件(需 device_request_delete_permission): 锁/标记用“覆盖写”实现, 不要依赖删除; 宿主侧 pump/cmd 可删自己的 STOP/RESTART。
- cmd 批处理文件运行中不要编辑(按字节偏移读取): 新逻辑用新文件名(start-pump-loop.cmd)。
- WebFetch 对 arXiv 同时多页会限流(一次一页); 商业期刊页(tandfonline/projecteuclid/bohrium)常被反爬拦截 -> 记为“未读线索”, 交 GLM 侦察或找作者PDF镜像。
- 进程存在 != 结果: worker 退出码为0之前 status.json 可能停在 running; 以 queue/done + output.jsonl 为准。
- 2026-11-05T08:11:51Z OpenCode output.jsonl 为 UTF-16LE(带BOM); 读取必须先判 BOM 再 utf-8/gbk, 否则 gbk 会"成功"解出乱码。worker 文本中的非 ASCII 标点会以 GBK 乱码形式保存(原样如此, 非我方损坏)。
- 2026-11-05T08:11:51Z 非任务文本: GLM 输出里出现与任务无关的内容(其它仓库/CVE/补丁)。处理: 只采信与工具调用一致且我能抽查的断言, 其余忽略; 勿据其执行任何动作。
- 2026-11-05T08:11:51Z export.arxiv.org API 被 WebFetch 的 robots 拦截; arxiv.org 同时多页会限流(一次一页); 官方 abs 页面摘要可能不含新版本评论, 版本问题需用 /abs/<id>v2 单独核对。

- 2026-11-05T08:40:35Z: run-worker.ps1 把整份任务文本内联到命令行, opencode.cmd 限 ~8191 字符; 任务文件>~7KB 会立即 exit 1 (表象: "命令行太长")。修复: >5500 字符时只传"读任务文件"的指针。教训: 长规格放文件, 命令行只给指针。

2026-11-05T11:06:39Z 教训 (Sonnet): 我写了 `open(p,'w').write(open(p).read().replace(...))` 式的一行 edit 助手, Python 先以 'w' 截断文件再读, 把 CHECKLIST.md 清成 0 字节。已按对话内容完整重建 (含 v3 pilot/Stage 1 行), 其余 memory 文件未受影响 (它们用先读后写的 edit)。规则: 改文件一律"先 read 到变量, 再 open(p,'w')", 不用单表达式读写同一文件; 改完 wc -c 核对非 0。

2026-11-05T18:01:04Z 教训 (Sonnet, 失败日志规则): 从现在起, 所有失败/被否决假说/INVALID/INCONCLUSIVE/基础设施故障/近邻碰撞/真实限额都必须当场追加到 memory/FAILURES.md (字段见该文件头), 并在 DECISIONS 留索引行; 只追加, 不删除, 不改写成成功, 不无限重试。F0/H2 的核心教训 (FAIL-0001): 先问"决策规则究竟用到了哪个量"——若把 df_full 拆成 df_par+sdf 不改变决策, 则拆分无方法贡献; 近邻基线 (fission-CV, 只用 y) 须在合同里作强基线, 且新颖性门应在大实验之前。

- 2026-11-09 (JR): 云容器里 nohup/& 启动的后台计算在会话空闲数分钟后会被回收 (容器重启, uptime 归零, 进程消失, 磁盘文件保留)。长跑必须用 Bash run_in_background (harness 跟踪, 可达 2h) 或保持会话在线; 所有 runner 必须可续跑 (按输出文件跳过), 写 JSON 时单文件原子 (结束时一次性写)。每次醒来先看 uptime 与 pgrep。

- 2026-11-09 (JR): 向冻结记录追加闸门依赖的行 (TUNE_DONE / VERIFY_UNSEALED 等) 时, 必须按闸门的匹配规则书写 (jr_gen._sealed_gate 按行首 startswith, 不能带时间戳前缀); 在单次真实读取之前, 先用 _sealed_gate 的 rec_path/environ/main_file/module_files 参数对实际冻结记录的**副本**做一次不改记录的闸门演练, 否则浪费一次启动 (本次幸而闸门在读任何图之前拒绝, 无后果, 已披露)。

- 2026-11-09 (CA): Bash run_in_background 的 timeout 最大 7200000 ms (2 h), 超时后任务被标 killed; 长运行 (CA 密封 CONFIRM 估计 4.5 h) 必须在启动前把总墙钟与该上限比较, 并预先登记分段续跑方案 (每段一条 CONFIRM_RESUME_OK + 披露; 守卫要求全量 P,S,X, 已完成运行跳过)。另: 带 --blocks 全量守卫的密封运行里, 无条件块 (X) 必须在任何约简之前跑完, 否则出现 "看了 P 再决定 X" 的自由度。
- 2026-11-09 (CA): 提交给密封闸门的冻结记录里, NOTE 行不要写出闸门会 grep 的关键字 (如 CONFIRM_CONSUMED), 否则演练的 "只追加到副本" 检查会误判; 闸门本身按行首匹配不受影响。
- 2026-11-09 (CA): reducer 与诊断脚本 (reduce/diag load) 也要像分析器一样登记 sha, 并断言登记行在 CONFIRM_UNSEALED 之前 (Opus 确认核对建议); 密封运行拒绝 --imgs/--conds 子集与任意块序。
- 2026-11-09 (CA): 单一对照下的 "缺口随噪声翻转" 必须用并列对照的分解对 (OBS-J vs IND1/SPA-J、各臂无噪→有噪的下降量) 才能判断是被测臂变差还是对照变好; 否则会误归因 (Opus 终态审抓到: 是 RND-J 变好, 不是 OBS-J 劣化)。结果笔记先写两句定调再给数; V-INS 不授权任何因果措辞 (含 CFG 排除与停止时点限定词)。
- 2026-11-09 (CA): 绝对质量远低于表示上限 (20–23 vs 30.6 dB) 时, "表示因子未检出" 不能外推; 判别性测试设计要让工作区触及表示瓶颈, 或明说不触及。
