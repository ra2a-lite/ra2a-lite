---
version: v2.4-plan-2
supersedes: v2.4-plan-1
date: 2026-10-26
status: b0_b1_applied_v2.4
charter_trace: []
scope_note: 治理与开发工作流改造，不提出研究实验，不修改研究目标
reviews:
  - update/claude_review_auto_mode.md
  - update/claude_review_auto_mode_2.md
  - update/plan_review.md
prior_audit: research/audits/permissions-2026-10-26.md
---
# 两份 review 对账与最终修改执行方案

## 1. 最终取舍

建议先交付“日常开发少弹窗、夜间代码与 CPU 工作不等人”，随后增加“人工预批固定实验批次，由隔离外的受信执行器运行”。不把预算/轮数上限直接解释成对未来任意代码和实验的授权。

长期目标是日常 Claude 使用 `acceptEdits`，在隔离配置中保留 auto 选项，继续禁止 bypass。B1 必须先验证文件系统命令不会削弱保护，再切默认模式；未通过时保留 default，只精确放行已登记的普通源码编辑。B2 验收前的未隔离会话临时禁用 auto，B2 隔离与目标版本回归通过后再恢复。上述均为拟议变更，尚未改变当前已放行 auto 的配置。

正式批准的首版目标入口改为隔离外的宿主独立人工命令；它不运行模型，属于人工签署通道。worker 的权限模式、hook 载荷和环境标签都不证明人工身份，聊天中的批准文字仅作镜像。这个操作习惯变化列为 B2 实施前须明确接受的设计决定，不能由本次读 review 推断已获批准。夜间 Claude 使用显式 dontAsk 无头入口；Codex 使用保留沙箱的 never 入口。纯读取审计不要求业务批准，但运行模式仍须遵守部署策略。

相对 plan-1，本版修正“B2 前仍直接保留 auto”和“B1 直接切 acceptEdits”的实施顺序，不推翻隔离后可用 auto 的长期目标。本机重新核对为 2.1.247；官方 2.1.257 更新日志明确记载 auto 中复合命令/子 shell 跳过 ask 的修复。版本风险已核实，未在本机实际复现绕过。依据：ev:update/plan_review.md#L24-L49；ev:research/audits/permissions-2026-10-26/work/plan-review-r2/runtime_evidence.json#claude_version.stdout；[官方更新日志](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md#21257)。

