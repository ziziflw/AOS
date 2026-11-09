# P0-03 架构发现与候选技术记录

日期2026-10-24。依据[实际运行报告](./p0-03-runtime-verification.md)与[精确描述反例](../experiments/p0-03/evidence/contract-counterexamples.json)。本文件提出建议，未接受正式ADR，未修改正式模块边界或既有Schema。

## F01：required输出缺少按结果激活的定义

原catalog的core.input.task等节点把error输出声明required=true；成功输入节点实际只应该输出out及done。若通用执行器把所有required输出解释为每次必发，正常成功也必然失败，或者被迫制造错误值。原core.condition同时把pass/fail标required=true，而原场景要求互斥选择，不能同时满足字面上的“每次两者必发”。提取脚本保存原描述、成功输出集合和缺少的字面必需端口，可重复观察，无需改动原文件。

**最小建议**：明确required仅对输入连接是否允许缺失，或为输出增加结果激活约束（success/error/rejected以及exactly-one-of分支组）；不能只把所有required随手改成false。影响范围是NodeDefinition解释、输出校验与编辑器诊断，工作流现有连线不必整体重写。下一轮先评审、版本化补丁及迁移测试，再更改正式契约。

本原型在固定版本builtin白名单中定义输出激活：成功不发error/rejected、condition仅一个数据分支、done由C1产生。原A/B/C因此可运行，但这是受限的明确解释，不能声称仅从Schema就能生成任意正确执行器。新第三方节点若没有受信实现与对应激活语义，拒绝执行。

## F02：policy层级、汇合及失败范围须先固定

原B的workflow maxAttempts=1/retryMode=never与tool maxAttempts=2/retryMode=safe并存。若root是每节点总上限，tool第二次不能执行；若root指整run重放，则两者不冲突。原型采取后者，节点safe重试已有实际断言，workflow自动重放拒绝。建议正式文档明确策略作用域与合并算法，防止UI、SDK、执行器分别重试导致次数相乘。

严格all不能静默忽略必需分支skip；exclusive可以消去未选条件路径，但不可消去failed/cancelled/unknown。本原型以固定节点类型表达两种策略；未实现any/race。`onFailure=stop`解释为阻止受影响依赖闭包，不强杀无关已派发分支。生产版须把“全局fail-fast”还是“依赖传播”形成版本化决策，并固定终态聚合优先级；否则未来大图会出现最难排查的差异。

## F03：审批描述必须由可信控制层补足

仅靠模型或adapter描述effect不足以强制安全。C1取NodeDefinition、AdapterDefinition、可信注册实现的最保守effect；write/unknown及always在派发前被阻断。测试中操作policy=policy仍需要批准，证明不是模拟节点自行遵守。

批准绑定runId、operationId、scope/node、固定定义/输入/环境/模拟计划摘要、参数和期限；消费与派发同事务。拒绝、旧内容、过期、取消和重复提交各有实际断言。重启后pending仍pending；已派发未确认则unknown，不靠重新批准冒充安全重放。建议正式版增加审批主体、可信授权存储、资源动作集、可核实操作状态及核实审计。本原型approve()调用者均为可信测试操作者，不提供用户认证或抗同用户恶意篡改能力。

## F04：尝试、迭代与未知结果是不同维度

同逻辑节点重试：同operationId，不同attemptId/number；有界修复循环：不同iteration scope、operationId和节点实例，各自attempt从1开始。定义修订和run身份不可互换，恢复摘要不一致直接拒绝。

本地提交不能证明远端未执行。结果丢失或崩溃后未确认在途节点保守unknown，即使它是纯节点也不自动重跑。只有运行中明确失败、可重试错误、none/read副作用、适配器safe-read与剩余尝试上限同时满足时才安全重试。billable、write、unknown及不可查询结果不盲重试；idempotent尚未实现，明确拒绝。未来需定义“核实操作”及其权限，不能把unknown直接改failed后自动再发。

## F05：单一权威先于引入成熟框架

