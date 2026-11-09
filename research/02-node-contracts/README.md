# R02 · 节点契约与数据交换

P0-06增量：[原格式load token与IPC封套](../../planning/p0-06-ipc-contract.md)、[Schema校验桥最小替代与版本固定](../../planning/p0-06-architecture-findings.md)。同一原Schema由jsonschema解释并与旧桥做7例对照，原Schema/旧源码不改；完整派发契约及required/policy歧义仍未冻结。

P0-05增量：[Agent身份/结果/恢复](../../planning/p0-05-architecture-findings.md)在原格式下扩展领域JSON类型，taskId等只存运行记录；默认恢复逻辑仅提取为C1扩展点，原Schema未变。旧required输出及policy歧义继续保留。

P0-04增量：[Schema内联与节点映射](../../planning/p0-04-protocol-compatibility.md)、[最小反例/接口建议](../../planning/p0-04-architecture-findings.md)。真实MCP场景B已执行；原Schema/catalog/场景保留，P0-03校验器仅修正Schema属性误认运行URI，未冻结契约歧义。

P0-03执行增量：[契约发现](../../planning/p0-03-architecture-findings.md)记录required输出激活及policy作用域的最小反例。原Schema、catalog和A/B/C样例未改；[原型](../../experiments/p0-03/README.md)使用同一格式与固定实现解释运行，不能将其等同任意Schema实例可执行。

P0-02新增：[工作流Schema草案](./workflow-schema-draft.md)、[端口契约](./node-port-contracts.md)、[能力声明](./adapter-capabilities.md)、[声明性Schema](./schemas/contract.schema.json)、[场景样例catalog](./examples/fixture-catalog.json)。以下保留P0-01研究背景；具体候选语义以P0-02草案及其验证边界为准，未冻结。

状态：规范事实已核实，以下契约均为初步设想。[索引](../sources.md)。

## 可复用事实

[JSON Schema 2020-12](../sources.md#s16)及[Validation词汇](../sources.md#s46)可描述JSON实例并校验数据；format是否作为断言与验证器配置有关。它们不直接规定业务图的可达性、执行顺序或两个任意Schema间的可赋值算法。

[ComfyUI](../sources.md#s05)展示后端输入/输出类型及动态输入定义，[Workflow JSON](../sources.md#s06)展示格式版本演进；[MCP Tools](../sources.md#s28)用输入Schema和可选输出Schema描述工具。上述格式提供参考，不代表能够互相无损转换。

## 候选契约要素（不是完整schema）

| 对象 | 最低讨论要素 | 责任归属 |
| --- | --- | --- |
| 节点定义 | 稳定typeId、定义版本、输入输出、参数Schema、能力要求、副作用声明 | 定义模块管理，适配器提供描述 |
| 节点实例 | 实例ID、固定定义版本、参数值、绑定的端口 | 工作流文档拥有 |
| 数据值 | 文本/JSON/消息/文件引用/流等候选类别；空值和缺失需分开 | 契约模块解释 |
| 文件引用 | artifact标识、大小、媒体类型、摘要、来源、保留规则 | 基础设施拥有实物；定义只存引用 |
| 执行计划 | 已校验不可变定义与依赖闭包 | 定义模块生成，执行模块消费 |

二进制不宜默认塞入图JSON。候选做法为产物引用；跨进程需检验引用作用域、权限、文件存在与摘要，不能把外部URI自动当作可访问文件。流式块不能直接冒充最终已验证值。

## 数据流与控制流

方案一：数据边既表示值传递也表示就绪依赖；分支/循环以结构化节点表示。
方案二：数据边仅供取值，控制边独立决定触发；更接近显式控制路径，但必须处理数据未就绪与多次触发。
方案三：消息驱动节点；适合事件，但汇合关联、批次身份和恢复更复杂。

暂不选定。通用DAG只描述无环部分；有界循环可用受控子图/迭代实例展开，不能一面允许任意环一面声称纯DAG调度。

## 校验层与兼容

保存时做结构校验；运行前做端口/引用存在、必填、类型策略、分支作用域、无非法环、子图边界、循环上限、可达性和权限需求预检；执行前后做实际输入输出校验。权限预检不能替代真正执行时的授权。

Schema版本、节点定义版本与工作流格式版本独立迁移。破坏性变化应拒绝运行或显式迁移副本；未知节点保留原始参数并提示缺失。不能认为SemVer标签本身证明兼容。

待验证：E01覆盖旧图、未知字段、动态端口及非法图；E02覆盖结构化输出不合Schema和参数支持变化；E03覆盖MCP工具描述变更。暂不建立完整数据库或接口实现。

