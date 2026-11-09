# P0-07 架构发现

2026-10-27。本轮证明图编辑器可以接入原有执行体系，不代表正式产品架构已冻结。采用项目级 `$frontend-design` 原文与已选 A 规范，用户现要求保留当前UI，后续设定后再完善。

## F01 原契约可以直接驱动编辑和执行

UI语义保存的是原 Workflow Definition，没有独立的不可执行UI方言。Vue Flow只管理几何/选中/连线投影，布局版本单独保存；新增的builtin模型/类型转换仍用原NodeDefinition、configSchema、typed ports和catalogLock格式。原Schema不改，resourceRef固定常量`catalog:core`也未为方便实现而放宽。

直接把Text连进MCP工具是可复现的不兼容反例：MCPArgs_echo_text是JSON对象`{text}`，不是字符串。采用明确的封装/提取节点，原Contracts检查schemaRef一致；不能把端口颜色或所有值转字符串当类型系统。合成模型输出Text，本轮不冒称真实模型标准输出/usage。

未知节点可在缺描述时以既有边推导只读可视端口占位，原配置、版本、边和扩展保留；占位端口不能产生新的执行连接，后端拒绝运行。保存成功只是草稿可往返，不能混成执行通过。

## F02 调度和审批没有移到前端或Rust

P0-03原C1/SQLite仍唯一写run/node/attempt/iteration/approval。P0-07继承P0-06端点、P0-04 Registry/BoundRuntime，新增受限profile和少量builtin handler，不复制Runtime.drive。Rust沿用Job/帧/权限入口，不打开业务库。P0-05 A2A没有迁移进画布；独立回归继续通过。

审批摘要来自C1固定spec与真实依赖输入，重新算指纹，前端只提交id/fingerprint/decision。Rust固定approver角色、C1状态/TTL/取消门禁、MCP wire边界复核同时保留。没有通用pause/resume/任意重试按钮，也没有因按钮禁用就宣称安全。

## F03 原单run探针必须最小扩展

P0-06 builtin选择不能驱动编辑后的任意图。本轮增加受检草稿、摘要token、每run独立目录、顺序新建、固定文档名保存与已绑定定义查询。运行中可验证新草稿，但不能替换旧C1合同；unknown禁止盲目替代创建。窗口重启查询原run，pending不自动批准，代码profile漂移失败关闭。

未实现生产多工作流服务、并发多run仲裁、编辑器CAS/命令跨库事务。仍有prototype级限制：create与receipt不跨库原子；主文档与两个导出不是多文件事务；profile持久化初始创建窗口遇崩溃会明确失败，需要核实。不能靠“多run目录”宣称完成正式引擎API。

## F04 复制图形内部状态会制造交互缺陷

最初从Vue Flow节点复制内部几何/初始化标志，再把其当受控输入，导致重载不可见、选中和检查器不同步、拖动累积偏移。改用标准v-model保留同一几何/选中模型，节点渲染从独立原语义定义和C1 snapshot读取；真实键鼠测试校核位移。这里的单一视图来源与C1业务状态权威是不同层面的约束。

当前App.vue仍偏集中，适合实验；后续可分离编辑命令栈、文档服务、Schema renderer和只读run投影，但不能再创建一个业务状态机。所有视图计时仅用于轮询/布局测量，没有凭动画推演节点终态。

## F05 跨语言数字往返也需独立核查

原型宿主默认JSON解析在少量时间戳上出现约0.24μs漂移：旧IPC值`1793112274.7612965`对原SQLite值`1793112274.7612963`。终态与seq一致仍不足以宣称整份记录一致。保留首次失败审核并在本轮宿主启用`serde_json/float_roundtrip`；最终严格比较成功，没有靠四舍五入、时间容差或修改权威记录过关。

依据：[serde_json实际feature定义](https://docs.rs/crate/serde_json/1.0.154/features)。本轮未验证任意大整数、Decimal或跨Schema所有数字域，未来真实模型usage/计费/时间仍需明确数值编码和范围。原P0-06源码没改；如将来合并宿主应通过正式变更同步该修正。

## F06 Python继续可用，发行与API仍未定案

Python继续复用已经验证的调度/恢复和官方SDK，避免Rust/TS重写再引入一套故障语义。代价是独立运行时、SDK依赖闭包、IPC故障、数据数值和版本耦合。Rust管理系统能力有效，但普通进程/Job不是OS沙箱。

新前端使用Vue3/Vue Flow，Vite构建；没有生产安装包、签名、升级、干净Windows部署、ARM64或Linux/macOS运行证据。NPM安装禁用生命周期脚本并锁integrity；依赖许可副本仅支持审查，不等同已完成发行法律合规。原P0-06 Python体积数据仍只代表开发机，不能把前端bundle大小当完整发行体积。

Vue Flow布局与原合同能对接，有依据继续小范围工作；仍不冻结Python为产品引擎。P0-02 required输出激活、完整派发上下文、policy作用域、背压、持久化fail-stop的生产收敛仍待后续决策，本轮不大改正式模块边界。

## 下一次真实模型接入的最小条件

建议先选择一个模型协议、一个Text输入/结构化输出的受控任务，明确provider能力与节点版本；凭据仅宿主配置别名，不进入便携定义/日志；由用户明确授权费用与预算，区分调用前批准、超时、结果未知和可能已计费。实际usage不可得时显示unknown，不假定价格/进度。保留本轮画布→固定定义→C1路径，先做真实响应/usage/取消计费与断连核实的专项，再考虑多模型或A2A可视管理。

这是建议，尚未调用任何收费模型或连接账户。本轮完成后停止。

## 实现参考与验证层级

前端API参考[Vue官方Quick Start](https://vuejs.org/guide/quick-start.html)、[Vue Flow官方指南](https://vueflow.dev/guide/)与[Handles](https://vueflow.dev/guide/handle.html)；宿主配置参考[Tauri官方配置](https://v2.tauri.app/reference/config/)，真实WebView调试入口参考[Microsoft WebView2文档](https://learn.microsoft.com/en-us/microsoft-edge/webview2/how-to/debug-visual-studio-code)。版本依据本轮lock/实际构建；这些文档仅是实现依据，不代替本轮实际窗口/SDK/SQLite证据。

模型边界补充：`p07.model`明确定义为合成文本builtin，沿用原NodeDefinition/端口/configSchema格式；它没有真实Model适配器或计费能力。当前“最大输出”单位是合成字符，temperature不参与推理。不能将其当作原`model.generate`适配/真实模型已验证的证据；后续真实模型必须实现原model类别、AdapterDefinition、环境和预算/授权边界。
