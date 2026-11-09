# 适配器能力声明与自由配置

P0-02研究设计。依据：[S22–S28](../sources.md#s22)、[S44/S45](../sources.md#s44)，新增版本候选见[适配边界](../05-tool-agent-protocols/adapter-boundaries.md)。

## 谁声明、谁验证

D1/D2/D3从锁定实现、官方元数据和受控探测产生描述；B1登记可信版本并绑定工作流；A1按该描述呈现表单；实际派发前由B1/D再次校验配置与真实输入，C1验证调度策略，E2验证权限。导入文件自带的声明、模型输出或远端工具提示都不能替代本机可信注册与实际能力检查。

CapabilityDeclaration.selector区分provider、model、apiVersion、interface；适配器id/version和capability.id进一步锁定映射含义。evidence区分fixture/documented/probed；observedAt记录时间。默认不自动接受过期/漂移快照，实验前复查。模型名称是别名时还需记实际响应版本/供应商指纹，不能证明稳定版本时显示不确定。

## 参数面板与执行策略

| 用户控制 | 描述方式 | 后端负责人 |
| --- | --- | --- |
| 模型、采样、推理、最大输出Token | selector+parameterSchema，条件依赖/互斥可用JSON Schema；原生字段命名空间化 | D1验证并映射 |
| 上下文范围/消息角色 | 显式节点输入及类型化映射，不偷偷带全局聊天 | B1/D1 |
| 数据映射 | 已注册声明式映射节点；JSON Pointer取值、输出Schema | B1/D2；本轮不允许任意表达式脚本 |
| 超时、重试、并发、优先级、预算 | supportedControls筛选ExecutionPolicy；effective值取系统、run、节点与供应商限制的收敛 | C1统一调度/预算；D仅一次请求 |
| 失败分支 | onFailure=stop或error-port，error-port须有有效连线 | C1决定状态并传播Error |
| 人工审批 | policy或always；不能在工作流配置“跳过安全政策” | E2决定，C1等待，E3/D强制使用授权 |
| 启用/禁用 | enabled；禁用不等于旁路 | B1诊断、C1标记skipped |
| 子工作流 | 固定定义/版本、显式边界与有界策略 | B1校验、C1管理子运行 |

unsupported参数不呈现可编辑控件；unknown能力显示为待确认且阻止派发。历史图已有不支持值时保留并报错，不静默删除、钳制或发送。若支持“高级原生参数”，必须有对应版本Schema及权限规则，不能用任意JSON逃过校验。

## 精确参数差异样例

fixture.model.a只允许maxOutputTokens；fixture.model.b另允许0–1的temperature。它们是离线校验夹具，**不是Claude/Gemini实际参数表**。测试证明本地校验器能拒绝A的temperature及B的越界值；没有证明任一供应商真实兼容。

P0-01的[S27](../sources.md#s27)已说明Claude API版本变化；本轮复核该官方版本页，保留结论与旧LiteLLM模型表的适用范围差别。真实E02应在固定模型、API版本、账户渠道下重新生成能力快照，不能把fixture配置直接发给真实端点。

## 平台与执行能力

AdapterDefinition.platforms按OS/arch列最低运行时、外部程序、协议版本、权限、无头能力；capability另外声明cancel、resume与retrySafety。能力分别有unsupported/best-effort/confirmed或相应枚举，不能用一个supportsEverything布尔值。

样例列Windows/Linux x64只是夹具预检数据，不是安装/运行承诺。实际探测需验证程序版本/制品、服务协商、账户权限及OS限制；运行时不一致应报阻断诊断。未声明的可选能力不可假定存在。

## 取消、重试与副作用

取消分为“请求已发送”和“远端已确认终止”；超时可能留下unknown副作用。retrySafety不是工具自报就可信，E2/D需要受信任证据。无副作用/只读且安全的调用可在预算内有限重试；写入或未知操作禁止safe重试；idempotent模式须有真实幂等键、查询及服务端行为证据。

C1生成稳定逻辑操作身份；同一操作的重试复用幂等键，新迭代/新授权操作使用新的逻辑身份。SDK不能隐藏无限重试，C1统筹实际请求次数和费用。Fixture中的idempotency-key只验证声明分支，未证明服务端去重。

