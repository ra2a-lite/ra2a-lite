#!/usr/bin/env bash
# RA2A-Lite 启动脚本。ra-round 替换 __ROUND__ 和"实验清单"后存为 research/rounds/<R>/launch.sh，随锁定提交入库。
# 用法：bash research/rounds/<R>/launch.sh                       启动全部已批准实验（已启动过的自动跳过）
#       bash research/rounds/<R>/launch.sh retry <新id> <源id>    技术故障重跑（须先在 retries.md 登记批准并提交）
# v2.3 修复（P0-1a）：__run 需携带 start_exp 发放的一次性令牌（三重前置校验，堵"空对空"与无参直调）；
#                      启动前 check_approval 核验账本批准原文（锚定正则 + 非 auto + 早于锁定提交 + exp 集合覆盖）。
#                      依据：/data/wangshirui/ra2a/check/demo-conformance-final-verdict.md §3 P0-1a
set -euo pipefail
ROUND=__ROUND__
cd "$(git rev-parse --show-toplevel)"
RD=research/rounds/$ROUND
LEDGER=research/ledger/runs.jsonl
log() { printf '{"ts":"%s","exp_id":"%s","event":"%s","gpus":"%s","commit":"%s","rc":%s}\n' \
        "$(date -Is)" "$1" "$2" "${3:-}" "${4:-}" "${5:-null}" >> "$LEDGER"; }

if [ "${1:-}" = "__run" ]; then            # 内部入口：在 tmux/nohup 中实际运行一个实验（须携带一次性令牌）
  EXP=$2; GPUS=$3; SCRIPT=$4; TOKEN_ARG="${5:-}"; DIR=runs/$EXP
  # 三重前置：令牌参数非空 + .token 存在且非空 + 内容一致（v2.1 修正：两侧皆空会使比较为真）
  if [ -z "$TOKEN_ARG" ] || [ ! -s "$DIR/.token" ] || [ "$TOKEN_ARG" != "$(cat "$DIR/.token")" ]; then
    echo "✗ __run 令牌缺失或不符。智能体会话请勿直接调用 __run；启动入口是 bash research/rounds/$ROUND/launch.sh"; exit 1
  fi
  export EXP CUDA_VISIBLE_DEVICES=$GPUS
  set +e; bash "$SCRIPT" > "$DIR/train.log" 2>&1; rc=$?; set -e
  if [ $rc -eq 0 ]; then ev=DONE; else ev=FAILED; fi
  date -Is > "$DIR/$ev"; log "$EXP" "$ev" "$GPUS" "$(cat "$DIR/COMMIT")" "$rc"; exit $rc
fi

# ---- 启动者检查：智能体会话只有在 launch_mode=B 且运行时为 Claude Code 时才能启动 ----
AGENT=0
if [ -n "${CLAUDECODE:-}" ] || [ -n "${CODEX_SANDBOX:-}" ] || [ -n "${CODEX_SANDBOX_NETWORK_DISABLED:-}" ]; then AGENT=1; fi
if [ "${CUDA_VISIBLE_DEVICES+set}" = set ] && [ -z "${CUDA_VISIBLE_DEVICES}" ]; then AGENT=1; fi
MODE=$(grep -E '^- launch_mode:' research/charter.md | awk '{print $3}')
if [ "$AGENT" = 1 ] && { [ "$MODE" != B ] || [ -z "${CLAUDECODE:-}" ]; }; then
  echo "✗ 检测到智能体会话环境（launch_mode=${MODE:-?}）。请研究员在自己的终端运行本脚本。"; exit 1
fi

# ---- 预注册与代码检查 ----
[ -z "$(git status --porcelain -- "$RD")" ] || { echo "✗ 本轮文件有未提交或被修改的内容（未锁定，或锁定后被改）"; exit 1; }
git ls-files --error-unmatch "$RD/launch.sh" >/dev/null 2>&1 || { echo "✗ launch.sh 未提交"; exit 1; }
grep -q '^status: approved' "$RD/decision.md" || { echo "✗ decision.md 不是 approved 状态"; exit 1; }
git diff --quiet HEAD -- . ':(exclude)research' ':(exclude)runs' || { echo "✗ 有未提交的代码改动"; exit 1; }
[ -z "$(git ls-files --others --exclude-standard -- '*.py')" ] || { echo "✗ 有未跟踪的 .py 文件"; exit 1; }
COMMIT=$(git rev-parse HEAD)

