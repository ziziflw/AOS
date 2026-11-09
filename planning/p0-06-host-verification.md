# P0-06 Windows宿主验证

2026-10-27，Windows11 x64 build22631。最终[专项摘要](../experiments/p0-06/evidence/suite-20261027T121250322189Z/summary.json)：**15测试方法通过，0失败、0错误、0跳过**。其中T15是实际Tauri窗口，其他case是实际Rust探针；不能把它们统称为15次真实窗口测试。

## 证据矩阵

下表case目录均在[最终suite](../experiments/p0-06/evidence/suite-20261027T121250322189Z)。每个case有`assertions.json`期望/实际和`owned-process-check.json`；session下有驱动请求/响应、宿主trace、真实C1数据库、输入定义及导出。故障位置在测试名、输入hex/模式/生命周期记录中。

| 测试 | 实际输入/注入 | 检查的真实结果 | 证据类别 |
| --- | --- | --- | --- |
| T01 | 固定worker；init-fail、startup-timeout、重复start | 健康/版本来自实际子进程，实际PID归Job；失败/超时拒绝且清理 | Rust→Python真实进程 |
| T02 | 原scenario-a workflow；变更token、非法builtin；7份有效/无效Schema对照 | 原摘要一致、完整Contracts加载、错误拒绝；本轮jsonschema与旧桥结果相同 | 实际加载+静态契约解释，不是A中真实模型 |
| T03 | 原P0-03 serial、parallel | C1所有节点真实succeeded，事件来自同库seq；原内核并行/依赖详断言另有18项回归 | Rust→原C1，节点为Mock |
| T04 | P0-04 structured_result | 真实stdio初始化与tools/call，C1正确类型结果及终态 | 官方MCP1.30.0/协议2025-11-25，自有合成服务 |
| T05 | A2A echo、effect | taskId持久绑定；效果任务批准前未提交，批准后只有一个任务并成功 | 官方A2A1.2.3/线1.0，独立合成服务 |
| T06 | 非法JSON/UTF8/重复键/未知字段；exact-limit/超限/截断帧；未知命令 | 真实执行端/宿主返回明确错误，没有路径/脚本执行；限制按真实字节测试 | 实际长度协议边界 |
| T07 | 插入expired-request响应；重复/冲突create；分页事件 | 晚到响应不能满足当前请求；相同create一个run，改内容冲突；C1 seq无缺口/重复，推送关联打开流的请求 | 实际通信+持久事件 |
| T08 | viewer/operator越权；effect pending/旧指纹/拒绝/重复批准；真实MCP effect | 后端阻断；拒绝不派发；批准后attempt1；MCP未批准前Server未启动，批准后effect-committed恰好1 | 后端权限、Mock效果及真实合成MCP分别有证据 |
| T09 | 并行中取消、待审批取消、正常宿主stdin EOF | 原C1取消/撤销grant，下游无旧输出；普通退出先suspend ACK，Job活动成员0 | 真实生命周期+协作Mock |
| T10 | MCP tools/call在途时终止实际executor Job | 已确认输入保留，原runId；工具unknown，attempt1，不盲重跑；宿主先报断连而非业务终态 | 实际进程中断、恢复 |
| T11 | 审批暂停时kill真实Rust宿主；批准完成后二次重启 | pending未自动批准；同run；明确决定后成功，已完成效果attempt不变 | 实际宿主崩溃及C1恢复 |
| T12 | 第二个真实宿主/执行器打开同一run库 | CONTROLLER_ALREADY_OWNED；原所有者关闭后可认领，无第二调度权威 | 原Windows文件锁+SQLite |
| T13 | Agent在途时kill宿主；另一case正常suspend | Agent独立继续；本地保留原taskId，恢复query-only，同attempt/task且没有第二提交 | 实际外部Agent生命周期 |
| T14 | MCP含idle子进程时关闭；A2A不支持取消时取消/关闭 | 自有树最终无残留；远端未知不伪称取消，旧结果不发布，Agent仍活 | 实际Job与A2A取消解释 |
| T15 | 真实Tauri2/WebView2 JS自测 | invoke→Rust→Python；等待审批/错误/批准/事件/关闭；独立SQLite/桥trace及实际会话缓存目录佐证 | **真实窗口IPC**，没有mock Tauri API |

T06输入包括实际长度头与hex，可重现错误。T10/T13的`before-crash.json`、`after-recovery.json`和C1原库/Agent任务库可核实故障前后。C1输出是typed envelope，不把JSON/文件引用全部转字符串；状态/attempt/iteration语义仍由原代码负责。

## 回归与历史失败

- P0-03：[18项通过](../experiments/p0-03/evidence/suite-20261027T114843167780Z/summary.json)。原串行、并行、条件/汇合、有界循环、类型、审批、取消、持久化原子性等保持。
- P0-04：[14项通过](../experiments/p0-04/evidence/suite-20261027T114843520145Z/summary.json)。原真实MCP/SDK/故障/嵌套进程检查保持。
- P0-05：[18项通过](../experiments/p0-05/evidence/suite-20261027T114843402804Z/summary.json)。原独立A2A、taskId、query-only恢复与未知终态保持。

以上独立统计，不与旧117项静态检查、断言数、进程数或来源数合计。旧源码未改，回归按原机制产生新suite/latest，旧suite与研究均保留。

[失败索引](../experiments/p0-06/evidence/development-failures.json)列出全部试跑。早期PowerShell策略失败、本轮目录绑定、错误的合成参数/模式、测试误查不存在的MCP effects表均保留；后者实际服务效果在records的effect-committed行。最重要的关闭I/O失败及修正见[生命周期](./p0-06-runtime-lifecycle.md)。首次Tauri构建还因缺图标失败，原build-window.log保留，创建本轮简单图标后成功。未构建时的T15明确skip，从未以探针冒充。

## 验证等级

**实际执行**：上述有限Windows单机case、官方固定SDK真实协议、真实独立进程、真实Tauri invoke、原三套18/14/18项独立回归。Agent内容及工具效果是自有合成数据，不是LLM/MCP第三方商业操作。

**静态检查**：P0-02原Schema/模块边界、Tauri capability限定main、CSP与未注册通用插件、依赖锁/源摘要、跨环境不包含Windows句柄的消息设计。

**仅设计/未验证**：Linux/macOS替代Job实现、正式身份/凭据、恶意插件OS隔离、完整桌面打包/签名/安装升级、长期任务/高压/慢读者、任意MCP/A2A互操作、多窗口/远程origin攻击检查、真实模型/计费。窗口自测通过不等于用户体验、物理人工身份或安全审计通过。
