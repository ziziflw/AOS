# 0.1.2 工作台组件与真实窗口验收

本轮采用 Vue Code Layout 1.2.5（MIT）作为唯一面板布局，Naive UI 2.45.3（MIT）提供分类树、搜索输入、可添加性筛选和数值参数控件，Vue Flow 1.48.2 继续负责图和端口。运行于 Vue 3.5.44、Tauri 2.12.5 的 Windows WebView2 工作台。入口见 START_HERE.md。精确依赖与 integrity 见 demo/studio/frontend/package-lock.json，发行目录 licenses/npm 和 licenses/native-web-manifest.json 保留声明与分发文件。

首选布局组件以官方 npm 包接入。隔离试验先把 Vue Flow 嵌入 centerArea，创建左右和底部区域。初次运行缺少显式根布局数据而报错，后续发现折叠配置需在组件挂载前恢复。修正后的真实 Tauri 试验记录在 demo/studio/probe-final.txt，截图为 probe.png，之前的失败输出保留。首选方案通过后直接用于正式前端。Dockview Vue 8.8.3（MIT）只核对元数据，本轮没有安装或运行。

## 前端变化

- 原手写活动栏、工作区网格、独立分隔条和面板定位，改由 CodeLayout 的组、面板、编辑区与状态栏槽位管理。右侧「属性」和底部「输出」按钮控制真实的布局配置。布局树和区域尺寸保存在本机 WebView 配置中。
- 节点分类树从后端 catalog 生成，复用 Naive UI 展开、搜索输入和筛选。保留点击添加、用途说明、依赖缺失提示和原 Vue Flow 坐标换算。节点库没有拖入添加入口。
- 顶部保留文档和执行操作。运行区展示 C1 的输出、事件、问题和详细记录。旧侧栏密度开关和独立模型设置弹窗没有重新引入。仍沿用用户工作区列表和原权限检查。
- 修复编辑时文本输入可能被状态轮询覆盖的问题，文本即时写入草稿。执行器仍按启动时固定的版本运行。

## 验收

最终真实窗口记录在 [result.json](../demo/studio/qa-1794060397239/result.json)。其中 13 组实际操作覆盖：新建、搜索、添加、拖动与选中、检查器连接、非法连接、输入焦点、参数修改、快捷键、保存及另存比对、离线 MCP 示例、C1 输出、真实失败、断连诊断等。关闭原生窗口并重新启动，重新打开保存的工作流并验证检查器折叠状态。使用鼠标拖动底部分隔条，断言画布实际高度变化。导入 0.1.1 的 SDK 示例 JSON 后实际执行成功，并展示 C1 的 node-dispatched 事件。截图覆盖 1366×768、1440×900 和 1920×1080。START_HERE.md 的正常发行入口已启动，窗口标题 0.1.2，health 握手成功。

## 限制

本轮实际连线验收走检查器入口。自由跨区域停靠的全部组合、端口拖线、所有历史 JSON 版本、干净 Windows 安装和本地模型真实推理仍待专项验证。草稿切换前应先保存。0.1.2 使用独立用户目录，旧版文档可导出 JSON 后导入。没有更换 C1、审批、MCP、A2A 或模型适配器。后端专项没有按新前端重复计算通过数。

上游资料：[Vue Code Layout](https://github.com/imengyu/vue-code-layout)、[布局 API](https://docs.imengyu.top/vue-code-layout-docs/en/guide/useage.html)、[Naive UI](https://www.naiveui.com/)、[Vue Flow](https://vueflow.dev/examples/)。