run.sqlite快照与事件共同事务，C1是唯一业务写者；模拟外部账本只作观测，不能决定run终态。文件锁、seq/checksum及事务中断在Windows上已实测。SQLite提供事务基础而非工作流语义；[S21](../research/sources.md#s21)、[S59](../research/sources.md#s59)、[S60](../research/sources.md#s60)不构成任意外部副作用共同原子提交的保证。

未来如采用LangGraph或其他checkpoint，须先选择：框架成为唯一执行权威，本地只是投影；或C1继续权威，框架不得再拥有可独立恢复/调度相同run的checkpoint。禁止把两套终态事后“同步”当协调方案。本轮没有验证外部框架对照，不据此得出自研比成熟框架更好。

## 技术选型记录：验证方便，不锁定产品

| 项 | 实际选择/观察 |
| --- | --- |
| 语言 | 已有Python 3.12.14；asyncio方便显式调度和故障注入，sqlite3/unittest/hashlib等标准库足够完成验证 |
| Schema | 已有pwsh 7.6.5的Test-Json调用原Draft 2020-12，JsonSchema.Net程序集7.0.0.0；不写简化Schema方言，不安装框架 |
| 成本 | 实现集中于小控制器、契约校验、SQLite事务和固定mock；完整源码/测试可读，仍需要自行维护状态与边界，不能以代码小推断生产成本低 |
| 并发 | 单进程asyncio协作并发，global worker槽与同adapter/type分组上限；不是CPU并行、多run公平调度或分布式执行 |
| 持久化 | 每次状态变更deepcopy整个snapshot并同步写SQLite，简单可审计；大图、长历史、吞吐、背压尚未测，不能作为性能基线 |
| 依赖风险 | Python目前还依赖pwsh做校验；这是本机复用条件，分发时可能成为包体/启动/跨平台障碍 |
| 预算 | 合成0成本，输出上限保守token预留；不覆盖失败调用计费、价格更新、真实usage未知、货币换算 |
| 协议限制 | model/tool/agent均固定模拟，不能证明供应商参数、MCP会话、A2A取消/任务身份等真实语义 |

Python的任务取消是协作式机制，[asyncio官方说明](../research/sources.md#s58)支持这个实现基础，不意味着外部阻塞进程可无条件终止。节点timeout用于可信mock等待；不合作取消确认缺失转unknown。未进行断电/磁盘故障测试；SQLite的进程退出恢复结果只限本次注入条件。

| 候选语言 | 推断的后续成本，非本轮实测 |
| --- | --- |
| Rust | 可贴近Tauri宿主和OS资源控制；异步状态机、动态Schema与故障夹具需要更多实现/集成工作，不能据此否定其生产优势 |
| TypeScript | 可与前端类型共享，异步适配自然；仍需可信运行验证器、持久化和Windows进程管理，静态类型不能替代JSON边界校验 |
| Python | 现有原型迭代快，适合保存为契约一致性测试参照；解释器/校验桥分发、依赖控制、性能与桌面进程治理尚无结论 |

Tauri集成候选：宿主只发版本化submit/approve/cancel/query请求、读取事件；独立执行进程拥有run.sqlite，宿主和前端不得直接写运行状态。需验证IPC分帧、身份/序号、协议版本、背压、崩溃和子进程树生命周期；这只是设计，没有创建Tauri工程。

## 会造成大规模返工的问题及下一步

优先解决F01/F02的激活语义和策略作用域、F03的可信审批边界、F04的核实/重试身份，以及F05的权威选择。若先写GUI或接更多插件，这些缺口会扩散到节点描述、编辑器、调度、日志及恢复格式。其余生产缺口包括状态迁移、token/金额账本、资源生命周期/摘要、审批时钟与超时计时政策、进程隔离、清理和持久化故障处理。

**建议保留当前原型作为可执行契约参照，不直接提升为正式引擎基础。** 下一轮优先验证“Windows上自有无副作用MCP stdio服务”，把进程生命周期作为这一受控集成的组成部分：固定规范/SDK、握手与工具描述锁、输出校验、stdout污染、超时/取消、响应丢失、宿主退出及子进程清理；继续复用本轮状态/审批/unknown断言。相较直接接入完整Agent，它能先暴露本原型尚未覆盖的IPC与取消真实性，且无需付费模型或真实账户。A2A任务查询/核实应在该基础之后单独验证。以上仅推荐，未执行P0-04。
