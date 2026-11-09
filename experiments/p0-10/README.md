# P0-10 · 本地工作流评测

Windows，已加载 google/gemma-4-e4b，GGUF Q4_K_M，8192 上下文。只访问预配置的 127.0.0.1:1234。默认采样参数与服务端一致，关闭推理模式、流式和 SDK 重试；通常上限 192，截断探针 8。每条请求的完整 user 消息、HTTP 状态、usage 和返回正文见 baseline.json。cache token 未提供。请求耗时是本机 HTTP 往返，未单独测首 Token、纯推理或冷启动。

## 复现

在项目根目录的 PowerShell 执行以下命令。需要本机 v0.1.3 私有运行环境和已保存的 Gemma 连接，已将修复后的 demo/local_models.py 同步到该环境。现有发行 ZIP 未改动。运行标签必须全新，每次保留独立 SQLite 记录。未达预期会以非零退出并保留完整结果。

```powershell
& .\experiments\p0-08\.venv\Scripts\python.exe -B -X utf8 .\experiments\p0-10\evaluate.py myRun
& .\experiments\p0-08\.venv\Scripts\python.exe -B -X utf8 .\experiments\p0-10\evaluate.py myCutoff E01
node .\experiments\p0-10\window.cjs
```

cases.json 固定输入、规则、节点、参考答案和是否需要推理。以 id 关联结果文件中的 rows，route 区分 direct、single 和 tool，repeat 区分重复。每条保留通过标记和失败原因。A02、D03 每路径预先安排两次，其他各一次。历史原始数据集 v1 的 A01 参考期限为“周五”，v1.1 唯一题目改动为“周五前”；输入与提示均未改变。baseline.json 与 after.json 使用完全相同的 v1 数据集哈希及断言。correctedReference.json 为单独校准，保留旧评分。

