# CHANGELOG — RA2A-Lite demo-revised 包版本索引

维护规则（v2.4 起生效，详见 `PATCH-v2.4.md` §9）：
- 版本号 `vX.Y`；一个获准批次（B0/B1/…）或一组同类获准修改 = 一个版本；方案文档修订用 `plan-N` 后缀，不占包版本。
- 发布 = 分批 git 提交 + annotated tag（`git tag -a vX.Y`）+ `PATCH-vX.Y.md`（修改、依据、验收状态、回退步骤）+ 本文件条目。
- 历史条目**只增不改**；当前版本以最新 tag 与 `research/STATUS.md`"包版本"字段为准。
- 一致性纪律：改 `ra2a_lite_8xa100.md` §5 收录的文件后须过 `python3 research/runtime/checks/lite_doc_sync.py --check`（T11）；基线回归用 `baseline_manifest.py --verify`。

---

## v2.4 — 2026-10-26

实施 `update/final_modification_plan.md`（v2.4-plan-2）的 **B0 + B1**；B2–B4 未实施（门条件见该方案 §9）。完整修改清单与依据：`PATCH-v2.4.md`。

- **B0 修改基线**：74 个治理/受保护文件 sha256 清单 + 工具版本（Claude 2.1.247 / Codex 0.164.0）+ 权限源登记，产物在 `research/audits/permissions-2026-10-26/work/b0-baseline/`；新增 `research/runtime/checks/`（baseline_manifest.py、lite_doc_sync.py）；实证 Lite §5 漂移集 = v2.3 登记的 8 文件。
- **B1 白天减负**（settings.json）：`defaultMode` 保持 `default` + 精确 allow（`update/**`、`research/runtime/checks/**`、约 30 条只读命令）；**auto 过渡期禁用**（`disableAutoMode: "disable"`，中止 2026-10-23 的 auto 放行裁决，恢复条件见 PATCH-v2.4 §8）；`git tag -a/-s` 显式 ask；新增 PermissionRequest / Notification **只记账** hook。
- **B1 候选配置**：`.claude/candidates/settings.acceptEdits.draft.json`（未启用；启用前置 T01a/T01b）。
- **B1 规则语义**：CLAUDE.md 新增"权限模式"章节；AGENTS.md 新增"工具确认/草案与基线"两条；PROTOCOL.md 升 **lite-1.1**（§9 v2.4 注）；PATCH-v2.3.md 追加 §5 处置记录（D03 ask/auto 语义、D05 Codex Python 描述更正）。
- **文档同步**：Lite §5 全部 38 块 **0 漂移**（10 块经脚本刷新）；§2"三次弹窗"承诺改为人工决定点+工具确认清单；§6.7 hook 计数 4→6；STATUS.md 新增"包版本"字段。
- **版本机制**：本文件 + PATCH-v2.4.md + annotated tag；**不另建 fork**（决定与理由：PATCH-v2.4 §2）。
- 验收状态：T01a/T01b 待研究员实测（PATCH-v2.4 §7）；已知边界与残留风险见其 §6。
- 提交：`0611d8c`（前置材料入库）→ `f849d1f`（B0）→ 本版提交（tag `v2.4`）。

## v2.3 — 2026-10-23（tag `v2.3` = e85cd92）

单提交重建自 demo-fixed：相对原版 demo 的全部修复——launch.sh `__run` 三重令牌与 `check_approval` 批准核验（F1/F6）、ra_log.py ra:out 白名单（fail-closed，休眠交付）、`python3 research/rounds/*` 移入 ask、`.token` 禁读、审计项补齐（C1 链/C2b/C14/C15/K9）、技能 fail-closed 措辞、ERC abort 条件补全——以及 **auto 放行变体**（2026-10-23 研究员裁决的知情偏离；v2.4 起过渡禁用）。详见 `PATCH-v2.3.md`、`conformance-final-verdict.md`。
