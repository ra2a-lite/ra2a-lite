---
audit_type: permissions_and_human_interaction
date: 2026-10-26
status: review_complete_proposal_only
scope: demo-revised
charter_trace: []
scope_note: 治理层审核，不提出科学实验，不进入轮次计划
research_round_started: false
protected_configuration_changed: false
---
# 人机交互、非 auto 批准与夜间无人值守审核

## 1. 结论与验证范围

当前设计同时存在三种等待：工具权限确认、研究员的业务批准、异常后的流程停等。它们由不同规则触发；批准计划不会自动消除后续 Python 执行、decision 写入和 git commit 的权限确认。依据：ev:.claude/settings.json#L41-L59；ev:.agents/skills/ra-round/SKILL.md#L75-L103。

**非 auto 的约束对象是作为批准凭据的用户输入，不是整个讨论、编码或审计会话。** CLAUDE.md 放行一般 auto 会话；ra-round 检查批准记录；ra-audit C14 检查的也是批准记录。依据：ev:CLAUDE.md#L6-L7；ev:.agents/skills/ra-round/SKILL.md#L20-L24；ev:.agents/skills/ra-audit/SKILL.md#L31-L31。

本次进行了配置与流程静态审核、版本检查和 Codex 离线规则查询；未进行 Claude 权限 UI 实测，也未运行 ra-audit canary、训练、评测或 GPU 作业。证据脚本和输出位于 `research/audits/permissions-2026-10-26/work/`。候选命令只作为 execpolicy 查询的数据，不会被执行。依据：ev:research/audits/permissions-2026-10-26/work/inspect_permissions.py#L80-L113；ev:research/audits/permissions-2026-10-26/work/policy_checks.json#0.candidate_executed。

本机版本为 Claude Code 2.1.247、Codex CLI 0.164.0；项目 Claude 配置没有 sandbox 块，当前 PATH 未发现 bwrap。这不等于已经排除了其他外部隔离机制；外部容器与设备权限未核验。依据：ev:research/audits/permissions-2026-10-26/work/inventory.json#claude.stdout；ev:research/audits/permissions-2026-10-26/work/inventory.json#codex.stdout；ev:research/audits/permissions-2026-10-26/work/inventory.json#bwrap_in_path；ev:research/audits/permissions-2026-10-26/work/inventory.json#claude_sandbox_in_project_settings。

## 2. 工具层：哪些操作会触发确认

下表的 Claude 项按仓库配置与当前官方规则语义解释。实际安装版 UI、用户/管理层覆盖仍需目标环境实测；不是本轮已观测到的弹窗次数。

