#!/usr/bin/env python3
"""收集两份 review 对账依据；只读源码，不运行 review 中的命令。"""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
PLAN = ROOT / "update/final_modification_plan.md"


def run(argv):
    result = subprocess.run(
        argv, cwd=ROOT, env=dict(os.environ, CUDA_VISIBLE_DEVICES=""),
        capture_output=True, text=True, check=False, timeout=30,
    )
    return {"argv": argv, "rc": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    baseline = json.loads((OUT / "source_hashes.json").read_text(encoding="utf-8"))
    extras = [
        "update/claude_review_auto_mode.md", "update/claude_review_auto_mode_2.md",
        "ra2a_lite_8xa100.md", "research/audits/permissions-2026-10-26.md",
        "research/audits/R00-2026-10-23.md", "research/templates/meta.yaml",
        "research/templates/brief.md", "research/templates/decision.md",
        "research/templates/erc.yaml", "research/templates/exp.sh",
        *[str(p.relative_to(ROOT)) for folder in (".claude/agents", ".codex/agents")
          for p in sorted((ROOT / folder).glob("*")) if p.is_file()],
    ]
    hashes = {rel: digest(ROOT / rel) for rel in sorted(set(baseline) | set(extras))}
    changed = [rel for rel, item in baseline.items() if hashes[rel] != item["sha256"]]
    protected = run([
        "git", "status", "--porcelain", "--", "AGENTS.md", "CLAUDE.md",
        ".claude", ".agents", ".codex", "research/charter.md",
        "research/rubric.md", "research/PROTOCOL.md", "research/hooks",
        "research/templates", "research/memory/knowledge.md",
        "research/memory/negative_results.md", "research/memory/hypotheses.md",
        "research/memory/playbook.md",
    ])
    facts = {
        "review_files": extras[:2],
        "source_hashes": hashes,
        "changed_since_previous_audit": changed,
        "protected_git_status": protected,
        "whitelist_marker_exists": (ROOT / "research/hooks/.whitelist_on").exists(),
        "runtime": {"claude": run(["claude", "--version"]),
                    "codex": run(["codex", "--version"])},
        "deployment_programs_in_path": {
            program: shutil.which(program) for program in ("bwrap", "docker", "podman")
        },
        "deployment_capabilities_tested": False,
    }
    (OUT / "reconciliation_evidence.json").write_text(
        json.dumps(facts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )

    errors = []
    pointers = sorted(set(re.findall(
        r"ev:([A-Za-z0-9_./-]+)#([A-Za-z0-9_.-]+)",
        PLAN.read_text(encoding="utf-8"),
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
            count = len(raw.splitlines())
            if not (1 <= start <= end <= count):
                errors.append(f"行号越界：{rel}#{anchor}（共 {count} 行）")
        else:
            try:
                value = json.loads(raw)
                for key in anchor.split("."):
                    value = value[int(key)] if isinstance(value, list) else value[key]
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                errors.append(f"JSON 指针无效：{rel}#{anchor}：{exc}")
    if changed or protected["rc"] or protected["stdout"]:
        errors.append("保护源码存在变化，需要重新对账。")
    result = {
        "local_evidence_pointers": len(pointers), "source_files_hashed": len(hashes),
        "prior_source_files_checked": len(baseline), "errors": errors,
        "scope": "可解析性与源码一致性校验；不替代语义核验或运行时验收",
    }
    (OUT / "reconciliation_verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({**result, "deployment_programs_in_path": facts["deployment_programs_in_path"],
                      "whitelist_marker_exists": facts["whitelist_marker_exists"]},
                     ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
