# demo Conformance 两份评审对账与终局结论

日期：2026-10-23 ｜ 位置：`check/demo-conformance-final-verdict.md`

> **定稿声明（v2.3，2026-10-23，第七轮评审后）**：第七轮评审无任何新发现（纯复述第六轮结论），文档迭代就此**关闭**，不再有 v2.4。剩余开放项全部是运行时实测（§4 ❓ 六项、P3 三关、bwrap 解冻），只能由执行回答，不能由评审回答。执行入口：P3 第 1 步。

**输入**：
- 评审一（下称"原报告"）：`check/demo-conformance-report.md`（2026-10-22 16:52）
- 评审二（下称"复核"）：`check/demo-conformance-report-review.md`（2026-10-23 10:21）

**唯一裁判**：`生成demo用的prompt.md`（demo 的需求原文）、`ra2a_261021.md`（原型规范）、`demo/` 源码与 `research/ledger/*.jsonl` 当前事实。两份评审互不作为事实来源，只作为"问题清单"。
**核验方式**：每条断言重新读取源码/规范原文取证；账本计数以 2026-10-23 当前值为准（human 9 条、subagent_outputs 3 条、events 3 条）。

---

## 1. 对账总表

### 1.1 双方都提、结论一致（13 项成立 + 1 项部分）

F1`__run`旁路（核心）、F2 `ra:out` 无白名单（核心）、F3 auto 模式、F4 压缩无判定（缺口本身）、F5 meta 字段缺写入（缺口本身）、F6 launch.sh 不核验批准、D2 别名、D3 enforcement ③④⑤层缺失、D4 批准不绑 hash 无时效、D5 锁定顺序、D6 lite 评委数、D7 P5 顺序混杂、D8 账本可伪造、D10 模板/审计小缺口；D9 跨运行时不对称（复核降调，判 ⚠️）。

### 1.2 仅一方提出

| 来源 | 条目 | 终局 |
|---|---|---|
| 仅原报告 | F7（单层 `*` 疑似失效） | ❌ 不成立（见 §2.7） |
| 仅原报告 | 运行时观察（source=fork 会话说明） | ✅ 成立，复核确认 |
| 仅复核 | F1 深化：`Bash(python3 research/rounds/*)` allow 链绕过 ask；`__run` 不写 STARTED；C9/C11 空真失明 | ✅ 全部确认（§2.1） |
| 仅复核 | F2 边界：伪造需在 L 前随锁定提交；Python 直写可绕 hook 白名单 | ✅ 确认（§2.2） |
| 仅复核 | F3 计数更新 6→9；候选键名 `permissions.disableAutoMode` | 计数 ✅；键名 ❓（§2.3） |
| 仅复核 | 安装第 5 项 `.gitignore` 缺失、第 6 项 `/ra-audit R00 canary` 未跑 | ✅ 确认（§2.13） |

### 1.3 结论相反的争点（5 处，终局裁决）

| 争点 | 原报告 | 复核 | 终局 |
|---|---|---|---|
| F7 Bash 规则 `*` 是否只匹配一层 | 疑似静默失效 | 不成立 | **❌ 复核正确**：spec 把两套语义分开规定（§2.7 引文） |
| F1 中 `__run` 是否写 STARTED、C9 能否查出 | "写 STARTED"；"C9 能查出" | 不写 STARTED；C9/C11 不命中 | **复核正确**（源码引文） |
| F4 归类 | 未声明偏离 | 已声明风险（§7.2#9）但判定未实现 | **复核正确**（两处引文） |
| D1 归类与工具清单 | "已声明偏离"；"analyst/skeptic/verifier 带 Bash+Write" | 隐式选择未声明；verifier 无 Write | **复核正确**（源码引文） |
| D9 程度 | "Codex 版 read-only 都做不到" | 能力较弱需审批，非做不到 | **复核正确**（verifier.toml 自身指令引文）→ ⚠️ 部分成立 |

---

## 2. 逐条核验（四档：✅确认 / ⚠️部分成立 / ❌不成立 / ❓无法核验）

### 2.1 F1（高）`__run` 内部入口绕过全部检查 —— ✅确认（以复核版为准）

**源码引文**（`demo/research/templates/launch.sh:13-19`）：

```bash
if [ "${1:-}" = "__run" ]; then            # 内部入口：在 tmux/nohup 中实际运行一个实验
  EXP=$2; GPUS=$3; SCRIPT=$4; DIR=runs/$EXP
  export EXP CUDA_VISIBLE_DEVICES=$GPUS
  set +e; bash "$SCRIPT" > "$DIR/train.log" 2>&1; rc=$?; set -e
  if [ $rc -eq 0 ]; then ev=DONE; else ev=FAILED; fi
  date -Is > "$DIR/$ev"; log "$EXP" "$ev" "$GPUS" "$(cat "$DIR/COMMIT")" "$rc"; exit $rc
fi
```

