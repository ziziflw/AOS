# P0-05 架构发现与实施前最小决策

日期2026-10-24。此节在接入前记录冲突与受限修正；不改写P0-02 Schema或历史研究，不冻结正式架构。

## R01：已知远端taskId的恢复不能被等同盲目重跑

最小反例：C1持久化node.running，Agent已接受并返回taskId，随后执行引擎进程退出而Agent继续运行。P0-03 Runtime构造器目前无条件把所有running attempt改unknown；旧Context也没有远端引用/恢复方式。单纯把节点改queued会新建attempt并重新submit，产生第二任务；直接import Agent函数则完全绕过任务身份。

受限方案：只把原默认恢复分支抽取为可覆盖的C1方法，默认行为保持unknown；P0-05的C1子类仅在已持久化Agent身份/固定定义一致、未取消时保留同一attempt并计划query-only恢复，禁止SendMessage。远端引用与观察通过C1事务写入其唯一快照，Adapter只提供事实。没有可靠taskId但提交已发时仍unknown；可选的按关联ID核实必须有本实验服务的明确语义和独立测试，不当作A2A普遍保证。

影响：原runtime.py一个受限方法提取；调度、审批、预算、依赖和输出继续由原C1控制。新增的Agent恢复与状态解释放在p0-05子类，不新增工作流调度器。原P0-03与P0-04必须完整回归。禁止通过修改旧快照、伪造queued或重新submit来冒充恢复。

## R02：远端取消事实和本地状态决策

Agent拥有任务状态，C1拥有工作流状态。Agent适配器记录匹配taskId/operation/attempt的取消响应及查询事实；只有C1子类在已记录CANCELED证据时才能得出本地cancelled。已发送取消、取消不支持、失联或取消后仍完成均不能伪称已停止，旧结果不进入下游。

以上为接入前记录，现追加实际结果；[18项专项及18/14项回归](./p0-05-agent-verification.md)均通过。原P0-02/P0-03/P0-04历史报告和反例没有改写。

## R03：最小改动已落地，仍不是完整DispatchRequest

原runtime.py仅把原有恢复分支抽成`_recover_inflight`；默认仍INTERRUPTED_IN_FLIGHT→unknown，P0-03/P0-04回归通过。P0-05 AgentRuntime在身份匹配、有taskId或明确关联核实权限、未取消且原attempt仍running时计划查询恢复；drive恢复原attempt而非重新_begin。调度、依赖、并发槽、预算、审批、输出封套和本地终态仍由C1拥有。

D3通过C1的intent/observation方法提交事实：提交前submit-intent，响应后可靠保存taskId、messageId/contextId、run/node/attempt/operation、Agent端点/能力摘要、状态序号/进度和期限。恢复后只Get/List，不Send；期限固定，不因重启续期。无可靠关联时仍unknown，不通过“改queued”触发第二任务。

实际Context依然不等于P0-02概念中的完整DispatchRequest。适配器仍读取可信Runtime.snapshot并使用_fingerprint，存在与C1内部接口的实验耦合。建议后续形成不可变派发/查询/取消上下文和受限外部引用接口，明确授权作用于submit、query、cancel、publish的不同范围；本轮未直接重构正式契约或模块边界。

## R04：两种权威分开，不是两个工作流调度器

| 所有者 | 权威数据 | 不能做的事 |
| --- | --- | --- |
| C1 | run.sqlite快照/事件、NodeAttempt、批准、依赖、有效输出、本地终态 | 不能把网络超时解释为Agent没有收到任务，不能伪造远端已停止 |
| 独立Agent | agent.sqlite任务表、内部worker、进度、结果、合成产物与效果 | 不能覆盖本地run/节点状态，不能以Task.COMPLETED强迫C1发布失效结果 |
| D3 | 协议协调及身份/能力/产物验证，提供观察事实 | 不能建立第二套工作流调度、自动重发未知提交或根据日志直接改终态 |
| 实验监督器 | 自己启动的Agent Job/进程生命周期 | 不能以执行器退出为由删远端任务、查杀同名无关进程或声称强沙箱 |

服务接受任务和最终结果/效果各自原子提交；中间进度与其事件分开提交，服务任务表是权威，断电可能使进度事件不完整，未作为生产完整审计日志验收。C1观察与事件仍同一事务。本轮没有外部工作流框架checkpoint，也没有引入跨设备分布式调度。

## R05：同一次逻辑提交的身份与核实

