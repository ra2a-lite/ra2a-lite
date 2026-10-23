#!/usr/bin/env bash
# __EXP__ | ERC: research/rounds/__ROUND__/erc/__EXP__.yaml | 锁定后不得修改
# 由 launch.sh 设置 EXP 和 CUDA_VISIBLE_DEVICES；所有输出都写到 runs/$EXP/
set -euo pipefail
CFG=research/rounds/__ROUND__/exp/__EXP__.yaml
NPROC=$(echo "$CUDA_VISIBLE_DEVICES" | tr ',' '\n' | wc -l)
for SEED in 1 2 3; do                 # 必须等于 ERC.seeds
  OUT=runs/$EXP/seed$SEED
  # 训练：命令模板取自 project_card §1；--standalone 会自动选空闲端口，可与其他实验并行
  torchrun --standalone --nproc_per_node=$NPROC <训练入口> --config "$CFG" --seed $SEED --output_dir "$OUT"
  # 评测：使用冻结的评测入口；checkpoint 按 ERC.checkpoint_rule 选取
  python <评测入口> --ckpt "$OUT/<ckpt>" --split dev --output "$OUT/eval_dev.json"
done
