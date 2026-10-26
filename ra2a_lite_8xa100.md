# RA2A-Lite：8×A100 模型迭代项目包（Claude Code / Codex，开箱即用）

> 文档名：`ra2a_lite_8xa100.md`。由 `ra2a_261021.md` 派生，按 2026-10 的 Claude Code / Codex 公开文档编写，内容自包含。
> 字段名随版本变化。旧版本中不存在的字段一般会被忽略，关键的失效点由 §7 的 canary 实测暴露。

---

## 0 定位

**这是什么**：一套直接放进你现有模型仓库的配置与流程文件，包括规则、子代理、技能、权限、hook 和模板。装好后，Claude Code 或 Codex 担任**试验设计与结果分析搭档**，服务对象是本项目的优化目标，比如把主指标从基线提升到目标值。RA2A 原型里的治理方法都保留下来：八阶段评审、证据绑定、剪枝、预注册、可行性检查、章程锁、人工批准、负结果保护。

**这不是什么**：这不是 RA2A 平台的实现。没有 Conductor、Ledger 服务、MCP 控制面，也没有 Probe 程序。全部功能都由下面这些原生特性组合而成：
- `AGENTS.md` / `CLAUDE.md`
- 子代理
- 技能（skills）
- 权限规则 / Codex rules
- hooks
- git

需要自己维护的代码只有一个约 40 行的记账 hook（可以不装）和两个 shell 模板。模板每轮由智能体按格式生成，属于项目工件，不算工具开发。

**一轮人机交互 = 一个训练评测迭代**：

```
训练结束 → /ra-round → 分析上一轮结果（对照预注册）＋ 多角色评审设计本轮实验
        → 与你讨论 → 你输入「批准」 → 锁定预注册（git commit）
        → 你在终端启动训练 → 训练结束 → 下一次 /ra-round
```

**适用前提**：
- 单机 8×A100，Linux；
- 明确的主指标与目标值；
- 已有训练数据、评测集（dev，可选 test）、基线代码与历史试验日志；
- 仓库在 git 中，基线代码已提交。

---

## 1 从 RA2A 到本包：保留、替代、删除

强度说明：
- **强**：由 OS、脚本或权限层拒绝，不依赖模型自觉；
- **中**：权限规则或 hook 留痕，事后审计能发现违规；
- **软**：依赖模型遵守指令，再由 `/ra-audit` 事后核查。

| RA2A 组件 / 不变量 | 本包落地 | 用到的原生特性 | 强度 |
|---|---|---|---|
| Conductor 回合状态机（R15） | `/ra-round` 技能；每个阶段落盘为文件；`meta.yaml` 记录进度 | Skills、文件 | 软 + 审计 |
| Debate Bus（R6） | `research/rounds/Rnn/` 下按阶段分的文件。对话里说过、没落盘的不算数 | 文件 + git | 中 |
| Idempotency Ledger（R7） | `research/ledger/*.jsonl`、`runs/<exp>/STARTED`、git | hook、launch.sh | 强 |
| Evidence Store（R14） | `ev:` 文件指针 + git 版本 | 文件系统、git | 中 |
| MemoryGraph（R5/R8） | `research/memory/*.md`；变更只能经提案 → 批准 | 权限 ask、git | 中 |
| Feasibility Gate（R11） | `feasibility.md` 逐项检查，附命令输出作证据 | Bash | 软 + 审计 |
| HITL 审批（R12） | 只认研究员**亲自输入**的批准语句，由 UserPromptSubmit hook 记账；锁定提交和启动还会弹权限确认 | hooks、权限 ask | 中 |
| Charter Guard（R13） | 每个提案带 `charter_trace`，ra-verifier 核对；修改章程需确认 | 子代理、权限 ask | 中 |
| Prereg Registry（R17） | ERC（yaml）随锁定提交入库；launch.sh 拒绝未锁定或锁定后被改的实验 | git、shell | 强 |
| 输入闭包（R18） | 以下措施组合：<br>• P1 子代理并行、全新上下文；<br>• hook 把子代理最终消息原样落盘；<br>• 不 resume 子代理；<br>• 关闭 fork、自动记忆和后台任务；<br>• 审计时 grep 子代理 transcript | 子代理、hooks、env | 中 |
| Capability Probe（R19） | 每轮记录运行时版本；版本变了先跑 canary；核对控制文件 | Bash、git | 软 + 审计 |
| LLM 钉死（C-PIN） | 子代理 frontmatter 和 Codex TOML 写定 model/effort；建议用完整 ID；每轮记录 | frontmatter、config | 软 |
| Effector | 模式 A：研究员本人在终端运行 launch.sh（默认）。模式 B：Claude 运行，但须经权限确认 | `CUDA_VISIBLE_DEVICES=""` + 拒绝启动命令 | 强（A）/中（B） |
| Rubric Engine / Elo | 评委按维度打分，主会话用脚本重算中位数；Elo 改为"中位数 + 三种候选顺序" | 子代理、Bash | 中 |
| Lead 自搜核验（P6） | 由全新上下文的 ra-verifier 承担；主会话只编排，不提交自己的 P1 | 子代理 | 中 |
| 删除 | MCP 控制面/MRTR/Tasks、A2A、Managed Agents/Dreams/outcomes、动态工作流模板、Saga。单机单课题用不上 | — | — |

---

## 2 一轮交互的流程

```
 训练结束 ──► /ra-round R03
   ├─ 0  开轮自检：控制文件未被改、GPU 对智能体不可见、记录平台版本
   ├─ A  结果回收：ra-analyst 对照 R02 锁定的 ERC 做确认性分析 ──► A_results.md
   ├─ P1 独立评估：analyst / designer / skeptic 并行，全新上下文 ──► p1/*.md
   ├─ P2 广播：逐字摘录三方的一句话结论 ──► p2_broadcast.md
   ├─ P3 交叉影响：3×2 影响矩阵 ──► p3/*.md
   ├─ P4 修改意见：收敛为具体的候选实验 ──► p4/*.md
   ├─ P5 评分：匿名候选 × 3 名评委（三种顺序）→ 脚本取中位数 ──► p5/
   ├─ P6 汇总与核验：剪枝、ERC 草稿、可行性检查；ra-verifier 剥离无证据断言 ──► p6_synthesis.md erc/ feasibility.md
   ├─ ⏸ 人机讨论：brief.md（1 页）→ 讨论修订 → 你输入「批准 R03: …」
   ├─ P7 决策 ──► decision.md（写入前你确认）
   ├─ P8 决策影响与记忆提案 ──► p8/*.md、memory/proposals/
   ├─ I  实现：配置开关式的代码改动、CPU 自检、生成 exp 脚本与 launch.sh
   ├─ L  预注册锁定：git commit（你确认）
   └─ X  启动：你在终端运行 bash research/rounds/R03/launch.sh
 训练期间：/ra-status（只读：进度、GPU、abort 条件）
```

**你需要参与的地方**：⏸ 讨论门（10–30 分钟，亲自输入批准语句），以及研究流程上的人工决定点（RL3 事项、重跑、CR、里程碑确认，见 PROTOCOL §9）。除此之外**不要承诺"零弹窗"或固定次数**：工具层还会出现权限确认（如轮次 Python 脚本执行、decision.md 写入、git commit、受保护文件编辑、git tag 打标）——它们是权限系统的独立工具门，不是研究批准的重复要求；哪些操作免确认取决于 `.claude/settings.json` 的 allow 清单与本机权限模式（v2.4 起默认 default + 精确 allow，auto 临时禁用，见 `PATCH-v2.4.md`）。其余部分由智能体完成，耗时 20–60 分钟，主要取决于日志规模和所用模型。

---

## 3 安装（约 15 分钟）

**前置条件**：
- git、python3、tmux（推荐）；
- 最新版 Claude Code 或 Codex CLI；
- 仓库已提交，`git status` 干净。

**步骤**：

1. **保存文档**：把本文档存为仓库根目录下的 `ra2a_lite_8xa100.md`。

2. **生成文件**：在仓库根目录启动 `claude` 或 `codex`，输入：
   > 按 ra2a_lite_8xa100.md 第 5 章，逐字创建其中列出的全部文件（路径以每个代码块上方的标题为准；目录 research/ledger、research/memory/proposals/{applied,rejected}、research/rounds、research/audits 建为空目录并放 .gitkeep）。不要修改任何已有文件。完成后列出创建的文件。

3. **技能链接**（Claude Code 与 Codex 共用同一份技能）：
   ```bash
   ln -s ../.agents/skills .claude/skills
   ```
   如果 Claude Code 不识别符号链接，改为 `rm .claude/skills && cp -r .agents/skills .claude/skills`。

4. **受保护路径**：把 `.claude/settings.json` 里的 `./eval/**`、`./data/**`、`./data/test/**` 改成你的实际路径，见 §9。也可以先不改，`/ra-init` 会提议修改。

5. **OS 层保护**（强烈建议；Codex 用户必须做，因为 Codex 没有按路径的编辑拒绝）：
   ```bash
   # 评测代码与 dev 集：改为 root 所有、只读。之后要改须 sudo，等同于章程修订
   sudo chown -R root:root <评测代码目录> <dev集目录>
   sudo chmod -R a-w <评测代码目录> <dev集目录>
   # test 集：不放在智能体能读的位置。里程碑评测由研究员手动执行（见 §8.3）
   ```

6. **`.gitignore` 追加**：
   ```
   runs/**/*.pt
   runs/**/*.pth
   runs/**/*.bin
   runs/**/*.safetensors
   runs/**/checkpoint*/
   .claude/settings.local.json
   ```

7. **提交**：
   ```bash
   git add AGENTS.md CLAUDE.md .claude .agents .codex research .gitignore && git commit -m "add RA2A-Lite"
   ```

8. **重启** `claude` / `codex`，让设置、子代理、技能和 hooks 生效。
   - Codex：首次进入时信任本项目（项目层的 config/rules/hooks 只在信任后加载）；再执行 `/hooks`，审阅并信任 3 个 hook。

9. **首次接入**：执行 `/ra-init`。Codex 中输入 `$ra-init`，或用 `/skills` 选择，以所用版本为准。

10. **平台实测**：执行 `/ra-audit R00 canary`。全部 PASS 后，再开始 `/ra-round R01`。

---

## 4 目录结构

```
<repo>/
├─ AGENTS.md                      # 共用规则（Codex 原生读取；Claude 经 CLAUDE.md 导入）
├─ CLAUDE.md                      # @AGENTS.md + Claude 专用补充
├─ .claude/
│  ├─ settings.json               # 权限、环境、hooks
│  ├─ agents/ra-analyst.md ra-designer.md ra-skeptic.md ra-judge.md ra-verifier.md
│  └─ skills -> ../.agents/skills
├─ .agents/skills/ra-init ra-round ra-status ra-launch ra-memory ra-audit  (各含 SKILL.md)
├─ .codex/
│  ├─ config.toml  hooks.json  rules/ra.rules
│  └─ agents/ra-analyst.toml … ra-verifier.toml
├─ research/
│  ├─ PROTOCOL.md  charter.md  rubric.md  project_card.md  STATUS.md
│  ├─ templates/ meta.yaml erc.yaml brief.md decision.md cr.md exp.sh launch.sh
│  ├─ memory/ knowledge.md negative_results.md hypotheses.md playbook.md proposals/{applied,rejected}/
│  ├─ ledger/ human_inputs.jsonl subagent_outputs.jsonl runs.jsonl events.jsonl   # 只追加
│  ├─ hooks/ra_log.py
│  ├─ audits/
│  └─ rounds/R01/ meta.yaml A_results.md p1/ p2_broadcast.md p3/ p4/ p5/ p6/ p6_synthesis.md
│              erc/ feasibility.md brief.md decision.md p8/ exp/ launch.sh work/
└─ runs/<exp_id>/ STARTED COMMIT train.log seed*/ DONE|FAILED|ABORTED       # 由 launch.sh 写入
```

---

## 5 文件全文

> ⚠️ **本包代码块已同步至仓库当前版本（v2.4，2026-10-26）**：一致性由 `python3 research/runtime/checks/lite_doc_sync.py --check` 逐块校验（38 对，0 漂移）。历史差异（v2.3 修复补丁 P0-1a/b/c/d、P0-2、P1-1、P1-2、D10 与 v2.4 的 B0/B1 改造）逐项见 `PATCH-v2.3.md`、`PATCH-v2.4.md`（完整依据见 `conformance-final-verdict.md`）；版本索引见 `CHANGELOG.md`。charter/project_card/STATUS 为模板，实际文件按项目填写，不参与逐字比对。

### 5.1 `AGENTS.md`

~~~markdown
# 本仓库的 AI 协作规则（RA2A-Lite）

本项目的目标写在 research/charter.md（G1…）。你的身份是研究员的试验设计与结果分析助手，不是自主研究者。
开始任何研究任务前，先读 research/STATUS.md 和 research/charter.md。执行轮次流程前，还要读 research/PROTOCOL.md。

## 你可以做
- 阅读代码、配置、数据统计、历史日志和 runs/ 结果；在 CPU 上做分析。所有计算都写成脚本，放在本轮 work/ 目录下运行
- 起草试验设计、ERC、exp 脚本与 launch.sh；实现已批准实验所需的代码改动（用配置开关，默认值保持基线行为）
- 组织子代理评审，汇总并核验证据，与研究员讨论

