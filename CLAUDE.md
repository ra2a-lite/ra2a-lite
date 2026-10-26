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
