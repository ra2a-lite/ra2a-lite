#!/usr/bin/env python3
"""review_queue —— 受影响清单生成器（v2.5，PROTOCOL §11 / PATCH-v2.5）。

用法：python3 research/scripts/review_queue.py R05    （唯一参数：轮次号）

扫描 conclusions.jsonl 中 origin.round == 该轮 的 supersede 事件，对每个被取代
结论 ID 检索全部轮次产物与 STATUS.md 的引用，三档分类（missing/stale/
legacy_unversioned），写出 research/rounds/<R>/work/review-queue.md（路径硬编码）。
只读派生：不改写历史文件、不自动触发实验（红线 3）。无其他参数（防 confused-deputy）。
"""
import json, os, re, subprocess, sys

CONC_REL = "research/memory/conclusions.jsonl"


def find_root():
    base = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    top = subprocess.run(["git", "-C", base, "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True, timeout=5).stdout.strip()
    root = os.path.abspath(top or base)
    if not os.path.isfile(os.path.join(root, CONC_REL)):
        sys.exit("review_queue: 不在 RA2A-Lite 仓库内")
    return root


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r"R\d{2,}", sys.argv[1]):
        sys.exit("用法：python3 research/scripts/review_queue.py R05（仅轮次号参数）")
    rnd = sys.argv[1]
    root = find_root()

    events = []
    for line in open(os.path.join(root, CONC_REL), encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        if (r.get("kind") != "genesis" and (r.get("origin") or {}).get("round") == rnd
                and r.get("supersedes")):
            events.append(r)
    if not events:
        print(f"review_queue: {rnd} 无 supersede 事件，未生成清单")
        return

    targets = {}
    for e in events:
        for addr in e["supersedes"]:
            cid = addr.split("@")[0]
            targets[cid] = {"new": f'{e["id"]}@v{e["v"]}',
                            "reason": e.get("supersede_reason", "")}

    scans = []
    rounds_dir = os.path.join(root, "research", "rounds")
    for rid in sorted(os.listdir(rounds_dir)):
        for dirpath, _dirs, files in os.walk(os.path.join(rounds_dir, rid)):
            for fn in sorted(files):
                if fn.endswith((".md", ".yaml", ".yml")):
                    scans.append(os.path.join(dirpath, fn))
    st = os.path.join(root, "research", "STATUS.md")
    if os.path.isfile(st):
        scans.append(st)

    items = []
    for path in scans:
        rel = os.path.relpath(path, root)
        try:
            txt = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for cid, meta in targets.items():
            pat = re.compile(re.escape(cid) + r"(?:@v(\d+))?")
            for i, ln in enumerate(txt.splitlines(), 1):
                m = pat.search(ln)
                if not m:
                    continue
                if m.group(1) is None:
                    cat = "legacy_unversioned"
                elif int(m.group(1)) < int(meta["new"].split("@v")[1]):
                    cat = "stale"
                else:
                    cat = "current"
                items.append({"file": rel, "line": i, "id": cid, "cat": cat,
                              "text": ln.strip()[:100], **meta})

    out = os.path.join(rounds_dir, rnd, "work", "review-queue.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    L = [f"# 受影响清单（review queue）—— {rnd} 的 supersede 事件", ""]
    for cid, meta in targets.items():
        L.append(f"- {cid} → {meta['new']}：{meta['reason'] or '（见对应 CR）'}")
    L += ["", f"共 {len(items)} 处引用（stale {sum(1 for x in items if x['cat']=='stale')}"
          f" / legacy {sum(1 for x in items if x['cat']=='legacy_unversioned')}"
          f" / current {sum(1 for x in items if x['cat']=='current')}）", "",
          "| # | 结论 | 文件 | 行 | 类别 | 建议动作 | 引用原文 |", "|---|---|---|---|---|---|---|"]
    for k, x in enumerate(items, 1):
        act = {"stale": "重审该处表述是否仍成立",
               "legacy_unversioned": "迁移补 ID@vN；核对语义",
               "current": "已是新版本，无需动作"}[x["cat"]]
        L.append(f"| {k} | {x['id']} | {x['file']} | L{x['line']} | {x['cat']} "
                 f"| {act} | {x['text']} |")
    L += ["", "> 本清单只喂给下一轮 P1 与讨论门，不自动改写历史，不自动触发实验。", ""]
    open(out, "w", encoding="utf-8").write("\n".join(L))
    print(f"review_queue: {len(items)} 处引用 → {os.path.relpath(out, root)}")


if __name__ == "__main__":
    main()