启动者检查在 `:21-28`、预注册检查在 `:30-36`，均在 `__run` 分支**之后**。`STARTED` 只由 `:43` 的 `start_exp`（`mkdir -p "$DIR"; date -Is > "$DIR/STARTED"`）写入——**`__run` 不写 STARTED**（原报告此点错误，复核正确）。

**零确认触发场景**（复核提出，核验成立）：
1. `settings.json:15` allow `"Edit(./research/rounds/**)"` → Edit 工具在 rounds 下新建 `x.py`，无确认；
2. `settings.json:21` allow `"Bash(python3 research/rounds/*)"` → 运行 `python3 research/rounds/R03/work/x.py`，无确认；
3. 脚本内 `os.makedirs("runs/R03-E1")` + `subprocess.run(["bash","research/rounds/R03/launch.sh","__run","R03-E1","0,1,2,3","research/rounds/R03/exp/R03-E1.sh"])` → `export CUDA_VISIBLE_DEVICES=0,1,2,3`（解除 GPU 隔离）并前台训练。全程零弹窗。
4. 事后审计失明：`ra-audit` C9（SKILL.md:18-19）"lock commit 时间早于每个 `runs/<exp>/STARTED`"与 C11（:24）"每个 exp_id 至多有 1 条 STARTED"在无 STARTED 时**空真通过**；只有人工注意到"有 DONE/FAILED 却无 STARTED"才能发现（现有检查项无此条）。

规范依据：ra2a_261021.md §8.5/:1602（C-PREREG-001：dispatch 前必须 lock+approval）、§11.7/:1449（"命令规则只看字符串，hook 只拦得住直接调用"——真正的墙在 OS/Effector，demo 没有）。

### 2.2 F2（高）`ra:out` 落盘无路径白名单 —— ✅确认（含复核补充的两个边界）

**源码引文**（`demo/research/hooks/ra_log.py:13`）：

```python
OUT_RE = re.compile(r"\A\s*<!--\s*ra:out\s+(R\d{2,}/[A-Za-z0-9_./-]+\.md)\s*-->")
```

`save_out()`（:36-52）只做 `..` 与"目标在 `research/rounds` 下"两项检查，无 `(agent_type, 阶段)` 白名单；hook 进程写入不经 permissions。两条攻击路径成立：伪造 `R03/decision.md`（配 `status: approved` 通过 `launch.sh:33` 的 `grep -q '^status: approved'`）；预占 `R03/p1/analyst.md` 使真产出变 `.dup-` 文件（:47-48）且 C2 的 sha256 比对恰好被伪造者自己的 SubagentStop 记录满足（C2 未绑定 agent_type）。

**边界一（复核提出，核验成立）**：`launch.sh:31` 要求 `[ -z "$(git status --porcelain -- "$RD")" ]`——伪造若发生在 L 之后且未提交会被挡；但正常流程 L 步是 `git add -A research`（ra-round SKILL.md:92），**L 之前伪造的文件会随锁定提交一并入库**，:31 与 :33 同时通过。前提不是削弱，是攻击成立的标准路径。
**边界二（核验成立）**：F1 的 python allow 链同样可**不经 hook 直写**任意 rounds 文件——修 `ra_log.py` 只堵 hook 这一条，根因是 D3（无沙箱/OS 边界）。

### 2.3 F3（高）auto 权限模式 —— ✅确认（计数更新；键名 ❓）

**引文**：`settings.json:12-13`：

```json
"defaultMode": "default",
"disableBypassPermissionsMode": "disable",
```

无任何禁用 auto 的键。**当前账本**：`human_inputs.jsonl` 9 条，`permission_mode` 全部为 `"auto"`（2026-10-23 实测输出 `['auto'×9]`；原报告 6 条是 16:52 时点，复核 9 条与当前一致）。规范 :1179："auto mode 不启用：auto mode 的分类器是概率性的，在受控工具上一律不启用。"
复核给出的键名 `permissions.disableAutoMode` 来自平台文档，**无法从裁判材料核验** → ❓，作为修复候选并需 K 类实测。

### 2.4 F4（中）压缩事件记账但无判定 —— ✅确认缺口；归类采纳复核

