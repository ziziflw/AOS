# P0-03 最小运行时验证

2026-10-24，Windows x64。独立实验，未建立正式应用或GUI。最终自动化套件 **18个测试方法通过，0失败、0错误**；首轮17通过、1失败的证据同样保留。测试中的失败节点是合成故障的预期结果，不计作测试失败。

入口：[运行验证报告](../../planning/p0-03-runtime-verification.md)、[架构发现](../../planning/p0-03-architecture-findings.md)、[交付报告](../../planning/p0-03-delivery-report.md)。

## 运行

使用本机已有 Python 3.12.14、标准库 SQLite 3.53.1、PowerShell 7.6.5（Test-Json / JsonSchema.Net assembly 7.0.0.0）。没有安装依赖或工作流框架。以下命令在项目根目录运行；Python路径只用于本机启动说明，不进入工作流定义。

```powershell
Set-Location -LiteralPath 'D:\AIOrchestrationStudio'
$p03Python = 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $p03Python -B -X utf8 experiments/p0-03/test_runtime.py
& $p03Python -B -X utf8 experiments/p0-03/run_demo.py --scenario serial
& $p03Python -B -X utf8 experiments/p0-03/run_demo.py --scenario effect
& $p03Python -B -X utf8 experiments/p0-03/run_demo.py --scenario c --approve-simulated
& $p03Python -B -X utf8 experiments/p0-03/contract_counterexamples.py
& $p03Python -B -X utf8 experiments/p0-03/audit_delivery.py
```

effect演示默认停在waiting-approval，副作用计数为零。`--approve-simulated`显式调用测试操作者，批准本次合成操作；执行内核本身没有自动批准逻辑。测试驱动器覆盖恢复流程，演示CLI不提供通用工作流导入或真实工具执行入口。每次套件/演示生成独立UTC命名目录，失败记录不被新运行覆盖。运行依赖原项目P0-02 Schema及样例仍在原位置，并需要pwsh可用。

## 文件与职责

| 文件 | 职责 |
| --- | --- |
| common.py | 严格JSON、摘要、错误、逻辑URI检查 |
| contracts.py / schema_host.ps1 | 原Draft 2020-12完整Schema校验、引用/能力/连线/有向图计划诊断；桥接脚本只做校验 |
| runtime.py | C1唯一业务控制层：节点状态、调度、审批、尝试、循环、取消、恢复 |
| store.py | 同一SQLite事务写入快照和事件；文件锁限制每个run单控制者 |
| mocks.py | 固定白名单模拟实现；另一个数据库只记录模拟外部调用/产物/副作用，不决定run终态 |
| fixtures.py / fixtures/ | 原契约下的7组合成工作流与请求、扩展catalog及纯模拟环境绑定 |
| harness.py / test_runtime.py | 独立夹具、断言、证据导出与测试操作者 |
| crash_worker.py | 本项目自有子进程，在指定事务点以exit 73实际终止 |
| contract_counterexamples.py | 原描述中的精确歧义提取；不改原始资料 |
| baseline-manifest.json | 实施前43个既有文件的SHA256 |
| audit_delivery.py | 既有资料保留、测试源码摘要与交付链接的只读审计 |
| evidence/ | 真实执行产生的输入、结果、事件、断言、SQLite和日志 |

## 状态与身份

Workflow Definition是不可变修订；Workflow Run用新UUID创建并绑定定义、请求、catalog、环境、模拟故障计划的摘要。恢复保留runId；定义改变则拒绝恢复。Node Instance用`scope/nodeId`定位；Node Attempt每次派发生成独立ID和number。重试保留operationId；新的Iteration建立新scope、iterationPath与operationId。Execution Event有同一事务提交的递增seq。

queued的phase分为waiting-dependencies与ready；running、succeeded、failed、skipped、waiting-approval、cancel-requested、cancelled、unknown互不混用。阶段细分是实验内部运行记录，不给旧ExecutionStatus枚举添加新状态。对外数据沿用P0-02 RuntimeValueEnvelope，含版本、类型、摘要和attempt/iteration来源。导出JSON和界面快照均不是可回写状态入口。

全局并发上限按实际worker计数；节点并发上限在相同adapter ID或builtin type组内计算；就绪节点按priority降序、key稳定排序。循环容器不占worker槽，避免子图死锁。多输入按edge.order绑定，不按返回顺序。

