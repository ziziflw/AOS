# P0-03 运行语义验证

日期2026-10-24；Windows x64，NT 10.0.22631；Python 3.12.14 / SQLite 3.53.1 / PowerShell 7.6.5 / JsonSchema.Net assembly 7.0.0.0。无新增依赖、无付费API、无真实账户、无正式GUI。代码及复现命令见[实验README](../experiments/p0-03/README.md)。

## 结论与证据等级

原P0-02格式可以驱动实际调度，A/B/C原图与请求均未经改写，运行时读取原catalog和Schema，并校验实际流经端口的值。**但Schema本身不足以唯一决定执行语义**：required输出、互斥分支及policy层级存在需要澄清的解释。原型使用固定版本白名单实现的显式规则，不能将这次成功说成任意符合Schema的工作流都能正确执行。

最终套件实际执行18个unittest方法，18通过、0失败、0错误。[summary](../experiments/p0-03/evidence/suite-20261024T034720437972Z/summary.json)、[日志](../experiments/p0-03/evidence/suite-20261024T034720437972Z/unittest.log)、[代码摘要](../experiments/p0-03/evidence/suite-20261024T034720437972Z/source-hashes.json)。运行输出、事件及断言全部由程序保存。

| 等级 | 本轮结论 |
| --- | --- |
| 已通过实际执行 | 本机最小调度器、原A/B/C合成适配器、审批、持久化、真实子进程退出恢复、取消和故障断言 |
| 已通过静态检查 | 新工作流/配置/请求/输出的原Schema校验、引用与版本诊断；P0-02历史117项仍只作为原静态证据保留 |
| 仅有设计依据 | 将该控制层接入Tauri、对照Rust/TS/成熟框架、多平台实现方案 |
| 尚未验证 | 真模型、MCP、A2A、OS沙箱、进程树终止、Linux/macOS运行、断电/满盘、多进程生产调度、跨框架checkpoint |

首轮套件18项中17通过、1失败，保留[原失败结果](../experiments/p0-03/evidence/suite-20261024T033548013484Z/summary.json)。T02中B/C均进入barrier后执行，但Windows monotonic_ns的粗粒度让C的started/finished相等，严格区间重叠断言失败。改用perf_counter_ns记录实际调用区间，保留原断言、屏障和并发上限测试；最终整套复测通过。没有把失败证据删除或修改为通过。

## 测试与输入/实际比较

以下路径均位于[通过套件](../experiments/p0-03/evidence/suite-20261024T034720437972Z/)；每个test_*下的assertions.json含expected/actual/passed，每个运行子目录有workflow.json、request.json、catalog.json、environment.json、simulation-plan.json、run.sqlite、synthetic-system.sqlite、assertion-point/final快照及事件。摘要不是替代这些原始证据的手写预期日志。

| 需求 | 测试方法/输入 | 实际断言结果 |
| --- | --- | --- |
| T01串行 | test_T01_serial / serial | 成功seedB；A持久成功seq早于B派发，B输入为A验证输出 |
| T02并行 | test_T02_parallel_and_limit / parallel | B/C高分辨率调用区间重叠，D开始晚于两者结束；反序完成仍按edge.order输出seedB、seedC；并发1不重叠 |
| T03条件 | test_T03_condition_and_exclusive_join / conditional | C skipped且调用0次；exclusive仅接收B，整图成功 |
| T04汇合 | test_T04_join_skipped_failed_cancelled | strict-all遇未选分支skipped且无死等；失败分支使run failed；取消分支使run cancelled；D不在无效依赖上执行；全部成功见T02 |
| T05循环 | test_T05_bounded_loop_and_iterations / 原scenario-c | 人工测试操作者逐项批准；第0轮失败、第1轮修复成功；不同iteration各有attempt 1和不同operationId；耗尽2轮时failed且无第3轮、无无效输出 |
| T06安全重试 | test_T06_safe_retry_attempt_history / serial + failFirst | B两个attempt分别failed/succeeded，ID不同，逻辑operationId一致，run成功 |
| T07未知结果 | test_T07_response_lost_unknown_no_retry / effect + lostResponse | 审批前副作用0；批准后副作用1但响应丢失，节点/run unknown；不重试，不派发C；重启后计数仍1 |
| T08进程中断 | test_T08_process_crashes_and_recovery | 三次独立子进程exit 73；提交后A成功不重跑；事务写入中完成状态回滚为running，恢复unknown且B不启动；审批暂停恢复仍待批，批准后副作用1 |
| T09取消 | test_T09_cancel_queued_running_and_approval | 未启动调用0；运行中协作取消确认cancelled、C不派发；待审批取消使旧批准失效且副作用0 |
| T09不合作调用 | test_T09_uncooperative_cancel_is_unknown | 忽略取消令牌，超过宽限期unknown；之后释放模拟阻塞，晚到结果审计并丢弃，无输出和下游 |
| T10权威状态 | test_T10_single_authority_and_transaction_view | 同run第二控制者被文件锁拒绝；修改返回快照/伪UI日志不改数据库；事件seq连续且快照一致；integrity_check=ok；合成校验和损坏被明确拒绝 |
| 原始A/B | test_P02_original_a_b_and_output_types | 原工作流修订保留，A双模型模拟/评审与B工具模拟实际成功，结果为对象；没有字符串化JSON |
| 审批阻断 | test_approval_pending_denied_and_duplicate | policy=policy的可信write也被C1阻断；未批/拒绝均副作用0；重复批准后计数1 |
| 审批绑定 | test_approval_content_binding_and_expiry | 摘要不符、内容变更的新run、旧审批及过期令牌拒绝；各对应副作用0 |
| 变更恢复 | test_approval_changed_definition_recovery_rejected | 暂停后改变定义的恢复被RECOVERY_DEFINITION_MISMATCH拒绝 |
| 类型/资源 | test_data_null_error_and_resource_validation | 允许nullable时显式null成功；Error对象冒充Text及不合结构的模型输出失败，下游不执行；缺失逻辑资源明确RESOURCE_NOT_BOUND |
| 预检诊断 | test_preflight_rejects_unknown_versions_fields_and_parameters | 缺字段、null、未知节点/未来字段/格式、版本漂移、能力/参数/连线不符、路径穿越、缺mock绑定、不可实现策略、不安全写重试均拒绝；输入保留；预检调用0 |
| 运行策略 | test_policy_timeout_budget_priority_and_rejections | 实际超时失败；token预留不足时不派发模型；并发1时优先级高的C先于B完成 |