**引文一**（spec :930）："治理会话中一旦出现压缩事件，该会话承载的全部参与者本阶段都判 closure_broken。"
**引文二**（Lite :1657，§7.2 剩余风险 #9）："上下文压缩后协议被遗忘 ｜ 模型本身的局限 ｜ SessionStart 注入 STATUS；每个阶段都落盘；`last_phase` 可恢复 ｜ 低"——**风险确已声明**（原报告"未声明"归类错误）。
**缺口确认**：`settings.json:47` 挂了 PreCompact hook、`ra_log.py` 记账，但 `ra-audit` C1–C14（SKILL.md:7-29）与 `ra-round` 自检均无压缩检查项——规范要求的 closure_broken **判定未实现**。终局定性：已声明风险 + 判定缺失。

### 2.5 F5（低）meta 的 runtime/models 无写入步骤 —— ✅确认缺口；措辞采纳复核

**引文**：ra-round SKILL.md:24："按 templates/meta.yaml 写 meta.yaml：charter_blob 用 `git hash-object research/charter.md`；parent_lock_commit 从 STATUS.md 取"——仅两个字段有明确指令；ra-init SKILL.md 第 8 步"记录运行时版本"未指明落盘位置；C14 不校验非空。"模板字段在、写入步骤与校验缺"是源码事实；"必然为空"是推断（⚠️），终局取复核措辞。

### 2.6 F6（低）launch.sh 不核验批准原文 —— ✅确认

**引文**：`launch.sh:33`：`grep -q '^status: approved' "$RD/decision.md"`；对照 `/ra-launch` SKILL 第 2 步（模式 B）明确核对"批准原文能在 human_inputs.jsonl 中逐字找到"——模式 A 无此检查。与 F2 叠加（L 前伪造 + 随锁定提交 + 研究员随手跑脚本）链条完整。

### 2.7 F7 Bash 规则单层 `*` 疑似失效 —— ❌不成立（原报告撤回）

**裁判材料引文**（ra2a_261021.md，PERM-SYNTAX 同一节内两条独立规定）：
- :1305 "**递归用 \*\*：\* 只匹配一层。**" —— 位于 :1304"绝对路径用 //"、:1306"写保护要加 Edit deny"、:1307"只认 Read 与 Edit"之间，四条均为**文件路径规则**的 gitignore 式语义；
- :1308 "**Bash 规则只是提示：写作 Bash(cmd \*)，只当前缀提示。只匹配命令字符串**……" —— Bash 规则按**命令字符串**前缀匹配，另有语义。

原报告把路径规则的"单层"语义套到了 Bash 命令串规则上，属误读。`Bash(python3 research/rounds/*)` 能匹配 `python3 research/rounds/R01/work/analyst/x.py`（这也正是 F1 python 链成立的前提，两条结论自洽）。不存在"每次弹确认的可用性退化"。F7 删除；如需 100% 确证可做一次 PLAT-02 实测，但不作为问题保留。

### 2.8 D1–D10

| # | 判定 | 关键证据（源码/原文引文） |
|---|---|---|
| D1 | ✅偏离成立；"已声明"❌、verifier 有 Write ❌（复核正确） | `ra-analyst.md:4`/`ra-skeptic.md:4`：`tools: Read, Grep, Glob, Bash, Write`；`ra-verifier.md:4`：`tools: Read, Grep, Glob, Bash, WebFetch`（**无 Write**）。Lite §1 R18 行（:56）所列措施无一字涉及 Bash/Write；§5.10 注（:758）只禁 `memory:` 与 `Agent`。spec :1608 GOV-DEPTH："治理参与者的工具集不含 Agent……**Bash 与代码执行工具**"。→ 属随包隐式选择，未按 GOV-DEPTH 声明 |
| D2 | ✅（已声明偏离） | frontmatter `model: opus`/`sonnet`、toml `gpt-5.6`；Lite :759"model 默认用别名……建议换成完整模型 ID"；spec C-PIN-001（:1594）"pin 中无别名" |
| D3 | ✅ | settings.json 全文无 `sandbox` 键；human_inputs 16:48 原文"我没有sudo权限"；Lite §3 第 5 步（:113）"强烈建议；Codex 用户必须做"；spec :1410"每条不变量的最后一道墙都要落到 OS 与外部系统权限上" |
| D4 | ✅ | decision.md 模板 frontmatter 仅 `round/phase/status/decided_at/risk_level/charter_blob/rubric_version`——无 plan/erc hash、无 expires；spec :1316 RL2"72 小时"、:1318 批准记录字段含 `expires_at, plan_hash, erc_hashes` |
| D5 | ✅ | Lite 流程 P7（批准）→ L（锁定）→ X（启动）；spec :1602 C-PREREG-001 "`prune_record < erc_lock < gate_pass < approval < dispatch`" |
| D6 | ✅（已声明，知情选择） | PROTOCOL.md:61 "P5 只用 2 名评委"；spec :907 "评委数不少于规则库规定的下限（默认 3）" |
| D7 | ✅ | ra-round SKILL.md:53-57：三个顺序文件，"并行调用 3 次 ra-judge，**每次给一个文件**"→顺序效应与评委效应完全混淆；spec :967"每对提案按正、反两种顺序**各评一次**"（同评委双序）+ :1006 `both_orders: true` |
| D8 | ✅（Claude 侧未声明） | deny 仅 `Edit(./research/ledger/**)`（Edit 规则管不到 python 子进程）；Lite :1651 §7.2#3 该行标注"Codex 下" |
| D9 | ⚠️部分成立（复核降调正确） | 不对称存在：Claude verifier 显式带 `WebFetch` 工具；Codex `ra-verifier.toml` `sandbox_mode = "read-only"`。但其指令写明"需要复算时，python3 只输出到 stdout""ev:web 指针用网页搜索核对"，config.toml:7 `web_search = "cached"`——read-only 下复算与网页核对**设计上可用**（实际可用性 ❓ 需 Codex 实测），原报告"都做不到"不成立 |
| D10 | ✅ | erc.yaml:32-35 仅 `technical_fault/resource_overrun/data_fault`；spec :1036-1039 示例另有 `safety_or_ethics`（A2）与 `futility`（A3）；ra-audit:7 C1 顺序链 `P1<P3<P4<P5<P6<decision<P8<lock` 缺 A 与 P2 |

