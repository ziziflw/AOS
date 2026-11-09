# AOS Windows x64 离线 Demo

双击 Start-Demo.cmd 启动。请解压到当前用户可写的目录，完整保留目录结构。
默认使用本机合成模型服务，不产生真实模型 Token 或费用。
真实供应商仍禁用；本包没有提供已获授权的 DeepSeek 配置入口。
Vue Flow、Tauri、C1、MCP 和 A2A 复用既有实验实现，A2A 没有新增画布入口。

本包包含 Python 运行时与已安装依赖，不需要安装 Python、Node 或 Rust。
Windows x64 与 Microsoft Edge WebView2 Runtime 是运行前提。
尚未捆绑 WebView2 离线安装程序；无 WebView2 的干净机器暂不满足运行条件。
当前使用既有 debug 宿主，不是签名安装版。

关闭窗口后可重新启动，数据保留在 experiments/p0-08/evidence。
卸载：关闭全部 Demo 窗口，备份需要的 evidence 后删除整个解压目录。
若曾强制终止，先使用包内 Python 运行 experiments/p0-08/cleanup_credentials.py，
清理明确收据关联的合成凭据；勿在实例运行期间清理。

在原开发目录运行 demo/build.ps1 可生成新目录。构建复用本机已验证的
宿主产物、Python 和锁定环境；manifest.json 记录每个发布文件的 SHA256。
这是依赖搬移封装，不宣称位级可复现构建，也不代表干净机器验收通过。
