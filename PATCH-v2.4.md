# PATCH-v2.4：修改基线锁定（B0）＋ 白天减负与规则语义修正（B1）＋ 版本机制

> 版本：**v2.4**（2026-10-26）｜基线：v2.3 @ `e85cd92`（tag `v2.3`）｜实施对象：`update/final_modification_plan.md`（v2.4-plan-2）的 **B0 与 B1**；**B2–B4 未实施**，门条件见该方案 §9。
> 版本索引：`CHANGELOG.md`｜一致性校验：`research/runtime/checks/`｜验收状态：见 §7（T01a/T01b 待研究员实测）。

---

## 1. 授权记录

- 2026-10-26 研究员会话指令（原文大意）："结合 update 内的 final_modification_plan 对 demo-revised 进行更新，先完成 B0、B1，希望能搞成有版本号的、可回溯的、有版本说明的（需不需要 fork 由 assistant 决定）"。
- 按 plan §9 授权门（PR08 修订后）：B0 为纯读取与产物登记，按 RL0 执行；B1 涉及 `.claude/settings.json`、`CLAUDE.md`、`AGENTS.md`、`research/PROTOCOL.md` 的修改，属"该批具体文件范围"的授权，由上述指令给定；实际写入时每份受保护文件均逐项通过权限系统 ask 确认。
- 本文不代写任何研究批准语句；如需将本批补记为正式 `批准(RL3)`，由研究员亲自输入后追加到 §10。

## 2. fork 决定：不另建 fork

1. demo-revised 本身就是 demo 的演进分支（源流见 PATCH-v2.3 头部）；其 `research/ledger/`、`runs/`、`memory/`、`audits/` 是**只增的权威记录**——再 fork 会把权威记录一分为二或中断连续性。
2. AGENTS.md 禁 `git reset/restore/rebase/amend`：本仓库的回退模型本就是"前向修复（发新版本）"，与 git 历史 + tag 的 append-only 回溯一致；目录级 fork 不提供额外安全边界（同样的文件在 fork 里照样可改）。
3. 可回溯性由四层承担：**分批提交**（每批一个可审阅 diff）→ **annotated tag**（`v2.3`/`v2.4`）→ **每版 PATCH-vX.Y.md**（修改、依据、验收状态、回退步骤）→ **CHANGELOG.md** 索引。
4. 历史过程 fork（`../demo-fixed`）的档案职能由本仓库提交 `0611d8c`（材料入库）与 PATCH 引用承担。

后续版本一律在 master 上以"提交 + tag + PATCH + CHANGELOG"发布。若某批需要长期并行试验（如 B2 runtime 原型），届时随该批授权再议分支策略。

## 3. B0：修改基线与部署能力登记（产物）

| 产物 | 位置 | 内容 |
|---|---|---|
| 基线清单 | `research/audits/permissions-2026-10-26/work/b0-baseline/manifest.{json,md}` | 74 个治理/受保护文件 sha256；git HEAD=`e85cd92`；Claude 2.1.247 / Codex 0.164.0；外部权限源（用户层 `~/.claude/settings.json` 已登记哈希，无管理层配置）；`.claude/skills` 符号链接登记；账本 4 文件快照（只增，不进 verify） |
| 漂移注册表 | 同目录 `lite_sync_before.json` | Lite §5 一致性漂移集 = **恰为 PATCH-v2.3 §1b 登记的 8 个文件**（实证脚本与 v2.3 登记一致） |
| 基线脚本 | `research/runtime/checks/baseline_manifest.py` | 重新生成清单 / `--verify` 回归比对（changed/added/removed） |
| 一致性脚本 | `research/runtime/checks/lite_doc_sync.py` | §5 代码块 vs 实际文件逐块比对（38 对）；`--apply` 仅限 verbatim 模式，受保护模板只登记不自动改写 |

能力登记（静态证据，**运行时行为未验收**，沿用 plan §3 能力表的边界）：2.1.247 二进制内存在 `PermissionRequest`、`Notification` hook 事件名与 `disableAutoMode` 设置键；`--permission-prompts none` 在本机 help 未提供（PR06，不使用）。

## 4. B1：修改清单（文件级）