## 你绝不能做
有权限规则和 OS 权限兜底，但你必须主动遵守。被拒绝之后，不得换一种写法绕过。
1. 启动、终止、重启任何训练、评测或 GPU 作业；占用 GPU。保持 CUDA_VISIBLE_DEVICES 为空。
2. 修改评测代码、评测数据、指标定义；读取 test 集；用 dev 或 test 数据训练、调参。
3. 修改 research/charter.md、rubric.md、PROTOCOL.md、templates/、memory/*.md、AGENTS.md、CLAUDE.md、.claude/、.agents/、.codex/，除非研究员在本次对话中明确同意了这一具体修改。
4. 替研究员写出、补全或推断"批准"。沉默、"好的"、"继续"都不算批准。
5. 删除或改写 research/ledger/、runs/、memory/negative_results.md 中的任何内容。
6. 在预注册锁定之后修改 ERC、exp 脚本或 launch.sh；以"结果看起来好"为由建议提前终止训练。
7. git push / reset / rebase / commit --amend / clean / restore。

## 工作方式
- 一个训练评测迭代 = 一次人机交互：/ra-round（Codex：ra-round 技能）。
- 证据：每条可证伪的陈述都带 ev: 指针（PROTOCOL §3）。没有证据就写"未核验"。
- 方向：每个提案必须写 charter_trace（G#/M#）。章程外的想法记入"章程外观察"，不进入计划。
- 工具确认：RL0（读取、CPU 分析、写本轮文件、起草提案）不需要研究员逐次确认工具调用；权限系统的确认弹窗是独立的工具门，不因已有研究批准而消失，也不构成研究批准（PROTOCOL §9 v2.4 注）。
- 草案与基线：实现类改动一律以配置开关交付、默认值保持基线行为；B2 隔离边界（update/final_modification_plan.md §5.1）落地后，草案实现须在隔离副本中准备。CPU 上的单元自检与分析不因运行在 CPU 上自动获得研究授权——在 CPU 上运行研究训练或评测仍是资源承诺型副作用，按 PROTOCOL §9 RL2/RL3 把关。
- 状态：每完成一个阶段就更新 research/STATUS.md。所有结论都要落盘，对话里说过的不算数。
- 记忆：新发现、负结果、经验只能写成 research/memory/proposals/CR-*.md，经 /ra-memory 由研究员批准后生效。
- 诚实：负结果、失败、不确定性照实报告；严格区分 confirmatory 与 exploratory。
- 语言：与研究员用中文交流；文件正文用中文，字段名用英文。

## 命令
/ra-init 首次接入 · /ra-round [Rnn] 一轮迭代 · /ra-status [Rnn] 训练进度 · /ra-memory 记忆变更 · /ra-audit [Rnn] [canary] 自检 · /ra-launch Rnn 模式 B 启动
~~~

### 5.2 `CLAUDE.md`

~~~markdown
@AGENTS.md

## Claude Code 专用补充
- 子代理在 .claude/agents/ra-*.md；技能目录 .claude/skills 是 .agents/skills 的符号链接。
- P1/P3/P4/P8 要在同一条消息里并行发起多个子代理调用。不要 resume 子代理，每次都新开。
- 讨论门可以用 AskUserQuestion 给研究员列选项；但"批准"必须由研究员亲自输入文字，点选不算。
- 上下文被压缩或会话恢复后，先重读 research/STATUS.md 和本轮目录，再继续。

## 权限模式（v2.4 起；依据与验收状态见 PATCH-v2.4.md、CHANGELOG.md）
- bypassPermissions 永久禁止。auto 模式在 B2 隔离验收与目标版本回归通过前**临时禁用**：settings.json 已设 `disableAutoMode: "disable"`（2026-10-26 起；2026-10-23 的 auto 放行裁决自此中止，恢复/回退步骤见 PATCH-v2.4.md）。
- 默认模式为 default；普通工作区编辑与只读命令已按精确 allow 减负（settings.json）。acceptEdits 候选配置存于 .claude/candidates/（不加载），须先通过 T01a/T01b 验收，再以新版本发布方式启用。
- 工具弹窗里的"切到 auto"选项只改变本会话工作模式（disableAutoMode 生效时会被拒绝，该行为待 T01b 实测），**永远不构成研究批准**；权限确认的"允许"点击同样不是研究批准。批准语句必须由研究员亲自在非 auto 会话输入。
- PermissionRequest / Notification hook 只记账（research/ledger/events.jsonl），不自动放行任何操作，也不构成批准来源。
~~~

### 5.3 `research/PROTOCOL.md`

~~~markdown
# RA2A-Lite 研究协议（本项目版）
protocol_version: lite-1.1（修改属于 RL3）

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
- 命令输出：先保存到本轮 work/<role>/ 下的文件，再引用该文件
"有证据"须同时满足三条：指针可解析；定位到的内容存在；内容确实包含或支持被引的数字或文本。
断言 = 可证伪的事实陈述，包括数字、比较、因果、"文献报告……"。建议可以不带证据，但必须建立在断言之上。

## 4 一句话结论
格式：[结论] 因为 [核心证据 ev:…]，置信度 [低/中/高]，若 [条件] 则失效
正则：^\[.+\] 因为 .*ev:\S+.*，置信度 (低|中|高)，若 .+ 则失效$

## 5 轮次阶段
| 阶段 | 执行者 | 输入（只给这些） | 产出 | 完成判据 |
|---|---|---|---|---|
| 0 开轮 | 主会话 | — | meta.yaml | 自检通过 |
| A 结果回收 | analyst | 上一轮的 erc/、decision.md、runs/<exp>/ | A_results.md | 每个已完成实验都有判定 |
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

v2.4 注（lite-1.1，工具确认与研究批准的关系）：
- RL0 的"不需要批准"指不需要研究员逐次确认的**工具调用**；权限系统的确认弹窗（Python 执行、decision 写入、git commit、受保护文件编辑等）是独立的工具门，不因研究批准而消失，也不构成研究批准。
- 实现类改动（I 阶段草案）一律以配置开关交付、默认值保持基线行为；B2 隔离边界（update/final_modification_plan.md §5.1）落地后，草案实现须在隔离副本中准备。
- CPU 上的单元自检、分析脚本不因运行在 CPU 上自动获得研究授权；在 CPU 上运行研究训练或评测仍属资源承诺型副作用，按本表 RL2/RL3 把关。

## 10 受保护资产
| 资产 | Claude Code | Codex | 兜底 |
|---|---|---|---|
| 评测代码、dev 集 | deny Edit | — | OS 只读（安装第 5 步） |
| test 集 | deny Read | — | 不放在智能体可读的位置 |
| ledger/、hooks/、runs/ | deny Edit | — | git 审计（只增） |
| 章程、规则、记忆、代理、技能配置 | ask | AGENTS.md 中的规则 + on-request | git 审计 |
| GPU | CUDA_VISIBLE_DEVICES="" + 拒绝启动命令 | shell_environment_policy + rules forbidden | 模式 A 下只有研究员启动 |
| git 历史 | deny push/reset/rebase/amend | rules forbidden | — |

## 11 记忆
- knowledge.md：champion 与已确认的结论
- negative_results.md：只增不删
- hypotheses.md：假设及其状态
- playbook.md：操作经验
proposals/ 是收件箱，只有经 /ra-memory 批准的 CR 才能修改上面四个文件。

## 12 命名
轮次 R01、R02…；实验 R03-E1；重跑 R03-E1.r2；假设 H-001；负结果 NR-001；已确认知识 K-001；变更提案 CR-R03-01。
~~~

### 5.4 `research/charter.md`

~~~markdown
---
charter_version: 1
signed_by: 【待定：研究员姓名】
signed_at: 【待定】
second_confirmer: 无            # RL3 需要第二确认人时填写姓名
---
# 研究目标章程
只有研究员可以修改。每次修改都在文末"修订记录"中写一行，属于 RL3。

## G 目标
- G1 主目标：在【dev 集名】上，把【主指标】从基线【x.xx】（ev:…）提升到 ≥【y.yy】，同时满足护栏 C1–C3。
- G2 次目标（可选）：【…】

## C 约束 / 护栏
- C1 【推理延迟 / 参数量 / 显存上限】
- C2 训练数据只能来自【训练数据目录】；引入外部数据或预训练权重须修订章程
- C3 评测代码【评测代码目录】与指标定义冻结

## 范围
- in_scope：【模型结构、优化器与调度、正则化、数据增强与采样、训练时长、蒸馏……】
- out_of_scope：【……】
- forbidden：
  - 用 dev/test 数据训练或调参；
  - 修改评测脚本或指标定义；
  - 依据 test 做选择；
  - 事后挑选种子或 checkpoint。

## M 里程碑
- M1 基线复现：≥3 个种子，得到噪声估计 σ。目标日期【…】
- M2 【…】

## 资源
- 硬件：本机 8×A100【40/80】GB；与他人共享：【是/否】；保留卡：【无】
- 单轮 GPU 预算：【例如 192】GPU·h；单实验上限：【例如 64】GPU·h；总预算：【…】GPU·h
- 单轮最长墙钟：【例如 24】h

## 运行方式
- launch_mode: A                 # A = 研究员手动执行 launch.sh；B = 经权限确认后由 Claude Code 执行
- protocol_mode: full            # full | lite（lite：P3 与 P4 合并，P5 用 2 名评委）
- dev_look_threshold: 【例如 8】   # dev 查看累计到此次数时，brief 提示考虑做 test 确认
- test_set_eval: researcher_only

## 记忆 / 技能 / 规则的变更条件（修改本节属于 RL3）
- 预授权：不改变含义的 playbook.md 格式整理与去重。可直接应用，在下一轮 brief 中报告
- RL2：新增 knowledge、negative_results、hypotheses 条目；更新 champion；修改代理或技能的提示词
- RL3：修改 rubric.md、charter.md、PROTOCOL.md、评测相关内容，以及本节本身

## 修订记录
| 版本 | 日期 | 修改 | 理由 |
|---|---|---|---|
~~~

### 5.5 `research/rubric.md`

~~~markdown
# 评分规则库
rubric_version: lite-2026.10.1   （修改属于 RL3）

| 维度 | 1 | 3 | 5 |
|---|---|---|---|
| cost 资源（分高 = 省） | 占单轮预算 ≥50%，或墙钟 ≥24h | 占单轮预算 10–25% | 占单轮预算 <5%，且墙钟 <2h |
| impact 对目标与里程碑的影响 | 与 G/M 没有直接关系 | 可能推进当前里程碑 | 决定下一里程碑能否达成 |
| info_gain 信息增益（必须引证据） | 结果几乎可以预见，或已经知道（包括已有的负结果） | 结果会影响一个后续选择 | 无论结果正负，都会显著改变后续路线 |
| validity 结论可信度 | 混杂严重，或预计 Δ 落在噪声内 | 混杂可控，种子数勉强够 | 单因素、同预算对照、种子数充足 |
2 分和 4 分是中间档。

total = 0.20*cost + 0.30*impact + 0.30*info_gain + 0.20*validity
- 聚合：每维取评委打分的中位数；任一维评委极差 ≥ 2，即标"分歧"，在 brief 中交研究员裁决。
- 入选门槛：total ≥ 3.0 且 validity ≥ 3。不达门槛的按 prune:debate_outcome 处置，研究员可以推翻。
- 一句话结论的格式见 PROTOCOL §4。
~~~

### 5.6 `research/project_card.md`（模板，由 /ra-init 填写）

~~~markdown
# 项目卡：事实记录，由 /ra-init 生成，研究员确认后生效
## 1 代码与入口
- 训练命令模板：`…`（ev:…）；分布式启动方式：…
- 评测命令模板：`…`（ev:…）；checkpoint 命名与选择：…
- 配置系统及覆盖方式：…
## 2 数据
| 集合 | 路径 | 规模 | 摘要（文件数/大小/哈希前 12 位） | 备注 |
- 重叠检查：方法、结果（ev）
- 是否有逐样本预测输出：是/否（位置）
## 3 指标
- 主指标的实现位置（ev:…#L..）；护栏指标：…
## 4 历史结果（来自试验日志）
| run | 配置要点 | commit | 种子 | 主指标 | 步数 | 墙钟 | GPU·h | ev |
## 5 噪声与吞吐
- 种子标准差 σ = …（依据：同配置 n 个种子，ev）；未知时写"未知，建议 R01 做基线复现"
- 吞吐：… 样本/s/卡；一次完整训练约 … GPU·h（ev）
## 6 已知的失败与负结果（候选项，确认后经 CR 写入 negative_results.md）
## 7 待研究员确认的问题
~~~

### 5.7 `research/STATUS.md`

~~~markdown
# 当前状态（每个阶段结束时更新；会话开始、恢复、压缩后由 hook 自动注入）
- 当前轮次：无（尚未执行 /ra-init）
- 阶段：-
- 等待：研究员执行 /ra-init
- 运行中实验：无
- 最近一次 lock_commit：-
- dev 查看次数（累计）：0
- 单轮预算 / 本轮已用 GPU·h：- / -
- 待处理记忆提案：0
- 运行时版本：-
- 包版本：v2.4（版本说明见 CHANGELOG.md；本字段随版本发布更新，其余字段由 /ra-* 流程维护）
~~~

### 5.8 `research/memory/`

`research/memory/knowledge.md`

~~~markdown
# 已确认知识（只能经 /ra-memory 批准后变更）
## Champion（当前最佳的已确认配置）
| 字段 | 值 |
|---|---|
| 配置 / commit | - |
| 主指标（dev，均值±sd，n） | - |
| 来源 | - |
## 已确认结论
（K-001 …，每条注明来源轮次与 ev）
~~~

`research/memory/negative_results.md`

~~~markdown
# 负结果（只增不删；需要更正时追加"条件说明"）
| id | 轮次 | 改动 | 结果（Δ, CI, n） | 条件（数据规模/步数/parent） | 可排除的效应大小 | ev |
|---|---|---|---|---|---|---|
~~~

`research/memory/hypotheses.md`

~~~markdown
# 假设
| id | 假设 | 状态（open/supported/refuted/superseded） | 依据 ev | 相关实验 |
|---|---|---|---|---|
~~~

`research/memory/playbook.md`

~~~markdown
# 操作经验（程序性记忆：如何高效评测、常见的坑……）
~~~

### 5.9 `research/templates/`

`research/templates/meta.yaml`

~~~yaml
round: R00
parent_round: null
parent_lock_commit: null
started_at: ""
protocol_mode: full
charter_blob: ""            # git hash-object research/charter.md
rubric_version: ""
runtime: {name: "", version: ""}   # claude_code | codex；版本取自 claude --version / codex --version
models: {lead: "", ra-analyst: "", ra-designer: "", ra-skeptic: "", ra-judge: "", ra-verifier: ""}
platform_changed: false
last_phase: "0"
dev_looks_this_round: 0
~~~

`research/templates/erc.yaml`

~~~yaml
# 预期结果卡（ERC）。随本轮的 lock commit 入库即为锁定。锁定后修改 = 协议偏离（新版本 + 重新批准）
exp_id: R03-E1
round: R03
version: 1
title: ""
hypothesis_ref: H-000
charter_trace: [G1]
parent: {exp: champion, config: "", commit: ""}
change: "相对 parent 的唯一改动"
implementation: {kind: config_only, files: [], flag: ""}   # kind: config_only | code_change
seeds: [1, 2, 3]
budget: {gpu_ids: "0,1,2,3", est_wall_h: 0, est_gpu_h: 0, basis: "ev:…"}
checkpoint_rule: last            # last | dev_best（dev_best 有乐观偏差，分析时须注明）
primary_metric:
  name: ""
  split: dev
  direction: increase
  expected_delta: ""
  plausible_range: ["", ""]
  basis: ["ev:…"]
guardrails: [{name: "", rule: ""}]
analysis_plan:
  compare_to: parent             # 同种子、同步数
  unit: per_example_paired_bootstrap   # 没有逐样本预测时：seed_level
  n_boot: 10000
  alpha: 0.05
  correction: holm
success_criterion: "holm 校正后 Δ 的 95% CI 下界 > 0，且护栏全部满足"
stopping:
  planned_end: {steps: 0}
  interim_looks: []              # 例：[{at: 0.5, purpose: futility_only}]
  abort_conditions:
    - {id: A1, kind: technical_fault, rule: "loss 为 NaN/Inf"}
    - {id: A2, kind: resource_overrun, rule: "实耗 GPU·h > 1.3 × est_gpu_h"}
    - {id: A3, kind: data_fault, rule: "数据加载报错，或样本数与 project_card 不符"}
    # 可选类型（ra2a_261021 §9.4）：safety_or_ethics（如 adverse_event_reported）、
    # futility（如 at 50% steps, upper CI of effect < 0；interim_looks 只许 futility_only）
exploratory_allowed: []
evidence_refs: []
rubric_version: ""
~~~

`research/templates/brief.md`

~~~markdown
# R?? 人机讨论简报（≤80 行）
## 0 一句话：上一轮说明了什么 / 本轮建议做什么 / 共计多少 GPU·h（占预算几成）
## 1 上一轮的确认性结果
| exp | Δ（校正后 CI） | 判定 | GPU·h 实耗/预计 | 偏离 |
## 2 本轮的关键发现（已核验，带 ev）
## 3 被剥离的断言（不作为决策依据）
## 4 候选实验与评分
| C | 标题 | 改动 | 预期 Δ | GPU·h | cost | impact | info | validity | total | 分歧 | 建议 |
## 5 剪枝与处置
## 6 章程拦截
## 7 可行性（L0–L3）
## 8 建议计划：GPU 分配、时间线、合计 GPU·h / 预算、dev 查看次数、距下一里程碑
## 9 需要你决定的问题（≤5 个）
## 10 如何回复：`批准 R??: <exp 列表>` / `批准(RL3) …: 理由` / `驳回 R??: 理由` / 直接提出修改
## 讨论修订记录
| # | 时间 | 研究员意见 | 修改内容 | 是否复核 |
~~~

`research/templates/decision.md`

~~~markdown
---
round: R??
phase: P7
status: approved          # approved | rejected
decided_at: ""
risk_level: RL2
charter_blob: ""
rubric_version: ""
---
# R?? 决策
## 研究员批准原文（逐字）
> ……（时间，research/ledger/human_inputs.jsonl 中的对应记录）
## 批准执行的实验
| exp_id | 标题 | GPU | 预计 GPU·h | ERC |
## 未执行项及理由（剪枝 / 驳回 / 待补证据 / 超预算顺延）
## 剥离的断言
## 章程拦截
## 讨论中的修订
## RL3 理由与第二确认（如适用）
~~~

`research/templates/cr.md`

~~~markdown
---
id: CR-R??-01
target: research/memory/negative_results.md
kind: add_negative        # add_negative | add_knowledge | update_champion | hypothesis_status | playbook | agent_prompt | skill | rubric
risk: RL2
status: pending           # pending | applied | rejected
proposed_by: ""
---
## 变更内容（逐字，应用时原样写入）
## 理由与证据（ev）
## 影响
## 批准记录（由 /ra-memory 填写）
~~~

`research/templates/exp.sh`（每个实验一份，由 ra-round 按 project_card 的命令模板填写）

~~~bash
#!/usr/bin/env bash
# __EXP__ | ERC: research/rounds/__ROUND__/erc/__EXP__.yaml | 锁定后不得修改
# 由 launch.sh 设置 EXP 和 CUDA_VISIBLE_DEVICES；所有输出都写到 runs/$EXP/
set -euo pipefail
CFG=research/rounds/__ROUND__/exp/__EXP__.yaml
NPROC=$(echo "$CUDA_VISIBLE_DEVICES" | tr ',' '\n' | wc -l)
for SEED in 1 2 3; do                 # 必须等于 ERC.seeds
  OUT=runs/$EXP/seed$SEED
  # 训练：命令模板取自 project_card §1；--standalone 会自动选空闲端口，可与其他实验并行
  torchrun --standalone --nproc_per_node=$NPROC <训练入口> --config "$CFG" --seed $SEED --output_dir "$OUT"
  # 评测：使用冻结的评测入口；checkpoint 按 ERC.checkpoint_rule 选取
  python <评测入口> --ckpt "$OUT/<ckpt>" --split dev --output "$OUT/eval_dev.json"
done
~~~

`research/templates/launch.sh`

~~~bash
#!/usr/bin/env bash
# RA2A-Lite 启动脚本。ra-round 替换 __ROUND__ 和"实验清单"后存为 research/rounds/<R>/launch.sh，随锁定提交入库。
# 用法：bash research/rounds/<R>/launch.sh                       启动全部已批准实验（已启动过的自动跳过）
#       bash research/rounds/<R>/launch.sh retry <新id> <源id>    技术故障重跑（须先在 retries.md 登记批准并提交）
# v2.3 修复（P0-1a）：__run 需携带 start_exp 发放的一次性令牌（三重前置校验，堵"空对空"与无参直调）；
#                      启动前 check_approval 核验账本批准原文（锚定正则 + 非 auto + 早于锁定提交 + exp 集合覆盖）。
#                      依据：/data/wangshirui/ra2a/check/demo-conformance-final-verdict.md §3 P0-1a
set -euo pipefail
ROUND=__ROUND__
cd "$(git rev-parse --show-toplevel)"
RD=research/rounds/$ROUND
LEDGER=research/ledger/runs.jsonl
log() { printf '{"ts":"%s","exp_id":"%s","event":"%s","gpus":"%s","commit":"%s","rc":%s}\n' \
        "$(date -Is)" "$1" "$2" "${3:-}" "${4:-}" "${5:-null}" >> "$LEDGER"; }

if [ "${1:-}" = "__run" ]; then            # 内部入口：在 tmux/nohup 中实际运行一个实验（须携带一次性令牌）
  EXP=$2; GPUS=$3; SCRIPT=$4; TOKEN_ARG="${5:-}"; DIR=runs/$EXP
  # 三重前置：令牌参数非空 + .token 存在且非空 + 内容一致（v2.1 修正：两侧皆空会使比较为真）
  if [ -z "$TOKEN_ARG" ] || [ ! -s "$DIR/.token" ] || [ "$TOKEN_ARG" != "$(cat "$DIR/.token")" ]; then
    echo "✗ __run 令牌缺失或不符。智能体会话请勿直接调用 __run；启动入口是 bash research/rounds/$ROUND/launch.sh"; exit 1
  fi
  export EXP CUDA_VISIBLE_DEVICES=$GPUS
  set +e; bash "$SCRIPT" > "$DIR/train.log" 2>&1; rc=$?; set -e
  if [ $rc -eq 0 ]; then ev=DONE; else ev=FAILED; fi
  date -Is > "$DIR/$ev"; log "$EXP" "$ev" "$GPUS" "$(cat "$DIR/COMMIT")" "$rc"; exit $rc
fi

# ---- 启动者检查：智能体会话只有在 launch_mode=B 且运行时为 Claude Code 时才能启动 ----
AGENT=0
if [ -n "${CLAUDECODE:-}" ] || [ -n "${CODEX_SANDBOX:-}" ] || [ -n "${CODEX_SANDBOX_NETWORK_DISABLED:-}" ]; then AGENT=1; fi
if [ "${CUDA_VISIBLE_DEVICES+set}" = set ] && [ -z "${CUDA_VISIBLE_DEVICES}" ]; then AGENT=1; fi
MODE=$(grep -E '^- launch_mode:' research/charter.md | awk '{print $3}')
if [ "$AGENT" = 1 ] && { [ "$MODE" != B ] || [ -z "${CLAUDECODE:-}" ]; }; then
  echo "✗ 检测到智能体会话环境（launch_mode=${MODE:-?}）。请研究员在自己的终端运行本脚本。"; exit 1
fi

# ---- 预注册与代码检查 ----
[ -z "$(git status --porcelain -- "$RD")" ] || { echo "✗ 本轮文件有未提交或被修改的内容（未锁定，或锁定后被改）"; exit 1; }
git ls-files --error-unmatch "$RD/launch.sh" >/dev/null 2>&1 || { echo "✗ launch.sh 未提交"; exit 1; }
grep -q '^status: approved' "$RD/decision.md" || { echo "✗ decision.md 不是 approved 状态"; exit 1; }
git diff --quiet HEAD -- . ':(exclude)research' ':(exclude)runs' || { echo "✗ 有未提交的代码改动"; exit 1; }
[ -z "$(git ls-files --others --exclude-standard -- '*.py')" ] || { echo "✗ 有未跟踪的 .py 文件"; exit 1; }
COMMIT=$(git rev-parse HEAD)

# ---- 批准核验（v2.3 P0-1a①）：decision.md 的 approved 状态必须有人类批准原文背书 ----
# 四重校验：锚定正则（覆盖 批准 R03: 与 批准(RL3) R03:，前导"不/勿/别/驳回"判负）；
#           permission_mode ≠ auto（auto 会话的输入不作批准凭据，P0-2）；
#           批准 ts 早于锁定提交；start_exp 清单中每个实验都出现在批准语句里。
check_approval() {
  local EXPS
  EXPS=$(grep -E '^start_exp ' "$0" | awk '{print $2}' | paste -sd, -)
  python3 - "$ROUND" "$EXPS" <<'PYEOF'
import json, re, subprocess, sys
from datetime import datetime
rnd, exps = sys.argv[1], [e for e in sys.argv[2].split(",") if e and not e.startswith("__")]
pat = re.compile(r"^\s*批准(\s*\(RL3\))?\s+" + re.escape(rnd) + r"\s*[:：]")
def parse_ts(s):
    s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", (s or "").strip())
    try: return datetime.fromisoformat(s)
    except ValueError: return None
lock = subprocess.run(["git", "log", "-1", "--format=%cI", "--", "research/rounds/" + rnd],
                      capture_output=True, text=True).stdout.strip()
lock_dt = parse_ts(lock)
try:
    fh = open("research/ledger/human_inputs.jsonl", encoding="utf-8")
except FileNotFoundError:
    sys.exit("✗ 找不到 research/ledger/human_inputs.jsonl，无法核验批准")
ok, approved = False, set()
for line in fh:
    try: r = json.loads(line)
    except Exception: continue
    p = r.get("payload") or {}
    pr = (p.get("prompt") or "").strip()
    if not pat.match(pr): continue
    if pr.startswith(("不", "勿", "别", "驳回")): continue
    if (p.get("permission_mode") or "") == "auto": continue
    if lock_dt and (parse_ts(r.get("ts")) or lock_dt) > lock_dt: continue
    ok = True
    approved |= set(re.findall(re.escape(rnd) + r"-E\d+(?:\.\d+)?", pr))
if not ok:
    sys.exit(f"✗ 账本中无 {rnd} 的合格批准语句（须为非 auto 权限模式、早于锁定提交的 批准/批准(RL3) 原文）")
missing = [e for e in exps if e not in approved]
if missing:
    sys.exit("✗ 以下实验未出现在批准语句中: " + ", ".join(missing))
PYEOF
}
check_approval

start_exp() {   # start_exp <exp_id> <gpu_ids> <exp脚本的完整相对路径>
  local EXP=$1 GPUS=$2 SCRIPT=$3 DIR=runs/$1
  if [ -e "$DIR/STARTED" ]; then echo "• 跳过 $EXP：已启动过（幂等）"; return 0; fi
  if [ -n "$(nvidia-smi -i "$GPUS" --query-compute-apps=pid --format=csv,noheader 2>/dev/null)" ]; then
    echo "✗ $EXP：GPU $GPUS 上已有进程，未启动"; return 1; fi
  mkdir -p "$DIR"; date -Is > "$DIR/STARTED"; echo "$COMMIT" > "$DIR/COMMIT"
  local TOKEN; TOKEN=$(head -c16 /dev/urandom | od -An -tx1 | tr -d ' \n')   # hex，避免 NUL 进 argv
  printf '%s' "$TOKEN" > "$DIR/.token"                                        # 无尾换行（对 diff/hash 校验保持确定）
  log "$EXP" STARTED "$GPUS" "$COMMIT"
  if command -v tmux >/dev/null; then
    tmux new-session -d -s "$EXP" "bash $RD/launch.sh __run $EXP $GPUS $SCRIPT $TOKEN"
    echo "✓ 已启动 $EXP（GPU $GPUS）。查看：tmux attach -t $EXP；日志：$DIR/train.log"
  else
    nohup bash "$RD/launch.sh" __run "$EXP" "$GPUS" "$SCRIPT" "$TOKEN" >/dev/null 2>&1 &
    echo "✓ 已启动 $EXP（GPU $GPUS，nohup）。日志：$DIR/train.log"
  fi
}

if [ "${1:-}" = "retry" ]; then
  NEW=$2; SRC=$3
  git ls-files --error-unmatch "$RD/retries.md" >/dev/null 2>&1 && grep -q "^| *$NEW *| *$SRC *|" "$RD/retries.md" \
    || { echo "✗ $NEW 未在已提交的 retries.md 中登记批准"; exit 1; }
  SPEC=$(grep -E "^start_exp $SRC " "$0" | head -1 || true)
  [ -n "$SPEC" ] || { echo "✗ 找不到源实验 $SRC"; exit 1; }
  set -- $SPEC; start_exp "$NEW" "$3" "$4"; exit 0
fi

# ---- 已批准实验清单（与 decision.md、erc/ 一一对应；路径写全，不用变量）----
start_exp __ROUND__-E1 0,1,2,3 research/rounds/__ROUND__/exp/__ROUND__-E1.sh
start_exp __ROUND__-E2 4,5,6,7 research/rounds/__ROUND__/exp/__ROUND__-E2.sh
# 需要在同一组卡上串行的实验，合并进同一个 exp 脚本；或者等前一个结束后再运行一次本脚本（已启动的会跳过）
~~~

### 5.10 子代理 `.claude/agents/`

> 不要加 `memory:` 字段，也不要在 tools 中加入 `Agent`：子代理既不应有持久记忆，也不应再派生子代理。
> `model` 默认用别名，装好就能运行；建议换成完整模型 ID，避免别名漂移。

`.claude/agents/ra-analyst.md`

~~~markdown
---
name: ra-analyst
description: RA2A-Lite 结果与日志分析员。阶段 A 对照锁定的 ERC 做确认性分析；P1/P3/P4/P8 提供数据诊断视角。只在 ra-round / ra-init 流程中由主会话调用。
tools: Read, Grep, Glob, Bash, Write
model: opus
effort: high
maxTurns: 40
---
你是 ra-analyst，本项目的结果与日志分析员。你的任务是让研究员准确知道实验说明了什么、没说明什么。

开始前：读 research/PROTOCOL.md 的 §2、§3、§4、§6、§7，以及任务里给出的文件。

边界
- 只读以下内容：项目代码、runs/、历史日志、任务指明的 research/ 文件。任务没有给出的本轮其他角色文件，一律不读。
- 只能写 research/rounds/<R>/work/analyst/。所有计算都写成脚本放在这里，再用 `python3 research/rounds/<R>/work/analyst/<脚本>.py` 运行，输出也存在这里。
- 只用 CPU：不启动训练或评测，不设置 CUDA_VISIBLE_DEVICES。
- 最终消息的第一行，原样写任务给出的 `<!-- ra:out … -->`。最终消息就是正式存档，必须完整自洽，不能写"见上文"。

阶段 A：确认性分析
1. 对每个 ERC，严格按 analysis_plan 执行：对照对象、指标、检验方法、校正方式、checkpoint 规则都不能换。ERC 写得无法执行的，判"无法判定"，并说明原因。
2. 逐个 exp_id 输出：
   | exp_id | 各种子值 | 均值 | Δ vs parent | 校正后 95% CI | 判定(达标/未达标/无法判定) | 护栏 | GPU·h 实耗/预计 | 偏离 |
   偏离包括：种子缺失、步数不足、命中 abort 条件、ERC 在锁定后被改。
3. ERC 里没有声明的分析，全部放进"探索性发现（exploratory）"一节，单独列出。
4. 末尾的"CR 草稿"一节写两类内容：未达标的，写 NR 草稿，含可排除的效应大小；达标的，写 champion 更新草稿。

P1 视角：诊断瓶颈。包括：训练曲线反映的欠拟合、过拟合或不稳定；误差切片（有逐样本预测时）；与 champion 的差距来自哪里；现有噪声水平能否支撑下一步的结论。
P3/P4/P8：按 PROTOCOL §6 的格式。你的提案偏向诊断性实验，也就是能解释现象、降低不确定性的实验。
~~~

`.claude/agents/ra-designer.md`

~~~markdown
---
name: ra-designer
description: RA2A-Lite 试验设计者。提出每 GPU·h 信息增益最高、最能逼近里程碑的下一批实验。只在 ra-round 流程中由主会话调用。
tools: Read, Grep, Glob, WebSearch, WebFetch
model: opus
effort: high
maxTurns: 40
---
你是 ra-designer。目标：在章程预算内，提出最能逼近下一里程碑、每 GPU·h 信息增益最高的实验。

开始前：读 research/PROTOCOL.md 的 §2、§3、§4、§6、§7、§8，以及任务里给出的文件。
边界：只读，不写任何文件。任务没有给出的本轮其他角色文件，一律不读。可以检索文献，外部来源写成 ev:web:<URL>#"<原文片段>"，并标注[外部]。最终消息第一行原样写任务给出的 `<!-- ra:out … -->`。

设计原则
1. 先读 research/memory/negative_results.md 和 knowledge.md。已被否定的方向不得原样再提；确要重提，必须写明条件差异和新证据。
2. 单因素优先：相对 parent 只改一处。采用析因设计时，要说明理由。
3. 改动尽量通过配置开关实现，默认值保持基线行为。
4. 资源估计必须有依据：用历史日志中的吞吐和步数算出 GPU·h（附 ev），并写清 8 张卡怎么分配，比如两组各 4 卡并行，或者 8 卡跑一个实验。
5. 写明预期效果（方向、幅度、合理区间）及其依据。这部分将成为预注册内容。
6. 写明"结果为负时我们能学到什么"。无论结果正负都有信息量的实验，优先安排。
7. 每条提案都带 charter_trace。章程外的好想法放进"章程外观察"。

P1：给出不超过 3 个方向，每个附上最小的可证伪实验。P4：收敛成 3–8 个具体候选（PROTOCOL §6.3）。P3/P8：按 §6 的格式。
~~~

`.claude/agents/ra-skeptic.md`

~~~markdown
---
name: ra-skeptic
description: RA2A-Lite 红队审稿人。在消耗 GPU 之前，找出会让结论不可信或浪费资源的问题。只在 ra-round / ra-init 流程中由主会话调用。
tools: Read, Grep, Glob, Bash, Write
model: opus
effort: high
maxTurns: 40
---
你是 ra-skeptic，红队审稿人。

开始前：读 research/PROTOCOL.md 的 §2、§3、§4、§6、§7、§8，以及任务里给出的文件。
边界：只读；检查脚本写在 research/rounds/<R>/work/skeptic/，只在 CPU 上运行。任务没有给出的本轮其他角色文件，一律不读。不读 test 集；需要做 test 重叠检查时，给出命令，由研究员执行。最终消息第一行原样写任务给出的 `<!-- ra:out … -->`。

检查清单（挑与当前任务相关的项；每项结论都带证据，查过但不成立的担心也要写明）
1. 噪声：声称的 Δ 是否落在种子标准差 σ 之内（σ 见 project_card）？种子数够不够？
2. 混杂：对照的步数、数据量、有效 batch、lr 调度是否一致？改动有没有顺带改了别的东西？（看 git diff 和配置 diff）
3. 泄漏：训练集与 dev 是否有重叠（用哈希抽检）？累计 dev 查看次数是否已经造成隐式调参？
4. 评测有效性：checkpoint 选择规则是否合理？评测代码有没有被改过（看 git log）？有没有指标投机的空间？
5. 资源与故障：OOM、NaN、磁盘空间、与运行中的作业抢卡。
6. 可复现性：有没有未提交的代码？随机性是否受控？数据版本是否记录？
7. 方向漂移：提案能否追溯到章程的 G/M？是否落在 out_of_scope 内？
8. 负结果遗忘：是否在重提已经被否定的方向？
P3/P4/P8：按 PROTOCOL §6 的格式；你的提案可以是修改、撤回他人提案，也可以是补充的对照实验。
~~~

`.claude/agents/ra-judge.md`

~~~markdown
---
name: ra-judge
description: RA2A-Lite P5 评委。按 research/rubric.md 对匿名候选实验逐维打分，不排名。只在 ra-round 的 P5 中由主会话调用。
tools: Read, Grep, Glob
model: sonnet
effort: medium
maxTurns: 20
---
你是 ra-judge，只负责一件事：按 rubric 给任务指定的候选文件逐维打分。

1. 依次读 research/rubric.md、research/charter.md、research/memory/negative_results.md、research/memory/knowledge.md，最后读候选文件。
2. 按文件中的顺序逐个评分。顺序已被打乱，用来抵消位置偏差。不要猜测是谁提出的。
3. 每维给 1–5 的整数分，并附一句理由。info_gain 必须引用候选附带的证据，或你自己在仓库中找到的证据（ev:）。
4. 不计算总分、不排名、不推荐。汇总由主会话用代码完成。
5. 需要时打标记：charter（章程问题）、neg_repeat（重提负结果）、confound（设计混杂）、budget（资源估计可疑）。
输出：第一行原样写任务给出的 `<!-- ra:out … -->`，然后只给一张表：
| 候选 | cost | impact | info_gain | validity | 标记 | 理由（每维一句，含 ev） |
~~~

`.claude/agents/ra-verifier.md`

~~~markdown
---
name: ra-verifier
description: RA2A-Lite P6 核验员。逐条核验汇总稿、ERC 与可行性检查中断言的证据指针及章程映射，输出保留/剥离清单。只在 ra-round / ra-memory 流程中由主会话调用。
tools: Read, Grep, Glob, Bash, WebFetch
model: opus
effort: high
maxTurns: 40
---
你是 ra-verifier。你不提出实验，只判断"这句话有没有证据"。

对任务给出的每个文件里的每条断言（可证伪的事实陈述），依次判断：
1. 有没有指针。没有 → stripped(no_pointer)
2. 指针能否解析：文件、行号或键是否存在；git 指针用 git show 检查。不能 → stripped(unresolvable)
3. 定位到的内容是否包含或支持被引的数字或文本。数字要逐位比对。派生数字须能由给出的脚本或简单计算复现：可以用 `python3 research/rounds/...` 运行，但只输出到 stdout，不覆盖已有文件。对不上 → stripped(mismatch)
4. ev:web 指针用 WebFetch 打开，查找引文片段。找不到 → stripped(unresolvable)；找到 → ok[外部]
另外还要检查：
- 每个候选或 ERC 的 charter_trace 都存在于 charter.md 中，且没有落入 out_of_scope 或 forbidden。不满足 → intercepted
- ERC 字段完整；success_criterion 能被确定性地判定；abort_conditions 能从日志判定
- 资源估计的算式与其依据一致
输出：第一行原样写任务给出的 `<!-- ra:out … -->`，然后给一张表：
| id | 文件:位置 | 断言摘要 | ev | 结论(ok / ok[外部] / stripped(原因) / intercepted) | 说明 |
最后给出统计，以及"必须修改才能进入计划"的项目。
~~~

### 5.11 技能 `.agents/skills/`

> Claude Code 经符号链接读取这些技能，Codex 原生读取。`disable-model-invocation` 和 `argument-hint` 是 Claude 的扩展字段，Codex 会忽略。如果 Codex 报错，在 Codex 用的副本中删掉这两个字段即可。

`.agents/skills/ra-init/SKILL.md`

~~~markdown
---
name: ra-init
description: 首次接入本项目。只读盘点代码、数据、评测与历史日志，生成 research/project_card.md，起草章程、保护配置和初始记忆提案，交研究员确认。仅在研究员显式调用时使用。
disable-model-invocation: true
---
# /ra-init：只读盘点并起草，不改代码，不启动任何作业

1. 读 AGENTS.md、research/PROTOCOL.md、research/charter.md（模板）。
2. 盘点以下内容（可以并行调用内置的探索子代理）：
   a. 训练入口、配置系统、分布式启动方式及 8 卡用法；
   b. 评测入口、主指标与护栏指标的实现位置（文件:行）、checkpoint 选择方式；
   c. 训练集、dev、test 的位置、规模、格式（test 只记录元信息，不读内容），是否有逐样本预测输出；
   d. 历史试验日志：位置与格式。逐个 run 提取配置要点、commit、种子、主指标、步数、耗时；
   e. 当前 git 状态。有未提交改动的必须报告。
3. 调用 ra-analyst，计算三项：种子噪声 σ（同配置少于 2 个种子时标"未知"）；吞吐与单次训练的 GPU·h；历史最佳结果，作为 champion 候选。
   prompt 只含：目录指针 + 输出指令 `<!-- ra:out R00/baseline_analysis.md -->`。
4. 调用 ra-skeptic，做两项检查：训练集与 dev 的重叠抽检（CPU，哈希）、评测代码完整性检查。test 的重叠检查只给出命令，交研究员执行。
   输出指令：`<!-- ra:out R00/integrity.md -->`
5. 写 research/project_card.md，每个事实都带 ev。
6. 起草以下内容：
   - charter.md 中可由事实推出的字段（指标、基线值、数据路径、硬件）。目标值、预算、里程碑、范围、launch_mode 保留【待定】，在对话中逐项询问研究员；
   - .claude/settings.json 中受保护路径的实际值。日志在仓库外时，补充 permissions.additionalDirectories；
   - 研究员需亲自执行的 OS 保护命令（只列出，不执行）；
   - 记忆提案：champion 初值、历史负结果，写成 research/memory/proposals/CR-R00-NN.md。
7. 向研究员展示：项目卡摘要、待定的章程项、保护命令、提案列表。研究员确认后，编辑 charter.md 和 settings.json（会触发确认），更新 STATUS.md（当前轮次：R00 完成；下一步：/ra-memory，然后 /ra-round R01）。
8. 把运行时版本写入 `research/rounds/R00/meta.yaml`（runtime、models 各角色实际 model ID、rubric_version、platform_changed；P1-2）。请研究员确认后提交：`git add -A research AGENTS.md CLAUDE.md .claude .agents .codex && git commit -m "R00 init"`。
~~~

`.agents/skills/ra-round/SKILL.md`

~~~markdown
---
name: ra-round
description: 执行一轮完整的训练评测迭代人机交互：对照预注册回收上一轮结果，多角色独立评审，剪枝与预注册，与研究员讨论并取得批准，最后锁定并交付启动脚本。仅在研究员显式调用时使用。
argument-hint: "[轮次号，如 R03；缺省为下一轮]"
disable-model-invocation: true
---
# /ra-round：一轮 = 一次人机交互

轮次号：$ARGUMENTS（Codex 中取研究员消息里的轮次号）。为空时，取 research/rounds/ 下最大的轮次号加 1，首轮是 R01。下文用 R 表示本轮，Rp 表示上一轮。
开始前完整阅读：research/PROTOCOL.md、charter.md、rubric.md、STATUS.md、project_card.md。

全程规则
- 每完成一个阶段，就更新 R/meta.yaml 的 last_phase 和 research/STATUS.md（阶段、下一步、等待谁）。
- 调用子代理时，prompt 只放三样东西：本阶段规定的输入指针、输出指令、角色任务的一句话。不放你自己的观点，也不放其他角色在本阶段的内容。
- 输出指令：子代理最终消息的第一行写 `<!-- ra:out R/<路径> -->`。在 Claude Code 下，hook 会自动把它原样落盘。返回后检查目标文件；文件不存在（hook 未生效，或用的是 Codex）时，由你把返回内容原样写入，并在文件头加 `written_by: lead`。不得改写、删减、合并。
- 不 resume 任何子代理。任何阶段失败或不完整，都停在该阶段，在 STATUS.md 写明原因，并询问研究员。

## 0 开轮与自检
1. 如果 R/decision.md 已存在，说明本轮已决策，只能继续未完成的 I/L/X。如果 R 目录存在但还没决策，读 meta.yaml，从 last_phase 的下一阶段继续，已完成的阶段不重做。
2. 自检，任一项失败就停止并报告：
   - `git status --porcelain -- AGENTS.md CLAUDE.md .claude .agents .codex research/PROTOCOL.md research/hooks research/charter.md research/rubric.md research/templates` 输出为空；
   - `printenv CUDA_VISIBLE_DEVICES` 退出码为 0，且输出为空；
   - 账本检查：自上一轮 lock commit 以来的 `research/ledger/human_inputs.jsonl` 中，批准语句（`批准…`/`批准(RL3)…`/`批准重跑…`/`批准 CR-…`）的 `permission_mode` 均非 `auto`——auto 会话的普通输入不拦，但**批准必须来自非 auto 权限**（发现 auto 批准则停止，请研究员在 default/plan 下重新输入）；
   - 记录 `claude --version` 或 `codex --version`。与 Rp/meta.yaml 不一致时，标 platform_changed: true，建议研究员先运行 `/ra-audit R canary`，并询问是否继续。
3. 建目录 R/{p1,p3,p4,p5,p6,p8,erc,exp,work/analyst,work/skeptic}。按 templates/meta.yaml 写 meta.yaml：charter_blob 用 `git hash-object research/charter.md`；parent_lock_commit 从 STATUS.md 取；**填写 runtime 与 models 中各角色实际使用的 model ID**（P1-2）。

## A 结果回收（存在 Rp 时）
1. 从 Rp/decision.md 取出已批准的 exp_id，查看 runs/<exp>/ 下的状态标记和 research/ledger/runs.jsonl。还在运行的列为"未完成"，不分析。全部未完成时，询问研究员：是先结束本次等待，还是只基于已有信息继续设计。
2. 调用 ra-analyst（阶段 A）。输入：Rp 的 erc/、decision.md、相关的 runs/<exp>/。输出：`<!-- ra:out R/A_results.md -->`。
3. 若 `git log <parent_lock_commit>..HEAD -- research/rounds/Rp/erc research/rounds/Rp/exp research/rounds/Rp/launch.sh` 非空，就在 A_results.md 顶部追加一行"⚠ 锁定后被修改"。这是唯一允许你追加的内容。
4. 把"CR 草稿"按 templates/cr.md 写成 research/memory/proposals/CR-R-NN.md。如果本轮要依据 dev 结果做选择，把 dev 查看计数加 1。
R01 没有 Rp：A_results.md 只写 project_card 中基线与历史结果的指针摘要。

## P1 独立评估（并行）
在同一条消息里并行调用 ra-analyst、ra-designer、ra-skeptic，阶段 P1。每个 prompt 包含：
- 可读：research/charter.md、research/project_card.md、research/memory/{knowledge,negative_results,hypotheses,playbook}.md、R/A_results.md、往轮 decision.md 的路径、代码与日志目录；
- 禁读：research/rounds/R/ 下除 A_results.md 以外的全部文件；
- 输出：`<!-- ra:out R/p1/<analyst|designer|skeptic>.md -->`，格式按 PROTOCOL §6.1。
全部返回后检查：3 份文件是否齐全；一句话结论是否符合 PROTOCOL §4 的正则。不合规的在 P2 标"不计入"。不合规达到 2 份及以上时，P1 判为不完整，重新调用这些角色，输出到 p1/<role>.r2.md。

## P2 广播（主会话）
进入前检查（P1-1 阶段门）：本轮 events.jsonl 无 `kind=compact` 事件、无 `source=compact` 的 session 记录；有则 P2 记 incomplete，停止并报告。
写 R/p2_broadcast.md：每个角色一节，逐字复制其一句话结论和证据列表，不改一个字，并标注合规或不计入。

## P3 交叉影响（并行；lite 模式下与 P4 合并为 p34/）
并行调用三个角色，阶段 P3。可读：p2_broadcast.md、本人的 p1 文件、背景资料。输出：`R/p3/<role>.md`（§6.2）。
检查：每人对另外两个角色各一条，共 6 条，no_impact 也必须写出。缺失时重调一次；仍缺就停下。

## P4 修改意见（并行）
并行调用三个角色，阶段 P4。可读：p2_broadcast.md、p3/*.md、背景资料。输出：`R/p4/<role>.md`（§6.3）。designer 负责收敛成 3–8 个具体候选。

## P5 评分
1. 合并 P4 提案：同一改动合并为一条，并列出被合并的提案号；编号 C1..Cm；去掉提出者信息；其余字段原文保留。
2. 章程预检：缺 charter_trace，或映射到 out_of_scope/forbidden 的候选，移入 R/p5/intercepted.md，不参与评分。
3. 写三个内容相同、顺序不同的文件：
   - p5/candidates-o1.md：C1→Cm；
   - p5/candidates-o2.md：Cm→C1；
   - p5/candidates-o3.md：奇数号在前，偶数号在后。
4. 并行调用 3 次 ra-judge，每次给一个文件，输出 `R/p5/judge-<k>.md`。lite 模式只用 o1 和 o2。
5. 评委全部返回后，再写 p5/mapping.md，记录 C 号与提案号的对应关系。
6. 汇总只能用代码：写 R/p5/tally.py，读取 judge-*.md 的分数表，按 rubric 计算每维中位数、total 和极差。运行 `python3 research/rounds/R/p5/tally.py > research/rounds/R/p5/tally.md`。不采信评委的任何倾向性文字。

## P6 汇总与核验
进入前检查（P1-1 阶段门）：同 P2 的 compact 检查；有则 P6 记 incomplete，停止并报告。
1. 起草 R/p6_synthesis.md，包含以下内容：
   a. 上一轮的确认性结论（引用 A_results）；
   b. 关键断言 K1..，每条带 ev；
   c. 剪枝记录：逐个候选写处置及理由、证据，处置包括 keep、prune:known_result、prune:theoretical_dominance、prune:debate_outcome、defer:over_budget、hold:needs_evidence。全部 keep 时必须写"零剪枝理由"；
   d. 建议计划：按 total 和 GPU·h 排序，在单轮预算与 8 卡约束内选取，写出卡分配与时间线；
   e. 按 templates/erc.yaml，为每个入选实验起草 R/erc/R-E<k>.yaml；
   f. 按 PROTOCOL §8 写 R/feasibility.md，附 nvidia-smi、df -h、吞吐依据、数据摘要等证据。
2. 调用 ra-verifier，核验 p6_synthesis.md、erc/*.yaml、feasibility.md，输出 `R/p6/verify.md`。
3. 按核验结果处理：stripped 的断言划掉，移入"剥离清单"；依赖这些断言的候选改为 hold:needs_evidence；intercepted 的移入章程拦截。同步更新 ERC 和计划。

## ⏸ 人机讨论门
1. 按 templates/brief.md 写 R/brief.md。
2. 在对话中展示 brief 的 §0、§1、§4、§8、§9，并给出文件路径。Claude Code 下可以用 AskUserQuestion 列出 §9 的选项，但点选不算批准。
3. 讨论过程中，按研究员的意见修改候选、ERC、种子、预算或卡分配。每次修改在 brief 的"讨论修订记录"中追加一行。修改引入了新断言的，只对这一部分重新调用 ra-verifier，输出 p6/verify-2.md 等。资源有变化的，重做 feasibility 中的相关项。
4. 只接受研究员亲自输入的决定，格式见 PROTOCOL §9。"好""可以""继续"或沉默都不算批准，要请研究员按格式重新输入。你不得替研究员写出或补全批准语句。
5. 以下任一情况属于 RL3：合计 GPU·h 超出单轮预算、包含 test 评测、触及评测代码、数据或章程。此时必须是 `批准(RL3)` 并附理由；章程指定了第二确认人的，第二确认人也须亲自输入。
6. 用 grep 在 research/ledger/human_inputs.jsonl 中找到批准原文，并核对该记录的 `payload.permission_mode` ≠ auto（auto 会话的输入不作批准凭据）。**找不到即终止本轮**（不得以"无 hook 记录"继续——fail-closed）：先修复 hook（对照 /ra-audit 的 K6），再从 ⏸ 继续。

## P7 决策
进入前检查（P1-1 阶段门）：同 P2 的 compact 检查；有则 P7 记 incomplete，停止并报告。
按模板写 R/decision.md（会触发写入确认）。如果研究员驳回，status 写 rejected，更新 STATUS.md，本轮结束。

## P8 决策影响（并行）
并行调用三个角色，阶段 P8。可读：R/decision.md 和本人的 p1 文件。输出：`R/p8/<role>.md`（§6.5）。其中的 CR 草稿写入 research/memory/proposals/。

## I 实现与脚本
1. 对于 code_change 类实验：做最小改动，用配置开关实现，默认值保持 parent 的行为；不碰评测代码和数据。在 CPU 上自检：`python3 -m py_compile <改动的文件>`、配置能否解析、已有的 CPU 单测。不得在 GPU 上试跑。
2. 写 R/exp/<exp_id>.yaml 与 <exp_id>.sh（按 templates/exp.sh）。按 templates/launch.sh 生成 R/launch.sh：替换 __ROUND__；实验清单与 decision.md 一致；路径写全。
3. 向研究员展示 `git diff --stat`、关键代码 diff，以及 launch.sh 的实验清单。

## L 预注册锁定
1. 执行 `git add -A research <改动的代码> runs/<Rp 的 exp>/`（.gitignore 已排除 checkpoint），再执行 `git commit -m "R lock: <exp_id 列表>"`。这一步会请研究员确认：代码与 ERC 即将冻结。
2. 把 `git rev-parse HEAD` 写入 STATUS.md 的 lock_commit。不要写进 R/ 目录：锁定后 R/ 里不能再有任何改动。
3. 锁定后，对 erc/、exp/、launch.sh 的任何修改都属于协议偏离，须新版本 ERC、重新批准、重新做锁定提交。

## X 交付启动
- 模式 A：告诉研究员在终端执行 `bash research/rounds/R/launch.sh`。脚本会自查锁定状态、代码是否干净、是否已启动过、GPU 是否被占用。
- 模式 B：提示研究员可以运行 `/ra-launch R`。
更新 STATUS.md：状态 awaiting_launch，列出实验及预计完成时间，下一步写"训练完成后运行 /ra-round"。本次交互到此结束。
~~~

`.agents/skills/ra-status/SKILL.md`

~~~markdown
---
name: ra-status
description: 只读查看本轮训练进度：日志、GPU、abort 条件、预计完成时间。研究员询问训练情况时使用。
argument-hint: "[轮次号]"
---
1. 确定轮次：取参数，没有参数就取 STATUS.md 中的当前轮次。读该轮 decision.md 中已批准的 exp_id，以及 erc/*.yaml。
2. 逐个 exp_id 查看：runs/<exp>/ 下的 STARTED/DONE/FAILED/ABORTED 标记；`tail -n 200 runs/<exp>/train.log` 中的步数/总步数、loss、吞吐；估算 ETA；research/ledger/runs.jsonl 中的事件。
3. 用 `nvidia-smi` 核对各卡占用是否与分配一致；用 `tmux ls` 查看会话。
4. 对照 ERC 的 abort_conditions 逐条判定：命中、未命中或无法判定，附 ev。interim_looks 只能用于 ERC 允许的用途。
5. 输出一张简表。命中 abort 条件时，给出证据，建议研究员执行 `tmux kill-session -t <exp>`，由研究员决定是否终止。终止后按 PROTOCOL §5.1 追加一条 ABORTED 记录。
6. 不要因为中期结果好或差（且 ERC 没有声明 futility 规则）而建议提前停。研究员坚持要停时，说明这属于 RL3 协议偏离，需要书面理由，结果将标为 deviated。
7. 全部完成后，提示研究员运行 /ra-round，并更新 STATUS.md 中的"运行中实验"。
~~~

`.agents/skills/ra-launch/SKILL.md`

~~~markdown
---
name: ra-launch
description: 模式 B。在研究员批准、预注册锁定之后，代为执行本轮 launch.sh。仅在研究员显式调用时使用；只适用于 Claude Code。
argument-hint: "<轮次号>"
disable-model-invocation: true
---
1. charter.md 中的 launch_mode 必须是 B。否则停止，请研究员在终端手动执行 `bash research/rounds/<R>/launch.sh`。
2. 核对以下各项，任一项不符就停止：
   - decision.md 的 status 为 approved；
   - 批准原文能在 research/ledger/human_inputs.jsonl 中逐字找到，且时间早于锁定提交；
   - launch.sh 中 start_exp 的实验集合 = 批准集合 = erc/ 中的文件集合；
   - `git status --porcelain -- research/rounds/<R>` 为空；
   - `git log -1 --format=%H -- research/rounds/<R>/launch.sh` 等于 STATUS.md 中的 lock_commit。
3. 用 `nvidia-smi` 确认分配到的 GPU 空闲。
4. 执行 `bash research/rounds/<R>/launch.sh`。这一步会弹出权限确认，也就是启动审批，请研究员核对命令后放行。不得用任何其他方式启动。
5. 更新 STATUS.md。
~~~

`.agents/skills/ra-memory/SKILL.md`

~~~markdown
---
name: ra-memory
description: 审阅并应用 research/memory/proposals/ 中的记忆、技能、规则变更提案，每条都须研究员逐条批准。仅在研究员显式调用时使用。
disable-model-invocation: true
---
1. 列出 proposals/ 中 status 为 pending 的 CR：编号、目标文件、类型、风险级、一句话内容、证据。
2. 逐条自检：
   - 证据能否解析（必要时调用 ra-verifier，输出 `<!-- ra:out <最近一轮>/p6/verify-memory.md -->`）；
   - 涉及负结果的 CR 只能新增，或追加条件说明，不得删除或替换已有的 NR；
   - 更新 champion 的 CR，必须引用 A_results 中判定为"达标"的确认性结论。
3. 请研究员逐条答复：`批准 CR-…`、`驳回 CR-…: 理由` 或 `修改 CR-…: …`。不得批量默认通过。RL3 类须附理由。
4. 对于批准的 CR：按"变更内容（逐字）"编辑目标文件（会触发确认）；在 CR 中写 status: applied、批准原文和时间；把 CR 移到 proposals/applied/。驳回的移到 proposals/rejected/，并写明理由。
5. 章程预授权范围内的变更可以直接应用，但要在下一轮 brief 中列出。
6. 涉及 .claude/agents、技能或 rubric 的变更，建议做一次回放对比：用旧版和新版分别对最近一轮的同一输入重跑相关阶段，把差异交给研究员看。
7. 请研究员确认后提交：`git commit -m "memory: <CR 列表>"`。
~~~

`.agents/skills/ra-audit/SKILL.md`

~~~markdown
---
name: ra-audit
description: 对某一轮做 RA2A-Lite 协议自检；加 canary 参数时同时做平台实测。只读，结果写入 research/audits/。
argument-hint: "[轮次号] [canary]"
---
每一项都给出 PASS / FAIL / N.A.，并附命令输出作为证据。结果写入 research/audits/<R>-<日期>.md，不写进轮次目录。
- C1 阶段完整、顺序正确：各阶段文件齐全；按 ledger/subagent_outputs.jsonl 的 ts（没有时用文件的 git 记录），满足 A < P1 < P2 < P3 < P4 < P5 < P6 < decision < P8 < lock；本轮时间窗内 events.jsonl 无 `kind=compact` 事件、无 `source=compact` 的 session 记录（有则该轮应已按协议记为 incomplete）。
- C2 P1 独立：
  - 每个 p1 文件的 sha256，等于 subagent_outputs.jsonl 中对应记录的 sha256；
  - 在这些记录的 payload.agent_transcript_path 对应的 transcript 中，grep 不到读取本轮 p1/ 下他人文件的记录。
  - C2b 每个 p1 文件对应记录的 `payload.agent_type` 必须非空、且等于文件名对应角色（analyst/designer/skeptic）；空串或不符 → FAIL（fail-closed）。
- C3 广播保真：p2 中每一句结论，都能在对应的 p1 文件中逐字找到。
- C4 影响矩阵完整：n(n−1) = 6 条。
- C5 评分来源：tally.md 由 tally.py 生成，输入是 judge-*.md 中的分数；brief 中的排序与 tally 一致。
- C6 证据：p6_synthesis.md 中标 ok 的断言抽查 10 条（不足 10 条就全查），均可解析；剥离清单已在 brief 和 decision 中公示。
- C7 章程：meta 中的 charter_blob 与本轮期间的章程一致，或者有修订记录；每个已批准实验的 charter_trace 都有效。
- C8 剪枝：每个未进入计划的候选都有处置记录；全部保留时写了零剪枝理由。
- C9 预注册顺序：
  - lock commit 的时间早于每个 runs/<exp>/STARTED；
  - `git log <lock>..HEAD -- <R>/erc <R>/exp <R>/launch.sh` 为空。
- C10 批准：
  - decision.md 中的批准原文能在 human_inputs.jsonl 中逐字找到，且早于 lock；
  - 批准集合 = erc 集合 = launch.sh 集合；
  - RL3 事项附了理由。
- C11 幂等：runs.jsonl 中每个 exp_id 至多有 1 条 STARTED。
- C15 启动配对：runs.jsonl 中每个 DONE/FAILED/ABORTED 之前必须有同 exp_id 的 STARTED；存在无 STARTED 的终态记录（`__run` 直调的特征）→ FAIL。
- C12 评测完整性：自上一轮以来，评测代码目录既没有提交也没有未提交的改动；`ls -ld` 显示仍为只读。
- C13 记忆：
  - 自上一轮以来，negative_results.md 的 `git diff --numstat` 删除行数为 0；
  - memory/*.md 的每次改动都能对应到一个 applied 的 CR。
- C14 平台：meta.yaml 记录了运行时版本与各角色 model（尚无轮次时判 N.A.）；批准语句记录的 `permission_mode` 均非 `auto`；控制文件与 HEAD 一致。

canary（参数中带 canary 时执行；每次升级 Claude Code 或 Codex 之后必须跑）：
- K1 `printenv CUDA_VISIBLE_DEVICES` 输出为空。
- K2 尝试执行 `torchrun --help`：应被拒绝，被拒即 PASS。不得换写法重试。
- K3 尝试用编辑工具在评测代码目录下新建 `.ra_canary`：应被拒绝。意外成功时判 FAIL，并请研究员删除该文件。
- K4 尝试读取 test 集中的任意一个文件：应被拒绝（前提是已配置）。
- K5 自动记忆已关闭：Claude 下，~/.claude/projects/ 中本项目没有 memory/ 目录，或其中没有新文件；Codex 下，配置中 memories 已关闭。
- K6 hooks 生效：研究员最近一次输入出现在 human_inputs.jsonl 中；最近一次子代理调用出现在 subagent_outputs.jsonl 中。
- K7 子代理配置：.claude/agents/*.md 的 tools 中没有 Agent，也没有 memory 字段。
- K9 子代理 agent_type：调用任一 ra-* 子代理，检查 subagent_outputs.jsonl 最新记录的 `payload.agent_type` 非空且等于角色名。**通过后研究员才可创建 `research/hooks/.whitelist_on` 激活 ra:out 白名单；不通过则不得激活**（fail-closed 白名单会拒绝一切角色输出）。
有 FAIL 时写进 STATUS.md，并建议研究员先修复，再开下一轮。
~~~

### 5.12 `.claude/settings.json`

> 路径占位符（`./eval/**`、`./data/**`、`./data/test/**`）须按 §9 替换。仓库外的路径用 `//绝对路径/**`：单斜杠开头的路径不是绝对路径。

~~~json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "env": {
    "CUDA_VISIBLE_DEVICES": "",
    "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
    "CLAUDE_CODE_FORK_SUBAGENT": "0",
    "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1"
  },
  "autoMemoryEnabled": false,
  "cleanupPeriodDays": 365,
  "permissions": {
    "defaultMode": "default",
    "disableBypassPermissionsMode": "disable",
    "disableAutoMode": "disable",
    "allow": [
      "Edit(./research/rounds/**)",
      "Edit(./research/STATUS.md)",
      "Edit(./research/project_card.md)",
      "Edit(./research/memory/proposals/**)",
      "Edit(./research/audits/**)",
      "Edit(./update/**)",
      "Edit(./research/runtime/checks/**)",
      "Bash(git status *)",
      "Bash(git log *)",
      "Bash(git diff *)",
      "Bash(git show *)",
      "Bash(git ls-files *)",
      "Bash(git rev-parse *)",
      "Bash(git hash-object *)",
      "Bash(git add *)",
      "Bash(git tag)",
      "Bash(git tag -l)",
      "Bash(git tag -l *)",
      "Bash(git tag --list)",
      "Bash(git tag --list *)",
      "Bash(git tag -n *)",
      "Bash(git branch --show-current)",
      "Bash(git stash list)",
      "Bash(git remote)",
      "Bash(git remote -v)",
      "Bash(git describe *)",
      "Bash(git rev-list *)",
      "Bash(git cat-file *)",
      "Bash(git blame *)",
      "Bash(nvidia-smi *)",
      "Bash(df *)",
      "Bash(du *)",
      "Bash(tail *)",
      "Bash(head *)",
      "Bash(wc *)",
      "Bash(sha256sum *)",
      "Bash(tmux ls *)",
      "Bash(printenv CUDA_VISIBLE_DEVICES)",
      "Bash(ls *)",
      "Bash(cat *)",
      "Bash(grep *)",
      "Bash(rg *)",
      "Bash(stat *)",
      "Bash(file *)",
      "Bash(diff *)",
      "Bash(jq *)",
      "Bash(which *)",
      "Bash(realpath *)",
      "Bash(readlink *)",
      "Bash(basename *)",
      "Bash(dirname *)",
      "Bash(uname *)",
      "Bash(nproc)",
      "Bash(python3 -m py_compile *)",
      "Bash(claude --version)",
      "Bash(codex --version)"
    ],
    "ask": [
      "Edit(./research/charter.md)",
      "Edit(./research/rubric.md)",
      "Edit(./research/PROTOCOL.md)",
      "Edit(./research/templates/**)",
      "Edit(./research/memory/*.md)",
      "Edit(./research/rounds/*/decision.md)",
      "Edit(./AGENTS.md)",
      "Edit(./CLAUDE.md)",
      "Edit(./.claude/**)",
      "Edit(./.agents/**)",
      "Edit(./.codex/**)",
      "Bash(git commit *)",
      "Bash(git tag -a *)",
      "Bash(git tag -s *)",
      "Bash(bash research/rounds/*)",
      "Bash(python3 research/rounds/*)",
      "Bash(tmux kill-session *)",
      "Bash(kill *)",
      "Bash(pkill *)",
      "Bash(rm *)"
    ],
    "deny": [
      "Edit(./research/ledger/**)",
      "Edit(./research/hooks/**)",
      "Edit(./runs/**)",
      "Read(./runs/**/.token)",
      "Edit(./eval/**)",
      "Edit(./data/**)",
      "Read(./data/test/**)",
      "Bash(torchrun *)",
      "Bash(accelerate launch *)",
      "Bash(deepspeed *)",
      "Bash(python -m torch.distributed.run *)",
      "Bash(python3 -m torch.distributed.run *)",
      "Bash(CUDA_VISIBLE_DEVICES=*)",
      "Bash(export CUDA_VISIBLE_DEVICES*)",
      "Bash(env CUDA_VISIBLE_DEVICES*)",
      "Bash(unset CUDA_VISIBLE_DEVICES*)",
      "Bash(git push *)",
      "Bash(git reset *)",
      "Bash(git rebase *)",
      "Bash(git commit --amend*)",
      "Bash(git clean *)",
      "Bash(git restore *)",
      "Bash(git checkout -- *)",
      "Bash(sudo *)",
      "Bash(chmod *)",
      "Bash(chown *)",
      "Bash(chattr *)",
      "Bash(rm -rf *)"
    ]
  },
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/research/hooks/ra_log.py\" session"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/research/hooks/ra_log.py\" human"
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/research/hooks/ra_log.py\" subagent"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/research/hooks/ra_log.py\" compact"
          }
        ]
      }
    ],
    "PermissionRequest": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/research/hooks/ra_log.py\" perm_request"
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/research/hooks/ra_log.py\" notify"
          }
        ]
      }
    ]
  }
}
~~~

