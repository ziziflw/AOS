# P0-08 能力、类型与供应商边界

实际节点类型为 `p08.openai.text/json`、`p08.anthropic.text/json`，NodeDefinition0.1.0、原 schemaVersion0.1.0-draft.1，executionKind=model、effect=billable。`fixture.*` 适配器表示本轮服务为合成，不表示模型收费语义被降为 none。catalogLock 的 resourceRef 仍为 catalog:core，内容哈希绑定本轮目录；旧目录和 Schema不改。

| 能力 | OpenAI 离线接口 | Anthropic 离线接口 | 证据 / 范围 |
|---|---|---|---|
| API / SDK | /v1/chat/completions；3.41.0 | /v1/messages；2.3.0，声明2023-06-01 API | 实际 HTTP；不是实际供应商版本兼容认证 |
| 输入 | 一个 Text 用户消息 | 一个 Text 用户消息 | C1类型校验与 SDK请求账本 |
| 输出 | Text，或 P08Answer JSON | Text，或 P08Answer JSON | JSONSchema要求 `{answer:string}`，额外字段拒绝；下游提取器仍是明确类型 |
| 输出限制 | max_completion_tokens | max_tokens | AOS maxOutputTokens映射；usage另检查输出上限 |
| 采样 | 夹具显式支持 temperature | 夹具不声明 temperature | UI按两份 configSchema显示，后端拒绝额外参数；**不能推导真实 Anthropic 模型均不支持温度** |
| 用量 | prompt_tokens / completion_tokens | input_tokens / output_tokens | 分别保留实际返回字段；缺失为 null，不是零 |
| 超时 / 取消 | 1.2s SDK超时，C1另有节点/运行期限 | 相同 | 客户端取消/断网后 unknown，未确认服务端停止或计费 |
| 流式 / 工具 / 多模态 / 推理参数 | 本轮不支持 | 本轮不支持 | capabilities明确 false；没有假装可调控件 |

参数链：固定能力声明 → catalog configSchema与 Adapter parameterSchema → 原 Contracts 后端验证 → 原检查器生成基础控件。未知参数、错误类型、版本漂移、未绑定别名拒绝。没有通用 Schema 表单框架或供应商任意 extra_body 通道。

环境绑定沿用 P0-05 的可信本地程序解析约定：`connection:p08-model` 的 cli/programRef 指向固定执行进程提供的本机服务工厂；它**不是 HTTP 线协议名称**。真正 HTTP 端口由本进程创建并直接交给 SDK，不进入便携工作流。原 Schema transport 只有 https/stdio/cli，尚无 http-loopback：本轮未把明文 HTTP 冒写为 https，也未扩大 Schema；后续若外接通用本机 HTTP 服务，应正式定义传输扩展并对照兼容，而不是依赖这个限定程序绑定。

模型 serviceSlot、AdapterRef、selector、凭据状态及固定连接均后端核验；不能靠改 EnvironmentBinding 将自有服务变为任意程序或远程收费服务。具体运行时凭据别名和动态端口不参与便携定义。模型节点名与工作流修订在派发时固定，运行中改草稿不改变已启动版本。

新增厂商应主要增加 D1 SDK调用/错误映射、专属能力声明、环境绑定和同组回归；不改 C1调度或 MCP/A2A 协议。缓存 Token、推理计量、多模态、流式中断、供应商特定 structured-output 子集及真实模型可用性均待实测，不能从两份夹具推及所有模型。

L1定义加载/诊断保持目标；L2仅Windows当前依赖闭包与限定服务实测；L3不承诺密钥/插件/环境自动迁移。Linux/macOS没有执行证据。

旧P0-07文档可按原格式保留/诊断；其catalogLock属于旧目录，不能在本轮静默改哈希后宣称原版本直接运行。要迁移执行，必须显式重绑定受检目录及核对节点版本。本轮提供新目录的合成样例，未实现自动目录迁移。
