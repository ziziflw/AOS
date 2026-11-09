# P0-06 架构发现与技术栈评估

2026-10-27。基于[15项专项](./p0-06-host-verification.md)及18/14/18独立回归，建议继续复用Python实验器与Rust系统宿主；**不冻结正式执行核心**。P0-01–P0-05研究/源码保留，正式模块职责未改。

## F01：现有契约能驱动宿主集成，无需第二调度器

原Schema、catalog、逻辑resourceUri、EnvironmentBinding与固定节点版本均沿用。load使用原Contracts；C1仍拥有run/node/attempt/iteration/approval/事件，Rust仅管理进程及命令门禁。MCP和A2A分别通过原BoundRuntime/AgentRuntime运行，不能把两类协议混称Agent函数。

本轮源代码全部在experiments/p0-06，没有改原runtime.py。可复用的边界成立，但原P0-02 required输出激活、policy作用域和完整DispatchRequest缺口未自动消失。适配器仍读C1内部snapshot/_fingerprint；真实产品应形成不可变的dispatch/query/cancel上下文与外部引用记录接口。

## F02：旧校验桥对宿主精简环境有隐含依赖

最小反例：相同Schema/fixture，直接从既有测试环境运行可通过；精简宿主环境中的pwsh脚本退出1，stderr为`SecurityError: AuthorizationManager check failed`。旧父环境的执行策略上下文不能作为干净桌面部署保证。

本轮没有传入策略绕过或提权。增加SchemaAdapter，使用已安装jsonschema4.26.0/Draft202012Validator解释**同一份**原Schema，子Schema同样合并原$defs与catalog.types，沿用check_references，不获取远程$ref。T02对有效文档、缺字段、版本漂移、null及未知字段7例与旧桥结果一致，核心/协议场景实际执行通过。

这是受限实现等价证据，不是所有JSON Schema实现的完全等价证明。原历史校验工具未删除，生产应固定关键词/format/数字边界与标准测试集，避免不同编辑端/执行端悄悄接受不同图。

## F03：venv launcher退出不等于执行树已停止

实际ready显示launcher与解释器PID不同。第一次关闭实现只wait launcher，ACK早于SQLite close，随后一次立即读库发生I/O错误。必要修正：C1库关闭后ACK，Rust终止自有Job并检查ActiveProcesses=0；最终所有停止观测为0。原失败库后来integrity_check正常，不能把这次短窗口问题夸大为SQLite普遍损坏，也不能据最终通过声称已覆盖断电恢复。

见[原始失败与恢复解释](./p0-06-runtime-lifecycle.md)。以后若只kill直接子进程、把Python launcher视为唯一进程、或先发“已关闭”再持久化，会造成真实返工。

## F04：系统适配层必须有明确可信程序解析

原服务/启动器硬限定各自实验evidence目录，直接传本轮目录实际失败。新增固定shim只改变原独立服务的证据根；仍调用原官方SDK Server/RequestHandler，不复制服务业务或调度器。系统层只允许两个本轮入口、固定解释器/参数、有限模式和P0-06路径；MCP包装器摘要进入本机绑定，适配源摘要进入load token，原服务制品摘要检查继续保留。

这也是部署耦合：当前导入原实验目录、复用catalog/环境安装引用，尚不能把p0-06单文件夹搬走即运行。未来需要可信programRef解析、安装制品闭包、版本/哈希/更新清单和依赖隔离，不应把旧实验绝对路径复制进可移植workflow。L1仍为定义加载/诊断，L2具备适配器依赖才执行，L3不迁移完整环境；只有Windows实测。

## F05：命令去重账本与运行状态不是同一事务

ipc-receipts只去重原命令ACK，不能决定业务终态。跨两个库崩溃会有“C1已提交、ACK尚未记录”的窗口；当前通过固定单run会话、原run恢复、内容指纹和不自动重发保守处理，而非声称分布式exactly-once。生产应把命令接纳/效果派发与C1事务语义明确衔接，区分correlationId、commandId、operationId、attemptId和taskId。

推送seq来自C1，Rust投影可丢通知；补齐靠原事件库。当前512项有界队列和16项查询分页仅验证有限图，极端慢读者仍可能阻塞同步stdout。长期背压、可靠gap通知、流大小、快照分页/裁剪和恢复游标是画布前必须补齐的工作，不能靠UI日志修状态。

## F06：审批门禁成立，但不是恶意代码隔离