### 2.9 安装缺口 —— ✅六项全部确认（当前实测）

1. **不是 git repo**：`git rev-parse` → `fatal: not a git repository`（2026-10-23 复测）。
2. **`.claude/skills` 符号链接不存在**：`.claude/` 下仅 `agents/` 与 `settings.json`（复测 grep 计数 0）。
3. **`/ra-init` 未执行**：charter.md 仍为【待定】模板；STATUS.md"当前轮次：无"。
4. **settings 占位路径未替换**：`settings.json:33` 仍是 `"Edit(./eval/**)", "Edit(./data/**)", "Read(./data/test/**)"`。
5. **`.gitignore` 不存在**（复核补充，核验成立）：`ls .gitignore` → No such file；Lite §3 第 6 步（:121）要求先追加 `runs/**/*.pt` 等规则——**必须先于 git init 首提，否则 runs 产物会被收入版本库**。
6. **`/ra-audit R00 canary` 未跑**（复核补充，核验成立）：`research/audits/` 仅 `.gitkeep`；Lite §3 第 10 步（:141）"全部 PASS 后，再开始 /ra-round R01"。

### 2.10 运行时事实 —— ✅（计数以当前为准）

当前：human_inputs **9 条全部 auto**；subagent_outputs 3 条全部 `written_to: null`（无 ra:out 写入）；events 3 条 session（`source: fork`，系会话 fork，与 `CLAUDE_CODE_FORK_SUBAGENT=0` 所管的子代理 fork 无关，不构成 R18 问题——两份评审一致，核验同意）。原报告 6/1/2 为 16:52 时点数，复核 9/3/2 为 10:21 时点数，本报告 9/3/3 为当前值；计数增长不改变任何结论，仅使 F3 更严重。

---

## 3. 终局问题清单与修改方案 **v2**（仅 ✅确认项，按严重度排序）

