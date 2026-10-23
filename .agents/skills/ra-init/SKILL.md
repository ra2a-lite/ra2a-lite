---
name: ra-init
description: 首次接入本项目。只读盘点代码、数据、评测与历史日志，生成 research/project_card.md，起草章程、保护配置和初始记忆提案，交研究员确认。仅在研究员显式调用时使用。
disable-model-invocation: true
---
# /ra-init：只读盘点并起草，不改代码，不启动任何作业

1. 读 AGENTS.md、research/PROTOCOL.md、research/charter.md（模板）。
2. 盘点以下内容（可以并行调用内置的探索子代理）：
   a. 训练入口、配置系统、分布式启动方式及 8 卡用法；
   b. 评测入口、主指标与护栏指标的实现位置（文件:行）、checkpoint 选择方式；
   c. 训练集、dev、test 的位置、规模、格式（test 只记录元信息，不读内容），是否有逐样本预测输出；
   d. 历史试验日志：位置与格式。逐个 run 提取配置要点、commit、种子、主指标、步数、耗时；
   e. 当前 git 状态。有未提交改动的必须报告。
3. 调用 ra-analyst，计算三项：种子噪声 σ（同配置少于 2 个种子时标"未知"）；吞吐与单次训练的 GPU·h；历史最佳结果，作为 champion 候选。
   prompt 只含：目录指针 + 输出指令 `<!-- ra:out R00/baseline_analysis.md -->`。
4. 调用 ra-skeptic，做两项检查：训练集与 dev 的重叠抽检（CPU，哈希）、评测代码完整性检查。test 的重叠检查只给出命令，交研究员执行。
   输出指令：`<!-- ra:out R00/integrity.md -->`
5. 写 research/project_card.md，每个事实都带 ev。
6. 起草以下内容：
   - charter.md 中可由事实推出的字段（指标、基线值、数据路径、硬件）。目标值、预算、里程碑、范围、launch_mode 保留【待定】，在对话中逐项询问研究员；
   - .claude/settings.json 中受保护路径的实际值。日志在仓库外时，补充 permissions.additionalDirectories；
   - 研究员需亲自执行的 OS 保护命令（只列出，不执行）；
   - 记忆提案：champion 初值、历史负结果，写成 research/memory/proposals/CR-R00-NN.md。
7. 向研究员展示：项目卡摘要、待定的章程项、保护命令、提案列表。研究员确认后，编辑 charter.md 和 settings.json（会触发确认），更新 STATUS.md（当前轮次：R00 完成；下一步：/ra-memory，然后 /ra-round R01）。
8. 把运行时版本写入 `research/rounds/R00/meta.yaml`（runtime、models 各角色实际 model ID、rubric_version、platform_changed；P1-2）。请研究员确认后提交：`git add -A research AGENTS.md CLAUDE.md .claude .agents .codex && git commit -m "R00 init"`。
