#!/usr/bin/env python3
"""Lite 文档一致性检查：ra2a_lite_8xa100.md §5 代码块 vs 仓库实际文件。

依据：ra2a_lite_8xa100.md §5 开头横幅（"生成文件与 §5 不得漂移"，差异须登记）；
update/final_modification_plan.md D19（同步维护、不做全量覆盖）、§8（各批：research/runtime/checks/）、T11。
用法：
  python3 research/runtime/checks/lite_doc_sync.py --check                 # 全量比对，漂移则退出码 1
  python3 research/runtime/checks/lite_doc_sync.py --apply <仓库路径> ...   # 把指定文件的 §5 代码块替换为实际文件内容
模式说明：
  verbatim   目标态=逐字一致；可 --apply
  check_only 受保护文件（rubric/charter/memory 模板等）：只报告漂移，绝不自动改写文档块
  skip       模板对实例（如 STATUS.md），不参与比对
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
LITE = ROOT / "ra2a_lite_8xa100.md"

PAIRS = [
    # （仓库相对路径, 模式）
    ("AGENTS.md", "verbatim"),
    ("CLAUDE.md", "verbatim"),
    ("research/PROTOCOL.md", "verbatim"),
    ("research/charter.md", "check_only"),
    ("research/rubric.md", "check_only"),
    ("research/project_card.md", "check_only"),
    ("research/STATUS.md", "skip"),
    ("research/memory/knowledge.md", "check_only"),
    ("research/memory/negative_results.md", "check_only"),
    ("research/memory/hypotheses.md", "check_only"),
    ("research/memory/playbook.md", "check_only"),
    ("research/templates/meta.yaml", "verbatim"),
    ("research/templates/erc.yaml", "verbatim"),
    ("research/templates/brief.md", "verbatim"),
    ("research/templates/decision.md", "verbatim"),
    ("research/templates/cr.md", "verbatim"),
    ("research/templates/exp.sh", "verbatim"),
    ("research/templates/launch.sh", "verbatim"),
    (".claude/agents/ra-analyst.md", "verbatim"),
    (".claude/agents/ra-designer.md", "verbatim"),
    (".claude/agents/ra-skeptic.md", "verbatim"),
    (".claude/agents/ra-judge.md", "verbatim"),
    (".claude/agents/ra-verifier.md", "verbatim"),
    (".agents/skills/ra-init/SKILL.md", "verbatim"),
    (".agents/skills/ra-round/SKILL.md", "verbatim"),
    (".agents/skills/ra-status/SKILL.md", "verbatim"),
    (".agents/skills/ra-launch/SKILL.md", "verbatim"),
    (".agents/skills/ra-memory/SKILL.md", "verbatim"),
    (".agents/skills/ra-audit/SKILL.md", "verbatim"),
    (".claude/settings.json", "verbatim"),
    ("research/hooks/ra_log.py", "verbatim"),
    (".codex/config.toml", "verbatim"),
    (".codex/hooks.json", "verbatim"),
    (".codex/rules/ra.rules", "verbatim"),
    (".codex/agents/ra-analyst.toml", "verbatim"),
    (".codex/agents/ra-designer.toml", "verbatim"),
    (".codex/agents/ra-skeptic.toml", "verbatim"),
    (".codex/agents/ra-judge.toml", "verbatim"),
    (".codex/agents/ra-verifier.toml", "verbatim"),
]

LOOKBACK = 12  # 从围栏向上找锚点的最大行数


def is_anchor(line, repo_path):
    """锚点行 = 行首就是反引号包裹的完整路径（可带尾注），或 §5 小节标题。"""
    s = line.strip()
    tok = "`%s`" % repo_path
    return s.startswith(tok) or (s.startswith("#") and tok in s)


def find_fence(lines, repo_path):
    """返回 (open_idx, close_idx, anchor_idx)；围栏=以 ~~~ 开头的行。"""
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("~~~"):
            anchor = None
            for j in range(i - 1, max(i - 1 - LOOKBACK, -1), -1):
                s = lines[j].strip()
                if s.startswith("~~~"):      # 上一代码块：越界
                    break
                if is_anchor(lines[j], repo_path):
                    anchor = j
                    break
            if anchor is None:
                continue
            for k in range(i + 1, len(lines)):
                if lines[k].lstrip().startswith("~~~"):
                    return i, k, anchor
            return i, None, anchor  # 未闭合
    return None, None, None


def block_text(lines, o, c):
    return "\n".join(lines[o + 1:c]).rstrip("\n")


def file_text(repo_path):
    p = ROOT / repo_path
    if not p.is_file():
        return None
    with open(p, "r", encoding="utf-8", newline="") as f:   # 保留文件原始行尾，供严格比对
        return f.read().rstrip("\n")


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def check():
    lines = LITE.read_text(encoding="utf-8").split("\n")
    rows, drifted = [], []
    for path, mode in PAIRS:
        if mode == "skip":
            continue
        o, c, a = find_fence(lines, path)
        if o is None:
            rows.append({"path": path, "mode": mode, "status": "anchor_not_found"})
            drifted.append(path)
            continue
        if c is None:
            rows.append({"path": path, "mode": mode, "status": "unclosed_fence"})
            drifted.append(path)
            continue
        blk, ftxt = block_text(lines, o, c), file_text(path)
        if ftxt is None:
            rows.append({"path": path, "mode": mode, "status": "file_missing"})
            drifted.append(path)
            continue
        same = blk == ftxt
        rows.append({"path": path, "mode": mode, "status": "in_sync" if same else "drifted",
                     "block_sha12": sha(blk), "file_sha12": sha(ftxt)})
        if not same:
            drifted.append(path)
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    print("---- summary: %d compared, %d drifted %s" % (
        len(rows), len(drifted), drifted if drifted else ""))
    return 1 if drifted else 0


def apply_pairs(targets):
    allowed = {p: m for p, m in PAIRS}
    lines = LITE.read_text(encoding="utf-8").split("\n")
    changed = 0
    for t in targets:
        mode = allowed.get(t)
        if mode is None:
            sys.stderr.write("skip %s: 不在登记表\n" % t)
            continue
        if mode != "verbatim":
            sys.stderr.write("refuse %s: 模式=%s，只登记不自动改写\n" % (t, mode))
            continue
        o, c, a = find_fence(lines, t)
        if o is None or c is None:
            sys.stderr.write("skip %s: 未找到/未闭合代码块\n" % t)
            continue
        ftxt = file_text(t)
        if ftxt is None:
            sys.stderr.write("skip %s: 文件不存在\n" % t)
            continue
        lines[o + 1:c] = ftxt.split("\n")
        changed += 1
        print("applied: %s (block L%d-L%d)" % (t, o + 1, c))
    if changed:
        LITE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("ra2a_lite_8xa100.md updated (%d block(s))" % changed)


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--check":
        sys.exit(check())
    if len(sys.argv) >= 3 and sys.argv[1] == "--apply":
        apply_pairs(sys.argv[2:])
        return
    sys.stderr.write(__doc__)
    sys.exit(2)


if __name__ == "__main__":
    main()
