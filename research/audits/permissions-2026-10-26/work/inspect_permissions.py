#!/usr/bin/env python3
"""只读收集权限配置；候选命令仅送入 execpolicy，不执行候选命令。"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
ENV = dict(os.environ, CUDA_VISIBLE_DEVICES="")


def run(argv):
    result = subprocess.run(
        argv, cwd=ROOT, env=ENV, capture_output=True, text=True,
        timeout=30, check=False,
    )
    return {
        "argv": argv, "rc": result.returncode,
        "stdout": result.stdout, "stderr": result.stderr,
    }


def write_json(name, value):
    (OUT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )


def main():
    files = [
        "AGENTS.md", "CLAUDE.md", ".claude/settings.json",
        ".codex/config.toml", ".codex/rules/ra.rules", ".codex/hooks.json",
        "research/PROTOCOL.md", "research/charter.md", "PATCH-v2.3.md",
        "research/hooks/ra_log.py", "research/templates/launch.sh",
        *[f".agents/skills/{name}/SKILL.md" for name in (
            "ra-round", "ra-init", "ra-memory", "ra-launch", "ra-audit", "ra-status",
        )],
    ]
    sources = {}
    snapshot = []
    for rel in files:
        raw = (ROOT / rel).read_bytes()
        sources[rel] = {"sha256": hashlib.sha256(raw).hexdigest()}
        snapshot.append(f"\nFILE: {rel}\n")
        snapshot.extend(f"{i:04d}: {line}\n" for i, line in enumerate(
            raw.decode("utf-8").splitlines(), 1,
        ))
    (OUT / "source_snapshot.txt").write_text("".join(snapshot), encoding="utf-8")
    write_json("source_hashes.json", sources)

    settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
    inventory = {
        "root": str(ROOT),
        "cuda_visible_devices_for_subprocesses": ENV["CUDA_VISIBLE_DEVICES"],
        "claude": run(["claude", "--version"]),
        "codex": run(["codex", "--version"]),
        "bwrap_in_path": shutil.which("bwrap"),
        "claude_sandbox_in_project_settings": settings.get("sandbox"),
        "claude_permissions": settings["permissions"],
        "git_status_at_collection": run(["git", "status", "--short"]),
        "protected_status_at_collection": run([
            "git", "status", "--porcelain", "--", "AGENTS.md", "CLAUDE.md",
            ".claude", ".agents", ".codex", "research/charter.md",
            "research/rubric.md", "research/PROTOCOL.md", "research/hooks",
            "research/templates", "research/memory/knowledge.md",
            "research/memory/negative_results.md", "research/memory/hypotheses.md",
            "research/memory/playbook.md",
        ]),
    }
    write_json("inventory.json", inventory)

    # 这里的 argv 是规则查询的数据。execpolicy 不会运行这些候选程序。
    candidates = [
        ["python3", "research/rounds/R00/work/analyst/check.py"],
        ["bash", "research/rounds/R00/work/check.sh"],
        ["env", "CUDA_VISIBLE_DEVICES=", "python3", "analysis.py"],
        ["env", "PYTHONHASHSEED=0", "python3", "analysis.py"],
        ["git", "status", "--short"],
        ["git", "commit", "-m", "policy-query-only"],
        ["torchrun", "--help"],
    ]
    checks = []
    for candidate in candidates:
        query = run([
            "codex", "execpolicy", "check", "--rules", ".codex/rules/ra.rules",
            "--", *candidate,
        ])
        query["candidate_executed"] = False
        if query["rc"] == 0:
            query["policy_result"] = json.loads(query["stdout"])
        checks.append(query)
    write_json("policy_checks.json", checks)
    print(json.dumps({
        "claude_version": inventory["claude"]["stdout"].strip(),
        "codex_version": inventory["codex"]["stdout"].strip(),
        "bwrap_in_path": inventory["bwrap_in_path"],
        "protected_files_clean": not inventory["protected_status_at_collection"]["stdout"],
        "policy_checks": [
            {"candidate": c["argv"][6:], "rc": c["rc"], "result": c.get("policy_result")}
            for c in checks
        ],
    }, ensure_ascii=False, indent=2))
    if any(c["rc"] != 0 for c in checks):
        raise SystemExit("有规则查询失败，请检查 policy_checks.json。")


if __name__ == "__main__":
    main()