| action | 当前配置与触发条件 | 是否等于研究批准 | evidence |
|---|---|---|---|
| 读取普通代码、日志、研究文件 | 通常不要求确认；test 与令牌等禁读项除外 | 否 | ev:.claude/settings.json#L61-L68；[Claude 权限说明](https://code.claude.com/docs/en/permissions#permission-system) |
| 修改普通业务代码、配置、已有单元测试 | `defaultMode=default`，Edit allow 只列出若干 research 路径，没有普通代码目录；因此未获其他授权时会进入文件修改确认 | 否；研究任务本身仍须在授权范围内 | ev:.claude/settings.json#L12-L19；ev:AGENTS.md#L6-L8 |
| 写 rounds、STATUS、project_card、记忆提案、审计报告 | 有 Edit allow，通常可直接写；decision.md 的 ask 优先 | 否 | ev:.claude/settings.json#L15-L19；ev:.claude/settings.json#L47-L47 |
| `python3 research/rounds/...` | 整类 ask；analyst 分析脚本、P5 tally、verifier 复算都落入该范围 | 否 | ev:.claude/settings.json#L55-L55；ev:.claude/agents/ra-analyst.md#L12-L15；ev:.agents/skills/ra-round/SKILL.md#L58-L60 |
| `bash research/rounds/...` | 整类 ask，同时覆盖简单 CPU 脚本与 launch.sh | 否；launch 另有研究批准 | ev:.claude/settings.json#L54-L54 |
| Python 编译检查 | `python3 -m py_compile ...` 有 allow；不代表任意 Python 都放行 | 否 | ev:.claude/settings.json#L37-L37 |
| 其他 CPU 命令、单元自检、联网/下载 | 未被当前 allow 覆盖者，default 下可能需要确认；不能因运行在 CPU 就视为无副作用 | 否 | ev:.claude/settings.json#L20-L39；[Claude 权限说明](https://code.claude.com/docs/en/permissions#permission-system) |
| 写 decision.md | 独立 Edit ask；已有计划批准也不消除这次工具确认 | 否，属于第二道工具门 | ev:.claude/settings.json#L47-L47；ev:.agents/skills/ra-round/SKILL.md#L83-L85 |
| 改章程、rubric、PROTOCOL、模板、正式记忆、AGENTS/CLAUDE、代理/技能/配置 | Edit ask；另外要求本次对话中明确同意具体修改 | 权限点击与具体变更批准是两件事 | ev:.claude/settings.json#L42-L52；ev:AGENTS.md#L15-L16 |
| `git commit` | Claude ask；Codex 项目规则 prompt，且 .git 写入涉及沙箱边界 | 否；锁定、记忆流程另外要求研究员确认 | ev:.claude/settings.json#L53-L53；ev:.codex/rules/ra.rules#L26-L34；ev:.agents/skills/ra-memory/SKILL.md#L15-L15 |
| `rm`、kill、pkill、tmux kill-session | 列入 ask；训练终止还受研究流程约束；`rm -rf` 属 deny | 否 | ev:.claude/settings.json#L56-L59；ev:.claude/settings.json#L89-L89；ev:.agents/skills/ra-status/SKILL.md#L10-L11 |
| Codex：`env ...` | 项目规则把所有 env 前缀设为 prompt，包括设置空 CUDA 和只设置随机种子的情况；离线查询已复现 | 否；审批请求由当前 reviewer 路由，不一定展示给人 | ev:.codex/rules/ra.rules#L17-L18；ev:research/audits/permissions-2026-10-26/work/policy_checks.json#2.policy_result；ev:research/audits/permissions-2026-10-26/work/policy_checks.json#3.policy_result |
| Codex：普通工作区编辑/CPU 执行 | workspace-write + on-request 本身不要求每次人工批准；离线查询中裸 Python、裸 Bash 没有命中本项目规则，不能将 Claude 的 Python ask 套用到 Codex | 否 | ev:.codex/config.toml#L5-L10；ev:research/audits/permissions-2026-10-26/work/policy_checks.json#0.policy_result；ev:research/audits/permissions-2026-10-26/work/policy_checks.json#1.policy_result |
| Codex：写工作区外、受保护路径或请求网络例外 | 可能形成沙箱越界审批；是否由人处理取决于有效 reviewer 与更高层策略 | 否 | ev:.codex/config.toml#L5-L10；[Codex 沙箱与审批](https://learn.chatgpt.com/docs/sandboxing#configure-defaults) |

`ask` 不是研究风险等级 RL2/RL3 的自动映射：当前 CPU 分析也被设为 ask；`deny` 则不是点 Yes 就能继续的事项。GPU/训练命令、test、评测写入、历史改写等禁止项不应计作普通的审批弹窗。CPU 上的训练或评测也不属于普通 CPU 分析的自动授权。依据：ev:research/PROTOCOL.md#L139-L146；ev:AGENTS.md#L13-L19；ev:.claude/settings.json#L61-L89。

**版本语义有一处重要冲突。** PATCH-v2.3.md 把 auto 下的 Python ask、decision 编辑确认等描述为会被分类器软化；当前 Claude 官方说明则规定显式 ask 仍要求确认，且 ask 优先于 allow。不能再把“切到 auto”当作移除这些弹窗的方案。安装版 2.1.247 的逐项 UI 行为本轮未核验，需在部署验收中核对并修正文档。依据：ev:PATCH-v2.3.md#L49-L78；[Claude 规则优先级](https://code.claude.com/docs/en/permissions#manage-permissions)；[Claude auto 的决策顺序](https://code.claude.com/docs/en/permission-modes#how-auto-mode-evaluates-actions)。

