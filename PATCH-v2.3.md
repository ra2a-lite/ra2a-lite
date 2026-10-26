# PATCH：demo-revised 相对原版 demo 的全部修改与依据

> 单提交重建版（2026-10-23）。源流：`../demo`（原版）→ `/data/wangshirui/ra2a/demo-fixed`（修复与验证的过程档案，其 git 历史含全部逐笔证据）→ **本包**（v2.3 修复全量 ＋ auto mode 放行变体，单提交重建）。
> 规范层级：`../ra2a_261021.md`（全量规范）→ `ra2a_lite_8xa100.md`（Lite 项目包，本包直读规范）→ 本包。
> 评审证据链：同目录 `conformance-final-verdict.md`（七轮评审定稿报告）；逐提交级过程见 demo-fixed 的 git log。

---

## 1. 修改清单

### 1a. 仓库级（原版 demo 缺失的安装项，Lite §3 第 1/3/6/7 步）

| 项 | 原版状态 | 本版 | 依据 |
|---|---|---|---|
| git 仓库 | 不是 repo | `git init` 单提交重建 | Lite 的预注册锁定、幂等账本、审计（C9/C10/C13）全部依赖 git——原版 `launch.sh`/`ra-round` 的锁定检查会直接失败（定稿报告 §2.9 安装项 1） |
| `.gitignore` | 不存在 | `runs/**/*.{pt,pth,bin,safetensors}`、`checkpoint*/`、`.claude/settings.local.json` | Lite §3 第 6 步；**必须先于首提** |
| `.claude/skills` 链接 | 不存在（六个技能加载不到） | `ln -s ../.agents/skills .claude/skills` | Lite §3 第 3 步 |
| `research/ledger/*.jsonl` | 携带原 demo 定制会话记录 | 清空 | 包应全新开始；原值在 `../demo/` 与 demo-fixed 存档 |
| 证据文档 | 无 | `conformance-final-verdict.md` ＋ 本 PATCH | 自含证据链 |

### 1b. 文件级（实现缺陷修复；缺陷编号 F*/D* 均指向 `conformance-final-verdict.md` §2/§3）

| 文件 | 原版 → 本版 | 依据（缺陷 → 根因） |
|---|---|---|
| `research/templates/launch.sh` | ① `__run` 分支位于全部检查**之前**且不写 STARTED → 分支最前面加**三重前置令牌**（参数非空＋`.token` 存在非空＋内容一致；hex 令牌由 `start_exp` 以 `printf '%s'` 无尾换行写入并随 tmux/nohup 传入）。② 启动只 `grep status: approved` → 新增 `check_approval()`：python 解析账本，锚定正则（覆盖 `批准 R03:` 与 `批准(RL3) R03:`，"不/勿/别/驳回"前导判负）＋ `permission_mode ≠ auto` ＋ 批准 ts 早于锁定提交 ＋ 实验清单全覆盖 | **F1**（高）：`__run` 可绕过启动者/预注册/批准/幂等四道检查并 `export CUDA_VISIBLE_DEVICES`，且经"Edit allow＋python allow"构成**零弹窗**链；简单令牌比较存在"空对空"漏洞（无参＋无 `.token` 两侧皆空，实测复现）。**F6**：不核验批准原文，与 F2 叠加成完整伪造链。C9/C11 对无 STARTED 的直调**空真失明**（已补 C15） |
| `research/hooks/ra_log.py` | `ra:out` 正则允许任意 `Rnn/**/*.md` 且 hook 写入不经权限系统 → 按 `agent_type` 的目标路径白名单（**fail-closed**：空串→`rejected:agent_type_missing`；主会话文件 decision/brief/p2_broadcast 等一律拒绝）；默认休眠，`research/hooks/.whitelist_on` 存在才生效 | **F2**（高）：子代理可伪造 `decision.md`，或预占 `p1/analyst.md` 使真产出变 `.dup` 且 C2 审计的 sha256 比对恰好通过。**实测**：原账本子代理记录 `agent_type` 均为空串——故 fail-closed＋K9 前置（见 §4） |
| `.claude/settings.json` | ① `Bash(python3 research/rounds/*)` 在 allow → 移到 **ask**；② `Read(./runs/**/.token)` deny。**auto mode：本变体经研究员 2026-10-23 裁决放行**（已声明偏离，影响登记见 §2.3；demo-fixed 存档版为禁用态并实测生效） | ① **P0-1c**：掐断 F1 的零弹窗 python 链（其硬门效力依赖 auto 禁用，本变体下已降级，见 §2.3）。② ①层令牌防读回（沙箱不可用，见 §4） |
| `.agents/skills/ra-audit/SKILL.md` | C1 顺序链缺 A/P2、无压缩检查；C9/C11 空真；无 C2b/C15/K9 → 补齐：C1 链 `A<P1<P2<…<lock`＋compact 兜底；**C2b**（p1 记录的 agent_type 匹配角色，空串 FAIL）；**C15**（每个 DONE/FAILED/ABORTED 前必有同 exp_id 的 STARTED）；C14 检查"批准语句记录非 auto"；**K9** canary | **P0-1d**、**P1-1**、**D10**、P0-2 审计兜底 |
| `.agents/skills/ra-round/SKILL.md` | ① 开轮自检无账本检查 → 加"批准语句记录均非 auto"；② ⏸.6 找不到批准记录时"注明'无 hook 记录'继续" → **fail-closed 终止**＋核对批准记录 `permission_mode ≠ auto`；③ P2/P6/P7 无压缩检查 → 进入前实时查 `events.jsonl`（`kind=compact`/`source=compact`）；④ 0.3 补填 runtime 与 models | ② 原软回退违反 C-APPROVAL-003（spec:1599 "dispatch 之前必回账本核验"）。③ **P1-1**：压缩判定属回合状态机（spec:930）。①④ **P0-2② / P1-2** |
| `.agents/skills/ra-init/SKILL.md` | 第 8 步"记录运行时版本"无落盘位置 → 明确写入 `research/rounds/R00/meta.yaml` | **P1-2**：否则 C14 无审计对象 |
| `research/templates/erc.yaml` | abort_conditions 仅 3 类 → 注释补 `safety_or_ethics`、`futility` | **D10**：spec:1036-1039 示例为 4 类 |
| `ra2a_lite_8xa100.md` | §5 头部加横幅指向本文件 | "生成文件与 §5 不得漂移"规则，以登记差异方式履行 |

