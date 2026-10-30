# PATCH v2.5：结论版本层与框架修复（2026-10-30）

> 源流：`demo` → `demo-fixed` → 本包 v2.3 → v2.4-B0 → v2.4-B1 → **v2.5**。
> 依据链：km2a-ra-hzj 轨迹审计（ratk v0.3，37 findings，2026-10-29/30）
> → `../trajectory_analysis/ra2a-lite-fix-proposals.md`（P0×3/P1×6/P2×3）
> → `../trajectory_analysis/l3-lite-conclusion-versioning.md`（设计）+ `-decision.md`（定稿）
> + `l3-lite-implementation-plan.md`（采纳裁定：拒收 historical_ref 语法；R8 分文件；
> 快照五字段；执法件落点；脚本自保护）。本 PATCH 只登记实例层修改。

## 1. 修改清单（14 个文件）

### 新增（6）
| 文件 | 作用 | 约束 |
|---|---|---|
| `research/ledger/results.jsonl` | RES 实验判定账本（创世行） | append-only；免 CR（派生事实） |
| `research/memory/conclusions.jsonl` | 语义结论版本账本（创世行） | append-only；行必带 approval_ref（R8） |
| `research/scripts/res_extract.py` | RES 唯一写入器 | 无路径参数；输出硬编码；flock；禁猜档 |
| `research/scripts/commit_conclusion.py` | conclusions 唯一写入器 | 锁内分配 v/content_hash；R8/Q1/P1-4/P1-5 断言 |
| `research/scripts/review_queue.py` | 受影响清单生成器 | 仅轮次号参数；输出固定当轮 work/ |
| `research/hooks/guard_writes.py` | PreToolUse 守卫 | 受保护路径拦截；decision 前置门；spawn 记账 |

### 修改（8）
| 文件 | 变更 |
|---|---|
| `research/PROTOCOL.md` | §3 结论引用 ID@vN；§5 表 0/A 判据；新增 §5.3；§9 批准语法族谱+非 auto；§10 表两行替换+scripts 保护；§11 词表/NR-draft/编号断言；§12 版本地址 |
| `research/templates/meta.yaml` | conclusions_snapshot 五字段 + ledger_protection |
| `research/templates/erc.yaml` | hypotheses 列表（P1-6）+ identifiability 节（P2-10） |
| `research/templates/cr.md` | supersedes/relations/band_source + approval_ref/conclusion_addr |
| `research/templates/decision.md` | hypotheses 字段 + 批准表增列 |
| `research/templates/brief.md` | §0.5 上轮研究员质疑节 |
| `.agents/skills/ra-memory`、`ra-round` | 词表自检/commit_conclusion/单提交原子化；开轮三检+快照+A 阶段 res_extract+brief 质疑节+锁定后 review_queue |
| `.claude/settings.json`、`.codex/hooks.json`、`.codex/rules/ra.rules` | deny×7/allow×3/PreToolUse×2；Codex 镜像+5 规则 |
| `ra2a_lite_8xa100.md` | §3 chattr 步骤；§5 全文同步（5 文件+erc 块）；§5.10 新件节；§11 v2.5 登记 |

## 2. 依据映射（问题 → 修复）

| 审计发现（km2a） | 修复条目 |
|---|---|
| R04 缺 P1/P34/P5 仍出决策（V×5）；6 轮仅 2 轮跑过 ra-audit | **P0-1**：guard_writes 的 decision 前置门 + PROTOCOL §9 偏离语句 |
| written_to 7/72、产物主会话转写、merged.md | **P0-2**：ra-round 输出指令不变 + spawn/stop 对账底账（见 P0-3）；审计断言承 ratk D1.3/D2.5 |
| 15 条空 agent_type；maxTurns 用尽路径零记账 | **P0-3**：guard_writes spawn 侧记账入 events.jsonl（kind:spawn），与 SubagentStop 对账 |
| R04 治理会话内 fork×2 | **P1-7**：开轮自检增 FORK_SUBAGENT/DISABLE_AUTO_MEMORY 实测 |
| CR-R02-03 把 no_diff 档写成 refuted（H-003 案） | **P1-4**：状态词表 + band_source + commit_conclusion 升格拒绝（ratk D8.10 同源逻辑） |
| H-003 编号 17 分钟换编；K-005 悬空 | **P1-5**：commit_conclusion 编号断言；版本地址消歧 |
| R04 decision/brief 零假设引用 | **P1-6**：erc/decision hypotheses 字段 |
| NR-005 候选落空无痕 | **P1-8**：NR-draft 入 proposals，改判必处置 |
| 批准变体 m×5；auto 效力靠项目自建 | **P1-9**：§9 语法族谱 + 非 auto 规则升入 PROTOCOL |
| 天花板效应靠研究员人工发现 | **P2-10**：ERC identifiability 节（no_diff 解释边界） |
| R04 只能现场问"root 恢复后自动启动？" | **P2-11**：偏离语句纳入族谱（条件授权的规范形态） |
| deny 覆盖不全；ev 叙述式漂移 | **P2-12**：deny×7；§3 版本引用语法 |

L3-lite 四决策（定稿+裁定）：Q1 递增号+hash+锁内事务 → commit_conclusion；Q2 五类+RES 分文件（R8 修订）→ 两本账；Q3 三档（拒收 historical_ref）→ review_queue；Q4 原子提交+轮中冻结+五字段快照 → §5.3+meta.yaml。执法分层（D-2/D-3/D-4）：hook 前置 + deny/rules + **degraded**（本机 chattr 不可用，git 对账补偿）+ 脚本无路径参数。

## 3. 验证（update/v2.5-verification.md 全录）

冒烟/金丝雀（2026-10-30，全部通过）：res_extract 拒参数；review_queue 拒非轮次参数；commit_conclusion 拒空 approval_ref（R8）+ 升格拒绝 + 版本断言；guard 拦 Edit/Bash-redirect、放行白名单；spawn 记账入 events.jsonl。

## 4. 已知边界

- 本机无 CAP_LINUX_IMMUTABLE → **ledger_protection: degraded**（lsattr 无 a 位）；补偿=git 对账（开轮断言旧行零变更；ratk D6 扩展）。研究员可在终端 `sudo chattr +a …` 升级为 os-append-only。
- Codex 的 PreToolUse 事件支持以其 CLI 实测为准（hooks.json 已镜像；不受支持时由 rules + degraded 对账兜底）。
- 审计侧（ratk）D8.10/D8.11 已可直读两本账做离线核查；项目内断言在 commit_conclusion/guard_writes。

## 5. 回滚

单提交（`git revert <v2.5 提交>`）即可整体回退；两本账仅含创世行与一条冒烟 spawn 记录，无科研内容损失。