补充：PATCH 称 Codex rules 的 Python 本就 prompt，但当前 ra.rules 没有通用 Python prompt，离线查询也没有命中。应以实际文件和有效运行时为准。依据：ev:PATCH-v2.3.md#L93-L93；ev:.codex/rules/ra.rules#L1-L40；ev:research/audits/permissions-2026-10-26/work/policy_checks.json#0.policy_result。

## 3. 流程层：哪些地方必须由研究员交互

| stage | 研究员需要做什么 | 是否属于必须非 auto 的批准输入 | evidence |
|---|---|---|---|
| ra-init 初始化 | 补目标、范围、预算、里程碑、启动方式等；确认章程与保护配置；确认初始化提交 | 普通补充信息没有模式要求；形成正式批准时按非 auto 规则处理 | ev:.agents/skills/ra-init/SKILL.md#L20-L26；ev:CLAUDE.md#L7-L7 |
| ra-round 讨论门 | 阅读 brief 后亲自输入正式批准或驳回；“好/继续”和点选不算批准 | **正式批准必须**；驳回、澄清没有同样的非 auto 要求 | ev:.agents/skills/ra-round/SKILL.md#L75-L81 |
| RL3 决定 | 对超预算、test、评测/章程变更、协议偏离等输入 RL3 批准并附理由；如章程规定则还需第二确认人 | **必须** | ev:research/PROTOCOL.md#L145-L152；ev:.agents/skills/ra-round/SKILL.md#L79-L81 |
| P7 决策存档 | 批准后写 decision，当前仍有工具确认 | 写文件动作本身没有必须切模式的独立条文；批准凭据必须非 auto | ev:.agents/skills/ra-round/SKILL.md#L81-L85 |
| L 预注册锁定 | 审阅实现与清单，确认提交冻结 | 有明确人工确认要求；未额外规定提交命令必须处于非 auto | ev:.agents/skills/ra-round/SKILL.md#L88-L98 |
| X 启动：模式 A | 研究员在自己的终端运行 launch.sh | 人工启动；脚本检查之前记录的批准，不检查终端权限模式 | ev:.agents/skills/ra-round/SKILL.md#L100-L103；ev:research/templates/launch.sh#L28-L35；ev:research/templates/launch.sh#L45-L87 |
| X 启动：模式 B | 显式调用 ra-launch，核对并放行 launch 的工具确认；仅 Claude，且章程须 B | 启动前的批准凭据必须非 auto；技能未另写启动会话必须非 auto | ev:.agents/skills/ra-launch/SKILL.md#L1-L15；ev:research/templates/launch.sh#L76-L81 |
| 技术故障重跑 | 输入“批准重跑”，登记新 id，再提交并由研究员启动 | **必须**；纳入 ra-round 开轮对批准记录的检查 | ev:research/PROTOCOL.md#L67-L71；ev:.agents/skills/ra-round/SKILL.md#L23-L23 |
| ra-memory | 逐条批准/驳回/修改 CR；实际写正式记忆等受保护文件另有工具确认；再确认提交 | **批准 CR 必须**；不能以批量默认通过代替 | ev:.agents/skills/ra-memory/SKILL.md#L11-L15；ev:.agents/skills/ra-round/SKILL.md#L23-L23 |
| 冠军更新、里程碑确认 | 按 RL2 批准；冠军还须已达标的确认性证据与 CR | **形成批准记录时必须** | ev:research/PROTOCOL.md#L115-L115；ev:research/PROTOCOL.md#L145-L146 |
| 命中 abort 条件 | 展示证据，研究员决定是否停止并执行终止 | 有人工决定要求；并非 agent 可自行终止 | ev:.agents/skills/ra-status/SKILL.md#L10-L11；ev:AGENTS.md#L13-L13 |
| ra-audit / ra-status 的读取、核对与报告 | 通常可由 agent 完成；canary 的权限实验及环境修复可能引入额外交互 | **执行审核本身没有必须非 auto 的条文**；C14 核验的是批准记录 | ev:.agents/skills/ra-audit/SKILL.md#L6-L42；ev:.agents/skills/ra-status/SKILL.md#L5-L9 |
| 普通讨论、角色评审、草拟候选/ERC、提案、CPU 分析、已批准范围内编码 | 研究层面无需逐次批准，但当前工具 ask 仍可能打断 | **不要求非 auto** | ev:research/PROTOCOL.md#L140-L144；ev:AGENTS.md#L6-L9；ev:CLAUDE.md#L7-L7 |

