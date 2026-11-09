# P0-06 执行进程生命周期与恢复

2026-10-27。实际状态依据[最终套件](../experiments/p0-06/evidence/suite-20261027T121250322189Z/summary.json)，不是日志推断；IPC规则见[通信契约](./p0-06-ipc-contract.md)。

## 拥有关系与权威

Rust Host拥有自己的Windows Job、执行器launcher及实际解释器、继承管道。启动固定本轮venv/script后先加入Job，再开放worker-gate；ready返回实际PID，宿主核查它确实属于该Job。Python可在宿主批准的固定profile内启动可信MCP及其子进程；它们还属于Rust父Job，并由原MCP适配器的嵌套Job管理。

独立A2A服务由本轮测试监督器拥有另一Job，用来模拟远端任务的独立生命周期。宿主既不扫描同名进程，也不终止这个Job。测试结束监督器只清理自己的记录PID。生产远端服务如何部署不由本轮模拟服务推导。

| 数据/状态 | 所有者 | 宿主行为 |
| --- | --- | --- |
| workflow definition、固定revision/node version | 原契约/manifest | 传固定选择与token，不复制解释器 |
| run、node、attempt、iteration、approval、seq | 原Python C1 + run.sqlite | 读投影/转命令，不写终态 |
| 原Agent taskId与观察 | C1快照绑定；Agent另有任务事实权威 | 不能把本机退出当远端取消 |
| IPC ACK账本 | 通信端receipt库 | 去重命令，不据此决定工作流终态 |
| PID、Job活动数、断连 | Rust系统监督 | 只报告本机生命周期事实 |

没有外部框架checkpoint，也没有两个系统分别宣布工作流终态。宿主掉线时未提交的推送丢失不改变C1；恢复检查SQLite快照摘要与事件序号一致。

## 启动、关闭与异常

1. 固定配置→创建kill-on-close Job→启动可信执行器→加入Job→开放gate→5秒内ready。初始化失败/超时清理自己的Job；重复启动不再启动第二个执行器。
2. 加载固定原格式workflow并验证→token→create；run UUID由原C1生成。一次会话只允许一个run，第二个宿主若认领同一库，由原ControllerLock拒绝。
3. `cancel`由原C1将节点/工作流置取消中、撤销待审批/未消费grant并发协作信号；未启动节点取消，迟到输出不得释放下游。纯合成延时节点允许0.9秒取消宽限；MCP/A2A保持各自原策略。不能无条件立即终止外部阻塞调用。
4. `host.stop(cancel)`先等原C1有限取消、保存证据，再关闭SQLite后发ACK；`host.stop(suspend)`保存已有快照/事件/远端身份及待审批，关闭SQLite后ACK，**不把在途业务强行改成cancelled**。
5. ACK后宿主终止/回收仍属于自己的Job，等待ActiveProcesses=0再报告本机停止。普通探针stdin EOF的正常退出也尝试suspend协调；Tauri退出走相同路径。管理超时单独报错，不能覆盖业务结果。
6. 宿主/执行器被真正杀死时可能来不及协调；Job关闭回收本机树，SQLite WAL/FULL及原C1恢复负责解释最后提交事实。Rust不生成一个替代终态。

正常suspend使用实验专用的同步关闭后退出方式，不把asyncio取消所有协程误当业务取消；因此已开始但未确认的MCP恢复为unknown，已确认结果保留。此方式适合本轮可信固定子进程，不是完整插件析构、远端事务回滚或用户数据保存框架。

## 恢复决策

- **已确认成功**：同run及原attempt/output保留，不再执行效果；T11批准后重启再次核查attempt完全相同。
- **审批暂停**：pending保持，不能自动批准；原批准内容/TTL/取消规则仍生效。T11先杀真实宿主，再显式批准。
- **MCP在途**：没有可靠完成事实时原C1置unknown，不重放；T10保留已确认输入，工具attempt只有1个。
- **Agent已知taskId**：复用P0-05 query-only恢复，同run/node/operation/attempt/taskId，原deadline不续期；T13分别覆盖宿主被杀和正常suspend后Agent继续工作，恢复没有第二次SendMessage。
- **无法核实的副作用/远端取消**：保留unknown及task身份，不把关闭应用解释成远端停止。T14实际CancelTask不支持，C1 unknown且无下游输出，外部Agent仍活。
- **并发认领**：第二个执行器CONTROLLER_ALREADY_OWNED；第一所有者关闭后可由原C1认领。尚未测试文件别名/网络盘/多用户绕过或跨机器锁。

## 本轮发现的关闭窗口

扩展测试曾在宿主收到ACK并等待launcher退出后，立即读SQLite得到`disk I/O error`；证据在[失败套件T13](../experiments/p0-06/evidence/suite-20261027T115030914197Z/summary.json)。当时宿主没有等待Job成员清空，ACK又早于数据库关闭。这两处都是确切实现缺口；推断它们共同形成Windows解释器/WAL共享内存清理竞态，不能据单次观测证明唯一根因。

修正为关闭C1/receipt数据库后ACK，并查询Job活动成员直至0。原失败库稍后重开`integrity_check=ok`、state=running，[复核记录](../experiments/p0-06/evidence/prior-io-error-recheck.json)保留。修正后两轮完整15项均通过，最终每次Job停止记录activeAfterStop=0；没有删除失败、跳过恢复检查或把I/O错误改成“测试通过”。这仍不是断电/文件系统故障穷举证明。