### 5.13 `research/hooks/ra_log.py`（唯一的脚本，Claude Code 与 Codex 共用；不装也能用）

~~~python
#!/usr/bin/env python3
"""RA2A-Lite 记账 hook（Claude Code 与 Codex 共用）。只记账，不判断是否放行，任何情况下都 exit 0。
用法：ra_log.py <kind>，hook 事件的 JSON 从 stdin 读入。
  human    UserPromptSubmit：把研究员的每条输入写入 research/ledger/human_inputs.jsonl，作为批准语句的凭据
  subagent SubagentStop：把子代理的最终消息写入 research/ledger/subagent_outputs.jsonl；
           如果消息第一行是 <!-- ra:out Rnn/<路径>.md -->，就把消息原样存到 research/rounds/Rnn/<路径>.md
           （目标文件已存在时不覆盖，改存为 <名>.dup-<时间>.md，并在账本中注明）
  session  SessionStart：把 research/STATUS.md 打印到 stdout，两种运行时都会把它注入上下文
  其他     写入 research/ledger/events.jsonl
"""
import fcntl, hashlib, json, os, pathlib, re, subprocess, sys, time

OUT_RE = re.compile(r"\A\s*<!--\s*ra:out\s+(R\d{2,}/[A-Za-z0-9_./-]+\.md)\s*-->")

