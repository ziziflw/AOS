# AI Orchestration Studio

AOS 是本地优先的 Windows 可视化工作流工作台。当前开发入口 **P0-11** 使用浅色 Vue / Vue Flow 画布，通过 Tauri 宿主启动独立 Python C1 执行器。工作流可以编辑、校验、保存、重开和执行。节点状态、审批和最终结果由 C1 的 SQLite 运行记录决定。

[启动集成工作台](apps/aos-workbench/启动集成工作台.cmd) · [Windows 启动说明](START_HERE.md) · [使用手册](docs/USER_GUIDE.md) · [故障排查](docs/TROUBLESHOOTING.md)

- **立即试用**：点左侧「文件」，选择 [WF-02 本地工具协作](examples/workflows/README.md)，再点「运行」。此示例只使用项目自有 MCP Echo 服务。
- **本地模型**：在 LM Studio 启动已有模型，在「模型」中测试回环地址、选择服务返回的模型 ID 并保存。已使用 google/gemma-4-e4b 实测文本推理和任务提取。
- **实现位置**：Vue 控制逻辑与集成视图在 demo/studio/frontend，Rust 宿主在 demo/studio/host，独立启动入口在 apps/aos-workbench。私有执行环境由 v0.1.3 便携目录初始化；每次运行及其事件保存在 P0-11 用户目录。
- **适用范围**：本机开发构建；A2A 已有后端实验，尚无正式管理界面。材料预览用的 React 草稿页面、LT01 专用执行目录与新版桌面工作区各有独立入口。现有 [v0.1.3 便携发行包](dist/AOS-Demo-v0.1.3-win-x64.zip) 仍对应旧界面。
- [标准工作流及依赖](examples/workflows/README.md) · [P0-11 接口、实机验收及限制](planning/p0-11-integration-report.md)

## 历史研究与实验入口

面向需要可视连接模型、工具、独立 Agent、本地程序与数据组件的个人研究者和开发者。项目暂定名不构成商标或发布承诺。本目录是独立研究空间，与 Personal File Tags（PFT）没有源码、数据库或需求继承关系。

## 从这里阅读

1. [P0-01交付与质量报告](./planning/p0-01-delivery-report.md)：目录树、核验统计、主要发现及限制。
2. [资料总索引](./research/sources.md)：65条来源记录（63条文档核验、2条正文访问失败）、版本与验证边界。
3. [研究导航与维护规范](./research/README.md)：R01–R10研究笔记。
4. [预立项草案](./planning/project-charter-draft.md)、[模块职责草案](./planning/module-boundaries-draft.md)、[开放决策](./planning/open-decisions.md)。
5. [E01–E07实验设计](./research/10-feasibility-experiments/README.md)：保留原整体门槛；P0-03/P0-04/P0-05分别提供内核、真实MCP与独立Agent的受限证据。
6. [决策记录规则](./decisions/README.md)：本轮没有已接受架构决策。

## P0-08 完成时的实验边界

本目录保存研究资料与独立的experiments/p0-03至p0-08实验、合成夹具和SQLite证据，包含可操作的实验性Tauri/Vue Flow画布与原执行器联动，没有生产发行应用。新增SDK只在各自.venv并锁定依赖；未安装模型、不可信插件/Agent或擅自提交Git。原研究和117项静态检查保留，PFT与真实账户未操作。

## P0-02入口

- [交付报告](./planning/p0-02-delivery-report.md)、[架构审查](./planning/p0-02-architecture-review.md)、[开放决策](./planning/p0-02-open-decisions.md)。
- [工作流契约](./research/02-node-contracts/workflow-schema-draft.md)、[端口契约](./research/02-node-contracts/node-port-contracts.md)、[能力声明](./research/02-node-contracts/adapter-capabilities.md)。
- [跨环境绑定](./research/08-desktop-runtime/portability-and-environment-binding.md)、[三个场景及测试矩阵](./research/10-feasibility-experiments/compatibility-matrix.md)。

L1定义兼容是必须的设计目标，L2执行依赖环境满足并需实测，L3完整环境迁移不承诺。顺序为Windows x64→Linux x64→macOS；Windows已有模拟内核、真实MCP和自有A2A任务服务证据；Linux/macOS、真实模型及任意第三方Agent仍未验证。

“已核实”指一手文档支持，不等于已安装、已运行或已通过实验。运行结论以对应证据范围为准；生产性能、OS隔离及跨框架兼容性仍需验证。建议与架构假设会显式标记，引用可经S编号追溯。

## P0-03入口

- [实验代码与复现方法](./experiments/p0-03/README.md)、[运行验证](./planning/p0-03-runtime-verification.md)、[架构发现](./planning/p0-03-architecture-findings.md)、[交付报告](./planning/p0-03-delivery-report.md)。
- [通过套件18项](./experiments/p0-03/evidence/suite-20261024T034720437972Z/summary.json)，[首轮失败记录](./experiments/p0-03/evidence/suite-20261024T033548013484Z/summary.json)保留。
- 原契约能够驱动受限执行，但required输出和policy作用域须澄清；没有修改原Schema、冻结技术栈或自动进入P0-04。

## P0-04入口

