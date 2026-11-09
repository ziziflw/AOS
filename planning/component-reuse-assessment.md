# AOS 主要组件复用评估

评估日期：2026-10-29（Asia/Shanghai）。遵循[Reuse First政策](./reuse-first-policy.md)。**本轮是规范、源码/依赖审查与选型评估；未安装候选、未运行SDK对照、未重构P0-03至P0-07、未启动P0-08。**附件P0-08任务作为下一轮要求，当前用户明确范围优先。

结论：继续复用Vue Flow、官方MCP/A2A SDK、Tauri、SQLite及现有Schema校验。C1暂保留为当前唯一执行权威和对照基线；LangGraph值得独立比较，尚无替换依据。模型层优先在Python进程评估成熟SDK：**以官方Python SDK作协议基准和当前首选实验路线；LiteLLM有条件候选；Vercel AI SDK保留可信JS运行时对照**，最终采用须以P0-08实测决定，不能因当前Python永久排除TS。

证据：L=历史实际验证；R=本轮源码/锁文件/上游审查；P=计划；U=未验证。L均为2026-10-27等旧阶段证据，本轮没有重跑或新增通过数量。当前SDK兼容性、安全、依赖闭包和打包建议不是实际集成通过。

## 1. 现有能力与复用边界

本轮读取[本地元数据清单](./reuse-first-evidence/2026-10-29/local-inventory.json)和既有lock/源码。P0-06环境枚举49项发行元数据包含pip，不是新增安装；原报告48项运行依赖口径保留。候选模型SDK/LangGraph/keyring未在该环境清单中，不能把其他工具环境中的包当AOS已安装能力。

