# P0-03 交付报告

2026-10-24。本轮完成隔离最小运行时与确定性故障验证；停止于P0-03，未开展P0-04，未冻结语言/框架或调整正式模块边界。

## 交付物

- [实验README与运行方法](../experiments/p0-03/README.md)：Python源码、原Schema校验桥、固定mock、合成夹具、故障注入及复现命令。
- [运行验证报告](./p0-03-runtime-verification.md)：T01–T10与审批/数据校验的实际结果、输入和证据位置。
- [架构发现](./p0-03-architecture-findings.md)：最小反例、必要修正建议、Python/Rust/TS取舍、Tauri候选集成与限制。
- [最终执行摘要](../experiments/p0-03/evidence/suite-20261024T034720437972Z/summary.json)：18个测试方法，18通过、0失败、0错误。
- [首轮失败摘要](../experiments/p0-03/evidence/suite-20261024T033548013484Z/summary.json)：18个方法，17通过、1失败、0错误；计时证据问题与修正在验证报告中说明，历史原样保留。
- [契约反例](../experiments/p0-03/evidence/contract-counterexamples.json)、[基线文件摘要](../experiments/p0-03/baseline-manifest.json)、[交付审计](../experiments/p0-03/evidence/delivery-audit.json)。

每个测试运行有独立合成输入、真实运行输出、事件/状态、断言expected/actual、模拟调用/副作用账本及SQLite。T08保存三个实际退出进程的注入点、exit 73与恢复前数据库状态。总数18按unittest方法统计，没有将子场景、断言、117项历史静态检查或资料数量累加成执行通过数。

## 八个问题的回答

1. **P0-02契约能否直接驱动执行？** 文件格式、节点引用、类型、版本和A/B/C原图能够直接驱动原型；但required输出激活、root/node retry作用域仍有歧义，必须依赖显式builtin语义，不能说Schema已经完整或所有节点均可运行。原契约没有被绕过改成自定义模拟图格式。
2. **串行、并行、汇合和分支是否正确？** 已执行的受限语义正确：持久有效输出才解锁下游；B/C真实协作重叠；edge.order汇合；exclusive消去未选路径；strict-all遇必需skip传播skip，遇失败/取消阻断。没有实现any/race或任意循环，不能扩张宣称。
3. **审批是否真正阻断？** 是，在C1可信派发入口检查；未批、拒绝、旧/过期/取消批准均不能产生模拟副作用，重复批准不重复调用，重启不自动批准。未验证任意外部程序的OS强制隔离。
4. **取消、失败和恢复如何？** 明确失败有Error记录；未启动节点直接取消，协作取消确认cancelled，未确认取消或响应丢失unknown，晚到输出丢弃。已提交完成节点恢复不重跑；事务中断未确认节点保守unknown；审批暂停可恢复。只验证进程退出，不等于断电/磁盘容错。
5. **哪些可以安全重试？** none/read、适配器safe-read、明确retryable故障且在maxAttempts以内的节点。每次有独立attempt，逻辑operationId不变。billable/write/unknown不盲重试；idempotent机制未实现而拒绝；崩溃在途即使纯节点也不自动重放。
6. **哪些会导致返工？** 输出按结果激活、策略继承和失败范围、汇合规则、审批授权主体/内容绑定、attempt与iteration身份、未知结果核实、checkpoint唯一权威。应先修订其语义，避免扩散到GUI、插件和恢复格式；反例与建议已记录，未大改历史资料。
7. **是否作为正式引擎基础？** 值得保留为可执行契约/回归参照，尚不值得直接作为正式引擎定案。当前全快照持久化、单进程协作并发、pwsh校验桥、无真实协议和完整金额账本，缺少框架对照/压力/分发测试。Python选择服务验证，不锁死技术栈。
8. **下一轮先验证什么？** 推荐Windows上的自有无副作用MCP stdio服务，连同固定握手/描述、输入输出、协议污染、取消/响应丢失与进程清理；随后再验证Agent任务查询/核实。此处只是建议，没有自动启动下一轮。

## 变更与范围审计

实验代码、夹具、SQLite和证据全部位于experiments/p0-03；planning只新增本轮三个报告。既有文件仅更新根README及研究导航/来源索引共6个Markdown文件。实施前43个文件有baseline-manifest；交付审计对所有43项逐一比较，允许的6项是README.md、research/README.md、research/sources.md及R02/R03/R10的README.md，其余37项应保持原SHA256。

P0-01/P0-02报告、Schema、原catalog、A/B/C、跨环境模板、旧静态检查脚本和结果保持原样。sources仅增量记录S58–S60并标记新统计；根/研究README注明当前状态，原实验设计门槛和历史统计保留。

未修改PFT；未创建正式GUI；没有付费调用、大模型下载、新包安装、真实账户、任意插件执行或Git提交/标签。唯一启动的辅助脚本是本项目新建的校验桥与崩溃工作者。模拟外部账本不访问真实业务系统。

## 完成边界

本轮证明了受限核心语义，并明确找出契约无法仅靠Schema唯一解释之处。L1设计兼容、L2依赖目标环境执行、L3不迁移完整环境的边界保持。实际主机只为Windows；真实MCP/Agent/模型调用、Linux/macOS、OS沙箱、外部框架checkpoint、Tauri IPC、生产性能和持久化故障仍未验证。保持这些未验证项，不能以18个模拟执行测试替代原E01–E07的全部门槛。