# v2.3 P0-1b：ra:out 目标路径白名单（fail-closed）。依据：check/demo-conformance-final-verdict.md §3 P0-1b。
# 激活前置（K9）：真实 ra-* 子代理的 SubagentStop 输入 agent_type 非空且等于角色名——实测通过后，
# 由研究员创建 research/hooks/.whitelist_on（空文件）方才生效；标记不存在时维持旧行为（仅记账，不拦截）。
# ⚠️ 平台若不填 agent_type（账本实测出现过空串），激活白名单会拒绝一切角色输出、流程不可用——此时不得激活。
# 主会话文件（decision.md、brief.md、p2_broadcast.md、p5/candidates-*、p6_synthesis 等）不在任何角色的白名单内。
WHITELIST = {                                   # 角色 → (精确后缀集合, 前缀集合)；后缀指 Rnn/ 之后的部分
    "ra-analyst":  (("A_results.md", "baseline_analysis.md"), ()),
    "ra-skeptic":  (("integrity.md",), ()),
    "ra-designer": ((), ()),
    "ra-judge":    ((), ("p5/judge-",)),
    "ra-verifier": ((), ("p6/verify",)),
}
for _role in ("ra-analyst", "ra-skeptic", "ra-designer"):
    _name = _role.split("-", 1)[1]
    _exacts, _prefixes = WHITELIST[_role]
    WHITELIST[_role] = (_exacts + tuple(f"{_ph}/{_name}.md" for _ph in ("p1", "p3", "p34", "p4", "p8")), _prefixes)


