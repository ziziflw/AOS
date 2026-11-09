# 组件选择与第三方声明

核验日期为 2026-11-08。版本取自本工作区 package-lock.json 和已安装 npm 制品。Node 22.17.1、npm 10.9.2 上执行 `npm ls --depth 0` 成功，12 项直接依赖均可解析。旧 Vue 工作区仍使用自己的锁。

|组件|锁定版本 / 来源|许可|用途及兼容依据|
|---|---|---|---|
|React、React DOM|19.3.0，19.3.0|MIT|本地图编辑器渲染。React DOM peer 要求 React ^19.3.0。[React 构建指南](https://react.dev/learn/build-a-react-app-from-scratch)|
|dockview-react、dockview-core|8.8.3，8.8.3|MIT|本地制品 LICENCE.md 标明 Copyright (c) 2021 mathuo。React peer 包含 19。使用停靠分组、分隔条和布局序列化，企业扩展未引入。[官方介绍](https://dockview.dev/docs/overview/introduction/)|
|@xyflow/react、@xyflow/system|12.12.1，0.0.84|MIT|React Flow peer 要求 React 和 React DOM ≥17。核心库提供节点、边、视口和手柄，保留可见归属标记。[官方 API](https://reactflow.dev/api-reference/react-flow)|
|Radix Dialog、Dropdown Menu|1.1.15，2.1.16|MIT|取自 @radix-ui/react-dialog 与 @radix-ui/react-dropdown-menu，React 19 在 peer 范围内。复用焦点、弹层及菜单键盘行为。[上游实现](https://github.com/radix-ui/primitives)|
|lucide-react|0.468.0|ISC，含 Feather 的 MIT 归属|采用制品 LICENSE 中的完整版权声明。[上游许可](https://github.com/lucide-icons/lucide/blob/main/LICENSE)|
|Vite、@vitejs/plugin-react|7.3.1，5.1.1|MIT|插件接受 Vite 7；Node ^20.19.0 或 ≥22.12.0。浏览器预览绑定回环地址。[官方指南](https://vite.dev/guide/)|
|TypeScript、React 类型声明|5.9.3；@types/react 与 @types/react-dom 均为 19.3.0|Apache-2.0；类型声明 MIT|strict 类型检查，编译器及类型仅用于开发。[TypeScript 上游](https://github.com/microsoft/TypeScript)|
|shadcn/ui Kbd 源码|8ab27715521cbd4f87ae6886cd989cbb678f6de7|MIT|src/ui/Kbd.tsx 保留 kbd 语义，改用工作台 CSS。版权声明在 docs/licenses/shadcn-ui.txt。升级时比对此提交并保留本地样式差异。[固定源码](https://github.com/shadcn-ui/ui/blob/8ab27715521cbd4f87ae6886cd989cbb678f6de7/apps/v4/registry/new-york-v4/ui/kbd.tsx) · [固定许可](https://github.com/shadcn-ui/ui/blob/8ab27715521cbd4f87ae6886cd989cbb678f6de7/LICENSE.md)|

## 依赖范围与复现

锁文件中共有 183 个有版本的包条目（含可选平台包）。70 个生产范围条目的 license 字段为 MIT 59、ISC 9、BSD-3-Clause 1、0BSD 1。113 个开发范围条目为 MIT 104、Apache-2.0 2、CC-BY-4.0 1、ISC 5、BSD-3-Clause 1。CC-BY-4.0 条目为构建工具使用的 caniuse-lite 数据。以上是锁文件条目统计，实际浏览器 bundle 会经 tree-shaking 裁剪。

所有 npm 条目都有 integrity，下载来源为 registry.npmjs.org。复现采用 `npm ci --ignore-scripts`；锁中标有安装脚本的 esbuild、fsevents 分属构建工具和可选平台依赖。Windows 实测以本工作区验收记录为准，跨平台构建、最新安全公告与生产再发行审查仍需单独核验。发行时应携带实际打包依赖的许可证，以及本地改编 Kbd 的声明。

视觉细节采用工作区 CSS 变量，与 Dockview/React Flow 的控件状态对齐。Tailwind CSS 为 MIT，shadcn/ui 有 React 19 与 Tailwind v4 的官方配方；本切片只使用上表中的源码片段及 Radix 原语，无需安装 Tailwind 编译插件或运行 shadcn CLI。Tauri 2 沿用既有宿主，其权限与安全配置独立于这一 npm 工作区。[shadcn/ui 配方](https://ui.shadcn.com/docs/tailwind-v4) · [Tailwind 许可](https://github.com/tailwindlabs/tailwindcss/blob/main/LICENSE) · [Tauri 权限](https://v2.tauri.app/security/capabilities/)