`dontAsk` 是把需要确认的调用拒绝，不能让缺失授权的工作自动通过；agent 应把事项列为待审并继续独立工作。依据：[Claude dontAsk](https://code.claude.com/docs/en/permission-modes#allow-only-pre-approved-tools-with-dontask-mode)。Codex 的 `never`、`workspace-write` 与 `auto_review` 也是不同设置，自动工具审查不等于研究员批准。依据：[Codex 沙箱与审批](https://learn.chatgpt.com/docs/sandboxing#configure-defaults)。

本方案分 B0–B4 实施。B0–B3 作为拟议核心改造；B4 是新增资源执行授权类型，单独交付。B3 只覆盖夜间代码/CPU 工作，B4 只覆盖事先签署的固定实验清单；“夜间自行设计新实验并连续启动新轮次”须另行修订研究决策授权协议。原始诉求未明确授予该能力，也不能默认研究员已接受把所有夜间迭代目标限制到当前版本；实施授权须写清选择的能力范围。

## 2. 对账结果

以下 R1、R2 分别指第一、第二份 review。“采纳”表示采纳建议或静态结论，不表示已经完成运行时验收。

| id | review 观点 | 对账裁定与最终处理 | evidence |
|---|---|---|---|
| D01 | 原版就存在普通代码编辑弹窗，PATCH 又增加轮次 Python 弹窗 | 采纳。问题同时来自 Lite 默认配置与补丁的权限收紧 | ev:update/claude_review_auto_mode_2.md#L42-L53；ev:ra2a_lite_8xa100.md#L1158-L1179；ev:.claude/settings.json#L53-L55 |
| D02 | P1/P3/P4 等子代理阶段会密集弹窗 | 有条件采纳。带 Bash 的角色复用相关权限会放大影响；具体弹窗次数、哪个阶段最多未核验，不能把所有角色都视为会执行 Python | ev:update/claude_review_auto_mode_2.md#L55-L55；ev:.claude/agents/ra-analyst.md#L4-L16；ev:.claude/agents/ra-judge.md#L4-L7；ev:.claude/agents/ra-designer.md#L4-L12 |
| D03 | 显式 ask 不会因为切 auto 就消失 | 采纳当前官方语义；修正 PATCH。补充：dontAsk 下是拒绝，不是“所有模式都弹窗”；本机 UI 仍须验收 | ev:update/claude_review_auto_mode.md#L103-L114；ev:PATCH-v2.3.md#L45-L64；[Claude 规则优先级](https://code.claude.com/docs/en/permissions#manage-permissions) |
| D04 | v2.1.283 起默认 auto 导致当前问题 | 采纳 R2 更正。项目明确设置 default，不能用平台默认值直接解释实际会话；本机已记录版本还早于该版本 | ev:update/claude_review_auto_mode_2.md#L91-L94；ev:.claude/settings.json#L12-L12；ev:research/audits/permissions-2026-10-26/work/inventory.json#claude.stdout |
| D05 | Codex 的 Python 也设为 prompt；allow 全是只读操作 | 更正。当前 Codex 没有通用 Python prompt；Claude 还允许轮次文件编辑、git add、py_compile，不能概括成“只有只读” | ev:update/claude_review_auto_mode.md#L116-L124；ev:.claude/settings.json#L15-L39；ev:research/audits/permissions-2026-10-26/work/policy_checks.json#0.policy_result |
| D06 | 改 acceptEdits 并恢复 disableAutoMode | 经 plan review 修订：acceptEdits 通过保护验收后才设默认；未隔离过渡期临时禁 auto，B2 与版本回归通过后再恢复。正式批准走独立人工入口 | ev:update/claude_review_auto_mode.md#L179-L214；ev:update/plan_review.md#L24-L49；[Claude 权限模式](https://code.claude.com/docs/en/permission-modes#available-modes) |
| D07 | 没有 GPU 的隔离环境后再放宽 Python | 采纳顺序。隔离还须覆盖全部工具、控制文件/账本、宿主套接字和远程调度凭据；仅 nvidia-smi 失败不能证明设备不可访问 | ev:update/claude_review_auto_mode.md#L164-L173；ev:update/claude_review_auto_mode.md#L318-L323；ev:ra2a_lite_8xa100.md#L1647-L1676 |
| D08 | 直接采用 R1 的 settings 样例 | 不整体采用。样例把正式记忆写成 research/knowledge.md 等错误路径，遗漏现有模板/.codex 等保护项；只能基于当前配置做增量修改 | ev:update/claude_review_auto_mode.md#L193-L204；ev:.claude/settings.json#L42-L52；ev:research/PROTOCOL.md#L164-L169 |
| D09 | demo-revised 已满足审批把关；F1/F2/F6 已修 | 更正为“有所加强，尚未闭环”。本次标记文件不存在，白名单未激活；CR/retry 与缺失 mode 检查仍有缺口，同用户脚本写入风险仍须隔离 | ev:update/claude_review_auto_mode_2.md#L65-L67；ev:research/hooks/ra_log.py#L15-L18；ev:research/audits/permissions-2026-10-26/work/reconciliation_evidence.json#whitelist_marker_exists；ev:research/templates/launch.sh#L69-L84；ev:research/templates/launch.sh#L107-L113；ev:.agents/skills/ra-memory/SKILL.md#L11-L15 |
| D10 | 非 auto 白名单只接受 default/acceptEdits | 经 plan review 明确分层：现行对话的 default/acceptEdits/plan 只用于旧机制核验；B2 新权威来自宿主独立人工签署，不信任 worker 自报 mode。新通道的 permission_mode 为显式 null，不伪填 default | ev:update/claude_review_auto_mode.md#L212-L214；ev:update/plan_review.md#L51-L59；ev:.agents/skills/ra-round/SKILL.md#L23-L23 |
| D11 | 由 RA_SESSION != night 证明人类批准；agent 改不了该环境变量 | 不采纳其安全保证（设计推论）。具备代码执行能力的进程可以为新子进程选择环境，不能靠标签证明人工来源；保留标签用于日志，批准凭据由隔离外人工入口签发 | ev:update/claude_review_auto_mode.md#L286-L289；ev:.claude/agents/ra-analyst.md#L15-L16；ev:research/hooks/ra_log.py#L100-L107 |
| D12 | dontAsk 解决夜间挂在权限输入框 | 采纳，但必须补齐允许的工作链、子代理配置与待审队列；否则只是从“等待”变成“被拒后全轮终止” | ev:update/claude_review_auto_mode.md#L276-L295；ev:.agents/skills/ra-round/SKILL.md#L16-L16；[Claude dontAsk](https://code.claude.com/docs/en/permission-modes#allow-only-pre-approved-tools-with-dontask-mode) |
| D13 | 用 night_decision.md 绕过 decision ask；用 ra-lock 包装 git commit | 改为正式的草稿/签署分离：夜间只能产出 draft；有效批准后由受信落盘器发布 decision 并锁定。包装脚本路径 allow 不是授权证明 | ev:update/claude_review_auto_mode.md#L278-L284；ev:.agents/skills/ra-round/SKILL.md#L79-L98 |
| D14 | 睡前批准宽泛信封，早上追认夜间新实验为正式记录 | 不按原案采用。预算上限与 change 类别标签不足以核验未来任意代码；追认不能补成启动前批准。B4 仅执行事先签署、内容冻结的固定清单 | ev:update/claude_review_auto_mode.md#L222-L246；ev:update/claude_review_auto_mode.md#L302-L311；ev:research/PROTOCOL.md#L21-L24；ev:research/PROTOCOL.md#L139-L152 |
| D15 | 只用已耗 GPU·h + 新实验估计判断预算 | 补强。须原子预留在途预算、并发资源与启动次数，处理超时、撤销、重启与重复请求；估计不能代替运行时硬限制 | ev:update/claude_review_auto_mode.md#L306-L312；ev:research/templates/erc.yaml#L13-L13；ev:research/templates/erc.yaml#L31-L38 |
| D16 | launcherd 用研究员 uid，所以仍是现有模式 A | 不采纳该等同。现有 A 是研究员自己启动脚本；委托执行器自动启动/终止是新增授权能力，须显式改协议，不能靠 uid 推定权限 | ev:update/claude_review_auto_mode.md#L266-L270；ev:research/PROTOCOL.md#L7-L8；ev:.agents/skills/ra-round/SKILL.md#L100-L103 |
| D17 | 新无头会话每轮一次即可避开压缩；skeptic veto 替讨论门 | 部分采纳分段运行；整轮仍可能压缩，须阶段检查点。独立角色保持新上下文；新 veto 阈值不擅自改 rubric，也不能替人签署 | ev:update/claude_review_auto_mode.md#L272-L295；ev:.agents/skills/ra-round/SKILL.md#L42-L64；ev:research/PROTOCOL.md#L19-L23 |
| D18 | 先统计一天弹窗，再开发；Notification 可统计每次弹窗 | 补正。短基线采样与开发可并行，不强制等待一天；Notification 可能延迟且漏掉快速应答，须结合权限请求与调用结果。事件支持以部署版本验收为准 | ev:update/claude_review_auto_mode.md#L343-L358；[Claude 权限事件](https://code.claude.com/docs/en/hooks#permissionrequest)、[通知事件](https://code.claude.com/docs/en/hooks#notification) |
| D19 | 修改 Lite 文档后重新生成所有文件 | 采纳同步维护，不做全量覆盖。先合并现有 v2.3 修复，再同步受影响代码块，避免旧模板覆盖令牌/批准/白名单修复 | ev:update/claude_review_auto_mode_2.md#L98-L112；ev:PATCH-v2.3.md#L23-L31；ev:ra2a_lite_8xa100.md#L173-L175 |
| D20 | 启用 K10–K13、约 150 行实现守护进程 | 采纳测试目标，不接受行数即复杂度承诺。隔离、恢复、授权与资源限制通过后才交付自动执行；测试使用合成目录/模拟执行器 | ev:update/claude_review_auto_mode.md#L314-L323；ev:update/claude_review_auto_mode.md#L351-L358 |
| D21 | 当前“夜里根本跑不起来” | 更正绝对化表述。研究员睡前已启动的冻结批次可在 tmux/nohup 中继续；缺的是无人参与时的新决定、新启动与自动开下一轮 | ev:update/claude_review_auto_mode.md#L329-L335；ev:research/templates/launch.sh#L89-L104；ev:.agents/skills/ra-round/SKILL.md#L100-L103 |
| D22 | 原 demo 缺 git、技能链接、gitignore 是安装遗漏 | 采纳责任归类；当前包已记录补齐，不在本次执行中重复 git init、清空账本或全量生成 | ev:update/claude_review_auto_mode_2.md#L80-L87；ev:ra2a_lite_8xa100.md#L91-L141；ev:PATCH-v2.3.md#L13-L19 |

与前一份审核的关系：主要诊断保持一致；本次新增 Lite 源模板的责任定位，并把原先概括的“预授权 runner”收紧为固定批次、可信批准来源和可核验的资源预留。原审核不回写，保留形成过程。依据：ev:research/audits/permissions-2026-10-26.md#L97-L150。

### 2.1 plan review 的处置

| id | 意见 | 裁定与修订位置 | evidence |
|---|---|---|---|
| PR01 | acceptEdits 会扩展部分 Bash 文件操作的自动许可，可能弱化 B1 | 采纳。B0 增加合成保护目录负例；B1 未通过就不切默认，采用 default+普通源码精确 Edit allow。路径字符串规则不被描述为完整隔离 | ev:update/plan_review.md#L24-L36；[acceptEdits 官方说明](https://code.claude.com/docs/en/permission-modes#auto-approve-file-edits-with-acceptedits-mode) |
| PR02 | B2 前保留 auto 与旧版本 ask 绕过有风险 | 采纳过渡期临时禁用，保留 B2 后恢复的目标。核实本机 2.1.247 及官方 2.1.257 修复；升级或版本号本身不代替回归与隔离 | ev:update/plan_review.md#L38-L49；ev:research/audits/permissions-2026-10-26/work/plan-review-r2/runtime_evidence.json#claude_version.stdout；[官方更新日志](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md#21257) |
| PR03 | 批准入口位置不清，mode 白名单可能被当作来源证明 | 采纳澄清。D10/D11 是来源与模式政策两层，原文未把信任边界说具体；§5.2 改为宿主独立人工命令，聊天/hook 不再签发新批准 | ev:update/plan_review.md#L51-L59 |
| PR04 | B3/B4 仅部分覆盖夜间迭代；Python 高频弹窗 B3 才消除 | 采纳能力边界与收益说明，不假定用户已接受范围。原始诉求也未自动授权新实验自行启动；“最主要弹窗”没有实测排序，仍标未核验 | ev:update/plan_review.md#L61-L67；ev:.claude/settings.json#L54-L55 |
| PR05 | Docker socket 须有显式排除和负例 | 采纳。在既有宿主管理入口隔离基础上，补 Docker/Podman 的宿主与 rootless socket、远程 endpoint 和相关环境配置 | ev:update/plan_review.md#L71-L71 |
| PR06 | 登记 permission-prompts none 作为无头备选 | 有条件采纳。官方要求至少 2.1.259；本机 help 未列出，不在当前版本启用。dontAsk 在本机 help 已列出，实际行为仍待验收 | ev:update/plan_review.md#L72-L72；ev:research/audits/permissions-2026-10-26/work/plan-review-r2/runtime_evidence.json#permission_prompts_option_advertised；ev:research/audits/permissions-2026-10-26/work/plan-review-r2/runtime_evidence.json#dontAsk_choice_advertised；[CLI 官方说明](https://code.claude.com/docs/en/cli-reference#cli-flags) |
| PR07 | B2/B3 已部分恢复 Ledger/Conductor 能力，应承认定位和工程量变化 | 采纳。§5.0 区分原 Lite 核心与 supervised-work 扩展，不再沿用“只维护一个小 hook”的成本描述 | ev:update/plan_review.md#L73-L73；ev:ra2a_lite_8xa100.md#L8-L28 |
| PR08 | 每批都按 RL3 批准；先 B0 再 B1 | 修正适用范围。纯读取/CPU 盘点仍是 RL0，无需为每条命令加审批；B1–B4 中涉及权限/协议等受保护修改按该批最高级别、具体文件范围批准。相同范围已有授权沿用 | ev:update/plan_review.md#L75-L83；ev:research/PROTOCOL.md#L139-L146；ev:AGENTS.md#L15-L16 |

## 3. B0：锁定修改基线与部署能力

**产物**：当前文件哈希、review 的逐项处置、实际生效权限与工具版本清单、最小复现记录。纯读取盘点与本轮方案修订不实施 B1–B4 的保护配置变更。

- 保留现有账本、runs、正式记忆与用户未提交改动；不 reset/restore，不全量重建工作区。
- 以当前可执行文件及 v2.3 已应用修复为修改基线；Lite §5 同步到这一基线，PATCH 记录版本事实与历史判断，不把旧判断改写成当时已核验。
- 记录 Claude/Codex 版本、项目/用户/管理层权限来源；先做离线规则检查，再在合成目录做 UI 与无头验收。不得因最新文档出现新字段就假定本机支持。
- 检查容器/沙箱后端的实际可用性。PATH 中存在程序只是发现，不算通过隔离验收；没有可用后端时，B2/B3 不启用宽解释器权限。
- 对弹窗采集添加工具名、命中规则、角色、会话/阶段、有效模式、结果与耗时；不采集凭据。Notification 作为补充，不作为全部请求的计数器。
- 在临时合成仓库中，对仿真的 ledger、charter、memory、.claude/.codex 等保护路径，分别验证文件工具和 sed -i、cp、mv、touch、重定向的结果；补包装器、复合命令、子 shell 与路径别名用例。不得在真实账本、章程、记忆、评测或 test 上试写/试读。
- 验证目标版本在 auto 下对普通、复合与子 shell 命令均执行 ask；权限测试只使用无训练/评测行为的合成程序。记录普通文件可正常修改的正例，避免“所有操作都拒绝”也算保护通过。
- 单独登记容器内 socket/endpoint 不可达的验收结果；宿主存在 Docker 命令或 socket 的元信息不等于 worker 已可达，也不等于隔离已通过。

本轮已重读版本/help，尚未启动新模型会话或执行上述 UI/权限用例。当前能力登记如下，不能当作行为验收通过：

| capability | 发现 | 本版处理 |
|---|---|---|
| Claude 版本 | 2.1.247 | 低于官方记载的 ask 修复版本；B1 按未隔离过渡策略起草，不自动升级 |
| acceptEdits、dontAsk | 本机 help 列为模式选项 | 文件保护与无头拒绝语义待合成用例验收 |
| permission-prompts none | 本机 help 未列；官方要求 2.1.259+ | 当前不使用；升级后的固定版本另做能力与拒绝语义验证 |
| auto 复合命令 ask | 官方 2.1.257 记载修复 | 当前版本不宣称具有修复；本机绕过行为未复现 |

依据：ev:research/audits/permissions-2026-10-26/work/plan-review-r2/runtime_evidence.json#claude_version.stdout；ev:research/audits/permissions-2026-10-26/work/plan-review-r2/runtime_evidence.json#runtime_permission_tests_run；ev:research/audits/permissions-2026-10-26/work/plan-review-r2/claude_help.txt#L1-L10；[官方更新日志](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md#21257)、[CLI 参数版本要求](https://code.claude.com/docs/en/cli-reference#cli-flags)。

已有证据确认当前 broad ask、默认模式和阶段停等规则存在；无需等一天采样才能准备 B1 diff，但发布 B1 必须通过下面的保护与有效模式检查。依据：ev:.claude/settings.json#L12-L59；ev:.agents/skills/ra-round/SKILL.md#L16-L24；ev:update/claude_review_auto_mode_2.md#L42-L57。

## 4. B1：白天减负与规则语义修正

### 4.1 .claude/settings.json 的具体改动

1. `defaultMode` 先保留 default，起草 acceptEdits 候选配置。只有 T01a 的普通编辑正例与保护路径负例均通过，才切到 acceptEdits；否则保留 default，按接入项目已登记的普通源码/配置/单元测试目录增加精确 Edit allow，不放行全仓库 Edit。
2. 保留现有受保护路径的 ask/deny；本批不移除 Python/Shell 整类 ask，不增加未经隔离的 `Bash(python3 *)`、`Bash(pytest *)`、`Bash(find *)`。
3. 对确认过的只读调用补充精确 allow；写操作、解释器、测试与包管理器不因为名称常用就视为只读。已有 py_compile 许可保留。
4. 通过 ra-init 登记实际源码、配置、单元测试与日志路径；仓库外只添加必需的目录访问。完整权限列表基于现有设置增量合并，不采用 review 的缩略样例。
5. 权限请求/通知 hook 先只记录、不自动返回 allow；它们不能替正式研究批准。
6. B2 验收前的未隔离会话临时设置 `disableAutoMode: disable`，并验证新会话、恢复会话与模式切换均实际生效；bypass 继续禁用。键不支持或有效配置被覆盖时不发布候选配置，不以提示词假装强制成功。本版不自动升级 CLI。
7. 文件操作负例若意外被自动放行，候选配置不发布；可添加部署版支持的 Bash 路径/命令检查作为补强，但须重新测试，不能宣称几个字符串模式覆盖任意间接写入。若保护无法满足，使用第 1 项回退，完整隔离仍交 B2。

### 4.2 同步规则与使用说明

- CLAUDE.md：写明 B1 的候选/回退模式、B2 前临时禁 auto、B2 与版本回归后恢复 auto、始终禁止 bypass。说明“切到 auto”的工具按钮会改变工作会话的模式，不能当作研究批准；新签署入口按 §5.2 实施。
- AGENTS.md/PROTOCOL：明确 RL0 不需要每次工具批准；草案代码只能在隔离副本中准备，默认行为保持基线；CPU 自检与 CPU 研究训练/评测区分，后者仍需研究授权。
- 暂保留 decision/commit/启动的现有工具门；B2 完成可信落盘后再合并重复操作，避免先删门、后补防护。
- 修正 Lite “固定三次弹窗”的承诺，改为列出人工决定点与可能的工具确认；修正 PATCH 的 ask/auto 与 Codex Python 描述。

**B1 完成标准**：通过验收的 acceptEdits 或 default+精确 Edit allow 均可作为减负交付；普通源码编辑不逐次弹窗，保护命令的自动许可不比基线宽，临时禁 auto/bypass 实际生效，未隔离解释器保持原边界。轮次 Python 的 ask 仍在，须到 B3 在隔离环境中移除；本批不承诺 CPU 分析零弹窗。

## 5. B2：隔离、批准与锁定先形成可信边界

### 5.0 定位与实施前设计决定

B2/B3 是 **supervised-work 扩展**：新增人工签发、可信归档/锁定和有限工作调度，确实恢复了部分 Ledger/Conductor 职责。原 Lite 交互模式保留，但扩展模式不再声称只需一个小 hook；须同步修改 Lite §0、安装/运维说明和 PROTOCOL 的角色责任。

动工前完成下面 §5.2 的批准入口决定、宿主/worker 挂载清单、socket/凭据排除清单、事件链与失败策略，形成可审阅部署设计。研究员对该批具体修改的授权须明确包含签署操作习惯与能力范围；不能将本次 plan review 当成已经作出这些决定。

### 5.1 隔离部署

首选无 GPU 容器；可用且经验证的原生沙箱可作为替代，但必须实现同一组边界。整个 agent 及其文件工具、Shell、子代理都运行在该边界内。

- 普通源码、配置、允许的单元自检和本轮 scratch 可写；正式评测与数据只读；真实 test、启动令牌、批准签发状态不暴露。
- AGENTS/CLAUDE、.claude/.agents/.codex、PROTOCOL、章程、rubric、模板、hook、正式记忆、既有账本、冻结产物与 .git 对 worker 只读。需要合法更改时由人工入口批准后交受信落盘器应用。
- 不暴露 GPU 设备、宿主进程/容器管理套接字、SSH agent、集群调度凭据等启动旁路；只提供模型调用所需的最小认证与已登记网络访问，不挂整个宿主认证目录。
- 明确不挂载或开放 /var/run/docker.sock、宿主 rootless Docker/Podman socket、containerd 管理入口及它们的远程 endpoint；清理或拒绝指向宿主控制面的 DOCKER_HOST、CONTAINER_HOST 与 context/认证配置。T03 同时检查挂载清单和容器内不可达负例，不能只检查一个固定 socket 路径。
- 禁止自动降级到未隔离执行；配置不支持、挂载不正确或必要目录不可访问时，在开始工作前退出并写明原因。
- 资源上限覆盖 CPU、内存、磁盘、墙钟和模型调用预算。具体值来自本次工作单，缺失的硬上限不由 agent 填成研究批准。

隔离控制影响范围，不能自动判断任意 Python 的科研含义。agent 仍须遵守禁止自行训练/评测和禁止使用 dev/test 调参等规则；普通 CPU 分析的许可不扩展为研究作业许可。依据：ev:AGENTS.md#L13-L15。

### 5.2 人工批准与自动化输入分开

**首版设计决定（待该批实施授权）**：有效的新批准只由研究员在宿主终端独立运行 `ra-approve` 签发。命令不运行模型，先展示冻结 manifest 的完整 digest、diff、实验与资源清单，再收取研究员亲自输入的批准原文；不接受 worker 队列、聊天镜像或自动化驱动代签。

| component | 所在位置与权限 | 责任 |
|---|---|---|
| ra-approve 与签发者状态 | 隔离外宿主的受保护安装/状态目录；worker 不可写、不可调用签发接口 | 展示已备妥内容、收取人工决定、原子生成凭据；不导入 worker 仓库代码、配置 hook 或任意插件 |
| worker hook / outbox | 容器内，按工作单可写 | 提交 draft 与事件；聊天里的批准只作提示/镜像，不签发权限 |
| 公开批准凭据 | 由宿主签发，worker 最多只读；私有 issuer 状态与密钥不挂载 | 绑定 project、对象完整 digest、明确动作、期限与撤销状态 |
| verifier / finalize | 宿主受信侧；实现代码与状态不可被 worker 改写 | 通过私有注册表或签名验证凭据来源，再核对内容和权限；只应用已授权对象 |

关键保证来自宿主与 worker 的权限隔离。TTY、uid、环境变量、mode 字符串都不能单独证明是人在签署；宿主入口不得向 worker 暴露通用签发 API 或自动同意开关。

统一记录包括 `approval_id`、`project_id`、`actor_type`、`approval_channel`、`origin`、`runtime`、`permission_mode`、`subject_digest`、`actions`、`issued_at`、`expires_at`、`revoked_at`、`receipt_digest`。宿主独立命令使用 `approval_channel: host_terminal`、独立 CLI runtime、显式 `permission_mode: null`，因为它没有模型权限模式；禁止伪填 default 来凑白名单。worker 的 observed_mode 与 RA_SESSION 只作来源不可信的诊断附件。

- Claude/Codex 工作会话的模式不签发权限，也不使已有效签署、内容未变的凭据因切模式而失效。旧机制中 default/acceptEdits/plan 与 auto 的区分只用于旧记录核验，不能升级为新机制的身份验证。
- 无头驱动输入、子代理输出、普通队列文件、镜像中的批准文字、手工 decision 状态均不能签发批准；有效来源先由宿主验证，不能靠请求自报 `approval_channel`。
- round、memory、retry、launch、audit 统一调用验证器。必填字段按通道 schema 判断；宿主合法的 null mode 不拒绝，未知通道、缺必要字段、无可信来源、过期、撤销、hash 不符均拒绝。
- 不合并历史多条批准集合扩大权限。一次 auto 下的无效尝试保留为无效事件，不能永久污染后续已纠正的轮次。
- 对话批准改为镜像的生效时点写入协议。旧账本不回写；已有明确授权的迁移核验并关联原记录，不补写原文或扩大范围；无法核验的历史来源标为未核验。

这意味着批准时需要一次独立的宿主签署操作，后续相同内容的机械存档复用该授权。研究员尚未在本次对话中接受这一操作习惯变化；本方案将其列为 B2 的明确设计决定，不先行启用。依据：ev:update/plan_review.md#L51-L59。

需要修正的当前实现依据：launch 只排除 mode=auto，并合并扫描到的批准集合；CR/retry 也没有相同的独立核验。ev:research/templates/launch.sh#L68-L84；ev:research/templates/launch.sh#L107-L113；ev:.agents/skills/ra-memory/SKILL.md#L11-L15。

### 5.3 草案、签署、锁定的内容绑定

工作流调整为：`A–P6 → 隔离副本中的实现草案与 CPU 自检 → 完整 brief/manifest → 人工讨论批准 → P7/P8 → L 锁定 → 人工启动或已授权批次执行`。前置实现只产出 draft，不产生研究批准或消耗实验资源。

manifest 使用完整 digest，覆盖源码/配置、ERC、脚本、实验与种子清单、资源上限、数据/评测版本和统计计划。批准凭据保存在冻结内容之外，避免“内容包含自身批准 hash”的循环。

受信落盘器只应用 manifest 指定的文件，验证内容一致后写 decision 并完成锁定；不执行 worker 传来的任意 git 命令、参数或仓库 hook。不使用 `git add -A research` 将其他并行任务或未审文件一并带入。

保留“批准早于锁定、锁定早于启动”的现有顺序。任何影响批准内容的后续修改都生成新 digest 并重新批准；P7/P8 仅登记与说明批准，不得改变已签署的实验内容。不可用“早上追认”回填这一顺序。依据：ev:research/PROTOCOL.md#L21-L24；ev:.agents/skills/ra-round/SKILL.md#L75-L98。

### 5.4 事件与角色输出

隔离后不能继续假定 worker 内的 hook 可直接写只读账本。hook 输出走受控事件收集通道，宿主收集器追加归档；普通事件通道不具备批准签发权。写入失败必须使对应阶段保持未完成，不能静默宣称已有证据。

保留角色输出白名单、原文 hash、attempt/阶段绑定。当前 K9 的旧通过记录不足以代替新运行时验收；本次对账另记录标记文件的实际存在性。验证角色字段后才由研究员启用白名单；重试文件名也须在新规则中有明确、有限的合法形式。依据：ev:research/hooks/ra_log.py#L15-L30；ev:research/hooks/ra_log.py#L64-L78；ev:research/hooks/ra_log.py#L109-L125；ev:research/audits/R00-2026-10-23.md#L51-L51。

**B2 完成标准**：worker 通过 Python/Shell/文件工具均不能改保护资产、伪造有效批准或自行锁定；合法人工批准可被各入口一致验证；受信落盘与角色归档完成端到端验收。

## 6. B3：交付夜间代码与 CPU 工作

### 6.1 权限配置与入口

- Claude：使用明确的无头入口和 dontAsk；继承 B2 隔离。为普通可写目录与已允许的 CPU 分析/单元自检添加许可，移除与它们冲突的 Python 整类 ask；将 Shell ask 从整个 rounds 缩到实际启动/资源承诺入口。
- permission-prompts none 仅登记为可选的升级后入口：官方要求 2.1.259+，本机 2.1.247 的 help 未提供，不在当前命令中加入。选定新的固定版本后先验证能力、模式与“需要确认即拒绝”的行为，再决定与 dontAsk 的搭配；不自动升级或静默换成别的模式。
- 显式 ask/deny 的保护项继续保留。夜间的保护文件变更或正式批准需求直接转待审；不使用 PreToolUse allow 盖过 ask，不换写法重试已拒绝的操作。
- Codex：白天保持 workspace-write/on-request；夜间明确 never 且保持沙箱。保留 forbidden。已有 env prompt 在首批不简单删除，夜间所需环境由受信启动层一次设置并继承；被拒的额外 env 请求照常进入待审。后续若移除整类 env prompt，须在隔离专用配置中单独验收，不能用一个 allow 规则假装覆盖 prompt。
- 启动前检查有效模式、工作目录、模型认证、依赖、网络、hook 与子代理事件链；不允许运行中跳出到新的交互式登录或权限宿主。字段和输出 schema 按 B0 实际版本固定。
- B2 隔离和目标版本回归通过后，才在隔离专用工作配置恢复 auto 选项；宿主签发命令仍是独立人工入口，不能被 auto reviewer 或分类器替代。

### 6.2 流程与状态

ra-round 增加 `interaction_mode: interactive|unattended`，这只是工作交互方式，不是研究批准状态。用户显式发起的 unattended 工作包可以执行 A–P6、草案实现与软件自检；没有研究批准时不进入 P7/L/X。

工作单包含任务范围、输入版本、允许写入路径、CPU/墙钟/模型预算、最多机械重试次数和完成判据。可继续的任务必须在此工作单内，不能为填满夜间时间自行扩展研究目标。

新增状态：

| state | 含义与后续 |
|---|---|
| working | 执行已授权工作 |
| retrying_mechanical | 在限定次数内修正格式、路径、临时工具错误；不改变科学内容 |
| pending_human | 单个分支缺批准/输入/权限，记录原因、证据、依赖和请求范围 |
| review_ready | 材料已完成，等待研究员讨论签署；不是失败 |
| failed_safe | 阶段证据、隔离或一致性无法恢复；依赖该阶段的后续工作停止 |

只阻断依赖相应批准或失败阶段的分支；完整性不足时仍不得发布正式决策。无独立任务可做就正常结束，并写早报，不保留悬置的 Yes 或 AskUserQuestion。

### 6.3 上下文恢复与故障

每阶段保存冻结输入、产物 hash、角色/attempt、运行时与下一步。阶段间恢复先核验检查点；P1 等独立评审中途压缩或证据链失效时，使用同一冻结输入重新开受影响的角色，保留旧尝试，不 resume，不改写原文。不能简单删掉 compact 检查。

阶段不完整只能做预定的机械恢复，不能少一个角色也发布结论；新策略/新断言或研究含义变化返回相应核验与人工边界。旧的“任何失败都询问人”改为这套状态规则。

**B3 完成标准**：代码编辑、配置解析、CPU 自检、分析与评分链在无人输入条件下完成；一个受保护操作被拒不会使所有独立任务停摆；最终产物为完成材料或明确待审事项。

## 7. B4：可选的固定实验批次委托执行

这一批是新增执行能力，必须作为具体的协议/章程变更授权；不把人工启动过一个守护进程等同于已批准它未来执行任何实验。第一版不接受“未来若干轮、任意 hparam/schedule/data_mix”的宽泛信封。

### 7.1 允许执行的对象

研究员在非 auto 人工入口批准一张**固定清单**：完整内容 digest、exp_id、种子、冻结代码/镜像、配置、资源预留、期限、启动次数、失败策略、预注册停止条件。可包含多个事先设计好的实验与依赖，但不能由 agent 夜间加入新代码、新实验或重跑。

批次凭据明确写 `authority: human_batch_preapproval` 和原始 approval_id；不要写成“研究员夜间逐轮亲自批准”。越界候选、CR、冠军更新与新轮次计划只起草待审。日后如要参数搜索，必须先将固定执行代码、可变参数、取值域、选择规则和 dev 使用规则形式化并另行授权。

### 7.2 执行器要求

- 执行器与 agent 权限分离；程序、状态和批准凭据不在 worker 可写区。请求仅引用已批准对象，不能携带任意 shell 命令、脚本路径或重新解释的 change 标签。
- 启动前原子检查并预留 `exp_id/attempt`、在途与已用预算、并发设备资源；再通过可执行的墙钟/资源限制控制实际消耗。只查看 nvidia-smi 与日志不是原子的分配机制。
- 无效、撤销、过期、重复请求不启动；重启后恢复占用和已启动记录，不重新发放预算或重复启动。
- 截止时间、停止文件与已运行任务的处置规则在批准前写清。自动终止只执行人工已授权且 ERC 预注册的可判定条件，禁止依据“结果好”提前停；没有终止授权时只能阻止新启动并报告。
- 使用只读的冻结执行副本；原工作区的新 diff 不影响正在执行的批次。角色收集、实验开始/结束与资源占用均留可核验记录。
- 模式 A 人工终端启动继续保留。新增委托模式必须与 AGENTS/PROTOCOL/charter/ra-launch/launch.sh 一起统一描述；不自动把当前 charter 的 A 改成 B 或新增模式。

**B4 完成标准**：模拟执行器覆盖授权、预算竞争、重启、重复请求、撤销、到期、停止与日志配对，再由研究员安排真实资源验收。真实训练/GPU 任务不属于本轮方案工作的自动执行范围。

## 8. 文件级执行清单

新增工具名称为实现接口约定，当前均未创建或启用。

| batch | files | 具体修改/新增责任 |
|---|---|---|
| B0/B1 | ra2a_lite_8xa100.md、PATCH-v2.3.md | 同步当前修复，修正文档语义与弹窗承诺；保留历史版本依据，增加 v2.4 处置记录 |
| B1/B3 | .claude/settings.json、CLAUDE.md | B1 验收后才切 acceptEdits，未过则 default+精确 Edit allow；未隔离过渡期禁 auto，B2/版本回归后恢复；禁止 bypass，补权限事件 |
| B1/B3 | .codex/config.toml、.codex/rules/ra.rules、.codex/hooks.json | 区分交互与无人值守入口；夜间 never+沙箱，保留 forbidden；补事件与来源适配，谨慎处理 env prompt |
| B1/B2/B3 | AGENTS.md、research/PROTOCOL.md | 草案实现范围、人工来源、授权复用、状态/恢复、审批顺序；GPU/评测/test 与账本保护不放宽 |
| B2 | research/hooks/ra_log.py | 人工/自动化来源区分、事件传输与归档错误反馈；角色输出白名单、阶段/attempt 绑定；不以环境标签签发批准 |
| B2 | 新增 research/runtime/approval.py、finalize.py、collect.py | 实现宿主独立 ra-approve、按通道 schema 统一验真；按批准 digest 落盘锁定；收集角色原文与追加事件。受信程序与私有状态不向 worker 开放签发权限 |
| B2/B3 | 新增 research/runtime/agent-container/、work.py | 隔离配置、启动前检查、有限预算、无头入口与检查点调度；无 GPU、无权限升级、无自动降级 |
| B2/B3 | .agents/skills/ra-init、ra-round、ra-memory、ra-audit、ra-status | 接入路径与能力登记；统一批准验证；unattended 状态；恢复与早报；补验收项 |
| B2/B3 | .claude/agents/ra-*.md、.codex/agents/ra-*.toml | 与相应工作模式一致的权限与输出责任；保持角色职责与独立性，不给评委新增任意代码执行能力 |
| B2/B3 | research/templates/meta.yaml、brief.md、decision.md、erc.yaml、launch.sh | 工作模式、来源与 digest、草案/正式状态、有限 attempt、统一批准检查；保留令牌守卫、幂等与冻结检查 |
| B4 | 新增 research/runtime/batch.py；更新 ra-launch、launch.sh、PROTOCOL、charter 的运行方式 | 独立的固定批次授权与执行；真实预算、范围和资源由研究员填写，不生成新的科研目标 |
| 各批 | 新增 research/runtime/checks/；更新 Lite §5、§7、§9 与安装说明 | 最小有意义的离线/合成回归、文档与文件一致性检查、可复现的部署验收记录 |

不修改 rubric 的评分公式、评测代码/数据/指标、正式记忆结论、现有账本和 runs；不改变模型选型。对 rubric 的新 veto 或分歧阈值不纳入此次改造。

## 9. 验收清单与发布顺序

| id | 必须验证的行为 | scope |
|---|---|---|
| T01a | default 与 acceptEdits 下普通源码编辑正例可用；对仿真 ledger/charter/memory/.claude/.codex 的 sed -i、cp、mv、touch、重定向及包装/复合/路径别名负例被拒或进入人工门 | B0/B1，只在合成目录；未通过不切默认 |
| T01b | B1 的临时禁 auto/bypass 在新/恢复会话、模式切换和相关配置覆盖下有效；目标固定版本的 auto 在普通、复合与子 shell 命令中均执行 ask | B0/B1/B2，记录版本与实际有效设置；不以版本号代替验收 |
| T01c | dontAsk 对 ask 立即拒绝；Codex never 不悬置输入；permission-prompts none 仅在本机明确支持且行为验收后可用 | B3，不能因未知参数或配置失效而静默降级 |
| T02 | 父会话与至少一个带 CPU 脚本的角色走完工作链，无权限输入框；只读评委权限不扩大 | B3，合成任务 |
| T03 | 文件工具与解释器都不能改保护资产；worker 不可访问宿主/rootless Docker、Podman、containerd socket 与远程管理 endpoint；隔离不暴露 GPU；缺后端拒绝启动 | B2，检查部署清单及容器内负例，不读真实 test、不占 GPU |
| T04 | 自动化输入、伪造环境/来源标签、聊天镜像、未知通道、缺必要字段、过期/撤销/digest 不符均不能形成有效批准；宿主人工凭据的显式 null mode 可按其 schema 验证 | B2，自动负例在临时库，真实有效批准正例由研究员在宿主命令亲自输入 |
| T05 | round、CR、retry、launch、audit 统一接受/拒绝相同凭据；纠正后的有效批准不被历史无效尝试永久阻断 | B2，不改真实旧账本 |
| T06 | 批准后的相同内容仅机械存档一次；内容变化须重新批准；只锁定清单内文件；__run 守卫保留 | B2，临时 git 仓库与模拟启动器 |
| T07 | 角色错误路径、冒名输出、缺身份、重复与重试 attempt 正确处置，原文 hash 可核对 | B2/B3，合成事件，不伪造真实子代理凭据 |
| T08 | 机械故障有限恢复；阶段压缩后按冻结输入恢复/重做；缺角色不发布正式结论；待审分支不阻塞独立任务 | B3 |
| T09 | 无人值守运行至少一个完整工作包，结束时有早报、待审清单与拒绝记录；无悬置 Yes、登录或 AskUserQuestion | B3，不以“没有弹窗但关键工作全被拒”判通过 |
| T10 | 固定批次的并发预算预留、幂等、重启、撤销、到期和预注册停止条件生效；未批准对象无法启动 | B4，先模拟资源验收 |
| T11 | 修改后的实际文件与 Lite 对应代码块/版本说明一致，v2.3 回归仍通过，历史账本与结果未改写 | 每批 |

发布顺序为 B0 → B1 → B2 → B3；B4 单独发布。每批先完成可审阅 diff、相应离线检查和部署验收记录，再推进下一批；隔离失败时不放开解释器，批准来源未验收时不启用自动锁定或资源执行。

授权与发布门：B0 纯读取、CPU 盘点及方案文档工作按 RL0 继续，不新增逐命令审批；B1–B4 中修改权限/协议/章程等保护文件的批次，按该批最高风险等级和具体文件范围取得明确授权，已有相同具体范围的授权沿用。B1 发布前须 T01a/T01b；B2 开工前须批准入口与部署设计明确；B3 须 B2 的 T03–T07 通过；B4 另立资源执行协议修订。

收益与范围门：B1 只减少普通编辑确认，轮次 Python ask 要到 B3 才移除；B3 不承诺夜间启动新实验，B4 不承诺自由生成并执行新轮次。实施批次须明列这两项范围及宿主签署习惯，不以研究员读过 review 或沉默推定已接受。已授权工作提前完成时正常结束，不为填满夜间时间生成新任务。

正常回退使用已保留的配置/部署版本重新部署，停止新工作包或撤销未来批次请求；不得使用禁用的 git reset/restore、改写历史账本或擅自终止研究作业。

## 10. 本轮实际完成情况

本轮在两份 review 对账基础上读取 plan review，并修订为 v2.4-plan-2；只采集版本/help、留存 plan-1 与核验证据指针。没有应用控制配置、升级 CLI、启动新模型会话或执行 UI/权限攻击探测，没有创建/启动 runner、训练、评测或 GPU 作业。

对账依据与验证结果位于 `research/audits/permissions-2026-10-26/work/reconciliation_evidence.json`、`reconciliation_verification.json`。实际改动范围为本方案、对账脚本/输出及 STATUS 的审核索引；review 原文与前一份审核保持原样。

plan-2 的原版留存、当前版本/help、指针与基线检查另存于 `research/audits/permissions-2026-10-26/work/plan-review-r2/`，不覆盖 plan-1 的对账结果。对应 review 与全部基线保护文件保持原样。

只读发现 docker 可执行文件位于 PATH，bwrap/podman 未发现；尚未测试容器服务访问或隔离能力，因此 B2 后端部署仍是实施验收事项，不能由“有 docker 命令”推定已具备隔离。依据：ev:research/audits/permissions-2026-10-26/work/reconciliation_evidence.json#deployment_programs_in_path；ev:research/audits/permissions-2026-10-26/work/reconciliation_evidence.json#deployment_capabilities_tested。

## 11. 方案修订记录

| version | 修改 | 留存/依据 |
|---|---|---|
| v2.4-plan-1 | 两份初始 review 的 22 项对账与 B0–B4 方案 | 原版留存于 research/audits/permissions-2026-10-26/work/plan-review-r2/plan-1.original.md |
| v2.4-plan-2 | 增加 acceptEdits 文件操作验收与回退、未隔离过渡期禁 auto、明确宿主人工签署和按通道验证、socket/版本能力测试、工程定位和收益范围 | update/plan_review.md；本文件 §2.1 的 PR01–PR08；只修订方案，未应用配置 |
| v2.4（应用）| 2026-10-26 研究员指令"先完成 B0、B1"：B0 基线锁定与 B1 白天减负/规则语义修正实施为包版本 v2.4（含版本机制：CHANGELOG/PATCH-v2.4/tag）；B2–B4 未实施，门条件见 §9 | PATCH-v2.4.md；CHANGELOG.md；git tag v2.4 |
