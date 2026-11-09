# P0-05 独立 Agent 验证

2026-10-24，Windows 11 x64 / NT10.0.22631，Python3.12.14。规范参照A2A v1.0.1，实际线版本1.0，双方官方a2a-sdk1.2.3。复现入口：[实验README](../experiments/p0-05/README.md)。

## 结果与证据分类

专项**18测试方法通过、0失败、0错误**：[固定摘要](../experiments/p0-05/evidence/suite-20261024T061121087692Z/summary.json)、[日志](../experiments/p0-05/evidence/suite-20261024T061121087692Z/unittest.log)、[源码/夹具摘要](../experiments/p0-05/evidence/suite-20261024T061121087692Z/source-hashes.json)。受影响回归独立执行：P0-03 [18方法通过](../experiments/p0-03/evidence/suite-20261024T060828857517Z/summary.json)；P0-04 [14方法通过](../experiments/p0-04/evidence/suite-20261024T060834989387Z/summary.json)。不将三者相加称作50个Agent协议测试。

| 等级 | 已证实范围 |
| --- | --- |
| 真实独立Agent协议 | 官方A2A SDK客户端/服务端、HTTP JSON-RPC、独立OS进程、发现、Send/Get/List/Cancel、结构化Artifact |
| 合成Agent行为 | 无模型确定性worker，真实异步延迟、状态/进度、持久任务、取消/拒绝/故障；不代表模型能力或第三方Agent产品 |
| 工作流集成 | 原C1依赖/汇合/审批/attempt/预算和SQLite权威；新增受限查询恢复，真实执行器exit85及Agent服务重启 |
| Mock/静态 | 原P0-03模拟套件及部分类型/环境拒绝；不是额外A2A互操作或跨OS证据 |

所有业务数据和副作用只在p0-05/evidence独立目录；真实账户、付费模型、Linux/macOS运行均为0。

## 测试到实际证据

以下方法目录位于[最终套件](../experiments/p0-05/evidence/suite-20261024T061121087692Z/)。每个方法有assertions.json（expected/actual/passed）和process-cleanup.json；每个run有workflow/request/environment、run.sqlite、快照/事件；每个Agent有启动命令/ready、http.jsonl、agent.sqlite、观测任务/事件。T08/T18另有worker-result、fault-injection和persisted-before-recovery。

| 需求/方法 | 输入与实际结果 |
| --- | --- |
| T01正常 / test_T01_normal_delegation_pipeline | input→agent→output成功；独立任务1，text=SYNTHETIC，taskId与运行关联一致，产物实际获取/校验，C1输出validated |
| T02异步 / test_T02_asynchronous_states_and_progress | delay700ms；拿到taskId时远端SUBMITTED/WORKING、本地running、下游queued；查询持久记录10/60/100进度，最后成功 |
| T03拒绝 / test_T03_remote_rejection | mode reject；保留TASK_STATE_REJECTED，C1 failed/AGENT_REJECTED，下游skipped，无伪结果 |
| T04断连 / test_T04_real_disconnect_requery_same_task | GetTask响应故意截断真实HTTP连接；恢复成功，所有查询同taskId，task-created只有1，无第二提交 |
| T05提交丢响应 / test_T05_submission_response_lost_unknown_and_reconcile | 接受后截断Send响应；默认unknown、taskId=None、远端任务1、下游skip。显式启用本实验关联profile后，ListTasks按contextId和精确身份唯一匹配，记录核实并成功，无重发。受审批effect任务丢响应亦unknown，远端effect1，三个不同run各任务1 |
| T06取消 / test_T06_cancel_confirmed_unsupported_and_completion_race | 正常任务CancelTask得到匹配CANCELED才本地cancelled；不支持/取消后仍完成为unknown，Agent实际收到cancel，随后可独立COMPLETED，旧结果没有输出 |
| T07并行 / test_T07_two_independent_agents_parallel_join | 两个实际服务进程/任务区间重叠，结果按edge.order为agentA、agentB；taskId与artifact URI各自独立，正确汇合 |
| T08执行器重启 / test_T08_engine_crash_query_only_recovery | C1提交WORKING观察及taskId后执行器exit85，Agent仍活着；同run、attempt、operation、taskId及deadline恢复，query-only完成，attempt1/任务1 |
| T09过期结果 / test_T09_stale_definition_and_authorization_results | 更改旧请求后恢复拒绝；新run取得自己的NEW-INPUT；受控任务授权在结果前过期则本地unknown、下游skip，但已接受远端effect1，不假称撤销 |
| T10产物 / test_T10_artifact_schema_source_and_availability | bad-result/bad-reference均failed且未获取任意路径；result-delayed等待后成功；result-never最终unknown/AGENT_RESULT_UNAVAILABLE，远端COMPLETED状态保留 |
| T11审批 / test_T11_approval_controls_real_send_message | 未批、拒绝、过期、取消批准均零受保护请求/任务；重复有效批准只产生一个实际A2A任务及effect1；门禁在C1/D3，不依赖自然语言或Agent广告 |
| T12异常 / test_T12_abnormal_states_timeout_exit_and_protocol_error | 外部FAILED映射failed；INPUT_REQUIRED/AUTH_REQUIRED保持等待phase后可确认取消；查询不可核实、非法JSON、实际服务exit81均unknown；等待deadline到期为AGENT_WAIT_TIMEOUT而非远端failed |
| T13身份 / test_T13_task_identity_mismatch | 错operation或错taskId分别AGENT_IDENTITY_MISMATCH/AGENT_TASK_ID_MISMATCH，local unknown，无输出 |
| T14重复 / test_T14_duplicate_submission_and_duplicate_result | 标准messageId在本服务原子去重，重复请求同taskId；同ID改内容拒绝；两次真实GetTask的完成结果一致，C1终态后拒收重复观察，下游attempt1 |
| T15旧状态 / test_T15_old_state_cannot_overwrite_new | 注入更旧sequence/SUBMITTED后报AGENT_STATE_REGRESSION，接受的WORKING与序号不回退 |
| T16参数/版本 / test_T16_invalid_parameters_versions_and_missing_service | 节点输入与服务端参数分别校验；非法版本9.9拒绝、无任务；Agent自动重试配置拒绝；服务缺失不删节点；Agent Card版本漂移阻止提交 |
| T17日志 / test_T17_sensitive_error_redaction | 预设错误含合成Bearer标记，任务状态仍unknown；保存JSON/JSONL/log未含标记且有实际REDACTED，未使用真实秘密 |
| T18服务持久化 / test_T18_service_persistence_and_query_recovery | 执行器exit85后，再实际终止/重启Agent，恢复相同endpoint与持久taskId；新服务进程继续任务，C1查询完成，任务总数1 |