特别区分：“在 auto 会话输入了一条批准”与“在 auto 下执行之前已经批准的工作”不同。前者会被批准核验排除，后者不因 auto 身份自动无效；仍要遵守具体工具规则和任务边界。依据：ev:.agents/skills/ra-round/SKILL.md#L23-L23；ev:.agents/skills/ra-round/SKILL.md#L81-L81；ev:research/templates/launch.sh#L69-L84。

## 4. 非 auto 是怎样检查的，哪些只是流程要求

1. **总原则**：CLAUDE.md 要求批准语句来自非 auto。ra-round 开轮明确列出普通轮次批准、RL3、重跑和 CR 批准，发现 auto 批准记录就停止。依据：ev:CLAUDE.md#L7-L7；ev:.agents/skills/ra-round/SKILL.md#L23-L23。
2. **讨论门**：ra-round 在账本查找原文并检查该条 `payload.permission_mode`；无记录则不能进入决策。依据：ev:.agents/skills/ra-round/SKILL.md#L79-L81。
3. **启动脚本**：只筛选本轮“批准/批准(RL3)”记录；字段等于 auto 时排除，随后检查时间与实验覆盖。脚本并未验证整个会话始终非 auto。依据：ev:research/templates/launch.sh#L55-L84。
4. **审计**：C14 是批准记录的事后检查，不是强制 ra-audit 使用非 auto 的配置。现有 R00 审计还明确记录过 auto 模式下执行审计指令的情况。依据：ev:.agents/skills/ra-audit/SKILL.md#L31-L31；ev:research/audits/R00-2026-10-23.md#L22-L27。
5. **覆盖缺口**：ra-memory 本身未明确重复检查 permission_mode；retry 分支只检查已提交的 retries 登记，未独立核验这次重跑批准的 mode。总原则仍要求非 auto，不能把实现缺口解释成许可。依据：ev:.agents/skills/ra-memory/SKILL.md#L11-L15；ev:research/templates/launch.sh#L107-L113；ev:.agents/skills/ra-round/SKILL.md#L23-L23。
6. **字段缺失缺口**：launch.sh 使用 `(p.get("permission_mode") or "") == "auto"`，会接受未提供该字段的记录进入后续检查。“不等于 auto”不等于已验证来自可信人工通道；跨平台应使用各平台的明确人工来源证据，缺失时不应默认可信。依据：ev:research/templates/launch.sh#L72-L79；ev:.codex/hooks.json#L8-L10。

切模式只需覆盖研究员输入有效批准的那一步。当前文件建议用 default/plan 重新输入；plan 是只读工作方式，批准输入完成后还需切回可执行工作方式才能继续实现。依据：ev:.agents/skills/ra-round/SKILL.md#L23-L23；[Claude 权限模式](https://code.claude.com/docs/en/permission-modes#available-modes)。

## 5. 即便没有权限弹窗，仍会停等的地方

| trigger | 当前行为 | evidence |
|---|---|---|
| 任意阶段失败或不完整 | 全轮停在该阶段，询问研究员 | ev:.agents/skills/ra-round/SKILL.md#L16-L16 |
| 控制文件不干净、CUDA 环境不合规、存在 auto 批准 | 开轮失败即停止报告 | ev:.agents/skills/ra-round/SKILL.md#L20-L24 |
| 运行时版本变化 | 提议 canary 并询问是否继续 | ev:.agents/skills/ra-round/SKILL.md#L24-L24 |
| 上一轮实验全部未完成 | 询问结束等待还是基于已有信息继续设计 | ev:.agents/skills/ra-round/SKILL.md#L28-L28 |
| P3 输出缺失且一次重调仍失败 | 停下 | ev:.agents/skills/ra-round/SKILL.md#L45-L47 |
| 检测到本轮 compact 事件 | P2/P6/P7 入口判 incomplete 并停止 | ev:.agents/skills/ra-round/SKILL.md#L42-L42；ev:.agents/skills/ra-round/SKILL.md#L64-L64；ev:.agents/skills/ra-round/SKILL.md#L84-L84 |
| 人尚未批准、批准无账本证据 | 不进入 P7 | ev:.agents/skills/ra-round/SKILL.md#L79-L81 |
| 锁定完成 | 交付启动，本次交互结束；训练完成后再由研究员调用下一轮 | ev:.agents/skills/ra-round/SKILL.md#L100-L103；ev:.agents/skills/ra-status/SKILL.md#L12-L12 |
| 冻结后需要改 ERC/脚本 | 新版本、重新批准并重新锁定 | ev:.agents/skills/ra-round/SKILL.md#L98-L98 |

