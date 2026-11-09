# P0-02交付报告

日期：2026-10-24。项目位置：`D:\AIOrchestrationStudio`。**本轮完成契约、场景、跨环境与架构设计及离线静态检查；没有开发正式GUI或执行引擎，没有进行收费模型调用。**

## 交付清单

新增25个文件：13份Markdown、10份声明性JSON（1份Schema与9份夹具）、1份验证结果JSON、1份离线检查脚本。项目当前共43个文件：31份Markdown、11份JSON、1份Python；16个子目录。

```text
research/
├── 02-node-contracts/
│   ├── workflow-schema-draft.md
│   ├── node-port-contracts.md
│   ├── adapter-capabilities.md
│   ├── schemas/contract.schema.json
│   └── examples/
│       ├── fixture-catalog.json
│       ├── scenario-a.workflow.json
│       ├── scenario-a.run-request.json
│       ├── scenario-b.workflow.json
│       ├── scenario-b.run-request.json
│       ├── scenario-c.workflow.json
│       ├── scenario-c.run-request.json
│       ├── environment.windows.template.json
│       └── environment.linux.template.json
├── 05-tool-agent-protocols/
│   └── adapter-boundaries.md
├── 08-desktop-runtime/
│   └── portability-and-environment-binding.md
└── 10-feasibility-experiments/
    ├── scenario-a-multi-model.md
    ├── scenario-b-tool-integration.md
    ├── scenario-c-agent-approval.md
    ├── compatibility-matrix.md
    └── validation/
        ├── README.md
        ├── validate_contracts.py
        └── static-check-results.json
planning/
├── p0-02-architecture-review.md
├── p0-02-open-decisions.md
└── p0-02-delivery-report.md
```

另更新10个既有入口/草案：根README、research/README、sources、R02/R05/R08/R10入口、charter、module-boundaries、open-decisions。保留P0-01历史报告与旧实验内容，补上阶段说明；没有删除旧文件。

## 核心契约成果

[版本化Schema草案](../research/02-node-contracts/workflow-schema-draft.md)采用Draft 2020-12，候选版本0.1.0-draft.1。包含要求的10项概念：WorkflowDefinition、WorkflowVersion、NodeDefinition、NodeInstance、PortDefinition、EdgeDefinition、AdapterDefinition、CapabilityDeclaration、ExecutionPolicy、EnvironmentRequirement；另描述环境绑定、运行输入与值封套。

定义和运行记录分开；类型和实例分开；配置和当前输入分开；workflow/node/adapter/API版本独立；UI布局不决定语义；逻辑资源引用代替便携文件中的机器路径；秘密仅用引用。已知结构严格校验，未知节点/未来字段走保留诊断模式并阻断执行。

Fixture catalog提供23个示例节点描述和5个示例适配器描述，仅用于表达三个场景的精确I/O与策略，**没有可执行实现，也不是支持的产品节点基线**。全部供应商能力为fixture，不能将其参数直接用于真实模型。

## 本轮验收问题的回答

| 问题 | 当前回答与证据 |
| --- | --- |
| 工作流如何描述节点、连线、配置与版本？ | workflow.graph保存NodeInstance与Edge，typeId/typeVersion引用catalog，version.revision标识业务修订；catalogLock固定描述快照。[契约](../research/02-node-contracts/workflow-schema-draft.md) |
| 自由连线怎样判合法？ | 方向/通道/类型/nullable/基数、必填、顺序、环与子图分层校验；不兼容需显式转换。[端口](../research/02-node-contracts/node-port-contracts.md) |
| 模型参数谁声明、谁验证？ | D描述，B1注册，A1呈现；B1/D后台按锁定能力重新校验，C1验证策略、E2决定权限。[能力](../research/02-node-contracts/adapter-capabilities.md) |
| 三类执行对象怎样进入同一体系？ | 共享DispatchRequest关联/预算/授权/事件，保留model/tool/agent不同请求、结果和生命周期。[边界](../research/05-tool-agent-protocols/adapter-boundaries.md) |
| Windows图如何在Linux/macOS加载重绑？ | 同一便携定义+本机EnvironmentBinding，L1必须设计、L2条件执行、L3不承诺；平台按用户指定顺序推进。[兼容](../research/08-desktop-runtime/portability-and-environment-binding.md) |
| 未知节点如何保存/展示/诊断？ | 原JSON树保留，严格校验错误与保留模式分开；未知实现禁止执行。当前只测值级往返，产品UI尚未实现。 |
| 哪些能重试？ | 受信任无副作用/只读可有限重试；写/未知禁止盲重试；真实幂等键/查询与授权充分时才可考虑idempotent。超时不等于未发生。 |
| 三个场景能否同契约表达？ | 三份workflow、三份run-request及同一catalog通过结构、配置和有限图语义检查；不等于场景已运行。[A](../research/10-feasibility-experiments/scenario-a-multi-model.md)/[B](../research/10-feasibility-experiments/scenario-b-tool-integration.md)/[C](../research/10-feasibility-experiments/scenario-c-agent-approval.md) |
| 哪些是技术依据、哪些待实验？ | 规范/官方文档事实见S来源，设计是本项目候选；117项仅静态，真实接口/恢复/隔离/跨OS执行全部待测。[矩阵](../research/10-feasibility-experiments/compatibility-matrix.md) |
| 下一轮最先验证什么？ | 无GUI/无收费的有界子图、skip/汇合、Agent任务身份、审批暂停/重连/取消与框架checkpoint桥接，检验唯一状态权威及未知副作用不盲重发。[架构审查](./p0-02-architecture-review.md) |