def find_root(p):
    base = os.environ.get("CLAUDE_PROJECT_DIR") or p.get("cwd") or os.getcwd()
    try:
        top = subprocess.run(["git", "-C", base, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        return pathlib.Path(top or base).resolve()
    except Exception:
        return pathlib.Path(base).resolve()


def append(path, rec):
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:      # 三个子代理可能同时结束，所以加锁
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(line)
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)


def save_out(root, msg, agent_type="", enforce=False):
    m = OUT_RE.match(msg)
    if not m:
        return None
    rel = m.group(1)
    if ".." in pathlib.PurePosixPath(rel).parts:
        return "rejected:path"
    rounds = (root / "research" / "rounds").resolve()
    target = (rounds / rel).resolve()
    if rounds not in target.parents:
        return "rejected:path"
    if enforce:                                  # v2.3 P0-1b：白名单判定（fail-closed）
        at = (agent_type or "").strip()
        parts = rel.split("/", 1)
        suffix = parts[1] if len(parts) == 2 else ""
        if not at:
            return "rejected:agent_type_missing"  # 账本实测 agent_type 可能为空串：一律拒绝
        exacts, prefixes = WHITELIST.get(at, ((), ()))
        if suffix not in exacts and not (prefixes and suffix.startswith(tuple(prefixes))):
            return f"rejected:whitelist({at})"
    if target.exists():
        target = target.with_name(f"{target.stem}.dup-{time.strftime('%Y%m%dT%H%M%S')}.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="") as f:   # 原样写入，sha256 与账本一致
        f.write(msg)
    return str(target.relative_to(root))


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else "event"
    raw = sys.stdin.read()
    try:
        p = json.loads(raw) if raw.strip() else {}
    except Exception:
        p = {"raw": raw[:20000]}
    root = find_root(p)
    led = root / "research" / "ledger"
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    if kind == "session":
        st = root / "research" / "STATUS.md"
        if st.exists():
            print("【RA2A-Lite 当前状态：先读，再行动】\n" + st.read_text(encoding="utf-8")[:6000])
        append(led / "events.jsonl", {"ts": now, "kind": "session", "source": p.get("source"),
                                       "session_id": p.get("session_id"), "model": p.get("model")})
        return

    msg = p.get("last_assistant_message") or p.get("prompt") or ""
    rec = {"ts": now, "kind": kind, "session_id": p.get("session_id"),
           "agent_id": p.get("agent_id"), "agent_type": p.get("agent_type"),
           "model": p.get("model"),                       # Codex 每个事件都带 model；Claude 可能为空
           "sha256": hashlib.sha256(msg.encode("utf-8")).hexdigest() if msg else None,
           "payload": p}
    if kind == "human":
        append(led / "human_inputs.jsonl", rec)
    elif kind == "subagent":
        enforce = (root / "research" / "hooks" / ".whitelist_on").exists()   # K9 通过后由研究员创建
        rec["whitelist_enforced"] = enforce
        rec["written_to"] = save_out(root, msg, p.get("agent_type"), enforce) if msg else None
        append(led / "subagent_outputs.jsonl", rec)
    else:
        append(led / "events.jsonl", rec)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:      # 记账失败也不能阻断会话
        try:
            sys.stderr.write(f"ra_log: {e}\n")
        except Exception:
            pass
    sys.exit(0)
~~~

### 5.14 `.codex/config.toml`

> 项目层配置只有在信任本项目之后才会加载。用 `/status` 确认 sandbox、approval 和模型的实际生效值。模型 ID 要换成 `/model` 里列出的、当前可用的完整 ID。

~~~toml
# RA2A-Lite：Codex 项目层配置。修改属于控制文件变更，须研究员批准（AGENTS.md 规则 3）。

model = "gpt-5.6"                    # 主会话（Lead）；换成你可用的完整 ID
model_reasoning_effort = "high"
approval_policy = "on-request"       # 写 .git、联网、写仓库外时请求批准
sandbox_mode = "workspace-write"     # 仓库可写；.git 与 .codex 受沙箱保护
web_search = "cached"

[sandbox_workspace_write]
network_access = false

[shell_environment_policy]
set = { CUDA_VISIBLE_DEVICES = "" }  # 智能体执行的所有命令都看不到 GPU

[features]
memories = false                     # 关闭跨会话记忆（键名以所用版本为准，由 canary K5 核验）
hooks = true                         # hooks 已经稳定的版本可以删掉这一行

[agents]
max_threads = 4                      # P1/P3/P4/P8 三路并行，P5 三名评委
max_depth = 1                        # 子代理不能再派生
~~~

### 5.15 `.codex/hooks.json`

> 这里只有 3 个 hook。首次启动后执行 `/hooks`，逐个审阅并信任。以后 hook 定义一有改动，就要重新信任，否则会被跳过。

~~~json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "timeout": 30,
        "command": "python3 \"$(git rev-parse --show-toplevel)/research/hooks/ra_log.py\" session" } ] }
    ],
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command", "timeout": 30,
        "command": "python3 \"$(git rev-parse --show-toplevel)/research/hooks/ra_log.py\" human" } ] }
    ],
    "SubagentStop": [
      { "hooks": [ { "type": "command", "timeout": 30,
        "command": "python3 \"$(git rev-parse --show-toplevel)/research/hooks/ra_log.py\" subagent" } ] }
    ]
  }
}
~~~

