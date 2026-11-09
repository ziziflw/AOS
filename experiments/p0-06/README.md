# P0-06 · Windows宿主、独立执行进程与本地IPC

2026-10-27，隔离技术实验。最终 **15项专项通过**，其中T15实际运行Tauri 2 / WebView2窗口；P0-03原18项、P0-04原14项、P0-05原18项回归分别通过。不是正式桌面产品、任意插件平台或OS沙箱。没有付费模型、真实账户、PFT修改或Git提交。

## 阅读入口

- [最终15项摘要](./evidence/suite-20261027T121250322189Z/summary.json)、[最新指针](./evidence/latest.json)、[历史失败说明](./evidence/development-failures.json)。
- [实际窗口报告](./evidence/suite-20261027T121250322189Z/test_T15_real_tauri_window_ipc/window/window-report.json)、[Rust窗口桥调用](./evidence/suite-20261027T121250322189Z/test_T15_real_tauri_window_ipc/window/window-bridge.jsonl)。报告之外，T15还独立检查SQLite终态与Rust批准调用。
- [验证矩阵](../../planning/p0-06-host-verification.md)、[IPC契约](../../planning/p0-06-ipc-contract.md)、[生命周期](../../planning/p0-06-runtime-lifecycle.md)、[架构发现](../../planning/p0-06-architecture-findings.md)、[交付报告](../../planning/p0-06-delivery-report.md)。
- [依赖及体积](./environment-evidence.json)、[Python哈希锁](./requirements.lock)、[Python清单](./dependency-inventory.json)、[Rust清单](./rust-dependency-inventory.json)、[Cargo锁](./host/Cargo.lock)、[交付审计](./evidence/delivery-audit.json)。

## 实际组成

```text
本地Tauri测试窗口或Python测试驱动
  → Rust Host：固定权限角色、请求校验、Windows Job与超时
  → 私有继承stdio：4字节大端长度 + UTF-8 JSON
  → executor.py：通信与会话适配
  → 原P0-03 Runtime / P0-04 BoundRuntime / P0-05 AgentRuntime
  → 原C1 SQLite快照与事件（唯一工作流状态权威）
      ├─ 原官方SDK MCP独立服务 → 自有Job内
      └─ 原官方SDK A2A独立服务 → 外部实验监督器的独立Job
```

Rust不打开run.sqlite；没有复制调度器。`ipc-receipts.sqlite`只保存命令摘要与原响应，不能推进业务状态。Agent服务自己的任务库拥有远端任务事实，不能覆盖C1。

源码：`host/src/lib.rs`为宿主，`main.rs`为控制台探针，`window.rs`与`host/ui/`为真实窗口。`executor.py`复用原Session；`schema_adapter.py`以已安装jsonschema执行原Draft2020-12 Schema；`system_layer.py`和两个`*_server_entry.py`只解决固定程序/本轮证据目录绑定。原P0-03至P0-05源文件完全未改。`supervisor.py`只拥有本轮外部Agent，`test_host.py`提供故障与真实进程断言。

窗口WebView2运行时数据显式置于会话的`webview-profile`；早期默认AppData测试缓存已核实并归档到本轮evidence，见[隔离修正记录](./evidence/isolation-correction.json)。没有操作其他应用数据。

## 已有本机环境运行

PowerShell，在本项目目录执行；不需要安装Vue、Node前端依赖或大型工作流框架：

```powershell
Set-Location D:\AIOrchestrationStudio\experiments\p0-06
cargo build --manifest-path .\host\Cargo.toml --locked --features window --bins
& .\.venv\Scripts\python.exe .\test_host.py
& .\.venv\Scripts\python.exe .\collect_evidence.py
```

每次测试建立新的UTC suite目录；真实窗口T15会短暂出现并自动退出。人工打开窗口：

```powershell
$taskRoot = 'D:\AIOrchestrationStudio\experiments\p0-06'
& "$taskRoot\host\target\debug\host-window.exe" $taskRoot "$taskRoot\evidence\manual-window-01"
```

先启动执行进程，再选择内置工作流并加载启动；合成审批操作必须点击批准或拒绝。可查状态、下一批事件、取消和保存关闭。重开相同会话后用“恢复已有运行”，不要当作新运行创建。每个会话只允许一个run；新实验用新的会话目录名。手工窗口没有自动批准；只有明确传入`selftest`的测试入口启用自动化测试操作者。

最小探针可直接输入JSONL；它是测试驱动入口，**Rust→Python实际边界仍为长度分帧**：

```powershell
& .\host\target\debug\host-probe.exe $taskRoot "$taskRoot\evidence\manual-probe-01" approver normal normal
```

输入例：`{"v":"aos-local/0.1","kind":"request","id":"health-start","op":"host.start","body":{}}`，再以新id调用`health`。角色由可信本机启动配置指定，不能在消息body修改。最后一个参数只有明确`test`才开启固定`host.crash-worker`故障入口；正式测试窗口不开启它。

## 依赖复建与回归

Windows x64，本机Rust1.95.0/MSVC、Visual Studio2022 C++工具、WebView2 155.0.4283.62、Python3.12.14。Tauri2.12.5、tauri-build2.7.4；具体传递版本以Cargo.lock为准，必须使用`--locked`。本机缓存的`--locked --offline`构建也通过，但未证明干净机器离线安装。

Python环境由原P0-04/P0-05可信wheelhouse离线组合，48个运行分发包；mcp1.30.0、a2a-sdk1.2.3、jsonschema4.26.0。已有适用Python建立本轮`.venv`后，可恢复精确制品：

```powershell
& .\.venv\Scripts\python.exe -m pip install --no-index --find-links ..\p0-04\wheelhouse --find-links ..\p0-05\wheelhouse --require-hashes -r .\requirements.lock
& .\.venv\Scripts\python.exe -m pip check
```

保留原P0-03/P0-04/P0-05目录及各自环境，不能只复制本轮venv即宣称可独立部署。当前可信服务实现、catalog、Schema和fixture都从原实验导入。原回归命令在各自目录执行：P0-03用既有Python运行`test_runtime.py`；P0-04/P0-05分别用自己的`.venv/Scripts/python.exe`运行`test_mcp.py`/`test_agent.py`。各自在历史目录新增证据并更新latest；本轮引用见[回归指针快照](./evidence/regressions.json)。

## 证据与边界

每个case包含驱动输入/响应、工作流/请求/环境定义、C1快照/事件/SQLite、期望实际断言、进程与协议记录。T06保存实际帧十六进制及错误响应；T10保存崩溃前后；T13保存原taskId、Agent任务库和恢复查询。日志不代表终态，断言读取真实C1及服务库。

只开放固定内置配置：原P0-02场景A加载，P0-03串行/并行/审批，真实MCP结构化/延时/合成效果，以及A2A正常/合成效果/取消不支持。未知节点/字段/参数由原契约和明确IPC检查拒绝，不能上传任意工作流命令行、脚本或路径。

单机、单run/会话、有限图/事件/消息验证；事件推送可能在断连或有界队列溢出时丢失，必须按C1 seq查询补齐。长期背压、慢读者压力、时钟回拨、强OS隔离、签名/MSI/NSIS、干净机器分发、Linux/macOS未验证。保留Python是后续实验选择，不冻结产品技术栈。完成本轮后停止。
