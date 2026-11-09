# 既有桌面工作台源码核对

核对日期为 2026-11-08。以下版本来自仓库内实际清单和锁文件；界面实测记录另见本目录的验收证据。

## 工程与版本

工程根目录为 `D:\AIOrchestrationStudio`。在根目录执行 `git rev-parse --show-toplevel` 和 `git status --short --branch` 均得到 `not a git repository`。因此分支、HEAD、基于 Git 的变更对照均不可用。新工作台有自己的目录、依赖树和锁文件。

|环节|核对结果|源码依据（相对工程根目录）|
|---|---|---|
|旧桌面前端|Vue 3.5.44，Vue Flow core 1.48.2 / background 1.3.2，Naive UI 2.45.3，vue-code-layout 1.2.5|demo/studio/frontend/package.json、package-lock.json|
|旧前端构建|npm、Vite 7.3.1、plugin-vue 6.0.4、TypeScript 5.9.3。应用挂载到 #app，默认编译到旧宿主 ui 目录|demo/studio/frontend/src/main.js、vite.config.js|
|窗口与打包|Tauri 锁定 2.12.5。host-window 启用 window feature，主窗口由 Rust setup 创建；frontendDist 为 ui。build.py 复制对应实验宿主、构建 Vue、运行离线 Cargo 构建并复制可执行文件|demo/studio/host/Cargo.lock、tauri.conf.json、src/window.rs；demo/studio/build.py|
|桌面命令|本地主窗口获准使用 host_request 和 window_report。Rust 核查窗口标签、消息大小，业务命令仍由原宿主与执行器处理|demo/studio/host/src/window.rs、src/lib.rs、capabilities/probe.json|
|定义与画布|P0-02 schemaVersion 0.1.0-draft.1。Vue 把节点 typeId / typeVersion / config、边两端的节点和端口写入 workflow；另存布局版本 aos-layout/0.1 与位置|research/02-node-contracts/schemas/contract.schema.json；demo/studio/frontend/src/App.vue 中 definition、document、applyDoc|
|运行与事件|旧版启动时请求 host.start 和 health。执行前通过 load/validate 取得 token，再调用 create。轮询 status、approvals 与 events(after)，按 runId 和递增 seq 接受结果|demo/studio/frontend/src/App.vue 中 api、run、poll、onMounted|
|模型与数据|本地模型使用原适配器；C1 负责唯一运行终态，SQLite 保存运行记录。实验 profile 与桌面目录有各自的节点集合|demo/local_models.py、experiments/p0-03/runtime.py、store.py、experiments/p0-08/model_runtime.py|

## 原生验证条件

旧发行窗口会加载编译入程序的静态资源。其启动参数是执行器根目录、会话目录和可选的 test 标志。test 打开回环调试端口。直接打开旧 exe 无法据此验证这次制作的页面。可在独立测试夹具使用原宿主源码、自有临时 session 和新前端静态资源；实际采取的窗口类型与测得的行为，以验收证据为准。调试端口只用于验收。
