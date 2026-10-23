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
