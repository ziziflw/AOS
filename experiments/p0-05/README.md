# P0-05 独立 Agent 任务与协同验证

2026-10-24，Windows 11 x64。使用**实际 A2A JSON-RPC 与官方 Python SDK**连接独立进程中的自有合成 Agent。不是MCP工具别名，不调用模型，不连接真实账户。专项18个方法通过；P0-03原18项、P0-04原14项回归分别通过。

入口：[任务验证](../../planning/p0-05-agent-verification.md)、[协议兼容](../../planning/p0-05-protocol-compatibility.md)、[架构发现](../../planning/p0-05-architecture-findings.md)、[交付报告](../../planning/p0-05-delivery-report.md)。

## 协议与版本

- 规范参照：[A2A v1.0.1](https://a2a-protocol.org/v1.0.1/specification/)，实际线版本/header为 **1.0**，不是SDK版本或规范patch号。P0-02已记录的规范站页Latest Released标题1.0.0与URL/tag1.0.1差异继续保留。
- 客户端/服务端：[官方 a2a-sdk==1.2.3](https://github.com/a2aproject/a2a-python/releases/tag/v1.2.3)，[固定README兼容表](https://github.com/a2aproject/a2a-python/blob/v1.2.3/README.md)声明1.0各绑定；本轮只实测JSON-RPC。
- 实际使用官方Agent Card路由、JSON-RPC dispatcher、protobuf类型、A2ACardResolver与JsonRpcTransport；本项目实现独立RequestHandler与SQLite任务/worker。旧0.3兼容关闭，无自动降级。
- RPC为`SendMessage`（returnImmediately=true）、`GetTask`、`ListTasks`、`CancelTask`；发现路径为`/.well-known/agent-card.json`，每次请求带A2A-Version:1.0。没有自定义HTTP任务协议替代这些操作。
- 服务实现0.1.0，echo/effect两个skill；状态为SUBMITTED、WORKING、INPUT_REQUIRED、AUTH_REQUIRED、COMPLETED、FAILED、CANCELED、REJECTED。进度、Schema、序号和关联核实保证属于本实验Agent Card扩展，**不是所有A2A Agent必然具备的能力**。

## 运行

```powershell
Set-Location -LiteralPath 'D:\AIOrchestrationStudio'
$p05Python = 'D:\AIOrchestrationStudio\experiments\p0-05\.venv\Scripts\python.exe'
& $p05Python -B -X utf8 experiments/p0-05/test_agent.py
& $p05Python -B -X utf8 experiments/p0-05/run_demo.py
& $p05Python -B -X utf8 experiments/p0-05/run_demo.py --parallel
& $p05Python -B -X utf8 experiments/p0-05/run_demo.py --effect
& $p05Python -B -X utf8 experiments/p0-05/run_demo.py --effect --approve-simulated
& 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 experiments/p0-03/test_runtime.py
& experiments/p0-04/.venv/Scripts/python.exe -B -X utf8 experiments/p0-04/test_mcp.py
& $p05Python -B -X utf8 experiments/p0-05/collect_environment.py
& $p05Python -B -X utf8 experiments/p0-05/audit_delivery.py
```

默认演示为input→Agent任务→output；parallel为两套独立服务和任务后汇合。effect未批准时停在waiting-approval；服务可以已经启动，但**受门禁的SendMessage不会发送**。approve-simulated是显式合成测试操作者，不是Agent或模型自行批准。

每次运行生成独立UTC证据目录。测试/演示监督器拥有Agent服务的Job句柄，执行器进程不拥有它们；因此T08执行器真实退出后Agent仍运行。测试结束监督器只清理自己启动的Job/PID，包含Windows venv launcher与实际Server；没有按程序名杀进程。

## 依赖与离线限制

已有Python3.12.14/pwsh7.6.5继续使用；新增依赖仅在本目录.venv。官方SDK的http-server extra、固定uvicorn0.54.0/pywin32 312/jsonschema4.26.0及其依赖共42个安装制品，见[逐包版本/来源/许可](./dependency-inventory.json)、[安装报告](./installation-report.json)、[SHA256锁](./requirements.lock)、[环境及SDK源码摘要](./environment-evidence.json)。能复用的依赖版本采用P0-04约束；解析后在SDK执行前冻结全部制品，不使用不受控latest。未修改P0-04环境。

SDK为Apache-2.0，保留许可及适用NOTICE；各传递依赖遵守各自许可。`licenses/`复制制品携带的版权/许可/NOTICE，不表示正式分发合规已经审查。未安装grpc/sql/Agent框架/模型extras；google-auth等是SDK依赖，没有初始化真实账户或调用云服务。

wheelhouse保留42个制品，SHA与安装报告一致。本机已执行无网络索引、忽略现有安装的哈希锁定**离线解析dry-run**，见offline-resolution-report.json，未声称干净机器完整离线安装通过。重建时先用相同CPython3.12 Windows x64创建本目录.venv，然后：

```powershell
# 仅在.venv不存在时创建，保留已有环境。
& 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m venv experiments/p0-05/.venv
& experiments/p0-05/.venv/Scripts/python.exe -m pip install --no-index --find-links experiments/p0-05/wheelhouse --require-hashes -r experiments/p0-05/requirements.lock
& experiments/p0-05/.venv/Scripts/python.exe -m pip check
```

还需要原项目P0-02/P0-03目录和pwsh；wheel含Windows专用二进制，不支持直接拿去Linux/macOS。原.venv不是便携产品安装包。

## 源码与夹具

| 文件 | 作用 |
| --- | --- |
| agent_service.py | 独立A2A服务；自己拥有任务/进度/产物/取消/恢复，不导入C1调度或调用执行器函数 |
| service_host.py | 测试服务监督、Job、白名单命令、loopback地址与进程证据 |
| agent_client.py | 官方SDK发现/Send/Get/List/Cancel及同源产物获取；无提交自动重试 |
| agent_integration.py | D3适配器、C1子类的事实记录/查询恢复/取消解释/结果授权检查 |
| agent_specs.py / agent_cases.py / fixtures/ | 任务/结果Schema、Agent Card扩展、原P0-02格式catalog和单任务/并行工作流 |
| test_agent.py / crash_engine.py | 18方法、真实HTTP断连与进程退出、状态和副作用断言 |
| prepare_environment.py / collect_environment.py / audit_delivery.py | 依赖/历史摘要、许可证与交付审计，不计作Agent执行测试 |

`fixtures/`保存确定性定义/请求；每次运行另外保存完整EnvironmentBinding，包含本机程序和动态loopback endpoint。工作流中不放绝对路径、凭据、PID、taskId或OS句柄。纯共享JSON/Schema声明不代表服务被引擎import执行；任务工作在独立进程和独立数据库中继续。

原Schema连接类型没有明文http选项。本轮保留cli/programRef作为**本机服务程序安装引用**，真实A2A endpoint/JSONRPC/1.0放在既有命名空间`aos:agent-services`扩展；cli本身不是A2A传输。这个契约空白及正式注册建议已记录，没有把HTTP伪标为https或改写历史Schema。

## 身份、权威与恢复

本地身份为runId、scope/node、attemptId、operationId；外部另有taskId、contextId和messageId。C1在发送前事务记录submit-intent与固定身份，取得taskId后事务记录关联。原attempt中的输入、环境/能力摘要与等待deadline不会因恢复换掉。已知taskId重启只GetTask，不调用SendMessage、不增加attempt、不重新消费批准。

原C1唯一源文件改动是将默认中断→unknown逻辑抽取为`_recover_inflight`方法，默认行为不变；P0-05子类只允许匹配身份的query-only恢复。无法核实的提交仍unknown。可选ListTasks关联核实只在本实验明确的messageId去重/元数据profile下启用，匹配必须唯一；A2A规范对SendMessage幂等只是MAY，不能泛化。

Agent的agent.sqlite拥有任务状态；C1的run.sqlite拥有工作流状态。remoteState/进度只是C1记录的观测，不覆盖本地终态。序号回退、身份错配、迟到/重复终态、旧定义和失效授权不会发布下游值。普通Agent节点也禁止maxAttempts>1；重连是查询，不是提交重试。

## 取消与产物

CancelTask请求、Agent收到、Agent返回CANCELED与C1决定cancelled分开留证。只有匹配taskId/身份的取消事实才能确认本地cancelled；不支持、失联或取消后仍完成则unknown且不发布旧结果。已接受任务的内部动作不能由本地过期/取消自动撤销，尤其远端拥有自己的工具权限时，本地审批只约束本平台发起和发布的动作。

产物通过标准A2A Artifact的data/url parts返回：结构化领域JSON和逻辑FileReference。只允许本Agent来源与UUID taskId推导的同源URL，不打开任意返回的本机路径；下载后验证类型、task/operation/agent来源、媒体类型、大小、SHA256及内容，再登记本地合成产物并由C1校验端口/最终输出。

INPUT_REQUIRED/AUTH_REQUIRED保留本地等待phase，未实现澄清/认证续谈；COMPLETED但无产物会等待查询，到期unknown。外部FAILED/REJECTED与本地unknown区分。测试使用合成Bearer标记并对协议/错误日志脱敏；它不是生产认证、TLS或沙箱。

## 证据与边界

[最终通过套件](./evidence/suite-20261024T061121087692Z/summary.json)、[原回归](./evidence/regressions.json)、[首轮失败](./evidence/suite-20261024T060420267685Z/summary.json)、[失败原因](./evidence/development-failures.json)、[交付审计](./evidence/delivery-audit.json)。每个测试有expected/actual断言和PID清理检查，每个run有输入/绑定、SQLite、快照/事件；每个Agent有启动命令、ready、HTTP记录、任务数据库、事件与产物，T08/T18有真实exit85和恢复前快照。

没有实现任意第三方互操作、跨设备调度、正式GUI、真实模型、TLS/OAuth、多租户、SSE/push、通用Agent插件、通用恢复迁移或生产规模压力。L1定义可加载/诊断，L2依赖环境与实现，L3不迁移全部凭据和运行环境；本轮仅Windows实际运行。原P0-03/P0-04的契约歧义与限制继续保留。完成后停止，不自动进入下一阶段。
