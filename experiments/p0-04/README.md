# P0-04 真实 MCP stdio 与 Windows 外部进程验证

本实验使用**官方 MCP Python SDK 客户端与服务端、独立 Windows Server 进程和真实 stdio 消息**。工具仅处理合成数据或写入各测试自己的账本。C1仍使用P0-03调度器与SQLite快照，没有第二套工作流调度器，不是正式应用或OS安全沙箱。

入口：[运行验证](../../planning/p0-04-mcp-verification.md)、[协议兼容](../../planning/p0-04-protocol-compatibility.md)、[架构发现](../../planning/p0-04-architecture-findings.md)、[交付报告](../../planning/p0-04-delivery-report.md)。

## 固定版本与官方依据

核查日期2026-10-24。MCP协议固定 **2025-11-25**，客户端/服务端SDK均 **mcp==1.30.0**，Server实现版本0.1.0。SDK版本和协议版本不是同一编号。

- [固定stdio规范](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)：UTF-8、每行一条JSON-RPC、stdout只含协议，日志走stderr。
- [固定生命周期](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)：initialize→notifications/initialized→tools/list→tools/call。
- [固定工具规范](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)及[取消规范](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation)。
- [SDK v1.30.0发布](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v1.30.0)、[固定源码与依赖](https://github.com/modelcontextprotocol/python-sdk/blob/v1.30.0/pyproject.toml)、[v1维护线文档](https://py.sdk.modelcontextprotocol.io/v1/)、[MIT许可](https://github.com/modelcontextprotocol/python-sdk/blob/v1.30.0/LICENSE)。

当前官方规范已有[2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28)，官方SDK主文档为v2；本轮不混用其无旧式初始化的请求模型。P0-02候选Python 2.3.0没有被宣称不兼容；本轮为缩小验证范围选择仍受维护的v1.30.0及对应源码，**未对2.3.0做兼容测试，也不主张1.30.0是全局最新版**。实际initialize.json与protocol.jsonl证明本次协商2025-11-25。

## 运行与复现

已有Python 3.12.14、PowerShell 7.6.5继续使用；新增SDK等30个直接/传递运行依赖仅装入本目录.venv。原项目和P0-03不依赖这套新SDK环境。

```powershell
Set-Location -LiteralPath 'D:\AIOrchestrationStudio'
$p04Python = 'D:\AIOrchestrationStudio\experiments\p0-04\.venv\Scripts\python.exe'
& $p04Python -B -X utf8 experiments/p0-04/test_mcp.py
& $p04Python -B -X utf8 experiments/p0-04/run_demo.py
& $p04Python -B -X utf8 experiments/p0-04/run_demo.py --tool simulated_effect
& $p04Python -B -X utf8 experiments/p0-04/run_demo.py --tool simulated_effect --approve-simulated
& 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 experiments/p0-03/test_runtime.py
& $p04Python -B -X utf8 experiments/p0-04/collect_environment.py
& $p04Python -B -X utf8 experiments/p0-04/audit_delivery.py
```

默认演示为原场景B的新实验修订。未批准的simulated_effect停在waiting-approval，不启动Server；`--approve-simulated`是显式测试操作者批准，只影响合成账本。每次测试/演示使用独立UTC目录，旧失败不覆盖。CLI不支持任意Server命令或第三方插件。

重建.venv时使用同一CPython 3.12 Windows x64解释器创建该路径，随后执行锁定安装：

```powershell
# .venv不存在时才执行创建；不要覆盖正在使用的环境。
& 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m venv experiments/p0-04/.venv
& experiments/p0-04/.venv/Scripts/python.exe -m pip install --no-index --find-links experiments/p0-04/wheelhouse --require-hashes -r experiments/p0-04/requirements.lock
& experiments/p0-04/.venv/Scripts/python.exe -m pip check
```

安装理由是需要真正SDK双方协议实现；未安装CLI extras、模型或工作流平台。初始解析只固定顶层SDK，随后在执行SDK前把实际解析的全部30个制品版本/哈希锁定，后续只使用锁文件。`installation-report.json`保存PyPI制品URL和SHA256；`requirements.lock`没有latest或范围依赖；`dependency-inventory.json`逐包记录版本、项目URL、许可证元数据及原因。`licenses/`保留已安装制品携带的许可证/NOTICE，分发仍须保留相应版权和许可证，不构成正式法律审查。

30个wheel的SHA256与安装报告一致；已实际完成`--no-index --ignore-installed --dry-run --require-hashes`离线解析，见offline-resolution-report.json。**没有宣称在干净机器完整离线安装已验收**：仍须准备Python、pwsh、Windows运行环境和原P0-02/P0-03目录；wheel包含CPython 3.12/Windows x64专用制品，不能用于Linux/macOS。具体环境见environment-evidence.json。

## 代码边界

| 文件 | 职责 |
| --- | --- |
| synthetic_server.py | 仅独立运行的官方SDK Server；六个工具及受控故障模式 |
| mcp_client.py | 官方ClientSession、严格分帧、握手/发现、描述锁、一次调用、超时/取消/错误 |
| process_host.py | 白名单命令参数数组、精简环境、无shell、启动门闩、Windows Job及关闭 |
| integration.py | D2注册/派发检查、EnvironmentBinding实现、存储失败停止保护；复用原C1 |
| cases.py / fixtures/ | 原契约catalog扩展、场景B修订及六种合成图/请求/绑定 |
| tool_specs.py | 声明式Schema和工具版本，仅共享描述，不把Server函数导入执行器 |
| test_mcp.py / crash_worker.py | 实际SDK/工作流/故障/静态各类证据，拥有进程的真实退出注入 |
| lock_environment.py / collect_environment.py / audit_delivery.py | 依赖锁、许可证/制品记录、交付审计，均不计为MCP执行测试 |

工具包括echo_text、add_numbers（有界有限数）、delayed_result、structured_result（原ToolArgs→ToolResult）、simulated_failure、simulated_effect。后者故意声明readOnlyHint=true，可信注册表仍认定write并强制审批，证明注释不是权限证据。

## 节点与权限

原场景B保留request→map→tool.query→check→output的节点/端口类型；新修订只绑定本轮适配器catalog。其余夹具用原NodeDefinition/AdapterDefinition/JSON类型扩展，不引入新工作流方言。参数先经节点输入/参数Schema，再经真实发现的工具inputSchema；结果必须为structuredContent，经SDK/outputSchema和原端口/工作流输出Schema验证。content原样留证，不拿字符串冒充类型化输出。

程序路径/参数只放在EnvironmentBinding的programRef及命名空间extensions['aos:programs']，工作流无Windows绝对路径。原Schema只有programRef，没有程序注册表实现，因此本轮利用既有extensions保存本机白名单启动配置，不修改历史Schema。更换平台绑定在结构上可表达，实际执行只接受已验证Windows；无Server时仍可读取和保存原始定义，尚无GUI编辑器。

MCPRegistry调用必须绑定正在运行的C1 run、节点版本、attempt、operationId和具体工具白名单。write门禁依赖C1消费的批准指纹；Server握手后再次检查取消、内容和批准期限，过期批准不能发送调用。原始传输类只用于可信内部/测试，不是可供插件绕过C1的公共授权入口。

## 错误、取消与恢复

初始化/参数/Schema漂移、工具isError、JSON-RPC error、stdout损坏、Server退出、请求超时、用户取消、外部结果未知、存储失败分别留证。SDK源码的send_request/call_tool没有自动重试循环；本适配器也不重试。仅C1在可信none/read、safe策略及明确SAFE_TRANSIENT的情况下增加attempt；write/unknown始终maxAttempts=1，结果丢失不重发。

取消发送notifications/cancelled。该版本SDK可能返回“Request cancelled”错误，但本轮不把它当作物理停止确认：shield的handler仍可能运行。客户端只记录已请求，未确认的取消为unknown；测试单独观察Server账本中合作handler已取消，不能将账本写回C1终态。关闭先关stdin并等待，必要时只终止本次Job，晚到结果不用于下游。

本地存储失败后GuardedStore停止后续提交/派发，保留最后成功提交的running快照；停止诊断不是伪造的持久终态。恢复仍由C1将未确认attempt标unknown；外部账本不会自行宣布run成功。

进程Job启用KILL_ON_JOB_CLOSE，Server在分配Job后才被启动门闩放行；覆盖Windows venv launcher、实际Python Server与自有idle子进程。检查仅针对本实验记录的PID/Job，不按名称清理。它是可信进程生命周期管理，未限制同用户文件/网络访问，不是强沙箱；breakaway、恶意Server与干净机器分发未验证。

## 证据与限制

[最新套件指针](./evidence/latest.json)、[P0-03回归](./evidence/p0-03-regression.json)、[开发失败记录](./evidence/development-failures.json)、[交付审计](./evidence/delivery-audit.json)。每个测试有assertions.json和process-cleanup.json，每个run保存输入/绑定、C1快照/事件；mcp-*有initialize、工具发现、逐方向真实协议、原始结果、stderr、进程日志及独立server-ledger.sqlite。T10保存工作者退出码、注入位置和恢复前快照。具体固定套件链接及测试数量见运行报告。

每个连接只允许一个在途调用，每次C1 attempt新建/关闭Server；没有连接池、并发请求复用、大消息/背压压力、远程HTTP、认证、资源/采样/任务扩展或Agent互操作。Job只在当前Windows主机实测；L1/L2/L3边界不变。当前原型可作为协议一致性探针，未定案正式执行引擎。
