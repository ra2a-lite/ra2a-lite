#!/usr/bin/env python3
"""res_extract —— RES 实验判定行的唯一写入器（v2.5，PROTOCOL §5 阶段 A / §11）。

从 ERC × A_results × runs 确定性派生实验判定，追加到 research/ledger/results.jsonl。
约束（防 confused-deputy，PATCH-v2.5 §D-4）：
  - 无任何输出路径参数（输出硬编码）；仓库根由 git 探测；
  - 仅追加（flock）；已存在的 exp 不重写；行 schema 合法才写；
  - 只提取 A_results 中【明示】的落档声明，禁止猜测档位（提取失败=undeclared）。
用法：python3 research/scripts/res_extract.py   （在仓库内执行，无参数）
"""
import fcntl, json, os, re, subprocess, sys, time

OUT_REL = "research/ledger/results.jsonl"
EXPS_RE = re.compile(r"R\d{2,}-E\d+(?:\.r\d+)?")

BAND_PATTERNS = [
    re.compile(r"\*\*`?([a-z_0-9]+)`?\*\*（"),
    re.compile(r"：\*\*`?([a-z_0-9]+)`?\*\*"),
    re.compile(r"落\s+`?([a-z_0-9]+)`?\s*档"),
    re.compile(r"\*\*`?([a-z_0-9]+)`?\s*档(?:\s*×\d+)?\*\*"),
    re.compile(r"→\s*\*\*`([a-z_0-9]+)`\*\*"),
    re.compile(r"判[档定]?\s*`([a-z_0-9]+)`"),
    re.compile(r"[（(]\s*exploratory[：:]\s*`([a-z_0-9]+)`"),
]
TECH_FAIL = re.compile(r"\*\*无法判定\*\*")


def find_root():
    base = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    top = subprocess.run(["git", "-C", base, "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True, timeout=5).stdout.strip()
    root = os.path.abspath(top or base)
    if not os.path.isdir(os.path.join(root, "research", "ledger")):
        sys.exit("res_extract: 不在 RA2A-Lite 仓库内（缺 research/ledger/）")
    return root


def extract_band(a_text, exp_id, window=3):
    """落档归属三段式：主语表格行直取 → ±3 行邻域（无其他实验号）→
    重跑令牌（要求本轮文本提及该实验完整编号）。技术故障只认主语行。"""
    if not a_text:
        return (None, None)
    other = re.compile(r"R\d{2,}-E\d+(?:\.r\d+)?")
    primary = re.compile(r"^\|\s*" + re.escape(exp_id) + r"\b")
    lines = a_text.splitlines()
    hits = [i for i, ln in enumerate(lines) if exp_id in ln]
    for i in hits:
        if primary.search(lines[i]) and TECH_FAIL.search(lines[i]):
            return ("inconclusive_technical", i + 1)
        for pat in BAND_PATTERNS:
            m = pat.search(lines[i])
            if m and (primary.search(lines[i]) or
                      not other.search(lines[i].replace(exp_id, ""))):
                return (m.group(1), i + 1)
    for i in hits:
        for d in range(1, window + 1):
            for j in (i + d, i - d):
                if 0 <= j < len(lines) and not any(
                        t != exp_id for t in other.findall(lines[j])):
                    for pat in BAND_PATTERNS:
                        m = pat.search(lines[j])
                        if m:
                            return (m.group(1), j + 1)
    m_tok = re.match(r"R\d{2,}-(E\d+)\.r(\d+)$", exp_id)
    if m_tok and hits:
        token = (m_tok.group(1) + "r" + m_tok.group(2)).lower()
        for ln in lines:
            if token in ln.lower():
                for pat in BAND_PATTERNS:
                    m = pat.search(ln)
                    if m:
                        return (m.group(1), None)
    return (None, None)


def erc_band_names(txt):
    names, in_blk = set(), False
    for ln in (txt or "").splitlines():
        if re.match(r"^\s*reading_bands\s*:", ln):
            in_blk = True
            continue
        if in_blk:
            m = re.match(r"^\s{2,}([a-z_0-9]+)\s*:", ln)
            if m:
                names.add(m.group(1))
            elif re.match(r"^\S", ln):
                in_blk = False
    return names


def main():
    if len(sys.argv) > 1:
        sys.exit("res_extract: 不接受任何参数（输出路径硬编码，见 PATCH-v2.5 §D-4）")
    root = find_root()
    rounds_dir = os.path.join(root, "research", "rounds")

    erc = {}
    for rid in sorted(os.listdir(rounds_dir)):
        d = os.path.join(rounds_dir, rid, "erc")
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            m = re.match(r"(R\d{2,}-E\d+(?:\.r\d+)?)\.ya?ml$", f)
            if m:
                erc[m.group(1)] = (os.path.join("research", "rounds", rid, "erc", f),
                                   open(os.path.join(d, f), encoding="utf-8",
                                        errors="replace").read())
    runs = {}
    rl = os.path.join(root, "research", "ledger", "runs.jsonl")
    if os.path.exists(rl):
        for line in open(rl, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                runs.setdefault(r.get("exp_id"), []).append(r)
    a_texts = {}
    for rid in sorted(os.listdir(rounds_dir)):
        f = os.path.join(rounds_dir, rid, "A_results.md")
        if os.path.isfile(f):
            a_texts[rid] = open(f, encoding="utf-8", errors="replace").read()

    out_path = os.path.join(root, OUT_REL)
    done = set()
    with open(out_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    done.add(json.loads(line).get("exp_id"))
                except ValueError:
                    pass

    rows = []
    for exp in sorted(set(erc) | set(runs)):
        if exp in done:
            continue
        rid = re.match(r"(R\d{2,})", exp).group(1)
        band = src = ln = None
        for r in sorted(a_texts):
            if r >= rid:
                band, ln_ = extract_band(a_texts[r], exp)
                if band:
                    src, ln = r, ln_
                    break
        erc_rel, erc_txt = erc.get(exp, (None, ""))
        if not band:
            band = ("no_bands_preregistered" if erc_rel and not erc_band_names(erc_txt)
                    else "undeclared")
        started = (runs.get(exp) or [{}])[0]
        rows.append({"schema_version": 1, "kind": "res", "exp_id": exp,
                     "interpretation_band": band,
                     "declared_in": ({"round": src, "file":
                                      f"research/rounds/{src}/A_results.md",
                                      "line": ln} if src else None),
                     "erc": erc_rel,
                     "commit": started.get("commit"),
                     "started_ts": started.get("ts"),
                     "terminal": next((x.get("event") for x in
                                       reversed(runs.get(exp, [])) if x.get("event")
                                       in ("DONE", "FAILED", "ABORTED")), None)})
    # .r2 折叠于母行
    by = {r["exp_id"]: r for r in rows}
    for r in rows:
        m = re.match(r"(R\d{2,}-E\d+)\.r\d+$", r["exp_id"])
        if m and r["interpretation_band"] == "undeclared" and m.group(1) in by:
            p = by[m.group(1)]
            if p["interpretation_band"] not in ("undeclared", "no_bands_preregistered"):
                r["interpretation_band"] = p["interpretation_band"]
                r["declared_in"] = p["declared_in"]
                r["folded_into_parent"] = True

    if rows:
        with open(out_path, "a", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            fcntl.flock(f, fcntl.LOCK_UN)
    print(f"res_extract: 追加 {len(rows)} 行 RES → {OUT_REL}"
          f"（undeclared {sum(1 for r in rows if r['interpretation_band']=='undeclared')}）")


if __name__ == "__main__":
    main()