> **v2 修订（2026-10-23，第三轮评审后）**：第三轮对 v1 提出 8 处执行细节修正，逐条核验**全部成立**；其中两处事实断言经账本复测证实：`subagent_outputs.jsonl` 现有 3 条记录的 `agent_type` **均为空串**（top-level 与 `payload.agent_type` 同值）；`ra-round/SKILL.md:78` 存在"找不到批准记录→注明后继续"的软回退。关键定性变化：**`__run` 令牌从"闭环"降级为"减速带"**——F1 完整闭环显式依赖 P0-2＋P0-1c＋P1-3；**P1-1 从"仅审计"升级为"阶段门实时检查＋审计兜底"双层**；**P0-1a 批准核验从子串 grep 升级为 JSON 解析＋锚定正则＋集合/时序校验**。新增两条执行顺序硬约束：**P0-2 先于（或同步于）P0-1c；skills 符号链接先于 git init 首提**。
>
> **v2.1 修订（第四轮核验后）**：确认 4 项执行阻塞，均已实测/取证——①令牌校验存在**空对空漏洞**（实测复现：无第 5 参且无 `.token` 时两边皆空、比较为真）；②`settings.json:32` 的 `Edit(./research/hooks/**)` 是 deny，**P0-1b 须研究员亲自执行**，且 K9 未验证前白名单不得上线；③**宿主无 bwrap**（实测 `command -v bwrap` 为空），P1-3 **暂缓**；④`disableAutoMode` 键名已确认存在，但**生效性须 canary 实测**（项目级/用户级覆盖方向未知），写配置不等于修复。详见各条目内 **v2.1** 标注。
>
> **v2.2 修订（第五轮后，执行基线）**：定性为**降级版执行**——完整闭环因 bwrap 缺失冻结，令牌防护接受"①层 Read deny ＋ P0-1c ＋ P0-2"的降级组合。修正 v2.1 遗留的三处文本/顺序问题：①**P3 顺序矛盾**（原把 P0-1b 放第 5 步入库、K9 放第 6 步 canary，白名单先于自己的前置检查上线）——改为 P3 总执行序，**K9 单独实测先于 P0-1b**；②§4 #4 bwrap 由"待核验"改"已实测缺失"；③§5 补降级版定性。第五轮第 5 点经实测为**部分成立**：`$(cat)` 剥离尾换行，echo 写入的令牌在当前 `[ = ]` 比对下同样通过（"比对失败"不成立）；仍采纳 `printf '%s'` 写入，作为对后续 diff/hash 校验的稳健性预留。
>
> **v2.3 修订（第六轮后）**：第六轮判定"v2.2 可作降级版执行基线，但非完整闭环版"，并指出两处非阻塞文本残留，均属实并已修：①P0-1a 验证句原引"P1-3 的 denyRead"（已冻结）→ 改为"①层 Read deny＋P0-1c"；②P3 第 7 步原只列 P0 系列 → 补齐 P1-1/P1-2、D2/D10 的落位与 P2 裁决项的入库方式。第六轮同时确认的三个运行时关卡（K9、P0-2 canary、研究员手改 hook）属设计内 fail-closed，任一不过即停在对应降级状态，不作文本修改。**执行定性维持 v2.2：P0 降级基线可启动；§3 全量完成 = 降级基线 ＋ 三关通过 ＋ bwrap 解冻后补 P1-3。**

修复边界仍以 `生成demo用的prompt.md` 为准（开箱即用、避免工具开发），下述全部为现有文件小改。

### P0-1｜未经批准启动实验的完整伪造链（F1+F2+F6）——严重度：最高

**闭环依赖链（v2 明示）**：P0-1a/b/d（应用层堵截）＋ **P0-2（auto 禁用，使 ask 成为真门）** ＋ **P0-1c（python 收紧）** ＋ **P1-3（沙箱 denyRead）**。缺任何一环，其余都只是减速带——令牌可被同用户读回重放，ask 在 auto 未禁用时可被分类器放行。

