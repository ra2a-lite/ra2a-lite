# RA2A-Lite

RA2A-Lite 是一套放入模型项目仓库使用的研究迭代治理与协作文件包，面向 Claude Code / Codex。它把研究流程、角色边界、权限规则、hooks、证据引用、预注册和审计模板放在同一个可回溯的 Git 仓库中。

> 当前版本：**v2.5**（2026-10-30）  
> 当前维护分支：`stable`

## 这是什么

- 研究设计与结果分析的协作框架，不是训练框架，也不包含模型代码或数据集。
- 适配单机 8×A100 的项目模板；具体项目仍需由研究员填写数据、指标、基线和训练入口。
- 默认把训练、评测和 GPU 作业留给研究员在终端执行；智能体负责设计、分析、记录和审计。
- 详细安装与文件生成说明见 [`ra2a_lite_8xa100.md`](ra2a_lite_8xa100.md)。

## v2.5 当前内容

v2.5 引入结论版本层和对应的框架保护：

- `research/ledger/results.jsonl`：实验判定账本；
- `research/memory/conclusions.jsonl`：带 `approval_ref` 的语义结论版本账本；
- `research/scripts/res_extract.py`、`commit_conclusion.py`、`review_queue.py`：受保护的唯一写入路径；
- `research/hooks/guard_writes.py`：对受保护路径、决策前置门和 spawn 记账的守卫；
- Claude / Codex 配置、技能、协议和 Lite 主文档同步到 v2.5 语义。

版本变更、依据、验证结果和回滚方式见 [`PATCH-v2.5.md`](PATCH-v2.5.md)，金丝雀记录见 [`update/v2.5-verification.md`](update/v2.5-verification.md)。历史版本索引见 [`CHANGELOG.md`](CHANGELOG.md)。

当前已知边界：本机没有 `CAP_LINUX_IMMUTABLE`，账本保护等级为 `degraded`，通过 Git 对账补偿；Codex 的 PreToolUse 行为仍以部署版本实测为准。v2.5 没有执行训练或评测轮次。

## 快速开始

1. 先读 [`AGENTS.md`](AGENTS.md)、[`CLAUDE.md`](CLAUDE.md)、[`research/STATUS.md`](research/STATUS.md) 和 [`research/charter.md`](research/charter.md)。
2. 按 [`ra2a_lite_8xa100.md`](ra2a_lite_8xa100.md) 第 3–5 节把文件包安装到目标模型仓库。
3. 在目标仓库完成 `/ra-init`，确认项目卡、数据边界、指标和训练入口后再开始轮次。
4. 每轮使用 `/ra-round Rnn`；训练和评测由研究员按项目授权在终端启动。
5. 版本变化后先运行项目规定的 canary / audit，再进入下一轮。

本仓库本身只保存 Lite 文件包及其研究记录；不要把真实项目的模型权重、checkpoint 或测试集提交进来。`.gitignore` 已忽略常见 checkpoint 后缀，但新增数据路径仍需人工检查。

## 目录速览

| 路径 | 用途 |
| --- | --- |
| `ra2a_lite_8xa100.md` | 安装说明、文件模板和完整设计文档 |
| `.agents/skills/` | Claude / Codex 共用技能 |
| `.claude/`、`.codex/` | 角色、权限、hooks 与规则配置 |
| `research/` | 协议、状态、账本、记忆、审计和轮次模板 |
| `update/` | 方案、评审和版本验证材料 |
| `PATCH-vX.Y.md` | 单个版本的修改、依据、验收和回滚记录 |
| `CHANGELOG.md` | 只增不改的版本索引 |

## 版本维护规则

每次发布新版本时，按同一批次更新以下内容：

1. 新增 `PATCH-vX.Y.md`，写明修改清单、依据、验证状态、已知边界和回滚方式；
2. 在 `CHANGELOG.md` 追加一条历史记录，不改写旧条目；
3. 更新本 README 的当前版本和摘要；
4. 若研究流程状态也变化，同步 `research/STATUS.md` 的包版本字段；
5. 对 Lite 第 5 节收录的文件运行 `python3 research/runtime/checks/lite_doc_sync.py --check`；
6. 提交后创建 annotated tag，分支和 tag 一起推送到 GitHub。

建议的发布检查顺序：

```bash
git status --short --branch
python3 research/runtime/checks/lite_doc_sync.py --check
git diff --check
git log --oneline -5
```

版本采用前向发布：历史提交、tag、PATCH 和 CHANGELOG 保持可回溯；发现问题时新增修正版或使用 `git revert`，不改写已发布历史。

## 发布前检查

`research/ledger/*.jsonl` 会保存会话、批准和工具事件，可能含本机路径、会话标识或提示词。推送到公开 GitHub 仓库前，先确认这些记录符合你的公开范围；需要保留完整审计记录时，优先使用私有仓库。

## 许可证与来源

本目录当前未声明独立开源许可证。公开仓库前请补充你选择的许可证和第三方来源说明。
