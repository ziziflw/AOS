# 技术资料总索引

核验日期：2026-10-24（Asia/Shanghai）。统计单位为独立资料记录，不是产品数量、网页打开次数或实验数。

截至P0-02共57条记录：55条已从可访问一手正文核验，2条正文访问失败。P0-01原有48条（46/2）保留，P0-02新增9条；本轮只完成本地静态契约检查，真实模型/MCP/Agent与跨OS运行实验仍未执行。“已核实”只表示下述文档内容有一手支持。

P0-03增量：新增S58–S60，共60条（58条正文核验、2条访问失败）；实际执行证据另见[运行验证](../planning/p0-03-runtime-verification.md)，不与资料数量混算。历史P0-02统计和条目保留。

P0-04增量：新增S61–S63，共63条（61条正文核验、2条访问失败）。本轮复核S36的Job Objects、S44/S45的2025-11-25生命周期/传输和MCP工具/取消固定规范；实际SDK/进程结果见[P0-04验证](../planning/p0-04-mcp-verification.md)，旧“尚未验证”字段保留为历史边界，不能覆盖本轮限定证据。

P0-05增量：新增S64，合计64条（62正文核验/2访问失败）；复核S53/S54/S55的A2A规范/线版本/固定SDK候选及许可、幂等和取消要求。具体实际A2A、合成行为与工作流证据见[P0-05验证](../planning/p0-05-agent-verification.md)，不以资料数量替代测试；原规范站版本标识差异和历史未验证字段保留。

P0-06增量（2026-10-27）：新增S65，合计65条（63正文核验/2访问失败），复核S36/S38/S39的Job/Tauri权限与分发边界；[实际15项宿主/窗口验证](../planning/p0-06-host-verification.md)及原18/14/18回归单独统计，旧研究记录不覆盖。

<a id="categories"></a>
## 分类导航

- [R01 · 01-visual-editor](./01-visual-editor/README.md)
- [R02 · 02-node-contracts](./02-node-contracts/README.md)
- [R03 · 03-execution-engine](./03-execution-engine/README.md)
- [R04 · 04-model-adapters](./04-model-adapters/README.md)
- [R05 · 05-tool-agent-protocols](./05-tool-agent-protocols/README.md)
- [R06 · 06-observability-evaluation](./06-observability-evaluation/README.md)
- [R07 · 07-security-permissions](./07-security-permissions/README.md)
- [R08 · 08-desktop-runtime](./08-desktop-runtime/README.md)
- [R09 · 09-competitors](./09-competitors/README.md)
- [R10 · 10-feasibility-experiments](./10-feasibility-experiments/README.md)

## 记录维护规则

资料ID永久保留；失效链接不删除历史，补记新URL、版本、核验日期和差异。滚动文档不代表已锁定软件版本；不得把选项页、示例或产品宣传视为目标安装环境实测。每条的“未验证”保留待验证状态；复用理由是研究建议，不是架构决定。

<a id="s01"></a>
### S01 · Vue Flow 概览