因此，“消除普通权限弹窗”“一次任务持续过夜”“多轮实验自动闭环”是三个不同目标。当前模板可支持准备工作和已经启动的批次，但没有授予 agent 连续自行批准新轮次的权限。依据：ev:.agents/skills/ra-round/SKILL.md#L75-L103；ev:AGENTS.md#L13-L19。

## 6. 重新权衡后的建议

以下均为待评审方案，本轮未应用。

### 6.1 保留的人工边界

- 人工确认研究方向/范围、预算、对外资源承诺、正式实验计划、正式记忆与规则变更。
- 批准记录从明确的人工通道取得；普通工作会话可以 auto，自动工具审查不能替研究员签研究批准。
- test、评测冻结、账本完整性、锁定后不可改、禁止自行变更研究含义继续作为硬约束。

### 6.2 日常工作与批准入口分开

建议工作会话承担讨论、证据回收、草拟候选、代码修改与允许的 CPU 自检；审核/签署入口只在准备好的变更包上取得人工决定。无需让工作会话长期停留在 default。

批准应绑定可审阅的具体内容，例如源码/配置、ERC、实验清单与资源预算的 digest，而不只绑定 exp_id。后续写入 decision、登记锁定等机械动作在内容一致时复用已有授权，避免再次要求人核对同一件事。若语义或预算变化，重新送审。

可以先保留现有研究计划批准，再减少其后的重复工具门；若希望收敛为一次最终批准，需要同时调整当前“先 P7、后 I 实现”的顺序，预授权无资源承诺的草案实现，让人看到代码与 CPU 自检后再签署。不能只删弹窗而保持相互冲突的流程文字。

### 6.3 先建立执行边界，再放行 CPU 工作

普通源码/配置/已有单元测试/文档的可写范围要在接入项目时明确登记。正式评测、数据、规则、账本与冻结产物应位于 agent 不能通过 Python 或 Shell 任意改写的边界之外：可选只读挂载、独立权限主体或经过验证的沙箱。GPU 禁止应由设备/调度权限保证，空 CUDA 环境只作为辅助。

在该边界经过验证后，再移除覆盖所有轮次 Python/Shell 的 ask，放行边界内的 CPU 分析与软件自检。只增加更细的 allow 无法盖过当前 broad ask；只放行一个可由 agent 任意改写的 Python 文件，也不是安全隔离方案。

