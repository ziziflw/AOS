# P0-07 交付报告

2026-10-27。已交付可启动的真实 Tauri / Vue Flow 工作台，完成编辑→原契约校验→固定运行→C1→真实合成MCP→实际节点状态/输出闭环。**当前UI按用户要求保留，后续改设定后再完善。**不是正式产品发布，不自动进入下一阶段。

入口：[运行方法](../experiments/p0-07/README.md)、[启动脚本](../experiments/p0-07/launch.ps1)、[验收与截图](./p0-07-workbench-verification.md)、[最小IPC扩展](./p0-07-ipc-extension.md)、[架构发现与下一轮建议](./p0-07-architecture-findings.md)。

## 实际成果

- A · Graphite五区工作台，使用已安装项目级frontend-design Skill和预研规范；节点库/搜索、无限平移缩放、真实端口、类型拒绝、移动、选择、复制/删除、基本撤销/重做、快捷键、面板调整/折叠/密度。
- 10类固定受检节点，包括文本输入/处理、明确标记的合成模型、真实独立MCP Echo/合成写入、类型封装/提取、文本输出。配置来自实际NodeDefinition.configSchema；支持所用string/number/integer/boolean/const/enum，未支持复杂Schema不伪造控件。
- 项目内保存/重载、JSON编辑文档导入/导出；原Workflow Definition保持P0-02格式，布局独立。未知节点/未来扩展草稿可往返并明确不兼容，后端校验失败不能执行。
- 固定run版本，运行期间编辑不改变原定义/批准；真实成功、失败、合作取消、审批等待与断连待核实；重要错误当前视口可见。C1/SQLite仍唯一状态权威，Rust不调度、不写终态。
- 原SDK MCP真正独立stdio调用；模拟模型没有收费调用。A2A本轮GUI无管理入口，原独立A2A回归保留通过。

## 验证结果

[最终12个后端测试方法](../experiments/p0-07/evidence/backend-20261027T145724786217Z/summary.json)全部通过；[真实窗口19个验收步骤](../experiments/p0-07/evidence/gui-20261027T145714748Z/summary.json)全部通过，窗口脚本无console/page错误。19为步骤/尺寸子用例，不能与12测试方法或旧回归混成一个通过数量。

原P0-03/P0-04/P0-05/P0-06分别 **18/14/18/15** 方法回归通过，源码未改，原suite和失败历史保留。最终交付独立读取5个GUI run库，完整性与seq检查通过；正常/批准两份窗口观测整份严格等于SQLite权威记录，包括浮点时间戳。合成写入在批准后仅1次。

[15张实际窗口截图](../experiments/p0-07/evidence/gui-20261027T145714748Z)、[构建/源码身份](../experiments/p0-07/evidence/final-build-identity.json)、[独立核对](../experiments/p0-07/evidence/delivery-audit.json)、[失败索引](../experiments/p0-07/evidence/development-failures.json)可复核。最终进程核查针对记录过的自有PID/Job，未发现存活残留；不扫描或清理别的应用。

首轮连线消失、重载/选中/拖动同步、缺失解释器路径、构建图标、测试ID/模块作用域及JSON数字往返问题均保留失败并修正；没有用打印预期、放宽实际状态比较或删除证据换取通过。

## 仍然有限

只验证Windows开发环境。四种原生窗口尺寸已实际查看；125/150%是WebView缩放，截图有捕获区域裁剪，不能等同实体Windows显示DPI验收。当前UI不继续润色，读屏、精细焦点、库拖放的独立断言、更多分辨率/长文本、批量和大图性能仍需后续专项。

没有真实收费模型/账户、完整A2A可视管理、任意插件/脚本、嵌套子图、自由浮动停靠、完整JSON Schema renderer、生产历史管理、通用重试/暂停、并发多run服务、生产安装包/签名/升级或干净机器发行验证。unknown必须核实，本轮不提供盲目替代运行。原P0-02合同的生产澄清项仍存在，不冻结正式执行引擎技术栈。

新代码、前端依赖、夹具和证据位于`experiments/p0-07`，planning新增四份报告，根/研究导航增量更新；原Schema、旧运行时/IPC/MCP/A2A和研究历史保留。未修改PFT、全局Codex配置，未提权，未下载模型或安装不可信插件，未创建Git提交/标签/推送。

下一阶段建议先以一个受预算授权的模型协议验证真实响应、typed output、usage不可得、超时/取消与可能计费的unknown语义，以及凭据别名/脱敏和Windows依赖闭包。仅提出建议，本轮没有发起这些调用。