| # | 位置 | 具体改法（v2） | 验证方式 |
|---|---|---|---|
| a | `research/templates/launch.sh`（同步 Lite §5.9/§5.18） | **① 批准核验（替换 v1 子串 grep）**：新增 `check_approval()`，用 python 逐行解析 `human_inputs.jsonl`，取 `payload.prompt`，锚定正则 `^\s*批准(\s*\(RL3\))?\s+R<ROUND>\s*[:：]`——同时覆盖 `批准 R03:` 与 `批准(RL3) R03:` 两种法定格式（PROTOCOL §9），前导"不/勿/别/驳回"判负；并校验：语句中 exp 集合 ⊇ decision.md 批准集合；该记录 `ts` 早于 lock commit（`git log -1 --format=%cI`）。任一不满足 → `exit 1`。**② `__run` 令牌（v2.1 修正空对空漏洞）**：`TOKEN_ARG="${5:-}"`；校验必须**三重前置**——`[ -n "$TOKEN_ARG" ] && [ -s "$DIR/.token" ] && [ "$TOKEN_ARG" = "$(cat "$DIR/.token")" ] || { echo "✗ 令牌缺失或不符"; exit 1; }`。v2 原式 `[ "${5:-}" = "$(cat … 2>/dev/null)" ]` 在"无第 5 参且无 `.token`"时两边皆空、**比较为真（已实测复现）**——攻击者 `mkdir runs/<exp>` 后无参直调 `__run` 即可穿过；故令牌参数非空、`.token` 存在且非空（`-s`）是硬前置。令牌本体 `TOKEN=$(head -c16 /dev/urandom \| od -An -tx1 \| tr -d ' \\n')`（hex，避免 NUL 进 argv），由 `start_exp` 以 **`printf '%s' "$TOKEN" > .token`（无尾换行）** 写入并作为第 5 参传入 tmux/nohup 命令（写入法实测注：`$(cat)` 剥离尾换行，echo 写入在当前 `[ = ]` 比对下亦能通过；printf 是为后续若改用 diff/hash 校验保持确定）。**定性：令牌只打断无参重放与误触，不是闭环**——`.token` 同用户可读，其门效依赖 P0-2＋P0-1c＋①层 `Read(./runs/**/.token)` deny（v2.1，见 P1-3）＋沙箱 denyRead（暂缓） | ① 输入"我不批准 R03"→ 拒绝；RL3 格式 → 正确识别；批准集合缺 E2 → 拒绝；批准 ts 晚于 lock → 拒绝。② 无/错令牌直调 `__run` → 拒绝；正常 tmux 路径 → 通过；python 读令牌重放 → 由 c 的 ask 与 ①层 `Read(./runs/**/.token)` deny 拦（v2.3 修正：原句引 P1-3 denyRead，但 P1-3 已冻结——降级态下的实际拦截就是这两层） |
| b | `research/hooks/ra_log.py`（同步 Lite §5.13） | `save_out` 白名单 **fail-closed**：`agent_type` 为空串或缺失时（top-level 与 `payload.agent_type` 两处都查——当前账本实测两者均为 `''`），一切角色绑定路径 → `rejected:agent_type_missing` 并记账，**不得空真放行**。完整映射：ra-analyst → `Rnn/{A_results,p1/analyst,p3/analyst,p34/analyst,p4/analyst,p8/analyst}.md` 与 `R00/baseline_analysis.md`；ra-skeptic → `p1\|p3\|p34\|p4\|p8/skeptic.md` 与 `R00/integrity.md`；ra-designer → 同型 designer 路径；ra-judge → `p5/judge-*.md`；ra-verifier → `p6/verify*.md`；**主会话文件一律拒绝**：`decision.md`、`brief.md`、`p2_broadcast.md`、`p5/candidates-*.md`、`p5/mapping.md`、`p6_synthesis.md`、`feasibility.md`。新增 **K9 canary**：真实 ra-* 子代理结束时 hook 输入的 `agent_type` 必须非空且等于角色名（对齐 spec PLAT-06 键集登记）；平台若不提供该字段，白名单整体降级为"全部 rejected、Lead 不得代写"，不得静默放行。**v2.1 执行约束（两项前置）**：① `settings.json:32` 的 `Edit(./research/hooks/**)` 在 deny——**本项修改须研究员亲自执行**（或临时放宽、改完复原，全程留 git 记录）；② **K9 先于白名单上线**：现有 3 条子代理记录 `agent_type` 全为空串，若实测确认平台不填该字段，fail-closed 白名单会拒绝一切角色输出、**流程直接不可用**——此时白名单不得启用，先升级平台版本或改用研究员人工落盘，问题登记在 §4 ❓#5 | 子代理发 `ra:out R03/decision.md` → `rejected:whitelist`；发合法路径但 agent_type 空 → `rejected:agent_type_missing`；正常轮次 → 落盘成功 |
| c | `demo/.claude/settings.json:21` | `Bash(python3 research/rounds/*)` 从 allow 移到 ask。**顺序约束：晚于或同步于 P0-2**——auto 未禁用时 ask 可被分类器放行，c 单独不是门 | P0-2 前：auto 会话 python 可能被放行（演示用）；P0-2 后：必弹确认 |
| d | `.agents/skills/ra-audit/SKILL.md` | C2b：每个 p1 文件对应记录的 `agent_type` 必须等于文件名对应角色，**空值 fail-closed**；C15：`runs.jsonl` 中每个 `DONE/FAILED/**ABORTED**` 之前必须存在同 exp_id 的 `STARTED`（v1 漏了 ABORTED） | 构造"ABORTED 无 STARTED"→ C15 FAIL；agent_type 空串的 p1 记录 → C2b FAIL |

### P0-2｜F3 auto 模式（9/9 已实际发生）——严重度：高（v2 三处强化）

1. settings 禁用键（v2.1 更新）：`permissions.disableAutoMode: "disable"`——**键名已在 settings schema 确认存在**（第四轮提供）。但**项目级设置是否被用户级覆盖、方向未知**：写入后必须 canary 实测——`claude --permission-mode auto` 启动（或会话内切换 auto）应被拒；**实测通过前不视为已修复，写配置 ≠ 修复**（§4 ❓#1 同步收窄为"生效性实测"）。
2. 检查点从"开轮时点"扩为三处：开轮自检（历史窗口）＋ **⏸ 批准时**——P7 核验到的批准原文那条 human_inputs 记录，其 `payload.permission_mode` 必须 ≠ `auto`（对批准有效性的直接判定，非时点抽查）＋ C14 审计兜底。
3. **新确认缺口（SKILL.md:78 软回退）**：现文"找不到（hook 不可用）时，在 decision.md 中注明'无 hook 记录'"允许**无账本证据继续走 P7**，违反 spec C-APPROVAL-003（"dispatch 之前必回账本核验"）。改为 fail-closed：找不到批准记录 → 终止 P7、排查 hook、修复后重查。

