# R05 · 外部工具与智能体协议

P0-06增量：[宿主发起真实MCP/A2A](../../planning/p0-06-host-verification.md)及[工具树/外部Agent不同生命周期](../../planning/p0-06-runtime-lifecycle.md)；复用原官方SDK和合成服务，批准前不提交，关闭本机不代表远端停止。没有真实模型/账户或任意第三方服务互操作证明。

P0-05增量：[实际A2A JSON-RPC](../../experiments/p0-05/README.md)已用线版本1.0/官方SDK1.2.3验证Send/Get/List/Cancel、独立异步任务与恢复；[兼容范围](../../planning/p0-05-protocol-compatibility.md)明确messageId去重/关联核实依赖自有profile。原MCP成果保留，Agent不是MCP工具别名，未宣称任意第三方互操作。

P0-04增量：[真实MCP stdio](../../experiments/p0-04/README.md)已用2025-11-25 / 官方Python SDK1.30.0维护线完成14项测试，含C1集成；[兼容记录](../../planning/p0-04-protocol-compatibility.md)解释与P0-02 SDK2.3.0候选的选择区别及SDK取消偏差。原候选/历史不覆盖，未把MCP当作Agent互操作通过。

P0-02新增[适配器职责与固定协议/SDK候选](./adapter-boundaries.md)，明确统一调度封套、模型/工具/Agent不同生命周期及远端信任限制；旧latest研究结论保留为背景，不代表兼容已实测。

[来源索引](../sources.md)；[安全分析](../07-security-permissions/README.md)。

## 三类调用必须保留差别

| 类别 | 输入与输出 | 生命周期 | 候选接口边界 |
| --- | --- | --- | --- |
| 模型调用 | 消息、参数 → 生成内容、usage、工具请求 | 一次生成及流式输出 | model.generate/stream概念 |
| 工具调用 | 工具名、已校验参数 → 工具结果、产物或错误 | 确定操作；也可能耗时或带副作用 | tool.describe/invoke概念 |
| Agent委托 | 任务目标、上下文 → 任务状态、澄清、消息、产物 | 可长期运行、等待输入、取消和重连 | agent.submit/query/cancel概念 |

接口名称仅为讨论，不是本轮实现或冻结的API。可以共享运行关联ID、错误封套和权限上下文，不能把Agent长期任务挤成只能返回字符串的一次函数。

## MCP已核实部分

[S28](../sources.md#s28)提供tools能力声明、工具发现与调用、输入Schema、可选输出Schema与structuredContent；服务端声明的输出规范仍需客户端校验。[S44](../sources.md#s44)定义初始化版本/能力协商与关闭；[S45](../sources.md#s45)定义stdio与Streamable HTTP。stdio的stdout只可写协议消息，日志应分离。

本地MCP候选流程：宿主按批准配置启动服务 → 初始化协商 → 枚举工具 → 保存描述快照 → 校验参数 → 策略检查 → 受控调用 → 校验/隔离输出 → 记录结果与关闭。工具列表变化时重新绑定定义，不能把旧审批自动用于新工具。

MCP不仅有工具，还有其他能力；本项目首个候选子集仅stdio工具发现/调用。是否支持resources、prompts、sampling、elicitation、tasks和远程认证仍开放，不能声称已支持完整MCP。2025-11-25文档已出现tasks相关能力，因此也不能断言MCP永远只支持同步函数；其任务扩展实现与A2A差异未深入核验。

## A2A已核实部分与版本风险

[S30](../sources.md#s30)定义Agent Card、任务操作、消息和产物及版本协商。latest页面同时涉及1.0和0.3兼容行为，不能据此认为任意SDK已支持同一版本。必须先固定规范tag、传输和SDK，按远端Agent实际能力处理取消、流式订阅、重连与需要输入的任务。

A2A负责Agent协作语义，不自动授予本机工具或文件权限；任务完成状态也不等于产物可信。建议后续独立设计契约实验，本轮E05只覆盖远端取消/结果未知的通用故障思想。

## HTTP与本地CLI候选约束

HTTP要限定方法/目标、超时、重试安全性、重定向、请求体大小、凭据注入位置与SSRF风险；远端响应是数据，不是权限指令。具体客户端库尚未选定。

[Node子进程文档](../sources.md#s41)说明spawn、execFile及Windows脚本差异。CLI应使用明确可执行文件、独立参数数组、指定工作目录、精简环境、标准流分离和输出上限；禁止把模型文本拼接为shell命令。无shell参数数组减少命令注入，但不约束程序自身的文件或网络行为。

待验证：E03检查stdio生命周期、畸形结果和描述变更；E06检查权限拒绝；E07检查日志污染、进程树回收及退出协调。

