# P0-06 本地IPC契约

2026-10-27；实现入口：[Rust](../experiments/p0-06/host/src/lib.rs)、[执行端](../experiments/p0-06/executor.py)。内部协议是`aos-local/0.1`，与P0-02的工作流`0.1.0-draft.1`、NodeTypeVersion `0.1.0`分别版本化，没有创建新工作流格式。

## 封套与传输

请求：`{"v":"aos-local/0.1","kind":"request","id":"request-17","op":"status","body":{}}`。

成功响应：同v、`kind=response`、同id、`ok=true,result=...`。错误响应：`ok=false,error={code,retryable:false}`；不回显异常堆栈、秘密、原始非法数据或本机路径。无可安全解析的id用保留空串，不能把它关联到一个正常请求。

事件：`{v,kind:"event",id:<本次create或recover请求ID>,runId,seq,event:<原C1事件>}`。id关联打开该运行流的请求，**不宣称它是每个异步事件的精确因果ID**。命令取消/批准有各自响应id；事件业务顺序始终是C1 seq。启动ready使用保留`id=startup`关联隐含的固定启动握手；包含执行端版本和本机PID。PID只供当前系统监督/审计，不充当跨环境工作流身份，没有传Windows HANDLE。

宿主与执行器是继承的私有匿名管道，不开本地TCP命令端口。每帧为4字节无符号大端长度，后接UTF-8 JSON；长度1–262144字节，收头先检查大小再分配。执行端拒绝重复JSON键、非有限数、非法UTF-8、不完整帧与未知封套字段。Rust使用严格Request反序列化，body再由执行端逐命令检查。正常日志只写stderr/受控日志文件，stdout只写帧。

探针的外层测试入口采用同一封套的JSONL，262144字节上限；超长行返回FRAME_SIZE后断开，不能冒称它就是内部长度协议。T06直接向真实执行进程发送分帧非法输入，并测试恰好上限与超限；Tauri使用其实际WebView IPC，另经Rust进入同一长度通道。

## 操作与权限

| 操作 | body | 后端门禁/行为 |
| --- | --- | --- |
| host.start | 空对象 | operator/approver；固定Python/脚本/会话配置；重复启动返回alreadyStarted |
| health | 空对象 | 查询实际进程版本、C1权威、driverFault；进程失联返回通信错误 |
| load | builtin枚举 | operator/approver；加载固定原格式fixture，原Schema和Contracts完整检查，返回摘要token；不开放路径/任意JSON导入 |
| create | token | operator/approver；摘要匹配，创建唯一run，打开对应事件流 |
| recover | 空对象 | operator/approver；重读固定会话manifest及原run库，校验定义/绑定/本轮适配代码摘要后由原C1恢复 |
| status | 空对象 | 只读原C1 snapshot，不能由Rust编辑 |
| events | after非负整数 | C1持久事件分页，每页最多16项；返回lastSeq/authoritySeq |
| approvals | 空对象 | 查询原C1待审批动作，不是有效执行grant |
| approve | approvalId、fingerprint、decision布尔 | 仅approver；C1继续检查状态、run/operation/内容摘要、期限与取消，原子消费批准 |
| cancel | 空对象 | operator/approver；C1发起取消，不能直接把远端任务宣布已停止 |
| host.stop | mode=cancel/suspend | operator/approver；转执行端shutdown协调，得到ACK后核查自有Job清空 |
| shutdown（内部） | 同上 | 不从窗口直接暴露；cancel等待原C1有限取消，suspend保留持久在途身份及待审批 |
| host.crash-worker | 空对象 | 仅明确测试启动参数允许；测试窗口关闭该能力，只结束自有Job |

角色来自可信宿主启动配置，消息不能声明更高角色。viewer不能管理进程或启动运行，operator不能批准；T08实际越权调用被拒。正式用户认证/物理操作证明未实现，不能把本实验角色当OS安全身份。

`load` token绑定工作流、请求、catalog和本轮执行/系统适配源摘要；C1自身还固定workflow/request/catalog/environment/simulationPlan身份，原节点版本必须精确匹配。EnvironmentBinding保留原逻辑slot与局部命名扩展。原有配置中的本机安装路径仅在受信系统适配层解析，不进入工作流或IPC命令参数。

## 请求身份与故障

id为1–64位ASCII字母数字、下划线、连字符。执行器单会话同时处理一个命令，C1 driver异步推进；每进程最多记录4096个id摘要，超出明确拒绝。相同id改变op/body返回REQUEST_ID_CONFLICT。

create/approve/cancel的成功响应另存`ipc-receipts.sqlite`，跨重启同请求返回原ACK；原ACK可含当时快照，调用者应再查status。读取结果不持久缓存。命令账本不是工作流状态权威；只有C1库能证明节点是否成功。

这不是跨库exactly-once事务。C1提交和IPC receipt之间崩溃可能没有ACK；create会话已经存在则拒绝新建，需recover查询；批准和取消还受C1原有幂等/失效检查保护。不得换新id盲目重发未知副作用。未实现自动业务重试或无限重连。

启动握手5秒；管道写入由有界写线程执行，ACK等待3秒；响应等待20秒；关闭cancel在执行端至多等待4秒，随后只有原C1明确结果或错误；终止自有Job后最多等3秒核查ActiveProcesses=0。等待超时是通信/管理错误，**不是节点failed/cancelled的证据**。本轮没有对所有写阻塞/时钟/压力组合做完整故障穷举。

响应必须匹配当前id与v；晚到/不匹配响应只产生transport-warning，不能满足另一请求。事件队列与宿主投影均有界512项；投影丢弃旧通知时，不改C1事件库。断连、队列丢失或重启后按`(runId,seq)`查原事件补齐，已接收事件可重放，消费者去重；推送不是恢复权威。当前同步事件写在极端慢读者下仍可能阻塞C1，需生产背压改造，本轮仅验证有限合成图。

## 数据保护与信任范围

只使用自有合成数据，Agent合成Bearer由原SDK适配脱敏，Rust trace仅记录生命周期及代码，不记录凭据。错误不回显请求内容；窗口桥、驱动和C1证据会包含合成节点输入输出、审批指纹，正式产品仍需字段级输出/导出政策与保留策略。

管道不是抵抗同用户恶意进程的认证机制；Job Objects管理生命周期，Tauri capabilities限制窗口调用面，二者都不是完整OS沙箱。Python是可信执行器，拥有宿主选定固定profile内的程序/服务能力；不支持不可信Python代码、通用文件/网络访问IPC或任意插件。实际窗口允许main的两个应用命令，其他窗口/远程origin能力仅做配置审查，未宣称完成攻击面安全测试。