验证：auto 会话输入批准 → ⏸ 核验 FAIL；default 会话 → PASS；屏蔽 hook 后走 P7 → 终止而非"注明继续"。运行时处置不变：修复前既有 auto 输入一律不得视为批准凭据（当前无批准语句，实际无损）。

### P1-1｜F4 压缩判定 —— 严重度：中（v2 升级为双层）

- **实时门（主）**：`ra-round` 在进入 P2、P6、P7 前检查本轮窗口内 `events.jsonl`：无 `kind=compact` 事件、无 SessionStart `source=compact` 记录（`source` 字段已在账本出现 `fork` 取值；`compact` 取值待 K 实测，列入 ❓）。命中 → 该阶段记 incomplete、本回合不出决策（对齐 spec :930 的实时语义）。
- **审计兜底（辅）**：C1 加同一检查，事后可发现。

验证：人为触发压缩后继续 ra-round → 阶段门拦截；/ra-audit → C1 FAIL。

### P1-2｜F5 meta 字段 —— 严重度：低（v2 补 R00）

ra-round 0.3 明确"填写 runtime 与 models 各角色实际 model ID"；**ra-init 第 8 步明确写入 `research/rounds/R00/meta.yaml`**（runtime/models/platform_changed）——否则 `/ra-audit R00 canary` 的 C14 无审计对象；C14 对"无轮次"显式判 N.A.，不空真通过。

### P1-3｜D3 沙箱 —— 严重度：中高（v2.1：**暂缓，前置不满足**）

**实测：宿主无 bwrap**（`command -v bwrap` 为空，2026-10-23）。此状态下 `failIfUnavailable:true` 会让**全部 Bash 失败**（不可用），设 false 则沙箱被**静默跳过**（不可接受）——两者都不能上线，**方案冻结**，直至 bwrap 可用或换沙箱后端。

**v2.1 补充（不等沙箱的立即动作）**：sandbox 的 `denyRead` 只作用于 Bash 子进程，**内置 Read 工具仍可读 `runs/<exp>/.token`**——无论沙箱是否可用，①层立即加 `Read(./runs/**/.token)` deny（平台原生、零依赖，随 P0 系列一并入库）。沙箱缺失期间，令牌防读回的保证 = ①层 Read deny ＋ P0-1c（python ask）——较完整方案**降级**，须知情接受。

（沙箱可用后再补：`enabled`、`failIfUnavailable:true`、`allowUnsandboxedCommands:false`、`excludedCommands` 为空；`denyRead` 覆盖 `data/test`、`eval`、`.token`。现有 Read/Edit deny 届时全部保留——沙箱只管 Bash 及其子进程（spec §11.7 层表），内置文件工具仍归①层管。）

### P2｜设计裁决项（v2 调整 D1、D4/D5）

| # | 建议（v2） |
|---|---|
| D7 | 不变：A 每评委评全三序（成本×3）／ B 改措辞"顺序均衡"／ C 同评委双序 pairwise；推荐 A 或 B，研究员拍板 |
| D1 | **优先级反转**：首选 Lite §1 显式声明（零成本）；次选 verifier 配只读沙箱（保留 Bash、写由沙箱拒）；**撤销 v1 的"复算交 analyst"**——analyst 是被核验方，转交破坏 P6 独立性（spec :1614：P6 由 fresh verifier 承担） |
| D4/D5 | **修正绑定语义**：decision.md 记 `erc_hashes` 本身只是漂移检测（Lead 批准后改 ERC 再重算 hash 仍可过）；真绑定 = hash 在 ⏸ 前写入 brief §8（研究员可见）＋ decision.md 记同一组 hash（P7 写入经 ask 确认＝人工绑定点）＋ 新审计 C10b 校验三方一致（decision == 锁定时 ERC 的 `git hash-object` == brief §8）。可选强化：批准语句带 hash 后缀（研究员自愿） |
| D2 | frontmatter 换完整模型快照 ID；至少落实 P1-2 的 meta 记录 |
| D10 | erc.yaml 模板补 `safety_or_ethics`、`futility` 注释示例；C1 顺序链补 A 与 P2 |
| D6/D8/D9 | 不变：知情接受；D8 每轮 L 前跑 §7.4 交叉核对；D9 Codex web 能力实测再定 |

### P3｜安装与修复总执行序（v2.2 修正顺序矛盾）—— 严重度：前置阻断

