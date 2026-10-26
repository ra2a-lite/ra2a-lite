# B0 基线清单（2026-10-26T14:27:08+0800）

- git HEAD：`e85cd922a745318474f7099961da764340c07624`（branch=master，describe=e85cd92）
- Claude：2.1.247 (Claude Code)；Codex：codex-cli 0.164.0
- 受保护/治理文件：74 项（哈希见 manifest.json）
- 账本快照：4 个文件（只增，不进 verify）
- 符号链接：{".claude/skills": "../.agents/skills"}
- git status（生成时）：见 manifest.json git.status_short

| 文件 | sha256（前 16 位） |
|---|---|
| .agents/skills/ra-audit/SKILL.md | ae8fb6944dac3dde |
| .agents/skills/ra-init/SKILL.md | c0d129f1810da668 |
| .agents/skills/ra-launch/SKILL.md | 5f57b022a4e0c2b2 |
| .agents/skills/ra-memory/SKILL.md | a3b0b214cc845e5b |
| .agents/skills/ra-round/SKILL.md | 976669a0569af5b4 |
| .agents/skills/ra-status/SKILL.md | bfca43fb26f20144 |
| .claude/agents/ra-analyst.md | d07422511adfda70 |
| .claude/agents/ra-designer.md | a918778040bf00ee |
| .claude/agents/ra-judge.md | fe8da1c0a32ccdb0 |
| .claude/agents/ra-skeptic.md | 540731ea634f4499 |
| .claude/agents/ra-verifier.md | ba7706857edbe097 |
| .claude/settings.json | a2eae394cb166411 |
| .claude/settings.local.json | 8269844a363399c3 |
| .codex/agents/ra-analyst.toml | 5c8e3d9641c2c385 |
| .codex/agents/ra-designer.toml | ef1b0064fe552ff3 |
| .codex/agents/ra-judge.toml | e406480b5e5faab1 |
| .codex/agents/ra-skeptic.toml | 43e1ea62dc8f82a2 |
| .codex/agents/ra-verifier.toml | b7e4ce705e587bc8 |
| .codex/config.toml | f8aea81633648853 |
| .codex/hooks.json | b10bc91d044f8164 |
| .codex/rules/ra.rules | 9237394cf1e37131 |
| .gitignore | 76d3ef7f71bc7589 |
| AGENTS.md | 1dcebc0c46c9303b |
| CLAUDE.md | cda6db6763b96d68 |
| PATCH-v2.3.md | 75f695402f2c7d9e |
| conformance-final-verdict.md | 0d7cbf441ba6233a |
| ra2a_lite_8xa100.md | 301169cec650bc9b |
| research/PROTOCOL.md | a773f1a3daf1e963 |
| research/STATUS.md | db4933770983b1e1 |
| research/audits/.gitkeep | e3b0c44298fc1c14 |
| research/audits/R00-2026-10-23.md | 59268720fb1bda18 |
| research/audits/permissions-2026-10-26.md | 0ea55e352e01d179 |
| research/audits/permissions-2026-10-26/work/b0-baseline/lite_sync_before.json | c2c198f61baef110 |
| research/audits/permissions-2026-10-26/work/b0-baseline/manifest.json | ebde9a731833d355 |
| research/audits/permissions-2026-10-26/work/b0-baseline/manifest.md | 393f8437805e7a4d |
| research/audits/permissions-2026-10-26/work/inspect_permissions.py | f80b34e549407697 |
| research/audits/permissions-2026-10-26/work/inventory.json | ef1b3f3ce9fea1db |
| research/audits/permissions-2026-10-26/work/plan-review-r2/baseline.json | 7a053c169cc1c14b |
| research/audits/permissions-2026-10-26/work/plan-review-r2/check_revision.py | c030e0516a5e78d3 |
| research/audits/permissions-2026-10-26/work/plan-review-r2/claude_help.txt | 71ad650f59e08ae4 |
| research/audits/permissions-2026-10-26/work/plan-review-r2/plan-1.original.md | a271b1be8f45dc07 |
| research/audits/permissions-2026-10-26/work/plan-review-r2/runtime_evidence.json | 7da984fa4379d05f |
| research/audits/permissions-2026-10-26/work/plan-review-r2/verification.json | 0515d130bf5f0cbe |
| research/audits/permissions-2026-10-26/work/policy_checks.json | 4371005a8e569fea |
| research/audits/permissions-2026-10-26/work/reconcile_reviews.py | 2a7fe15af8b98c86 |
| research/audits/permissions-2026-10-26/work/reconciliation_evidence.json | b8e2274f64844e6c |
| research/audits/permissions-2026-10-26/work/reconciliation_verification.json | f2ba42f8c58ed390 |
| research/audits/permissions-2026-10-26/work/report_verification.json | 2f474cde2935803d |
| research/audits/permissions-2026-10-26/work/source_hashes.json | 16a0c5c2e4cc0d75 |
| research/audits/permissions-2026-10-26/work/source_snapshot.txt | 31d2759e3a8f1f37 |
| research/audits/permissions-2026-10-26/work/verify_report.py | 4f66afca7320ca92 |
| research/charter.md | 861105fad153797d |
| research/hooks/ra_log.py | 2100afabfbf21626 |
| research/memory/hypotheses.md | 178702ba78735532 |
| research/memory/knowledge.md | c78aa7cc2b5068a6 |
| research/memory/negative_results.md | 3c4951f3016b83b6 |
| research/memory/playbook.md | 6a481771e4327dbe |
| research/memory/proposals/applied/.gitkeep | e3b0c44298fc1c14 |
| research/memory/proposals/rejected/.gitkeep | e3b0c44298fc1c14 |
| research/project_card.md | 37a24b088c441b4c |
| research/rubric.md | 4ae7ade4f1107148 |
| research/runtime/checks/baseline_manifest.py | acbe9e60740588ae |
| research/runtime/checks/lite_doc_sync.py | 9d7e75ee91ab115c |
| research/templates/brief.md | 4989fc121e6b03d0 |
| research/templates/cr.md | fd48cd74a82e2b7b |
| research/templates/decision.md | f934388089628ee7 |
| research/templates/erc.yaml | 73b74c05023550cb |
| research/templates/exp.sh | 82afee297c1c664a |
| research/templates/launch.sh | 7d8b8a33e3268b30 |
| research/templates/meta.yaml | 30dded8cdfba5f95 |
| update/claude_review_auto_mode.md | b5a2f726d98a8e0e |
| update/claude_review_auto_mode_2.md | 2c558e7c5a046b84 |
| update/final_modification_plan.md | 3ce2f280145cba25 |
| update/plan_review.md | 1ec6dd5bf81f87ec |
