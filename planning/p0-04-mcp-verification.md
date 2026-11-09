# P0-04 MCP 与进程验证报告

2026-10-24，Windows 11 x64 / NT 10.0.22631，Python 3.12.14。真实协议固定MCP 2025-11-25，客户端及服务端官方Python SDK 1.30.0。完整环境和复现步骤见[实验README](../experiments/p0-04/README.md)。

## 实际结果与证据等级

**14个P0-04测试方法通过，0失败、0错误**：[固定摘要](../experiments/p0-04/evidence/suite-20261024T053902557486Z/summary.json)、[完整日志](../experiments/p0-04/evidence/suite-20261024T053902557486Z/unittest.log)、[本次源码/夹具摘要](../experiments/p0-04/evidence/suite-20261024T053902557486Z/source-hashes.json)。原P0-03独立回归**18通过、0失败、0错误**：[回归原始结果](../experiments/p0-03/evidence/suite-20261024T052920513341Z/summary.json)。两个套件分开计数，不把它们说成32个MCP测试。

| 类别 | 证据 | 可得结论 |
| --- | --- | --- |
| SDK与独立Server | T01/T02/T09直接调用官方ClientSession和自有官方SDK Server | 本次固定协议的stdio握手、发现、调用、结构化结果及关闭真实可用 |
| 工作流集成 | T03–T08、T11、T13/T14通过原C1调度 | 节点类型/身份、审批、结果验证和错误语义没有被绕过 |
| 故障Server与拥有进程 | 特定mode及T10实际进程exit 74 | 受控污染/退出/丢响应/取消/执行器退出与Job回收已测试 |
| 静态诊断/原Mock | T12及P0-03回归 | Schema/环境结构、缺失绑定保留定义、旧模拟语义回归；不是Linux运行或真模型/Agent |

这里只接入本项目创建的可信合成Server。真实协议不意味着真实账户、真实业务文件或第三方工具服务。收费模型调用、真实账户连接、Linux/macOS运行均为0。

## 输入、实际输出与断言映射

以下test_*路径均在[通过套件目录](../experiments/p0-04/evidence/suite-20261024T053902557486Z/)下。assertions.json保存expected/actual/passed；所有Server PID、关闭与检查见process.jsonl及每个测试的process-cleanup.json。

| 需求/方法 | 输入与注入 | 实际结果 |
| --- | --- | --- |
| T01 / test_T01_real_sdk_discovery_and_calls | 独立Server；echo中文、add 2.5+3 | 发现6工具、协商2025-11-25；结果保留对象和数值5.5；普通日志仅stderr |
| T02 / test_T02_parameters_outputs_unknown_and_schema_drift | 缺text、text数字、额外字段、infinity、未知工具；bad-output/schema-drift | 无效/无权限调用0条tools/call；不合结构化输出报MCP_OUTPUT_INVALID且下游skip；发现Schema漂移拒绝 |
| T03 / test_T03_stdout_pollution | Server在调用中向stdout写DEBUG非JSON | PROTOCOL_STDOUT_CORRUPT，终止本次Job，节点failed、输出为空，污染不变业务结果 |
| T04 / test_T04_server_abnormal_exit | 工具开始后Server os._exit(62) | SERVER_DISCONNECTED，只读节点failed、attempt1，无SDK隐藏重试 |
| T05 / test_T05_timeout_and_cancellation | 延迟1500ms/节点期限1500ms；调用中取消；ignore-cancel | 初始化和清理从总期限中扣除，得到MCP_REQUEST_TIMEOUT；真实notifications/cancelled可见；用户取消结果unknown、下游cancelled；合作handler另有取消观测，不合作没有伪确认 |
| T06 / test_T06_response_lost_effect_unknown | 审批后合成账本先提交，Server在响应前exit 63 | effect1、tools/call1、attempt1；node/run unknown，无下游；operationId在真实_meta中保留 |
| T07 / test_T07_approval_real_mcp_gate | 未批/拒绝/过期/取消/旧内容/重复批准；慢初始化期间过期 | 未批不启动Server；拒绝/过期/取消/旧批准effect0；有效批准后真实MCP调用1次，重复批准无额外调用；握手时过期报APPROVAL_EXPIRED_BEFORE_MCP、调用0 |
| T08 / test_T08_original_scenario_b_integration | scenario-b-p04-r1，原ToolArgs/ToolResult、5节点链 | 所有5节点succeeded；结果items[0].text为“查找测试资料”；真实调用1；run/attempt身份与C1一致，输出validity=validated |
| T09 / test_T09_process_tree_init_failure_and_duplicate_close | 自有idle子进程、init-exit、不支持版本、重复关闭 | 启动/初始化失败明确报错；已记录的launcher/真实Server/自有子进程全部退出；重复关闭无额外执行 |
| T10 / test_T10_owner_process_crash_recovery | 拥有执行器在派发前、账本提交后响应前、C1成功提交后exit 74 | 三处均实际达到注入点并保留同runId；派发前恢复后调用1；在途恢复unknown且effect仍1；提交后恢复succeeded且不重复调用 |
| T11 / test_T11_safe_retry_owned_by_C1 | 纯工具首次SAFE_TRANSIENT，节点safe/maxAttempts2 | failed→succeeded两个attempt；真实调用2；operationId稳定、attemptId不同，重试仅由C1发起 |
| T12 / test_T12_definition_environment_and_permission_diagnostics | 缺Server、未知节点、无权限、Linux替代绑定、resourceUri声明反例 | 缺Server阻止执行但原图原样保留可加载；未知工具加载诊断；广告不授予权限；Linux仅结构校验；Schema字段声明与运行URI分开 |
| T13 / test_T13_local_persistence_failure_fails_closed | effect提交后，node-terminal事务COMMIT前注入OSError | GuardedStore停止后续提交/调度；最后持久化tool仍running而非伪成功；恢复unknown、effect保持1，无重放 |
| T14 / test_T14_tool_errors_and_jsonrpc_errors | 工具isError与JSON-RPC -32602分别注入 | MCP_TOOL_ERROR与MCP_JSONRPC_ERROR分开记录，均为明确非写操作失败，无错误当正常输出 |