严格all汇合要求所有必需路径有效；未选路径使all跳过。exclusive汇合等待相关前驱终结，只允许一个有效分支；失败、unknown和取消不会被当作条件未选中。失败/取消/unknown阻止依赖闭包派发，独立已派发分支允许结束；工作流终态优先unknown、failed、cancelled，再根据sink判断成功/跳过。这是本原型对`onFailure=stop`的明确解释，不承诺全局瞬时杀停。

## 契约子集和拒绝边界

原始A/B/C工作流和请求逐字保留并实际加载执行；适配器实现全部替换为白名单进程内模拟，环境是独立mock绑定。新夹具仍使用原schemaVersion、NodeDefinition、AdapterDefinition、端口、policy、catalogLock和EnvironmentBinding，未创建第二种工作流格式。`simulation-plan.json`只作为实验故障注入参数，不是可移植业务定义。

完整Schema检查之外，还检查节点/端口/适配器版本、能力参数、输入输出实际值、nullable、many顺序、目录锁摘要、逻辑资源存在与元数据。类型兼容采用保守的同名/同schemaRef规则，不实现任意JSON Schema包含关系推导。未来核心字段/未知节点拒绝运行并保留输入副本；extensions只保留已存在的夹具标注，不执行扩展语义。

支持白名单内23种原builtin/model/tool/agent节点的**模拟返回语义**和12种synth测试节点。不实现真实模型流、MCP握手、A2A任务查询/取消、系统命令或任意脚本。缓存必须off、错误分支必须stop、workflow重放必须maxAttempts=1/retryMode=never；idempotent重试、未注册实现、多值输出、任意环、多sink、未连通节点、未知版本明确拒绝。安全重试只接受none/read和适配器safe-read声明，且错误明确可重试。

审批由C1依据可信注册表与catalog的最保守副作用分类强制；write/unknown、always及core.approval必须先批准。批准绑定run/操作/参数/输入/定义摘要及有效期，消费与派发同事务；拒绝、过期、取消或内容变化不能执行。此机制只验证可信模拟入口，不构成任意Python代码或同用户恶意进程的安全沙箱。

token用最大输出声明做保守预留和实际用量记录；局部/全局限制不允许无限派发。模拟成本固定0，非零成本结果拒绝，金额预算不代表真实计费验证；供应商usage缺失、失败后计费与货币换算尚未实现。模型/Agent配置只驱动相应固定模拟行为，不证明模型参数、网络权限或远端任务生命周期生效。workflow priority只有单run内元数据意义，无多run仲裁器。

## 恢复和限制

run.sqlite的快照是权威，事件与快照在同一事务提交；没有外部框架checkpoint。snapshot采用checksum、seq及单控制者锁，导出不能覆盖权威。模拟外部系统与run记录故意分开提交，用来暴露外部操作完成、响应丢失的窗口。恢复时未确认在途节点一律unknown，不盲目重复；安全重试和崩溃恢复不是同一个动作。待审批恢复不会自动批准；已消耗批准且未确认结果的节点也不能重放。

进程中断测试证明本机SQLite提交/回滚和恢复分支；未做断电、磁盘损坏/满盘、网络共享存储、生产规模压力或跨框架checkpoint实验。不合作模拟调用超过取消宽限期转unknown，晚到结果丢弃；没有声称外部阻塞调用可立即终止。审批期限与运行总超时采用本机壁钟，审批时间计入总期限，生产版须明确时钟回拨和暂停计时政策。

L1定义加载与诊断延续原设计；本轮只有Windows上的实际执行证据。L2仍要求目标环境有适配器/依赖；L3不承诺凭据、插件及完整环境自动迁移。Linux模板静态检查没有升级成Linux执行通过。当前Python原型适合作为一致性测试参照，不能据此冻结正式执行引擎或Tauri集成路线。

## 证据入口

- [当前通过套件](./evidence/suite-20261024T034720437972Z/summary.json)及[测试日志](./evidence/suite-20261024T034720437972Z/unittest.log)。
- [保留的首轮失败](./evidence/suite-20261024T033548013484Z/summary.json)：Windows粗粒度monotonic_ns使短任务区间判定失败，改用perf_counter_ns后复测通过。
- [最新结果指针](./evidence/latest.json)供后续复跑；静态报告固定链接本次通过套件，避免未来运行覆盖结论。
- [契约最小反例](./evidence/contract-counterexamples.json)。

每个test_*目录有expected/actual/passed断言；每个运行有完整输入、assertion-point与final快照、事件、模拟调用计数及SQLite。T08另有worker-result、故障点和恢复前持久化状态。统计单位是18个unittest测试方法，子场景、断言、故障点及原P0-02的117项静态检查不混加。