---

## 2. auto mode 专章

### 2.1 现状

**放行**（经研究员 2026-10-23 裁决，已声明偏离）。settings.json 无 `disableAutoMode` 键；CLAUDE.md 声明"批准语句仍须在非 auto 权限下输入"。规范的默认立场为禁用（见 2.2），本包为知情偏离（影响见 2.3）。

### 2.2 为什么规范的默认立场是禁用（决策背景）

- **规范立场**（`../ra2a_261021.md`，引用均经全文语境核对）：R10（:101）"概率性放行不能替代确定性 enforcement"；§11.1（:1179）"auto mode 不启用"；§11.6（:1360）`permission.auto_mode: {allow: false}`；§11.2（:1189）可作门❌；§10.2（:1111）与 SDK 示例（:1084）治理会话以 dontAsk 运行、"禁止 bypassPermissions 与 auto mode"；§2.2（:200/:288）auto mode 被列为开出旁路的平台能力。
- **架构原因**：闸门分两层——deny 层（不受 auto 影响，deny＞分类器）与 **ask 层**（auto 把该层交给概率分类器）。禁用态下 ask 层是真门（demo-fixed 存档版实测：`disableAutoMode` 生效两次确认）。
- **Lite 语境**：全量架构中宿主全部会话均 dontAsk；Lite 单会话混合，项目级键是唯一抓手。

### 2.3 放行 auto 的影响（知情登记）

**不受影响的修复**（deny 层＋脚本内校验＋hook 层，与权限模式无关）：

| 修复 | 机理 |
|---|---|
| heldout / 评测脚本 / 危险 git / `.token` 读取的全部 **deny** 规则 | deny 优先于 auto 分类器（审计 K4 实测） |
| `__run` 三重令牌校验、`check_approval` 批准核验 | bash 脚本内执行，不看权限模式 |
| ra:out 白名单（hook 层）、C15/C2b 审计、compact 阶段门、meta 填写 | hook/技能层 |

**受影响的修复**（ask 层——确认由概率分类器接管）：

| 项 | 后果 |
|---|---|
| **P0-1c（python3 ask）** | **失效**。F1 的 python 路径重开：Edit allow 建 py → python 读 `.token`（Read deny 管不到 python 的 `open()`）→ 带令牌调 `__run`。**令牌退回"减速带"，F1 的完整闭环在本变体下不成立**——知情接受的降级 |
| 模式 B 启动审批（`bash launch.sh` 的 ask） | 分类器可能自动放行；**模式 A（研究员在终端运行）不受影响** |
| `git commit` / decision.md 写入 / 保护文件编辑确认 | 同样软化；兜底靠 git 审计（历史可查）与 hook 白名单 |

**保留的缓解**：批准语句仅在非 auto 权限下输入才有效——⏸.6 核对与 `launch.sh` 的 `check_approval` **双重拒绝 auto 批准**；deny 层全部照常；ra:out 白名单照常。