Claude 可采用隔离内 auto 工作，或者在沙箱内采用 `acceptEdits` 与自动放行 Bash 的组合；内容级 ask 仍需逐项重划。当前项目缺 sandbox 配置、PATH 未发现 bwrap，不能声称只改一个开关就获得这些保证。沙箱方案须验证可用性、关闭未沙箱重试，并核对不同工具与 hook 的覆盖面。参考：[Claude 沙箱](https://code.claude.com/docs/en/sandboxing#sandbox-modes)。

Codex 保持 workspace 边界；按部署能力选用 on-request + auto_review 处理工具例外，或使用 never 的无人值守配置让越界操作立即拒绝并记入待办。**never 是不询问，不是自动授权越界；auto_review 也不是研究员批准。** 项目现有 on-request 不是普通工作区编辑的逐次确认开关。参考：[Codex 配置含义](https://learn.chatgpt.com/docs/sandboxing#configure-defaults)、[自动审批审查](https://learn.chatgpt.com/docs/agent-approvals-security#automatic-approval-reviews)。

### 6.4 夜间遇到审批项，挂起相应分支

建议允许对纯机械故障做有限次数的修复/重试；没有人工回复时，将需要批准的事项写为 pending_human，继续已授权且不依赖它的工作。不得越过缺失审批进入决策/启动，不得改变预注册的科学内容。

建议用阶段产物、输入输出 hash 与状态记录恢复上下文。压缩发生在阶段边界时核验后进入下一阶段；发生在独立评审中途时，用冻结输入重做受影响的评审，不复用被污染的角色上下文。替换目前“本轮出现过 compact 就在后续入口停止”的规则需要单独修订协议/技能。

夜间运行前应准备依赖、允许访问的目录/域名与资源上限，使用无交互启动方式验收。不能让新的授权需求隐式等待终端 Yes；必须即时拒绝或登记为待办，并保留其余独立任务的进展。

### 6.5 两种夜间工作目标

| scenario | 可交付的夜间工作 | 人工边界 |
|---|---|---|
| 睡前尚未批准研究计划 | 完成允许的分析、讨论、候选方案、代码草案与 CPU 自检，形成待审材料 | 不自行批准或启动新研究作业 |
| 睡前已经批准并启动一个冻结批次 | 批次依照既定脚本执行；agent 只读监控、回收已经完成的结果、准备下一批材料 | 新实验、扩大预算、研究含义变更仍重新审批 |

更进一步的预授权批次队列可作为后续方案：由权限独立的 runner 只接受人工签署的冻结清单，执行限定资源、期限、次数与故障策略；agent 不能新增实验或自行签发授权。这属于协议与执行架构改动，不是切 auto 就能实现。

## 7. 建议修改清单与验收

| priority | target | change |
|---|---|---|
| P0 | PATCH-v2.3.md、使用说明 | 修正 ask/auto 语义与“Codex Python 本就 prompt”等漂移；公布本报告的三类交互清单 |
| P0 | 隔离部署、.claude/settings.json、.codex 配置 | 明确普通工作可写目录、CPU/网络边界；验证后缩小 Python/Shell/env 的整类确认；保护资产继续独立控制 |
| P0 | ra-round、ra-memory、launch.sh、ra-audit | 统一批准来源验证，补 CR/retry 与字段缺失处理；避免只用 mode 不等于 auto 判断可信性 |
| P1 | ra-round、decision/brief 模板、PROTOCOL | 明确草案实现权限；批准绑定具体内容；已批准内容的机械存档尽量不重复请求批准 |
| P1 | ra-round、STATUS/meta 约定 | 加入 pending_human、有限机械重试与阶段恢复；审批失败继续阻断依赖分支 |
| P2 | 受信 runner 与批次清单 | 如需批次无人值守执行，新增带资源/次数/期限约束的授权机制；训练启动权限不交给讨论 agent |

上述控制文件修改都必须取得具体授权后实施；本报告不构成批准，也不修改既有规则。

建议验收以下场景，验收脚本只能在专用假目录/模拟资源上操作；实际 test 与 GPU 不参与权限探测：

1. 正常源码修改、配置解析、CPU 自检、角色分析与评分汇总全程没有人工工具弹窗。
2. 修改规则/正式记忆、越界访问、尝试使用不可用资源被拒绝或转 pending_human；其他独立的已授权工作继续。
3. auto 下的普通用户意见允许记录；auto 下的正式批准不能生效；可信非 auto 批准可用；来源字段缺失不视为可信。
4. 一次批准后，相同 digest 的机械存档不重复签署；digest/资源/实验集合变化后，旧批准失效。
5. CR 和 retry 走同一套批准验证；重复启动被阻断；批准撤回或到期不能执行。
6. 运行时升级、阶段压缩、一个角色的机械失败能够落盘并按预定策略恢复；恢复不破坏独立评审。
7. 以无人值守入口连续运行一个工作批次，最终只有完成产物或明确待审事项，不存在悬置的工具权限输入框。

## 8. 本轮变更范围

本轮新增本报告、只读收集脚本及其 work 输出，并在 STATUS 添加审核索引；没有修改控制配置、技能、协议、模板、正式记忆或既有账本。收集时保护文件的 git status 为空；原有账本和 R00 报告变更已保留。依据：ev:research/audits/permissions-2026-10-26/work/inventory.json#protected_status_at_collection.stdout；ev:research/audits/permissions-2026-10-26/work/inventory.json#git_status_at_collection.stdout。
