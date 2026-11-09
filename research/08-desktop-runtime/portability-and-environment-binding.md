# 跨环境兼容与环境绑定

P0-02设计目标：Windows x64 → Linux x64 → macOS。**本轮仅在当前Windows做静态校验；Linux/macOS没有运行验证。**

## 三级承诺

| 层级 | 目标 | 验证要求 |
| --- | --- | --- |
| L1定义兼容 | 支持版本的同一JSON可加载、查看、编辑、诊断；未知数据保留 | 各OS实际解析/保存器往返；本轮只测Windows的JSON值往返与结构 |
| L2执行兼容 | 具备相应实现、运行时、服务、凭据、权限时可执行 | Windows与Linux分别跑同一工作流并重绑定；macOS后置 |
| L3完整环境迁移 | 自动装插件、迁凭据、恢复外部服务和全部运行状态 | 首版不承诺；不能由L1/L2推导 |

兼容失败仍应允许查看、检查参数、替换节点、改绑定、另存副本。导入不等于运行批准，不自动下载或安装缺失插件。

## 四类可分发数据

1. **WorkflowDefinition**：便携定义、逻辑资源/服务slot、版本锁和权限需求，不含机器路径/密钥/运行结果。
2. **Catalog描述**：节点/适配器/能力Schema快照及锁；描述可以跨OS阅读，但不是可执行实现。
3. **EnvironmentBinding**：本机mountPath、连接引用、secretRef、程序/环境变量引用、模型选择。可导出不含秘密的模板；每台设备重新填写。
4. **运行与产物**：C1/E1保存，另行授权导出；不会混入workflow形成默认迁移。

已提供[Windows绑定模板](../02-node-contracts/examples/environment.windows.template.json)与[Linux绑定模板](../02-node-contracts/examples/environment.linux.template.json)。二者使用相同serviceSlot和workspace:source；mountPath分别为Windows盘符与Linux目录。这只是声明差异，未创建这些目录或服务。credentials.status均unbound，example.invalid连接不可执行。

运行环境变量仅记录environmentRefs，不存明文值；机密经secretRef注入，非机密由本机profile解释。设备/服务连接用connectionRef；模型供应商配置由target与capability.selector精确匹配。更换模型或API不能被“重新绑凭据”掩盖，必须重新验证/修订。

## 平台能力与预检次序

AdapterDefinition按os/arch声明minRuntime、externalPrograms、协议版本、permissions和headless，执行能力再声明cancel/resume/retrySafety。后端逐项验证，不能相信声明即满足。

1. 安全读取原始JSON，识别schemaVersion；不支持时保留原文件，禁止执行。
2. B1解析锁定catalog、节点/适配器版本、配置和图；未知实现不能执行。
3. E3核实目标OS/架构、运行时/外部程序的可信安装和版本；无头需求单独核对。
4. D检查本地工具服务或远端端点、版本协商、真实Schema/能力与锁的一致性。
5. E2/E3解析凭据引用、文件/网络/程序权限和资源挂载；不在诊断输出秘密。
6. C1固定执行快照，再在每次派发重查授权；预检不是无限有效的grant。

## 诊断格式与处理

候选Diagnostic包含code、severity、phase、workflowRevision、node/port/slot、expected/observed、impact、remedies；observed须脱敏。severity区分阻断error与不确定warning；存在执行所需unknown时也不得放行。建议处理必须由用户明确执行，不能自动替换或安装。

| 诊断 | 影响 | 可选处理 |
| --- | --- | --- |
| NODE_UNRESOLVED / PORT_UNRESOLVED | 保留可看，不能运行 | 安装已核验实现或替换节点并另存修订 |
| 节点/adapter/catalog/capability版本不符 | 禁止静默升级 | 恢复锁版本，或检查差异后迁移副本 |
| PRE_OS_ARCH_UNSUPPORTED | L1仍可用，L2阻断 | 换相同契约的已支持适配器/使用受支持环境 |
| 缺运行时/程序 | 该节点不可派发 | 手动配置可信程序与版本；首版不自动安装 |
| PRE_SERVICE_MISSING / PRE_CONNECTION_UNBOUND | 工具或模型端点未绑定 | 配置connectionRef、服务slot并重新握手 |
| PRE_CREDENTIAL_MISSING | 不发网络请求 | 在本机凭据库配置secretRef，不把Key粘进工作流 |
| 权限不足或审批未决 | 不发生目标操作 | 缩小资源范围、请求批准或取消 |
| PORT_TYPE_MISMATCH / ORDER_AMBIGUOUS | 数据解释不明确 | 显式转换/改接/设置顺序，后端重校验 |
| PRE_RESOURCE_UNBOUND | 文件引用无法解析 | 重绑workspace挂载，检查内容摘要 |
| PRE_RUNTIME_UNVERIFIED | 声明虽一致也尚不能证明可执行 | 完成目标系统探测；不能把静态一致变成支持声明 |

本轮检查器实际实现的是有限声明比对，如OS/arch、服务引用、凭据声明和目标漂移；运行时/程序存在、网络、权限和真实凭据访问全部未探测。Linux profile校验在Windows进程中完成，不是Linux测试。

## 文件引用与迁移

FileReference使用逻辑URI，分辨大小写时保持逻辑标识原样，不套用Windows默认不区分大小写的假设。原生路径分隔符只由E3转换。解析必须拒绝绝对路径、../、编码穿越、挂载逃逸；检查链接/重解析点及文件在检查到读取间的变化。内容缺失/摘要不符时必须报错，不能把同名文件默认为相同数据。

定义迁移：识别旧版本→创建原件保留副本→纯转换产生新修订与差异→校验Schema/图/节点/权限影响→用户接受→重绑环境；不修改旧run的定义。无已知迁移器则只读保留，禁止猜测转换。降级不是“删掉新字段”；要恢复原修订或声明不可逆。节点配置迁移与文件格式迁移独立。

**本轮没有实现产品迁移器或版本回退器。** 负例测试仅证明不支持版本被拒、原始JSON可保留；实际升级与回退列入测试矩阵待运行。

