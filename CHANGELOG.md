# CHANGELOG — RA2A-Lite 版本索引

维护规则：

- 版本号使用 `vX.Y`；一个获准批次或一组同类修改对应一个版本。
- 每个版本配套 `PATCH-vX.Y.md`，记录修改、依据、验证状态、边界和回滚方式。
- 本文件只追加历史条目，不回写已经发布的版本。
- 发布完成的版本应有 Git 提交和 annotated tag；当前版本以最新 tag、README 和项目状态记录为准。

---

## v2.5 — 2026-10-30

结论版本层与框架保护修复。完整说明见 [`PATCH-v2.5.md`](PATCH-v2.5.md)，验证记录见 [`update/v2.5-verification.md`](update/v2.5-verification.md)。

- 新增 RES 实验判定账本和语义结论版本账本；
- 新增 `res_extract.py`、`commit_conclusion.py`、`review_queue.py` 三个受保护写入器；
- 新增 `guard_writes.py`，补齐受保护路径、决策前置门和 spawn 记账；
- 同步更新协议、模板、技能、Claude / Codex 配置和 Lite 主文档；
- 金丝雀验证通过；本机账本保护为 `degraded`，以 Git 对账补偿；
- 尚未执行研究轮次、训练或评测。

## v2.4 — 2026-10-26

修改基线锁定、白天权限减负和版本机制。该版本的完整技术说明保留在历史 `v2.4` tag 的 `PATCH-v2.4.md` 中。

- B0：生成受保护文件基线、工具版本和权限源登记；
- B1：保持 `default` 模式，增加精确 allow，临时禁用 auto，补充权限事件记账；
- 修正 Claude 权限模式和 Codex 规则的文档语义；
- 建立“提交 + annotated tag + PATCH + CHANGELOG”的版本发布纪律；
- B2–B4 未实施，候选配置不作为默认配置启用。

## v2.3 — 2026-10-23

RA2A-Lite 修复版，提交为 `e85cd92`，tag 为 `v2.3`。完整说明见 [`PATCH-v2.3.md`](PATCH-v2.3.md)。

- 补齐 launch、批准核验、`ra:out` 白名单和审计项；
- 将敏感路径、轮次脚本和权限边界纳入保护；
- 保留 2026-10-23 的 auto 放行知情偏离，并在 v2.4 起进入过渡禁用状态。