## 中断与失败后的持久化

T10三个运行子目录分别为before-call、during-call、after-call；含workflow/request/environment、run.sqlite、fault-injection.json、worker-result.json（exit74）、persisted-before-recovery.json和恢复后快照/事件。

| 点 | 最后提交 | 恢复 | 外部观测 |
| --- | --- | --- | --- |
| before-call | main/tool queued、phase ready，无attempt | 新建唯一attempt并调用 | tools/call总数1 |
| during-call | main/tool running、批准已消费、attempt已派发；外部effect已独立提交 | C1将未确认attempt标unknown，不重发 | effect1、tools/call1；拥有进程退出触发Job清理Server |
| after-call | main/tool succeeded且结构化输出已提交 | 用有效输出继续下游，不重开工具调用 | tools/call总数1 |

T13的OSError仅在隔离事务故障钩子中注入，没有破坏实际磁盘。失败事务回滚，存储被保护层阻止继续写入；storage-failure.json和worker-storage-failure.json是诊断而非第二个终态权威。恢复时以最后提交快照为准，不能用Server账本的成功记录覆盖run状态。

取消只证明请求已发送；本轮没有通用远端查询/核实接口。SDK的cancel错误响应不被当成物理停止证明，客户端保守unknown。合作/不合作handler观察与本地终态分开记录，关闭Job结束本次可信进程，不等于撤销已经提交的外部账本效果。

## 失败记录与修正

首轮[14方法、4失败](../experiments/p0-04/evidence/suite-20261024T052712492770Z/summary.json)，第二轮[14方法、1失败](../experiments/p0-04/evidence/suite-20261024T052859273636Z/summary.json)均保留原快照和traceback。具体修正：SDK任务组包装使具体诊断丢失，改为提取原ContractError；调用期限未扣初始化，改为总节点期限分配；不支持版本注入只改支持表、未改SDK回退版本，修正故障夹具；账本观察器遇文件已建表未提交的窗口，改为先检查sqlite_master。未靠减弱状态/副作用断言消除失败。

此前启动探针的resourceUri校验反例、pywin32匿名Job名称错误和相关失败目录见[开发失败记录](../experiments/p0-04/evidence/development-failures.json)。第三轮14方法通过后，又补充“握手期间批准过期”和“启动已耗尽期限时不得发调用”的边界并完整复测，固定最终通过套件为053902557486Z。旧成功与失败均未覆盖。

## 结论限度

本机已证明受控外部工具可以接入原C1，且写操作不在未批准、失败不明、超时不明或恢复不明时自动再次执行。没有完成任意MCP Server兼容、恶意插件隔离、HTTP/认证、Tasks/Agent、连接池、多请求并发、进程消息压力、断电或干净Windows机器分发验证。Job的实际回收证据只限本实验启动和记录的进程；不按名称查杀任何其他程序。
