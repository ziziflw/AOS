# P0-08 · 官方模型 SDK 与工作台离线闭环

沿用 Graphite 界面、Vue Flow、P0-06 Rust 生命周期/IPC、P0-07 编辑定义接口及原 C1。**真实 SDK + 真实本机 HTTP；无模型推理、无收费调用。**OpenAI / Anthropic 实际供应商未配置、未授权。

## 启动

本机已准备独立 `.venv` 与构建产物，在 PowerShell 中运行：

```powershell
Set-Location D:\AIOrchestrationStudio\experiments\p0-08
.\launch.ps1 -SessionName desktop
```

左侧“离线 SDK 场景”可载入 OpenAI/Anthropic 文本或 JSON 工作流。选中模型节点后，在原属性检查器设置支持的参数及运行预算；保存/重载仍由受限后端接口完成。运行结果区显示 C1 确认的 Token、预留和合成估算费用。SDK场景选择会加载新草稿，请先保存需要保留的编辑。

`fixture-*` 是自有服务的故障/响应夹具名称，绝非供应商实际模型。保留原本地函数模拟模型及真实 MCP 合成节点，标签分别标识。真实供应商没有假装可用的配置按钮。未知终态会阻止同一会话直接再次派发；需核实，不可通过重复点击重试。

## 重建与验证

只用项目自己的目录，不执行远程安装脚本。新的 Windows x64 Python 3.12 环境可以使用保留的 wheelhouse：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-index --find-links wheelhouse --require-hashes -r sdk-requirements.lock
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe model_profile.py
Set-Location frontend
npm ci --ignore-scripts
npm run build
Set-Location ..\host
cargo build --features window --bins --locked --offline
Set-Location ..
.\.venv\Scripts\python.exe test_models.py
.\.venv\Scripts\python.exe test_host_models.py
node gui-acceptance.cjs
.\.venv\Scripts\python.exe audit_delivery.py
```

原本机 Rust crate 缓存、MSVC/WebView2 以及 Node 22 是前提；`--offline` 不会下载缺失 crate。GUI脚本使用本机 Codex 捆绑 Playwright 的明确路径和真实 WebView2 CDP 9238，换机器需调整测试工具定位，不能宣称生产发行包已就绪。正常启动不开放调试端口。`scaffold.py` / `update_frontend.py` 是本轮生成过程记录，**不是日常重建步骤**。

## 代码边界

- `model_profile.py` / `fixtures/`：原 P0-02 Schema 格式的节点、能力、工作流和环境绑定；未另造工作流方言。
- `model_adapter.py`：D1，直接调用官方 AsyncOpenAI / AsyncAnthropic。SDK 负责协议请求、HTTP、响应对象与异常；AOS 只做能力、安全及结果映射。
- `http_fixture.py`：受控 loopback HTTP 测试服务与脱敏请求事实账本，明确合成。
- `model_runtime.py`：可信 C1 子类做准入/结算；复用原 scheduler、attempt、SQLite `_change` 和审批。原 `runtime.py` 只抽取默认行为不变的 usage 校验钩子。
- `executor.py`：复用 P0-07 Endpoint 和 P0-06 IPC。先取得运行库锁，再写清单/创建凭据和服务，第二认领不能影响第一运行。
- `credentials.py`：既有 pywin32 调用 Windows Credential Manager；只创建/读取/删除本轮合成目标。不枚举用户凭据。
- `host/` / `frontend/`：P0-07自有宿主与编辑器的隔离实验副本，仅调整固定执行进程和必要模型控件。Vue Flow/Tauri 上游源码未修改，未复制调度器。

## 证据与限制

机器入口：`evidence/latest-models.json`、`latest-host.json`、`latest-gui.json`、`delivery-audit.json`。每套输入、SQLite、快照、事件和 HTTP 事实分别保留；GUI目录含真实截图、交互检查、构建哈希。初轮失败日志及目录均保留。

新环境含两个 SDK 完整运行依赖闭包，锁文件名称 `sdk-requirements.lock` 包含既有 MCP/A2A 依赖，并非只包含 SDK。许可原文与 NOTICE 位于 `third-party/`，轮子哈希/依赖/原生文件/钩子检查在 `evidence/dependency-review.json`。pywin32 的既有引导只添加 DLL 搜索目录；未运行分发中的维护/安装脚本。此检查不是完整供应链安全审计。

强制关闭可能留下 Windows 会话级合成凭据；`owned-credential.json` 仅记录本轮目标别名。全部应用停止后可运行 `cleanup_credentials.py`，只删除这些明确收据对应目标，不枚举或清理其他用户凭据。该清理不能对仍运行的实验执行。

输入 Token 上界与价格只针对合成服务。真实模型需要专属计量/能力/费率及授权配置，尚未通过真实供应商验证。不支持流式、缓存/多模态/工具调用、通用路由自动回退、未知消耗自动解冻或真实凭据管理 GUI。取消客户端不等于服务端停止或免计费。

完整结论见 [交付报告](../../planning/p0-08-delivery-report.md)。完成于本轮，不进入 P0-09。
