---
charter_version: 1
signed_by: 【待定：研究员姓名】
signed_at: 【待定】
second_confirmer: 无            # RL3 需要第二确认人时填写姓名
---
# 研究目标章程
只有研究员可以修改。每次修改都在文末"修订记录"中写一行，属于 RL3。

## G 目标
- G1 主目标：在【dev 集名】上，把【主指标】从基线【x.xx】（ev:…）提升到 ≥【y.yy】，同时满足护栏 C1–C3。
- G2 次目标（可选）：【…】

## C 约束 / 护栏
- C1 【推理延迟 / 参数量 / 显存上限】
- C2 训练数据只能来自【训练数据目录】；引入外部数据或预训练权重须修订章程
- C3 评测代码【评测代码目录】与指标定义冻结

## 范围
- in_scope：【模型结构、优化器与调度、正则化、数据增强与采样、训练时长、蒸馏……】
- out_of_scope：【……】
- forbidden：
  - 用 dev/test 数据训练或调参；
  - 修改评测脚本或指标定义；
  - 依据 test 做选择；
  - 事后挑选种子或 checkpoint。

## M 里程碑
- M1 基线复现：≥3 个种子，得到噪声估计 σ。目标日期【…】
- M2 【…】

## 资源
- 硬件：本机 8×A100【40/80】GB；与他人共享：【是/否】；保留卡：【无】
- 单轮 GPU 预算：【例如 192】GPU·h；单实验上限：【例如 64】GPU·h；总预算：【…】GPU·h
- 单轮最长墙钟：【例如 24】h

## 运行方式
- launch_mode: A                 # A = 研究员手动执行 launch.sh；B = 经权限确认后由 Claude Code 执行
- protocol_mode: full            # full | lite（lite：P3 与 P4 合并，P5 用 2 名评委）
- dev_look_threshold: 【例如 8】   # dev 查看累计到此次数时，brief 提示考虑做 test 确认
- test_set_eval: researcher_only

## 记忆 / 技能 / 规则的变更条件（修改本节属于 RL3）
- 预授权：不改变含义的 playbook.md 格式整理与去重。可直接应用，在下一轮 brief 中报告
- RL2：新增 knowledge、negative_results、hypotheses 条目；更新 champion；修改代理或技能的提示词
- RL3：修改 rubric.md、charter.md、PROTOCOL.md、评测相关内容，以及本节本身

## 修订记录
| 版本 | 日期 | 修改 | 理由 |
|---|---|---|---|
