
# 结论：可以执行，但不要整份一次性照做

方向我认同，而且它修正了我前两份回答里几处过度的说法：

- "用 `RA_SESSION` 证明是人在操作"不成立；
- "守护进程用研究员的 uid 就等于模式 A"不成立；
- "睡前给个宽泛额度、早上再追认"不可取。

这三处方案的裁定是对的。但有 4 个问题要先补上，其中 2 个会直接影响 B1 能不能安全上线。

## 1. 各批次能不能动

| 批次 | 能否开始 | 前提 |
|---|---|---|
| B0 基线与能力登记 | **可以马上做** | 先确认本机 Claude Code 版本（见 2.2） |
| B1 白天减负 | **可以做，但要先修 2.1 和 2.2** | 每批 RL3 批准 |
| B2 隔离、批准、锁定 | **先补一页设计决定再动工**（见 2.3） | 容器后端通过验收 |
| B3 夜间代码与 CPU 工作 | 依赖 B2，暂不开始 | B2 的 T03–T07 通过 |
| B4 固定批次执行 | 另立协议修订 | 研究员单独决策 |

## 2. 需要先补的问题

### 2.1 acceptEdits 会自动放行 Bash 文件命令，B1 可能漏掉控制文件保护（必须修）

官方文档写明，acceptEdits 除了放行文件编辑，还会自动批准 mkdir、touch、mv、cp 等文件系统命令。有实测文章列出的完整集合是 `mkdir touch rm rmdir mv cp sed`，加上 `timeout`、`nohup` 这类包装器。范围是工作目录内的路径，平台内置的受保护路径除外。

这对本项目的影响：

- `rm` 已经在 ask 里，仍然会弹窗。
- 但 `sed -i … research/charter.md`、`cp x research/ledger/human_inputs.jsonl`、`mv` 覆盖 `memory/*.md` 这类命令，是否受 `Edit(...)` 的 deny/ask 约束，文档没有明说。如果不受约束，B1 的完成标准"控制文件仍受保护"就不成立，而且这是**比现状更弱**的状态。

处理办法：

- 在 T01 里加负例：分别用 `sed -i`、`cp`、`mv`、`touch` 去改 ledger、charter、memory、`.claude` 这几处，都应当被拒绝或弹窗。
- 如果实测发现被自动放行，就在 B1 里按部署版本支持的语法补上路径级的 Bash deny/ask，然后才能把默认模式切到 acceptEdits。

### 2.2 B2 完成前保留 auto 有风险，要看本机版本

方案的长期判断没问题：auto 用于干活，批准走单独的入口。但在 B2 隔离到位之前，auto 会带来两个具体风险。

1. **不在 ask 里的解释器命令交给分类器判断。** 比如 `python3 src/x.py`、`bash scripts/*.sh`、`make`。分类器可能放行，而 Python 可以在内部改写 `CUDA_VISIBLE_DEVICES`，这正是 Lite §7.2 第 1 条列的风险。在 Manual 或 acceptEdits 下，这些命令至少还会弹窗。
2. **旧版本里 ask 可以被绕过。** 有记录显示 v2.1.257 修复了一个问题：在 auto 模式下，命令放进复合命令或子 shell 时，匹配的 ask 规则会被跳过，命令不经确认就执行。方案提到本机版本早于 2.1.283，**如果还早于 2.1.257**，`cd x && python3 research/rounds/...` 这种写法就能在 auto 下绕过 ask。

我的建议：

- B0 先确认版本。低于 2.1.257 的，要么先升级，要么在 B1 里临时加 `disableAutoMode`。
- 更稳妥的做法是：B2 隔离验收通过之前临时禁用 auto，B2 之后再按方案开放。这只是调整先后顺序，不推翻 D06。
- 另外有个界面上的坑：Manual 和 acceptEdits 下的 Bash 弹窗里有一个"Yes, and switch to auto mode"选项，点一下整个会话就进了 auto。之后在这个会话里输入的批准，会被模式检查拒绝。这就是你之前遇到的那种循环，要写进 CLAUDE.md 的使用说明。

### 2.3 B2 的人工批准入口没说清在哪里，D10 和 D11 有矛盾

方案一方面说环境标签不能证明是人输入的（D11），另一方面又要在批准入口校验 Claude 的 `permission_mode`（D10）。

问题在于：Claude 跑在容器里之后，`UserPromptSubmit` hook 也在容器里执行，它的载荷（包括 `permission_mode`）对同一个 uid 的 worker 来说同样可以伪造。所以只要批准还是"在 Claude 对话里打字"，模式白名单就不是可靠的来源证明。