| 模块 / 实际版本 | 既有第三方能力 / AOS代码 | 复用成本、替换风险与建议 | 证据 |
| --- | --- | --- | --- |
| A1画布：Vue3 3.5.44、Vue Flow 1.48.2 / background1.3.2 | Vue Flow提供几何/交互；AOS保留原定义映射、类型兼容、命令历史和C1投影 | 继续用现有API，不重做平移/缩放/端口/选择。命令栈是业务胶水；通用布局引擎另评估。替换图库会重验保存/取景/键鼠，成本高，无当前理由 | L/R；MIT，源码见frontend package-lock |
| D2 MCP：mcp1.30.0，原线版本2025-11-25 | ClientSession、协议对象/协商来自官方SDK；AOS拥有受限stdio、帧/描述签名、Job和执行授权 | 保留SDK，不自写JSON-RPC栈。自有传输安全包装不等于自研全部协议；未来优先评估SDK现成transport可否满足，不能因“更短”删限界检查 | L/R；MIT；P0-04/06回归 |
| D3 A2A：a2a-sdk1.2.3，既有线版本1.0 | 官方resolver/JsonRpcTransport；AOS保存taskId/原attempt、查询恢复、产物/身份核验 | 继续官方SDK。恢复query-only、未确认取消与unknown保留为合同回归，不能用模型SDK的Agent循环替换 | L/R；Apache-2.0；P0-05/06 |
| C1：Python asyncio + stdlib sqlite3 | SQLite事务/WAL来自成熟数据库；StateStore与Runtime状态语义为AOS实验代码 | 不另造存储引擎；保留C1当前权威。自研scheduler的长期维护风险真实存在，见第4节LangGraph对照，不能直接升级为生产保证 | L/R；AOS代码，SQLite上游[公开领域说明](https://www.sqlite.org/copyright.html) |
| B1：jsonschema4.26.0，Draft2020-12原合同 | 成熟validator；AOS做本地引用、版本/类型/节点/图校验 | 直接复用，禁止为SDK另造JSON方言。JSON Schema通过不代表DAG/权限/能力通过 | L/R；MIT；P0-06 SchemaAdapter/原Contracts |
| A1参数表单：P0-07有限renderer | 当前Schema的string/number/integer/bool/enum/const控件为AOS业务UI | 当前范围继续用；复杂object/array/oneOf扩张前比较JSON Forms Vue（MIT），不默认重写通用表单框架，也不为少数字段强加整套组件主题 | L/R/P；JSON Forms仅文档/许可审查 |
| E3宿主：Tauri2.12.5 / wry0.57.1 / serde_json1.0.154 | 窗口/IPC/序列化为第三方，AOS为固定命令/权限/进程生命周期胶水 | 保留现有能力与float_roundtrip；不自写WebView壳或另加通用shell IPC。windows-sys0.61.2、Job是系统适配，不是完整沙箱 | L/R；Tauri等MIT/Apache双许可按具体制品保留 |
| A2追踪：已间接安装opentelemetry-api1.45.1 | API来自现有依赖链，未有本项目SDK/exporter配置证据 | 先复用已有API，再隔离评估匹配SDK/exporter；不是“先自研trace格式再迁移”，也不把API已安装说成已完成遥测 | R/P；Apache-2.0 |
| E3凭据：已有pywin32 312 | 可复用Windows成熟Credential Manager API；当前没有真实模型凭据实现 | 优先E3受限凭据后端，不自行加密。Rust windows-sys或已有pywin32只选清楚的可信入口；keyring仅跨平台备选，不自动安装/探测用户凭据 | R/P；pywin32元数据PSF，实际分发还需逐文件核验 |
| 多模态：尚无ComfyUI执行接入 | 已有ComfyUI UI研究，不等于官方执行API已集成 | 优先独立服务的官方API；不复制图像执行引擎或默认安装GPU/模型/插件，见第6节 | R/P/U；GPLv3边界需单审 |

历史基线：[P0-07后端12方法](../experiments/p0-07/evidence/backend-20261027T145724786217Z/summary.json)、[真实窗口19步骤](../experiments/p0-07/evidence/gui-20261027T145714748Z/summary.json)，原P0-03/04/05/06分别18/14/18/15方法见[P0-07验收](./p0-07-workbench-verification.md)。SDK升级不得自动覆盖这些环境；官方SDK身份不保证任意新major与旧线版本兼容。

## 2. 模型SDK：三条路线

| 候选 / 本次观察版本（不是安装批准） | 能力与集成 | 依赖/许可/维护及风险 | 暂定结论 |
| --- | --- | --- | --- |
| LiteLLM / litellm-core 1.106.6 | Python async多供应商映射、统一结果/异常；SDK可嵌入现有进程，不必Proxy。参数覆盖须按provider/model核实 | SDK核心MIT，enterprise目录另许可；core与完整包不能共装。较多传递依赖，存在原生tokenizer/可选云SDK；实际wheel来源需特别审查，见第3节 | R/P：技术适配高，但安全门槛未通过；暂缓安装，不先定为主方案 |
| Vercel AI SDK：ai7.0.156；openai provider4.0.104 / anthropic4.0.91 | TypeScript provider管理、结构化输出、流、AbortSignal；适合未来可信JS执行层 | Apache-2.0（观察源码/包元数据）；本项目只有前端构建用Node，不等于已有可信模型执行侧车。需要部署JS运行时/服务边界；不能把密钥放Vue/WebView | R/P：保留对照，不为它现在迁移C1或添加常驻服务 |
| 官方Python SDK：openai3.41.0 / anthropic2.3.0 | 各自正式API、异步客户端、类型/响应/错误处理；在D1做小范围能力/结果映射 | 本次观察两仓库许可证均Apache-2.0。供应商差异由AOS能力声明保留，不另写HTTP栈；两个SDK仍是两种协议，不假定同一OpenAI兼容端点能覆盖 | R/P：当前首选实验路线与协议基准，待离线实测和依赖审查后选定版本 |

版本来自[PyPI元数据快照](./reuse-first-evidence/2026-10-29/upstream-snapshot.json)与[NPM元数据](./reuse-first-evidence/2026-10-29/npm-metadata.json)。它们只含**直接依赖声明/制品元数据**，不是已解析的传递锁、安装成功、漏洞扫描通过或干净机器打包结果。

关键适配限制：

- **存在实际版本冲突线索**：LiteLLM1.106.6声明`openai>=2.20,<3`，不能与观察到的OpenAI3.41.0在同一解析方案中直接满足。应分隔离环境对照，或经审查选兼容SDK发布；不能强制安装/悄悄降级旧环境。候选选择不是“全部安装到当前venv”。
- OpenAI3.41.0和Anthropic2.3.0元数据使用`httpx2`；现有AOS是`httpx0.28.1`。不能把已有HTTPX客户端/测试替身当作可直接注入的新SDKtransport。原生jiter、LiteLLM tokenizer、LangGraph相关扩展均须查Windows wheel和ABI。Python3.12满足这些候选声明的版本下限，**不证明完整依赖可共存**。
- LiteLLM完整包与core的基础/extra依赖不同；core元数据仍有tiktoken，不宣称“无原生依赖”。默认不启用Proxy/Router/fallback/缓存/遥测回调。全局配置不能被不同节点并发改写。[官方SDK说明](https://docs.litellm.ai/docs/python_sdk)。
- LiteLLM的参数支持查询只作证据输入；AOS后端仍固定模型能力Schema，拒绝未知或不支持字段，不启用静默丢参数。AI SDK部分参数不支持时可能只返回warning，因此不能等请求花费后才把warning视作前置拒绝。[LiteLLM参数说明](https://docs.litellm.ai/docs/completion/input)、[AI SDK设置](https://ai-sdk.dev/docs/ai-sdk-core/settings)。
- SDK默认行为必须核对：OpenAI官方文档说明默认有自动重试和较长超时；AI SDK当前设置也有默认重试。离线比较先配置SDK重试为0，再核查网关/Router/HTTP层；若未来启用，必须进入同一C1派发预算。客户端abort不是供应商停机/未计费证明。[OpenAI官方Python参考](https://developers.openai.com/api/reference/python)、[AI SDK请求设置](https://ai-sdk.dev/docs/ai-sdk-core/settings)。

不因Python偏好排除TS：若P0-08证实AI SDK明显降低两协议能力/结构化处理的总成本，且可信JS运行时增加的生命周期、打包和IPC成本可接受，可提出单独服务方案。AI SDK本身不强制Next.js或Node这一种运行环境；问题是AOS当前后端没有该可信JS执行部署，不是Vue不能使用它。

## 3. LiteLLM安全门槛：本轮具体事实

官方2026-10-23调查报告确认，2026-10-21发布的`litellm==1.107.0`通过被滥用的发布链污染，涉及PyPI和容器制品；官方强调该报告覆盖此前不完整/修正过的调查判断。[官方攻击链报告](https://docs.litellm.ai/blog/security-incident-oct-21-2026-attack-chain)。

因此：不安装1.107.0，不依据GitHub tag看似无恶意就批准对应wheel，不把当前PyPI显示1.106.6直接称为“已安全”；需重新核验来源、构建证明/哈希、发布后公告、传递依赖及`.pth`/启动行为。源码复用也须固定实际仓库`BerriAI/litellm`，不能误认带额外连字符的近似名称。

本轮只读公开文档、许可证和包元数据，**未下载候选wheel、未安装/导入LiteLLM、未执行修复脚本，也没有扫描或访问用户凭据**。这不是对本机感染与否的全机审计，不需要未经授权进行清理。安全否决是一项具体有来源的准入结果，不是断言该项目永久不可用。

## 4. C1 vs LangGraph：先做语义对照，当前不替换

LangGraph观察版1.2.18，MIT；SQLite checkpointer包3.1.2是独立依赖，当前元数据还含`aiosqlite`、`sqlite-vec`。其持久化、interrupt、重试/故障处理值得复用评估，但**interrupt不是AOS的权限审批机制**，checkpoint也不自动提供AOS的版本、unknown、taskId和预算语义。[LangGraph持久化](https://docs.langchain.com/oss/python/langgraph/persistence)、[interrupt规则](https://docs.langchain.com/oss/python/langgraph/interrupts)。

当前C1是已实测实验器，不是“已证明优于成熟框架”。初期替换成本高，长期自维护也有成本；实际差异、适配量和故障正确性尚未测量，不预设胜者。LangGraph先选为最小对照候选；Temporal Python（MIT SDK）仅作为远期多worker/服务化候选，现阶段服务/worker部署成本更大，不为本地单活动run引入。[Temporal开发模型](https://docs.temporal.io/develop/python)。

### 本轮静态发现的真实限制（R，尚未新增运行测试）

1. `runtime.py:_reserve`仅按maxOutputTokens预留；`_execute`要求整数usage和零合成费用，非零会报`NONZERO_SYNTHETIC_COST_FORBIDDEN`，不是可直接接真实计费的总账。
2. 最小类型/业务反例：输入900 tokens、输出100、maxOutputTokens128；如果D1把总usage1000塞进现有`usage_tokens`，C1会按“超输出上限”拒绝。若仅返回100则遗漏输入消耗；未知usage默认0同样不可信。需区分input/output/known/unknown及费用暴露，不能在SDK适配里掩盖。
3. `_terminal`会释放原预留；在未知消耗情况下释放并结算默认0，不足以保守控制下一次真实收费派发。billable的timeout与协作cancel路径也不完全等同，必须专门对照“业务取消”和“可能已计费”。
4. P0-07 `p07.model`只是builtin合成文本，temperature不推理，最大输出按字符；不能把接上SDK直接宣称原Model适配/预算已成立。

这些是下一轮**最小必要扩展与对照的输入**，不在本轮修补核心，也不据此要求直接重写C1。SDK负责供应商协议，AOS保留预算准入/审批是必要业务控制，不是重复造SDK。

### 最小对照方案（P，未经本轮执行）

使用原P0-02类型/定义的同一组合成场景，各自独立SQLite和合成副作用账本；输出规范化的run/node/attempt/iteration/approval/op/task身份与事件比较。框架内部checkpoint字段可以不同，但有效输出、审批门禁、重放次数和终态解释必须一致或显式列差异。

| 对照项 | 必须观察的事实 |
| --- | --- |
| 串行/并行/条件/汇合/有界循环 | 上游有效值、真正并行、skip不会永久等待、失败/取消传播、attempt与iteration映射 |
| 审批与重启 | 缺/拒绝/过期/变内容/取消的批准不可派发；重启pending；重复提交不重复效果 |
| 中断与恢复窗口 | 完成前后、效果提交后但回复丢失、checkpoint写入中断；已确认不重放、无法确认unknown |
| LangGraph interrupt重进节点 | 恢复会从该节点开头重执行；审批前代码的副作用不能被重放，不能把恢复当普通函数续行 |
| 安全重试与隐藏重试 | 唯一重试owner、attempt/SDK实际请求数、unsafe不得重放；无自动fallback换模型/预算 |
| 取消与晚到结果 | 协作取消、阻塞调用、可能计费和远端继续；已取消下游不能由迟到输出释放 |
| taskId恢复 | 已知A2A任务只查原task，不再次submit；本机停机不等于远端取消 |
| 并发预算与所有者 | 预算只预留一次、未知消耗保留；同run双执行器拒绝认领；固定版本/指纹 |
| 单一权威与持久化故障 | 框架checkpointer与本地记录谁唯一决定终态；无法原子协调时必须失败关闭，不扩大实现 |

迁移方案须列：P0-02转换/不支持语义、C1接口保留或退为投影、在途run隔离/排空、旧审批与Agent taskId、事件/存储版本、备份/回滚、依赖/体积和回归成本。旧库不可被探针覆盖。先给真实差异与推荐，再经用户确认实施；不让两个执行器在生产同时调度同一run。

## 5. P0-08实际SDK对照门槛（尚未执行）

下一轮至少以两个供应商官方SDK作协议基准；LiteLLM须先通过第3节安全与兼容版本门槛，AI SDK若进入执行比较则使用隔离可信JS进程。禁止为了完成候选数量而安装未核准制品；被安全否决者记录原因和待解除条件，不算比较通过。

1. 隔离新环境固定精确版本、制品哈希和全部传递依赖；不动P0-06共享venv。用同一Windows机测解析/安装、启动、依赖体积和关闭，记录失败；当前只有元数据，不能给出虚构包体排名。
2. 自有HTTP服务提供两种代表性协议、请求记录和故障。SDK完成真实HTTP/类型解析；AOS不实现供应商客户端。测试服务是离线合成夹具，不冒充供应商互操作。
3. 测文本、结构化JSON/错Schema、未知和不支持参数、流/断流、429与明确错误、超时/取消/回复丢失、usage有无；记录SDK实际请求数及默认/关闭重试，禁止静默drop或warning当成成功兼容。
4. 使用假密钥/alias；禁止SDK自动读取本机已有密钥/自动发现云凭据、把prompt/headers发给遥测。用受限本地端点和可控HTTP配置，先证实只访问自有服务；不扫描环境找现成账户。
5. 同一C1固定定义运行input→model→output，实际并发预算竞争、unknown费用暴露、审批/晚到输出保护、MCP/A2A回归；真实窗口只接能力Schema和实际结果，不改现有视觉设定。
6. 比较AOS适配量、协议差异保留、错误/取消和用量事实、启动/打包/升级成本；以准入门槛加实测总成本定主方案。不能用SDK数量、接口统一或代码行更少决定胜负。

通过离线比较后也不自动获得收费授权。真实API只在供应商、模型、凭据用途、预算和次数/范围明确后进行；真实供应商计费/限流/取消依旧U。P0-08完整实现和这些实验均不在本轮执行。

## 6. 追踪、评估、凭据与多模态

**OpenTelemetry：**先用已有API，再评估同版SDK1.45.1和必要exporter。普通traces/metrics依官方状态逐信号核实；GenAI语义已迁到独立仓库，不把所有字段都宣称稳定。固定schema版本，关联run/node/attempt；默认不采集prompt、completion、密钥或任意输入。SDK自身与AOS instrumentation不得重复计数。遥测是可丢失/可重建投影，不参与状态恢复和预算权威。[Python文档](https://opentelemetry.io/docs/languages/python/)、[GenAI迁移说明](https://opentelemetry.io/docs/specs/semconv/gen-ai/)。

**评估：**OpenTelemetry不是质量评分引擎。当前复用既有unittest、合成夹具与类型/结果断言；模型质量评估可再比较Promptfoo OSS（[许可证](https://github.com/promptfoo/promptfoo/blob/main/LICENSE)），本轮未固定其运行依赖/未批准引入。评估器若调用模型，同样需预算授权；不为采集trace立即部署大型评估服务。

**凭据：**优先Windows Credential Manager受控API，现有pywin32或Rust系统绑定薄适配即可，不自创密码学。E3执行读写，E2准入，D1只用授权的短期材料；工作流只存alias。当前不读取/枚举任何凭据。Linux Secret Service和macOS Keychain留可替换后端，不能把Windows成功当跨OS通过。[Microsoft CredWrite说明](https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credwritew)。keyring25.7.0元数据声称MIT并有平台条件依赖，但本轮固定提交的根许可证文件未取得，故该可选包的源码许可核验不完整，暂不引入；无此包也可先复用现有Windows能力。

**ComfyUI：**优先独立官方服务：`/prompt`获取prompt_id，`/history/{prompt_id}`核实、`/ws`事件、`/object_info`能力。AOS只做任务/类型/产物/身份转换，不复制PromptExecutor或图像引擎。[官方API](https://docs.comfy.org/development/comfyui-server/comms_routes)。`/interrupt`等操作的目标范围须实测，不能误取消其他任务；保存原prompt_id，不因断连盲重发。GPLv3源码、分发二进制、模型权重、自定义节点许可各自审查；独立服务不等于已判定所有许可义务消失。不下载模型或安装插件，不承诺GPU/驱动/跨OS可迁移。

## 7. 上游、许可证与版本定位

本轮仅归档公开许可证作审查资料，没有引入其实现源码。固定SHA、原URL和许可证文件SHA256见[上游快照](./reuse-first-evidence/2026-10-29/upstream-snapshot.json)；初次TLS/超时、后续GitHub公共限流保留在[初始快照](./reuse-first-evidence/2026-10-29/upstream-snapshot-initial.json)。未关闭TLS、未读取Token绕过限流。

注意：GitHub自动license分类曾对Vercel/BerriAI显示NOASSERTION，不能据此写“无许可证”；本轮阅读实际文件，分别确认Apache-2.0及核心MIT/enterprise例外。观察版本的元数据/HEAD许可证只支持评估，采用前须再将实际发布制品与对应许可证/NOTICE核对；keyring仍明确未完成。各候选近期commit/归档状态仅是维护信号，不是长期支持或无漏洞承诺。Vue Flow观察HEAD日期2026-06-23，继续使用有证据的锁定版本并追踪维护，不自动追新。

下面的SHA是审查定位，**不是已安装版本的源码一致性证明**。完整SHA与许可副本以快照为准。

| 上游 | 许可审查 | 固定提交（审查用） | 本地许可副本 |
| --- | --- | --- | --- |
| [bcakmakoglu/vue-flow](https://github.com/bcakmakoglu/vue-flow) | MIT | [17953c329db2](https://github.com/bcakmakoglu/vue-flow/commit/17953c329db2d5dc5f5097370cbf5e1173bab520) | [原文件](reuse-first-evidence/2026-10-29/upstream-licenses/bcakmakoglu__vue-flow/LICENSE) |
| [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | MIT | [d7845c073a2b](https://github.com/modelcontextprotocol/python-sdk/commit/d7845c073a2b9ba5ab2817ecf93d3e45ef24cd14) | [原文件](reuse-first-evidence/2026-10-29/upstream-licenses/modelcontextprotocol__python-sdk/LICENSE) |
| [a2aproject/a2a-python](https://github.com/a2aproject/a2a-python) | Apache-2.0 | [43d1eff1b726](https://github.com/a2aproject/a2a-python/commit/43d1eff1b726af7a42874e212683396f62fbcaa3) | [原文件](reuse-first-evidence/2026-10-29/upstream-licenses/a2aproject__a2a-python/LICENSE) |
| [BerriAI/litellm](https://github.com/BerriAI/litellm) | 核心MIT / enterprise另许可 | [b93d26bc854c](https://github.com/BerriAI/litellm/commit/b93d26bc854c0519d60d8fb1643689cbb36589b8) | [原文件](reuse-first-evidence/2026-10-29/upstream-licenses/BerriAI__litellm/LICENSE) |
| [vercel/ai](https://github.com/vercel/ai) | Apache-2.0 | [48ab95d62a08](https://github.com/vercel/ai/commit/48ab95d62a08b409311c110852e8083910ba438d) | [原文件](reuse-first-evidence/2026-10-29/upstream-licenses/vercel__ai/LICENSE) |
| [openai/openai-python](https://github.com/openai/openai-python) | Apache-2.0 | [ca1217ca59a5](https://github.com/openai/openai-python/commit/ca1217ca59a5d0b4497e624771103853d39bd495) | [原文件](reuse-first-evidence/2026-10-29/upstream-licenses/openai__openai-python/LICENSE) |
| [anthropics/anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python) | Apache-2.0 | [202db72c87d7](https://github.com/anthropics/anthropic-sdk-python/commit/202db72c87d7c6eaa72129c67ce67fd343a3a20c) | [原文件](reuse-first-evidence/2026-10-29/upstream-licenses/anthropics__anthropic-sdk-python/LICENSE) |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | MIT | [ffc3336367e8](https://github.com/langchain-ai/langgraph/commit/ffc3336367e8139668d11e5f0b0e6def57e7c762) | [原文件](reuse-first-evidence/2026-10-29/upstream-licenses/langchain-ai__langgraph/LICENSE) |
| [open-telemetry/opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python) | Apache-2.0 | [dc7dbaf93684](https://github.com/open-telemetry/opentelemetry-python/commit/dc7dbaf93684b7b4afd2f653d37238f35d0db09b) | [原文件](reuse-first-evidence/2026-10-29/upstream-licenses/open-telemetry__opentelemetry-python/LICENSE) |
| [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) | GPLv3（具体使用/分发边界待审） | [0df1646a9cd7](https://github.com/Comfy-Org/ComfyUI/commit/0df1646a9cd71d4c990a87014fb37797a2956ead) | [原文件](reuse-first-evidence/2026-10-29/upstream-licenses/Comfy-Org__ComfyUI/LICENSE) |
| [eclipsesource/jsonforms](https://github.com/eclipsesource/jsonforms) | MIT | [2c5fae62a8aa](https://github.com/eclipsesource/jsonforms/commit/2c5fae62a8aace19970ac037d122fa6428cd0436) | [原文件](reuse-first-evidence/2026-10-29/upstream-licenses/eclipsesource__jsonforms/LICENSE) |
| [jaraco/keyring](https://github.com/jaraco/keyring) | PyPI声明MIT；源码许可未完成 | [566a2c61c8d1](https://github.com/jaraco/keyring/commit/566a2c61c8d13961185333370d7ee3a13494246f) | 未取得，不批准引入 |
| [temporalio/sdk-python](https://github.com/temporalio/sdk-python) | MIT（SDK） | [2a7d321cbe53](https://github.com/temporalio/sdk-python/commit/2a7d321cbe538c38f7c9a45fcc4c6c44733ecf85) | [原文件](reuse-first-evidence/2026-10-29/upstream-licenses/temporalio__sdk-python/LICENSE) |

## 8. 决策与本轮交付边界

| 条目 | 当前决策 | 下一动作 / 触发点 |
| --- | --- | --- |
| Vue Flow / MCP / A2A / Schema / Tauri / SQLite | 继续已有依赖，保留版本和合同回归 | 新需求先核实API；升级major先隔离兼容验证 |
| 模型SDK | 官方Python SDK作首选离线基准；LiteLLM条件候选；AI SDK保留对照 | P0-08授权后执行第5节；不自写多供应商HTTP客户端 |
| C1 / LangGraph | 暂不替换，不把C1冻结为最终引擎 | 授权的最小独立对照、迁移方案、用户确认 |
| OTel / 凭据 | 先复用现有API/系统能力，缺失部分薄适配 | 后续明确采集/秘密边界再小范围引入 |
| JSON Forms / Promptfoo / ComfyUI | 按实际复杂度与服务需求后置 | 先许可/安全/依赖/最小实验，不自动全装 |

根AGENTS已把本原则接入后续开发检查；普通胶水不做冗长研究，关键新依赖/替换必须留下比较。此表是建议和门槛，不是采用候选运行时的批准。本轮仅新增规范、评估和研究证据，更新根导航；旧实验、依赖环境、UI、历史报告和测试证据保留，不重跑未受影响套件、不制造新通过数量，不改PFT、不自动Git提交或进入P0-08。

## 后续实施增量：P0-08（2026-10-29）

本文件前述“未安装/未启动”保留为该次评估的历史范围。随后用户明确授权P0-08离线实施，已采用两种官方Python SDK；LiteLLM因安全门禁未安装，Vercel SDK未执行。实际范围、依赖闭包、用量/预算边界及未测项以[P0-08复用复核](./p0-08-component-reuse-assessment.md)和[交付报告](./p0-08-delivery-report.md)为准。未替换C1、未冻结技术栈、未进行收费调用。
