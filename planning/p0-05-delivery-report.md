# P0-05 交付报告

2026-10-24。完成独立Agent真实任务协议、协同与故障验证；保持无付费模型/真实账户，不开发正式GUI，不修改PFT，停止于本轮。

## 交付入口与数量

- [实验README/复现命令](../experiments/p0-05/README.md)：独立服务、D3适配器、合成任务/产物、原格式夹具、故障与进程工具。
- [专项验证](./p0-05-agent-verification.md)、[协议兼容](./p0-05-protocol-compatibility.md)、[架构发现及实施前反例](./p0-05-architecture-findings.md)。
- [最终专项摘要](../experiments/p0-05/evidence/suite-20261024T061121087692Z/summary.json)：**18测试方法通过、0失败、0错误**。
- [P0-03回归](../experiments/p0-03/evidence/suite-20261024T060828857517Z/summary.json)：18通过；[P0-04回归](../experiments/p0-04/evidence/suite-20261024T060834989387Z/summary.json)：14通过；三类证据独立统计。
- [首轮失败](../experiments/p0-05/evidence/suite-20261024T060420267685Z/summary.json)、[原因](../experiments/p0-05/evidence/development-failures.json)、[交付审计](../experiments/p0-05/evidence/delivery-audit.json)。
- [依赖清单](../experiments/p0-05/dependency-inventory.json)、[哈希锁](../experiments/p0-05/requirements.lock)、[版本/制品核验](../experiments/p0-05/environment-evidence.json)、[离线解析](../experiments/p0-05/offline-resolution-report.json)。

没有把子场景、断言、进程数、来源数、旧117项静态检查或其他回归合并成Agent通过数。首轮18方法中16通过、1方法失败、1方法有两个错误；原证据保留。修正序列化与故障注入标识后完整复测通过。

## 十个问题的回答

1. **是否真正完成独立Agent任务委托？** 是。Agent运行于不同OS进程，真实IPC提交后立即返回taskId并继续异步工作；通过GetTask取得状态/进度和最终Artifact，C1校验后下游执行。没有直接import服务执行函数冒充委托。
2. **是否采用实际A2A？** 是，官方SDK双方1.2.3，标准JSON-RPC SendMessage/GetTask/ListTasks/CancelTask，A2A-Version:1.0，规范参照v1.0.1。未使用非A2A HTTP任务替代方案，也未宣称完整规范/任意第三方互操作通过。
3. **是否需要修改核心调度器？** 需要一个小的恢复扩展点：将原默认在途→unknown分支抽为可覆盖方法，默认语义不变。P0-05 C1子类只恢复原attempt的query，不新增调度器；依赖、审批、预算和本地终态继续由C1控制，原18/14项回归通过。
4. **taskId怎样绑定？** C1快照同一事务记录run、node/scope、attempt、operation、message/context与taskId、Agent/endpoint/能力摘要及deadline；检查远端返回的身份/来源/序号。工作流定义不含这些一次性运行值。
5. **失联后能恢复而不重复提交吗？** 已知taskId的断连和执行器重启均只GetTask，同run/attempt/operation/taskId、任务1；提交响应丢失默认unknown不重发。自有服务profile允许显式ListTasks关联核实，实际测试匹配唯一任务；不能推广为所有A2A服务保证。
6. **取消能否得到可信终态？** 本轮合作服务返回匹配CANCELED时可以，本地才cancelled。不支持、失联或取消后仍完成保持unknown，旧结果不发布；发送按钮/HTTP请求不是停止证明，已发生内部动作不自动撤销。
7. **两个Agent是否安全并行？** 本机两个独立服务的任务执行区间实际重叠，taskId和产物分开，按edge.order正确汇合，未串用。仅自有可信合成服务，不是跨设备调度或恶意Agent安全证明。
8. **结果/产物如何进入原契约？** A2A Artifact data/url→类型化AgentTaskResult与原FileReference；同源/UUID、Schema、来源、大小/媒体、SHA及内容检查后登记合成产物，C1生成validated RuntimeValueEnvelope并检查最终输出。任意返回路径不授予本机读取权限。
9. **平台与Agent各保证什么？** 平台保证自己发起的请求门禁、身份绑定、有限查询、不盲重发、旧结果隔离及本地状态权威；Agent必须实现自己的真实任务状态、取消能力、持久化、去重/核实及内部工具权限。平台无法靠自然语言承诺控制远端全部内部行为。
10. **能否继续真实模型和桌面验证？** 有足够证据继续小范围探针，无足够依据进入正式产品开发或冻结栈。建议下一轮先做无GUI的Tauri/Rust宿主IPC/关闭恢复探针；真实模型预算、usage和取消计费应另行授权验证。本轮没有自动开始下一阶段。

## 变更与保留

新增代码、依赖环境、合成数据、数据库、产物与证据均在experiments/p0-05，planning新增四份报告。架构发现先记录最小恢复冲突及必要修正，再追加实际结果，没有大改旧研究资料或正式模块职责。

旧代码仅修改experiments/p0-03/runtime.py的默认恢复方法提取；P0-04源代码/Server/依赖环境及历史证据保持，原P0-03测试代码/Schema/catalog及P0-01/P0-02报告和静态结果保留。回归在原阶段新增独立UTC证据目录并正常更新latest指针；旧失败与旧成功未覆盖。根/研究索引增量更新，既有文件摘要由baseline-manifest与交付审计逐项核对。

新依赖在p0-05/.venv，42个制品锁确切版本/SHA256，官方SDK Apache-2.0及制品许可/NOTICE保留。wheel离线解析通过不等于干净机器完整安装或跨OS执行通过。没有付费API、真实账户、大模型、不可信Agent/插件、通用计算平台、提权、Git提交/标签/推送。

测试监督器只管理本实验Agent的Job/记录PID；普通Windows进程不是强沙箱，loopback合成标记不是真实账户认证。L1定义加载/诊断、L2目标依赖执行、L3不迁移完整环境边界保持，Linux/macOS没有实际运行。Model/Tool/Agent三类边界继续分开，MCP成果没有被Agent替代或重命名。