复用 P0-08 unittest 使用的真实 Session、C1 SQLite、官方 SDK 与现有本机 MCP 服务；Python 只负责枚举案例、计时与断言。Promptfoo 可以运行直接模型对照，但要评分 C1 重启、attempt 和审批仍需同一 Python 测试入口；本轮不增加另一层 provider。借鉴按数据项固定预期、独立 scorer、开发时固定数据的方法。[Promptfoo](https://www.promptfoo.dev/) · [Inspect AI](https://inspect.aisi.org.uk/) · [Langfuse Datasets](https://langfuse.com/docs/evaluation/experiments/datasets) · [n8n Pinning](https://docs.n8n.io/build/work-with-data/pin-and-mock-data/)

## 基线结果

20 个案例、41 条路径/重复观测。34 次真实推理，1205 输入、401 输出 Token。其余是校验或故障路径。没有付费调用。33 条满足冻结断言；8 条差异分别来自期限参考答案 2 条、会议事件误提取 2 条、额外引号 3 条、截断被当作完整结果 1 条。

|案例|实际结果|
|---|---|
|A01|两条路径均保留“周五前”，首次评分误判。修正参考答案后两条新观测均合格。|
|A02、A03|双负责人及无任务提取通过；A02 两轮均通过。|
|A04|直接与 C1 均将“周二开会”多列为任务；字段结构合法，但语义不符。|
|B01–04|空数组通过；数字负责人、重复 JSON 键、缺少 due 分别被拒绝，未派发输出。|
|C01–03|三条路径均正确。真实 MCP Echo 的输入与模型输出、最终结果逐字匹配。|
|C04|三条路径均多了引号；MCP 完整保留模型原文，严格格式评分失败。|
|D01–04|均通过；D03 两轮均通过。真实 HTTP 请求体与直调配置逐项核对，均只有一条用户消息。D02 增加反例后输入从17增至27 Token。|
|E01|截断反例实证，见下节。|
|E02|模型审批期间取消，模型零请求，下游零派发。|
|E03|使用自有 HTTP 夹具模拟响应丢失，原 run 恢复为 unknown，未向夹具重发。|
|E04|129 字符实参超出 Echo 工具的 128 字符约束，在调用工具前失败。|

耗时按 A、C、D 的真实任务统计。总耗时从创建客户端或 Session 开始，至取得结果；不含 GUI、关闭进程及清理。额外耗时按**同一次观测**的总耗时减生成 POST 往返求中位数，包含本机准备、模型发现、SQLite、节点及适用时的 MCP 开销。直接路径固定在每组首位，重复提示可能受服务端缓存或预热影响，不从跨路径耗时差判断模型变快。

|路径|样本|输入/输出 Token 合计|总耗时中位数|生成 POST 之外中位数|
|---|---:|---:|---:|---:|
|直接 SDK|14|529 / 192|200.73 ms|2.63 ms|
|AOS 单模型|14|529 / 173|128.44 ms|49.22 ms|
|AOS 加 MCP|4|87 / 20|1729.67 ms|1659.16 ms|

仅比较 C01–04，直接、单模型、加 MCP 的总耗时中位数分别为 203.14、130.95、1729.67 ms。每次模型节点实际发出一次模型列表 GET 和一次生成 POST；工具没有再交回模型。后者通过真实 stdio 子进程完成，当前数据未将启动、发现、握手分别计时。没有证据支持改调度器或删提示词。

## 修复、冗余与权限

E01 输入要求列出100项，上限8。直接服务与 C1 均收到 finish_reason=length 及非空片段。原适配器只在正文为空时报错，基线 C1 将残文发布到输出端口。demo/local_models.py 改为保留已返回 usage 并抛出不可重试的 LOCAL_OUTPUT_TRUNCATED。相同评分下 after.json 中模型失败，最终输出跳过，模型 POST 仍仅一次。B03、D03 同时复测。工作台“问题”页显示节点与原因；可调大最大输出 Token 或缩小请求后手动发起新运行。本机已同步适配器，未重打包。

真实 Tauri 点击运行并紧接 Ctrl+Enter 后只有一份 run 和一个模型 attempt，失败未派发输出，见 window.json、cutoff.png。另对 D01 的模型输出故意连接 JSON 校验并再次 drive 原终态，模型仅一次 POST，见 downstream.json。恢复与再次手动创建新 run 分开处理。重新运行 P0-03 的条件分支测试，被跳过的模拟适配器零调用；重新运行 P0-04 的真实 MCP 审批测试，覆盖待批、拒绝、过期、取消、修改内容及重复批准。证据目录分别为 experiments/p0-03/evidence/p010-branch-1794097920369544500 和 experiments/p0-04/evidence/p010-permission-1794098004710896600。以上是限定场景证据，未泛化到所有界面并发与外部工具。

## 固定输出实验

C1 可恢复同一 run，普通新运行未提供跨修订的节点缓存。preview.py 只读既有 A02 SQLite 快照，核对校验和、模型 attempt、版本、绑定、输入配置及产物摘要后，重新校验 JSON 并执行修改后的下游“按姓名排序”投影。运行命令与 evaluate.py 相同，脚本改为 preview.py，无参数。预览使用 pinSource.json 定位本机固定记录。全量来源运行 441.61 ms、61+43 Token；纯投影用时 3.08 ms（不含读取快照和解释器启动），无需模型请求，结果为李四、王五。preview.json 记录五种变更拒绝复用。该实验仅允许固定案例和纯函数，未向正式执行器增加注入接口，未验证任意图的局部重算。通用化前需设计跨修订依赖键、权限与环境身份及可信来源，并独立验证失效规则。

## 下一步

1. 对真实 MCP 子进程的启动、握手、工具发现与调用分别计时，验证复用会话的收益与退出清理。
2. 用小规模带标注的会议记录区分事件、分工、期限与严格格式，再对提示词做同输入对照。
3. 测量逐次模型发现的代价、模型卸载和连接变更行为，再决定是否采用有界缓存。

