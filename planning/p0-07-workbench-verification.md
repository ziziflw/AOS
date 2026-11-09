# P0-07 可视化工作台验收

2026-10-27，Windows 11 x64，Tauri 2.12.5 / WebView2 155.0.4283.62，Vue 3.5.44 / Vue Flow 1.48.2；Python 3.12.14、SQLite 3.53.1，复用原 P0-06 venv。当前 A · Graphite Workbench 外观按用户最新指示保留，不继续润色。

## 已通过实际执行

最终 [后端12测试方法](../experiments/p0-07/evidence/backend-20261027T145724786217Z/summary.json)，0失败/0错误。其中11方法通过真实 Rust 探针/私有长度帧访问执行器；T11 的4105次读取是 Python endpoint 直接调用原 C1 快照的专项，不算4105次 GUI 或 Rust IPC。

| 方法 | 输入 / 注入 | 真实断言 |
| --- | --- | --- |
| T01 | 编辑默认原格式图的文本 | 七节点成功，原输出字符串匹配；固定 workflow digest；独立 MCP ledger；IPC 整份快照与 SQLite 严格相等（含数字） |
| T02 | Text 接 MCPArgs JSON、温度4、节点版本9 | 原 Contracts 分别拒绝类型、config、版本 |
| T03 | future.unknown + 未来扩展、`../outside`、executable附加字段 | 未知草稿原样保存/加载，执行拒绝；路径与额外命令字段拒绝 |
| T04 | 合成写 MCP，旧指纹、重复批准 | 未批准无 MCP 子进程/attempt；旧批准拒绝；批准后真调用，仅1个effect-committed |
| T05 | 900ms模型在途时提交变更草稿 | 原run仍旧digest；下一新run有不同runId和新digest |
| T06 | fail=true，另一次delayMs=4000后取消 | 模型真实失败、下游跳过；合作取消后下游cancelled |
| T07 | pending审批时suspend/重启/recover | 同run/审批内容、仍pending，无自动批准 |
| T08 | 重复create ID、第二宿主恢复同库 | 原ACK返回同run；第二控制者CONTROLLER_ALREADY_OWNED |
| T09 | viewer启动、超长请求 | 后端权限拒绝；超长帧保留空响应id并断开，不误配正常请求 |
| T10 | 改动合成run里的profile摘要 | 恢复HOST_PROFILE_DRIFT；原pending/runId仍在 |
| T11 | 4105次只读查询，之后写ID内容冲突 | 无C1写入、内存只读窗口有界、写身份仍检查 |
| T12 | 模型实际running时结束自有执行器 | 同run恢复unknown；禁止未经核实直接替代创建 |

输入定义、完整真实响应、断言和失败状态均在对应方法的独立目录；每个run的 `workflow.json/request.json/environment.json/profile.json/run.sqlite` 可复核。故障只作用于自己的合成进程/账本，不运行破坏性文件操作。

## 真实窗口交互

最终 [GUI摘要](../experiments/p0-07/evidence/gui-20261027T145714748Z/summary.json)、[逐步结果](../experiments/p0-07/evidence/gui-20261027T145714748Z/checks.json)、[窗口身份](../experiments/p0-07/evidence/gui-20261027T145714748Z/identity.json)。这是 actual `http://tauri.localhost/` WebView2、真实 Tauri invoke、Rust 和 Python C1；没有创建浏览器替代工作台或通过前端计时器生成运行态。

共19个验收步骤：基本12组中另包含拖拽、未知节点、四种窗口尺寸和两种WebView缩放子步骤，**不等同19个独立单元测试，也不与12个后端方法相加制造总通过数**。

| 用户验收要求 | 证据 |
| --- | --- |
| 添加/删除/复制/撤销/重做/移动/连接 | G02、G02b：实际键鼠，校核24px拖动位移容差；删除原边后从真实端口拖连，边数5→6 |
| 非法连接拒绝 | G05：Text→MCPArgs_echo_text被拒，仍6边；错误截图 |
| 属性配置、保存、重开结构一致 | G03：Schema控件编辑文本，保存/重载仍相同；G04b未知节点与全部workflow深比较保留 |
| 后端同定义校验 | G04，以及桥中load/validate原定义和token |
| 真运行、实际节点状态及输出 | G06：七节点完成，与实际status一致；输出包含编辑文本；独立SQL再次整份比对 |
| 失败、取消 | G07/G08：真实C1失败/取消、下游受控，截图保留 |
| 运行期间编辑不改已固定版本 | G08：修改草稿前后原identity.workflow/revision相同 |
| 后端人工审批 | G09：pending时attempt=0，点击有效批准后实际MCP合成效果完成；独立账本1次 |
| IPC故障不虚假成功 | G12：真实结束自有worker，顶部“连接中断·待核实”，留最后快照；不把本机退出写成业务失败/取消 |
| 多分辨率、布局 | G10：真实原生窗口1440×900、1366×768、1920×1080、1024×768；G11面板键盘调整/折叠 |
| 缩放 | G11b：真实WebView1.25/1.5，记录CSS视口、DPR、overflow；不是实体Windows显示DPI通过 |
| 回归 | 原18/14/18/15方法分别通过，见下表 |