## 本轮实际检查与结果

[机器可读结果](../research/10-feasibility-experiments/validation/static-check-results.json)记录117项符合预期、0失败。预期负例被拒绝也计为检查通过，不能理解为117项产品功能已实现。

使用现有Python 3.12.14/标准库和PowerShell 7.6.5/Test-Json；主机报告Microsoft Windows 10.0.22631/AMD64。没有安装新依赖。结构检查覆盖9份根文档，二次校验覆盖节点配置/能力、场景输入输出与值封套；包含null、错误类型、缺必填、不支持参数等负例。

有限语义检查覆盖版本锁、端口/通道/类型/基数、必填、汇合顺序、直接成环、子图引用、禁用来源、危险重试和后继闭包。声明式环境检查能指出缺服务/凭据/连接和目标漂移，但没有探测真实服务/程序/秘密/OS权限。Linux模板检查在Windows完成，不是Linux运行结果。

未知数据保留测试仅用Python JSON树往返；迁移器、产品保存器和GUI诊断尚未实现。候选模块导入图检查无环，但没有应用源码可做真实依赖分析。输出文件保存检查脚本及Schema/夹具摘要，便于复核。

真实模型调用0、MCP连接0、Agent任务0、Linux运行0、macOS运行0。原E01–E07实验没有被整体标记通过。

## 来源核验与版本差异

[更新索引](../research/sources.md)共57条：55条文档核验，2条正文访问失败。保留原48条，新增S49–S57九条；S47/S48未被改成成功。补查JSON Schema Core、Test-Json、MCP两种SDK发布、A2A规范/SDK、Gemini接口和HTTP语义。

下一阶段候选：MCP 2025-11-25工具子集；Python mcp2.3.0或TS client/server/core2.4.0及node2.1.2；A2A发布tag1.0.1/线协议1.0与Python SDK1.2.3。**版本候选不等于已安装或兼容通过**。SDK发布说明涉及更晚MCP协议，固定A2A站点页仍写Latest Released1.0.0，与release1.0.1不一致；记录差异并要求实验前核对tag。tree页面访问受限，没有宣称源码审计完成。

## 关键架构风险与开放决策

保持原10项逻辑职责。B1拥有定义/注册/静态校验；C1唯一拥有业务状态；E2唯一批准权限；D1/D2/D3映射和执行；E3保管OS秘密并适配平台；E1存储；A1交互；A2追踪/评估。没有为数量整齐拆微服务。

最需防止返工的部分：
- E1/E2/E3文字交互如果照搬为类import会成环，采用接口和装配注入候选解决；不是改变业务所有权。
- 框架checkpoint和本地状态可能形成两个权威，需先做故障实验。
- 条件skip、互斥汇合、有界子图和attempt/iteration身份影响整个运行契约。
- 远端Agent内部操作不能被本地审批框自动约束，提交前授权与最终发布批准分开。
- SDK隐藏重试、远端取消未知和成本预留必须统一受C1约束。
- 描述快照锁不是实现制品认证；远端模型/工具漂移需重新核验。

Rust/TS/Python、完整执行框架、Linux/macOS凭据后端、普通子工作流/流式增量、真实制品锁和迁移算法仍开放，详见[P0-02开放决策](./p0-02-open-decisions.md)。

## 下一阶段建议与用户输入

顺序建议：合同运行时/框架故障探针（无GUI、无收费）→Windows IPC与A2A/MCP最小协议探针→Windows/Linux同图重绑与无副作用执行→授权/崩溃恢复强化→最后在指定供应商与预算下验证真实多模型。正式GUI/打包在关键语义证据形成后再排期。

用户已决定的平台顺序与兼容层级不再询问；实际收费实验前才需模型/预算，真实工具/Agent实验前才需授权端点或测试服务范围；最低OS/发行版、秘密存储后端及分发方式仍可后续决定。本轮无需等待这些输入。

## 文档质量与范围审计

最终检查：43文件/16子目录，31份Markdown、11份JSON、1份离线检查脚本；259处内部相对链接及来源锚点均可解析。57个来源编号与55/2状态统计一致；无空文件，无其他扩展文件；跨文档完全相同且不少于100字符的长段落为0（不代表没有必要的语义交叉引用）。

与本轮开始时18份文件的SHA-256清单比较：10份按上述范围更新，8份保持原字节，0份删除，新增25份。P0-01交付报告保持原样。结果JSON记录的11份Schema/夹具/检查脚本摘要均与当前文件一致，117项检查无失败。

PFT及同步sources均不在本轮写入范围，没有对其执行变更命令；没有Git操作、模型下载、依赖安装、插件安装或正式应用工程。检查脚本只调用现有本地Schema校验工具，不执行工作流中的节点。对PFT的未变更确认依据本轮操作范围，不是对外部进程行为的全盘审计。

P0-02到此停止，等待下一轮任务；不自行进入正式编程或真实接口实验。