# ---- 批准核验（v2.3 P0-1a①）：decision.md 的 approved 状态必须有人类批准原文背书 ----
# 四重校验：锚定正则（覆盖 批准 R03: 与 批准(RL3) R03:，前导"不/勿/别/驳回"判负）；
#           permission_mode ≠ auto（auto 会话的输入不作批准凭据，P0-2）；
#           批准 ts 早于锁定提交；start_exp 清单中每个实验都出现在批准语句里。
check_approval() {
  local EXPS
  EXPS=$(grep -E '^start_exp ' "$0" | awk '{print $2}' | paste -sd, -)
  python3 - "$ROUND" "$EXPS" <<'PYEOF'
import json, re, subprocess, sys
from datetime import datetime
rnd, exps = sys.argv[1], [e for e in sys.argv[2].split(",") if e and not e.startswith("__")]
pat = re.compile(r"^\s*批准(\s*\(RL3\))?\s+" + re.escape(rnd) + r"\s*[:：]")
def parse_ts(s):
    s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", (s or "").strip())
    try: return datetime.fromisoformat(s)
    except ValueError: return None
lock = subprocess.run(["git", "log", "-1", "--format=%cI", "--", "research/rounds/" + rnd],
                      capture_output=True, text=True).stdout.strip()
lock_dt = parse_ts(lock)
try:
    fh = open("research/ledger/human_inputs.jsonl", encoding="utf-8")
except FileNotFoundError:
    sys.exit("✗ 找不到 research/ledger/human_inputs.jsonl，无法核验批准")
ok, approved = False, set()
for line in fh:
    try: r = json.loads(line)
    except Exception: continue
    p = r.get("payload") or {}
    pr = (p.get("prompt") or "").strip()
    if not pat.match(pr): continue
    if pr.startswith(("不", "勿", "别", "驳回")): continue
    if (p.get("permission_mode") or "") == "auto": continue
    if lock_dt and (parse_ts(r.get("ts")) or lock_dt) > lock_dt: continue
    ok = True
    approved |= set(re.findall(re.escape(rnd) + r"-E\d+(?:\.\d+)?", pr))
if not ok:
    sys.exit(f"✗ 账本中无 {rnd} 的合格批准语句（须为非 auto 权限模式、早于锁定提交的 批准/批准(RL3) 原文）")
missing = [e for e in exps if e not in approved]
if missing:
    sys.exit("✗ 以下实验未出现在批准语句中: " + ", ".join(missing))
PYEOF
}
check_approval

start_exp() {   # start_exp <exp_id> <gpu_ids> <exp脚本的完整相对路径>
  local EXP=$1 GPUS=$2 SCRIPT=$3 DIR=runs/$1
  if [ -e "$DIR/STARTED" ]; then echo "• 跳过 $EXP：已启动过（幂等）"; return 0; fi
  if [ -n "$(nvidia-smi -i "$GPUS" --query-compute-apps=pid --format=csv,noheader 2>/dev/null)" ]; then
    echo "✗ $EXP：GPU $GPUS 上已有进程，未启动"; return 1; fi
  mkdir -p "$DIR"; date -Is > "$DIR/STARTED"; echo "$COMMIT" > "$DIR/COMMIT"
  local TOKEN; TOKEN=$(head -c16 /dev/urandom | od -An -tx1 | tr -d ' \n')   # hex，避免 NUL 进 argv
  printf '%s' "$TOKEN" > "$DIR/.token"                                        # 无尾换行（对 diff/hash 校验保持确定）
  log "$EXP" STARTED "$GPUS" "$COMMIT"
  if command -v tmux >/dev/null; then
    tmux new-session -d -s "$EXP" "bash $RD/launch.sh __run $EXP $GPUS $SCRIPT $TOKEN"
    echo "✓ 已启动 $EXP（GPU $GPUS）。查看：tmux attach -t $EXP；日志：$DIR/train.log"
  else
    nohup bash "$RD/launch.sh" __run "$EXP" "$GPUS" "$SCRIPT" "$TOKEN" >/dev/null 2>&1 &
    echo "✓ 已启动 $EXP（GPU $GPUS，nohup）。日志：$DIR/train.log"
  fi
}

if [ "${1:-}" = "retry" ]; then
  NEW=$2; SRC=$3
  git ls-files --error-unmatch "$RD/retries.md" >/dev/null 2>&1 && grep -q "^| *$NEW *| *$SRC *|" "$RD/retries.md" \
    || { echo "✗ $NEW 未在已提交的 retries.md 中登记批准"; exit 1; }
  SPEC=$(grep -E "^start_exp $SRC " "$0" | head -1 || true)
  [ -n "$SPEC" ] || { echo "✗ 找不到源实验 $SRC"; exit 1; }
  set -- $SPEC; start_exp "$NEW" "$3" "$4"; exit 0
fi

# ---- 已批准实验清单（与 decision.md、erc/ 一一对应；路径写全，不用变量）----
start_exp __ROUND__-E1 0,1,2,3 research/rounds/__ROUND__/exp/__ROUND__-E1.sh
start_exp __ROUND__-E2 4,5,6,7 research/rounds/__ROUND__/exp/__ROUND__-E2.sh
# 需要在同一组卡上串行的实验，合并进同一个 exp 脚本；或者等前一个结束后再运行一次本脚本（已启动的会跳过）