默认图与审批图都是原格式合成图。模型仅本地模拟；MCP是官方SDK独立服务；A2A在本轮GUI没有入口，不能把旧A2A回归算作GUI功能。

## 截图审查与当前限制

最终15张截图包含[成功](../experiments/p0-07/evidence/gui-20261027T145714748Z/success.png)、[审批](../experiments/p0-07/evidence/gui-20261027T145714748Z/approval.png)、[失败](../experiments/p0-07/evidence/gui-20261027T145714748Z/failure.png)、[取消](../experiments/p0-07/evidence/gui-20261027T145714748Z/cancelled.png)、[断连](../experiments/p0-07/evidence/gui-20261027T145714748Z/ipc-disconnected.png)、四分辨率与缩放。代码构建后实际查看过截图，首轮错误也保留。

观察到初始既有边被校验错误移除、重载后节点不可见/选择不同步、复制视图模型使拖动累积偏移；先后修正为区分既有边、重测尺寸、直接采用Vue Flow标准v-model管理几何/选中，业务语义和C1投影独立。不是只凭CSS编译通过。

1024窄窗口原先全图缩至42%，可读性不足，改为收起辅助面板；当前可重新展开，完整任意停靠未做。125/150% WebView缩放截图工具出现捕获区域裁剪，保留图和视口数据，**不据此宣布高DPI视觉验收完成**。没有改系统显示缩放或用户全局设置。当前UI依用户指示保留，完整视觉/读屏/实体高DPI/长文本和性能优化留待后续设定。

## 原实验回归

| 阶段 | 独立suite | 结果 |
| --- | --- | --- |
| P0-03 | [20261027T142709376924Z](../experiments/p0-03/evidence/suite-20261027T142709376924Z/summary.json) | 18方法，0失败/错误 |
| P0-04 | [20261027T142709838375Z](../experiments/p0-04/evidence/suite-20261027T142709838375Z/summary.json) | 14方法，0失败/错误，真实SDK MCP |
| P0-05 | [20261027T142709735637Z](../experiments/p0-05/evidence/suite-20261027T142709735637Z/summary.json) | 18方法，0失败/错误，真实SDK A2A合成服务 |
| P0-06 | [20261027T142709373492Z](../experiments/p0-06/evidence/suite-20261027T142709373492Z/summary.json) | 15方法，0失败/错误/跳过，含原真实Tauri窗口 |

原实现未改。后续修正只在P0-07目录，最终本轮后端/GUI已复测。不是跨平台、任意第三方协议或生产发行验收。

## 独立证据与失败保留

[交付核对](../experiments/p0-07/evidence/delivery-audit.json)读取最终5个run SQLite：integrity_check=ok、snapshot.seq=事件max序号；正常/批准两份窗口观测整份严格等于独立SQL快照。观察进程退出/Job清空只针对记录过的自有PID/Job，不扫描或结束其他应用。

[失败索引](../experiments/p0-07/evidence/development-failures.json)保留初始Schema拒绝、缺失本轮Python路径、图形同步失败、构建缺图标、测试关联ID/模块作用域错误、数字精度初次核对失败。最终通过不覆盖这些记录。源码与二进制摘要见[构建身份](../experiments/p0-07/evidence/final-build-identity.json)；摘要是测试后捕获，最终GUI之后没有重建该二进制/前端资产。

进程审计另发现一个历史PID已被其他程序复用。只读查询确认当前映像为Google Updater，与本轮Python/宿主不同；没有结束该进程。首次PID审计与核实记录保留在`audit-pid-reuse-first.json` / `pid-reuse-observation.json`，最终按映像身份保守判断，并结合自有Job活动数为0。PID数/核查次数不是新增通过测试。
