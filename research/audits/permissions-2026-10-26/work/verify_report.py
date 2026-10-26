#!/usr/bin/env python3
"""核对本次报告的本地 ev 指针、源码快照及保护文件状态。"""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
REPORT = ROOT / "research/audits/permissions-2026-10-26.md"


def main():
    errors = []
    pointers = sorted(set(re.findall(
        r"ev:([A-Za-z0-9_./-]+)#([A-Za-z0-9_.-]+)",
        REPORT.read_text(encoding="utf-8"),
    )))
    for rel, anchor in pointers:
        path = ROOT / rel
        if not path.is_file():
            errors.append(f"文件不存在：{rel}")
            continue
        raw = path.read_text(encoding="utf-8")
        match = re.fullmatch(r"L(\d+)-L(\d+)", anchor)
        if match:
            start, end = map(int, match.groups())
            if not (1 <= start <= end <= len(raw.splitlines())):
                errors.append(f"行号越界：{rel}#{anchor}")
        else:
            try:
                value = json.loads(raw)
                for key in anchor.split("."):
                    value = value[int(key)] if isinstance(value, list) else value[key]
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                errors.append(f"JSON 指针无效：{rel}#{anchor}：{exc}")

    sources = json.loads((OUT / "source_hashes.json").read_text(encoding="utf-8"))
    for rel, recorded in sources.items():
        actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if actual != recorded["sha256"]:
            errors.append(f"收集后源码变化：{rel}")

    checked = subprocess.run([
        "git", "status", "--porcelain", "--", "AGENTS.md", "CLAUDE.md",
        ".claude", ".agents", ".codex", "research/charter.md",
        "research/rubric.md", "research/PROTOCOL.md", "research/hooks",
        "research/templates", "research/memory/knowledge.md",
        "research/memory/negative_results.md", "research/memory/hypotheses.md",
        "research/memory/playbook.md",
    ], cwd=ROOT, env=dict(os.environ, CUDA_VISIBLE_DEVICES=""),
        capture_output=True, text=True, check=False, timeout=30)
    if checked.returncode or checked.stdout:
        errors.append("保护文件检查失败或存在修改")
    result = {
        "local_evidence_pointers": len(pointers),
        "source_hashes_checked": len(sources),
        "protected_git_status": checked.stdout,
        "errors": errors,
        "scope": "只检查指针可解析性和文件未变；语义支持由报告审核承担",
    }
    (OUT / "report_verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
