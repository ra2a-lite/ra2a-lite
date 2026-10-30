#!/usr/bin/env python3
"""guard_writes —— PreToolUse 守卫（v2.5，PATCH-v2.5 P0-1/P0-3/§D-2）。

两个模式（argv[1]）：
  guard  PreToolUse(Edit|Write|Bash)：受保护路径写拦截 + 白名单脚本放行
         + decision.md 写入前置门（P0-1：阶段产物齐备才允许写决策）
  spawn  PreToolUse(Agent|Task)：spawn 侧记账（P0-3，SubagentStop 漏发路径的对账底账）

Claude Code 协议：stdout 输出 permissionDecision JSON；Codex 下同名事件同理，
不被支持时静默放行（Codex 侧由 rules + OS 层兜底，见 PATCH-v2.5 §D-2/§D-3）。
"""
import json, os, re, subprocess, sys, time

PROTECTED = ("research/ledger/", "research/memory/conclusions.jsonl",
             "research/hooks/", "research/scripts/")
WHITELIST = re.compile(
    r"^\s*python3?\s+("
    r"\$CLAUDE_PROJECT_DIR/|\./|/data/\S+/ra2a/ra2a-lite/)?"
    r"research/scripts/(res_extract|review_queue|commit_conclusion)\.py\s*$")
WRITE_TO_PROTECTED = re.compile(
    r"(>>?|tee\s+-a\s+|tee\s+|sed\s+(?:-[a-zA-Z]*i[a-zA-Z]*\s+|-i\s*)|truncate\s+|shred\s+|:\s*>)[^|;&]*"
    r"(research/ledger/|research/memory/conclusions\.jsonl|research/hooks/|research/scripts/)")

JUDGE_MIN = {"full": 3, "lite": 2}


def root():
    base = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    top = subprocess.run(["git", "-C", base, "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True, timeout=5).stdout.strip()
    return os.path.abspath(top or base)


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}, ensure_ascii=False))
    sys.exit(0)


def rel(path, r):
    try:
        return os.path.relpath(os.path.abspath(path), r).replace(os.sep, "/")
    except ValueError:
        return path


def decision_gate(path, r):
    """P0-1：写 rounds/Rnn/decision.md 前，校验阶段产物齐备。"""
    m = re.match(r"^research/rounds/(R\d{2,})/decision\.md$", path)
    if not m:
        return
    rid = m.group(1)
    base = os.path.join(r, "research", "rounds", rid)
    def exists(*ps):
        return all(os.path.isfile(os.path.join(base, p)) for p in ps)
    p1_ok = exists("p1/analyst.md", "p1/designer.md", "p1/skeptic.md")
    p34_ok = exists("p34/analyst.md", "p34/designer.md", "p34/skeptic.md")
    n_judge = len([f for f in os.listdir(os.path.join(base, "p5"))
                   if f.startswith("judge-")]) if os.path.isdir(
        os.path.join(base, "p5")) else 0
    mode = "full"
    ch = os.path.join(r, "research", "charter.md")
    if os.path.isfile(ch):
        mt = re.search(r"protocol_mode[：:]\s*(\w+)", open(ch, encoding="utf-8",
                                                          errors="replace").read())
        if mt:
            mode = mt.group(1)
    missing = []
    if not (p1_ok or p34_ok):
        missing.append("P1（或 lite 的 P34）三方产出")
    if n_judge < JUDGE_MIN.get(mode, 3):
        missing.append(f"P5 评委文件（{n_judge} < {JUDGE_MIN.get(mode, 3)}）")
    if missing:
        deny(f"P0-1 阶段完整性前置门：{rid} 缺 {'；'.join(missing)}，"
             "不得写 decision.md。缺阶段而继续属协议偏离，须研究员输入"
             " 批准(RL3) 偏离语句并记入 ledger 后，由研究员手动落盘。")


def do_guard(p):
    tool = p.get("tool_name") or p.get("tool") or ""
    ti = p.get("tool_input") or p.get("input") or {}
    r = root()
    if tool in ("Edit", "Write", "MultiEdit"):
        path = rel(ti.get("file_path") or ti.get("path") or "", r)
        if any(path == pk or path.startswith(pk) for pk in PROTECTED):
            deny(f"受保护路径（PROTOCOL §10）：{path}。"
                 "账本只经白名单脚本追加；conclusions 经 /ra-memory 提交。")
        decision_gate(path, r)
    elif tool == "Bash":
        cmd = ti.get("command") or ""
        if WHITELIST.match(cmd):
            return
        if WRITE_TO_PROTECTED.search(cmd):
            deny(f"Bash 试图写受保护路径（PROTOCOL §10）：{cmd[:120]}…"
                 "只允许 python3 research/scripts/{res_extract,review_queue,"
                 "commit_conclusion}.py")
    sys.exit(0)


def do_spawn(p):
    ti = p.get("tool_input") or p.get("input") or {}
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "kind": "spawn",
           "agent_type": ti.get("subagent_type") or ti.get("agent_type"),
           "description": (ti.get("description") or "")[:80]}
    try:
        r = root()
        import fcntl
        path = os.path.join(r, "research", "ledger", "events.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        sys.stderr.write(f"guard_writes spawn 记账失败（不阻断）：{e}\n")
    sys.exit(0)


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else "guard"
    raw = sys.stdin.read()
    try:
        p = json.loads(raw) if raw.strip() else {}
    except ValueError:
        p = {}
    if kind == "spawn":
        do_spawn(p)
    else:
        do_guard(p)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"guard_writes: {e!r}（fail-open，仅记录）\n")
        sys.exit(0)
