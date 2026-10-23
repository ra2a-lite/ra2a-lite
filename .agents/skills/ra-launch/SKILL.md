---
name: ra-launch
description: 模式 B。在研究员批准、预注册锁定之后，代为执行本轮 launch.sh。仅在研究员显式调用时使用；只适用于 Claude Code。
argument-hint: "<轮次号>"
disable-model-invocation: true
---
1. charter.md 中的 launch_mode 必须是 B。否则停止，请研究员在终端手动执行 `bash research/rounds/<R>/launch.sh`。
2. 核对以下各项，任一项不符就停止：
   - decision.md 的 status 为 approved；
   - 批准原文能在 research/ledger/human_inputs.jsonl 中逐字找到，且时间早于锁定提交；
   - launch.sh 中 start_exp 的实验集合 = 批准集合 = erc/ 中的文件集合；
   - `git status --porcelain -- research/rounds/<R>` 为空；
   - `git log -1 --format=%H -- research/rounds/<R>/launch.sh` 等于 STATUS.md 中的 lock_commit。
3. 用 `nvidia-smi` 确认分配到的 GPU 空闲。
4. 执行 `bash research/rounds/<R>/launch.sh`。这一步会弹出权限确认，也就是启动审批，请研究员核对命令后放行。不得用任何其他方式启动。
5. 更新 STATUS.md。
