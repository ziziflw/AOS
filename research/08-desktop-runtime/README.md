# R08 · Windows桌面宿主与执行进程

P0-06增量：[真实Tauri2窗口IPC及Rust探针](../../planning/p0-06-host-verification.md)已分别实际验证；[长度协议/权限](../../planning/p0-06-ipc-contract.md)、[Job清空与SQLite关闭竞态修正](../../planning/p0-06-runtime-lifecycle.md)、[包体/语言成本](../../planning/p0-06-architecture-findings.md)。本机开发环境通过不等于干净机器发行、OS沙箱或跨平台通过，以下原研究/历史未验证范围保留。

P0-05增量：[独立Agent与执行器不同生命周期](../../planning/p0-05-agent-verification.md)：测试监督器拥有服务Job，执行器exit85后Agent仍运行；恢复查询原task，测试末只清理自有进程。尚未做Tauri宿主/监督器崩溃/干净机器打包，不能由此宣布桌面集成完成。

P0-04增量：[进程证据](../../planning/p0-04-mcp-verification.md)包含自有MCP Server、Windows Job、venv launcher/真实Server/子进程及拥有进程退出清理；[限制](../../planning/p0-04-architecture-findings.md)明确这不是OS强沙箱、Tauri集成或干净机器分发验证。以下原两路线研究保留。

P0-02新增[跨环境兼容与绑定](./portability-and-environment-binding.md)：L1为必须设计目标，L2条件执行，L3首版不承诺；Windows x64→Linux x64→macOS。以下是P0-01路线对照，语言/宿主仍未最终选定。

证据：[Vue 3](../sources.md#s40)、[Vue Flow](../sources.md#s01)、[Tauri Sidecar](../sources.md#s37)、[Capabilities](../sources.md#s38)、[Windows打包](../sources.md#s39)、[SQLite](../sources.md#s21)。所有组合均未实测。

## 两条主路线（不预先决定）

| 维度 | Rust核心调度 | 独立执行进程（TypeScript/Node或Python） |
| --- | --- | --- |
| 宿主 | Tauri/Rust拥有执行控制，Vue展示 | Tauri管理执行进程，进程拥有执行控制 |
| 框架复用 | Rust生态对应能力需另查，跨语言调用增加边界 | TS可评估AI SDK；Python可评估LangGraph/LiteLLM |
| 状态权威 | Rust运行控制写业务状态，执行器报告结果 | 执行进程运行控制写状态，Rust只监督生命周期 |
| 潜在收益 | 系统接口集中、减少跨进程控制路径 | 避免把成熟语言生态重写到Rust，故障可分进程观察 |
| 潜在成本 | 引擎与适配工作量、阻塞隔离、生态接入 | IPC、打包运行时、进程回收、协议版本与升级 |
| 安全 | 原生能力仍需策略；同进程插件风险 | 独立进程仍有同用户权限，不能自动视为沙箱 |
| 必须测 | 恢复正确性、框架接入、并发阻塞、总包体 | IPC背压、崩溃边界、干净机器分发、重连和清理 |

候选折中是Rust负责系统能力、凭据、进程监管，独立进程负责调度。但必须让其中一方成为run状态与调度唯一权威，不得双方各实现重试和恢复。

Tauri Sidecar已支持外部可执行文件及标准流，需按目标架构命名和打包；“能启动Python/Node程序”不代表目标用户机器无需额外资源，也不证明打包、更新或签名已解决。

## IPC与生命周期候选

通信候选为stdio帧协议、命名管道或带认证的loopback服务。E07先验证最小stdio方式，再根据并发、二进制传输和重连要求比较其他路线。帧必须有长度/消息边界、请求关联、协议版本、最大尺寸；stdout与日志分离。

宿主启动 → 版本握手 → 健康状态 → 提交命令/订阅事件 → 正常关闭时停止接单、请求取消或持久暂停、刷新状态、终止子进程 → 确认进程树退出。宿主崩溃、执行进程崩溃与用户取消分别处理。具体超时阈值待实验决定。

[Node child_process](../sources.md#s41)和[Windows Job Objects](../sources.md#s36)是生命周期参考；是否通过具体Tauri shell插件覆盖孙进程、特殊退出及breakaway仍未验证。

## 存储与部署约束

SQLite候选只用于同机持久状态与元数据；大型产物在受控目录存放引用。写入权威和事务边界先定，避免UI、宿主、执行进程同时更新同一run。WAL单写者、busy、checkpoint和备份流程需要E05覆盖。所选SQLite版本须检查官方已知问题，本轮未选库版本。

Windows分发需验证WebView2、VC运行库/其他执行依赖、架构、用户级安装、离线模式、签名与升级。Tauri文档有WebView2离线分发选项，但总包体和离线可用性尚无实测。首选支持的Windows版本、x64/ARM64和便携/安装包由用户后续确定。

E07输出两路线的实测证据和成本；它本轮只是实验计划，不启动工程或安装运行时。

