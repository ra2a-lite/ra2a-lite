*Thinking...*

> I need to audit why demo-revised keeps triggering constant permission prompts, so I'm looking at Claude Code's permission system—allow/ask/deny rules and modes like default, acceptEdits, plan, and bypassPermissions. The core issue seems to be that settings.json puts too many protected paths and even research script commands into "ask" rather than "allow," leaving only narrow read-only commands whitelisted.
> 
> I'm also weighing how "ask" rules interact with modes—whether they override acceptEdits or get handled differently in auto mode—and the fact that the archived version disables auto/bypassPermissions per CLAUDE.md, forcing approval checks to fail unless the user manually switches modes. I should probably verify how ask rules behave specifically in auto mode before finalizing my fix.
> 
> The core design problem is that training launches are restricted to the researcher's terminal by design, so true overnight autonomy is impossible without a separate mechanism—like a pre-authorized "envelope" of budget and scope that a deterministic launcher daemon (not the agent's shell) can check against, letting the agent operate within pre-approved bounds while the human reviews everything in the morning. I also need to account for the many existing ask-gated actions (decision logs, git commits, edits to research files, round writes, CPU-heavy scripts) that would otherwise interrupt an unattended run.
> 
> I'm now mapping out how Claude Code's permission system actually behaves with compound commands—pipes, redirects, subcommands all need individual allow-listing or they trigger prompts—plus how subagents inherit permissions and file reads outside the project tree get flagged. This pushes me toward a three-tier permission model: hard denies for destructive or sensitive operations, a free sandbox tier for routine code edits, and something in between for riskier-but-reversible actions.
> 
> Given the host lacks bwrap for Claude Code's built-in sandboxing, I'm thinking the real fix is shifting enforcement from per-command prompts to environment isolation entirely—running everything inside a container that has no GPU access and no test files mounted, so broad command permissions become safe by construction rather than needing granular allow rules.
> 
> For human gates, I'd narrow them to truly consequential decisions—approvals, RL3 changes, memory CRs—and make them non-blocking: the agent queues the request and keeps working or wraps up with a morning report rather than freezing. Using dontAsk mode overnight is the elegant piece here, since anything outside the pre-approved list gets auto-denied and logged instead of the agent hanging indefinitely waiting on a human response.
> 
> I should check whether dontAsk is an actual permission mode in Claude Code before relying on it. The overnight launch pattern I'm picturing is a standing approval envelope—human-set budget, allowed change classes, experiment cap, and deadline—recorded in the ledger before they sleep, with a separate launcher daemon running outside the agent's sandbox that watches the queue, verifies the lock commit and budget against the envelope, and only then launches GPU jobs, since the agent itself should never have direct GPU access.
> 
> I'm now thinking the daemon could also auto-trigger the next round's agent session once training completes, but I need to mark those as "envelope-approved" rather than human-approved per round, and I still need hard stop conditions: budget exhaustion, aborts, audit failures, or repeated failures should force a halt rather than let the daemon keep going. Champion updates shouldn't apply overnight—those stay queued for morning review.
> 
> I'm also reconsidering whether the broader "auto mode" is even necessary anymore—since day use can rely on acceptEdits with a broad allow list and night use on dontAsk, it might be cleaner to revert auto to disabled and restore the original hard gate, since enabling auto didn't actually solve the prompting problem and just weakened security.
> 
> The user's point is that even outside audit mode, routine edits still required manual "yes" clicks because the approval check explicitly rejects permission_mode=auto, so running in auto mode breaks approvals while running in default mode floods them with prompts. The fix is to make acceptEdits the default (which still counts as non-auto, so approvals remain valid) combined with allow lists, so file edits in the working directory and basic filesystem commands auto-approve while riskier actions still prompt.
> 
> I'm also worried that broadly allowing python for CPU tests would reopen the F1 token-leak path, since python can read the token file—so the real fix is architectural: keep the token out of the agent's reach entirely, maybe via a separate OS user or restricted directory permissions, though that's complicated since the agent runs as the same user as the researcher.
> 
> If a container is used, GPU devices simply aren't present at all, so exporting CUDA_VISIBLE_DEVICES does nothing—meaning F1 becomes largely moot and most per-command gates become unnecessary once containerization is in place. I should also list other hidden prompt sources: reads outside the project directory, compound/piped commands, subagents making their own Bash calls that bubble up permission prompts, and specific python/edit command patterns under the research directory that still trigger asks.
> 
> Beyond that, the git commit lock each round needs a fix for overnight runs—I'd rather have a narrow protected wrapper script that performs the validated lock commit (with hash/audit checks) than allow raw git commit, since the agent could edit an unprotected wrapper. Mid-dialog AskUserQuestion gates and approval policies (like Codex's on-request vs never) also need addressing so overnight runs don't hang, though without seeing their actual settings.json I'm working from the patch alone.
> 
> I should recommend they add logging for permission prompts—possibly via a PermissionRequest or Notification hook—to gather real data on what gets asked, since that would let them build a data-driven allow list. Better yet, a PreToolUse hook could implement deterministic policy-as-code instead of a probabilistic classifier: it evaluates commands against explicit rules and returns allow/deny/ask, though I need to confirm whether hook-granted allows can still be overridden by deny rules.
> 
> I want to verify a few specifics—dontAsk mode behavior, how PreToolUse allow interacts with deny rules, sandbox requirements on Linux (bubblewrap), and how acceptEdits actually behaves—so I'll do some searches.
> 
> I notice that starting from v2.1.283, auto mode became the default built-in permission mode for Claude Code, and ask rules seem to prompt across every mode, even bypass. This makes me think ask rules are the primary gating mechanism — in bypass mode, prompts only occur when an explicit ask rule matches, and precedence likely runs deny, then ask, then allow, before any classifier even gets involved.
> 
> But wait, if ask rules prompt even in auto mode, that directly contradicts the claim in PATCH §2.3 that auto mode hands the ask layer off to the classifier entirely. I need to verify this.
> 
> I should correct that claim in the PATCH: per documentation, explicit ask rules still prompt even in auto mode (though a Windows bug #103077 can skip them). So auto mode doesn't actually relieve ask-rule prompts the way §2.3 implies — the user still gets prompted for every ask-rule match.
> 
> Hooks also can't override ask rules since 2.1.77, so those prompts are essentially unavoidable across every mode, while dontAsk converts them into automatic denials instead, which works well for overnight runs. I need to flag this nuance with a caveat about the version-specific bug and suggest a test to verify.
> 
> On sandboxing, bubblewrap is missing on the host, and while it typically needs sudo, it might be installable without root if unprivileged user namespaces are enabled — possibly via a conda-forge package, though I'm not fully certain of that path.
> 
> Now I'm drafting the actual answer, starting with the conclusion, then ranking root causes: first, ask rules trigger hard popups in every mode regardless of auto settings since hook allows can't override them since 2.1.77, meaning the auto-release decision bought little convenience while costing the approval path; second, the base mode defaults to Manual where only read-only commands are auto-allowed, so every code edit, pytest run, or compound command still requires approval.
> 
> I'm also noting that approval validity is tied to permission_mode staying non-auto, forcing users to remain in Manual/default where everything prompts -- and since v2.1.283+ sessions default to auto start mode, approvals can get rejected mid-session, pushing users back to default where prompts resurface everywhere; and structurally, the workflow itself keeps humans in the critical path at discussion gates, approvals, commit locks, and terminal launches.
> 
> The deeper issue is that even with zero prompts, overnight runs still stall at needing a human to run the next round or resolve memory conflicts -- the prompts are just one visible symptom of a workflow that fundamentally requires human checkpoints. Security design also leans entirely on prompts as gates since there's no sandboxing or isolation layer -- same-uid execution means prompting is the only safeguard, and interactive-wait mechanisms like AskUserQuestion have no "don't ask" fallback, making them fundamentally incompatible with unattended background operation.
> 
> So I'm rethinking the principle: humans should sit at decision points (semantic approval) rather than operational points (every command), security should come from isolation rather than friction-prone prompts that cause fatigue-induced blind spots, and overnight anything needing a human should queue-and-reject rather than hang -- essentially pre-approving a bounded "night envelope" that a deterministic program executes within, stopping cleanly once it exits that envelope. I'm now working toward a three-layer improvement plan with two session types.
> 
> Layer A handles isolation as the real substitute for popup-based safety: preferring a GPU-less container or separate uid, falling back to a bubblewrap sandbox, where the container's restrictions (no GPU devices, test data unmounted, eval/data read-only, token/launcher state not mounted) make python/bash safe to allow outright. Layer B reorganizes permissions by setting defaultMode to acceptEdits and allowlisting routine CPU scripts and git operations, while reserving ask-prompts only for control-plane edits like charter, rubric, protocol, settings, agents, skills, and knowledge files.
> 
> I'm weighing whether to move the python3 research-rounds command from ask to allow depending on whether containerization is in place, and swapping raw git commit for a wrapper command that's allowed while keeping the raw command gated by time of day. I'm also reconsidering whether to disable auto-mode entirely now that acceptEdits plus broad allowlisting makes typed approvals simpler, but I need to make sure the approval-checking logic rejects approvals coming from headless or dontAsk sessions, since an overnight driver script feeding prompts to claude -p could otherwise spoof an approval record.
> 
> For the night envelope design, I'm sketching how a human would type an approval before bed specifying round limits, GPU-hour budgets, allowed change types, and a deadline, which gets written into a night config file. To prevent tampering I'm thinking the approval statement should reference the envelope file's commit hash prefix, with verification requiring the approval timestamp to come after the envelope was committed and quote that hash.
> 
> During the night session, the agent runs within these bounds but defers champion/knowledge updates to morning human ratification, marking decisions as approved under the night envelope rather than full RL2/RL3 sign-off. I'm also working out that the launcher daemon runs under the researcher's own account on the host, outside the container, polling a request queue for valid jobs.
> 
> Before launching anything, it checks that the lock commit is clean, ERC values stay within envelope, cumulative budget from the run log hasn't been exceeded, the GPU is free, the envelope hasn't expired, there's no audit failure, and the kill-switch file isn't present — only then does it launch the human's actual process and write a STARTED marker, since the agent itself has no path to directly launch GPU jobs. For the driver loop, since a session can't just sleep for hours waiting on experiments, I'm sketching a host-side driver script that invokes the next round automatically once all experiments in the current round finish.
> 
> Each round runs as a fresh headless session to sidestep context compaction, with stop conditions covering budget exhaustion, round limits, deadlines, repeated failures, and any preregistered abort rule — numeric aborts could be enforced automatically, while anything outside the envelope gets queued to a pending file rather than blocking. The morning report then summarizes what ran, the results, pending decisions, and any denied actions for the human to ratify.
> 
> For night mode, I'm replacing the human discussion gate with a "skeptic veto": if the skeptic flags a blocking concern or there's significant judge disagreement, that candidate gets excluded from auto-run and queued instead, keeping things conservative. On the safety side, I'm weighing how F1 (sandboxing), F2 (whitelisting), and F6 (approval checks) need to adapt — containerization closes off GPU access more strongly than prompt-based restrictions, though without it I'd want at least a separate uid; the whitelist stays dormant until K9, and the approval check extends to cover the new envelope mechanism, which introduces its own risk of becoming too permissive.
> 
> I'm also flagging a known bug (#103077 on Windows) that makes auto-approval behavior version-dependent, so I'm adding canary test K10 to verify prompting still occurs in auto mode rather than assuming it works. For next steps: today's diagnostic involves checking whether a PermissionRequest or Notification hook can log permission prompts to identify the most common ones, followed by daytime changes like defaulting to acceptEdits and expanding the allow list — all without requiring new infrastructure.
> 
> I'm then outlining further steps: isolating risky commands via container, building the nighttime envelope plus launcherd driver, and adding audit checks (envelope compliance, ask-in-auto behavior, non-blocking denial, and launcherd state isolation). I'm preparing to provide concrete settings.json snippets, a sample envelope config, and a launcherd skeleton in Python, writing the response in Chinese and keeping the permission settings JSON for daytime container use.
> 
> Still drafting permissions config...
> 
> I'm noting that the agent should edit a pending approval file in the night directory, with humans approving via a committed hash that the launcher reads, so the bin and approved directories need to stay protected from direct edits. I'm also flagging that allowing unrestricted python3 execution outside a container reopens a known risk, so I'll only permit it with containerization or accept the tradeoff explicitly.
> 
> Thinking through the decision.md approval flow: during the day, human presence at the review point makes the confirmation dialog redundant, but at night the envelope itself serves as the confirmation, which conflicts with the deny-by-default ask rule. I'm resolving this by having the night skill write to a separate night_decision.md file instead, so the launcher can accept either the human-approved decision.md or the envelope-verified night_decision.md.
> 
> For git commits at night, since direct commits would be denied, I'm routing them through a protected `research/bin/ra-lock` wrapper that only stages allowed paths, refuses if control files were touched, and commits with a standardized lock message—while the wrapper script itself stays locked down via deny rules and read-only permissions. I'm also sketching the driver command that invokes the night round skill via `claude -p` with dontAsk mode and streams output to a session log, though I'm not fully certain slash-invoked skills work the same way through `-p`.
> 
> On the approval side, I want to make sure human approvals can't be forged from headless driver sessions, so I'm having the driver set an environment variable like `RA_SESSION=night` that the hook records and `check_approval` rejects—since that env var is controlled by the host process launching Claude, not something the agent itself can tamper with. I'm also working out how the approval envelope binds to a specific hash of the night's lock file to prevent replay across different configurations.
> 
> I'm now leaning toward disabling auto mode again since it doesn't add protection and actually introduces risk—since v2.1.283+ makes auto the default start mode, sessions could silently start in a state where approvals are invalid, so setting `defaultMode` to `acceptEdits` avoids that friction; I need to double check which settings (likely bypassPermissions and auto itself) can't be set via project config versus acceptEdits which can. On the Codex side, I'm briefly considering how "never" approval policy interacts with workspace-write and forbidden rules, hedging since Codex's behavior when a command needs approval under "never" mode isn't fully clear to me.
> 
> Now I'll draft the full answer, aiming for a thorough but reasonably tight response given the complexity involved.
> 


# demo-revised 审核：为什么正常操作也要不停点 yes，以及重新权衡后的改进方案

## 0. 结论

一夜醒来卡在点 yes 上，背后有两类原因。

- **表层是权限配置。** demo-revised 把"弹窗"当成主要安全手段，而且把最常用的 python 放进了 ask。按 Claude Code 当前文档，**ask 规则在任何权限模式下都会弹**，放行 auto 也消不掉。
- **深层是流程结构。** 即使一个弹窗都没有，Lite 协议每一轮都必须有人在场：讨论门、P7 批准、锁定提交、在研究员终端启动、开下一轮。所以夜里最多只能跑到"请在你的终端运行 launch.sh"这一步。

改进的方向是：**人只在决策点把关，不在每条命令上把关。** 安全改由隔离环境保证，不再靠弹窗。夜间改为"睡前预批一个信封（预算与范围的上限）+ 一个确定性的启动守护进程"。凡是超出信封的事项，一律**拒绝并排队**，不挂起等人。

---

## 1. 问题成因（按影响排序）

### 1.1 ask 规则在所有模式下都弹，PATCH §2.3 的前提有误

PATCH §2.3 认为放行 auto 之后，ask 层会交给分类器处理。这与当前官方文档不符：

- 文档写明：deny 规则和显式 ask 规则都在分类器之前评估，**照样拦截或弹窗**。原文的理由是"显式 ask 规则表示你想被询问"（[auto-mode-config](https://code.claude.com/docs/en/auto-mode-config)）。
- 从 2.1.77 起，PreToolUse hook 返回 allow 也压不住 ask：匹配到 ask 规则时照样弹窗。也就是说，hook 只能收紧权限，不能放宽。

由此有三个推论：

1. `Bash(python3 research/rounds/*)`、`git commit`、decision.md、各控制文件的编辑，以及模式 B 的 `bash launch.sh`，这些 ask **在 auto、acceptEdits、default 下都会弹**。放行 auto 换来的便利几乎为零，代价却是 auto 下输入的批准语句全部被 `check_approval` 判为无效。
2. PATCH 对 auto 的风险估计偏悲观："python3 ask 在 auto 下失效"按文档并不成立。但有一个例外：存在 ask 规则在 auto 下被跳过的 bug（[#103077](https://github.com/anthropics/claude-code/issues/103077)，2.1.296，Windows，仍在复现）。这个行为随版本变化，应当加一项 canary 实测，不能靠推断。
3. **v2.1.283 起，交互会话默认以 auto 启动**（[permission-modes](https://claude-code.mintlify.app/en/permission-modes)）。你很可能遇到过这个循环：会话以 auto 启动 → 批准被拒 → 切到 Manual → Manual 下所有操作都弹。

### 1.2 基础模式是 Manual，allow 里只有只读命令

Lite 的 allow 只放了只读命令，python3 不在里面，Codex 的 rules 里 python 也是 prompt。对一个 ML 项目来说，这意味着：

- 每次改代码都弹。Manual 模式下，Edit 和 Write 一律需要确认。
- 每次 CPU 自检、pytest、`python3 -c` 复算都弹。
- 复合命令只要有一段不在 allow 里就弹。例如 `grep … | sort | uniq -c`，其中任何一个命令没进 allow 就会触发。
- 读仓库外的日志也弹（没有配置 `additionalDirectories` 的情况下）。

### 1.3 批准有效性和权限模式绑在一起，造成模式冲突

`check_approval` 和 ⏸.6 都要求 `permission_mode ≠ auto`。这条约束本身合理，但当前的模式选择逼你在两头之间二选一：

- 用 auto：所有操作不弹，但批准作废；
- 用 Manual：批准有效，但所有操作都弹。

中间档 **acceptEdits** 两者都能满足：它不是 auto，批准有效；编辑也不弹。但它没有被设成默认模式。

### 1.4 安全性押在弹窗上，缺少隔离层

F1 的修复 P0-1c，本质上就是"python 一律弹窗"。原因是同一个 uid、没有 bwrap 沙箱、GPU 对进程可见，**只剩弹窗能当门**。弹窗有两个坏处：

- 摩擦大；
- 人一旦疲劳，就会形成"盲点 yes"。弹窗疲劳本身就是安全漏洞：第 50 次弹窗时，你不会再仔细看命令内容。

### 1.5 流程结构：人在关键路径上（这是"卡一夜"的主因）

| 环节 | 当前设计 | 夜间后果 |
|---|---|---|
| ⏸ 讨论门 + P7 批准语句 | 必须由人输入 | 停在 brief |
| L 锁定 `git commit` | ask | 停在弹窗 |
| 启动 | 模式 A：研究员在终端执行 | 停在"请运行 launch.sh" |
| 命中 abort 条件 | 研究员手动 kill | 坏实验烧一夜 GPU |
| 训练结束 → 下一轮 | 人工执行 `/ra-round` | GPU 空闲到天亮 |
| 交互式弹窗、AskUserQuestion | 无限期等待 | 挂起，而不是失败 |

另外，后台子代理不触发 SubagentStop 记账（PATCH §3 已经实测），所以也不能靠后台任务绕开这些等待。

---

## 2. 重新权衡的原则

1. **把人从操作点移到决策点。** 每条命令不需要人确认。需要人把关的只有：预算与范围（信封）、记忆和 champion 变更（RL2）、章程和协议（RL3）。
2. **安全靠隔离，不靠弹窗。** 智能体所在环境里没有 GPU、看不到 test、评测代码和数据只读、接触不到启动凭据。在这样的环境里，放开 python 和 bash 的风险是可控的。
3. **夜间遇到需要人的事项，一律拒绝并排队，不挂起。** 用 `dontAsk` 模式：凡是会弹窗的操作都直接被拒，智能体换别的工作做，或者正常结束会话。
4. **批准异步化。** 睡前预批一个带硬上限的信封。信封内的事项由确定性程序（守护进程）执行，超出就停；早上由人追认。

---

## 3. 改进方案

### 3.1 隔离层（决定后面权限能放多宽）

| 方案 | 效果 | 成本 |
|---|---|---|
| **A. 无 GPU 容器（推荐，即 Lite §7.3）** | 容器里没有 GPU 设备，F1 失去意义：就算智能体拿到令牌调用 `__run`，也没有卡可用。test 不挂载；评测代码和数据以只读挂载；令牌和守护进程状态不挂载 | 需要一个镜像，Docker 或 podman 均可 |
| B. 独立 uid 运行智能体 | 令牌、test、守护进程目录设为 700，属于研究员用户，智能体读不到 | 需要 root 创建用户；GPU 仍可见，还要配合 cgroup 或设备权限 |
| C. 安装 bubblewrap，启用 Claude 原生沙箱 | `sandbox.enabled` + `autoAllowBashIfSandboxed`，沙箱内的 Bash 不弹；配合 `failIfUnavailable: true` | 当前宿主没有 bwrap，需要安装；对 GPU 设备的隔离能力需要实测 |
| D. 不隔离 | 只能维持现状，安全靠弹窗 | 无法支撑夜间无人值守 |

**没有隔离层就把 python 放进 allow，等于重新打开 F1 的完整闭环。** 后面的权限放宽都以 A、B、C 之一为前提。

### 3.2 权限重排（白天：自由讨论、自由改代码）

把 `.claude/settings.json` 的要点改成下面这样（以容器方案 A 为前提）：

```jsonc
{
  "permissions": {
    "defaultMode": "acceptEdits",          // 非 auto，批准有效；编辑不弹
    "disableBypassPermissionsMode": "disable",
    "disableAutoMode": "disable",          // 建议恢复：auto 不消除 ask 弹窗，只会让批准作废
    "allow": [
      "Bash(python3 *)", "Bash(python *)", "Bash(pytest *)",      // 只在有隔离时放开
      "Bash(bash research/bin/ra-lock *)",                        // 锁定提交用的受控包装脚本（见 3.4）
      "Bash(bash research/bin/ra-request *)",                     // 向守护进程提交启动请求
      "Bash(git status*)", "Bash(git diff*)", "Bash(git log*)", "Bash(git add *)", "Bash(git show*)",
      "Bash(ls*)", "Bash(cat *)", "Bash(grep *)", "Bash(head *)", "Bash(tail *)", "Bash(wc *)",
      "Bash(sort*)", "Bash(uniq*)", "Bash(jq *)", "Bash(find *)", "Bash(diff *)"
    ],
    "ask": [                               // 只留控制面：都是真正需要人看一眼的
      "Edit(./research/charter.md)", "Edit(./research/rubric.md)", "Edit(./research/PROTOCOL.md)",
      "Edit(./research/knowledge.md)", "Edit(./research/negative_results.md)",
      "Edit(./research/rounds/*/decision.md)",
      "Edit(./.claude/**)", "Edit(./.agents/**)", "Edit(./CLAUDE.md)", "Edit(./AGENTS.md)",
      "Bash(git commit*)"                  // 直接 commit 仍需确认；日常锁定走 ra-lock
    ],
    "deny": [
      // 原有的 deny 全部保留（test、评测、数据、危险 git、启动器、.token……），并新增：
      "Edit(./research/bin/**)", "Edit(./research/night/*.yaml)",
      "Bash(bash research/rounds/*/launch.sh*)",   // 取消模式 B：智能体永远不直接启动训练
      "Read(./research/night/.launcherd/**)"
    ]
  }
}
```

配套修改有三处：

- **删除 `Bash(python3 research/rounds/*)` 这条 ask**。它原本承担的 F1 防线，改由隔离层承担（第 4 节）。
- **`check_approval` 的有效模式改成白名单**：批准语句只有在 `permission_mode ∈ {default, acceptEdits}` 且 `RA_SESSION ≠ night` 时才有效（见 3.4）。这样批准不再要求你离开当前模式，无头会话里的批准也会被判为无效。
- **CLAUDE.md 第 7 行**改为"默认使用 acceptEdits；不使用 auto 或 bypassPermissions"。

做完这些，白天的弹窗只剩两类：修改控制面文件，以及直接执行 `git commit`。这两类本来就应该由人看一眼。

### 3.3 夜间信封：睡前预批一次

讨论结束后，让智能体起草 `research/night/N01.yaml`，用 ra-lock 提交，然后你输入一条带哈希的批准语句：

```yaml
# research/night/N01.yaml
id: N01
deadline: "2026-10-24T07:30+08:00"
max_rounds: 3
gpu_hours_total: 150          # 硬上限，由守护进程根据 runs.jsonl 累计
gpu_hours_per_exp: 60
allowed_change_classes: [hparam, schedule, data_mix]   # 参照 ERC 的 change 字段
forbidden: [eval_code, dev_set, architecture, charter]
max_dev_looks: 4              # 防止 dev 过拟合：夜间查看 dev 的次数额度
min_seeds: 3
auto_abort: [nan_loss, loss_divergence]   # 只执行 ERC 中预注册的、可以机器判定的 abort 条件
on_skeptic_blocker: queue     # skeptic 提出阻断级问题的候选，不跑，留到早上
on_judge_disagreement: queue  # impact 极差 ≥2 的候选，同样不跑，留到早上
memory_updates: defer         # champion、knowledge、负结果的 CR 只起草，不应用（RL2 仍由人批）
stop_on: [two_consecutive_failed, audit_fail, stop_file]
```

批准语句的格式：

```
批准(RL3) 夜间 N01 @3f9a2c1e
```

`@` 后面是 `git hash-object research/night/N01.yaml` 的前 8 位。守护进程会核对这个哈希，确保你批准的正是已经提交的那个版本。这一步也顺带部分解决了 D4/D5 的哈希绑定问题。

### 3.4 夜间执行：守护进程 + 无头会话 + dontAsk

```
宿主机（研究员的 uid，看得到 GPU）            容器（智能体，没有 GPU）
┌──────────────────────────┐            ┌──────────────────────────────┐
│ ra-launcherd（研究员在 tmux │ docker exec │ claude -p "/ra-round R04 night=N01" │
│  里启动，作用相当于模式 A）  │ ─────────▶ │   --permission-mode dontAsk  │
│ · 轮询 research/queue/*.req │            │   RA_SESSION=night（宿主设置）│
│ · 核验信封、哈希、截止时间、 │ ◀───────── │ 产出：night_decision.md、ERC、│
│   预算、锁定提交、GPU 空闲、 │  .req 文件  │   ra-lock 提交、ra-request    │
│   STOP 文件                │            │ 超出信封的事项 → pending.md   │
│ · 执行 launch.sh → 写 STARTED│            └──────────────────────────────┘
│ · 执行预注册的机器可判 abort │
│ · 本轮全部达到终态 → 开下一轮 │
│ · 截止、预算耗尽、失败 → 停   │
└──────────────────────────┘
```

**守护进程（launcherd）**
- 由你在宿主机启动，用的是你自己的 uid，所以本质上仍是模式 A：训练进程永远由人这一侧启动。
- 智能体只能写启动请求文件，碰不到 GPU，也碰不到令牌。
- 它的核验逻辑是确定性代码，与权限模式和分类器无关。
- 它的代码和状态目录不挂进容器。

**每轮一个新的无头会话**
- 每一轮都起一个新的 `claude -p` 进程。这样顺带避开了长时间运行时的上下文压缩问题。
- 加上 `--output-format stream-json`，把被拒的操作（`permission_denials`）写进早报。

**dontAsk 的作用**
- 所有会弹窗的操作都直接被拒，会话不会挂起。
- ask 规则在 dontAsk 下也是"拒"。所以夜间流程必须绕开 ask 路径：
  - 写 `night_decision.md`，不写 `decision.md`；
  - 锁定提交走 `ra-lock`，不直接执行 `git commit`。

**ra-lock 包装脚本**
- 放在 `research/bin/`。这个目录同时受 deny 规则保护和 OS 只读保护，在容器里以只读方式挂载。
- 它只暂存本轮目录和代码改动。如果检测到控制文件有变更，就拒绝提交。提交信息里带上信封 ID。

**批准记账防伪**
- `ra_log.py` 在记录每条人类输入时，加记 `os.environ.get("RA_SESSION")`。
- 这个环境变量由宿主机上的驱动设置，智能体改不了。
- 因此夜间会话里，即使 prompt 中出现"批准"两个字，也会被判为无效。

**ra-round 技能增加 `night=<id>` 分支**
- 跳过 ⏸ 讨论门。
- 遇到 skeptic 的阻断级问题或评委意见分歧，相关候选写进 `research/night/N01/pending.md`，然后跳过。
- 记忆类 CR 只起草，不应用。
- 遇到任何拒绝都不重试、不绕行：记录下来，继续做其他候选；没有可做的就结束会话。

**早报：`research/night/N01/report.md`**
- 跑了什么、各实验的阶段 A 确认性分析、累计 GPU·h；
- 待你决定的事项（pending）、被拒的操作清单；
- 起草好的 CR 和 champion 变更建议。

早上的追认操作：
- 用 `/ra-memory` 批准这些 CR；
- 用一条 `追认 N01: R04-E1, R05-E2` 把夜间实验从 `approval: envelope` 升级为正式记录。

**守护进程的核验清单**（每一项都是确定性的；任何一项不满足就拒绝启动，并写进早报）：
1. 信封已提交，而且批准语句里的哈希和它一致；批准语句来自 `RA_SESSION ≠ night`，且模式在 {default, acceptEdits} 中。
2. 当前时间早于截止时间；STOP 文件不存在；`audit_fail` 和连续失败都没有触发。
3. 请求所属的轮次已经锁定提交，工作区干净，ERC 和 launch.sh 都在锁定提交里。
4. ERC 的 change 类别在 `allowed_change_classes` 内，没有触碰 `forbidden`，种子数 ≥ `min_seeds`。
5. 累计 GPU·h + 本实验预计 GPU·h ≤ 上限；dev 查看次数在额度内。
6. GPU 空闲（`nvidia-smi` 输出与 runs.jsonl 一致）。

### 3.5 审计补项

| 编号 | 检查内容 |
|---|---|
| **C16** | 夜间的每个 STARTED 都能对应一个有效信封，而且守护进程的核验日志逐项通过 |
| **C17** | 夜间轮次的记忆类 CR 都是在早上由人批准后才应用 |
| **K10** | 在 auto 模式下触发一条 ask 规则，应当弹窗（验证 #103077 是否影响你的版本）|
| **K11** | 在 dontAsk 无头会话里触发一条 ask 规则，应当被拒而且会话不挂起 |
| **K12** | 在容器里执行 `nvidia-smi` 应失败；读取 `/dev/nvidia*`、令牌、launcherd 状态都应失败 |
| **K13** | 在 `RA_SESSION=night` 的会话里输入批准语句，`check_approval` 应拒绝 |

---

## 4. 安全收支对照

| 项 | demo-revised（auto 放行变体） | 改进后（容器 + 信封） |
|---|---|---|
| F1：`__run` 绕过 | 只有 python 弹窗挡着（auto 下是否仍弹取决于版本）| 智能体所在环境没有 GPU，路径不存在 |
| F2：伪造 decision.md 或抢占 p1 产出 | 白名单处于休眠 | 不变；K9 通过后启用 `.whitelist_on` |
| F6：伪造批准 | 有 `check_approval` | 再加信封哈希绑定和 `RA_SESSION` 检查 |
| 弹窗疲劳导致盲点 yes | 高 | 白天只剩控制面弹窗，夜间没有弹窗 |
| 夜间失控烧 GPU | 不适用（夜里根本跑不起来）| 硬上限：预算、轮数、截止时间、STOP 文件、自动 abort |
| dev 过拟合 | 按轮计数 | 夜间轮次更多，所以信封单独设 `max_dev_looks` |
| **新增风险** | — | 信封写得太宽；守护进程本身的 bug。对策：首夜只给小信封（1 轮、≤40 GPU·h），K10–K13 全部通过后再放大 |

没有容器或独立 uid 的情况下，3.2 节里 python 相关的 allow **不要启用**。那样只能做到"白天少弹"，做不到夜间无人值守。

---

## 5. 落地顺序

1. **先测量（今天，约 10 分钟）**：加一个 Notification hook（matcher 为 `permission_prompt`，以你所用版本的文档为准），把每次弹窗记到 `events.jsonl`。正常用一天，然后统计弹得最多的前 10 类操作，用实际数据决定 allow 列表。
2. **白天减负（不需要新基础设施）**：
   - `defaultMode` 改为 acceptEdits，恢复 `disableAutoMode`；
   - 把只读和 CPU 测试类命令加进 allow（python 先不放开）；
   - `check_approval` 改成白名单模式；
   - 配置 `additionalDirectories`。
3. **上隔离**：用容器方案 A，跑通 K12，然后放开 python 和 pytest 的 allow，删掉 P0-1c 那条 ask。
4. **上夜间信封**：
   - 写 ra-launcherd，约 150 行 Python，第 3.4 节的核验清单就是它的规格；
   - 写 ra-lock 和 ra-request；
   - ra-round 增加 night 分支；
   - 补 C16、C17、K10–K13；
   - 首夜用小信封试跑。
5. **Codex 侧**（如果要用）：夜间配置为 `approval_policy = "never"`，加 workspace-write。具体的拒绝语义以所用版本为准，同样要用 K11 实测确认。rules 里的 forbidden 规则保留。

需要的话，我可以接着给出 ra-launcherd、ra-lock 的完整实现，以及 ra-round 的 night 分支补丁，格式与 §5 保持一致，方便直接登记进 PATCH。

Learn more:
- <https://platform.claude.com/docs/pt-BR/agent-sdk/permissions>
- <https://claude-code.mintlify.app/en/permission-modes>
- <https://github.com/0xDarkMatter/claude-mods/blob/main/docs/AUTO-MODE-CLASSIFIER.md>
- <https://note.com/masa_aimaster/n/n9a35db0e079b?hl=en>
- <https://docs.anthropic.com/en/docs/claude-code/desktop?>
- <https://dev.to/aicoding-guide/claude-code-permission-modes-compared-default-acceptedits-plan-auto-dontask-bypasspermissions-f5k>
- <https://startdebugging.net/2026/09/fix-pretooluse-hook-allow-still-blocked-by-deny-rule/>
- <https://dev.to/boucle2026/how-to-fix-claude-codes-broken-permissions-with-hooks-23gl>
- <https://github.com/anthropics/claude-code/issues/77037>
- <https://github.com/anthropics/claude-code/issues/39344>
- <https://docs.anthropic.com/en/docs/claude-code/hooks-guide?>
- <https://code.claude.com/docs/en/auto-mode-config>
- <https://dev.to/rulestack/auto-mode-is-now-claude-codes-default-what-the-classifier-approves-and-how-to-switch-back-4j2j>
- <https://github.com/anthropics/claude-code/issues/103077>
- <https://docs.anthropic.com/en/docs/claude-code/security?>
- <https://github.com/ariel-frischer/autospec/blob/main/docs/public/claude-settings.md>
- <https://github.com/FlorianBruniaux/claude-code-ultimate-guide/blob/main/examples/skills/sandbox-status/SKILL.md>
- <https://ai-workshop.dometrain.com/docs/secure-execution/sandbox-mode>
- <https://blog.prototypr.io/how-to-create-a-secure-sandbox-environment-for-claude-code-on-ubuntu-2b8a80872fa5?source=user_profile_page---------6-------------f1913d8bf715---------------------->