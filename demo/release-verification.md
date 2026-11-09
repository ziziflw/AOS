# AOS Demo v0.1.0 Windows x64 封装验收

发行目录为 D:\AIOrchestrationStudio\dist\AOS-Demo-v0.1.0-win-x64，文件合计 131,211,677 字节。旁边的同名 ZIP 为 47,490,221 字节，SHA256 为 e17fbb314cd787a616664daf5963bd140630b99253f522cb5d6c870b2a3f9f15。release-audit.json 记录最终 ZIP 的 CRC、10,062 个文件与发行目录逐文件哈希比较、运行数据库结果及正常启动记录。

将整个 ZIP 解压后打开 AOS.exe。Windows x64 需要已安装 WebView2 Runtime。首次启动把私有程序及 Python 3.12 运行环境复制到 %LOCALAPPDATA%\AOS-Demo\v0.1.0，后续使用该副本。工作流在 experiments\p0-08\workspace，运行记录在 experiments\p0-08\evidence。关闭应用再备份这两个目录。当前首次复制机制不提供同版本覆盖升级。

实际以清空开发工具 PATH 的进程从项目外临时解压目录启动真实 WebView2 工作台。正常入口完成 C1 健康握手，关闭后 Job 活动进程计数为零。GUI 验收使用同一包内工作台的测试窗口参数，编辑文本、保存、重载后执行合成模型到独立 MCP Echo，得到“合成回答：便携版验收输入 / 已整理”。独立读取 SQLite 发现对应成功运行和 MCP 服务账本。待审批期间强制结束执行器，重启后保留原运行身份和待审批状态，再取消。该测试验证执行器崩溃恢复。整台机器异常断电尚待验证。

点击左侧「本地模型连接」，选择服务、回环地址，测试并获取模型列表，选定模型后保存。在左侧场景下拉框载入相应文本工作流并运行。配置由后端保存，创建运行时固定到该次环境。采用已有 OpenAI SDK 的模型列表和聊天接口，仅开放文本和最大输出限制。仅接受显式 127.0.0.1 HTTP 端点，禁用代理、重定向和自动重试。公网地址已实际拒绝。未配置的本地节点按预期失败。两个预设均在真实窗口完成配置、发现、持久化、实际 HTTP 请求和状态返回，服务器响应来自受控合成夹具。本机默认端口没有 Ollama/LM Studio 服务监听。真实型号推理、模型加载策略及各服务对参数的执行仍待实测。未下载模型权重或调用收费 API。

保留官方 A2A SDK 和现有 D3 模块。发行工作台没有 A2A 服务绑定入口，未绑定的 Agent 定义已实际返回 A2A_SERVICE_UNBOUND；发行包连接真实外部 Agent 尚未验收。P0-03 至 P0-08 七个既有后端/宿主/协议套件本轮返回零，逐套输出位于 regression-*.log。新窗口验收记录见 acceptance-delivery.log 和 release-window.png。未在独立干净系统或 Windows Sandbox 运行，目前仅证明同一台 Windows 上脱离源码目录和全局开发工具可运行。

复现构建使用 experiments\p0-08\.venv\Scripts\python.exe，依次运行 demo\build_host.py 与 demo\portable.py。前者调用现有 Vite、Cargo、Tauri 并在独立构建目录编译，后者按锁定环境组装 Python、依赖、夹具和许可并生成 ZIP。采用私有目录运行时方便原执行器和受检 MCP 子进程复用同一解释器，免去 PyInstaller 单文件解包和动态导入钩子维护。归档不含运行数据库、用户工作区、模型权重或历史测试证据。校验未发现本轮生成的假凭据泄漏。发行版未签名，本轮仅提供便携 ZIP。

下一步优先在装有 WebView2 的干净 Windows x64 环境复验，再用已有本地模型核验实际服务版本、模型标识与用量。官方兼容范围参考 https://docs.ollama.com/api/openai-compatibility 和 https://lmstudio.ai/docs/developer/openai-compat 。窗口部署前提参考 https://v2.tauri.app/distribute/windows-installer/ 。
