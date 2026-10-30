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
   - hypothesis_status 类 CR：状态词必须抄自所引实验的判读档（results.jsonl 的 interpretation_band，CR 带 band_source）；不可判定族（no_diff/flat/*negligible）只能写 tested_flat/unresolved_*——commit_conclusion.py 会拒绝升格。
   - supersedes 必填（指向被取代 ID@vN）；编号复用会被 commit_conclusion.py 拒绝。
3. 请研究员逐条答复：`批准 CR-…`、`驳回 CR-…: 理由` 或 `修改 CR-…: …`。不得批量默认通过。RL3 类须附理由。
4. 对于批准的 CR：按"变更内容（逐字）"编辑目标文件（会触发确认）；在 CR 中写 status: applied、approval_ref（human_inputs 的 ev 行号）与 conclusion_addr；把 CR 移到 proposals/applied/。涉及语义结论的，把结论行 JSON 经 stdin 交给 `python3 research/scripts/commit_conclusion.py` 追加（版本/hash/断言由它锁内完成）。驳回的移到 proposals/rejected/，并写明理由。随后单次 git commit（编辑+追加+提交原子化，PROTOCOL §5.3）。若发生 supersede，运行 `python3 research/scripts/review_queue.py <轮次>` 生成受影响清单。
5. 章程预授权范围内的变更可以直接应用，但要在下一轮 brief 中列出。
6. 涉及 .claude/agents、技能或 rubric 的变更，建议做一次回放对比：用旧版和新版分别对最近一轮的同一输入重跑相关阶段，把差异交给研究员看。
7. 请研究员确认后提交：`git commit -m "memory: <CR 列表>"`。