| 文件 | 修改 | plan 依据 |
|---|---|---|
| `.claude/settings.json` | ① `permissions.disableAutoMode: "disable"`（过渡期禁 auto）；② `defaultMode` 保持 `default`（acceptEdits 未达启用条件，走回退路径）；③ allow 新增 `Edit(./update/**)`、`Edit(./research/runtime/checks/**)`；④ allow 新增约 30 条**只读** Bash（ls/cat/grep/rg/stat/file/diff/jq/which/realpath/readlink/basename/dirname/uname/nproc；git tag 列表态、branch --show-current、stash list、remote/-v、describe/rev-list/cat-file/blame）；⑤ ask 显式新增 `git tag -a *`、`git tag -s *`（打标是写操作）；⑥ 新增 `PermissionRequest`、`Notification` 两条 hook，调 `ra_log.py perm_request|notify` 走既有 else 分支写 `events.jsonl`——**只记账、不返回放行决定**；⑦ deny 与其余 ask 原样保留（含 python3/rounds、bash/rounds 整类 ask） | §4.1 第 1/2/3/5/6 项 |
| `.claude/candidates/`（新） | `settings.acceptEdits.draft.json`（与生效配置唯一差异 `defaultMode`）＋ `README.md`（启用前置=T01a/T01b，启用方式=新版本发布） | §4.1 第 1 项 |
| `CLAUDE.md` | 新增"权限模式（v2.4 起）"章节：临时禁 auto 及恢复条件、bypass 永禁、default+精确 allow 交付形态、acceptEdits 候选未启用、"切到 auto"按钮≠研究批准、只记账 hook 不构成批准来源 | §4.2 |
| `AGENTS.md` | "工作方式"新增两条：工具确认 vs 研究批准（RL0 不需逐次工具确认；弹窗是独立工具门）；草案与基线（配置开关交付、默认值保持基线；B2 后草案入隔离副本；CPU 自检 ≠ CPU 研究训练/评测授权） | §4.2 |
| `research/PROTOCOL.md` | `protocol_version: lite-1.0 → lite-1.1`；§9 表后新增"v2.4 注"（同上三点语义） | §4.2 |
| `ra2a_lite_8xa100.md` | §5 十个代码块经 `--apply` 刷新为实际文件（38 对全部 0 漂移）；§5 横幅由"v2.3 差异登记"改为"已同步+校验方式"；§2"三次弹窗"承诺改写为"人工决定点+工具确认清单"；§5.7 STATUS 模板新增"包版本"字段；§5.18 注明补丁已内含；§6.7 对照表 hook 计数 4→6 | §4.2、D19 |
| `PATCH-v2.3.md` | 追加 §5"v2.4 处置记录"（auto 中止、D03/D05 更正、K9 状态核对）；原文不回写 | §8、D19 |
| `research/STATUS.md` | 新增"包版本"字段；更新治理审核/方案对账索引 | §8 |
| `update/final_modification_plan.md` | frontmatter `status` → `b0_b1_applied_v2.4`；§11 增应用记录行 | 回溯用 |
| `CHANGELOG.md`、本文件 | 新增：版本索引与本版说明 | 版本机制 |

**未改**（有意）：`.codex/**`（夜间入口与事件适配属 B3；B1 不做无验收的配置漂移，D05 仅更正文档表述）；`research/hooks/**`（deny 编辑，事件收集改造属 B2）；技能、模板、评测、账本、正式记忆；模型选型与 rubric。

## 5. B1 完成标准对照（plan §4 末）

| 标准 | 状态 |
|---|---|
| 交付形态：acceptEdits 验收版 **或** default+精确 Edit allow | ✅ 后者（回退路径）；普通源码编辑（update/、runtime/checks/、既有 rounds/audits/proposals 等）不再逐次弹窗 |
| 保护命令的自动许可不比基线宽 | ✅ deny 集合不变；新增 allow 全部为只读命令或已登记可写目录 |
| 临时禁 auto / bypass 禁用实际生效 | ⚠️ 键已写入且有静态支持证据（demo-fixed 实测先例 + 二进制键名）；**运行时有效性待 T01b**（§7） |
| 未隔离解释器保持原边界 | ✅ 未新增 `Bash(python3 *)`/`pytest`/`find`；`python3 research/rounds/*` 仍 ask |
| 轮次 Python ask 仍在（B3 才移除）；不承诺 CPU 分析零弹窗 | ✅ 如实保留并登记 |

## 6. 已知边界与残留风险