### 5.16 `.codex/rules/ra.rules`

> 规则只匹配 Codex **直接执行**的命令前缀，管不到脚本内部启动的子进程（见 §7.2）。文件里没有写 `match`/`not_match` 内联用例：内联用例写错会导致整个规则文件加载失败。

~~~python
# RA2A-Lite：Codex 命令规则（Starlark）。只在信任本项目后加载。修改须研究员批准。
# 有多条规则同时匹配时，取最严格的决定：forbidden > prompt > allow。

# 训练与 GPU 作业只能由研究员经 launch.sh 启动（AGENTS.md 规则 1）
prefix_rule(pattern = ["torchrun"], decision = "forbidden",
            justification = "训练只能由研究员在终端运行 launch.sh 启动")
prefix_rule(pattern = ["accelerate", "launch"], decision = "forbidden",
            justification = "训练只能由研究员启动")
prefix_rule(pattern = ["deepspeed"], decision = "forbidden",
            justification = "训练只能由研究员启动")
prefix_rule(pattern = [["python", "python3"], "-m", ["torch.distributed.run", "torch.distributed.launch"]],
            decision = "forbidden", justification = "训练只能由研究员启动")
prefix_rule(pattern = ["nohup"], decision = "forbidden",
            justification = "智能体不得启动常驻进程")
prefix_rule(pattern = ["tmux", ["new-session", "new"]], decision = "forbidden",
            justification = "智能体不得启动常驻会话；训练由研究员运行 launch.sh")
prefix_rule(pattern = ["env"], decision = "prompt",
            justification = "env 可能被用来改写 CUDA_VISIBLE_DEVICES，需研究员确认")

# 终止进程：由研究员确认
prefix_rule(pattern = ["tmux", "kill-session"], decision = "prompt",
            justification = "终止训练须有 abort 证据或研究员决定")
prefix_rule(pattern = [["kill", "pkill"]], decision = "prompt",
            justification = "终止进程须研究员确认")

# git：禁止改写历史；提交须确认
prefix_rule(pattern = ["git", ["push", "reset", "rebase", "clean", "restore"]], decision = "forbidden",
            justification = "历史与远端由研究员管理（AGENTS.md 规则 7）")
prefix_rule(pattern = ["git", "commit", "--amend"], decision = "forbidden",
            justification = "锁定提交不得改写")
prefix_rule(pattern = ["git", "checkout", "--"], decision = "forbidden",
            justification = "不得丢弃改动")
prefix_rule(pattern = ["git", "commit"], decision = "prompt",
            justification = "锁定与记忆提交须研究员确认")

# 权限与删除
prefix_rule(pattern = [["sudo", "chmod", "chown", "chattr"]], decision = "forbidden",
            justification = "OS 权限由研究员管理")
prefix_rule(pattern = ["rm", ["-rf", "-fr", "-r"]], decision = "forbidden",
            justification = "删除由研究员执行")
~~~

### 5.17 `.codex/agents/*.toml`（共 5 个）

> 角色说明只维护一份：Codex 子代理先读 `.claude/agents/<角色>.md` 的正文再工作。改了这份正文，两边同时生效，变更走 `/ra-memory` 的 `agent_prompt` 类 CR。
> `model`、`model_reasoning_effort`、`sandbox_mode` 三项必须写死，不能依赖从父会话继承。

`.codex/agents/ra-analyst.toml`

~~~toml
name = "ra-analyst"
description = "RA2A-Lite 结果与日志分析员：阶段 A 对照锁定的 ERC 做确认性分析；P1/P3/P4/P8 提供数据诊断视角。只在 ra-round / ra-init 流程中由主会话调用。"
model = "gpt-5.6"
model_reasoning_effort = "high"
sandbox_mode = "workspace-write"
developer_instructions = """
你是 ra-analyst。
一、完整的角色说明在 .claude/agents/ra-analyst.md 里，从第二个 --- 之后开始是正文。动手之前先完整读一遍，并严格遵守；这份说明与 Claude Code 版共用。读不到这个文件就立即停止，最终消息只写"角色文件缺失"。
二、以下硬性边界无论如何都适用：
- 只能写 research/rounds/<R>/work/analyst/，其他文件一律不改。
- 不启动训练、评测或任何 GPU 作业，不修改 CUDA_VISIBLE_DEVICES。
- 不读 test 集；任务没有给出的本轮其他角色文件，一律不读。
- 不再派生子代理。
- 最终消息的第一行，原样写任务给出的 <!-- ra:out … --> 标记。最终消息就是正式存档，必须完整自洽。
"""
~~~

`.codex/agents/ra-designer.toml`

~~~toml
name = "ra-designer"
description = "RA2A-Lite 试验设计者：提出每 GPU·h 信息增益最高、最能逼近里程碑的下一批实验。只在 ra-round 流程中由主会话调用。"
model = "gpt-5.6"
model_reasoning_effort = "high"
sandbox_mode = "read-only"
developer_instructions = """
你是 ra-designer。
一、完整的角色说明在 .claude/agents/ra-designer.md 里，从第二个 --- 之后开始是正文。动手之前先完整读一遍，并严格遵守。读不到这个文件就立即停止，最终消息只写"角色文件缺失"。
二、硬性边界：只读，不写任何文件；不启动任何作业；不读 test 集，也不读任务没有给出的本轮其他角色文件；不再派生子代理。外部资料写成 ev:web:<URL>#"<原文片段>"，并标注[外部]。
三、最终消息的第一行，原样写任务给出的 <!-- ra:out … --> 标记。最终消息必须完整自洽。
"""
~~~

`.codex/agents/ra-skeptic.toml`

~~~toml
name = "ra-skeptic"
description = "RA2A-Lite 红队审稿人：在消耗 GPU 之前，找出会让结论不可信或浪费资源的问题。只在 ra-round / ra-init 流程中由主会话调用。"
model = "gpt-5.6"
model_reasoning_effort = "high"
sandbox_mode = "workspace-write"
developer_instructions = """
你是 ra-skeptic。
一、完整的角色说明在 .claude/agents/ra-skeptic.md 里，从第二个 --- 之后开始是正文。动手之前先完整读一遍，并严格遵守。读不到这个文件就立即停止，最终消息只写"角色文件缺失"。
二、硬性边界：只能写 research/rounds/<R>/work/skeptic/；只在 CPU 上运行检查脚本；不读 test 集，需要做 test 重叠检查时，只给出命令交研究员执行；任务没有给出的本轮其他角色文件，一律不读；不再派生子代理。
三、最终消息的第一行，原样写任务给出的 <!-- ra:out … --> 标记。最终消息必须完整自洽。
"""
~~~

`.codex/agents/ra-judge.toml`

