# P0-07 受限可编辑定义 IPC

2026-10-27。实施前审查确认 P0-06 `load{builtin}` + 单 run manifest 不足以接收编辑图。本轮在隔离目录做下述必要扩展，原 P0-06 文件不改；没有新增调度器、改变 C1 权威或大改原 Schema。

## 固定边界

内部继续 `aos-local/0.1` 封套，`v/kind/id/op/body`，同 id 响应；4 字节大端长度 + UTF-8 JSON，1–262144 字节，重复键/非有限数/非法帧拒绝。Rust/Tauri main capability 验证来源、尺寸和固定角色，Python 再精确检查 body、原 Schema、节点/适配器能力和 DAG。启动5秒、写入3秒、响应20秒；超时不产生业务成功。stderr 与协议 stdout 分离。沿用 P0-06 权限、Job 和协调关闭，不开放 shell/fs 通用插件。

协议封套未改变；`health.executorVersion=p0-07.1` / `buildProfile=fixed-trusted-p07` 标识本轮 API profile。P0-06 的旧 builtin body 不在本轮 profile 自动接受；不是承诺已做跨版本通用协商。

| op / body | 本轮语义 |
| --- | --- |
| health `{}` | 实际执行器身份、C1 权威、锁定 catalog、标签、默认参数与两条原格式合成文档；非远程目录 |
| load `{action:validate,workflow}` | 以原 Schema/Contracts 校验，固定目录和环境要求、≤64节点/128边、无子图；返回 token、workflowDigest、revision |
| create `{token}` | token 绑定精确 workflow 和本轮执行 profile 摘要；复制定义/请求/绑定后由原 C1 创建 UUID run；不能用在途草稿替换已启动定义 |
| load `{action:save,name,document}` | name 仅 1–48 ASCII字母数字`_-`，限定本实验 workspace；document={workflow,layout}；原 Schema 检查后保存，允许不完整/未知草稿，**不授予执行权** |
| load `{action:open,name}` | 读取同一固定目录里的文档；没有任意路径参数 |
| load `{action:run-definition}` | 返回 C1 已固定的定义，供重启后投影原 run；不拿当前草稿猜测原版本 |
| recover `{}` | 读该宿主会话 latest 指向的原 run，核对实现 profile 摘要和原 C1 identity，沿用原 Store 单所有者锁；在途结果保守 unknown |
| status / events / cancel | 原 C1 snapshot、持久事件 after 游标、原取消控制；事件每页16项，runId/seq 去重补齐 |
| approvals `{}` | 原 pending 记录加从 C1 固定 spec/依赖得到的 action、inputs、operation/revision；重新计算指纹 verified；只是审阅投影，不是 grant |
| approve `{approvalId,fingerprint,decision}` | Rust approver + 原 C1 状态/期限/内容/取消核验 + 原子消费；原 MCP 适配仍在实际 wire 边界复核 |

草稿布局版本 `aos-layout/0.1` 的 positions 是独立视图数据，数值有界；工作流本体保持 P0-02 `0.1.0-draft.1`，节点精确 `0.1.0`。环境由后端生成，只允许两个自有合成 MCP 工具、固定程序和逻辑连接，不从工作流/消息接受 executable、脚本、凭据、URL 或系统句柄。原节点策略仍由 Contracts 检查；不支持的控制语义明确拒绝。

## 接纳、恢复与身份

一次宿主会话只开放一个活动 C1 run；成功/失败/取消后可新建不同 run 目录，所有旧库保留。unknown 必须核实，本轮直接拒绝替代创建，不能靠重启自动重放。新 session 是独立实验身份，不是消解旧副作用的方法。多个执行器认领同 run 仍由原 ControllerLock 拒绝。

每个 run 保存原 workflow/request/environment、profile 摘要、SQLite 和事件。create/approve/cancel 原 receipt 账本仍只缓存 ACK，不是业务权威。重复 create id 返回原 ACK，变 body 拒绝；C1 与 receipt 不是跨库 exactly-once。创建中断/未知 ACK 要 recover，不可换 id 盲重发。profile/代码漂移恢复失败关闭，不建立替代业务终态。

本轮为长时间状态轮询收敛了内存 id 账本：约4000项时淘汰最早只读 id；写命令 id/原持久 receipt 保留。只读请求身份冲突检测只保证保留窗口内，读结果不缓存；写 id 上限4096仍明确拒绝。4105次真实 C1 snapshot 读取的 Python endpoint 测试覆盖此边界，未冒称这项也是4105次真实窗口 IPC。

保存主编辑文档使用临时文件替换；独立 workflow/layout 文件是方便消费的导出。三文件不构成跨文件事务，重新打开以 `.document.json` 为准。并发多窗口草稿覆盖、编辑器 CAS、目录联结/同用户恶意进程、磁盘故障穷举尚未验证。

## 数字、事件和秘密

独立 SQLite 核对曾发现 Rust 默认 JSON 解析把少量 finishedAt 改动约 0.24μs。实际反例及失败核对保存在 `audit-first-state-comparison.json`；本轮启用 serde_json `float_roundtrip`，不改时间或放宽比较。最终 IPC 整份快照与 SQLite 严格相等。不是任意大整数/Decimal/跨语言完整数值域证明；当前参数有界，未来需显式数值范围。

Vue 不用日志或计时器生成节点终态；300ms仅轮询实际 C1。断连后保留最后确认快照，顶部明确“待核实”，不能显示虚假完成。事件落后时从原库补齐，不把通知队列当权威。当前≤64节点的有限合成图不是压力/背压证明。

证据只含合成数据；桥记录会保存定义/输出/审批指纹，正式真实模型接入前必须设计字段脱敏和保留策略。Job/stdio/capability 不是完整 OS 沙箱。正常启动不开调试端口；loopback CDP、固定 resize/zoom 和 crash-worker 仅 test 模式验收使用。
