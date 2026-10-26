---
version: v2.4-plan-1
date: 2026-10-26
status: reconciled_proposal_not_applied
charter_trace: []
scope_note: 治理与开发工作流改造，不提出研究实验，不修改研究目标
reviews:
  - update/claude_review_auto_mode.md
  - update/claude_review_auto_mode_2.md
prior_audit: research/audits/permissions-2026-10-26.md
---
# 两份 review 对账与最终修改执行方案

## 1. 最终取舍

建议先交付“日常开发少弹窗、夜间代码与 CPU 工作不等人”，随后增加“人工预批固定实验批次，由隔离外的受信执行器运行”。不把预算/轮数上限直接解释成对未来任意代码和实验的授权。

日常 Claude 默认改为 `acceptEdits`，保留已经放行的 auto 选项，继续禁止 bypass。正式批准从可信人工入口取得，并保持非 auto；纯读取审计、讨论与普通开发没有全程非 auto 的要求。夜间 Claude 使用显式 `dontAsk` 无头入口；Codex 使用保留沙箱的 `never` 无人值守入口。工作模式与研究批准类型分开记录。

这修正两份 review 的“恢复全局禁 auto”建议：切换默认值可减少普通编辑弹窗，禁止 auto 不是必要条件；当前仓库已登记允许 auto，正式批准的约束可以单独保留。依据：ev:CLAUDE.md#L6-L7；ev:PATCH-v2.3.md#L38-L40；ev:.claude/settings.json#L12-L19；ev:update/claude_review_auto_mode_2.md#L104-L107。

