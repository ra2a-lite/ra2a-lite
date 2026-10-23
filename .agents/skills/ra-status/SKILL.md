---
name: ra-status
description: 只读查看本轮训练进度：日志、GPU、abort 条件、预计完成时间。研究员询问训练情况时使用。
argument-hint: "[轮次号]"
---
1. 确定轮次：取参数，没有参数就取 STATUS.md 中的当前轮次。读该轮 decision.md 中已批准的 exp_id，以及 erc/*.yaml。
2. 逐个 exp_id 查看：runs/<exp>/ 下的 STARTED/DONE/FAILED/ABORTED 标记；`tail -n 200 runs/<exp>/train.log` 中的步数/总步数、loss、吞吐；估算 ETA；research/ledger/runs.jsonl 中的事件。
3. 用 `nvidia-smi` 核对各卡占用是否与分配一致；用 `tmux ls` 查看会话。
4. 对照 ERC 的 abort_conditions 逐条判定：命中、未命中或无法判定，附 ev。interim_looks 只能用于 ERC 允许的用途。
5. 输出一张简表。命中 abort 条件时，给出证据，建议研究员执行 `tmux kill-session -t <exp>`，由研究员决定是否终止。终止后按 PROTOCOL §5.1 追加一条 ABORTED 记录。
6. 不要因为中期结果好或差（且 ERC 没有声明 futility 规则）而建议提前停。研究员坚持要停时，说明这属于 RL3 协议偏离，需要书面理由，结果将标为 deviated。
7. 全部完成后，提示研究员运行 /ra-round，并更新 STATUS.md 中的"运行中实验"。