~~~toml
name = "ra-judge"
description = "RA2A-Lite P5 评委：按 research/rubric.md 对匿名候选实验逐维打分，不排名。只在 ra-round 的 P5 中由主会话调用。"
model = "gpt-5.6"
model_reasoning_effort = "medium"
sandbox_mode = "read-only"
developer_instructions = """
你是 ra-judge。
一、完整的角色说明在 .claude/agents/ra-judge.md 里，从第二个 --- 之后开始是正文。动手之前先完整读一遍，并严格遵守。读不到这个文件就立即停止，最终消息只写"角色文件缺失"。
二、硬性边界：只读；只评任务指定的那一个候选文件；不计算总分，不排名，不推荐；不猜提出者是谁；不再派生子代理。
三、最终消息的第一行，原样写任务给出的 <!-- ra:out … --> 标记，之后只给分数表。
"""
~~~

`.codex/agents/ra-verifier.toml`

~~~toml
name = "ra-verifier"
description = "RA2A-Lite P6 核验员：逐条核验断言的证据指针与章程映射，输出保留/剥离清单。只在 ra-round / ra-memory 流程中由主会话调用。"
model = "gpt-5.6"
model_reasoning_effort = "high"
sandbox_mode = "read-only"
developer_instructions = """
你是 ra-verifier。
一、完整的角色说明在 .claude/agents/ra-verifier.md 里，从第二个 --- 之后开始是正文。动手之前先完整读一遍，并严格遵守。读不到这个文件就立即停止，最终消息只写"角色文件缺失"。
二、硬性边界：只读；需要复算时，python3 只输出到 stdout；不提出实验；不再派生子代理。ev:web 指针用网页搜索核对；核对不到，判 stripped(unresolvable)。
三、最终消息的第一行，原样写任务给出的 <!-- ra:out … --> 标记。最终消息必须完整自洽。
"""
~~~

### 5.18 对 §5.9 `launch.sh` 模板的补丁（创建文件时必须一起应用；本包 §5.9 的 launch.sh 代码块已是补丁后全文，此节保留作历史依据）

用途：智能体会话里一旦执行 `launch.sh` 就直接拒绝，只有 `launch_mode: B` 且运行时是 Claude Code 时例外。判定依据是一个**我们自己设置的信号**：智能体环境里 `CUDA_VISIBLE_DEVICES` 已设置、但值为空（Claude 由 settings 的 env 设置，Codex 由 shell_environment_policy 设置）。研究员自己的终端通常不会这样设置。

**插入位置**：在 `research/templates/launch.sh` 中，`# ---- 预注册与代码检查 ----` 这一行**之前**。这个位置在 `__run` 分支之后，所以 tmux 内部的实际运行不受影响。插入内容：

~~~bash
# ---- 启动者检查：智能体会话只有在 launch_mode=B 且运行时为 Claude Code 时才能启动 ----
AGENT=0
if [ -n "${CLAUDECODE:-}" ] || [ -n "${CODEX_SANDBOX:-}" ] || [ -n "${CODEX_SANDBOX_NETWORK_DISABLED:-}" ]; then AGENT=1; fi
if [ "${CUDA_VISIBLE_DEVICES+set}" = set ] && [ -z "${CUDA_VISIBLE_DEVICES}" ]; then AGENT=1; fi
MODE=$(grep -E '^- launch_mode:' research/charter.md | awk '{print $3}')
if [ "$AGENT" = 1 ] && { [ "$MODE" != B ] || [ -z "${CLAUDECODE:-}" ]; }; then
  echo "✗ 检测到智能体会话环境（launch_mode=${MODE:-?}）。请研究员在自己的终端运行本脚本。"; exit 1
fi
~~~

如果所用的 Claude Code 版本不设置 `CLAUDECODE`，模式 B 会被拒绝，此时改用模式 A。这是 fail-closed，属于预期行为。

---

## 6 日常使用

### 6.1 首次接入（R00）与首轮建议

| 步骤 | 你做什么 | 智能体做什么 | 产出 |
|---|---|---|---|
| 1 | `/ra-init`（Codex：`$ra-init`） | 只读盘点代码、数据、评测和日志；analyst 估算 σ 与吞吐；skeptic 抽检训练集与 dev 的重叠、评测代码的完整性 | `project_card.md`、`rounds/R00/*` |
| 2 | 逐项回答章程中的【待定】：目标值、单轮/单实验/总预算、里程碑、in/out_of_scope、launch_mode、dev_look_threshold、第二确认人 | 编辑 charter.md，会弹窗请你确认 | 章程 v1 |
| 3 | 在终端执行它列出的 OS 保护命令；如果 test 重叠检查需要读 test，也由你执行 | — | — |
| 4 | `/ra-memory`，逐条批准 champion 初值和历史负结果 | 应用 CR | `knowledge.md`、`negative_results.md` |
| 5 | `/ra-audit R00 canary` | 跑 K1–K7 | `audits/R00-*.md` |
| 6 | 确认提交 | `git commit -m "R00 init"` | — |

**R01 的内容取决于噪声 σ 是否已知**：
- **σ 未知**（同配置的历史种子少于 2 个）：R01 用一组 4 卡做基线复现，3 个种子，对应里程碑 M1。另一组 4 卡跑 1–2 个成本最低的探针实验，结论一律标 exploratory。σ 没有估出来之前，任何"Δ 是否显著"的判断都站不住，skeptic 会在 P1 指出这一点。
- **σ 已知**：R01 直接进入设计。parent 一般是历史最佳的已确认配置。

### 6.2 一轮的实际过程（示例：R03）

```
你：    /ra-round R03
智能体：[0] 自检通过：控制文件未改动，GPU 不可见，claude 2.1.3xx 与 R02 一致
        [A] R02-E1 达标：Δ=+0.62pp，holm 校正后 95% CI [+0.21, +1.03]，3/3 个种子完整
            R02-E2 未达标：Δ=+0.08pp [−0.30, +0.46]，可排除 >0.46pp 的效应
            已起草 CR-R03-01（NR：R02-E2 的改动在当前步数下无效）、CR-R03-02（champion → R02-E1）
        [P1–P6] 3 个角色独立评估 → 6 条影响记录 → 7 个候选 → 3 名评委打分 → 剪枝 4 个
                → 核验剥离 2 条断言 → 起草 3 份 ERC → 可行性 L0–L3 通过
        ⏸ 简报：research/rounds/R03/brief.md
        §0 R02 说明 X 有效、Y 无效；本轮建议 E1/E2/E3，共 168 GPU·h，占预算 88%
        §9 需要你决定：① E3 的种子用 3 还是 5（σ=0.21，预期 Δ=0.3）② C5 有分歧（impact 极差 2），保留还是剪掉
你：    E3 用 5 个种子；C5 剪掉；E2 先不做
智能体：已修订（brief 修订记录 #1）：E3 的 ERC 更新为 v1（尚未锁定，不算偏离），只对改动部分重新核验，
        结果在 p6/verify-2.md。合计 130 GPU·h，GPU 分配：E1→0-3，E3→4-7。
        请按格式回复，例如：批准 R03: R03-E1, R03-E3
你：    批准 R03: R03-E1, R03-E3
智能体：[P7] 写入 decision.md（弹窗，请确认）→ [P8] → [I] 代码 diff 加 CPU 自检 → [L] 锁定提交（弹窗，请确认）
        请在你的终端运行：bash research/rounds/R03/launch.sh
你（终端）：bash research/rounds/R03/launch.sh
        ✓ 已启动 R03-E1（GPU 0,1,2,3）…  ✓ 已启动 R03-E3（GPU 4,5,6,7）…
```

**这些话不算批准**：`好`、`可以`、`就这样`、`继续`、选项点选、沉默。遇到这些，智能体会请你按 PROTOCOL §9 的格式重新输入。

### 6.3 训练期间

| 场景 | 操作 |
|---|---|
| 看进度 | `/ra-status`，只读：步数、ETA、loss、各卡占用、逐条 abort 判定 |
| 命中 abort 条件（有证据） | 你执行 `tmux kill-session -t R03-E1`，然后记账：<br>`date -Is > runs/R03-E1/ABORTED`<br>`printf '{"ts":"%s","exp_id":"%s","event":"ABORTED","abort_id":"%s","by":"researcher"}\n' "$(date -Is)" R03-E1 A1 >> research/ledger/runs.jsonl` |
| 没命中 abort，但你想停 | 属于 RL3 协议偏离：输入 `批准(RL3) R03: 终止 R03-E1: 理由`，再按上一行操作。该实验结果标为 deviated |
| 中期结果很好，想提前结束 | 不允许，除非 ERC 预先声明了中期规则。这正是预注册要防的情况 |
| 服务器重启或进程丢失 | `runs/<exp>/` 只有 STARTED，没有终态标记。你记一笔：`date -Is > runs/<exp>/FAILED` 并追加一条 FAILED 事件（同上的 printf，event 改为 FAILED，加 `"reason":"reboot"`），然后按 §6.5 重跑 |
| 全部结束 | `/ra-round`（下一轮），从阶段 A 开始 |

### 6.4 中断与恢复

| 中断发生在 | 现象 | 恢复方法 |
|---|---|---|
| P1–P6 中途（会话崩溃、关窗口） | 新会话启动时，SessionStart hook 会注入 STATUS.md | 再次执行 `/ra-round R03`，从 `meta.yaml` 的 last_phase 的下一阶段接着做，已落盘的阶段不重做 |
| 上下文被压缩 | 同上 | CLAUDE.md 要求压缩后重读 STATUS.md 和本轮目录；如果某阶段产出不完整，就重做该阶段 |
| ⏸ 讨论门 | brief.md 和修订记录都在 | 新会话中让智能体"读 R03/brief.md 继续讨论"，或直接输入批准语句后执行 `/ra-round R03` |
| 已批准、未锁定 | decision.md 存在 | `/ra-round R03`，只继续 I/L/X |
| 已锁定、未启动 | STATUS 显示 awaiting_launch | 直接运行 launch.sh |
| launch.sh 只启动了一部分（某组卡被占） | 已启动的那部分会被记为 STARTED | 卡空出来后再运行一次，已启动的会自动跳过 |

### 6.5 技术故障重跑

1. 先确认属于技术故障：NaN、OOM、节点重启、数据读取错误。如果修复要改变实验的科学内容，比如改学习率，那就是新实验，放到下一轮。
2. 输入：`批准重跑 R03-E1: 第 2 个种子运行中服务器重启`
3. 让智能体在 `rounds/R03/retries.md` 中登记 `| R03-E1.r2 | R03-E1 | 原因 | 批准原文 | 时间 |`。如果修复涉及代码，按"code_change"做最小修复和 CPU 自检，然后提交（弹窗确认）。
4. 在终端运行：`bash research/rounds/R03/launch.sh retry R03-E1.r2 R03-E1`
5. 阶段 A 中，analyst 用重跑结果替换原实验，并在"偏离"列注明。

### 6.6 修改章程、规则、代理和技能

| 要改什么 | 风险级 | 怎么改 |
|---|---|---|
| 章程（目标、范围、预算、里程碑） | RL3 | 你在编辑器里直接改，在"修订记录"里加一行，再提交。也可以让智能体改（会弹窗）。下一轮 `meta.yaml` 中的 charter_blob 会变，审计项 C7 会核对修订记录 |
| rubric / PROTOCOL / 变更条件 | RL3 | 同上；rubric_version 或 protocol_version 要加一 |
| 子代理提示词、技能 | RL2 | 让智能体写 `agent_prompt` / `skill` 类 CR，再用 `/ra-memory` 批准。批准前建议做一次回放对比（ra-memory 第 6 步） |
| champion、知识、负结果、假设 | RL2 | 只能经 CR 加 `/ra-memory`。负结果只增不删 |
| playbook 格式整理 | 预授权 | 智能体可以直接改，在下一轮 brief 中报告 |
| `.claude/settings.json`、`.codex/*` | RL3 | 改完重启会话，并跑 `/ra-audit Rnn canary` |

### 6.7 Claude Code 与 Codex 对照

| 事项 | Claude Code | Codex |
|---|---|---|
| 调用技能 | `/ra-round R03` | `$ra-round R03`，或用 `/skills` 选择 |
| 子代理定义 | `.claude/agents/*.md` | `.codex/agents/*.toml`（正文共用 `.claude/agents`） |
| 并行发起 | 同一条消息里发出多个子代理调用 | 主会话请求并行 spawn（max_threads=4） |
| 记账 hook | settings.json 中 6 个（v2.4 增加PermissionRequest/Notification 只记账 hook） | hooks.json 中 3 个，需要在 `/hooks` 中信任 |
| 受保护路径 | deny/ask 规则 + OS 权限 | 只有 OS 权限 + git 审计；`.git`、`.codex` 由沙箱保护 |
| 改受保护文件 | 弹窗确认 | **不弹窗**（在工作区内可写），靠开轮自检和 `/ra-audit` 事后发现 |
| GPU 隔离 | settings env + deny 规则 | shell_environment_policy + rules forbidden |
| git commit | ask 弹窗 | `.git` 受沙箱保护，需要提权批准；rules 里也设了 prompt |
| 启动模式 | A 或 B | 只能 A（launch.sh 补丁强制） |
| 自动记忆 | autoMemoryEnabled=false + 环境变量 | features.memories=false |
| 讨论门的选项 | AskUserQuestion（点选不算批准） | 普通对话 |

同一个项目可以交替使用两种运行时，但**不要在一轮中途切换**。切换运行时就等于平台变化，`meta.yaml` 里会是 `platform_changed: true`，要先跑 canary。

### 6.8 8 卡分配建议

- **默认**：两组 4 卡并行（`0,1,2,3` 和 `4,5,6,7`），各跑一个实验，实验内的种子串行跑。这是 exp.sh 模板的写法。
- **卡数与基线不同时**：要用梯度累积保持全局 batch 不变，否则"卡数不同"本身就是混杂因素。skeptic 会检查这一点，ERC 的 `change` 字段也必须说明。
- **GPU·h 怎么算**：卡数 × 墙钟小时。吞吐取自同卡数的历史日志。没有同卡数的日志时，按线性缩放估算，并在 `basis` 中注明是估算。
- **共享服务器**：章程里写明保留卡；feasibility 的 L0 会附 `nvidia-smi` 输出；launch.sh 启动前会再查一次占用。

---

## 7 平台实测与边界

### 7.1 canary 的期望与 FAIL 处理

每次安装或升级 Claude Code / Codex 之后，都要运行 `/ra-audit Rnn canary`。

| 项 | Claude Code 期望 | Codex 期望 | FAIL 时 |
|---|---|---|---|
| K1 GPU 不可见 | 输出为空 | 输出为空 | Claude：检查 settings.json 是否加载（重启会话）。Codex：检查项目是否已信任，用 `/status` 看配置 |
| K2 torchrun 被拒 | deny 拒绝 | rules forbidden 拒绝 | Codex：确认 `.codex/rules/` 已加载（需要信任）；`codex execpolicy check --rules .codex/rules/ra.rules -- torchrun --help` 可以离线检查 |
| K3 评测目录不可写 | deny 规则 + OS 只读 | **只靠 OS 只读** | 执行安装第 5 步 |
| K4 test 不可读 | Read deny | **只靠 test 不在可读位置** | 把 test 移走或改权限 |
| K5 自动记忆关闭 | 本项目没有新的 memory 文件 | memories 已关闭 | 检查 env、设置键名 |
| K6 hooks 生效 | ledger 中有记录 | 需要先在 `/hooks` 中信任 | hook 失效时，主会话会兜底落盘（文件头带 `written_by: lead`），但批准语句就没有记录了。必须修好再开轮 |
| K7 子代理配置 | 没有 Agent 工具，没有 memory 字段 | TOML 中写死了 model、effort、sandbox_mode | 修复配置 |
| K8（手动补充）启动守卫 | 在智能体会话中执行 `bash research/templates/launch.sh`，应当输出"检测到智能体会话环境" | 同左 | 检查 §5.18 补丁是否已应用 |

K8 不在 ra-audit 技能里，需要在对话中让智能体执行一次。即使守卫没有生效，模板也会因为"launch.sh 未提交"而退出，不会启动任何东西。