1. **`.gitignore`**（先于一切 git 操作）→ 2. **`.claude/skills → .agents/skills` 符号链接**（首提即含链接）→ 3. `git init` + 首次提交（基线冻结）→ 4. `/ra-init`（含 P1-2 的 R00 meta）→ 5. **K9 单独实测**（真实 ra-* 子代理结束时 `agent_type` 非空且等于角色名）——**不通过则 P0-1b 永不上线**（fail-closed 白名单会让流程不可用，届时降级为研究员人工落盘并在 §4 ❓#5 挂账）→ 6. **P0-2 写配置 ＋ 生效 canary**（`--permission-mode auto` 应被拒；不过则 P0-2 未完成，P0-1c 不得生效）→ 7. 其余修复一并入库（v2.3 补齐 P1/P2 落位）：**launch.sh 侧** P0-1a（三重前置令牌＋`check_approval()` 批准核验）、P0-1d；**settings 侧** P0-1c（以第 6 步通过为前提）、①层 `Read(./runs/**/.token)` deny；**hook 侧** P0-1b（**研究员亲自改 hook**，以第 5 步通过为前提）；**技能/模板侧** P1-1（ra-round 阶段门实时查 compact＋C1 兜底）、P1-2（ra-init/ra-round 的 meta 写入步骤）、D10（erc.yaml 补 safety/futility 注释、C1 链补 A/P2）、D2（frontmatter 换完整模型 ID，可选）；**P2 裁决项** D4/D5（brief §8 hashes＋decision.md `erc_hashes`＋C10b）与 D1（Lite §1 显式声明）经研究员裁决后随本批或下一批入库，D7 纯裁决、不涉及本批 → 8. `/ra-audit R00 canary` 全 PASS → 才可 `/ra-round R01`。

> v2.1 的六步把 P0-1b 放在第 5 步入库、K9 放在第 6 步 canary——白名单先于自己的前置检查上线，属顺序矛盾，v2.2 已并入上述总序修正。

---

## 4. ❓无法核验项汇总（均不阻塞上述结论）

1. ~~`permissions.disableAutoMode` 键名未知~~ **（v2.1 收窄）**：键名已在 settings schema 确认存在；剩余待实测项是**生效性**——项目级与用户级设置的覆盖方向、`--permission-mode auto` 是否被实际拒绝（P0-2 部署后的 canary，未通过前 P0-2 不算完成）。
2. Bash 规则 `*` 的跨层语义最终确证——本报告依 spec :1305/:1308 两套语法的规定裁定 F7，如需 100% 实证可跑一次 PLAT-02（不影响 F1 结论，F1 的 python 链不依赖该语义边界之外的事实）。
3. Codex read-only 沙箱下 `web_search`/复算的实际可用性（D9 的程度判定）。
4. ~~宿主 bubblewrap 可用性~~ **（v2.2 更新）**：已实测**缺失**（2026-10-23 `command -v bwrap` 为空），P1-3 维持冻结；剩余待核验仅"后端何时可用 / 是否换后端"。
5. **（v2 新增）** SubagentStop 输入的 `agent_type` 键集：当前账本 3 条记录均为空串，无法区分"该平台版本不填"与"这几次子代理恰好是无角色类型"——P0-1b 的白名单可行性与 K9 canary 依赖此项（对齐 spec PLAT-06）。
6. **（v2 新增）** SessionStart `source` 字段在压缩恢复场景的取值是否为 `compact`（账本只见 `fork`）——P1-1 实时门的第二检查项依赖此项。

---

## 5. 终局一句话

两份评审高度一致地指向同一结论：**demo 的 Lite 映射在"声明纪律"上基本合格（个别归类需修正：D1、F4），真正的要害是四条实现缺陷构成的一条完整伪造链（F1+F2+F6，复核补充的 python allow 路径使其升级）与已实际发生的 F3（9/9 auto）**；修复全部可以在"现有文件小改"范围内完成（符合 prompt.md"避免工具开发"）。

**v2 补句（第三轮后）**：v1 把 P0-1 的闭环寄托在"令牌＋四处修改"上，第三轮证明令牌可被同用户读回重放、ask 在 auto 未禁用时形同虚设——因此**闭环的正确表述是依赖链：P0-2（禁 auto）是其余一切 ask 类门槛的前置，P1-3（沙箱 denyRead）是令牌与全部"同用户可读"秘密的前置**。执行顺序上，P0-2 必须最先落地；在它完成之前，P0-1c/d 与令牌都只是减速带，这一点不因修复数量增加而改变。

**v2.2 定性（第五轮后，执行基线）**：本方案按**降级版**执行——完整闭环因 bwrap 缺失而冻结（P1-3），现行接受的令牌防护 = ①层 `Read(./runs/**/.token)` deny ＋ P0-1c（python ask）＋ P0-2（禁 auto），知情接受其弱于沙箱方案；执行总序以 P3 为准（K9 先于 P0-1b、P0-2 canary 先于 P0-1c）。第五轮第 5 点经实测为部分成立（详见 §3 v2.2 修订注）。
