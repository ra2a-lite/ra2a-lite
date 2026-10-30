# RA2A-Lite 研究协议（本项目版）
protocol_version: lite-1.0（修改属于 RL3）

## 1 角色
| 角色 | 由谁担任 | 能做 | 不能做 |
|---|---|---|---|
| 研究员 | 你 | 批准计划；启动/终止训练；修改章程；确认里程碑；批准记忆变更；做 test 评测 | — |
| 主会话（Lead） | Claude Code / Codex 主会话 | 编排；写轮次文件；起草 ERC/脚本；实现已批准的改动 | 批准任何事项；启动/终止训练；未经确认修改受保护文件 |
| ra-analyst / ra-designer / ra-skeptic | 子代理 | 在 P1/P3/P4/P8 从各自视角发言；analyst 另负责阶段 A | 在自己的 work/ 目录之外写文件 |
| ra-judge | 子代理 | P5 逐维打分 | 排名、计算总分 |
| ra-verifier | 子代理 | P6 核验证据与章程映射 | 提出实验 |

## 2 不变量（括号内为 RA2A 编号）
| # | 不变量 | 检查方式 |
|---|---|---|
| I1 | 方向锁：一切候选与决策都带 charter_trace；章程只由研究员修改（R13） | verifier；审计 C7 |
| I2 | 证据绑定：断言必须带 ev；指针无效的断言被剥离并公示（R14） | verifier；C6 |
| I3 | 回合完整：A、P1…P8 全部发生且顺序正确；缺任何阶段都不出决策（R15） | C1 |
| I4 | 独立评审：P1 的子代理并行、全新上下文、互相看不到；不 resume（R18） | C2 |
| I5 | 先剪枝后分发：每个没进入计划的候选都有处置记录（R16） | C8 |
| I6 | 预注册：ERC 随锁定提交入库，且早于启动；分析按 ERC 执行；不因效果好提前停（R17） | launch.sh；C9 |
| I7 | 可行性：GPU·h、卡分配、磁盘、数据泄漏、种子数、依赖逐项通过（R11） | feasibility.md |
| I8 | 人工批准：只认研究员亲自输入的批准语句（R12） | hook 记录；C10 |
| I9 | 启动幂等：exp_id 唯一，至多启动一次；重跑使用新 id，并须批准（R7） | launch.sh；C11 |
| I10 | 评测冻结、基线不退化：评测代码、数据、指标只读；champion 只能依据确认性结论更新（R1） | OS 权限；C12 |
| I11 | 记忆经批准：记忆、规则、代理、技能的改动都须研究员批准；负结果只增不删（R8） | 权限 ask；C13 |
| I12 | 可复现、平台变化可见：每个实验绑定 commit、配置、数据摘要、种子；记录运行时版本与模型；版本变化后须跑 canary（R3/R4/R19） | meta.yaml；C14 |

