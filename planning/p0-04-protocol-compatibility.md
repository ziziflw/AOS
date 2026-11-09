# P0-04 协议与 SDK 兼容记录

核验2026-10-24；实际版本见[environment-evidence](../experiments/p0-04/environment-evidence.json)，逐方向协议见[通过套件](../experiments/p0-04/evidence/suite-20261024T053902557486Z/)。

## 版本组合和选择依据

| 层 | 固定值 | 证据与范围 |
| --- | --- | --- |
| MCP规范 | 2025-11-25 | 固定版本生命周期、stdio、tools、cancellation；本次initialize请求和响应相同 |
| 客户端SDK | 官方mcp 1.30.0 | wheel哈希、包元数据、ClientSession实际执行 |
| 服务端SDK | 官方mcp 1.30.0 | 同一锁定环境的独立进程，Server与stdio_server实际执行 |
| Server实现 | aos-p0-04-synthetic / 0.1.0 | initialize响应，启动源文件摘要及固定六工具描述 |
| 节点/适配器 | NodeDefinition/AdapterDefinition 0.1.0 | 原格式0.1.0-draft.1，catalogLock+具体capability/selector |
| 传输 | UTF-8、换行JSON-RPC 2.0、stdio | protocol.jsonl、严格解析、污染故障测试 |

P0-02固定规范候选2025-11-25继续沿用。P0-02 Python 2.3.0是研究候选，本轮未安装/测试该版，不以未使用推断其不兼容。官方主文档已是v2，当前规范页面存在2026-07-28无旧式初始化模型；本轮选择v1维护线以收窄新协议/SDK迁移变量，核查的是[对应v1文档](https://py.sdk.modelcontextprotocol.io/v1/)与[固定v1.30.0源码](https://github.com/modelcontextprotocol/python-sdk/tree/v1.30.0)。没有引用v2的API步骤来实现旧会话。

依据：[SDK发布/许可与依赖](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v1.30.0)、[生命周期](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)、[stdio](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)、[工具](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)、[取消](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation)。这些资料仅支持相应协议/SDK事实，实际兼容结论来自本轮保存的调用。

## 实际消息序列

1. 按EnvironmentBinding解析受信程序，创建Windows Job，启动Server并分配Job，再放行启动门闩。
2. 官方ClientSession发initialize，版本2025-11-25；核对响应版本、Server名称0.1.0、tools能力。
3. SDK发送notifications/initialized，随后tools/list。发现6工具，保存名称、说明、inputSchema、outputSchema、注释和_meta版本。
4. 可信白名单及本地描述签名匹配后，校验当前实际参数，C1消费批准；启动耗时后再查批准期限/取消，tools/call发送name/arguments与_meta中的run/node/attempt/operation身份。
5. 保存原始content/structuredContent或JSON-RPC error；SDK验证structuredContent，适配器再按发现outputSchema验证，C1再按端口类型及workflow outputSchema验证。
6. 关stdin、等待退出；超时则仅终止本次Job；重复关闭安全。没有MCP“shutdown RPC”自定义消息，也未取消initialize请求。

Server stdout正常情况下只有SDK协议消息；普通日志stderr。污染模式是明确命名的故障注入，客户端必须终止会话，不接受后续“恢复正常”的结果。本传输保留官方ClientSession/Server，只替换客户端stdio进程托管和严格分帧；不是自行实现另一套MCP握手或业务调度。

## Schema与节点映射

原场景B的ToolArgs{query,source:FileReference}对应structured_result.inputSchema，ToolResult{items,operationState}对应outputSchema。发现Schema在本轮描述锁中完整记录并以稳定摘要比对，版本_meta为aos:tool-version=0.1.0。原本地$defs引用在MCP描述中展开为等价内联Schema；没有更改原JSON类型、将JSON转成Text或把Tool错误塞进普通结果。

其他五种工具是原契约下新增的实验NodeDefinition与领域JSON类型：p04.input.*→tool.mcp.*→synth.output-*，均有原格式的节点版本、端口、policy、adapter、catalogLock。原scenario-b文件保持原样，新实验修订为scenario-b-p04-r1。客户端不自动采用工具列表变更、Schema漂移或未知工具；本轮没有工具列表热更新，变化需重新绑定/修订。

远端readOnlyHint/destructiveHint不是权限证据。simulated_effect故意声明readOnlyHint=true，但可信注册元数据effect=write，C1仍强制批准。发现只提供能力，不授予调用权限。Server可主动执行内部代码，普通子进程无法限制其所有文件/网络动作，所以只运行本项目自有Server。

## 错误、重试与取消的源码审查

审查固定版本[ClientSession.call_tool](https://github.com/modelcontextprotocol/python-sdk/blob/v1.30.0/src/mcp/client/session.py)和[BaseSession.send_request](https://github.com/modelcontextprotocol/python-sdk/blob/v1.30.0/src/mcp/shared/session.py)：每次请求建立requestId并等待一次响应，无自动重试循环。本适配器不使用HTTP传输，不启用SDK任务扩展，不增加重试。T11实测C1两个attempt对应两个tools/call，而写操作丢响应只有一个。

工具isError映射MCP_TOOL_ERROR，JSON-RPC error映射MCP_JSONRPC_ERROR。若请求已发且可信分类为write/unknown，断线/超时/工具错误均保守为unknown，禁止自动再次执行；只读/纯工具的明确失败可为failed，只有已锁定SAFE_TRANSIENT与safe policy可重试。

**发现SDK与规范的取消差异**：固定规范建议接收取消后不再响应原请求，但此SDK的RequestResponder.cancel会取消作用域并发送code=0、“Request cancelled”错误响应。shield handler可能仍然继续运行，不能由这个错误推断操作已停止。客户端不依赖该响应宣布cancelled；发送通知只记录cancel-requested，缺少业务核实为unknown。未把SDK实现细节当作通用MCP取消确认协议；合作handler另有测试账本观测。这项偏差应在正式选SDK前继续评审或更换实现。

## 环境、依赖与未支持范围

Server启动程序/参数属于EnvironmentBinding的programRef及aos:programs扩展，图不携带绝对路径。启动白名单验证确切解释器和Server脚本，使用参数数组、无shell、精简环境。该扩展补足草案只定义programRef但无程序注册表实现的空白；未改变历史Schema。

实际安装30个SDK运行依赖，版本/制品URL/许可证及SHA见[依赖清单](../experiments/p0-04/dependency-inventory.json)、[锁文件](../experiments/p0-04/requirements.lock)、[安装报告](../experiments/p0-04/installation-report.json)。mcp为MIT，保留版权/许可；其余依赖各遵守自己的许可证，packaged notices保存于licenses/，正式分发仍需单独审查。Windows特定wheel与已有Python/pwsh不构成跨OS离线包。

L1保留定义与诊断：缺程序仍可读取/保存原始JSON，未实现GUI编辑器。L2在当前Windows下通过，Linux替换绑定只通过Schema检查；L3仍不迁移凭据/插件/整个环境。远程HTTP、OAuth、MCP resources/prompts/sampling/elicitation/tasks、Agent和任意第三方Server均未验证。每连接单在途调用，新attempt新连接，不能宣称连接池/多路复用或完整MCP符合性通过。