18是unittest方法数，方法内子场景、断言、进程、资料条目和回归不作为额外通过数。

## 权威、身份及中断窗口

外部taskId、身份、stage、lastSequence、remoteState、progress、lastTask和deadline存于C1的同一run.sqlite快照/事件事务；服务自己的agent.sqlite只控制远端任务。适配器提供经过匹配的事实，不直接写本地终态，也不能让远端Task状态覆盖本地run。

| 窗口 | 可解释的处理 |
| --- | --- |
| SendMessage前 | 持久submit-intent和稳定messageId/contextId；未批准无请求 |
| 请求已发、响应丢失 | 不推断失败/未创建，taskId缺失保持unknown；禁止自动重发。可选关联核实须本实验profile的唯一匹配证据 |
| taskId已提交、执行器退出 | C1受限恢复原attempt并GetTask，不调用SendMessage，不重置等待期限 |
| Agent服务退出 | 远端已提交任务在服务数据库保留；失联观测unknown，不能靠进程死亡判断任务最终失败；受控重启服务后按已有身份查询 |
| 结果完成、产物不可得 | 远端COMPLETED与本地等待分离；有限查询后仍无产物则unknown，不制造空结果 |
| 结果到达但run取消/参数改变/授权失效 | 不发布旧输出；已取消远端或完成远端都保留原始观察，不能驱动新定义的下游 |

T08/T18真实退出码85，恢复前节点running且有外部关联，恢复后runId/attemptId/operationId/taskId均不变。Agent进程由实验监督器管理而非执行器拥有，因此工作流进程中断不等于杀Agent；测试结束才清理监督器拥有的Job。全部清理只针对自己记录的PID/句柄。

## 首轮失败保留

[首轮摘要](../experiments/p0-05/evidence/suite-20261024T060420267685Z/summary.json)为18方法：16通过、1方法失败、另1方法产生2个错误（测试及teardown各一次），不是3个不同方法失败。T04把set写入JSON证据失败，改为排序列表；T05故障按进程全局只丢首个响应，第二分支未真正触发核实，改为按messageId丢响应并保留核实断言。原日志、数据库、协议记录与部分断言原样保留，见[原因记录](../experiments/p0-05/evidence/development-failures.json)。后续完整复测通过，并对实际Server Job归属核查后再次完整复测。

## 尚未验证

仅同一SDK、同一主机的自有合成Agent；没有第三方Agent产品、真实推理、跨设备调度、TLS/OAuth、多租户、SSE/push、人工澄清续谈、通用分页、大负载/长周期、断电/磁盘故障或桌面打包证据。标准A2A操作通过不等于全部A2A规范符合性通过；messageId去重、进度序号和关联核实属于本服务的受限保证。Windows替代绑定不等于Linux/macOS执行验证。