messageId由稳定operationId导出；taskId由Agent生成并持久化。节点attempt、操作、迭代和远端任务仍分开；普通Agent节点禁止自动attempt重试，避免把新attempt变成独立远端任务。协议请求ID只关联一次JSON-RPC，不能替代operationId或taskId。

SendMessage响应丢失的反例实际成立：Server任务1，Client taskId=None，本地unknown；受控effect任务可在此后独立写账本1次。没有把HTTP失败当成未执行。自有服务的messageId唯一约束和请求摘要可抑制相同提交，标准只说MAY，不能泛化为所有Agent幂等。

本轮可选ListTasks核实使用标准contextId筛选及本profile精确身份匹配；只接受唯一完整匹配，不靠再次SendMessage查询。不存在匹配、分页不完整或身份不符时不重发。本轮没有多租户、任意任务大列表或跨服务一致性实验，正式实现须锁定对方可核实性，而不是只检查一个“supportsIdempotency”布尔值。

## R06：取消确认、等待和失效结果

匹配CANCELED事实由C1核查后映射cancelled。取消请求、收到请求和远端最终状态各有证据；不支持取消、失联或竞态完成均unknown，不把按钮当已停止。远端已完成但产物暂不可得保持waiting-agent-artifact，耗尽等待后unknown；INPUT_REQUIRED/AUTH_REQUIRED是等待phase，未实现自动续谈，不伪造用户答复。

身份、UUID、Agent来源、sequence及终态回退都检查；旧序号不覆盖新状态，终态后的重复结果只留审计不再次执行下游。定义/请求变更的恢复拒绝，新run有新身份；授权过期后即使远端COMPLETED也不发布。审批仅管本平台提交/发布，不能追溯撤销远端内部工具行为，这一点由已接受任务在过期后effect1的测试明确暴露。

## R07：产物引用、连接声明与安全界限

Artifact的data/url part是标准载体，具体AgentTaskResult/FileReference为实验领域类型。仅访问固定Agent来源、匹配UUID taskId推导的同源URL；校验Schema、operation/task/agent、媒体类型、大小、SHA及JSON内容后登记本地合成产物，不解释任意返回路径为文件权限。

旧EnvironmentBinding没有明文http连接枚举。本轮programRef/cli仅表示本机Agent程序安装，真实loopback A2A端点放入命名扩展，未谎称使用https。建议正式契约增加明确的受限服务接口注册/传输配置和可信制品闭包；工作流仍只含逻辑slot，不含本机路径/密钥/PID/句柄。缺服务保留原始节点，阻断执行而不删除。

服务仅监听127.0.0.1，使用合成Bearer标记、retries=0及脱敏记录；它不是TLS/OAuth、用户身份或抗同用户恶意进程的安全机制。Agent不可信时，本地审批不能代替远端沙箱。本轮只用自己创建的可信服务，不支持任意插件或任意命令。Windows Job核查launcher和真实Server归属，执行器崩溃时服务由独立监督器维持，测试结束清理；监督器自身崩溃/启动窗口、恶意breakaway及其他Windows版本未验证。

## R08：实现成本与下一阶段判断

保留Python标准库/asyncio/SQLite与原Schema校验桥；新增官方A2A SDK及42个锁定运行依赖，未修改MCP环境。Agent内部工作是确定性合成，不是大模型调用。SDK/JSON-RPC接入可控，但protobuf/ProtoJSON、任务身份、恢复、来源/授权核查明显比同步工具调用增加边界；这不是“只再加一个invoke函数”即可解决的功能。

有证据继续做受限真实模型或桌面集成探针，尚不足以定案生产执行引擎。建议下一轮优先验证**无正式GUI的Tauri/Rust宿主到现有执行器的最小IPC与关闭协调**，覆盖版本、身份、取消、引擎重启、独立Agent继续运行及事件背压。它可继续无收费/无账户，并检验目前只有Python实验监督器的宿主边界。真实模型usage/价格/超时计费需另立授权和预算，不能由本轮A2A成功推导。

未实现原场景C的全部真实Agent规划/执行/有界修复链；本轮是原契约扩展下的单任务和双Agent并行任务，原复杂控制语义仅通过P0-03模拟回归。required输出激活、policy作用域、完整派发上下文、持久化故障保护、时钟回拨、长期任务/产物保留和生产压力仍待解决。没有冻结语言/SDK/框架，也未自动进入下一阶段。
