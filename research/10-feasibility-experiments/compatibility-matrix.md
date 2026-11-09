# 兼容性测试矩阵 · P0-02

日期2026-10-24。D=设计论证；S=结构/嵌入Schema检查；G=有限声明语义检查；R=真实运行待验证；T=目标系统真实执行结果。**S/G不提升为R通过；当前没有任何T执行通过项。**

可复核证据：[117项离线结果](./validation/static-check-results.json)、[检查范围与复现](./validation/README.md)。所有Linux profile检查实际运行在Windows，不能标成Linux加载成功。

| ID | 验证事项 | D设计 | 本轮S/G及证据ID | R真实验收与失败 | T实际目标结果 |
| --- | --- | --- | --- | --- | --- |
| C01 | Windows本地定义加载 | 已论证严格/保留两模式 | S：schema.document.*；Windows现有工具可解析 | E01需真实编辑器加载/保存，丢ID/字段失败 | 仅Windows静态；无应用实测 |
| C02 | Linux定义加载 | L1必须目标 | S：Linux绑定模板结构合法；不是Linux加载 | Linux x64独立校验/保存同一图，比较JSON值；路径误解析失败 | Linux待测 |
| C03 | 不兼容节点可见诊断 | 定义/版本/环境分层 | G：negative.semantic.node-version、preflight.macos-adapter-block | A1展示节点/影响/处理选项，静默删节点失败 | UI与目标OS待测 |
| C04 | 未知节点无损保存 | 保留JSON树，执行阻断 | S未知节点外壳通过；G：preservation.unknown-node-json-value、negative.unknown-node-execution-block | 实际产品保存器保留config/边/extensions，错误执行失败 | 仅Python值级往返 |
| C05 | 节点/适配器版本变化 | 精确锁，不能静默采用latest | G：negative.semantic.node-version、adapter-catalog-change、preflight.target-change | 安装升级后旧图阻断或原实现继续，静默换模型/权限失败 | 实际升级待测 |
| C06 | 模型供应商参数差异 | 精确selector+Schema | S：negative.provider-a-temperature、positive.provider-b-temperature、negative.provider-b-range | E02两家真实端点/版本验证，不静默丢参；费用按预算 | 真实供应商待测 |
| C07 | MCP协议/工具Schema差异 | 固定协议候选与描述快照 | S：negative.tool-args-required、negative.tool-output-type；无MCP握手 | E03旧/新协议、tool变化、输出不合Schema；误读structuredContent失败 | MCP待测 |
| C08 | 跨OS文件引用重新绑定 | 逻辑URI+本地mount | S：negative.file-absolute-path；G：uri.path-traversal/encoded-traversal与portable.* | Windows/Linux读取同一摘要资源、大小写/链接/路径边界；误读同名文件失败 | 文件真实重绑定待测 |
| C09 | 缺凭据阻止执行 | E2/E3后端校验 | G：preflight.windows/linux.*、credentials-configured-not-proof | 凭据不可用时目标请求数0；仅写configured即放行失败 | 真实凭据与零调用待测 |
| C10 | 有副作用禁止盲重试 | unknown不当作未发生 | G：negative.semantic.write-blind-retry；Schema约束never只能1次 | E05发出后崩溃，幂等/查询/人工核对；无证据重发失败 | 真副作用/幂等待测 |
| C11 | 定义升级和回退 | 显式迁移副本与差异 | S拒未来schemaVersion；G保留未知核心JSON值；**未实现迁移器** | 双版本迁移/拒绝、保原修订、回退及权限变化；删字段降级失败 | 迁移/回退待测 |
| C12 | 参数修改影响范围 | 新修订与后继闭包 | G：impact.model-a期望join/review/package/output，不含modelB | E05实际缓存/子图/副作用失效；复用陈旧输出失败 | 执行缓存待测 |
| C13 | 条件/汇合/有界子图 | 数据与控制分离、互斥merge | G：cycle、control-data、join-order、missing-subgraph；S：zero-loop-limit | E04跳过传播、反序完成、2轮耗尽、重复事件；死等/超轮失败 | 调度待测 |
| C14 | Agent取消/恢复/审批 | 远端状态事实与本地权威分开 | S/G只覆盖图、版本及政策形状 | 场景C/GetTask重连、取消确认、审批篡改；发送取消即报停止失败 | A2A/E05/E06待测 |
| C15 | 模块依赖与状态唯一性 | 保持10职责，端口注入解耦 | G：architecture.proposed-import-dag及cycle-negative-control | 后续框架检查点/本地状态故障对照，双调度/双写权威失败 | 无应用源码可实测 |
| C16 | 输出类型/版本/秘密字段 | Envelope与payload分离，已知秘密字段禁用 | S：output.*、envelope、negative.output-structured-type；G：negative.secret-field-extension | 实际导出脱敏、有效终值与陈旧结果，文本藏秘密仍需额外治理 | 脱敏/运行来源待测 |

## 后续运行环境矩阵

| 层级 | Windows x64 | Linux x64 | macOS |
| --- | --- | --- | --- |
| L1 JSON/编辑器 | 本轮现有Windows工具静态部分通过；编辑器待测 | 全部待目标环境实测 | 后置，未选具体架构 |
| L2模型/MCP/Agent执行 | 后续E02/E03/C/E05 | Windows闭环后以同一可移植图重绑定验证 | 后置 |
| L3安装/凭据/全状态迁移 | 不承诺 | 不承诺 | 不承诺 |

环境最低OS版本、具体运行时/程序/SDK依赖在实验开始前记录；测试先无副作用模拟服务，再进入用户授权的真实接口。E01–E07原实验均未整体完成；本轮只提前完成部分静态契约子检查。

