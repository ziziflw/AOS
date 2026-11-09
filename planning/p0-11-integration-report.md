# P0-11 Windows 集成验收

## 交付与边界

2026-11-09。已有两个前端入口：原 Vue/Vue Flow 工作台接入 C1，浅色 React/React Flow 预览仅持有演示草稿。P0-11 沿用浅色工作区布局，把已有 Vue 控制器、节点定义和 IPC 动作直接交给集成视图。原 React 预览仍可单独启动。[集成视图](../demo/studio/frontend/src/integration/Workbench.vue) · [共享控制器](../demo/studio/frontend/src/App.vue)

开发测试宿主为 apps/aos-workbench/.desktop-preview/AOS-Integrated.exe，最终 SHA256 为 1CB5AFEC4195C7B61FB8BA15D43FC3B5BC703E88845AE90615211F1EE00A354D。已按启动指南用 PowerShell 及双击入口对应的 CMD 命令启动。正常启动日志记录 host.start、health 成功；空会话首次 recover 返回 RUN_NOT_FOUND 属正常情况。P0-11 私有工作区从现有 v0.1.3 文件初始化，只复用回环模型配置。未生成新的便携 ZIP 或安装程序。用户工作区和下述自动化合成会话分开。[启动方法](../START_HERE.md)

**实际调用链**：Vue Flow 画布与属性 → Vue 控制器 → Tauri host_request → Rust 角色/帧/进程管理 → Python C1 受检工作流与固定运行 → 本机模型 SDK 或 MCP stdio → C1/SQLite 事务 → status、events、approvals → 画布或运行面板。画布位置和编辑历史是用户草稿；固定后的业务状态及终态只有 C1 写入。[Rust 入口](../demo/studio/host/src/window.rs) · [原生契约与布局示例](../examples/workflows/README.md)

## 用户操作与接口

|操作|接口与数据来源|实际观察|
|---|---|---|
|启动或重启|host.start → health → recover；有运行时加载 run-definition|真实窗口启动 Python 并获得目录；恢复后原 runId、输出及 attempt 保持。最终原生窗口完整高度恢复已完成的 Gemma 运行。[截图与状态](../experiments/p0-11/evidence/replay-1794225512838/restored.png)|
|新建及添加|从原生定义建立文本输入和输出；目录、defaults、描述来自 health|界面新建、校验，再用真实目录添加三种节点。[记录](../experiments/p0-11/evidence/edit-1794201132434/checks.json)|
|编辑及连线|NodeDefinition.configSchema 生成字段；端口来自 catalog；执行前 load/validate|编辑 value，连成文本→模型→输出；前端拒绝自环及 Text→MCPArgs，后端独立拒绝不存在的端口。|
|保存和打开|load/save、list-documents、open；原生 workflow 与独立 layout|重开后完整文档相等。导入未知节点后，版本、配置、坐标和连线保留，运行前报 NODE_UNRESOLVED。[验收记录](../experiments/p0-11/evidence/portability-1794201236758/checks.json)|
|模型连接|local-settings、local-list、local-save；官方 SDK 请求受限回环地址|启动已安装的 LM Studio，加载已有 Gemma；测试连接、从 API 列表选择 google/gemma-4-e4b 并保存。缺模型的夹具仍能打开模板，显示 LOCAL_MODEL_UNAVAILABLE，未创建运行。[环境检查](../experiments/p0-11/evidence/environment-1794201578855/checks.json)|
|执行及输出|load/validate 获得固定 token，再 create；status/result 来自 C1|真实 Gemma 返回 AX-17。服务端生成正文、C1 result、SQLite 快照和 UI 输出相同。[服务记录](../experiments/p0-11/evidence/lmstudio-text.jsonl) · [窗口/数据库证据](../experiments/p0-11/evidence/edit-1794201132434/gemma-text.json)|
|运行状态及事件|按 runId、seq 查询；界面仅投影 C1；保留最近 500 条界面事件|在 WF-02 实测中，显示的序列号无重复且覆盖该次 run 的完整序列；未对超长事件流做压测。|
|审批及取消|approvals → approve，C1 检查 ID、决定、指纹、有效期；cancel 经宿主发送|WF-03 未批准时工具 0 attempt，错误指纹无效。关闭并重启仍待批；批准后恰有一次真实 tools/call。独立取消运行没有工具派发。[MCP 账本摘录](../experiments/p0-11/evidence/WF-03-1794201245104/mcp.json) · [取消快照](../experiments/p0-11/evidence/faults-1794201187889/cancel.json)|
|草稿与 Run 隔离|create 固定 workflow；运行修订匹配时才把状态显示到节点|审批暂停时修改原始文本，run-definition 保留旧输入。新草稿不继承原运行节点状态。|
|错误与断连|运行面板展示后端诊断；SDK 区分模型发现与已发送生成请求|隔离连接指向无服务的回环端口，发现阶段报 LOCAL_SERVICE_UNAVAILABLE_BEFORE_REQUEST；C1 与 UI 均显示失败，生成用量为 0。[故障快照](../experiments/p0-11/evidence/faults-1794201187889/disconnect.json)|