## 3 证据指针
- ev:<仓库相对路径>#L<a>-L<b>：文本或日志的行
- ev:<路径>#<json 键路径>：例如 ev:runs/R02-E1/seed1/eval_dev.json#metrics.acc
- ev:git:<commit>:<路径>[#L..]：某个历史版本
- ev://<绝对路径>#L..：仓库外的日志
- ev:web:<URL>#"<原文片段>"：标注[外部]，不能单独支撑确认性结论
- 结论引用（v2.5）：引用结论写 `H-003@v2`（conclusions.jsonl 版本地址）。迁移前无版本引用记 legacy_unversioned，只告警；新轮次产物必须带版本
- 命令输出：先保存到本轮 work/<role>/ 下的文件，再引用该文件
"有证据"须同时满足三条：指针可解析；定位到的内容存在；内容确实包含或支持被引的数字或文本。
断言 = 可证伪的事实陈述，包括数字、比较、因果、"文献报告……"。建议可以不带证据，但必须建立在断言之上。

## 4 一句话结论
格式：[结论] 因为 [核心证据 ev:…]，置信度 [低/中/高]，若 [条件] 则失效
正则：^\[.+\] 因为 .*ev:\S+.*，置信度 (低|中|高)，若 .+ 则失效$

## 5 轮次阶段
| 阶段 | 执行者 | 输入（只给这些） | 产出 | 完成判据 |
|---|---|---|---|---|
| 0 开轮 | 主会话 | — | meta.yaml | 自检通过（v2.5 增：FORK_SUBAGENT=0 与 DISABLE_AUTO_MEMORY=1 生效值实测；lsattr 探测账本保护等级记入 meta.yaml） |
| A 结果回收 | analyst | 上一轮的 erc/、decision.md、runs/<exp>/ | A_results.md＋results.jsonl 的 RES 行 | 每个已完成实验都有判定；随后跑 research/scripts/res_extract.py（提取失败=undeclared，禁止猜档） |
| P1 独立评估 | analyst、designer、skeptic 并行 | charter、project_card、memory、A_results、往轮 decision 列表 | p1/<role>.md | 3 份齐全，一句话结论合规 |
| P2 广播 | 主会话 | p1/* | p2_broadcast.md | 逐字摘录 |
| P3 交叉影响 | 三个角色并行 | p2 + 本人的 p1 | p3/<role>.md | 共 6 条（含 no_impact） |
| P4 修改意见 | 三个角色并行 | p2 + p3/* | p4/<role>.md | 每条提案字段齐全 |
| P5 评分 | 主会话 + judge×3 | 匿名、乱序的候选 + rubric | p5/ | tally 由脚本算出 |
| P6 汇总与核验 | 主会话 + verifier | p1–p5、memory | p6_synthesis.md、erc/、feasibility.md、p6/verify.md | 剥离清单、剪枝记录齐全 |
| ⏸ 讨论 | 研究员 + 主会话 | brief.md | brief 的修订记录 | 研究员亲自输入决定 |
| P7 决策 | 主会话 | 批准原文 | decision.md | 原文能在 ledger 中找到 |
| P8 影响 | 三个角色并行 | decision + 本人的 p1 | p8/<role>.md | 3 份 |
| I 实现 | 主会话 | 已批准的 ERC | 代码 diff、exp/ | CPU 自检通过 |
| L 锁定 | 主会话（研究员确认） | — | lock commit | — |
| X 启动 | 研究员（模式 A）/ 主会话经确认（模式 B） | launch.sh | runs/、ledger | launch.sh 自检通过 |

protocol_mode = lite 时（见章程）有两处精简：P3 与 P4 合并为每角色一次调用，输出 p34/<role>.md，内含两节；P5 只用 2 名评委。

### 5.1 runs.jsonl 事件格式
{"ts","exp_id","event":"STARTED|DONE|FAILED|ABORTED","gpus","commit","rc"}。前三种由 launch.sh 写入。ABORTED 在研究员终止训练后追加：
printf '{"ts":"%s","exp_id":"%s","event":"ABORTED","abort_id":"%s","by":"researcher"}\n' "$(date -Is)" <exp_id> <A?> >> research/ledger/runs.jsonl

### 5.2 技术故障重跑
1. 研究员输入：批准重跑 <exp_id>: <原因>。
2. 主会话在 rounds/<R>/retries.md 中追加一行：| <新id，如 R03-E1.r2> | <源id> | 原因 | 批准原文 | 时间 |。
3. 提交后，由研究员运行：bash research/rounds/<R>/launch.sh retry <新id> <源id>。
注意：修复项如果改变了实验的科学内容，就不算重跑，而是新实验，要走下一轮。

### 5.3 结论版本层与记忆变更时机（v2.5）
- `research/ledger/results.jsonl`：RES 实验判定行。由 res_extract.py 追加，**免 CR**（派生事实，对应全量 L1/L2）；只提取 A_results 明示落档，失败记 undeclared。
- `research/memory/conclusions.jsonl`：语义结论版本行。唯一写入路径是 /ra-memory → `commit_conclusion.py`（锁内分配版本、算 content_hash），**每行必带 approval_ref（R8，对应全量 L3）**。
- 判读升格约束（P1-4）：定论性状态（refuted/supported/confirmed/rejected/disproved）必须抄自所引实验的判读档（CR 带 band_source）；不可判定族（no_diff/no_difference/*_flat/*negligible/marginal）禁写定论性状态——H-003 教训（R02 曾把 no_diff 档写成 refuted）。
- supersede 提交后：`python3 research/scripts/review_queue.py R??` 生成受影响清单（missing 阻断/stale 入队/legacy 告警 三档），只喂下一轮 P1 与讨论门；不改写历史、不自动触发实验。
- 记忆变更时机：默认轮末或独立 /ra-memory 会话；**P1–P8 期间不刷新 conclusions 与 md 投影**——轮中发生即 closure_broken，已启动的治理输入闭包作废。单提交原子化：批准 → 追加 → 刷投影 → 校验哈希 → git commit。

## 6 阶段产出格式
子代理最终消息的第一行是 <!-- ra:out Rnn/<相对路径>.md -->，其后是 front matter（round/phase/role），再后是正文。

### 6.1 P1
## 一句话结论
## 证据与分析（断言编号 F1, F2…，每条带 ev）
## 未核验项
## 已知局限
## 提议方向（≤3 条，每条：方向 | 最小可证伪实验 | 依据 ev | charter_trace）
## 章程外观察（可选，不进入计划）

### 6.2 P3（对另外两个角色各写一行）
| 对象 | 方向(支持/削弱/no_impact) | 幅度(高/中/低) | 一句话 | 依据 ev |

### 6.3 P4（每条提案）
### <角色首字母+序号，如 d1>：标题
- 类型：new | modify:<编号> | withdraw:<编号>
- parent：champion | <exp_id>
- 改动：相对 parent 的唯一改动，精确到配置项或代码位置
- 动机与证据：… ev:…
- 预期效果：主指标 <方向> <幅度>，合理区间 [a, b]；依据 ev:…
- 结果为负意味着：…
- 资源：<卡数> × <小时> = <GPU·h>；依据 ev:…（吞吐、步数）
- 种子：n=…；理由（对照 σ）
- 风险与混杂：…
- charter_trace: [G1, M2]

### 6.4 P5：见 ra-judge 的说明

### 6.5 P8
## 对本角色下一步的影响
## 训练期间需要监控的信号（对应 abort 条件编号）
## CR 草稿（如有）

## 7 统计与决策默认规则（ERC 可以收紧，不可以放宽）
1. 对照：ERC 的 parent（默认是 champion），种子集合、训练步数、样本数、有效 batch 都相同，除非改动的正是这些。
2. 种子：确认性比较每臂至少 3 个种子。parent 若已有同 commit、同配置、同种子的结果，可以复用；否则同轮重跑。
3. 主检验分两种情况：
   - 有逐样本预测：用配对 bootstrap，按样本重采样，n_boot=10000；每次重采样先对各种子取平均，再算 Δ。
   - 没有逐样本预测：在种子层面报告均值 ± sd，并做 Welch t 检验（n≥3）；n<3 时只能作为 exploratory。
4. 多重比较：同一轮的全部确认性比较一起做 Holm 校正。
5. 达标判据：以 ERC 的 success_criterion 为准。默认是"校正后 95% CI 下界 > 0，且护栏全部满足"。
6. champion 只有在实验达标、且研究员批准了对应的 CR 之后才能更新。
7. dev 查看计数：每基于 dev 结果做一次选择记 1 次，累计记在 STATUS.md。达到章程阈值时，brief 要提示研究员考虑做一次 test 确认（RL3）。
8. 禁止：事后更换指标、检验方法、checkpoint 规则或种子；只报告表现好的种子；把 exploratory 写成 confirmatory；中期因为效果好而提前停。
9. 未达标不等于无效。要写明在多大的效应量以上可以排除，并起草 NR。

## 8 可行性检查（每项 PASS/FAIL，附证据）
- L0 资源：
  - 本轮 Σ GPU·h ≤ 章程规定的单轮预算；
  - 卡分配不重叠，总数 ≤ 8，且不与运行中的作业冲突（证据：nvidia-smi 输出、runs.jsonl 中已开始未结束的记录）；
  - 预计 checkpoint 占用 < df 可用空间的 70%；
  - 墙钟时间 ≤ 上限；
  - 估算依据是历史日志中的吞吐（附 ev）。
- L1 有效性：
  - 训练数据不含 dev/test；改动了数据管线的实验，须由 skeptic 重新抽检；
  - 不触碰评测代码；
  - 外部数据或权重须已登记许可，且在章程允许范围内。
- L2 统计：种子数与预期 Δ、σ 相称；checkpoint 规则已声明；需要做多重比较校正的已声明。
- L3 依赖：
  - parent 的配置和 checkpoint 存在；
  - 配置能在 CPU 上解析；
  - 数据摘要（路径、文件数、大小）已记录；
  - 代码改动已实现，并将随锁定提交入库。
任一项 FAIL：对应实验退回修改，或移出计划，并在 brief 中列出。

## 9 风险分级与批准
资源承诺型副作用（GPU 训练、终止训练、test 评测、外部数据）一律由研究员把关。纯软件副作用（轮次文件、提案、代码改动）由权限规则和 git 把关。
| RL | 事项 | 批准方式 |
|---|---|---|
| RL0 | 读取、CPU 分析、写本轮文件、起草提案 | 不需要 |
| RL1 | 章程预授权范围内的 playbook 整理 | 在下一轮 brief 中报告 |
| RL2 | 在单轮预算内启动已锁定的实验；有 abort 证据的终止；新增 knowledge/negative/hypotheses；修改代理或技能的提示词；确认里程碑达成 | 研究员输入批准语句 |
| RL3 | 超出预算；test 评测；修改评测代码、数据或指标；修改章程、rubric、PROTOCOL 或变更条件；协议偏离；删除任何账本或结果 | 输入 批准(RL3) 语句并附理由；章程指定了第二确认人时，还须其亲自输入 |
批准语句的格式：
- 批准 R03: R03-E1, R03-E2[; 条件]
- 批准(RL3) R03: <列表>: 理由
- 驳回 R03: 理由
- 批准 CR-R03-01
- 批准重跑 R03-E1: 原因
- 批准提交 <对象> / 批准锁定 R03（提交与锁定确认的规范说法）
- 批准(RL3) 偏离 R03: 理由（缺阶段仍出决策属协议偏离；decision 前置门的放行条件，须研究员手动落盘）

批准语句所在 prompt 的 permission_mode 必须非 auto（auto 会话的输入不作批准凭据；开轮自检与 launch.sh 双重核验）。

## 10 受保护资产
| 资产 | Claude Code | Codex | 兜底 |
|---|---|---|---|
| 评测代码、dev 集 | deny Edit | — | OS 只读（安装第 5 步） |
| test 集 | deny Read | — | 不放在智能体可读的位置 |
| ledger/、hooks/、runs/、research/scripts/ | deny Edit/Write + guard hook 拦 Bash 重定向 | rules + hook | git 审计（只增）；chattr +a，不可用则 degraded＋git 对账补偿 |
| memory/conclusions.jsonl、ledger/results.jsonl | deny Edit/Write；仅白名单脚本追加（res_extract / commit_conclusion） | rules + hook | 同上；RES 免 CR（派生事实），conclusions 行必带 approval_ref |
| 章程、规则、记忆、代理、技能配置 | ask | AGENTS.md 中的规则 + on-request | git 审计 |
| GPU | CUDA_VISIBLE_DEVICES="" + 拒绝启动命令 | shell_environment_policy + rules forbidden | 模式 A 下只有研究员启动 |
| git 历史 | deny push/reset/rebase/amend | rules forbidden | — |

## 11 记忆
- knowledge.md：champion 与已确认的结论
- negative_results.md：只增不删
- hypotheses.md：假设及其状态
- playbook.md：操作经验
proposals/ 是收件箱，只有经 /ra-memory 批准的 CR 才能修改上面四个文件。
- conclusions.jsonl / results.jsonl（v2.5，见 §5.3）：结论版本层。假设状态词表 = open / pending / supported / confirmed / refuted / tested_flat / unresolved_*；refuted 重开（→ 非 refuted）须 proposed_by 含研究员并附批准。负结果候选先入 proposals/ 作 NR-draft，改判必须显式处置（登记或撤销并注明）。编号唯一性由 commit_conclusion.py 断言（同 id 复用不同 claim 即拒绝）。

## 12 命名
轮次 R01、R02…；实验 R03-E1；重跑 R03-E1.r2；假设 H-001；负结果 NR-001；已确认知识 K-001；变更提案 CR-R03-01；结论版本地址 H-003@v2；RES 行以 exp_id 为键（kind: res）。
