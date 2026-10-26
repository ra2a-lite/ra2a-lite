#!/usr/bin/env python3
"""B0 基线清单：对治理与受保护文件生成 sha256 清单 + 工具版本 + git 状态快照。

依据：update/final_modification_plan.md §3（B0：锁定修改基线与部署能力）、§8（各批：research/runtime/checks/）。
用法（在本仓库根目录运行）：
  python3 research/runtime/checks/baseline_manifest.py <输出目录>            # 生成 manifest.json + manifest.md
  python3 research/runtime/checks/baseline_manifest.py --verify <manifest.json>  # 对比当前树与基线，报告差异
说明：
- 只读仓库内容，不修改任何文件；--verify 也只读。
- ledger/ 与账本类文件持续只增，其哈希仅作快照记录（snapshot 段），不进入 verify 比对。
- 本脚本属 research/runtime/checks/（普通源码，agent 可编辑）；运行它需要逐次权限确认是有意为之：
  允许 agent 任意改写的脚本不应获得免确认执行（research/audits/permissions-2026-10-26.md §6.3）。
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]

# 进入 verify 比对的治理/受保护文件（缺失记 added/removed，内容变化记 changed）
# 注意：pathlib 的 "dir/**" 只匹配目录，须写成 "dir/**/*" 才递归匹配文件
PROTECTED_PATTERNS = [
    "AGENTS.md", "CLAUDE.md", ".gitignore",
    "PATCH-v*.md", "CHANGELOG.md",
    "ra2a_lite_8xa100.md", "conformance-final-verdict.md",
    ".claude/**/*", ".agents/**/*", ".codex/**/*",
    "research/PROTOCOL.md", "research/charter.md", "research/rubric.md",
    "research/project_card.md", "research/STATUS.md",
    "research/templates/**/*", "research/hooks/*.py",
    "research/memory/**/*", "research/runtime/**/*",
    "update/**/*", "research/audits/**/*",
]
EXCLUDE_PARTS = {".git", "__pycache__", ".whitelist_on"}
EXCLUDE_NAMES = {".DS_Store"}
# 只增不改的账本/运行产物：记录快照但不进 verify
SNAPSHOT_PATTERNS = ["research/ledger/**/*"]

# 用户/管理层权限来源（存在则记哈希；读取失败不阻断）
EXTERNAL_SOURCES = [
    pathlib.Path.home() / ".claude" / "settings.json",
    pathlib.Path("/etc/claude-code/managed-settings.json"),
    pathlib.Path("/Library/Application Support/ClaudeCode/managed-settings.json"),
]


def sh(args, timeout=30):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        return {"argv": args, "rc": r.returncode, "stdout": r.stdout.strip()[:4000],
                "stderr": r.stderr.strip()[:1000]}
    except Exception as e:  # noqa: BLE001
        return {"argv": args, "rc": None, "stdout": "", "stderr": str(e)[:500]}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_files(patterns, exclude_dir=None):
    seen = {}
    for pat in patterns:
        for p in sorted(ROOT.glob(pat)):
            if not p.is_file() or p.is_symlink():
                continue
            rel = str(p.relative_to(ROOT))
            if any(part in EXCLUDE_PARTS for part in p.parts) or p.name in EXCLUDE_NAMES:
                continue
            if exclude_dir is not None and str(exclude_dir.resolve()) in str(p.resolve()):
                continue  # 排除清单自身的输出目录，避免自引用
            seen[rel] = True
    return sorted(seen)


def collect(exclude_dir=None):
    files = {}
    for rel in iter_files(PROTECTED_PATTERNS, exclude_dir):
        p = ROOT / rel
        files[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
    snapshot = {}
    for rel in iter_files(SNAPSHOT_PATTERNS, exclude_dir):
        p = ROOT / rel
        n_lines = None
        try:
            with open(p, "rb") as f:
                n_lines = sum(1 for _ in f)
        except Exception:  # noqa: BLE001
            pass
        snapshot[rel] = {"sha256": sha256_file(p), "lines": n_lines}
    symlinks = {}
    for d in (".claude", ".agents", ".codex"):
        for p in sorted((ROOT / d).rglob("*")):
            if p.is_symlink():
                symlinks[str(p.relative_to(ROOT))] = os.readlink(p)
    external = {}
    for src in EXTERNAL_SOURCES:
        key = str(src)
        if src.is_file():
            external[key] = {"sha256": sha256_file(src), "bytes": src.stat().st_size}
        else:
            external[key] = {"exists": False}
    return files, snapshot, symlinks, external


def build(out_dir):
    out = pathlib.Path(out_dir)
    files, snapshot, symlinks, external = collect(out.resolve() if out.exists() else (out.absolute()))
    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "purpose": "RA2A-Lite demo-revised B0 基线（update/final_modification_plan.md §3）",
        "git": {
            "head": sh(["git", "rev-parse", "HEAD"]),
            "branch": sh(["git", "branch", "--show-current"]),
            "describe": sh(["git", "describe", "--tags", "--always"]),
            "status_short": sh(["git", "status", "--short"]),
        },
        "tools": {
            "claude_version": sh(["claude", "--version"]),
            "codex_version": sh(["codex", "--version"]),
            "note": "权限相关 hook 事件（PermissionRequest/Notification）与 disableAutoMode 键在本机 2.1.247 二进制内存在（静态字符串证据）；运行时行为未验收",
        },
        "permission_sources_external": external,
        "protected_files": files,
        "mutable_snapshot": snapshot,
        "symlinks": symlinks,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    lines = [
        "# B0 基线清单（%s）" % manifest["generated_at"],
        "",
        "- git HEAD：`%s`（branch=%s，describe=%s）" % (
            manifest["git"]["head"].get("stdout", "?"),
            manifest["git"]["branch"].get("stdout", "?"),
            manifest["git"]["describe"].get("stdout", "?")),
        "- Claude：%s；Codex：%s" % (
            manifest["tools"]["claude_version"].get("stdout", "?"),
            manifest["tools"]["codex_version"].get("stdout", "?")),
        "- 受保护/治理文件：%d 项（哈希见 manifest.json）" % len(files),
        "- 账本快照：%d 个文件（只增，不进 verify）" % len(snapshot),
        "- 符号链接：%s" % json.dumps(symlinks, ensure_ascii=False),
        "- git status（生成时）：见 manifest.json git.status_short",
        "",
        "| 文件 | sha256（前 16 位） |",
        "|---|---|",
    ]
    for rel, meta in files.items():
        lines.append("| %s | %s |" % (rel, meta["sha256"][:16]))
    (out / "manifest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("manifest written: %s (%d protected files)" % (out, len(files)))


def verify(manifest_path):
    m = json.loads(pathlib.Path(manifest_path).read_text(encoding="utf-8"))
    mdir = pathlib.Path(manifest_path).parent.resolve()
    try:
        prefix = mdir.relative_to(ROOT).as_posix() + "/"
    except ValueError:
        prefix = None
    # 清单目录内的条目两侧都忽略：清单不可能稳定包含自身哈希
    drop = (lambda rel: prefix is not None and rel.startswith(prefix))
    base = {k: v for k, v in m["protected_files"].items() if not drop(k)}
    cur = {k: v for k, v in collect(mdir)[0].items() if not drop(k)}
    base_set, cur_set = set(base), set(cur)
    changed = sorted(r for r in base_set & cur_set if base[r]["sha256"] != cur[r]["sha256"])
    added = sorted(cur_set - base_set)
    removed = sorted(base_set - cur_set)
    print("baseline: %s (git %s)" % (m.get("generated_at"), m.get("git", {}).get("head", {}).get("stdout", "?")))
    print("changed : %d" % len(changed))
    for r in changed:
        print("  C %s  %s -> %s" % (r, base[r]["sha256"][:12], cur[r]["sha256"][:12]))
    print("added   : %d" % len(added))
    for r in added:
        print("  A %s" % r)
    print("removed : %d" % len(removed))
    for r in removed:
        print("  D %s" % r)
    return 0 if not (changed or added or removed) else 1


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--verify":
        sys.exit(verify(sys.argv[2]))
    if len(sys.argv) != 2:
        sys.stderr.write(__doc__)
        sys.exit(2)
    build(sys.argv[1])


if __name__ == "__main__":
    main()
