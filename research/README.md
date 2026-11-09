# 研究库使用与维护

核验基准：2026-10-24。总入口：[资料索引](./sources.md)，项目入口：[README](../README.md)。

P0-06增量（2026-10-27）：[Windows宿主与真实Tauri窗口](../experiments/p0-06/README.md)、[15项验证及18/14/18独立回归](../planning/p0-06-host-verification.md)、[IPC](../planning/p0-06-ipc-contract.md)、[生命周期](../planning/p0-06-runtime-lifecycle.md)与[架构发现](../planning/p0-06-architecture-findings.md)。新增S65，合计65条（63正文核验/2访问失败）；窗口、Rust探针与合成MCP/A2A证据分开。生产打包及跨OS未验证。

P0-05增量：[A2A独立任务实验](../experiments/p0-05/README.md)、[18项专项及18/14项独立回归](../planning/p0-05-agent-verification.md)、[兼容](../planning/p0-05-protocol-compatibility.md)与[架构发现](../planning/p0-05-architecture-findings.md)。新增S64，来源总64条（62正文核验/2访问失败）；真实协议、合成Agent行为与Mock/静态证据分开，未满足全部E01–E07生产门槛。

P0-04增量：[真实MCP实验](../experiments/p0-04/README.md)、[验证](../planning/p0-04-mcp-verification.md)、[协议兼容](../planning/p0-04-protocol-compatibility.md)与[架构发现](../planning/p0-04-architecture-findings.md)。14项新测试通过、P0-03原18项回归通过，统计独立；新增S61–S63，总63条（61正文核验/2访问失败）。仅Windows及自有可信Server，不是完整E01–E07通过。

P0-03增量：[最小运行原型](../experiments/p0-03/README.md)、[运行证据与边界](../planning/p0-03-runtime-verification.md)、[架构发现](../planning/p0-03-architecture-findings.md)。18个执行测试通过只限Windows与合成适配器；原E01–E07整体门槛保留。新增S58–S60为实现基础文档，总60条（58条正文核验/2条访问失败）。

## 分类

| 编号 | 内容 | 本轮重点 |
| --- | --- | --- |
| R01 | [可视化节点编辑](./01-visual-editor/README.md) | 画布、调参、保存、局部调试、版本 |
| R02 | [节点契约与数据交换](./02-node-contracts/README.md) | 类型、文件引用、兼容、图校验 |
| R03 | [执行引擎](./03-execution-engine/README.md) | 调度、汇合、恢复、幂等与复用 |
| R04 | [模型适配](./04-model-adapters/README.md) | 参数差异、能力发现、限额、成本 |
| R05 | [工具与Agent协议](./05-tool-agent-protocols/README.md) | MCP/A2A/HTTP/CLI边界 |
| R06 | [可观测性与评估](./06-observability-evaluation/README.md) | 追踪、成本、样本与结果比较 |
| R07 | [安全与权限](./07-security-permissions/README.md) | 凭据、注入、程序授权、隔离 |
| R08 | [Windows桌面架构](./08-desktop-runtime/README.md) | Rust与独立执行进程两路线 |
| R09 | [成熟实现对照](./09-competitors/README.md) | 证据矩阵与实际限制 |
| R10 | [技术实验](./10-feasibility-experiments/README.md) | E01–E07可执行验证设计 |

## 证据状态

- **已核实**：实际可访问的一手正文支持该能力描述；截至P0-02为55条，另2条正文访问失败。P0-01历史数为46/2。
- **待验证**：有文档或合理技术依据，但目标环境尚未实测；页面不可读时注明“正文未核验”。
- **初步设想**：本项目自己的产品、接口或实现假设，尚无实验结果。

资料条目状态与本地实验状态分别判断。规范的MUST/SHOULD描述实现义务，不保证任意服务端已经正确实现。性能数字、版别权益、费用和latest页面必须在实验前重查。

## 防重复与扩充流程

事实与来源元数据集中在sources；分类笔记只做分析、边界和验证问题；竞品页只做横向对照；实验页只保留验证协议；planning只描述候选职责和决策。添加新事实先建立S记录，再在正文链接到稳定锚点。

每次更新保留日期、版本、访问成功或失败原因、变更范围。不得把“没查到”写成“不支持”，不得把产品宣传写成已验证性能，不以文档数量衡量完成度。官方整库与模型权重不进入研究库。

## 待补资料

P0-02已补充[版本化契约](./02-node-contracts/workflow-schema-draft.md)、[适配边界](./05-tool-agent-protocols/adapter-boundaries.md)、[跨环境方案](./08-desktop-runtime/portability-and-environment-binding.md)、[场景与矩阵](./10-feasibility-experiments/compatibility-matrix.md)。本轮静态检查与真实实验分别记录，详见[检查结果](./10-feasibility-experiments/validation/README.md)。

固定版本的框架许可与再分发条款、A2A固定tag与站点版本标识差异及SDK真实互操作、GenAI追踪语义稳定状态、各OS隔离/秘密存储、Dify当前自部署版细节尚未充分研究。它们是选型门槛，不是既定实现。


## P0-07可视化执行验证（2026-10-27）

已在隔离实验中完成真实Tauri/Vue Flow画布→原Workflow Definition→C1→独立合成MCP闭环。12项后端方法、19个GUI步骤以及原18/14/18/15回归分别记录；不将本页早期“尚未执行”研究计划追溯改写为当时已通过。当前UI保留，不冻结技术栈；Windows实际窗口、WebView缩放与未验证的实体DPI明确区分。

入口：[实验](../experiments/p0-07/README.md)、[验收与截图](../planning/p0-07-workbench-verification.md)、[交付](../planning/p0-07-delivery-report.md)。

## P0-08增量（2026-10-29）

[官方SDK与真实Tauri离线闭环](../experiments/p0-08/README.md)、[专项/回归证据](../planning/p0-08-model-verification.md)、[SDK对照](../planning/p0-08-sdk-comparison.md)、[预算/凭据](../planning/p0-08-budget-and-credentials.md)。新增来源记录S66–S67；原阶段核验统计保留。真实SDK/自有HTTP响应与真实供应商推理/计费分别标记，后者尚未验证。