- [实验与运行方法](./experiments/p0-04/README.md)、[运行验证](./planning/p0-04-mcp-verification.md)、[协议兼容](./planning/p0-04-protocol-compatibility.md)、[架构发现](./planning/p0-04-architecture-findings.md)、[交付报告](./planning/p0-04-delivery-report.md)。
- [最新执行证据](./experiments/p0-04/evidence/latest.json)：固定MCP 2025-11-25 / SDK 1.30.0；真实stdio与独立自有Server，不代表任意第三方工具或OS沙箱。
- 继续复用原C1，两个Schema扫描小修正已由原18项回归验证。14项新测试和18项回归分开统计，完成后不自动进入下一阶段。

## P0-05入口

- [独立Agent实验与运行方法](./experiments/p0-05/README.md)、[任务验证](./planning/p0-05-agent-verification.md)、[协议兼容](./planning/p0-05-protocol-compatibility.md)、[架构发现](./planning/p0-05-architecture-findings.md)、[交付报告](./planning/p0-05-delivery-report.md)。
- [最新专项证据](./experiments/p0-05/evidence/latest.json)：A2A线版本1.0、SDK1.2.3，独立异步任务、查询恢复、取消确认、双Agent并行与产物验证。
- C1仅提取默认恢复扩展点，Agent子类只恢复原任务查询；无法核实不重发。三套测试分开统计，未自动进入下一阶段。

## P0-06入口

- [复现与代码](./experiments/p0-06/README.md)、[15项验证](./planning/p0-06-host-verification.md)、[IPC契约](./planning/p0-06-ipc-contract.md)、[生命周期](./planning/p0-06-runtime-lifecycle.md)、[架构发现](./planning/p0-06-architecture-findings.md)、[交付报告](./planning/p0-06-delivery-report.md)。
- [最终机器证据](./experiments/p0-06/evidence/suite-20261027T121250322189Z/summary.json)：真实Rust宿主、原C1、官方MCP/A2A合成服务与实际Tauri2/WebView2分别验收；唯一状态权威、后端审批、Job成员清空及原taskId恢复。
- 原P0-03至P0-05源代码未改；原18/14/18项回归分开通过。关闭I/O失败及修正保留；未验证生产打包、恶意程序隔离或Linux/macOS，未冻结Python，停止于P0-06。

## 桌面UI/UX预研（P0-07采用A方向）

- [设计预研入口与三方向对比](./design/ui-ux-prestudy/README.md)、[布局/信息架构](./design/ui-ux-prestudy/design-direction.md)、[核心组件](./design/ui-ux-prestudy/components-and-interactions.md)、[动态Schema与能力边界](./design/ui-ux-prestudy/schema-and-capability-boundaries.md)。
- 项目级`frontend-design`已审查安装至`.agents/skills`并通过Codex原生发现验证；[技能审查](./design/ui-ux-prestudy/skill-audit.md)。UI/UX Pro Max只评估、未安装。
- 原静态设计稿和审查历史保留；P0-07采用A · Graphite。原P0-06界面/引擎/IPC/MCP/A2A实现不改，新工作台隔离在p0-07。


## P0-07入口

- [启动与操作](./experiments/p0-07/README.md)、[启动脚本](./experiments/p0-07/launch.ps1)、[实际验收](./planning/p0-07-workbench-verification.md)、[IPC扩展](./planning/p0-07-ipc-extension.md)、[架构发现](./planning/p0-07-architecture-findings.md)、[交付报告](./planning/p0-07-delivery-report.md)。
- [最新后端证据](./experiments/p0-07/evidence/latest-backend.json)、[真实Tauri窗口证据](./experiments/p0-07/evidence/latest-gui.json)、[独立SQLite/源码/进程核对](./experiments/p0-07/evidence/delivery-audit.json)。12测试方法和19个GUI步骤分开统计；原回归18/14/18/15各自通过。
- 当前UI按用户要求保留，后续设定后完善。已实现画布编辑、Schema属性、保存/重载与原C1真实MCP合成执行；模型仍为明确模拟，A2A未新增GUI入口，真实显示DPI/生产打包未验证。未冻结技术栈，不自动进入下一阶段。

## Reuse First（2026-10-29起执行）

[项目级开发约束](./AGENTS.md) → [成熟技术优先复用原则](./planning/reuse-first-policy.md)与[主要组件复用评估](./planning/component-reuse-assessment.md)。新的核心功能先比较已有依赖、成熟SDK/组件、服务和源码复用；自研必须有需求缺口与总成本依据，普通胶水从简。

本次仅完成规范和评估，未自动进入P0-08、安装模型SDK或改动旧实验。C1保持唯一状态权威，重大替换需实际对照与迁移方案经确认；P0-08优先做成熟SDK离线比较，不自写多供应商HTTP协议栈。候选的当前安全和依赖冲突在评估中明确记录，技术栈不冻结。

## P0-08入口

- [启动/复现](./experiments/p0-08/README.md)、[交付报告](./planning/p0-08-delivery-report.md)、[实际验证](./planning/p0-08-model-verification.md)。
- [SDK比较](./planning/p0-08-sdk-comparison.md)、[模型兼容](./planning/p0-08-provider-compatibility.md)、[预算/凭据与真实API准备](./planning/p0-08-budget-and-credentials.md)、[复用复核](./planning/p0-08-component-reuse-assessment.md)。
- 使用官方openai3.41.0与anthropic2.3.0、真实本机HTTP和原C1；合成响应不代表真实推理。模型20方法/宿主4方法/窗口12步骤及旧阶段回归分开统计，保留失败记录。真实供应商未配置、收费调用未授权；不自动进入P0-09。
