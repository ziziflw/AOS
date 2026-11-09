# 版本化工作流定义契约 · P0-02草案

版本：`0.1.0-draft.1`，日期2026-10-24。**这是研究契约候选，不是稳定格式或已实现运行时。** 依据：[S16](../sources.md#s16)、[S46](../sources.md#s46)、[S49](../sources.md#s49)；实际检查见[静态验证](../10-feasibility-experiments/validation/README.md)。

## 交付与文档种类

[contract.schema.json](./schemas/contract.schema.json)使用Draft 2020-12，集中定义下表概念。根对象按kind区分workflow、catalog、environment-binding、run-request、value-envelope。保持一个Schema文件，避免引入应用工程或远程解析依赖。Schema的.invalid标识仅作命名，不作网络端点。

| 概念 | 所在位置与关键字段 | 语义与拥有者 |
| --- | --- | --- |
| WorkflowDefinition | workflowId、schemaVersion、version、catalogLock、graph、subgraphs、inputSchema/outputSchema、environmentRequirements、executionPolicy | 可移植且无运行状态的正式定义，B1拥有 |
| WorkflowVersion | revision、可选parentRevision/label | 工作流内容修订，独立于文件格式与节点版本；发布后视为不可变 |
| NodeDefinition | typeId、version、executionKind、ports、configSchema、effect、supportedControls | 注册的节点类型；B1登记可信D/E内置实现描述 |
| NodeInstance | id、typeId/typeVersion、config、enabled、policy、可选adapter/serviceSlot | 图中实例；配置随修订固定，输入不塞在config里 |
| PortDefinition | id、direction、channel、type、cardinality、required | 数据契约与控制依赖的静态描述 |
| EdgeDefinition | id、kind、from/to、order | 只连接端口；order用于多值顺序，布局不影响顺序 |
| AdapterDefinition | id/version、kind、platforms、capability、effect | 模型/工具/Agent的实现描述，不含凭据或连接明文 |
| CapabilityDeclaration | id、selector、parameterSchema、supportedControls、cancel/resume/retrySafety、evidence | 按模型/API/接口版本精确描述能力；fixture不能当真实支持 |
| ExecutionPolicy | timeoutMs、maxAttempts/retryMode、并发、优先级、预算、失败、审批、缓存 | 用户请求的上限与行为；C1/E2仍有最终约束 |
| EnvironmentRequirement | slot、kind、required、adapter、permissions | 工作流需要什么，不记录本机安装位置 |
| EnvironmentBinding | platform、services/resources/credentials/connections | 本机绑定，不属于可移植定义；E3管理具体配置 |
| RunRequest | workflowId/revision、environmentProfile、inputs | 一次运行输入，不携带已有运行状态 |
| RuntimeValueEnvelope | valueType/payload、validity、provenance、可选contentDigest | 实际输出的版本/来源/有效性；不能写回定义 |

## 定义、配置和运行的分离

正式workflow不含runId、attempt、运行结果、检查点、批准决定或API Key。输入来自单独RunRequest，匹配固定修订的inputSchema。节点config包含prompt策略、最大token、操作名称或映射规则等稳定配置；当前输入由数据边或输入节点传入。

C1后续应创建独立RunRecord，至少固定：workflowId/revision、定义摘要、catalog摘要、环境绑定摘要、实际能力快照、runId、输入产物引用、状态和事件序号。节点实例执行身份再含scope/iterationPath/attemptId；这些是运行记录设计，**本轮未建立数据库Schema或运行器**。

根级schemaVersion识别结构语法；version.revision识别业务内容；NodeDefinition.version识别节点行为；AdapterDefinition.version与capability.id识别映射和供应商接口语义。四者不可互相替代。

## 固定实现含义

样例用catalogLock固定[fixture-catalog.json](./examples/fixture-catalog.json)完整UTF-8文件字节的SHA-256。NodeInstance再精确引用节点/适配器版本与能力ID。Catalog是描述快照，**不等于已安装可执行代码**；实际运行还需可信安装记录/制品摘要与相应描述对应。此项后续必须验证。

修改catalog即使只是格式化也会改变此草案的锁摘要，必须显式更新workflow修订；保守但易验证。未来是否改用语义规范化摘要仍开放，当前不伪称已实现RFC规范化算法。适配器升级、模型别名漂移、API版本/工具Schema/权限变更均阻断自动沿用，需差异诊断、重绑定或显式迁移。工作流不会静默采用latest节点。

## Schema校验与语义校验分层

结构Schema校验字段、版本字符串、枚举、必填、基础数值限制。config本身先保留JSON对象，再用已锁定NodeDefinition.configSchema和实际CapabilityDeclaration.parameterSchema二次校验；不能以config通过外壳校验宣称参数合法。

inputSchema/outputSchema和catalog.types内的Schema需要在受信任本地Schema包中编译；只允许本包片段引用`#/$defs/...`。本轮检查器合并核心$defs与catalog.types供校验，不访问网络。正式导入需增加Schema复杂度/深度/大小限制与关键字白名单，防止恶意Schema消耗资源。

图校验另查ID唯一、节点/端口存在、方向、类型、基数、必填、汇合顺序、非法环、子图边界、被禁用依赖和绑定一致性。现有离线检查器只覆盖文档列出的有限规则，不证明任意Schema类型推理、分支可达性或调度正确性。

## 扩展、未知数据和版本失败

已知核心结构用additionalProperties=false防拼写错误；扩展应放到命名空间键，如`extensions["vendor:feature"]`。新类型可用限定名，必须有受信任定义、校验器与显式类型兼容规则后才能执行；未知类型不能退化成Text或any。

未知typeId的NodeInstance仍可通过结构外壳校验并原样保留config/extensions/连线；执行预检给出NODE_UNRESOLVED。未知核心字段或未来schemaVersion在严格校验中拒绝，但**编辑器导入保留模式**应保存完整原始JSON树并只读展示/诊断，允许保存原始副本。不得用一次严格解析失败来删除字段。实际产品导入/保存器尚未实现；本轮仅测JSON值级往返，不承诺空白、键顺序或数字字面量字节一致。

有未知核心语义时，不允许执行已知子集后假称完整流程成功。用户替换节点后另存修订，重新检查全部相关连线和授权。

## 资源与秘密

定义只含workspace:/artifact:/input:逻辑资源引用与serviceSlot。Windows盘符、UNC、file:和本机绝对路径留在EnvironmentBinding。本机绑定也只存secretRef/vaultAlias，密钥明文由E3的OS机制保管，E2控制访问。

任意自由文本无法靠JSON Schema证明绝不含秘密。契约禁止Key/Authorization/password等明文配置，已知节点Schema不提供此类字段；未来导出还需敏感字段元数据、秘密扫描和用户控制。未知节点只保留不执行；不能把不明config当作安全的可分发模板。

## 子图与受控控制语义

本候选采用**数据边隐含值就绪依赖，显式control边只增加门控**。同一作用域不允许环。条件节点只激活一条输出，未选路径必须传播skipped；多支“任取一个”须显式merge而不是给单值端口接多条线。

普通子工作流调用候选为单次输入/输出映射、独立子作用域和固定版本；本轮只对bounded-loop节点提供具体样例。Loop引用命名subgraph，显式maxIterations和until条件，每轮新身份，未达到条件耗尽上限则失败，不输出“成功的坏结果”。递归调用禁止；子图I/O匹配与分支跳过传播仍待后续执行实验。

三个样例共用本契约：[A](./examples/scenario-a.workflow.json)、[B](./examples/scenario-b.workflow.json)、[C](./examples/scenario-c.workflow.json)。样例catalog全部为fixture，没有实现任何模型、工具或Agent。

