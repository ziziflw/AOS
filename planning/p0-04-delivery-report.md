# P0-04 交付报告

2026-10-24。完成真实MCP stdio接入与Windows可信外部进程验证，停止于本轮。未开展正式GUI、真实模型/账户或下一阶段实现。

## 交付和结果

- [实验README及复现命令](../experiments/p0-04/README.md)：客户端适配器、独立SDK Server、场景B修订、故障注入、进程管理及证据格式。
- [运行验证报告](./p0-04-mcp-verification.md)、[协议兼容报告](./p0-04-protocol-compatibility.md)、[架构发现](./p0-04-architecture-findings.md)。
- [P0-04最终套件](../experiments/p0-04/evidence/suite-20261024T053902557486Z/summary.json)：14测试方法全部通过；含实际SDK调用、C1集成、故障Server和明确区分的静态诊断。
- [P0-03回归](../experiments/p0-03/evidence/suite-20261024T052920513341Z/summary.json)：原18方法全部通过；不混算为MCP通过数量。
- [依赖/许可清单](../experiments/p0-04/dependency-inventory.json)、[哈希锁](../experiments/p0-04/requirements.lock)、[制品环境核验](../experiments/p0-04/environment-evidence.json)、[离线解析报告](../experiments/p0-04/offline-resolution-report.json)。
- [保留失败记录](../experiments/p0-04/evidence/development-failures.json)、[交付审计](../experiments/p0-04/evidence/delivery-audit.json)。

报告固定链接本轮最终源码对应的通过套件，交付审计核对其摘要；其他成功和失败套件同样保留。14/18是各自测试方法数，不以工具数、断言数、进程数或历史117项静态检查凑通过数量。

## 十个问题的回答

1. **实际MCP stdio是否接入P0-03？** 是。官方ClientSession与独立官方SDK Server完成2025-11-25初始化/工具发现/调用；场景B原五节点角色由C1调度，ToolResult通过相同端口与输出契约进入下游。
2. **是否修改核心调度器？** P0-03 runtime.py保持原样；新增BoundRuntime环境实现、执行边界包装与GuardedStore停止保护，没有第二调度器。P0-03 common.py/contracts.py仅修正Schema声明被误认URI值的问题，原18项回归通过。
3. **协议/SDK兼容如何？** 实测组合为MCP 2025-11-25 + 官方Python SDK客户端/服务端1.30.0，Server实现0.1.0。当前主文档v2/2026-07-28与旧握手不同，本轮使用维护线和固定源码；未宣称SDK2.3.0不兼容。SDK取消错误响应的语义偏差已记录。
4. **Schema与端口如何映射？** 场景B保持ToolArgs→ToolResult，用等价展开Schema作MCP声明；先校验参数，发现签名锁定，再校验structuredContent，最后C1校验RuntimeValueEnvelope及工作流输出。其他工具以原契约注册新的领域JSON类型，不将所有内容转字符串。
5. **Windows进程是否可靠管理？** 本机所测正常/异常/取消/初始化失败/重复关闭/拥有进程退出和自有子进程均得到可解释清理；精确Job与记录PID检查未发现遗留。仅对自有可信Server成立，未证明任意插件、breakaway、所有Windows版本或OS沙箱。
6. **撤销、取消、响应丢失影响？** 取消/过期/旧内容使批准不能用于请求；取消通知仅表示已请求，物理停止未核实则unknown；写操作丢响应或恢复在途亦unknown，不自动重发。晚到结果不使下游继续。
7. **审批能否阻止外部执行？** 是。未批时连Server也未启动，拒绝/过期/取消/旧批准没有effect；重复批准只观察到一次真实tools/call/effect；握手期间过期也不调用。trusted effect覆盖错误readOnlyHint，不依赖模型承诺或Server注释。
8. **哪些执行契约应修改？** 保留P0-03输出激活/policy歧义；建议显式落地完整DispatchRequest、程序注册表、真实派发水位、取消观察/核实事实及持久化故障停止状态。本轮仅记录最小反例和建议，不大幅重写既有Schema。
9. **足够继续真实模型/独立Agent吗？** 足够开展下一轮受限探针，不足以宣称通用产品就绪。真实模型usage/预算/计费、Agent长期任务、远程认证和第三方隔离仍无证据；MCP适配不能等同Agent互操作。
10. **下一轮最有价值的实验？** 自有独立Agent任务服务的submit/query/cancel与断连后核实，使用合成任务，无账户、无收费模型；重点证明按taskId核实而非重复提交。仅为建议，未自动启动。

## 修改审计与历史保留

新增代码、夹具、依赖环境、wheel与实验数据库都在experiments/p0-04。planning新增四份P0-04报告。根/研究导航增量更新，新增官方资料记录S61–S63；P0-01/P0-02原报告、Schema、catalog、场景和117项静态结果保留。

P0-03仅两处校验源文件小改，原runtime.py、状态库、测试及旧证据不改写；执行回归新增独立证据目录，并正常更新latest指针。实施前baseline-manifest逐文件记录既有项目文件，交付审计确认允许列表以外的历史文件未改变。

依赖只安装在p0-04/.venv，30个运行依赖全部确切版本与SHA256锁定，官方MCP MIT许可及各依赖元数据/通知保留；没有大型平台、任意第三方MCP插件或大模型下载。离线仅实测本机wheel解析，不能说干净机器安装/跨OS分发通过。

PFT未修改；没有用户个人文件读写操作、真实账户、付费API、管理员提权、Git提交/标签/推送或稳定版发布。合成Server所有业务写入均限制在自己的p0-04/evidence测试目录；普通Windows子进程不被称作强隔离沙箱。
