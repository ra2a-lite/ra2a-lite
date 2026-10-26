# 候选配置（不被 Claude Code 加载）

本目录存放**已起草、未启用**的权限配置候选。Claude Code 只加载 `.claude/settings.json` 与 `.claude/settings.local.json`，本目录内的文件是纯文本草案。

## settings.acceptEdits.draft.json（v2.4 起草）

与生效配置 `.claude/settings.json` 的**唯一**差异：`permissions.defaultMode` = `acceptEdits`（生效配置为 `default`）。

### 启用前置（缺一不可）

依据 `update/final_modification_plan.md` §4.1 第 1 项与 §9 验收清单：

1. **T01a 通过**（在合成目录，不碰真实账本/章程/记忆/评测）：
   - 正例：default 与 acceptEdits 下普通源码编辑可用、不被逐次弹窗；
   - 负例：对仿真 ledger / charter / memory / .claude / .codex 路径分别用 `sed -i`、`cp`、`mv`、`touch`、shell 重定向（`>`/`>>`/`tee`）、包装器（`timeout`/`nohup`）、复合命令与子 shell 尝试写入，均应被拒或进入人工确认——acceptEdits 会自动放行部分文件系统命令（`mkdir touch mv cp sed` 等），须逐项实测 deny/ask 是否仍然生效；
   - 负例若被自动放行：本候选不得启用，改按 plan §4.1 第 7 项补路径级 Bash deny/ask 并重新测试。
2. **T01b 通过**：`disableAutoMode`/`disableBypassPermissionsMode` 在新会话、恢复会话、模式切换下实际生效（目标固定版本下 auto 对普通/复合/子 shell 命令均执行 ask）。
3. 以**新版本发布**方式启用：复制为 `settings.json` → 提交（含 CHANGELOG/PATCH 登记）→ 打 tag → 重启会话并跑 `/ra-audit Rnn canary`。不得直接覆盖生效配置。

### 为什么不现在启用

本机 Claude Code 2.1.247 的 acceptEdits 文件命令自动放行范围未在本仓库实测；在验收完成前切换默认模式违反 plan §4.1 第 1 项（"只有 T01a 的正例与负例均通过，才切到 acceptEdits"）。当前交付采用回退路径：`default` + 精确 Edit/Bash allow（见 `PATCH-v2.4.md` §B1）。
