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
   - v2.5 增检：`printenv CLAUDE_CODE_FORK_SUBAGENT` 为 0、`printenv CLAUDE_CODE_DISABLE_AUTO_MEMORY` 为 1；`lsattr research/ledger/results.jsonl` 含 a → meta.yaml 记 ledger_protection: os-append-only，否则 degraded（git 对账补偿，并在 brief §0 提示研究员）。
3. 建目录 R/{p1,p3,p4,p5,p6,p8,erc,exp,work/analyst,work/skeptic}。按 templates/meta.yaml 写 meta.yaml：charter_blob 用 `git hash-object research/charter.md`；parent_lock_commit 从 STATUS.md 取；**填写 runtime 与 models 中各角色实际使用的 model ID**（P1-2）；填写 conclusions_snapshot（conclusions/results 两本账的哈希与 results 行数）与 ledger_protection。

## A 结果回收（存在 Rp 时）
1. 从 Rp/decision.md 取出已批准的 exp_id，查看 runs/<exp>/ 下的状态标记和 research/ledger/runs.jsonl。还在运行的列为"未完成"，不分析。全部未完成时，询问研究员：是先结束本次等待，还是只基于已有信息继续设计。
2. 调用 ra-analyst（阶段 A）。输入：Rp 的 erc/、decision.md、相关的 runs/<exp>/。输出：`<!-- ra:out R/A_results.md -->`。
3. 若 `git log <parent_lock_commit>..HEAD -- research/rounds/Rp/erc research/rounds/Rp/exp research/rounds/Rp/launch.sh` 非空，就在 A_results.md 顶部追加一行"⚠ 锁定后被修改"。这是唯一允许你追加的内容。
4. 把"CR 草稿"按 templates/cr.md 写成 research/memory/proposals/CR-R-NN.md。如果本轮要依据 dev 结果做选择，把 dev 查看计数加 1.
5. 运行 `python3 research/scripts/res_extract.py`（白名单脚本，无参数）：把本轮判定的 RES 行追加到 results.jsonl。提取失败的实验以 undeclared 记录，不猜档位；undeclared 项在下一轮 review-queue 中提示补判。
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
1. 按 templates/brief.md 写 R/brief.md。§0.5 上轮研究员质疑：逐字引自 human_inputs.jsonl（附 ev#L…），已处理的标 resolved_by=<ID@vN>；上轮若有 supersede，先跑 `python3 research/scripts/review_queue.py Rp`，把受影响清单要点并入 §2/§5。
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
3. 若本轮轮末经 /ra-memory 发生过 supersede：运行 `python3 research/scripts/review_queue.py R`，受影响清单随本轮入库（喂下一轮 P1）。
3. 锁定后，对 erc/、exp/、launch.sh 的任何修改都属于协议偏离，须新版本 ERC、重新批准、重新做锁定提交。

## X 交付启动
- 模式 A：告诉研究员在终端执行 `bash research/rounds/R/launch.sh`。脚本会自查锁定状态、代码是否干净、是否已启动过、GPU 是否被占用。
- 模式 B：提示研究员可以运行 `/ra-launch R`。
更新 STATUS.md：状态 awaiting_launch，列出实验及预计完成时间，下一步写"训练完成后运行 /ra-round"。本次交互到此结束。