Rust固定角色拒绝viewer启动、operator批准；Python C1继续核对有效grant并原子消费。真实MCP/A2A受控效果均验证未批准不提交，批准才执行；旧指纹、拒绝、重复决定、取消/重启不会产生重复效果或自动批准。

宿主批准的是固定可信执行profile，Python可在其中使用本轮系统适配层；没有任意命令/文件/脚本IPC。Tauri AppManifest把两个自定义命令纳入main capability，CSP只供本地内容，没有通用shell/fs插件。标准依据见[Capabilities](https://v2.tauri.app/security/capabilities/)；不能只注册invoke_handler就宣称自定义命令自动受最小ACL保护。

但是同用户可信Python仍能使用OS权限，测试窗口的approver角色也不是账户身份/物理人证明。T15中不存在fs插件的拒绝只证明该入口未注册，不能等同全面ACL攻击测试。[Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)管理自有树，不能代替不可信插件沙箱。

## F07：语言与实现成本

| 选择 | 本轮证据与收益 | 仍需支付的成本 |
| --- | --- | --- |
| 继续Python C1 | 原调度/类型/审批/恢复及官方MCP/A2A SDK直接复用，旧源码0修改；实际跨进程恢复通过 | 48包、解释器分发、插件依赖冲突、asyncio取消与故障边界；适配器仍耦合C1内部接口 |
| TypeScript执行器 | 可能与Vue Flow前端共享生成类型、减少Python发行依赖；这是设计收益，未做TS对照执行 | 必须重验所有现有状态/SQLite/审批/恢复与协议行为；共享语言不自动共享单一权威，不以推测声称更轻更快 |
| Rust重写调度 | 可减少宿主/调度IPC、直接使用系统类型；这是候选 | 需重实现本轮实际复用的调度与领域契约、SDK适配、取消/未知/恢复，失去现有回归覆盖的实现；本轮没有Rust调度性能/成本数据 |
| Rust宿主+Python进程 | 已实测真实窗口/进程/异常/恢复，职责清楚 | 增加分帧、请求账本、版本握手、队列、双生命周期、源码/依赖制品打包；本轮I/O失败就是额外成本的实际例子 |

实测[环境清单](../experiments/p0-06/environment-evidence.json)：本轮venv约82.45 MiB，既有基础Python排除site-packages/缓存约48.24 MiB；debug探针约1.03 MiB、debug窗口约12.81 MiB。**这些不是发行包体积，不能简单相加宣称最终安装大小**：还含/缺运行库、SDK资源、原实验闭包、压缩、WebView2分发策略等。Cargo.lock记录406个解析包，含其他目标/可选依赖，不等于406个实际嵌入产品的库。

Windows当前有MSVC/VC工具和WebView2，实际Tauri2.12.5构建/运行成功；[官方前提](https://v2.tauri.app/start/prerequisites/)和[安装包选项](https://v2.tauri.app/distribute/windows-installer/)不能替代本机之外的安装实验。MSI/NSIS、签名、离线、升级、x64/ARM64、干净用户目录与最终许可闭包仍未验证。

## F08：画布之前的门槛

Vue Flow应继续只产生原Workflow Definition；布局存在扩展，不能把节点UI状态当运行状态。下一轮最关键的是形成稳定的“校验/固定修订/命令接纳/错误/审批/事件补齐”边界，并以干净Windows发行探针验证依赖闭包；之后只做一条受控画布闭环，不把本实验的单run API直接扩成产品服务。

需要明确的未决项：统一存储I/O失败后的fail-stop策略（P0-04有GuardedStore，其余仍有实验差异）、精确派发授权上下文、命令与C1事务窗口、持久事件背压、程序制品解析/版本升级和正式用户权限。可继续用Python验证这些边界，暂不值得把现原型原样作为正式引擎基础或开始全面Rust/TS迁移。未自动进入下一阶段。

## F09：窗口运行时数据也要显式隔离

交付检查发现早期Tauri窗口按默认行为在本应用标识的AppData目录创建WebView2缓存。已将本实验专有旧目录核实后归档到本轮evidence，并为窗口明确设置会话内`webview-profile`；最终T15检查实际EBWebView目录存在，原AppData应用目录不再存在。[修正记录](../experiments/p0-06/evidence/isolation-correction.json)保留，未触碰其他应用数据。它说明仅控制执行器SQLite/日志路径还不够，桌面运行时数据目录也必须纳入系统适配/清理设计。