需要明确拍板的一点：**有效批准只来自宿主机终端里的一条独立命令**（例如 `ra-approve R03 …`）。这条命令展示 manifest 的 digest，研究员亲自输入批准原文，状态写在容器以只读方式挂载的位置。对话里的"批准 R03: …"只作为提示和镜像记录，不再是权威凭据，D10 的模式白名单降为辅助检查。

这会改变你的操作习惯：批准要切到终端去输入。要先确认你能接受，再开工 B2。

### 2.4 方案对诉求 ③ 只是部分满足，需要你明确接受

B3 完成后，夜里可以改代码、做 CPU 分析、走完 A–P6，早上交给你待审的材料。B4 完成后，夜里可以执行你睡前签好的固定实验清单。

但"夜里自己设计新实验并自己启动下一轮"被明确排除了。我认为这个排除是对的，因为预注册加人工批准本来就是要防这件事。不过它和"夜间无人值守迭代"的原始诉求不完全一致，这一点应该由你明确接受，而不是默认被缩小。

另外要有个预期：**你现在最主要的弹窗来源是子代理跑 `python3 research/rounds/*`，这个要到 B3 才会消失**，B1 只解决改源码时的弹窗。在没有隔离的前提下，我没找到能安全提前放开它的办法。

## 3. 次要但要写进方案的几点

- **Docker：** 容器里绝不能挂 `/var/run/docker.sock`。docker 组成员实际上等同于 root，worker 一旦拿到这个 socket，就能起一个带 GPU 的容器绕开全部限制。T03 要有对应的负例。
- **无头入口的另一种选择：** 新版本有 `--permission-prompts none`，原本会弹窗的请求一律自动拒绝，权限模式本身照常生效。B0 可以和 dontAsk 一起登记，选一个本机支持的。
- **工程量要写明：** B2/B3 实际上把 Lite §0 说"删掉"的 Ledger 和 Conductor 的一部分做回来了，包括批准签发、可信落盘器、事件收集器和调度。应该在 PROTOCOL 和 Lite §0 里写明这个定位变化，避免文档继续写着"只需维护一个 40 行 hook"。

## 4. 怎么推进

1. **每一批都按 RL3 批准。** 改 `.claude/`、AGENTS、PROTOCOL 属于 RL3，同时受 AGENTS 规则 3 约束。格式例如：`批准(RL3) v2.4-B1: 修改 settings/CLAUDE.md/PATCH: 白天减负`。
2. **先做 B0。** 包括版本号、2.1 的 acceptEdits 文件命令实测、2.2 的 auto 复合命令实测，以及 docker socket 的可达性检查。
3. **再做 B1。** 带上 2.1 和 2.2 的修正，跑完 T01 后再切默认模式。
4. **补一页 B2 设计决定，再开工 B2。** 内容是批准入口放在宿主终端（2.3）、容器挂载清单、socket 和凭据的排除项。
5. **B3 和 B4 按方案原顺序推进。**

把 2.1–2.3 作为附加条件写进方案的 §4、§5.2、§9 之后，就可以按 B0 → B1 开始执行。需要的话，我可以把这三处修正直接写成可以合并进方案的 diff 文本。

参考：[权限模式（acceptEdits 的命令集、auto 切换按钮）](https://claude-code.mintlify.app/en/permission-modes) · [acceptEdits 实测](https://startdebugging.net/2026/08/auto-mode-vs-manual-approval-what-each-permission-mode-allows/) · [auto 模式与 ask 规则的优先级](https://code.claude.com/docs/en/auto-mode-config) · [v2.1.257 修复 ask 绕过、`--permission-prompts none`](https://dev.to/rulestack/auto-mode-is-now-claude-codes-default-what-the-classifier-approves-and-how-to-switch-back-4j2j)

Learn more:
- <https://claude-code.mintlify.app/en/permission-modes>
- <https://github.com/thevibeworks/claude-code-docs/blob/main/content/en/docs/claude-code/permission-modes.md>
- <https://startdebugging.net/2026/08/auto-mode-vs-manual-approval-what-each-permission-mode-allows/>
- <https://docs.anthropic.com/en/docs/claude-code/sdk/sdk-permissions>
- <https://docs.anthropic.com/en/docs/claude-code/desktop?>
- <https://code.claude.com/docs/en/auto-mode-config>
- <https://github.com/0xDarkMatter/claude-mods/blob/main/docs/AUTO-MODE-CLASSIFIER.md>
- <https://dev.to/rulestack/auto-mode-is-now-claude-codes-default-what-the-classifier-approves-and-how-to-switch-back-4j2j>
- <https://docs.anthropic.com/en/docs/claude-code/security?>