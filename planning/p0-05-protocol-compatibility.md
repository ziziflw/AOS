# P0-05 A2A 协议兼容记录

核验2026-10-24。实际环境、制品/SDK源码摘要见[environment-evidence](../experiments/p0-05/environment-evidence.json)；执行结论见[验证报告](./p0-05-agent-verification.md)。

## 版本与接口

| 层 | 固定值与证据 |
| --- | --- |
| 规范参照 | [A2A v1.0.1](https://a2a-protocol.org/v1.0.1/specification/)；沿用P0-02候选，保留站点标题1.0.0/URL-tag1.0.1差异 |
| 线协议 | Major.Minor **1.0**，每次HTTP请求A2A-Version:1.0；实际消息证明没有静默退到0.3 |
| SDK | [官方Python a2a-sdk1.2.3](https://github.com/a2aproject/a2a-python/releases/tag/v1.2.3)，客户端/服务端同版本；[兼容表](https://github.com/a2aproject/a2a-python/blob/v1.2.3/README.md)声明实现规范1.0而非SDK版本等于规范patch |
| 服务 | 自有aos-p05-agentA/B 0.1.0，独立进程和持久任务；不是模型或第三方Agent产品 |
| 发现 | 官方Agent Card路由与A2ACardResolver，/.well-known/agent-card.json；锁名称、版本、技能、JSONRPC URL、线版本和实验profile |
| 调用 | 官方JsonRpcTransport和create_jsonrpc_routes/JsonRpcDispatcher、protobuf模型、自有RequestHandler |
| 传输 | 本机127.0.0.1 HTTP JSON-RPC，SendMessage/GetTask/ListTasks/CancelTask；旧0.3兼容关闭 |

官方来源：[SDK依赖/Apache-2.0](https://github.com/a2aproject/a2a-python/blob/v1.2.3/pyproject.toml)、[JSON-RPC客户端](https://github.com/a2aproject/a2a-python/blob/v1.2.3/src/a2a/client/transports/jsonrpc.py)、[Server路由](https://github.com/a2aproject/a2a-python/blob/v1.2.3/src/a2a/server/routes/jsonrpc_routes.py)、[Server dispatcher](https://github.com/a2aproject/a2a-python/blob/v1.2.3/src/a2a/server/routes/jsonrpc_dispatcher.py)。本轮已核查固定源码及本机安装版本，旧apps/jsonrpc等路径不存在，未拿旧示例拼装新版API。

本轮采用**实际标准A2A**，无需退到非A2A HTTP任务探针；没有宣称所有1.0.1边界/所有SDK互操作通过。SDK1.2.3处理Major.Minor版本的发布修正与P0-02候选吻合，但仍以实际JSON-RPC有限测试为证据。

## 实际生命周期

Agent Card发现→检查能力/许可范围→C1批准并持久submit-intent→SendMessage(returnImmediately=true)→收到SUBMITTED Task/taskId→持久关联→GetTask观察WORKING/进度→COMPLETED→取Artifact→端口/产物校验→C1发布下游。

服务自己启动异步worker；提交后立即返回稳定taskId，HTTP请求结束不结束任务。状态查询只读原任务，重连不再次SendMessage。服务重启从自己的SQLite恢复待处理任务；C1恢复从自己的SQLite恢复run与task关联。二者是不同对象、不同权威。

标准Artifact中data part携带结构化业务结果，url part指向同源合成产物；下载是标准产物引用的受控HTTP读取，不是另一套非A2A任务调度协议。结果类型是原契约扩展的AgentTaskResult，FileReference沿用原定义，包含逻辑URI、媒体类型、大小、SHA256。

## 标准保证与实验profile保证

| 能力 | 标准基础 | 本实验的额外约束与局限 |
| --- | --- | --- |
| 稳定任务身份 | Task.id/contextId、GetTask | C1额外绑定run/node/attempt/operation及固定Agent/endpoint，不允许串用 |
| 非阻塞提交 | configuration.returnImmediately | 本profile要求true，非同步“立即完成”伪装；合成任务至少150ms |
| 消息去重 | 规范说SendMessage **MAY** 幂等，Agent可利用messageId | 自有SQLite messageId唯一约束及请求摘要，同ID改内容拒绝；不推导为任何A2A服务的exactly-once |
| 关联核实 | ListTasks按contextId筛选 | 仅显式启用后按精确本地身份/messageId唯一匹配，分页未完成则拒绝；进度/sequence和元数据含义由本profile定义 |
| 任务取消 | CancelTask与任务CANCELED/错误 | 得到匹配取消终态才确认；不支持/竞态完成/失联保持unknown，无补偿/撤销承诺 |
| 等待/结果 | INPUT_REQUIRED/AUTH_REQUIRED及COMPLETED Artifact | 本地保留等待phase，未实现交互续谈；产物缺失有限等待，到期unknown |
| 认证/权限 | Agent Card securityRequirements与部署安全要求 | 只用loopback合成Bearer标记，无真实认证账户；平台审批不能控制远端内部自主工具 |

规范的Idempotency条款没有保证所有SendMessage可安全重复。提交已发、taskId响应丢失时，默认unknown；即使本服务支持去重，适配器也不靠重复提交核实，而是选择一次标准ListTasks关联查询。查不到/不唯一不能静默重发。普通Agent节点的maxAttempts>1/safe重试配置明确拒绝。

## 状态与错误解释

| 外部事实 | C1结果/阶段 |
| --- | --- |
| SUBMITTED/WORKING | running + waiting-agent-query；不释放下游 |
| INPUT_REQUIRED/AUTH_REQUIRED | running + waiting-agent-input/auth；保留真实等待语义，无自动伪回应 |
| COMPLETED且产物可验证 | 若run/版本/授权仍有效，succeeded与validated输出 |
| COMPLETED但产物缺失 | waiting-agent-artifact；期限内查询，耗尽unknown/AGENT_RESULT_UNAVAILABLE |
| FAILED/REJECTED | 本地failed，保留AGENT_FAILED/AGENT_REJECTED，不把它改成成功 |
| 匹配CANCELED | 本地cancelled；单纯取消请求不够 |
| 未确认提交、失联、非法协议、身份/序号冲突、等待超时 | 本地unknown，无自动提交重试 |
| 取消/参数变更/授权失效后的旧结果 | 拒绝发布；远端可能仍COMPLETED，本地不假装撤销其内部动作 |

固定SDK的send_http_request/JsonRpcTransport没有隐藏重试循环，HTTPX transport显式retries=0。适配器只在预算内重复GetTask；每个发送/查询/取消及异常都有脱敏协议记录。服务InternalError中的合成秘密不进入C1错误文本，保存日志实际检查无泄漏；不是对任意秘密/隐私识别的普遍证明。

## 契约和环境

继续使用0.1.0-draft.1工作流、catalogLock、NodeDefinition、AdapterDefinition、JSON端口与RuntimeValueEnvelope；没有把Agent压成MCP工具。Model、Tool、Agent适配器仍分开。Task引用/进度不进入便携定义，只进入C1运行记录。

旧EnvironmentBinding仅有https/stdio/cli，无http-loopback类型；本轮cli/programRef指本机Agent程序，loopback A2A端点存入已有aos:agent-services扩展，明确不是将HTTP冒充https/CLI传输。程序路径/参数、OS信息属于本地绑定。正式版应设计有类型的程序注册与服务接口绑定，不继续依赖任意扩展。缺服务时仍保留原始图，可加载/诊断，无GUI编辑器声明。

42个依赖的确切版本、官方项目元数据、制品哈希和许可见实验目录清单。SDK Apache-2.0及各依赖许可/NOTICE保留；未修改上游SDK，未安装Agent框架/大型模型。Windows wheel离线解析成功不等于干净机器安装或Linux/macOS执行通过。TLS、OAuth、多租户、跨设备、SSE/push、完整列表/历史/续谈与其他绑定未验证；本次不能作为完整A2A符合性认证。
