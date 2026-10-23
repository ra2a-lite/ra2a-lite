#!/usr/bin/env python3
"""RA2A-Lite 记账 hook（Claude Code 与 Codex 共用）。只记账，不判断是否放行，任何情况下都 exit 0。
用法：ra_log.py <kind>，hook 事件的 JSON 从 stdin 读入。
  human    UserPromptSubmit：把研究员的每条输入写入 research/ledger/human_inputs.jsonl，作为批准语句的凭据
  subagent SubagentStop：把子代理的最终消息写入 research/ledger/subagent_outputs.jsonl；
           如果消息第一行是 <!-- ra:out Rnn/<路径>.md -->，就把消息原样存到 research/rounds/Rnn/<路径>.md
           （目标文件已存在时不覆盖，改存为 <名>.dup-<时间>.md，并在账本中注明）
  session  SessionStart：把 research/STATUS.md 打印到 stdout，两种运行时都会把它注入上下文
  其他     写入 research/ledger/events.jsonl
"""
import fcntl, hashlib, json, os, pathlib, re, subprocess, sys, time

OUT_RE = re.compile(r"\A\s*<!--\s*ra:out\s+(R\d{2,}/[A-Za-z0-9_./-]+\.md)\s*-->")

# v2.3 P0-1b：ra:out 目标路径白名单（fail-closed）。依据：check/demo-conformance-final-verdict.md §3 P0-1b。
# 激活前置（K9）：真实 ra-* 子代理的 SubagentStop 输入 agent_type 非空且等于角色名——实测通过后，
# 由研究员创建 research/hooks/.whitelist_on（空文件）方才生效；标记不存在时维持旧行为（仅记账，不拦截）。
# ⚠️ 平台若不填 agent_type（账本实测出现过空串），激活白名单会拒绝一切角色输出、流程不可用——此时不得激活。
# 主会话文件（decision.md、brief.md、p2_broadcast.md、p5/candidates-*、p6_synthesis 等）不在任何角色的白名单内。
WHITELIST = {                                   # 角色 → (精确后缀集合, 前缀集合)；后缀指 Rnn/ 之后的部分
    "ra-analyst":  (("A_results.md", "baseline_analysis.md"), ()),
    "ra-skeptic":  (("integrity.md",), ()),
    "ra-designer": ((), ()),
    "ra-judge":    ((), ("p5/judge-",)),
    "ra-verifier": ((), ("p6/verify",)),
}
for _role in ("ra-analyst", "ra-skeptic", "ra-designer"):
    _name = _role.split("-", 1)[1]
    _exacts, _prefixes = WHITELIST[_role]
    WHITELIST[_role] = (_exacts + tuple(f"{_ph}/{_name}.md" for _ph in ("p1", "p3", "p34", "p4", "p8")), _prefixes)


def find_root(p):
    base = os.environ.get("CLAUDE_PROJECT_DIR") or p.get("cwd") or os.getcwd()
    try:
        top = subprocess.run(["git", "-C", base, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        return pathlib.Path(top or base).resolve()
    except Exception:
        return pathlib.Path(base).resolve()


def append(path, rec):
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:      # 三个子代理可能同时结束，所以加锁
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(line)
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)


def save_out(root, msg, agent_type="", enforce=False):
    m = OUT_RE.match(msg)
    if not m:
        return None
    rel = m.group(1)
    if ".." in pathlib.PurePosixPath(rel).parts:
        return "rejected:path"
    rounds = (root / "research" / "rounds").resolve()
    target = (rounds / rel).resolve()
    if rounds not in target.parents:
        return "rejected:path"
    if enforce:                                  # v2.3 P0-1b：白名单判定（fail-closed）
        at = (agent_type or "").strip()
        parts = rel.split("/", 1)
        suffix = parts[1] if len(parts) == 2 else ""
        if not at:
            return "rejected:agent_type_missing"  # 账本实测 agent_type 可能为空串：一律拒绝
        exacts, prefixes = WHITELIST.get(at, ((), ()))
        if suffix not in exacts and not (prefixes and suffix.startswith(tuple(prefixes))):
            return f"rejected:whitelist({at})"
    if target.exists():
        target = target.with_name(f"{target.stem}.dup-{time.strftime('%Y%m%dT%H%M%S')}.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="") as f:   # 原样写入，sha256 与账本一致
        f.write(msg)
    return str(target.relative_to(root))


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else "event"
    raw = sys.stdin.read()
    try:
        p = json.loads(raw) if raw.strip() else {}
    except Exception:
        p = {"raw": raw[:20000]}
    root = find_root(p)
    led = root / "research" / "ledger"
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    if kind == "session":
        st = root / "research" / "STATUS.md"
        if st.exists():
            print("【RA2A-Lite 当前状态：先读，再行动】\n" + st.read_text(encoding="utf-8")[:6000])
        append(led / "events.jsonl", {"ts": now, "kind": "session", "source": p.get("source"),
                                       "session_id": p.get("session_id"), "model": p.get("model")})
        return

    msg = p.get("last_assistant_message") or p.get("prompt") or ""
    rec = {"ts": now, "kind": kind, "session_id": p.get("session_id"),
           "agent_id": p.get("agent_id"), "agent_type": p.get("agent_type"),
           "model": p.get("model"),                       # Codex 每个事件都带 model；Claude 可能为空
           "sha256": hashlib.sha256(msg.encode("utf-8")).hexdigest() if msg else None,
           "payload": p}
    if kind == "human":
        append(led / "human_inputs.jsonl", rec)
    elif kind == "subagent":
        enforce = (root / "research" / "hooks" / ".whitelist_on").exists()   # K9 通过后由研究员创建
        rec["whitelist_enforced"] = enforce
        rec["written_to"] = save_out(root, msg, p.get("agent_type"), enforce) if msg else None
        append(led / "subagent_outputs.jsonl", rec)
    else:
        append(led / "events.jsonl", rec)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:      # 记账失败也不能阻断会话
        try:
            sys.stderr.write(f"ra_log: {e}\n")
        except Exception:
            pass
    sys.exit(0)