1. **重定向写入残留**：被 allow 的只读命令（含 v2.3 既有的 tail/head/sha256sum 等）配合 `>`/`>>` 可写文件，路径级 Edit deny/ask 管不到 Bash 重定向。此为 v2.3 即存在的已知缺口，v2.4 **未扩大**（新增 allow 不带来新写入能力）；兜底=git 审计＋B2 隔离；T01a 负例清单包含重定向。
2. **PermissionRequest/Notification hook**：事件名与键在 2.1.247 二进制内存在（静态证据）；是否如期触发、载荷含哪些字段未验收。异常时回退=删除 settings.json 中这两条 hook 条目（不影响其余功能）。
3. **弹窗采集字段不全**：plan §3 要求的工具名/命中规则/角色/阶段/有效模式/结果/耗时，当前只能记到平台载荷自带部分；补齐属 B2 事件收集（collect.py）。
4. **acceptEdits 文件命令自动放行范围**（mkdir/touch/mv/cp/sed 等）在 2.1.247 未实测——候选配置因此不启用（`.claude/candidates/README.md`）。
5. `research/runtime/checks/` 为 agent 可改写源码，**有意不加执行 allow**：允许 agent 任意改写的脚本不应免确认执行（审核 §6.3）。
6. `research/runtime/` 根层未来将放 B2 受信程序（approval/finalize/collect），**未**加入 Edit allow，保持逐次确认。

## 7. 待研究员验收清单

**T01b（先做——验证本版已生效配置）**
1. 重启会话 → 模式切换（Shift+Tab 或 /permissions）：auto 应不可选（`disableAutoMode` 生效），bypass 不可选；
2. `--resume` 恢复会话重复第 1 步；
3. 触发一个 ask 项（如 `git commit`）确认仍弹窗；查 `research/ledger/events.jsonl` 末尾出现 `kind=perm_request` 记录；
4. 若 auto 仍可选或 hook 报错：按 §8 回退并登记。

**T01a（合成目录——验收候选配置，之后才谈启用 acceptEdits）**
1. `mkdir -p /tmp/ra-t01a`，仿造 ledger/charter/memory/.claude/.codex 目录结构（不使用真实文件）；
2. 分别在 default 与候选 acceptEdits（临时项目目录试验）下：正例=普通源码 Edit/Write 不弹窗；负例=对保护路径用 `sed -i`/`cp`/`mv`/`touch`/`>`/`>>`/`tee`/`timeout` 包装/`&&` 复合/子 shell 写入 → 均应被拒或弹窗；
3. 全部通过 → 按 `.claude/candidates/README.md` 以新版本发布方式启用；任一负例被自动放行 → 不启用，按 plan §4.1 第 7 项补路径级 Bash deny/ask 后重测。

## 8. 回退步骤（均为前向发布，不使用被禁的 git 操作）

- **恢复 auto**（反转本版过渡措施，前提=B2 隔离与目标版本回归通过）：settings.json 删除 `disableAutoMode` 行；CLAUDE.md"权限模式"章节改回一行"不使用 bypassPermissions 或 auto 模式，不用后台任务"；以 `v2.4.1` 发布登记（即 PATCH-v2.3 §2.4 的逆操作）。不得仅因弹窗烦恼回退——那是 B1 的其余减负项与 B3 的职责。
- **整体回退本版**：以"v2.4.1 回退版"前向发布，文件内容取 `git show v2.3:<path>` 恢复。
- **hook 异常**：仅删除 `PermissionRequest`/`Notification` 两条 hook 条目。

## 9. 版本机制（自本版生效）

- 版本号 `vX.Y`；一个获准批次（B0/B1/…）或一组同类获准修改 = 一个版本；方案文档修订用 `plan-N` 后缀（如 v2.4-plan-2），不占包版本。
- 发布 = 分批提交 + annotated tag（`git tag -a vX.Y`）+ `PATCH-vX.Y.md` + `CHANGELOG.md` 条目；STATUS.md"包版本"字段随发布更新。
- 一致性纪律：改动 §5 收录的文件后必须 `lite_doc_sync.py --check` 通过（T11）；基线回归用 `baseline_manifest.py --verify`；历史 PATCH/CHANGELOG 条目只增不改。

## 10. 验收与后续门

- 本版验收状态：B0 完成（§3 产物齐）；B1 已交付配置与文档，**T01a/T01b 待研究员实测**（§7）。
- B2 开工前置：批准入口与部署设计决定（plan §5.0/§5.2——研究员需明确接受宿主终端签署习惯）＋容器后端隔离验收（T03）。
- B3 前置：B2 的 T03–T07 通过；B4 另立资源执行协议修订。
- （正式批准补录区：无）
