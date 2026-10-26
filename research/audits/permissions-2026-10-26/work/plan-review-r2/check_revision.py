#!/usr/bin/env python3
"""留存 plan-1，采集版本/help；校验 plan-2。不会启动模型会话或运行权限探测。"""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]
PLAN = ROOT / "update/final_modification_plan.md"
REVIEW = ROOT / "update/plan_review.md"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv):
    result = subprocess.run(
        argv, cwd=ROOT, env=dict(os.environ, CUDA_VISIBLE_DEVICES=""),
        capture_output=True, text=True, check=False, timeout=30,
    )
    return {"argv": argv, "rc": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr}


def save(name, value):
    (OUT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )


def capture():
    target = OUT / "plan-1.original.md"
    with target.open("xb") as handle:
        handle.write(PLAN.read_bytes())
    version = run(["claude", "--version"])
    help_result = run(["claude", "--help"])
    if version["rc"] or help_result["rc"]:
        raise SystemExit("版本/help 读取失败。")
    (OUT / "claude_help.txt").write_text(help_result["stdout"], encoding="utf-8")
    baseline = json.loads((OUT.parent / "source_hashes.json").read_text(encoding="utf-8"))
    save("baseline.json", {
        "plan_1_sha256": digest(target),
        "review_sha256": digest(REVIEW),
        "protected_source_hashes": baseline,
        "review_files": {rel: digest(ROOT / rel) for rel in (
            "update/claude_review_auto_mode.md", "update/claude_review_auto_mode_2.md",
        )},
    })
    save("runtime_evidence.json", {
        "claude_version": version,
        "permission_mode_option_advertised": "--permission-mode" in help_result["stdout"],
        "dontAsk_choice_advertised": '"dontAsk"' in help_result["stdout"],
        "permission_prompts_option_advertised": "--permission-prompts" in help_result["stdout"],
        "runtime_permission_tests_run": False,
        "new_agent_sessions_started": False,
        "docker_socket_connections_attempted": False,
        "protected_configuration_changed": False,
    })
    print(json.dumps({"baseline_saved": str(target.relative_to(ROOT)),
                      "claude_version": version["stdout"].strip()}, ensure_ascii=False))


def verify():
    baseline = json.loads((OUT / "baseline.json").read_text(encoding="utf-8"))
    errors = []
    if digest(OUT / "plan-1.original.md") != baseline["plan_1_sha256"]:
        errors.append("plan-1 留存副本发生变化")
    if digest(REVIEW) != baseline["review_sha256"]:
        errors.append("plan review 原文发生变化")
    for rel, expected in baseline["review_files"].items():
        if digest(ROOT / rel) != expected:
            errors.append(f"旧 review 原文发生变化：{rel}")
    for rel, item in baseline["protected_source_hashes"].items():
        if digest(ROOT / rel) != item["sha256"]:
            errors.append(f"保护源码变化：{rel}")
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
            if not (1 <= start <= end <= len(raw.splitlines())):
                errors.append(f"行号越界：{rel}#{anchor}")
        else:
            try:
                value = json.loads(raw)
                for key in anchor.split("."):
                    value = value[int(key)] if isinstance(value, list) else value[key]
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                errors.append(f"JSON 指针无效：{rel}#{anchor}：{exc}")
    result = {
        "plan_version": "v2.4-plan-2", "plan_sha256": digest(PLAN),
        "local_evidence_pointers": len(pointers),
        "protected_source_files_checked": len(baseline["protected_source_hashes"]),
        "review_originals_preserved": not any("review" in item for item in errors),
        "errors": errors,
        "scope": "指针与文件一致性；不表示执行模式、隔离或批准入口已经实测",
    }
    save("verification.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    if sys.argv[1:] == ["capture"]:
        capture()
    elif sys.argv[1:] == ["verify"]:
        verify()
    else:
        raise SystemExit("用法：check_revision.py capture|verify")