- 分类：R01/R08。
- 官方来源：[Vue Flow 概览](https://vueflow.dev/guide/)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：页面标示 v1.48.2。
- 核实内容/访问结果：自定义节点、边、拖拽与视口组件。
- 本项目关联与复用判断：画布候选；复用交互基础，执行语义需自定。
- 尚未验证：大图性能、可访问性、宿主集成。
- 后续实验：E01。

<a id="s02"></a>
### S02 · Vue Flow Handles

- 分类：R01/R02。
- 官方来源：[Vue Flow Handles](https://vueflow.dev/guide/handle.html)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：同站 v1.48.2。
- 核实内容/访问结果：source/target Handle 构成连线端点；支持多个端口与连接校验。
- 本项目关联与复用判断：复用端口交互；类型规则由定义模块提供。
- 尚未验证：动态端口重建后的旧连线处置。
- 后续实验：E01。

<a id="s03"></a>
### S03 · Vue Flow Actions

- 分类：R01。
- 官方来源：[Vue Flow Actions](https://vueflow.dev/typedocs/interfaces/Actions.html)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：同站 v1.48.2。
- 核实内容/访问结果：toObject 导出图元素及视口供保存与重载。
- 本项目关联与复用判断：复用序列化入口，项目文件格式另定。
- 尚未验证：导出对象中自定义数据及迁移兼容。
- 后续实验：E01。

<a id="s04"></a>
### S04 · ComfyUI 节点

- 分类：R01/R09。
- 官方来源：[ComfyUI 节点](https://docs.comfy.org/basic-concepts/nodes)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：滚动文档；软件版本未固定。
- 核实内容/访问结果：节点包含参数、类型化连接及运行/错误/缺失状态。
- 本项目关联与复用判断：参考节点状态和缺失组件提示；不直接复用完整产品。
- 尚未验证：跨版本自定义节点和子工作流语义。
- 后续实验：E01/E04。

<a id="s05"></a>
### S05 · ComfyUI 自定义节点与缓存

- 分类：R02/R03。
- 官方来源：[ComfyUI 自定义节点与缓存](https://docs.comfy.org/custom-nodes/backend/server_overview)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：Python 后端接口文档；未锁软件版本。
- 核实内容/访问结果：INPUT_TYPES、RETURN_TYPES 等描述接口；IS_CHANGED 影响缓存判定。
- 本项目关联与复用判断：参考动态参数和缓存失效；不移植整套执行逻辑。
- 尚未验证：外部文件变化、非确定模型调用的缓存安全性。
- 后续实验：E01/E05。

<a id="s06"></a>
### S06 · ComfyUI Workflow JSON

- 分类：R01/R02。
- 官方来源：[ComfyUI Workflow JSON](https://docs.comfy.org/specs/workflow_json)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：格式 v1.0，含 legacy v0.4。
- 核实内容/访问结果：以 JSON Schema 描述节点、连线、分组、版本字段。
- 本项目关联与复用判断：参考格式演进；自主设计项目契约。
- 尚未验证：画布文件与服务端执行请求的转换。
- 后续实验：E01。

<a id="s07"></a>
### S07 · Langflow 可视化编辑器

- 分类：R01/R09。
- 官方来源：[Langflow 可视化编辑器](https://docs.langflow.org/concepts-overview)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：页面标示 1.13.x。
- 核实内容/访问结果：连接模型、数据源、Agent、MCP；Playground 检查工具输出；JSON 导出。
- 本项目关联与复用判断：参考组件调试与分享；完整复用需另评估部署。
- 尚未验证：局部运行边界、迁移及 Desktop 功能差别。
- 后续实验：E01/E02/E03。

<a id="s08"></a>
### S08 · n8n 流程逻辑

- 分类：R01/R03。
- 官方来源：[n8n 流程逻辑](https://docs.n8n.io/build/flow-logic.md)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：滚动文档；未锁软件版本。
- 核实内容/访问结果：条件、合并、循环、等待、子工作流和错误处理均有官方入口。
- 本项目关联与复用判断：参考控制节点语义；嵌入前另查许可和运行依赖。
- 尚未验证：可视并列分支的真实并行程度。
- 后续实验：E04/E05。

<a id="s09"></a>
### S09 · n8n 局部执行

- 分类：R01/R09。
- 官方来源：[n8n 局部执行](https://docs.n8n.io/build/understand-workflows/understand-executions/types-of-executions.md)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：滚动文档。
- 核实内容/访问结果：局部执行可带动所需前置节点；固定数据仅用于手动执行，生产忽略。
- 本项目关联与复用判断：参考调试样本与正式运行区分。
- 尚未验证：大分支数据量限制和副作用重放。
- 后续实验：E04/E05。

<a id="s10"></a>
### S10 · n8n 工作流历史

- 分类：R01/R09。
- 官方来源：[n8n 工作流历史](https://docs.n8n.io/build/manage-workflows/view-change-history.md)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：滚动文档；套餐政策快照。
- 核实内容/访问结果：可查看/恢复历史；完整历史限 Enterprise，其他保留窗口有别。
- 本项目关联与复用判断：参考版本回退；不假定所有部署享同一能力。
- 尚未验证：实际部署版本与套餐权益。
- 后续实验：E01。

<a id="s11"></a>
### S11 · Dify Workflow Studio

- 分类：R01/R09。
- 官方来源：[Dify Workflow Studio](https://dify.ai/workflows)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：产品页；未锁部署版本/版别。
- 核实内容/访问结果：官方描述分支、循环、人工输入、单节点调试、DSL 和发布历史。
- 本项目关联与复用判断：参考交互和产品能力；产品声明不能证明特定自部署版本行为。
- 尚未验证：社区版、企业版、云版能力对齐和恢复边界。
- 后续实验：E01/E04/E06。

<a id="s12"></a>
### S12 · Dify 1.5.0 调试说明

- 分类：R01/R06。
- 官方来源：[Dify 1.5.0 调试说明](https://dify.ai/blog/dify-1-5-0-real-time-workflow-debugging-that-actually-works)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：1.5.0；文章 2025-06-25。
- 核实内容/访问结果：文章说明 Last Run 保存节点输入输出并可复用变量进行单步调试。
- 本项目关联与复用判断：参考局部重跑与变量检查；是历史版本的一手说明。
- 尚未验证：当前版本失效规则及跨重启保留情况。
- 后续实验：E01/E05。

<a id="s13"></a>
### S13 · Node-RED Context

- 分类：R03/R09。
- 官方来源：[Node-RED Context](https://nodered.org/docs/user-guide/context)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：滚动文档；提及 0.19/0.20 历史功能。
- 核实内容/访问结果：有 node/flow/global 作用域；默认内存；文件存储默认缓存后每30秒写出。
- 本项目关联与复用判断：参考状态作用域；不能当作任务检查点承诺。
- 尚未验证：崩溃窗口、运行事件与上下文的一致性。
- 后续实验：E05。

<a id="s14"></a>
### S14 · Node-RED Subflows

- 分类：R01/R02。
- 官方来源：[Node-RED Subflows](https://nodered.org/docs/user-guide/editor/workspace/subflows)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：滚动文档。
- 核实内容/访问结果：子流程最多一个输入、多个输出，可暴露实例参数并设置模块版本。
- 本项目关联与复用判断：参考封装；其消息端口与本项目类型端口并非天然相同。
- 尚未验证：多输入汇合及嵌套边界。
- 后续实验：E01/E04。

<a id="s15"></a>
### S15 · Node-RED Projects

- 分类：R01/R09。
- 官方来源：[Node-RED Projects](https://nodered.org/docs/user-guide/projects/)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：滚动页含0.18预览措辞；不能据此认定当前状态。
- 核实内容/访问结果：Projects 使用 Git 管理流程和依赖，编辑器可查看差异与历史。
- 本项目关联与复用判断：参考工作流版本管理设计；本轮不启用或操作 Git。
- 尚未验证：当前开关默认值、凭据迁移体验。
- 后续实验：E01。

<a id="s16"></a>
### S16 · JSON Schema Draft

- 分类：R02。
- 官方来源：[JSON Schema Draft](https://json-schema.org/draft/2020-12)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：2020-12；页面列发布日2022-06-16。
- 核实内容/访问结果：定义核心、校验和元数据词汇；format 注解与断言分开。
- 本项目关联与复用判断：复用规范/验证器候选；UI布局及图语义仍需设计。
- 尚未验证：不同语言验证器一致性与供应商支持子集。
- 后续实验：E01/E02。

<a id="s17"></a>
### S17 · LangGraph 概览

- 分类：R03/R09。
- 官方来源：[LangGraph 概览](https://docs.langchain.com/oss/python/langgraph/overview)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：Python 滚动文档；未锁包版本。
- 核实内容/访问结果：面向有状态、长任务的编排；包含持久化、流式与人工介入。
- 本项目关联与复用判断：优先评估执行能力复用；无需先采用整套 LangChain。
- 尚未验证：动态画布编译、Python/JS接口差异与桌面部署成本。
- 后续实验：E04/E05/E06。

<a id="s18"></a>
### S18 · LangGraph Persistence

- 分类：R03。
- 官方来源：[LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：原 durable-execution 入口已重定向。
- 核实内容/访问结果：checkpointer 保存 thread 图状态，store 保存跨 thread 应用数据。
- 本项目关联与复用判断：参考检查点和长期数据分离。
- 尚未验证：选定后端的落盘、崩溃一致性；内存示例不具磁盘持久性。
- 后续实验：E05。

<a id="s19"></a>
### S19 · LangGraph Interrupts

- 分类：R03/R07。
- 官方来源：[LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：滚动文档；未锁包版本。
- 核实内容/访问结果：interrupt 暂停并等待恢复；恢复重跑节点，前置副作用须幂等。
- 本项目关联与复用判断：复用暂停候选，参考审批与副作用拆分。
- 尚未验证：多并发审批、版本升级后的恢复及真实取消。
- 后续实验：E05/E06。

<a id="s20"></a>
### S20 · Temporal Workflow Execution

- 分类：R03。
- 官方来源：[Temporal Workflow Execution](https://docs.temporal.io/workflow-execution)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：滚动文档；未锁 SDK/Service 版本。
- 核实内容/访问结果：基于事件历史重放恢复 Workflow；涉及 Service 和 Worker。
- 本项目关联与复用判断：参考成熟持久执行；是否复用取决本地部署负担。
- 尚未验证：动态定义映射、活动重试副作用和断网运行体积。
- 后续实验：E04/E05/E07。

<a id="s21"></a>
### S21 · SQLite WAL

- 分类：R03/R08。
- 官方来源：[SQLite WAL](https://www.sqlite.org/wal.html)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：WAL 自3.7.0；本轮未选引擎版本。
- 核实内容/访问结果：可读写并行但同一时刻单写者；要求同主机，不适用于网络文件系统。
- 本项目关联与复用判断：复用本地存储候选；恢复语义仍由执行层负责。
- 尚未验证：同步级别、崩溃/断电、WAL检查点及所选版本已知问题。
- 后续实验：E05/E07。

<a id="s22"></a>
### S22 · Vercel AI SDK Settings

- 分类：R04。
- 官方来源：[Vercel AI SDK Settings](https://ai-sdk.dev/docs/ai-sdk-core/settings)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：页面标示 v7；未锁具体包。
- 核实内容/访问结果：统一调用选项并保留供应商差异；不支持的通用选项会产生 warnings。
- 本项目关联与复用判断：TS适配候选；界面必须展示实际支持而非统一滑块。
- 尚未验证：具体模型、结构化输出子集、流式取消和usage。
- 后续实验：E02。

<a id="s23"></a>
### S23 · LiteLLM Router

- 分类：R04。
- 官方来源：[LiteLLM Router](https://docs.litellm.ai/docs/routing)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：滚动文档；未锁 SDK/Proxy 版本。
- 核实内容/访问结果：跨部署负载、超时、重试、冷却及fallback；分布式追踪可用Redis。
- 本项目关联与复用判断：Python/网关候选；先评估 SDK 以减少基础服务。
- 尚未验证：桌面最小依赖、预算准确性和重试叠加。
- 后续实验：E02/E04。

<a id="s24"></a>
### S24 · LiteLLM Input Params

- 分类：R04。
- 官方来源：[LiteLLM Input Params](https://docs.litellm.ai/docs/completion/input)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：滚动文档；模型示例非全局承诺。
- 核实内容/访问结果：get_supported_openai_params 按模型与供应商查询参数支持。
- 本项目关联与复用判断：参考能力发现；不是未来API兼容性的保证。
- 尚未验证：API版本、账户权限和供应商新增能力同步。
- 后续实验：E02。

<a id="s25"></a>
### S25 · vLLM Online Serving

- 分类：R04。
- 官方来源：[vLLM Online Serving](https://docs.vllm.ai/en/latest/serving/online_serving/)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：latest 滚动文档；旧入口跳转。
- 核实内容/访问结果：兼容多类HTTP接口；Chat依赖chat template，部分参数忽略/不支持。
- 本项目关联与复用判断：作为现有本地或局域网推理端点候选。
- 尚未验证：原生Windows部署可行性、硬件条件、具体模型行为；本轮不部署。
- 后续实验：E02。

<a id="s26"></a>
### S26 · Gemini 模型目录

- 分类：R04。
- 官方来源：[Gemini 模型目录](https://ai.google.dev/gemini-api/docs/models)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：滚动模型目录；不锁具体实验模型。
- 核实内容/访问结果：官方目录区分模型与端点，并链接各自说明。
- 本项目关联与复用判断：第二供应商候选；模型清单不等于完整能力Schema。
- 尚未验证：精确模型参数、限额、结构化输出和地区账户可用性。
- 后续实验：E02。

<a id="s27"></a>
### S27 · Claude API Versions

- 分类：R04。
- 官方来源：[Claude API Versions](https://platform.claude.com/docs/en/api/versioning)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：2026-10-21 与2023-06-01并列。
- 核实内容/访问结果：版本头影响行为；2026-10-21移除temperature、top_p、top_k并拒绝传入。
- 本项目关联与复用判断：直接证明能力须按API版本记录；不可统一假定支持采样参数。
- 尚未验证：实际账户/渠道的版本与选定SDK兼容。
- 后续实验：E02。

<a id="s28"></a>
### S28 · MCP Tools

- 分类：R05/R02。
- 官方来源：[MCP Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：2025-11-25；不声称是全局最新版。
- 核实内容/访问结果：tools能力、发现/调用、inputSchema及可选outputSchema/structuredContent。
- 本项目关联与复用判断：复用协议SDK候选；工具权限由本地策略强制。
- 尚未验证：服务端遵从程度、工具变化和输出校验。
- 后续实验：E03/E06。

<a id="s29"></a>
### S29 · MCP 安全建议

- 分类：R05/R07。
- 官方来源：[MCP 安全建议](https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：2025-11-25路径；旧规范路径重定向。
- 核实内容/访问结果：覆盖token passthrough、SSRF、会话劫持与本地服务被篡改等风险。
- 本项目关联与复用判断：参考威胁模型和最小权限；不将协议当作OS沙箱。
- 尚未验证：本地stdio防护与远端认证实现。
- 后续实验：E03/E06。

<a id="s30"></a>
### S30 · A2A Specification

- 分类：R05。
- 官方来源：[A2A Specification](https://a2a-protocol.org/latest/specification/)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：latest滚动页；含1.0和0.3兼容说明，未固定发布tag。
- 核实内容/访问结果：定义Agent Card、任务、消息、产物、查询/取消及版本协商。
- 本项目关联与复用判断：Agent委托适配候选；保留独立任务生命周期。
- 尚未验证：规范快照与SDK版本、取消可达性、异步结果恢复。
- 后续实验：E05；后续独立A2A契约实验待立项。

<a id="s31"></a>
### S31 · OpenTelemetry Traces

- 分类：R06。
- 官方来源：[OpenTelemetry Traces](https://opentelemetry.io/docs/concepts/signals/traces/)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：滚动概念文档；未锁SDK/语义约定版本。
- 核实内容/访问结果：Trace/Span上下文、属性、事件、链接表达执行及因果关系。
- 本项目关联与复用判断：复用追踪标准；业务恢复状态独立存储。
- 尚未验证：跨进程关联、采样、GenAI语义稳定性及脱敏。
- 后续实验：E04/E05/E07。

<a id="s32"></a>
### S32 · Langfuse Overview

- 分类：R06。
- 官方来源：[Langfuse Overview](https://langfuse.com/docs)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：页面有v4公告；未锁SDK/部署版本。
- 核实内容/访问结果：提供traces、成本延迟观察、prompt版本与评估功能；可自部署。
- 本项目关联与复用判断：参考评估工作台；可选导出接入，完整本地栈负担另评。
- 尚未验证：离线最小部署、数据保留、各供应商usage覆盖。
- 后续实验：E02/E07。

<a id="s33"></a>
### S33 · OWASP Prompt Injection

- 分类：R07。
- 官方来源：[OWASP Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：LLM01:2025。
- 核实内容/访问结果：区分直接和间接注入；外部资料可影响模型，RAG不彻底消除风险。
- 本项目关联与复用判断：参考攻击面；自主实现程序侧授权和输出不可信边界。
- 尚未验证：具体防护对多轮工具链的效果。
- 后续实验：E06。

<a id="s34"></a>
### S34 · Windows DPAPI

- 分类：R07。
- 官方来源：[Windows DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：Win32 API；未指定OS构建。
- 核实内容/访问结果：CryptProtectData加密数据，通常绑定登录凭据和机器，存在选项/例外。
- 本项目关联与复用判断：复用凭据保护候选；不保护已被同用户恶意进程读取的运行时明文。
- 尚未验证：账户迁移、备份恢复和语言绑定。
- 后续实验：E06/E07。

<a id="s35"></a>
### S35 · Windows Credential API

- 分类：R07。
- 官方来源：[Windows Credential API](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credwritew)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：Win32 CredWriteW。
- 核实内容/访问结果：将凭据写入当前token登录会话关联的用户凭据集。
- 本项目关联与复用判断：复用Windows凭据存储候选，项目只持有引用。
- 尚未验证：读取/删除闭环、目标名命名空间及部署账户。
- 后续实验：E06/E07。

<a id="s36"></a>
### S36 · Windows Job Objects

- 分类：R07/R08。
- 官方来源：[Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：Win32；嵌套Job自Windows8/Server2012。
- 核实内容/访问结果：可成组管理/终止关联进程并设置资源限制。
- 本项目关联与复用判断：参考受控进程生命周期；不据此宣称文件/网络隔离。
- 尚未验证：breakaway、宿主被强杀和孙进程回收。
- 后续实验：E07/E05。

<a id="s37"></a>
### S37 · Tauri Sidecar

- 分类：R08。
- 官方来源：[Tauri Sidecar](https://v2.tauri.app/develop/sidecar/)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：Tauri 2滚动文档。
- 核实内容/访问结果：externalBin打包外部可执行文件；需目标架构后缀，shell插件可spawn及读写流。
- 本项目关联与复用判断：复用桌面宿主能力，支持Node/Python候选。
- 尚未验证：分发体积、流量背压、取消与升级兼容。
- 后续实验：E07。

<a id="s38"></a>
### S38 · Tauri Capabilities

- 分类：R07/R08。
- 官方来源：[Tauri Capabilities](https://v2.tauri.app/security/capabilities/)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：Tauri 2滚动文档。
- 核实内容/访问结果：按window/webview约束前端可用权限；多个capability权限会合并。
- 本项目关联与复用判断：复用IPC权限门；Rust/sidecar策略仍需设计。
- 尚未验证：原生插件路径绕过与端到端授权。
- 后续实验：E06/E07。

<a id="s39"></a>
### S39 · Tauri Windows Installer

- 分类：R08。
- 官方来源：[Tauri Windows Installer](https://v2.tauri.app/distribute/windows-installer/)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：Tauri 2滚动文档。
- 核实内容/访问结果：提供Windows打包路径与WebView2分发选项，含离线安装模式。
- 本项目关联与复用判断：参考Windows分发；不能仅凭宿主轻量推断总包体小。
- 尚未验证：干净机器、签名、架构和离线安装实测。
- 后续实验：E07。

<a id="s40"></a>
### S40 · Vue 3 Introduction

- 分类：R08。
- 官方来源：[Vue 3 Introduction](https://vuejs.org/guide/introduction.html)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：Vue 3文档；未锁补丁版本。
- 核实内容/访问结果：声明式UI、响应式与组件化；可用于不同应用形态。
- 本项目关联与复用判断：前端候选；与Vue Flow组合待验证。
- 尚未验证：复杂节点表单状态与大数据渲染。
- 后续实验：E01/E07。

<a id="s41"></a>
### S41 · Node.js Child Process

- 分类：R05/R08。
- 官方来源：[Node.js Child Process](https://nodejs.org/api/child_process.html)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：页面标示v26.12.1；不是运行时选择。
- 核实内容/访问结果：spawn/execFile/exec等接口；Windows bat/cmd启动方式有差异。
- 本项目关联与复用判断：参考CLI适配及stdio；优先参数数组与关闭shell的候选方案。
- 尚未验证：退出信号、缓冲背压、路径编码及进程树关闭。
- 后续实验：E03/E07。

<a id="s42"></a>
### S42 · Flowise 发布状态

- 分类：R09。
- 官方来源：[Flowise 发布状态](https://github.com/FlowiseAI/Flowise/releases)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：flowise@3.1.4；GitHub API published_at=2026-07-29T15:51:25Z。
- 核实内容/访问结果：发布页可见3.1.4及近期功能/修复条目；API确认最近发布元数据。
- 本项目关联与复用判断：保留为在维护候选；发布存在不等于长期维护承诺。
- 尚未验证：响应时效、安全修补周期、后续维护持续性。
- 后续实验：E05/E06；后续竞品实测。

<a id="s43"></a>
### S43 · Flowise Agentflow V2

- 分类：R01/R03/R09。
- 官方来源：[Flowise Agentflow V2](https://docs.flowiseai.com/using-flowise/agentflowv2)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：Agentflow V2滚动文档；不等同软件主版本2。
- 核实内容/访问结果：显式控制路径、Flow State、人工输入与checkpoint恢复有官方说明。
- 本项目关联与复用判断：参考数据/控制分离和审批；是否可嵌入需另评估。
- 尚未验证：崩溃点恢复、重复副作用及并行支路实际表现。
- 后续实验：E04/E05/E06。

<a id="s44"></a>
### S44 · MCP Lifecycle

- 分类：R05。
- 官方来源：[MCP Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：2025-11-25。
- 核实内容/访问结果：初始化交换版本与capabilities，随后运行并协调关闭。
- 本项目关联与复用判断：复用握手协议，限制未经协商的可选能力。
- 尚未验证：服务端版本不兼容与关闭失败。
- 后续实验：E03。

<a id="s45"></a>
### S45 · MCP Transports

- 分类：R05。
- 官方来源：[MCP Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：2025-11-25。
- 核实内容/访问结果：stdio与Streamable HTTP；stdio按行JSON-RPC且stdout不能混日志。
- 本项目关联与复用判断：本地工具优先验证stdio；远程支持范围保持开放。
- 尚未验证：旧HTTP+SSE兼容、流断线和会话保护。
- 后续实验：E03/E07。

<a id="s46"></a>
### S46 · JSON Schema Validation

- 分类：R02。
- 官方来源：[JSON Schema Validation](https://json-schema.org/draft/2020-12/json-schema-validation)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：Draft 2020-12 validation；发布2022-06-16。
- 核实内容/访问结果：以词汇约束JSON实例并提供注解；是工作草案来源，不应称正式IETF RFC。
- 本项目关联与复用判断：复用校验规则；图可达性、端口兼容须另行校验。
- 尚未验证：format断言启用和验证器一致性。
- 后续实验：E01/E02。

<a id="s47"></a>
### S47 · Anthropic 原Messages入口（失败记录）

- 分类：R04。
- 官方来源：[Anthropic 原Messages入口（失败记录）](https://docs.anthropic.com/en/api/messages)。
- 实际核验日期：2026-10-24；状态：待验证（正文未核验）。
- 版本/适用范围：无法确认该入口当前内容。
- 核实内容/访问结果：未核验：浏览工具返回正文过大（4194305+）。
- 本项目关联与复用判断：仅保留入口；相关参数结论改据S27，不从该页推断。
- 尚未验证：完整接口正文。
- 后续实验：E02前重查规范化页面。

<a id="s48"></a>
### S48 · Dify Self-host 索引（失败记录）

- 分类：R01/R09。
- 官方来源：[Dify Self-host 索引（失败记录）](https://docs.dify.ai/_llms/en/self-host.txt)。
- 实际核验日期：2026-10-24；状态：待验证（正文未核验）。
- 版本/适用范围：无法确认该索引正文。
- 核实内容/访问结果：未核验：浏览工具报告URL不可访问。
- 本项目关联与复用判断：仅保留失败；改用S11/S12且明确产品页/历史说明的证据边界。
- 尚未验证：当前自部署版详细功能与版别。
- 后续实验：后续按固定发布版本查官方仓库与文档。

## 访问与重定向补充

- ComfyUI旧节点入口 `/development/core-concepts/nodes` 跳转至S04。
- n8n旧 `/flow-logic/`、`/workflows/history/` 和局部执行入口跳转至S08–S10记录的Markdown正文。
- LangGraph `/durable-execution` 跳转到S18的persistence页；本轮未把旧页描述当作当前正文。
- vLLM旧 `/serving/openai_compatible_server/` 先出现跳转页；继续到S25读取实际接口正文。
- MCP旧安全规范路径跳转到S29的教程路径；路径含版本不证明全站latest版本。
- Microsoft Learn页面出现授权提示模板，但S34–S36正文/API说明实际可读；已核实仅基于可读部分。
- Flowise GitHub API入口 `https://api.github.com/repos/FlowiseAI/Flowise/releases/latest` 在浏览工具不可读，随后以PowerShell只读请求成功获取tag/published_at/html_url；本轮S42维护状态依据含该元数据。UTC时间为2026-07-29 15:51:25，对应北京时间23:51:25。
- S47/S48访问失败未被计为核验成功；Dify文档首页可读不等于自部署细节已核验。

## P0-02补充核验（2026-10-24）

本轮保留原48条历史记录，新增S49–S57。版本候选仅供下一阶段实验；没有安装这些SDK或连接真实协议服务。S27官方版本页也已复读确认；S47/S48失败记录仍保留，不转为核验成功。

<a id="s49"></a>
### S49 · JSON Schema Core 2020-12

- 分类：R02。
- 官方来源：[JSON Schema Core 2020-12](https://json-schema.org/draft/2020-12/json-schema-core)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：2020-12。
- 已核实内容：$id/$ref、词汇与实例模型提供版本化契约基础。
- 本项目关联与复用理由：复用规范，不把它当调度与权限实现。
- 尚未验证/冲突：跨语言验证器、复杂度限制与未来方言迁移。
- 后续实验：契约静态检查；后续E01。

<a id="s50"></a>
### S50 · PowerShell Test-Json

- 分类：R02/R10。
- 官方来源：[PowerShell Test-Json](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/test-json?view=powershell-7.5)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：文档视图7.5；本机PowerShell7.6.5。
- 已核实内容：7.4起用System.Text.Json和JsonSchema.NET；本地命令存在并能校验本草案。
- 本项目关联与复用理由：直接复用已有工具，不安装jsonschema/Ajv。
- 尚未验证/冲突：不由此证明其他OS或所有Draft关键字互操作。
- 后续实验：本轮静态正负样例。

<a id="s51"></a>
### S51 · MCP Python SDK发布

- 分类：R05。
- 官方来源：[MCP Python SDK发布](https://github.com/modelcontextprotocol/python-sdk/releases)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：候选mcp 2.3.0；发布页tag v2.3.0。
- 已核实内容：版本存在；说明涉及2025-11-25旧连接和2026-07-28连接差异。
- 本项目关联与复用理由：后续MCP实验Python候选；不决定执行核心语言。
- 尚未验证/冲突：SDK真实握手、依赖版本、Windows/Linux行为；tree/v2.3.0页面浏览受限。
- 后续实验：E03/E07。

<a id="s52"></a>
### S52 · MCP TypeScript SDK发布

- 分类：R05。
- 官方来源：[MCP TypeScript SDK发布](https://github.com/modelcontextprotocol/typescript-sdk/releases)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：候选@modelcontextprotocol/client/server/core 2.4.0及node 2.1.2。
- 已核实内容：发布页列分包版本，说明2025-11-25连接的structuredContent变化。
- 本项目关联与复用理由：后续TS候选，与Python对照；不静默采用latest。
- 尚未验证/冲突：实际安装/API与依赖闭包，旧协议模式配置。
- 后续实验：E03/E07。

<a id="s53"></a>
### S53 · A2A规范发布

- 分类：R05。
- 官方来源：[A2A规范发布](https://github.com/a2aproject/A2A/releases)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：规范tag v1.0.1。
- 已核实内容：发布页存在v1.0.1并描述规范修正。
- 本项目关联与复用理由：锁定下一阶段规范候选，替代只引用latest。
- 尚未验证/冲突：固定规范站页的Latest Released标题仍写1.0.0；需对照tag差异。
- 后续实验：场景C协议握手实验。

<a id="s54"></a>
### S54 · A2A固定版本规范页

- 分类：R05。
- 官方来源：[A2A固定版本规范页](https://a2a-protocol.org/v1.0.1/specification/)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：URL v1.0.1；线协议1.0。
- 已核实内容：任务、产物、Send/Get/Cancel操作及Major.Minor版本语义有正文支持。
- 本项目关联与复用理由：保留Agent生命周期；patch不是线协议协商值。
- 尚未验证/冲突：页标题Latest Released仍列1.0.0，与S53存在版本标识差异；不擅自忽略。
- 后续实验：场景C与E05。

<a id="s55"></a>
### S55 · A2A Python SDK发布

- 分类：R05。
- 官方来源：[A2A Python SDK发布](https://github.com/a2aproject/a2a-python/releases)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：候选a2a-sdk 1.2.3；tag v1.2.3。
- 已核实内容：发布说明含1.0接口patch版本处理和旧0.3兼容相关修复。
- 本项目关联与复用理由：后续Agent实验SDK候选，不证明1.0.1全部兼容。
- 尚未验证/冲突：依赖、认证、服务端互操作及远端取消；tree/v1.2.3页面浏览受限。
- 后续实验：场景C真实任务/取消。

<a id="s56"></a>
### S56 · Gemini generateContent参考

- 分类：R04。
- 官方来源：[Gemini generateContent参考](https://ai.google.dev/api/generate-content)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：v1beta接口文档；未固定真实模型。
- 已核实内容：公开models.generateContent端点与contents输入，并说明模型能力不同。
- 本项目关联与复用理由：场景A第二供应商真实接口候选，不调用收费端点。
- 尚未验证/冲突：精确模型/API/参数/结构化输出/账户限额。
- 后续实验：E02/场景A。

<a id="s57"></a>
### S57 · HTTP Semantics

- 分类：R05/R03。
- 官方来源：[HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)。
- 实际核验日期：2026-10-24；状态：已核实（文档证据）。
- 版本/适用范围：RFC9110，2022-06。
- 已核实内容：定义HTTP语义，包含安全与幂等方法的标准基础。
- 本项目关联与复用理由：参考HTTP适配和重试设计；业务副作用还需具体接口证据。
- 尚未验证/冲突：第三方POST幂等键、超时结果查询及服务端遵从。
- 后续实验：E03/E05/场景B。

<a id="s58"></a>
### S58 · Python asyncio Tasks

- 分类：R03/R08。
- 官方来源：[Coroutines and Tasks](https://docs.python.org/3.12/library/asyncio-task.html)。
- 实际核验日期：2026-10-24；状态：已核实（官方正文）。
- 版本/适用范围：Python 3.12文档分支；网页滚动补丁可能高于本机3.12.14，不把网页版本当安装版本。
- 已核实内容：任务、协作取消及wait_for超时机制；超时取消并非任意外部调用立即终止保证。
- 本项目关联与复用理由：P0-03明确任务边界与unknown取消语义。
- 尚未验证：CPU阻塞扩展、真实远端调用、OS进程取消及生产负载。
- 后续实验：受控Windows MCP进程及生命周期探针。

<a id="s59"></a>
### S59 · Python sqlite3

- 分类：R03。
- 官方来源：[sqlite3 — DB-API interface for SQLite databases](https://docs.python.org/3.12/library/sqlite3.html)。
- 实际核验日期：2026-10-24；状态：已核实（官方正文）。
- 版本/适用范围：Python 3.12标准库；本机实际链接SQLite 3.53.1。
- 已核实内容：连接、事务控制和SQLite版本查询接口；P0-03使用isolation_level=None并显式BEGIN/COMMIT。
- 本项目关联与复用理由：无需安装数据库框架即可记录单权威快照及事件。
- 尚未验证：桌面正式分发、数据库迁移、满盘或损坏恢复与高并发。
- 后续实验：持久化失败及状态迁移验证。

<a id="s60"></a>
### S60 · SQLite Atomic Commit

- 分类：R03。
- 官方来源：[Atomic Commit In SQLite](https://sqlite.org/atomiccommit.html)。
- 实际核验日期：2026-10-24；状态：已核实（官方正文）。
- 版本/适用范围：SQLite原子提交原理说明；正文主要解释rollback journal，WAL实现不同，P0-03不据此替代WAL实测。
- 已核实内容：提交原子性依赖存储假设、锁、日志及同步；单数据库原子提交不等于任意外部操作共同原子提交。
- 本项目关联与复用理由：区分本地事务结果与外部副作用未知；原WAL依据仍为S21。
- 尚未验证：本机断电、硬件缓存行为、磁盘故障及网络文件系统。
- 后续实验：仅在专门安全环境开展持久化故障实验。

<a id="s61"></a>
### S61 · MCP Python SDK v1.30.0固定发布与制品

- 分类：R05/R10。
- 官方来源：[固定发布](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v1.30.0)、[依赖定义](https://github.com/modelcontextprotocol/python-sdk/blob/v1.30.0/pyproject.toml)、[MIT许可](https://github.com/modelcontextprotocol/python-sdk/blob/v1.30.0/LICENSE)。
- 实际核验日期：2026-10-24；状态：已核实（官方正文、固定源码与本机安装制品）。
- 版本/适用范围：mcp==1.30.0；本轮协议2025-11-25；SDK版本不是协议版本。
- 已核实内容：官方MIT SDK支持Python>=3.10，声明anyio/pydantic/jsonschema等运行依赖；实际Windows环境见实验锁及安装报告。
- 本项目关联与复用理由：为P0-04客户端/服务端固定同一维护线版本，减少新版协议迁移变量。
- 尚未验证：任意Server、其他SDK/OS/可选功能、正式分发合规及维护周期风险。
- 后续实验：完整派发上下文与进程/协议边界评审；不冻结正式语言。

<a id="s62"></a>
### S62 · MCP Python v1维护线与当前版本边界

- 分类：R05。
- 官方来源：[v1文档](https://py.sdk.modelcontextprotocol.io/v1/)、[当前安装文档](https://py.sdk.modelcontextprotocol.io/get-started/installation/)、[2026-07-28规范](https://modelcontextprotocol.io/specification/2026-07-28)。
- 实际核验日期：2026-10-24；状态：已核实（官方正文）。
- 版本/适用范围：v1为维护线，v2为当前主稳定线；2026-07-28与2025-11-25连接模型不同。
- 已核实内容：v1文档明确与v2分开；新规范为无旧式会话的请求模型，不能混合初始化步骤。
- 本项目关联与复用理由：P0-04仅用固定旧协议与v1源码；保留S51的2.3.0候选，不伪称其不兼容。
- 尚未验证：本项目在v2.3.0上的真实旧协议模式、迁移成本与双协议兼容。
- 后续实验：确有需要时另建版本对照探针，不静默升级。

<a id="s63"></a>
### S63 · MCP v1.30.0请求/取消源码与固定取消规范

- 分类：R03/R05/R07。
- 官方来源：[ClientSession](https://github.com/modelcontextprotocol/python-sdk/blob/v1.30.0/src/mcp/client/session.py)、[BaseSession与RequestResponder](https://github.com/modelcontextprotocol/python-sdk/blob/v1.30.0/src/mcp/shared/session.py)、[2025-11-25取消](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation)。
- 实际核验日期：2026-10-24；状态：已核实（固定源码、规范及本机安装源码检查）。
- 版本/适用范围：SDK1.30.0的stdio普通tools/call；不包括HTTP/Tasks。
- 已核实内容：send_request/call_tool无自动重试循环；取消通知不是物理停止证明。SDK cancel发送code0错误与规范建议不再响应有差异，本轮不据此确认终止。
- 本项目关联与复用理由：C1独占重试，外部写入响应丢失/未确认取消维持unknown，具体执行证据单独链接。
- 尚未验证：任意Server的取消遵守情况、通用业务核实机制、SDK未来修正及其他传输行为。
- 后续实验：独立任务的query/cancel核实与SDK选择评审。

<a id="s64"></a>
### S64 · A2A Python SDK 1.2.3 JSON-RPC固定实现

- 分类：R03/R05/R10。
- 官方来源：[客户端JsonRpcTransport](https://github.com/a2aproject/a2a-python/blob/v1.2.3/src/a2a/client/transports/jsonrpc.py)、[Server路由](https://github.com/a2aproject/a2a-python/blob/v1.2.3/src/a2a/server/routes/jsonrpc_routes.py)、[dispatcher](https://github.com/a2aproject/a2a-python/blob/v1.2.3/src/a2a/server/routes/jsonrpc_dispatcher.py)、[RequestHandler](https://github.com/a2aproject/a2a-python/blob/v1.2.3/src/a2a/server/request_handlers/request_handler.py)。
- 实际核验日期：2026-10-24；状态：已核实（官方固定源码、本机安装源码及制品摘要）。
- 版本/适用范围：SDK1.2.3，A2A线协议1.0；JSON-RPC绑定，旧0.3兼容可关闭。
- 已核实内容：SDK提供标准SendMessage/GetTask/ListTasks/CancelTask路由与protobuf模型；客户端一次HTTP请求路径无隐藏提交重试循环。实际异步任务和持久化仍由本项目自有服务实现，不是SDK自动保证全部业务语义。
- 本项目关联与复用理由：P0-05优先标准A2A，未降为非A2A任务协议；正式能力/任务证据见对应报告。
- 尚未验证：完整A2A符合性、其他SDK/传输、第三方服务、TLS/多租户、分页/续谈及长期负载。
- 访问说明：早期尝试旧apps/jsonrpc及独立json-rpc规范路径不可用，改按本固定版本实际routes源码与规范总页核查，未将旧路径访问失败当成SDK不支持。
- 后续实验：完整派发/查询上下文与桌面宿主生命周期；不冻结最终栈。

<a id="s65"></a>
### S65 · Tauri 2实际窗口IPC与Windows宿主边界

- 分类：R03/R07/R08/R10。
- 官方来源：[Tauri前提](https://v2.tauri.app/start/prerequisites/)、[Capabilities及应用命令清单](https://v2.tauri.app/security/capabilities/)、[Windows安装分发](https://v2.tauri.app/distribute/windows-installer/)、[Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)。
- 实际核验日期：2026-10-27；状态：已核实（官方正文及本机锁定crate源码/生成权限清单）。
- 版本/适用范围：Tauri 2文档；本机实际tauri2.12.5、tauri-build2.7.4、Rust1.95.0、WebView2 155.0.4283.62，具体Cargo.lock固定。在线文档不是固定版本制品，实际行为由构建/窗口证据限定。
- 已核实内容：Windows需要C++工具及WebView2；自定义应用命令需结合AppManifest/permission/capability配置；Job可管理嵌套进程生命周期，不能替代OS沙箱；安装分发依赖另行验证。
- 本项目关联与复用理由：P0-06真实窗口invoke与Rust探针分别验收，不用进程通信成功冒充窗口成功；旧P0-01/P0-02技术栈候选和模块职责保留。
- 尚未验证：干净机器安装/签名/升级、恶意breakaway/沙箱、多窗口/远程origin攻击、Linux/macOS、生产背压。
- 后续实验：稳定命令/派发契约、发行依赖闭包与最小画布闭环；不冻结Python或直接迁移Rust调度。


<a id="s66"></a>
### S66 · 官方Python模型SDK与本轮固定制品

- 分类：R02/R04/R07/R10；核验日期2026-10-29。
- 官方正文：[OpenAI Python SDK](https://developers.openai.com/api/reference/python)、[Anthropic Python SDK](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python)；上游[openai-python](https://github.com/openai/openai-python)、[anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python)。
- 本轮实际固定openai3.41.0、anthropic2.3.0，两个wheel的Apache-2.0许可和NOTICE保留；httpx2/httpcore2 2.16.0。源码未改，完整传递闭包/哈希见experiments/p0-08/sdk-requirements.lock及evidence/dependency-review.json。
- 已核验：async客户端、参数与响应对象、异常/自动重试入口；本轮实际SDK通过自有loopback HTTP，两协议、结构化输出、usage有无、错误/断连/取消均有独立C1和HTTP证据。文档不是固定版本制品，行为以实际锁定包为准。
- 未验证：真实供应商模型、限流/取消和账单，缓存/推理/多模态计量，以及干净机器发行与Linux/macOS。不能从夹具成功推出真实推理通过。

<a id="s67"></a>
### S67 · 多供应商候选复用与供应链门禁

- 分类：R04/R07/R09；核验日期2026-10-29。
- 一手正文：[Vercel AI SDK设置](https://ai-sdk.dev/docs/ai-sdk-core/settings)、[LiteLLM 1.107.0事件最终调查](https://docs.litellm.ai/blog/security-incident-oct-21-2026-attack-chain)。版本/元数据观察沿用planning/reuse-first-evidence/2026-10-29，候选不等于已安装。
- 已核验：Vercel提供参数/重试/取消等SDK入口，是可信JS运行时候选；LiteLLM官方最终调查确认被污染的1.107.0，早期中间判断不替代最终报告。P0-08不安装/导入LiteLLM，也未执行Vercel SDK。
- 项目结论：本轮采用可复用现有Python进程的两种官方SDK；不能永久排除TypeScript，不能把旧版本或latest标签自动当安全。方案和未测成本见planning/p0-08-sdk-comparison.md。

P0-08增量仅增加S66–S67两条正文核验记录；原65条历史口径不改，当前来源记录67条。SDK实际执行与文档核验分别统计。
