# 节点端口与数据类型契约

P0-02研究候选，未冻结。类型结构见[Schema](./schemas/contract.schema.json)，领域JSON形状见[样例catalog的types](./examples/fixture-catalog.json)。

## 最小类型与值语义

| 起始类型 | 值形状 | 限制 |
| --- | --- | --- |
| Text | JSON string | 不自动将JSON、文件或错误字符串化 |
| JSON | 指定schemaRef约束的JSON值 | 样例类型含Task、Candidate、CandidateSet、Review、Comparison、ToolRequest/Args/Result、Goal、Plan、ExecutionResult、Validation |
| FileReference | resourceUri、mediaType、sizeBytes，可选sha256 | 仅引用，不通过边复制二进制；实际存在性/摘要/权限运行时检查 |
| MediaReference | file、mediaKind，可选尺寸/时长 | 元数据不是解码验证，运行时仍需核实 |
| Error | code/message/category/retryable/sideEffect及可选details | retryable是建议，不能越过C1/E2安全判断 |
| ExecutionStatus | state、sequence、attemptId | control端口只作门控；权威状态由C1事件决定 |

类型清单是起点，新限定类型须登记其Schema和兼容规则。required=false表示允许没有输入；nullable=true表示允许显式null，两者不能混用。缺失、null、空字符串、空数组是不同值。多值端口接收按边order排序的值列表；它不是“某个JSON数组”单值端口。

样例中JSON端口采用同名schemaRef精确匹配，不推断任意Schema的子类型；看似可兼容也可能需要显式转换节点。Text→JSON解析、JSON字段投影、Media→FileReference等转换均应独立声明并校验，禁止依赖模型自判类型。

## 连线与激活

数据边：来源direction=output、目标=input，双方channel=data；名称/Schema标识与nullable兼容。控制边：双方channel=control、类型为ExecutionStatus，不携带业务payload。数据边本身已经建立执行依赖，control边不能替代缺失数据。

单值输入最多一条边；多分支选择后合并必须使用专门merge。many输入的order必须存在且唯一，到达顺序不改变业务顺序。A使用all汇合，必须收到两份有效Candidate；一支失败时不伪造缺省结果。C使用exactly-one-active汇合，只接受已激活分支之一；两支都激活或都无值为错误。

条件未选路径传播skipped；merge等待可达分支状态决议，不能永远等未选分支。disabled节点不会隐式透传；依赖它的必填输入产生阻断诊断，用户需显式改接或使用有定义的旁路节点。

## 检查时机

| 时机 | 可确定内容 | 尚不能保证 |
| --- | --- | --- |
| 画布连线时 | 已知节点/端口、方向、通道、标称类型、基数、明显成环 | 动态输出、运行值、远端实际Schema和权限 |
| 保存/执行前B1 | 完整图/版本、精确Schema绑定、配置、必填、子图引用、顺序、循环上限、disabled影响 | 已安装实现是否可信，服务在线，真实文件与秘密可访问 |
| 环境预检E3/D/E2 | OS/架构、运行时/程序、服务/凭据引用、协议协商、权限需求 | 调用后副作用、服务端输出与费用 |
| 运行时D/C1 | 实际输入、输出Schema、大小、产物摘要、流结束、取消确认与副作用状态 | 任意外部系统exactly-once和完全确定模型输出 |

前端校验用于即时反馈；后端必须以自己的注册表/能力快照重新校验。用户传来的ports/capabilities不是权威注册信息。

## 输出版本、有效性和大数据

RuntimeValueEnvelope把payload与provenance分开，后者含工作流修订、节点/适配器版本、capabilityId、attemptId、logicalOperationId和iterationPath。JSON payload要按valueType.schemaRef再次校验；外壳通过不够。validity为provisional/validated/stale；只有validated终值可触发普通下游。流式片段仅供观察，增量消费要另有显式节点协议。

输出修订或上游参数变化后，C1计算后继闭包并使相关缓存失效；子图变更先影响其调用节点，再影响外部后继。历史run仍绑定旧修订，不就地改成新参数。产物可用摘要寻址，但保留/删除受E1/E2策略约束。

FileReference不能直接反序列化为任意路径。解析先按最长合法逻辑挂载匹配，再规范化与检查目录边界、链接/重解析点、权限和摘要；禁止路径穿越、UNC绕过和解码后逃逸。大体积数据只传引用，真正读取须经执行端授权。具体缓存/引用计数实现仍开放。

