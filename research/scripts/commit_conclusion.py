#!/usr/bin/env python3
"""commit_conclusion —— conclusions.jsonl 的唯一写入器（v2.5，PROTOCOL §11 / R8）。

由 /ra-memory 在研究员批准后调用：从 stdin 读一行结论 JSON，锁内完成
「读取 → 校验 → 分配版本 → 计算 content_hash → 追加」整个事务（PATCH-v2.5 Q1）。

校验规则（任一失败即拒绝，exit 2）：
  R8   approval_ref 非空；origin.cr 对应文件存在；
  Q1   id 格式合法；v 缺省时自动分配（= 该 id 现有最大 v + 1）；
       supersedes 中每个 ID@v 必须已存在且 v 小于新 v；
  P1-4 kind=hypothesis 且状态为定论性（refuted/supported/confirmed/rejected/disproved）
       时，必须带 band_source{exp,band}，且该 RES 行存在于 results.jsonl、
       档位不得属于不可判定族（no_diff/no_difference/*_flat/*negligible/marginal）——
       防 H-003 型判读升格（R02 曾把 no_diff 档写成 refuted）；
  P1-5 id 不得复用不同 claim（同 id 历史中已存在相同 claim 的最高版可直接重引，不给新 v）。

无任何路径参数（输出硬编码）。content_hash = 规范化 JSON（去自身字段，sort_keys）。
"""
import fcntl, hashlib, json, os, re, subprocess, sys

CONC_REL = "research/memory/conclusions.jsonl"
RES_REL = "research/ledger/results.jsonl"
ID_RE = re.compile(r"^(H|NR|K|CHAMP|DEC)-[A-Za-z0-9.\-]+$")
KINDS = {"hypothesis", "negative", "knowledge", "champion", "decision"}
DEFINITIVE = {"refuted", "rejected", "supported", "confirmed", "disproved"}
UNDET = re.compile(r"^(no_diff|no_difference|marginal|note)$|flat|negligible")


def find_root():
    base = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    top = subprocess.run(["git", "-C", base, "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True, timeout=5).stdout.strip()
    root = os.path.abspath(top or base)
    if not os.path.isfile(os.path.join(root, CONC_REL)):
        sys.exit("commit_conclusion: 找不到 conclusions.jsonl（不在 Lite 仓库内？）")
    return root


def fail(msg):
    sys.stderr.write(f"commit_conclusion: 拒绝 —— {msg}\n")
    sys.exit(2)


def main():
    if len(sys.argv) > 1:
        fail("不接受任何参数（输出路径硬编码）")
    root = find_root()
    try:
        row = json.loads(sys.stdin.read())
    except ValueError as e:
        fail(f"stdin 不是合法 JSON：{e}")

    if row.get("kind") not in KINDS:
        fail(f"kind 必须 ∈ {sorted(KINDS)}")
    if not ID_RE.match(row.get("id") or ""):
        fail(f"id 格式不合法：{row.get('id')}")
    if not row.get("approval_ref"):
        fail("approval_ref 为空 —— R8：结论行必须绑定研究员批准记录")
    cr = (row.get("origin") or {}).get("cr")
    if not cr or not os.path.isfile(os.path.join(
            root, "research/memory/proposals/applied", cr + ".md")):
        fail(f"origin.cr 不是 applied 提案：{cr}")

    conc_path = os.path.join(root, CONC_REL)
    with open(conc_path, encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        existing = [json.loads(l) for l in f if l.strip()]
        fcntl.flock(f, fcntl.LOCK_UN)
    by_addr = {f'{r["id"]}@v{r["v"]}': r for r in existing if r.get("kind") != "genesis"}

    # Q1 supersedes 校验 + 版本分配
    sup = row.get("supersedes") or []
    for addr in sup:
        old = by_addr.get(addr)
        if not old:
            fail(f"supersedes 指向不存在的版本：{addr}")
    cur_v = max([r["v"] for r in existing if r.get("id") == row["id"]], default=0)
    row.setdefault("v", cur_v + 1)
    if row["v"] != cur_v + 1:
        fail(f"版本号必须递增：当前最大 v{cur_v}，应写 v{cur_v + 1}")
    for addr in sup:
        if by_addr[addr]["v"] >= row["v"]:
            fail(f"supersedes 的版本不小于新版本：{addr}")

    # P1-4 判读升格检查
    if row["kind"] == "hypothesis" and row.get("status") in DEFINITIVE:
        bs = row.get("band_source")
        if not bs or not bs.get("exp") or not bs.get("band"):
            fail("定论性状态必须带 band_source{exp,band}（P1-4）")
        res_rows = []
        rp = os.path.join(root, RES_REL)
        if os.path.isfile(rp):
            res_rows = [json.loads(l) for l in open(rp, encoding="utf-8") if l.strip()]
        hit = [r for r in res_rows if r.get("exp_id") == bs["exp"]
               and r.get("interpretation_band") == bs["band"]]
        if not hit:
            fail(f"band_source 在 results.jsonl 中不存在：{bs['exp']}={bs['band']}")
        if UNDET.search(bs["band"]):
            fail(f"判读档 {bs['band']} 属不可判定族，禁写定论性状态 "
                 f"「{row['status']}」（H-003 教训；应写 tested_flat/unresolved_*）")

    row.pop("content_hash", None)
    canon = json.dumps({k: v for k, v in row.items() if k != "content_hash"},
                       ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    row["content_hash"] = "sha256:" + hashlib.sha256(
        canon.encode("utf-8")).hexdigest()

    with open(conc_path, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)
    print(f"commit_conclusion: {row['id']}@v{row['v']} 已追加（{CONC_REL}）")


if __name__ == "__main__":
    main()