`dontAsk` 是把需要确认的调用拒绝，不能让缺失授权的工作自动通过；agent 应把事项列为待审并继续独立工作。依据：[Claude dontAsk](https://code.claude.com/docs/en/permission-modes#allow-only-pre-approved-tools-with-dontask-mode)。Codex 的 `never`、`workspace-write` 与 `auto_review` 也是不同设置，自动工具审查不等于研究员批准。依据：[Codex 沙箱与审批](https://learn.chatgpt.com/docs/sandboxing#configure-defaults)。

本方案分 B0–B4 实施。B0–B3 作为核心改造；B4 是新增资源执行授权类型，单独交付。进一步的“夜间自行设计新实验并连续启动新轮次”暂不纳入此版，须另行修订研究决策授权协议。

## 2. 对账结果

以下 R1、R2 分别指第一、第二份 review。“采纳”表示采纳建议或静态结论，不表示已经完成运行时验收。

| id | review 观点 | 对账裁定与最终处理 | evidence |
|---|---|---|---|
| D01 | 原版就存在普通代码编辑弹窗，PATCH 又增加轮次 Python 弹窗 | 采纳。问题同时来自 Lite 默认配置与补丁的权限收紧 | ev:update/claude_review_auto_mode_2.md#L42-L53；ev:ra2a_lite_8xa100.md#L1158-L1179；ev:.claude/settings.json#L53-L55 |
| D02 | P1/P3/P4 等子代理阶段会密集弹窗 | 有条件采纳。带 Bash 的角色复用相关权限会放大影响；具体弹窗次数、哪个阶段最多未核验，不能把所有角色都视为会执行 Python | ev:update/claude_review_auto_mode_2.md#L55-L55；ev:.claude/agents/ra-analyst.md#L4-L16；ev:.claude/agents/ra-judge.md#L4-L7；ev:.claude/agents/ra-designer.md#L4-L12 |
| D03 | 显式 ask 不会因为切 auto 就消失 | 采纳当前官方语义；修正 PATCH。补充：dontAsk 下是拒绝，不是“所有模式都弹窗”；本机 UI 仍须验收 | ev:update/claude_review_auto_mode.md#L103-L114；ev:PATCH-v2.3.md#L45-L64；[Claude 规则优先级](https://code.claude.com/docs/en/permissions#manage-permissions) |
| D04 | v2.1.283 起默认 auto 导致当前问题 | 采纳 R2 更正。项目明确设置 default，不能用平台默认值直接解释实际会话；本机已记录版本还早于该版本 | ev:update/claude_review_auto_mode_2.md#L91-L94；ev:.claude/settings.json#L12-L12；ev:research/audits/permissions-2026-10-26/work/inventory.json#claude.stdout |
| D05 | Codex 的 Python 也设为 prompt；allow 全是只读操作 | 更正。当前 Codex 没有通用 Python prompt；Claude 还允许轮次文件编辑、git add、py_compile，不能概括成“只有只读” | ev:update/claude_review_auto_mode.md#L116-L124；ev:.claude/settings.json#L15-L39；ev:research/audits/permissions-2026-10-26/work/policy_checks.json#0.policy_result |
| D06 | 改 acceptEdits 并恢复 disableAutoMode | 部分采纳：默认 acceptEdits；不恢复全局禁 auto。工作可 auto，批准独立控制；acceptEdits 不会取消显式 ask | ev:update/claude_review_auto_mode.md#L179-L214；ev:CLAUDE.md#L7-L7；[Claude 权限模式](https://code.claude.com/docs/en/permission-modes#available-modes) |
| D07 | 没有 GPU 的隔离环境后再放宽 Python | 采纳顺序。隔离还须覆盖全部工具、控制文件/账本、宿主套接字和远程调度凭据；仅 nvidia-smi 失败不能证明设备不可访问 | ev:update/claude_review_auto_mode.md#L164-L173；ev:update/claude_review_auto_mode.md#L318-L323；ev:ra2a_lite_8xa100.md#L1647-L1676 |
| D08 | 直接采用 R1 的 settings 样例 | 不整体采用。样例把正式记忆写成 research/knowledge.md 等错误路径，遗漏现有模板/.codex 等保护项；只能基于当前配置做增量修改 | ev:update/claude_review_auto_mode.md#L193-L204；ev:.claude/settings.json#L42-L52；ev:research/PROTOCOL.md#L164-L169 |
| D09 | demo-revised 已满足审批把关；F1/F2/F6 已修 | 更正为“有所加强，尚未闭环”。本次标记文件不存在，白名单未激活；CR/retry 与缺失 mode 检查仍有缺口，同用户脚本写入风险仍须隔离 | ev:update/claude_review_auto_mode_2.md#L65-L67；ev:research/hooks/ra_log.py#L15-L18；ev:research/audits/permissions-2026-10-26/work/reconciliation_evidence.json#whitelist_marker_exists；ev:research/templates/launch.sh#L69-L84；ev:research/templates/launch.sh#L107-L113；ev:.agents/skills/ra-memory/SKILL.md#L11-L15 |
| D10 | 非 auto 白名单只接受 default/acceptEdits | 修正。保留现有允许从 plan 输入批准的用法；Claude 人工入口允许 default/acceptEdits/plan，排除 auto/dontAsk/bypass 和未知模式。还必须核验人工来源 | ev:update/claude_review_auto_mode.md#L212-L214；ev:.agents/skills/ra-round/SKILL.md#L23-L23；ev:research/templates/launch.sh#L76-L76 |
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

## 3. B0：锁定修改基线与部署能力

**产物**：当前文件哈希、两份 review 的逐项处置、实际生效权限与工具版本清单、最小复现记录。

- 保留现有账本、runs、正式记忆与用户未提交改动；不 reset/restore，不全量重建工作区。
- 以当前可执行文件及 v2.3 已应用修复为修改基线；Lite §5 同步到这一基线，PATCH 记录版本事实与历史判断，不把旧判断改写成当时已核验。
- 记录 Claude/Codex 版本、项目/用户/管理层权限来源；先做离线规则检查，再在合成目录做 UI 与无头验收。不得因最新文档出现新字段就假定本机支持。
- 检查容器/沙箱后端的实际可用性。PATH 中存在程序只是发现，不算通过隔离验收；没有可用后端时，B2/B3 不启用宽解释器权限。
- 对弹窗采集添加工具名、命中规则、角色、会话/阶段、有效模式、结果与耗时；不采集凭据。Notification 作为补充，不作为全部请求的计数器。

已有证据确认当前 broad ask、默认模式和阶段停等规则存在；无需等一天采样才能起草或实施 B1。依据：ev:.claude/settings.json#L12-L59；ev:.agents/skills/ra-round/SKILL.md#L16-L24；ev:update/claude_review_auto_mode_2.md#L42-L57。

## 4. B1：白天减负与规则语义修正

### 4.1 .claude/settings.json 的具体改动

1. `permissions.defaultMode`：`default` → `acceptEdits`；`disableBypassPermissionsMode` 保持 disable；不新增 disableAutoMode。
2. 保留现有受保护路径的 ask/deny；本批不移除 Python/Shell 整类 ask，不增加未经隔离的 `Bash(python3 *)`、`Bash(pytest *)`、`Bash(find *)`。
3. 对确认过的只读调用补充精确 allow；写操作、解释器、测试与包管理器不因为名称常用就视为只读。已有 py_compile 许可保留。
4. 通过 ra-init 登记实际源码、配置、单元测试与日志路径；仓库外只添加必需的目录访问。完整权限列表基于现有设置增量合并，不采用 review 的缩略样例。
5. 权限请求/通知 hook 先只记录、不自动返回 allow；它们不能替正式研究批准。

### 4.2 同步规则与使用说明

- CLAUDE.md：写明日常 acceptEdits、可选择 auto、禁止 bypass；批准时进入受信非 auto 人工入口；auto 的普通输入可保留。
- AGENTS.md/PROTOCOL：明确 RL0 不需要每次工具批准；草案代码只能在隔离副本中准备，默认行为保持基线；CPU 自检与 CPU 研究训练/评测区分，后者仍需研究授权。
- 暂保留 decision/commit/启动的现有工具门；B2 完成可信落盘后再合并重复操作，避免先删门、后补防护。
- 修正 Lite “固定三次弹窗”的承诺，改为列出人工决定点与可能的工具确认；修正 PATCH 的 ask/auto 与 Codex Python 描述。

**B1 完成标准**：新会话普通源码编辑不逐次弹窗；控制文件仍受保护；Python 等解释器尚未隔离时保持原边界。B1 只解决日常编辑摩擦，不宣称已经支持完整夜间工作。

## 5. B2：隔离、批准与锁定先形成可信边界

### 5.1 隔离部署

首选无 GPU 容器；可用且经验证的原生沙箱可作为替代，但必须实现同一组边界。整个 agent 及其文件工具、Shell、子代理都运行在该边界内。

- 普通源码、配置、允许的单元自检和本轮 scratch 可写；正式评测与数据只读；真实 test、启动令牌、批准签发状态不暴露。
- AGENTS/CLAUDE、.claude/.agents/.codex、PROTOCOL、章程、rubric、模板、hook、正式记忆、既有账本、冻结产物与 .git 对 worker 只读。需要合法更改时由人工入口批准后交受信落盘器应用。
- 不暴露 GPU 设备、宿主进程/容器管理套接字、SSH agent、集群调度凭据等启动旁路；只提供模型调用所需的最小认证与已登记网络访问，不挂整个宿主认证目录。
- 禁止自动降级到未隔离执行；配置不支持、挂载不正确或必要目录不可访问时，在开始工作前退出并写明原因。
- 资源上限覆盖 CPU、内存、磁盘、墙钟和模型调用预算。具体值来自本次工作单，缺失的硬上限不由 agent 填成研究批准。

隔离控制影响范围，不能自动判断任意 Python 的科研含义。agent 仍须遵守禁止自行训练/评测和禁止使用 dev/test 调参等规则；普通 CPU 分析的许可不扩展为研究作业许可。依据：ev:AGENTS.md#L13-L15。

### 5.2 人工批准与自动化输入分开

新增一个由研究员启动、worker 无法写入其状态的人工批准入口；它展示具体变更包并保存批准原文、来源、范围和完整 digest。无需新建通用平台，先实现本地单项目入口与验证器。

建议统一记录：`approval_id`、`actor_type`、`origin`、`runtime`、`permission_mode`、`subject_digest`、`actions`、`issued_at`、`expires_at`、`revoked_at`、`receipt_digest`。issuer 状态或签名材料位于隔离外，worker 不能调用其签发功能。`RA_SESSION` 只作追踪标签。

- Claude：人工入口接受已规范化的 default/acceptEdits/plan；拒绝 auto、dontAsk、bypass、缺失或未知模式；原文仍由研究员亲自输入。
- Codex：使用平台适配的人工来源凭据，不拿 Claude 的 permission_mode 或 Codex 的 auto_review 冒充人类身份；来源能力未验收则不签发有效凭据。
- 无头驱动输入、子代理输出、普通队列文件、手工写出的 decision 状态均不能签发批准。自动化输入可以记账，但标明 automated/unverified。
- 统一验证器供 round、memory、retry、launch、audit 调用；缺字段、无可信来源、过期、撤销、hash 不符均拒绝。
- 不再合并历史多条批准的实验集合来扩大权限；依据当前有效、明确引用的批准记录执行。一次 auto 下的无效批准尝试保留为无效事件，不能永久污染后续已纠正的工作轮次。

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
- 显式 ask/deny 的保护项继续保留。夜间的保护文件变更或正式批准需求直接转待审；不使用 PreToolUse allow 盖过 ask，不换写法重试已拒绝的操作。
- Codex：白天保持 workspace-write/on-request；夜间明确 never 且保持沙箱。保留 forbidden。已有 env prompt 在首批不简单删除，夜间所需环境由受信启动层一次设置并继承；被拒的额外 env 请求照常进入待审。后续若移除整类 env prompt，须在隔离专用配置中单独验收，不能用一个 allow 规则假装覆盖 prompt。
- 启动前检查有效模式、工作目录、模型认证、依赖、网络、hook 与子代理事件链；不允许运行中跳出到新的交互式登录或权限宿主。字段和输出 schema 按 B0 实际版本固定。

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
| B1/B3 | .claude/settings.json、CLAUDE.md | 默认 acceptEdits、保留 auto、禁止 bypass；先保留保护门，B2 通过后缩小工作类 ask；补权限事件 |
| B1/B3 | .codex/config.toml、.codex/rules/ra.rules、.codex/hooks.json | 区分交互与无人值守入口；夜间 never+沙箱，保留 forbidden；补事件与来源适配，谨慎处理 env prompt |
| B1/B2/B3 | AGENTS.md、research/PROTOCOL.md | 草案实现范围、人工来源、授权复用、状态/恢复、审批顺序；GPU/评测/test 与账本保护不放宽 |
| B2 | research/hooks/ra_log.py | 人工/自动化来源区分、事件传输与归档错误反馈；角色输出白名单、阶段/attempt 绑定；不以环境标签签发批准 |
| B2 | 新增 research/runtime/approval.py、finalize.py、collect.py | 统一验证凭据；按批准 digest 落盘锁定；收集角色原文与追加事件。部署时受信部分位于 worker 写权限之外 |
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
| T01 | default/acceptEdits/auto 下的正常编辑与显式 ask 行为符合部署版；dontAsk 对 ask 立即拒绝；Codex never 不悬置输入 | B1/B3，合成目录与允许的普通操作 |
| T02 | 父会话与至少一个带 CPU 脚本的角色走完工作链，无权限输入框；只读评委权限不扩大 | B3，合成任务 |
| T03 | 文件工具与解释器都不能改保护资产；隔离不暴露 GPU/宿主执行旁路；缺后端拒绝启动 | B2，仅合成保护文件与部署配置核验，不读取真实 test、不占 GPU |
| T04 | 自动化输入、伪造环境标签、缺 mode/未知来源/过期/撤销/digest 不符均不能形成有效批准；合法人工批准可用 | B2，自动负例在临时库，真实有效批准正例由研究员亲自输入 |
| T05 | round、CR、retry、launch、audit 统一接受/拒绝相同凭据；纠正后的有效批准不被历史无效尝试永久阻断 | B2，不改真实旧账本 |
| T06 | 批准后的相同内容仅机械存档一次；内容变化须重新批准；只锁定清单内文件；__run 守卫保留 | B2，临时 git 仓库与模拟启动器 |
| T07 | 角色错误路径、冒名输出、缺身份、重复与重试 attempt 正确处置，原文 hash 可核对 | B2/B3，合成事件，不伪造真实子代理凭据 |
| T08 | 机械故障有限恢复；阶段压缩后按冻结输入恢复/重做；缺角色不发布正式结论；待审分支不阻塞独立任务 | B3 |
| T09 | 无人值守运行至少一个完整工作包，结束时有早报、待审清单与拒绝记录；无悬置 Yes、登录或 AskUserQuestion | B3，不以“没有弹窗但关键工作全被拒”判通过 |
| T10 | 固定批次的并发预算预留、幂等、重启、撤销、到期和预注册停止条件生效；未批准对象无法启动 | B4，先模拟资源验收 |
| T11 | 修改后的实际文件与 Lite 对应代码块/版本说明一致，v2.3 回归仍通过，历史账本与结果未改写 | 每批 |

发布顺序为 B0 → B1 → B2 → B3；B4 单独发布。每批先完成可审阅 diff、相应离线检查和部署验收记录，再推进下一批；隔离失败时不放开解释器，批准来源未验收时不启用自动锁定或资源执行。

正常回退使用已保留的配置/部署版本重新部署，停止新工作包或撤销未来批次请求；不得使用禁用的 git reset/restore、改写历史账本或擅自终止研究作业。

## 10. 本轮实际完成情况

本轮完成两份 review 的读取、源码对账和最终执行方案落盘；只运行只读收集与证据指针检查。没有应用本方案对控制文件、技能、协议、模板、章程或权限的修改，没有创建/启动 runner、训练、评测或 GPU 作业。

对账依据与验证结果位于 `research/audits/permissions-2026-10-26/work/reconciliation_evidence.json`、`reconciliation_verification.json`。实际改动范围为本方案、对账脚本/输出及 STATUS 的审核索引；review 原文与前一份审核保持原样。

只读发现 docker 可执行文件位于 PATH，bwrap/podman 未发现；尚未测试容器服务访问或隔离能力，因此 B2 后端部署仍是实施验收事项，不能由“有 docker 命令”推定已具备隔离。依据：ev:research/audits/permissions-2026-10-26/work/reconciliation_evidence.json#deployment_programs_in_path；ev:research/audits/permissions-2026-10-26/work/reconciliation_evidence.json#deployment_capabilities_tested。
