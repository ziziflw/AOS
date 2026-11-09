# P0-06 交付报告

2026-10-27。已完成Windows Rust宿主、独立Python执行器、受限IPC、真实Tauri最小窗口，以及故障/恢复/进程检查。**15项专项通过，原P0-03/P0-04/P0-05分别18/14/18回归通过**；没有将断言、进程、文档或旧117项静态检查算为新增测试。

交付入口：[实验与复现](../experiments/p0-06/README.md)、[验证矩阵](./p0-06-host-verification.md)、[IPC契约](./p0-06-ipc-contract.md)、[生命周期](./p0-06-runtime-lifecycle.md)、[架构与技术栈](./p0-06-architecture-findings.md)。[最终15项机器证据](../experiments/p0-06/evidence/suite-20261027T121250322189Z/summary.json)、[交付审计](../experiments/p0-06/evidence/delivery-audit.json)、[原失败索引](../experiments/p0-06/evidence/development-failures.json)均保留。

## 十个验收问题

1. **Rust能可靠管理独立执行进程吗？** 在本轮Windows固定可信profile下可以：正常/失败/超时/重复启动、真实进程崩溃、正常退出、取消/关闭、自有工具树和并发认领都实际测试。核查launcher与实际PID的Job归属；停止后核查Job活动成员0。不能推广为所有阻塞程序、breakaway或恶意插件均可控。
2. **真实Tauri窗口IPC通过了吗？** 通过。Tauri2.12.5 / WebView2 155.0.4283.62真正显示测试窗口，JS invoke→Rust→长度帧→Python C1，执行审批工作流、错误处理、事件读取和关闭。[窗口报告](../experiments/p0-06/evidence/suite-20261027T121250322189Z/test_T15_real_tauri_window_ipc/window/window-report.json)之外，还有Rust桥调用与SQLite终态佐证；不是mock窗口或Rust-only替代。
3. **是否只有一个工作流状态权威？** 是，沿用原Python C1/run.sqlite。Rust不打开业务库、不调度节点、不改终态；IPC receipt仅原命令ACK去重，Agent库仅远端任务事实。原ControllerLock拒绝第二执行器，恢复由原C1完成。
4. **MCP及A2A能由宿主实际调度吗？** 可以，T04/T05分别真实官方SDK stdio MCP工具和独立A2A JSON-RPC任务；受控合成效果也分别在有效批准后才提交。它们不是付费模型、真实账户或任意第三方服务互操作证明。
5. **如何协调关闭？** 正常cancel/suspend→C1保存/关闭数据库→ACK→Rust清理自有Job并等成员0。MCP及其idle子进程随本机树结束；外部Agent由独立监督器拥有，结束本机不能宣布远端已取消。正常宿主EOF/Tauri退出走协调路径，崩溃由Job及持久化恢复兜底。
6. **崩溃后能正确恢复核实吗？** 已确认结果/attempt保留，审批pending不自动批准，未知MCP不重发；已持久化Agent taskId恢复只查原任务，同run/attempt/task且任务数量1。一次真实关闭I/O失败被保留并修正ACK/Job等待顺序；原失败库随后完整性正常。长期/断电/所有磁盘故障未验证。
7. **审批和权限能阻止未批准执行吗？** 在可信执行器profile内成立：角色在Rust后端固定，operator/viewer越权拒绝；C1再检查内容/状态/取消/期限并原子消费。旧指纹、拒绝、重复/取消/重启覆盖；真实合成MCP/Agent未批准前不提交。没有声称能隔离被攻陷前端或不可信同用户Python。
8. **Windows打包风险？** 本机已有MSVC/WebView2和原实验目录；本轮venv48包约82.45 MiB，基础Python约48.24 MiB（排除site-packages等），debug程序体积已测。未建发行安装包/签名/升级，也未证明干净机器/离线/ARM64可用，当前仍依赖原实验源码和catalog闭包。
9. **Python是否值得继续？** 值得继续做受限执行验证，已有原三套18/14/18项独立回归和本轮IPC证据，避免重写状态语义；不宜原样冻结为正式核心。需要收敛派发上下文、存储fail-stop、命令事务、事件背压与发行依赖。TS/Rust替代收益尚无对照执行数据，不能因启动成功便定案。
10. **正式画布集成最缺什么？** 稳定且可版本化的定义校验→固定修订→命令接纳→审批/状态/事件补齐接口，以及干净Windows依赖闭包验证。Vue Flow只编辑Workflow Definition，不能拥有业务状态或把当前单run探针接口直接当正式引擎API。下一轮可围绕这些条件另行开展一条最小画布闭环，本轮不自动开始。

## 变更与保留

新代码、环境、夹具入口、图标、构建文件、数据库、测试和证据全部位于experiments/p0-06；planning新增本轮五份报告；根/研究索引增量更新。原P0-03/P0-04/P0-05源码、Schema、P0-01/P0-02历史报告与原117项检查未改，只有各原套件latest指针按回归正常更新，旧suite不覆盖。

最终审计：8969份历史基线文件无删除或未预期变更；测试源摘要无漂移；99条期望/实际比较全部匹配，82次自有PID检查无存活，30次Job停止核查成员为0。19份导航/报告链接检查无缺失，395份最终文本证据无合成秘密标记泄漏；这些是审计观测数，不增加15项专项的通过数。窗口默认AppData缓存已归档回本轮并改为会话内缓存，修正及最终实际目录证据保留。

依赖来自原可信wheelhouse及Cargo官方registry，Python哈希锁、Cargo.lock、安装/构建日志、许可元数据清单、环境/体积与源摘要可查。缓存离线构建通过不等于干净机器离线分发。使用已有工具链，无提权、无PFT操作、无正式画布、无付费API/真实账户、大模型、不可信插件、Git提交/标签/推送。

L1定义兼容、L2依赖满足才执行、L3不迁移完整环境保持；Linux/macOS只是替代设计空间，尚未运行。工作完成，停止于P0-06。
