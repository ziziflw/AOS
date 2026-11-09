# P0-07 · Graphite Workbench

Windows x64 上可实际操作的 **Tauri 2 + Vue 3 / Vue Flow** 实验工作台。画布 → 原 P0-02 Workflow Definition → 原 Contracts → 固定修订 → Rust 私有长度帧 → 原 Python C1 → SQLite/事件 → 画布状态。C1 仍是唯一业务状态权威。用户已要求本轮先沿用当前 UI，后续修改设定后再完善，不继续视觉润色。

## 启动已有构建

在 PowerShell 中：

```powershell
Set-Location D:\AIOrchestrationStudio
.\experiments\p0-07\launch.ps1
```

若本机策略不允许运行脚本，可直接启动二进制，不修改执行策略：

```powershell
& 'D:\AIOrchestrationStudio\experiments\p0-07\host\target\debug\host-window.exe' 'D:\AIOrchestrationStudio\experiments\p0-07' 'D:\AIOrchestrationStudio\experiments\p0-07\evidence\session-desktop'
```

正常入口不打开 WebView 调试端口、不启用故障注入。关闭窗口会协调保存并清理本机 Job。再次启动同会话尝试恢复原 run；pending 审批不自动批准，在途未确认结果由 C1 恢复成 unknown。unknown 会话禁止直接新建替代 run，应先核实；本轮没有通用核实/重试 UI。只做新的独立合成实验可显式使用 `launch.ps1 -SessionName another-synthetic-session`，这不是恢复旧副作用的办法。

## 操作一条真实工作流

1. 初始图：文本输入 → 文本处理 → **合成模型（本地模拟）** → Echo 参数封装 → **真实独立 MCP Echo 服务** → 提取文本 → 输出。
2. 单击节点，在右侧修改 Schema 参数，失焦提交。点击库节点或拖入画布添加；拖动端口连接。检查器也提供起点/终点连接按钮。
3. 校验由后端原 Schema/Contracts 完成。缺输入、断开节点、类型不匹配、未知版本和无兼容节点均不能运行。
4. 保存/重载使用左下文档名（仅字母数字、`_`、`-`），限定在本实验 `workspace/`。`*.document.json` 是原 workflow 加独立 layout 的编辑文档；另输出原格式 `*.workflow.json` 和 `*.layout.json`。导出/导入同样不把布局塞入执行语义。
5. 点击运行创建固定修订。可继续改草稿，但已启动运行的版本、节点配置和授权内容不改变。顶部/底部明确显示草稿与运行修订。
6. “载入审批示例”使用真实 MCP `simulated_effect`，其副作用仅写本实验合成账本。未批准不启动工具；下方动作内容由 C1 核对，批准绑定 run/operation/输入/配置/期限/指纹。
7. 模型参数 `fail` 和 `delayMs` 只用于确定性失败/取消实验。模型不是收费模型，temperature 仅验证数值约束，不声称影响真实推理。

Ctrl+S 保存，Ctrl+Z / Ctrl+Shift+Z 撤销/重做，Ctrl+D 复制，Delete 删除，Shift 多选，Ctrl+A 画布全选，Home 适应画布；中键或 Space+左键平移，Ctrl+滚轮缩放，Ctrl+Enter 运行，Shift+F5 请求取消；Ctrl+B / Ctrl+Alt+B / Ctrl+J 控制辅助区。表单输入不被画布删除/运行快捷键抢占。分隔条支持鼠标与方向键、Shift 加大步长、双击复位。左轨可折叠面板和切换密度；小窗口自动收起辅助面板，可重新展开。

## 复建与测试

依赖本机已有 MSVC、Cargo、Node、WebView2、P0-06 Python venv，以及旧实验源码/夹具。不是生产发行包，也未验证干净机器安装。

```powershell
Set-Location D:\AIOrchestrationStudio\experiments\p0-07\frontend
npm ci --ignore-scripts --no-audit --no-fund
npm run build
Set-Location ..\host
cargo build --features window --bins --locked --offline
Set-Location ..
& ..\p0-06\.venv\Scripts\python.exe -B -X utf8 test_backend.py
node gui-acceptance.cjs
& ..\p0-06\.venv\Scripts\python.exe -B -X utf8 audit_delivery.py
```

GUI 验收使用已捆绑 Playwright 的绝对依赖路径，**附着实际 Tauri WebView2**，不是浏览器替代页。仅测试启动参数 `test` 在 loopback 9237 开调试端口，并开放自有 worker 崩溃/固定窗口尺寸/WebView 缩放；不要把测试模式当日常入口。测试输入、数据库、截图与配置在每次独立 `evidence/gui-*` 或 `backend-*`；测试保存文档使用 `qa-*`，不覆盖用户普通文档名。

原回归仍在各自目录执行 `test_runtime.py`、`test_mcp.py`、`test_agent.py`、`test_host.py`，各用原 Python 环境；历史 suite 不覆盖，仅 latest 正常更新。新 NPM 安装禁用了生命周期脚本，构建仅执行锁定工具；Cargo 离线锁定构建，无新增 Python 安装。

## 代码与证据

- `frontend/src/App.vue`、`FlowNode.vue`、`style.css`：当前工作台。Vue Flow 的视图模型承载几何/选中，原语义节点单独保留；运行状态只读 C1。
- `executor.py`：受限草稿 API / run 管理，继承 P0-06 transport 和 endpoint，复用原 Contracts/Runtime/Store/MCPRegistry。
- `workbench_profile.py`：原格式可信 catalog，新增少量 builtin 类型转换与明确模拟模型；没有重写工作流方言。
- `windows_adapter.py`：P0-06 固定 Windows 适配的本轮派生，使用 P0-06 Python 和 P0-04 原服务，本轮 root shim 仅改变自有证据根。
- `host/`：P0-06 宿主生命周期的本轮派生，Job/权限/帧边界延续；Rust 不打开 run 库、不写业务终态。JSON 启用 float_roundtrip 保持数字往返。
- `fixtures/`、`workspace/`：合成输入与保存的编辑文档；`licenses/`、`dependency-inventory.json`、两个 lock 文件记录依赖。
- [最新后端证据](./evidence/latest-backend.json)、[最新 GUI 证据](./evidence/latest-gui.json)、[独立交付核对](./evidence/delivery-audit.json)、[构建/源码摘要](./evidence/final-build-identity.json)、[失败索引](./evidence/development-failures.json)。latest 只是导航，事实在所指独立 suite。
- [验收报告](../../planning/p0-07-workbench-verification.md)、[IPC 扩展](../../planning/p0-07-ipc-extension.md)、[架构发现](../../planning/p0-07-architecture-findings.md)、[交付与边界](../../planning/p0-07-delivery-report.md)。

范围：10 类受检节点、单个活动 run、多次串行新 run；不提供完整 A2A 管理、任意脚本、真实模型/账户、插件市场、嵌套图、任意停靠、全 JSON Schema 编辑器、完整历史管理或生产安装包。未知节点/字段作为草稿保留并诊断，保存成功不代表能执行。L1/L2/L3 不变；仅 Windows 实测，WebView 125/150% 缩放不能代替 Windows 实体显示 DPI 验收。
