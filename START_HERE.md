# 启动 P0-11 集成工作台

**已有开发构建（Windows x64）**。本机使用 PowerShell 7 和 WebView2。双击 [启动集成工作台.cmd](apps/aos-workbench/启动集成工作台.cmd)，或在 PowerShell 中执行本轮实测命令：

```powershell
Set-Location D:\AIOrchestrationStudio
& .\apps\aos-workbench\start-integrated.ps1
```

首次启动从现有 v0.1.3 便携目录取私有 Python、SDK 和契约，建立 %LOCALAPPDATA%\AOS-Demo\p011。已有本地服务配置仅复制通过回环地址检查的模型 ID 与 URL。旧数据库与工作流保留在原目录。点击「文件 → WF-02 · 本地工具协作 → 运行」可离线验证，单独启动 LM Studio 后可使用 WF-01。

**源码开发**。集成入口为 demo/studio/frontend/integration.html，复用 Vue 控制层和浅色工作区样式。需要锁文件对应的 npm 依赖、现有 Rust/Cargo 缓存。关闭准备替换的开发窗口后执行：

```powershell
Set-Location D:\AIOrchestrationStudio\demo\studio\frontend
.\node_modules\.bin\vite.cmd build --config vite.integration.config.js
Set-Location D:\AIOrchestrationStudio
& .\apps\aos-workbench\tests\build-desktop.ps1 -Integrated
& .\apps\aos-workbench\start-integrated.ps1
```

apps/aos-workbench 的 npm run dev 仅预览 React 草稿编辑器。用上面的原生窗口验证业务功能。P0-11 为本机开发构建；当前已有的独立发行包是 [v0.1.3 ZIP](dist/AOS-Demo-v0.1.3-win-x64.zip)，完整解压后双击 AOS.exe，界面和数据目录均属于旧版。下面保留 v0.1.2 的历史启动说明。

# 从这里启动 AOS 工作台 0.1.2

这是 Windows x64 桌面 Demo。已有构建使用随包 Python 和已编译的前端。Windows 需要安装 Microsoft Edge WebView2 Runtime。

**本机已有构建**：在 PowerShell 复制以下两行。

```powershell
Set-Location 'D:\AIOrchestrationStudio'
& '.\dist\AOS-Demo-v0.1.2-win-x64\AOS.exe'
```

**从 ZIP 使用**：将 dist/AOS-Demo-v0.1.2-win-x64.zip 整体解压，进入解压目录双击 AOS.exe。保留 app 子目录。首次启动会在 %LOCALAPPDATA%\AOS-Demo\v0.1.2 建立用户副本，请等待窗口显示「C1 已连接」。点击「使用离线示例」再点击顶部「运行」。看到绿色完成状态后，在底部「运行结果」查看文本。点击窗口右上角 × 关闭；有未保存编辑时请先保存。

**从源码构建**：开发机需要本项目 P0-08 已锁定环境与依赖、Node/npm、Rust/Cargo 缓存、MSVC 和 WebView2。前端使用 demo/studio/frontend/package-lock.json 固定的官方 npm 包。开发依赖缺失时，在该目录执行 npm ci --ignore-scripts 后返回项目根目录。当前开发机已执行以下构建命令。

```powershell
Set-Location 'D:\AIOrchestrationStudio'
& '.\experiments\p0-08\.venv\Scripts\python.exe' '.\demo\studio\build.py'
& '.\experiments\p0-08\.venv\Scripts\python.exe' '.\demo\package_studio.py'
```

前端入口是 demo/studio/frontend/src/App.vue。构建脚本复用发行版的 Tauri 宿主、Vue Flow 和配套依赖。0.1.0、0.1.1 用户可在原界面导出文档，再在新工作台导入 JSON。

打不开时先检查是否完整解压、WebView2 是否可用及用户目录能否写入。[使用手册](docs/USER_GUIDE.md) · [故障排查](docs/TROUBLESHOOTING.md)