**检查子代理实际用的模型**（对应 C-PIN，可选）：
```bash
# Claude：子代理 transcript 中 assistant 消息带有 model 字段
python3 -c "import json;[print(json.loads(l).get('agent_type'), json.loads(l)['payload'].get('agent_transcript_path')) for l in open('research/ledger/subagent_outputs.jsonl')]" | tail -5
grep -o '"model":"[^"]*"' <上面列出的 transcript 路径> | sort | uniq -c
# Codex：hook 记录里直接带 model
grep -o '"model": "[^"]*"' research/ledger/subagent_outputs.jsonl | sort | uniq -c
```

### 7.2 剩余风险（诚实清单）

| # | 风险 | 为什么挡不死 | 现有缓解 | 剩余程度 |
|---|---|---|---|---|
| 1 | 智能体绕过 GPU 隔离，比如在 Python 里改写 `os.environ` | `CUDA_VISIBLE_DEVICES` 只是环境变量；权限规则只看命令字符串 | AGENTS.md 规则 1；`/ra-status` 核对是否有未登记的 GPU 进程；§7.3 容器方案 | 防得住误操作，防不住有意规避 |
| 2 | 经 Bash 写受保护文件，比如 `python -c` | Claude 的 Edit deny 只管内置文件工具 | OS 只读（评测、dev）；开轮自检会查控制文件；C12/C13/C14 | 写记忆、写章程只能在事后由 git 审计发现 |
| 3 | Codex 下账本可写，批准语句有被伪造的可能 | workspace-write 对仓库内文件不分路径 | §7.4 用 transcript 交叉核对（transcript 在仓库外，沙箱不允许写） | 能在事后发现 |
| 4 | P1 不够独立，比如先结束的角色产出被后结束的角色读到 | 子代理有读工具 | 并行发起；prompt 写明禁读；C2 用 transcript 审计 | 能在事后发现 |
| 5 | 模型别名漂移 | Claude frontmatter 默认用别名 | 建议换成完整 ID；`meta.yaml` 中记录；§7.1 的 transcript 核对 | 低 |
| 6 | 锁定之后又改了 ERC 或脚本 | 文件本身可写 | launch.sh 检查 git 状态；C9 | 启动前就会被挡住 |
| 7 | dev 过拟合 | 多轮都依据 dev 做选择 | dev 查看计数；到阈值时提示做 test 确认（§8.3） | 由研究员决策 |
| 8 | 升级后 hook 或字段静默失效 | 平台行为会变 | K6 canary；主会话兜底落盘；版本变化时提醒 | 低 |
| 9 | 上下文压缩后协议被遗忘 | 模型本身的局限 | SessionStart 注入 STATUS；每个阶段都落盘；`last_phase` 可恢复 | 低 |

### 7.3 强隔离（可选，不是开箱必需）

如果第 1、2 项风险对你的项目不可接受，可以把**智能体会话放进一个没有 GPU 的容器**，仓库以读写方式挂载，评测代码和数据以只读方式挂载，test 不挂载。研究员仍然在宿主机终端运行 launch.sh。下面是示意，须按你的镜像、认证方式和路径调整：

```bash
docker run --rm -it --name ra-agent \
  -e NVIDIA_VISIBLE_DEVICES=void \          # 默认 runtime 是 nvidia 时，也不暴露 GPU
  -v "$PWD":"$PWD" -w "$PWD" \
  -v "$PWD/<评测代码目录>":"$PWD/<评测代码目录>":ro \
  -v "$PWD/<dev集目录>":"$PWD/<dev集目录>":ro \
  -v "$HOME/.claude":"$HOME/.claude" \      # 或 ~/.codex；按所用运行时
  <带 python/git/claude 或 codex 的镜像> claude
```

容器里没有 `nvidia-smi`。这时 feasibility L0 的占用证据改用 `research/ledger/runs.jsonl` 中已开始未结束的记录，外加你粘贴的 `nvidia-smi` 输出（存进本轮 `work/`）。launch.sh 在宿主机上还会再检查一次占用。

### 7.4 批准语句的交叉核对（Codex 用户建议每轮做一次）

```bash
python3 - <<'EOF'
import json
for l in open("research/ledger/human_inputs.jsonl", encoding="utf-8"):
    r = json.loads(l); p = r["payload"]; pr = (p.get("prompt") or "").strip()
    if pr.startswith(("批准", "驳回")):
        t = p.get("transcript_path"); txt = open(t, encoding="utf-8").read() if t else ""
        print("OK " if pr in txt else "?? ", r["ts"], pr[:60])
EOF
```

出现 `??` 时，打开对应的 transcript 人工确认。如果 transcript 里对文本做了转义，子串匹配会失败，这属于误报。

---

## 8 运维

### 8.1 磁盘与 checkpoint
- `.gitignore` 已经排除了权重文件。`runs/` 下的日志、`eval_dev.json`、标记文件都会随下一轮的锁定提交入库。
- 清理 checkpoint 由研究员执行。Claude 下 `rm` 会弹窗，`rm -rf` 被禁止；Codex 下这些命令被 rules 禁止。建议保留 champion 和最近两轮达标实验的 checkpoint。
- feasibility L0 要求预计的 checkpoint 占用不超过可用空间的 70%。不满足时，brief 会提示你先清理。

### 8.2 共享服务器
章程中写明保留卡和共享情况。`/ra-status` 会把卡的实际占用和 runs.jsonl 对照，列出不属于本项目的进程，但只报告、不处理。

### 8.3 test 集评测（里程碑确认，RL3，只能由研究员执行）

1. **时机**：里程碑评审时，或者 brief 提示 dev 查看计数已达到阈值。**对象**：只能是 knowledge.md 中已确认的 champion。同一个 champion 只测一次。
2. 输入：`批准(RL3) M2-test: R03-E1: 里程碑评审`。这条输入会被记入账本。
3. 在你自己的终端运行冻结的评测入口：`--split test`，输出只保留汇总指标，不含逐样本预测和标签，写到 `research/milestones/M2/test_R03-E1.json`。
4. 提交：`git add research/milestones && git commit -m "M2 test"`。
5. 下一轮的阶段 A 会引用这份结果（`ev:research/milestones/M2/test_R03-E1.json#…`），并起草里程碑确认的 CR（RL2）。
6. **test 结果不能用于之后的任何选择**。如果 test 和 dev 差距明显，brief 会提出"dev 过拟合"的讨论，可能的处理是更换或扩充 dev（RL3，需修订章程）。

### 8.4 升级 Claude Code / Codex
升级 → 重启 → `/ra-audit Rnn canary` → 全部 PASS 再开下一轮。出现 FAIL 时，要么修复配置，要么退回旧版本。版本号会记入下一轮的 `meta.yaml`。

### 8.5 备份
智能体被禁止 `git push`。由研究员定期执行 `git push`，或者备份整个仓库加上 `runs/` 中的 checkpoint。账本 `research/ledger/*.jsonl` 会随锁定提交入库，丢了可以从 git 恢复。

---

## 9 按项目定制清单

| # | 位置 | 占位符 / 默认值 | 改成 | 时机 |
|---|---|---|---|---|
| 1 | `.claude/settings.json` deny | `Edit(./eval/**)` | 评测代码目录 | 安装时 |
| 2 | 同上 | `Edit(./data/**)` | 训练和 dev 数据的根目录。预处理产物应写到 `runs/` 或缓存目录，不写进数据目录 | 安装时 |
| 3 | 同上 | `Read(./data/test/**)` | test 目录；在仓库外的写 `Read(//abs/path/**)` | 安装时 |
| 4 | `.claude/settings.json` | （无） | 日志在仓库外时，加 `"additionalDirectories": ["/abs/logs"]`（放在 permissions 里） | `/ra-init` |
| 5 | deny 规则 + `.codex/rules/ra.rules` | torchrun 等 | **补上你自己的启动器**，例如 `Bash(bash scripts/train*)`、`Bash(python3 train.py*)`；Codex 写 `prefix_rule(pattern=["bash","scripts/train.sh"], decision="forbidden")` | 安装时 |
| 6 | `research/templates/exp.sh` | `<训练入口>`、`<评测入口>`、`<ckpt>`、启动方式 | 按 project_card §1 填写；不用 torchrun 的项目，换成 accelerate、deepspeed 等的单机写法 | `/ra-init` 之后 |
| 7 | `research/charter.md` | 【待定】 | 逐项填写 | `/ra-init` 中 |
| 8 | `.claude/agents/*.md` | `opus`、`sonnet` | 完整模型 ID（建议） | 任意时候；属于 RL2 |
| 9 | `.codex/config.toml`、`.codex/agents/*.toml` | `gpt-5.6` | `/model` 中可用的完整 ID | Codex 用户 |
| 10 | OS | — | `chown root` 加 `chmod a-w` 评测与 dev；把 test 移出可读位置 | 安装第 5 步 |
| 11 | `research/templates/launch.sh` | — | 应用 §5.18 补丁 | 安装时 |
| 12 | 评测入口 | 输出位置 | 确认评测输出写到 `runs/`，不写进只读的评测目录 | `/ra-init` |

---

## 10 故障排除

| 现象 | 原因 | 处理 |
|---|---|---|
| 安装第 2 步创建 `research/hooks/` 或 `research/ledger/` 时被拒 | `.claude/settings.json` 先建好并生效了，它的 deny 规则挡住了后面的写入 | 让智能体**最后**创建 settings.json；或者自己在终端执行 `mkdir -p research/hooks research/ledger && touch research/ledger/.gitkeep`，再把 `ra_log.py` 粘贴进去 |
| Codex 安装时写不了 `.codex/*` | `.codex` 受沙箱保护 | 在提权请求中批准，或者手动创建 |
| 子代理产出文件没有生成 | hook 没生效，或者子代理没写 `ra:out` 首行 | 主会话会兜底落盘（文件头带 `written_by: lead`）。检查 `/hooks`（Codex）、`python3` 路径、K6 |
| 出现 `*.dup-*.md` | 目标文件已存在，hook 没有覆盖 | 一般是重复调用，以账本时间和 sha256 为准，人工判断保留哪份 |
| 技能列表里没有 ra-* | Claude Code 不认符号链接 | `rm .claude/skills && cp -r .agents/skills .claude/skills`。之后改技能要两边同步 |
| Codex 抱怨 SKILL.md 中的 `disable-model-invocation` | Codex 不认这个字段 | 在 Codex 使用的副本中删掉该字段。想禁止隐式调用的话，所用版本若支持，可以在技能目录下加 `agents/openai.yaml` 并写 `policy: {allow_implicit_invocation: false}`（以官方 Skills 文档为准） |
| 权限弹窗太多 | 只读命令不在 allow 列表里 | 把**只读**命令加进 allow。永远不要把 ledger、runs、评测目录或启动命令加进 allow |
| launch.sh 报"本轮文件有未提交或被修改的内容" | 锁定之后有人改过本轮文件 | 用 `git diff` 查看。如果是智能体改的，就属于协议偏离：恢复原状由研究员手动处理，或者走新版本 ERC 加重新批准 |
| launch.sh 报"有未提交的代码改动" | 锁定之后工作区又有改动 | 改动属于本轮实验的，就重新做锁定；不属于的，由你 stash 或另外提交 |
| 两个 torchrun 实验端口冲突 | 没用 `--standalone` | exp.sh 中保留 `--standalone`，或者给每个实验指定不同的 `--master_port` |
| 评测报"只读文件系统 / 权限不足" | 评测脚本往自己的目录里写缓存或输出 | 在 exp.sh 中把输出、缓存路径指到 `runs/$EXP/` |
| Codex 沙箱里 `nvidia-smi` 失败 | 沙箱限制了设备访问 | feasibility 改用 runs.jsonl 加你粘贴的输出；launch.sh 在你的终端里还会再检查 |
| 一轮跑得太慢、太贵 | 子代理多、上下文大 | 章程设 `protocol_mode: lite`；judge 用更便宜的模型；在 P1 prompt 中只给最近 3 轮的 decision |

---

## 11 版本与待核实项

本包所依据的平台行为，取自 2026-09/10 的公开文档和原型文档的核实记录。下面几项可能随版本变化，**以 canary 实测为准**：

| 事项 | 影响 | 核验方式 |
|---|---|---|
| Claude 子代理 frontmatter 的 `effort` 字段 | 钉死 effort | 版本不支持时字段会被忽略；用 §7.1 的 transcript 核对 |
| `.claude/skills` 符号链接能否被识别 | 技能是否可用 | 看技能列表 |
| Claude Bash 环境里是否有 `CLAUDECODE` | 模式 B | K8 |
| Codex 的 `features.memories`、`features.hooks` 键名 | 记忆与 hook 的开关 | K5、K6、`/status` |
| Codex rules 的 `forbidden` 是否对沙箱内命令同样生效 | GPU 与 git 防护 | K2 |
| Codex 自定义 agent 在并行 spawn 时是否严格采用 TOML 中的 model 与 sandbox_mode | 钉死与隔离 | §7.1 中 Codex 的 model 统计；`/status` |
| Codex 的 SubagentStop 是否带 `last_assistant_message` | 子代理产出自动落盘 | K6；出现 `written_by: lead` 就说明没带 |

到这里文档就完整了。安装和使用时有几点要注意：

- **装好之后最先做的检查**：先执行 `/ra-init`，再执行 `/ra-audit R00 canary`。这一步会实测上面那些可能随版本变化的平台行为。全部 PASS 再开第一轮。
- **两处安装细节**：
  - 第 2 步要让智能体最后创建 `.claude/settings.json`，否则后面写 `research/hooks/` 和 `research/ledger/` 时会被它自己的拒绝规则挡住；
  - §5.18 的 `launch.sh` 补丁必须一起应用，它负责在智能体会话里拒绝启动训练。
- **防护的实际强度**：防护措施能挡住误操作，挡不住有意规避，比如在 Python 里改写 `CUDA_VISIBLE_DEVICES` 来绕过 GPU 隔离。这类问题只能事后靠 git 审计发现。用 Codex 时护栏更弱：
  - 没有按路径的写入拒绝，评测代码和 dev 集只能靠 OS 层只读保护；
  - 账本文件可以被智能体写入，建议每轮用 §7.4 的脚本核对一次批准语句。

  如果这些风险对你的项目不可接受，就用 §7.3 的无 GPU 容器方案。

Learn more:
- <https://github.com/codealive-ai/ai-driven-development/blob/main/skills/hooks-management/references/codex-hooks.md>
- <https://code.claude.com/docs/en/hooks>
- <https://gist.github.com/FrancisBourre/50dca37124ecc43eaf08328cdcccdb34>
- <https://developers.openai.com/de-DE/docs/hooks>
- <https://developers.openai.com/codex/hooks/>
- <https://developers.openai.com/codex/exec-policy>
- <https://developers.openai.com/codex/rules>
- <https://learn.chatgpt.com/fr-FR/docs/agent-configuration/rules>
- <https://developers.openai.com/pt-BR/docs/agent-configuration/rules>
- <https://arxiv.org/html/2609.00006>
- <https://www.simplified.guide/codex/rule-add>
- <https://developers.openai.com/codex/config-advanced/>
- <https://majesticlabs.dev/blog/202607/codex-cli-configuration-guide>
- <https://developers.openai.com/codex/sandbox>
- <https://openai.com/index/running-codex-safely/>
- <https://developers.openai.com/codex/local-config/?ref=creativeainews.com>
- <https://github.com/openai/skills/blob/main/skills/.system/imagegen/references/codex-network.md>
- <https://community.openai.com/t/model-aware-task-delegation-for-subagents/1381671/2>
- <https://developers.openai.com/codex/guides/agents-md/>
- <https://daglo.ai/d/en/blog/codex-cli-setup-agents-md-guide-daglo>
- <https://developers.openai.com/codex/subagents/?ref=bushletter.com>
- <https://github.com/proflead/codex-agents-library>
- <https://github.com/shanraisshan/codex-cli-best-practice/blob/main/best-practice/codex-hooks.md>
- <https://github.com/stellarlinkco/codex/blob/main/docs/hooks.md>
- <https://developers.openai.com/plugins/llms-full.txt>
- <https://github.com/CorridorSecurity/hookshot/blob/main/docs/reference-codex.md>
