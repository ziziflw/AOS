# AOS-LT01 · 模拟订单综合审计

从本目录的 workflow.json 加载 P0-02 DAG，配套 catalog.json 在既有目录中加入专用节点，并复用 P0-03 控制节点描述、C1/SQLite、P0-08 ModelRuntime 和本机已安装的 Gemma 适配器。原桌面目录只支持固定节点集合，本轮通过隔离命令行入口执行。未将 LT01 注册到 Tauri。LT01 的错误可在各运行目录中的 snapshot.json、events.json 与故障日志查看，未取得工作台直接查看本任务错误的验收证据。

## 任务与分工

只读 MCP 服务仅暴露 read_dataset，参数只能选 30 或 200，读取该规模目录中的四张 CSV 与一份 JSON，不接受路径或写命令。官方 MCP SDK 执行 stdio 握手、发现和调用。C1 的读取、格式校验、金额/日期/大小写标准化和跨表对账均为不同节点。数据节点将中间 JSON 写入运行私有内容寻址目录，在图中传递带摘要与大小的 FileReference；每次读取重新检查。业务金额以整数分比较。重复相同行只计一次，冲突 ID 拒绝。非法支付金额不计入支付额，保留原记录作为异常证据。未发货和多条物流作为候选。无订单归属直接报错。