共18个测试方法。上述子项不是额外“通过数量”；方法内的多个运行及断言属于同一个测试方法。汇合不实现any/race：没有显式可接受其语义的节点定义与处理器时不冒充支持。

## 故障点和持久化观察

T08各子目录包含fault-injection.json、worker-result.json及persisted-before-recovery.json。工作者是本项目自己的crash_worker.py，不运行外来脚本。

| 注入位置 | 退出时已提交状态 | 恢复动作 | 重复风险处理 |
| --- | --- | --- | --- |
| after-success：A成功事务COMMIT后，内存赋值前 | A succeeded、有效输出/事件已提交 | 同runId继续B/C | A调用1次，无重放 |
| during-success：快照+事件SQL写入后，COMMIT前 | 派发事务已提交，A仍running；成功事务回滚 | C1把A标unknown，阻断下游 | 不依据模拟系统的finished日志擅自宣布成功，不盲重跑 |
| waiting-approval：审批请求事务COMMIT后 | A成功、B waiting-approval、pending摘要/期限保留 | 同run恢复pending；显式批准后继续 | 重启不生成批准；未批准计数0，批准后1 |

模拟系统账本独立提交，刻意不与run.sqlite组成共同事务。它是测试断言依据，不能越权把运行状态从unknown改成成功。T07验证的“计数1”只是此次测试观察，不构成任意外部系统exactly-once保证。未实现核实后人工resolve API，unknown保持终态，需要下一阶段设计单独核实记录或新run。

## 数据契约执行

没有新增互不兼容格式。JSON根校验走原Schema；模型/工具参数走锁定capability.parameterSchema；端口值走原类型和catalog.types；sink结果走工作流/子图outputSchema。目录hash精确匹配字节，节点版本与实现白名单精确匹配。多上游值按order形成many输入，单值JSON数组与many端口区分。控制依赖也等待终态，不能靠日志文本推进。

缺失与null分别诊断；未来核心字段在执行前拒绝，不静默删除；未知节点完整输入作为诊断证据保留。逻辑workspace/artifact引用由模拟资源表解析，不把Windows绝对路径写入可移植workflow。类型包含关系仅采用保守规则；本轮没有验证复杂Schema子类型、流式媒体或动态端口。

## 单一权威和边界

SQLite快照是权威，C1内存状态只在事务成功返回后更新；事件与快照同事务。控制者锁防同一run双派发；checksum/seq冲突拒绝加载。只使用本地最小层，没有LangGraph/Temporal等外部checkpoint，故不存在本轮两个系统各自宣布终态的路径。**这不是外部框架checkpoint集成通过**；若后续引入框架，必须先明确其是唯一权威还是只作非权威投影，不能直接叠加调度器。

独立分支遇另一分支失败时允许已派发工作结束；依赖无效的一侧及下游不会再执行。取消会先持久化请求、撤销审批，停止新增调度；协作只确认可信模拟handler，不宣称能强杀任意外部阻塞调用。所有审批在本进程可信入口内检查，未实现OS沙箱或抵御同用户恶意Python/SQLite写入。

这些结论满足本轮“可重复代码验证核心子集或暴露缺陷”，不满足原E01–E07全部验收门槛，也没有将Windows静态Linux模板检查写成Linux运行成功。
