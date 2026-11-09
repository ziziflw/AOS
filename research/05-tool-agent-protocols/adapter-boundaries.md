# 模型、工具与独立Agent适配边界

P0-02设计；不实现调用器。来源：[MCP](../sources.md#s28)、[MCP生命周期](../sources.md#s44)、[A2A固定规范候选](../sources.md#s54)、[HTTP](../sources.md#s57)。

## 统一入口可以统一什么

C1使用一份概念DispatchRequest：run/节点/作用域/iteration/attempt/逻辑操作ID、workflow修订、adapter版本、capability摘要、已验证输入、配置、有效政策、deadline、trace关联、E2授权凭证引用。此对象是受信任后端构造，不能把前端提供grant或能力表直接转交执行。

统一的是关联、预算、deadline、事件和错误封套；请求体保留model/tool/agent判别字段，不能把所有响应压成string。D返回事件事实，只有C1转换本地状态。调用前参数Schema、输入Schema、权限与能力快照均需一致。

| 对象 | 专用请求 | 必须保留的结果 | 生命周期 |
| --- | --- | --- | --- |
| 模型D1 | 消息角色/内容、上下文范围、精确模型/API配置、输出Schema | 文本/结构化内容、工具请求、流片段、finishReason、原始usage、warnings | 生成完成；工具请求不构成工具已执行 |
| 工具D2 | 发现快照、工具名称、已验证参数、授权、幂等/查询上下文 | content/structuredContent、产物、工具错误、operationId、sideEffect状态 | 超时仍可能已执行；必要时查询/人工核对 |
| Agent D3 | Agent Card/技能、任务目标/约束、上下文与任务引用 | taskId/contextId、等待输入、状态、消息、产物、取消结果 | 提交不等于完成，取消发送不等于远端终止 |

没有API、CLI、MCP/A2A或受支持插件接口的第三方软件，当前记为不可直接编排。平台不提供依赖通用界面模拟点击的适配方案。

## 下一阶段固定候选（本轮未安装）

| 项目 | 实验候选 | 范围与边界 |
| --- | --- | --- |
| MCP规范 | 2025-11-25 | 先stdio工具发现/调用；可选对照Streamable HTTP，其他能力不自动开启 |
| MCP Python | mcp 2.3.0，tag v2.3.0 | [S51](../sources.md#s51)发布说明支持研究旧版本连接；真实握手待测 |
| MCP TypeScript | client/server/core 2.4.0；node适配2.1.2 | [S52](../sources.md#s52)分包版本，不把所有包写成同一版本 |
| A2A规范 | 发布tag v1.0.1，线协议1.0；优先JSON-RPC绑定 | [S53](../sources.md#s53)、[S54](../sources.md#s54)，不自动降到0.3 |
| A2A SDK | Python a2a-sdk 1.2.3，tag v1.2.3 | [S55](../sources.md#s55)；TS替代候选版本尚未核验，保持开放 |
| HTTP/CLI | HTTP按RFC9110；CLI采用受控外部程序契约 | 客户端库和程序版本实验前固定；不假设HTTP方法名就足够证明业务可重试 |
| 模型 | Claude Messages API 2026-10-21与Gemini generateContent v1beta | [S27](../sources.md#s27)、[S56](../sources.md#s56)；精确模型及SDK版本待实验前选择，不用fixture冒充真实能力 |

发现：SDK发布说明已涉及MCP 2026-07-28，本轮仍选2025-11-25作为有限实验候选，不能称其全局最新版。A2A v1.0.1站点正文顶部仍写Latest Released 1.0.0，而GitHub发布tag为1.0.1；**保留版本标识冲突**。实验前须对照tag正文/制品摘要，不能将该页面标题当作已验证SDK兼容。固定版本源码tree入口浏览受限，未完成源码级审计。

## 状态、错误与取消传播

C1本地状态候选：queued→running→succeeded/failed，或waiting-input/waiting-approval；cancel-requested只表示已请求，可进一步到cancelled或unknown。skipped用于未激活分支。终态更新需run/attempt/sequence匹配；迟到事件记录审计，不能覆盖另一个attempt或撤销已确认取消后派发新下游。

Agent任务状态使用映射表保留原始值；远端working/input-required/auth-required、终态与错误，不能全部映射成成功的HTTP响应。D3在重连时query已存在taskId，不盲目submit同一任务。

错误封套含category、code、message、retryable建议与sideEffect状态；权限拒绝与参数失败在派发前产生not-started。工具超时/断线、远端Agent失联可能为unknown；C1停止依赖分支并请求核对，而不是自动当成安全失败。错误分支必须显式选择，Error不能流入普通Text/JSON端口伪装成正常结果。

## 授权与真实外部副作用

D2负责发起授权检查并将决定落实到具体调用，不拥有授权政策；E2是唯一决定者，C1持久化等待与执行状态，E3提供OS机制。D3也必须在提交任务前校验范围并审批，远端Agent内部工具权限不能仅靠本地Prompt约束。

场景C的执行/修复Agent均在提交前审批，最终审批只控制产物发布。若第三方Agent没有可审计的约束/审批接口，则其内部操作只能作为受信任外部系统处理，或拒绝该高影响场景；不能宣称本地E2能拦截远端任意内部动作。

## 复用与实验门槛

E03验证协议/Schema/错误；场景B验证本地与远程差异；场景C先用无副作用Agent服务验证任务、取消与重连，再考虑批准的写操作。每个候选记录完整依赖锁与目标OS结果。Python SDK用于探针不等于选择Python为最终核心，TS/Rust路线保持开放。