join → decision → core.condition 以投诉是否存在选择路径。有投诉时仅传投诉文字、工单 ID 和相关物流状态给模型。check 校验 JSON Schema、唯一键及工单覆盖，再交由 C1 按 run、输入和操作身份暂停审批。无投诉的另一条路径在本轮两次主运行中均跳过，未独立测试无投诉的数据集。汇合后由输出节点返回审计事实引用和获批建议，文件导出器从该结果生成 CSV、JSON 与 Markdown。没有支付、物流或退款写操作。原始输入不能访问 oracle；参考答案来自种子生成时独立记录的场景与期望数值，评分器单独读真实 SQLite 和最终导出物。没有部署额外评测服务。借鉴了环境状态验收、任务夹具与独立评分、开发时固定数据。[AppWorld](https://appworld.dev/) · [Terminal-Bench](https://github.com/harbor-framework/terminal-bench) · [Inspect AI](https://inspect.aisi.org.uk/) · [n8n](https://docs.n8n.io/build/work-with-data/pin-and-mock-data/)

## 复现

在项目根目录的 PowerShell 运行。依赖项目现有 P0-08 Python 环境、已安装 v0.1.3 私有 C1 代码和 127.0.0.1:1234 上已加载的 google/gemma-4-e4b。无需模型下载。本任务的 CLI 专用于自有合成节点。种子为 17613 加订单数。两套数据各含十项异常，适合检查输入规模增长时的模型开销；未测试高投诉密度或吞吐极限。

```powershell
$p = (Resolve-Path experiments/p0-08/.venv/Scripts/python.exe).Path
Set-Location experiments/lt01
& $p -B -X utf8 dataset.py
& $p -B -X utf8 flow.py prepare
& $p -B -X utf8 flow.py trial30 --size 30
```

trial30 必须为新标签。暂停后查看控制台的具体建议与 approval ID，保存暂停快照供独立评分，然后退出进程。仅在人工核准该次运行后重启以下命令，替换审批 ID。200 单使用另一新标签和 --size 200。每次运行最多一次生成，并发 1，模型输入准入 2048、输出上限 384 Token，工作流硬预算 4096 Token；SDK 与 C1 禁用生成重试。默认工作流期限与审批 TTL 30 分钟，可在首次运行与恢复时传入相同 --minutes。首次与恢复时的代码、输入和执行定义须一致。

```powershell
Copy-Item runs/trial30/snapshot.json runs/trial30/paused.json
& $p -B -X utf8 flow.py trial30 --size 30 --resume --approve <该次审批ID>
& $p -B -X utf8 report.py trial30
& $p -B -X utf8 compare.py trial30 30
& $p -B -X utf8 faults.py
& $p -B -X utf8 score.py trial30 30
```

faults.py 为各次挑战创建独立目录，challenges.json 指向最近一次挑战证据。score.json 将程序化指标分为数据35、异常与证据25、恢复与执行20、效率10、交付物10；安全阻断标记独立于数值。基础与完整版本共享在 200 单数据上测得的故障项。评分限定本夹具和 CLI 运行环境，不包括桌面集成与广泛的语义质量保证。

## 本轮结果

|数据|对账与模型|生成输入/输出 Token|模型 POST|C1 全程|扣除审批/离线时间|
|---|---|---:|---:|---:|---:|
|基础 30 单|10 项异常候选，2 张投诉|139 / 128|1.209 秒|49.421 秒|1.919 秒|
|完整 200 单|10 项异常候选，2 张投诉|139 / 123|1.150 秒|47.605 秒|1.938 秒|

每条运行一次真实生成、一次 MCP 调用、一次审批。基础 T15/T22、完整 T23/T27，分别建议核实签收冲突和驿站位置。用户在对话中明确批准两份报告，经绑定审批 ID 写入原运行，恢复后已完成的节点没有重做。两份业务输出在 runs/basic/results 与 runs/full/results；对应父目录保留直调结果、暂停快照、C1 SQLite、评分和中间节点证据。

直调使用 C1 已生成的同一消息、相同模型与参数，只评建议子任务。30 单直调 139/124 Token、1.721 秒，200 单直调 139/129 Token、1.805 秒，工单分类均为 2/2。AOS 两份也均为 2/2。直调未重做对账、MCP、审批、导出，无法据此推断端到端加速。扣除审批后，同一次 AOS 内的 POST 以外用时约 0.710 / 0.788 秒，含 MCP、模型发现、验证及落库。没有取得服务端缓存 Token。全程指标不含 Python 解释器启动和导出报告的时间。

基础初次运行 base1 在图验证时拒绝缺少的 core.condition 描述，尚未创建业务运行。LT01 改为导入已有 P0-03 描述。base2 真正调用了 Gemma，返回的合法 JSON 被单个 Markdown json 围栏包裹，原严格解析失败、未到达审批。唯一的模型输出兼容调整是剥离恰好包住整条消息的这一种围栏，然后执行原有 Schema 与业务校验。原始失败状态保留，用完全相同的响应离线复验可通过，无新增生成；附加解释、重复键和缺失工单依然失败。见 format-check.json。失败链还暴露了主错误后可能附加 EXCLUSIVE_JOIN_COUNT 的诊断噪声，未修改 C1。

## 故障和边界

- timeout 在客户端发送边界注入 SDK 读超时，未实际传输生成 POST，也未伪造服务 usage。C1 保留 unknown 与预算。
- mcp-stop 在真实 stdio 服务处理 read_dataset 时退出，C1 记录 MCP_READ_FAILED，不进入模型。
- bad-port 在规范化完成后返回非法数字，FileReference 端口拒绝，未进入跨表关联。
- 两份批准均在退出第一个 Python 进程后由新进程恢复；SQLite 的 run/attempt 身份保持。
- crash 在 join 节点派发后通过真实进程退出（74）中断。重新启动后已提交上游不重算，处理中节点保守标为 unknown，没有自动重启整单。
- lost 在真实 LM Studio 已返回回复后向适配器注入响应丢失，恢复前后仅一次生成，C1 保留 unknown。可见的服务真实回复位于故障实验测量侧，执行器没有使用该旁路结果确认业务终态。
- 原桌面未注册 LT01 目录和运行记录，未验证 LT01 故障在 Tauri 中可见。未知项核实与恢复后的纯节点安全重算仍需独立设计。

架构后续优先项为只读打开实验运行的桌面诊断、区分可验证纯节点与可能有副作用的中断处理，以及在失败链中突出首个具体错误并折叠下游连带错误。