### 2.4 若要改回禁用（恢复步骤）

1. `.claude/settings.json` 的 permissions 中加回 `"disableAutoMode": "disable"`（置于 `disableBypassPermissionsMode` 之后）；
2. CLAUDE.md 第 7 行改回"不使用 bypassPermissions 或 auto 模式，不用后台任务。"；
3. ra-round 开轮自检改回"上一 lock 以来 human_inputs 无 auto 输入"；ra-audit C14 改回"无 auto 输入"子项；
4. 本文件 §2.1 改为禁用并登记变更记录；
5. 验证：新会话切 auto 被拒；python3 恢复弹确认（P0-1c 恢复硬门）；复跑 `/ra-audit R00 canary`。

（等价于直接采用 demo-fixed 存档版的禁用态。）

---

## 3. 验证状态（2026-10-23）

- **单元**：hook 白名单 6 用例、launch.sh 6 用例全过；K8 启动者守卫实测拦截（证据采自 demo-fixed，代码与本包一致——本变体仅 settings/CLAUDE/技能措辞的 auto 相关处不同）。
- **集成**：`/ra-audit R00 canary` **FAIL 0**、K1–K9 全绿（采集自 deepgo-labv2 同源治理层，**auto 禁用态**）。**本变体交付前建议复跑一次 canary**：预期 K 项仍全绿（deny 层与权限模式无关），并加验一条——auto 会话输入批准语句 → `check_approval` 拒绝。
- **运行时**：ra:out 端到端成功；`ra:out` 非首行时主会话按规则兜底；后台/workflow 子代理不产生 SubagentStop 记账（spec §8.1 盲区活体证据——治理阶段坚持前台子代理）。

## 4. 遗留与边界

| 项 | 状态 | 说明 |
|---|---|---|
| K9 / 白名单激活 | **休眠交付**（`.whitelist_on` 不存在，hook 仅记账不拦截） | 白名单激活前提是 K9 在**目标环境**验证（`agent_type` 非空——原版账本的空串记录是前车之辙）；接收方首次使用时前台调用任一 ra-* 子代理确认后 `touch research/hooks/.whitelist_on` |
| P1-3 沙箱 | 冻结 | 宿主无 bwrap（实测）；令牌防读回为降级组合，且在 auto 放行变体下进一步弱化（见 §2.3） |
| P2 裁决项 | 待研究员 | D1（治理子代理含 Bash/Write 的显式声明）、D4/D5（ERC hash 绑定）、D7（P5 评分设计）——见定稿报告 §3 |
| Codex 侧 | 未适配 | `.codex/` 保持原版；rules 中 python 本就 prompt |
| 账本 | 已清空 | 原值在 `../demo/` 与 demo-fixed 存档 |

---

## 5. v2.4 处置记录（2026-10-26 追加；上文历史判断保留原文，不回写）

| 本文件位置 | v2.4 处置 | 依据 |
|---|---|---|
| §2.1"现状：放行" | **已中止**：settings.json 已写入 `disableAutoMode: "disable"`（即 §2.4 恢复步骤 1）。本次为 B2 隔离验收与目标版本回归通过前的过渡禁用；届时恢复 auto 须以新版本发布并登记，不回改本节 | update/final_modification_plan.md §4.1 第 6 项、§2.1 PR02/D06；实施记录见 PATCH-v2.4.md |
| §2.3"分类器可能自动放行""零弹窗链"等表述 | 语义更正（D03）：按当前官方规则优先级，显式 ask 高于 auto 分类器，"切到 auto"不能当作移除弹窗的手段；本机 2.1.247 的逐项 UI 行为仍未核验 | update/final_modification_plan.md §2 D03；research/audits/permissions-2026-10-26.md §2 |
| §4"Codex 侧……rules 中 python 本就 prompt" | 事实更正（D05）：当前 `.codex/rules/ra.rules` 没有通用 Python prompt，离线 execpolicy 查询亦未命中；Codex 侧配置在 v2.4 未改动 | update/final_modification_plan.md §2 D05；research/audits/permissions-2026-10-26/work/policy_checks.json |
| §4"K9 / 白名单激活：休眠交付" | 状态不变（`research/hooks/.whitelist_on` 仍不存在）；D09 已实测核对标记文件确实缺失，与本文描述一致 | update/final_modification_plan.md §2 D09 |
| §1b 中 settings.json、CLAUDE.md 两行 | 已被 v2.4 进一步修改（精确 allow、只记账 hook、权限模式章节、auto 禁用）；当前全文一律以仓库实际文件与 Lite §5 为准 | PATCH-v2.4.md §4；ra2a_lite_8xa100.md §5 横幅 |