## 三个标准示例

- **WF-01** 一次真实生成提取两项分工。小林整理测试清单，期限“周五前”；小陈更新安装说明，期限 null。JSON 节点通过、审批后输出。LM Studio 报告 85 输入、36 输出 Token。服务端记录只出现一对 prediction.input/output。[原始服务记录](../experiments/p0-11/evidence/lmstudio-extract.jsonl) · [验收快照](../experiments/p0-11/evidence/WF-01-1794200917789/WF-01.json)
- **WF-02** 确定性处理调用一次 echo_text，输出“核对模拟订单 A-17 / 已整理”，无模型生成。[协议记录](../experiments/p0-11/evidence/portability-1794201236758/mcp.json)
- **WF-03** 确定性建议经批准后调用一次 simulated_effect，产物为实验账本中的受控操作，输出“核对模拟订单 A-17 / 建议登记核查”，无模型生成。[运行记录](../experiments/p0-11/evidence/WF-03-1794201245104/WF-03.json)

专项验收跨开发构建累计三次真实推理：编辑链路修复前后各一次，WF-01 一次。最终文本链路用量 23/5 Token。在修正全高画布后通过旧运行重开验收，没有为了截图重新生成。恢复与故障验证使用隔离工作区。证据中早期采集的截图可能显示修正前的画布高度；最终布局见上方恢复截图。

## 缺陷与修复

1. 浅色预览的保存写浏览器存储，执行链未接通。集成窗口复用已有 Vue 控制器，调用 C1 的原生文档接口，与预览演示草稿独立。保存布局与定义一并做重开对比；保留当前端口版本和未识别节点。
2. 已启动运行和草稿复用节点 ID 时可能显示旧节点状态。现在只对同一工作流、同一修订显示节点状态，运行面板显示固定 runId。create 增加准入检查，保持一次操作只有一条运行请求，前端检查返回请求关联 ID。
3. 正常启动一度在固定 5 秒就绪期限内失败，空 stderr、宿主回收了所属进程。已将正常启动期限调整到 20 秒，故障模式仍使用原期限。没有更改角色、Job Object 或审批权限。这里验证了修复后的正常启动；没有把一次观测换算成全机器成功率。
4. 模型列表 GET 失败原来被归为“生成响应可能丢失”。现在已知未派发生成时为 failed、0 Token；生成发出后无法核实仍走原 unknown 逻辑。旧运行不重写。对照[修复前](../experiments/p0-11/evidence/faults-1794200831337/disconnect.json)与[修复后](../experiments/p0-11/evidence/faults-1794201187889/disconnect.json)。
5. 实机截图揭示复用样式时 Vue 根节点高度未填满窗口，已补足根元素高度并重测。保留测试初稿的失败记录：重启调试端口尚未释放、按钮定位重名、恢复前过早读取 UI、断连断言读取到上一个已取消运行。最终断言等待目标条件，逐项对照真实 SQLite 快照。

6. 经截图核实，以前自建运行重启时套用示例坐标，三个节点重叠。现在在 create 成功后缓存该次运行的布局，仅按 runId、工作流 ID 和修订精确匹配。无对应缓存的旧运行自动排列；C1 仍提供实际节点、连线和输出。WF-03 经过进程重启，六个节点坐标逐一相等，恢复无需模型推理。[坐标证据](../experiments/p0-11/evidence/WF-03-1794225499632/recovered-layout.json)

## 回归与复现

PowerShell 在项目根目录执行。prepare-tests.ps1 创建 P0-11 专用测试环境；faults 仅短暂改动该副本里的回环连接。LM Studio 模型实验需要先启动已安装的本机模型。每次运行脚本生成新的 evidence 子目录，保留失败和截图。

```powershell
& .\experiments\p0-11\prepare-tests.ps1
node .\experiments\p0-11\acceptance.cjs edit
node .\experiments\p0-11\acceptance.cjs templates
node .\experiments\p0-11\acceptance.cjs faults
node .\experiments\p0-11\acceptance.cjs portability
node .\experiments\p0-11\acceptance.cjs environment
```

GUI 自动化复用现有 Playwright（也可通过 AOS_PLAYWRIGHT 指定本地模块），调试端口 9238 仅用于测试。正常入口不传 test 标志。A2A 没有本轮 GUI 入口，已单独执行 P0-05 test_T04_real_disconnect_requery_same_task，独立合成 Agent 断连后按原任务核实成功；证据目录 experiments/p0-05/evidence/p011-1794200693914812100。

## 剩余限制

浏览器中的 React 演示草稿不会自动转换成可执行契约，旧版工作区也不会自动迁入；原生组合文档可手动导入。P0-11 支持当前可信目录及回环模型绑定，未开放任意插件或云端账号。真实 A2A GUI、LT01 专用目录注册、跨平台及干净机安装验收均在本轮范围外。本轮仅生成获准的本地测试宿主，发行包版本仍为 v0.1.3。

