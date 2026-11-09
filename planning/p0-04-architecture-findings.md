# P0-04 架构发现

2026-10-24。结论来自[运行证据](./p0-04-mcp-verification.md)与[协议兼容记录](./p0-04-protocol-compatibility.md)。本文件提出后续修订建议，不宣布生产架构定案。

## A01：核心调度可以复用，环境硬编码需要隔离

P0-03 runtime.py未修改；原串并行、分支、汇合、循环、attempt、审批、结果封套与状态持久化仍由C1决定。P0-04没有另写MCP调度器。新增BoundRuntime只替换环境校验，并包裹执行/drive边界以识别存储失效；MCPRegistry实现D2调用，GuardedStore实现停止继续写入的保护。它们仍继承原调度路径，不能把“源文件没改”说成“没有新增运行边界实现”。

原环境校验只接受builtin:mock，本身不能启动真实stdio。新环境层以原EnvironmentBinding的stdio/programRef和命名空间aos:programs解释本机程序。原Schema没有args/executable的受信程序注册表，本轮通过既有extensions限定在一个自有Server和固定解释器，不需要重构工作流格式。正式版建议把“程序安装记录/参数数组/制品摘要/运行权限”形成版本化E3注册对象，而非持续增长任意extensions。

## A02：复现的最小阻碍是校验器缺陷，不是契约必须重写

最小输入：在一个合法参数Schema中声明`properties.resourceUri={type:string,...}`。P0-03通用引用扫描器把这个字典当作运行时URI，报RESOURCE_URI；原catalog通过局部$ref间接引用而未暴露这个窗口，MCP内联展开Schema后立即失败。

仅修改P0-03 common.py的schema上下文遍历和contracts.py调用sub-schema扫描时的上下文标识。运行值中的路径穿越依旧拒绝，原Schema/catalog/scenario未改变；T12增加精确反例与运行值拒绝对照，原18项回归全过。后续应把Schema解析与业务值解析的责任彻底分开，并加入复杂度、大小和远程引用限制；当前通用字段扫描仍只是受限实验防线。

P0-03留下的required输出激活、root/node重试作用域、all/exclusive与onFailure=stop的解释全部保留，未因MCP接入冻结。真实工具结果通过相同validated输出才解锁下游，MCP的普通content、isError或协议错误不获得下游有效值身份。

## A03：DispatchRequest设计尚未完整落成接口

P0-02描述了包含run、attempt、operation、能力、授权、deadline的DispatchRequest；P0-03实际Context只有节点/输入/attempt/operation/取消令牌等。为保持本轮小改，D2从绑定的C1读取已提交快照，验证当前running attempt与批准消费状态，再构造MCP _meta身份；没有声称已有完整通用DispatchRequest类。

反例：仅拿Context调用一个真正外部工具，无法独立得知runId及批准是否对应当前操作。当前适配器因此依赖Runtime.snapshot和_fingerprint，属于实验耦合。建议下一轮形成明确、不可变、由C1构造的派发上下文：run/revision、scope/iteration、attempt与operation、能力/工具签名、具体动作与参数摘要、有效授权引用、deadline、取消状态；D2必须复核后使用。结果应包含requestSent/remoteResult/sideEffect/cancelObservation等事实，仍由C1决定状态。建议不等于本轮已改变全部契约。

## A04：授权必须在真实请求边界再次检查

C1消耗批准后，还要启动进程、初始化和发现。若这段时间批准过期，不能继续发工具请求。最终实现握手后再次检查run取消、批准状态、指纹与期限；慢初始化测试实际证明APPROVAL_EXPIRED_BEFORE_MCP且tools/call=0、effect=0。未批则连Server都不启动。

MCPServer工具广告不授予权限；simulated_effect故意自报readOnlyHint=true，注册表仍为write。D2检查node/adapter版本、具体工具白名单和C1 running attempt；write仅接受C1已经消费的绑定批准。客户端传输类是可信内部设施，不是任意插件可调用的授权API。没有用户身份系统或抗同用户恶意修改Python/SQLite的安全声明。

## A05：取消、响应丢失和 SDK 错误响应不能混同

MCP取消是通知，不能保证物理停止。SDK v1.30.0在取消后可能发“Request cancelled”code0；shield handler仍可不合作。此偏差与固定规范建议不再响应原请求的差异已记录，不能把它当成通用确认。D2记录通知已发，缺少业务核实结果为unknown；随后只回收本次Job，不宣称撤销外部副作用。

写操作先提交合成账本再丢响应时，C1 attempt及run为unknown、调用和effect均1；恢复不重发。只有明确的none/read、safe策略、可信SAFE_TRANSIENT才由C1发起第二attempt；稳定operationId和不同attemptId在真实_meta可见。Server不提供幂等查询/核实API，本轮不能把稳定operationId本身当成exactly-once。

建议后续单独设计“查询/核实已有operation”的受权节点及人工核实记录，而不是将unknown改failed后让通用重试器再次执行。取消前尚未真正发请求与请求后未确认在当前Context中仍难完全区分，原型优先保守unknown；正式接口需明确派发水位。

## A06：存储失败需要停止继续派发

外部工具已经响应成功，但本地完成事务失败，不能当作普通安全失败并重试。P0-04 GuardedStore遇OSError/sqlite错误后拒绝后续提交，BoundRuntime边界停止并关闭本次连接；最后持久化状态仍running，诊断另存但不宣称已持久成功/失败。重启由C1解释unknown，effect仍1。

这个保护没有增加第二个状态权威，也没有让Server账本回写run。尚未覆盖磁盘真正损坏、持续满盘、事务提交返回不确定、WAL损坏或恢复迁移。正式引擎要把存储健康/停止派发提升为C1明确状态与接口，不能长期依赖边界异常触发停止。

## A07：Windows Job 能解决本次生命周期问题，不能替代沙箱

启动使用固定exe与参数数组、精简环境、无shell；Job启用KILL_ON_JOB_CLOSE。自有Server等待启动门闩，只有关联Job成功后才进行业务及创建idle子进程。关闭先关stdin等待，再按本次Job终止；拥有进程os._exit时Job句柄释放，关联Server被回收。测试同时跟踪venv launcher PID、实际Python Server PID及自有子进程，避免只检查launcher而漏掉实际进程。

首次Anonymous Job调用参数和账本创建竞态等失败已保存并修复。清理只针对本实验持有的句柄/已记录PID，不按同名程序扫描杀进程。Job未施加文件/网络权限隔离，Server与用户同权限；启动前分配Job的保障依赖可信Server等待门闩，不适用于恶意程序。breakaway、不同宿主Job限制、干净机器安装与Windows其他版本仍未验证。

## 下一步与继续开发依据

有足够证据继续做小范围真实适配探针，尚不足以开始通用插件平台、正式GUI或完整Agent产品。当前每attempt启动一个Server、单在途连接、无连接池/背压压力；新环境扩展、授权主体、取消核实、存储停止语义及完整DispatchRequest都应先评审。

下一轮最有价值的是**自有、无账户、无收费模型的独立Agent任务服务**：submit返回稳定taskId、query核实已提交任务、cancel返回可核实状态、断连后query而非重新submit，并覆盖最终结果落盘前后中断。可复用本轮Job、Schema、授权和unknown夹具，专门补足真实MCP调用未证明的长期任务/核实语义。若届时采用A2A，先重新核查并锁定规范/SDK；本轮没有安装或调用Agent SDK，没有自动进入下一阶段。真实付费模型的usage、价格和取消计费仍需单独授权与预算，不能由本轮工具验证推导。
