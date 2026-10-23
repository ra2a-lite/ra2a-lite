@AGENTS.md

## Claude Code 专用补充
- 子代理在 .claude/agents/ra-*.md；技能目录 .claude/skills 是 .agents/skills 的符号链接。
- P1/P3/P4/P8 要在同一条消息里并行发起多个子代理调用。不要 resume 子代理，每次都新开。
- 讨论门可以用 AskUserQuestion 给研究员列选项；但"批准"必须由研究员亲自输入文字，点选不算。
- 不使用 bypassPermissions，不用后台任务。auto 模式经研究员 2026-10-23 裁决放行（已声明偏离，登记于 PATCH-v2.3.md §2）；批准语句仍须在非 auto 权限下输入。
- 上下文被压缩或会话恢复后，先重读 research/STATUS.md 和本轮目录，再继续。
