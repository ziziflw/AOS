# P0-01交付与质量报告

日期：2026-10-24（Asia/Shanghai）。交付状态：**技术研究库已建立；所有实验未执行；架构与需求未冻结。**

## 创建位置与隔离

实际位置：`D:\AIOrchestrationStudio`。创建前只读检查确认目录不存在，D盘可用后新建。所有交付写入均限定在该目录；没有在PFT仓库中建项目，没有对PFT源码、数据库、文档、Git或运行环境执行读写/变更命令，也没有复制其功能基线。

没有修改当前ChatGPT项目的synced sources或AGENTS.md。本轮未定位或取得PFT初始文件指纹，因此“未修改PFT”依据本轮操作范围；不是对其他进程在此期间行为的全盘审计。

## 完整目录树

```text
D:\AIOrchestrationStudio
├── README.md
├── research
│   ├── README.md
│   ├── sources.md
│   ├── 01-visual-editor
│   │   └── README.md
│   ├── 02-node-contracts
│   │   └── README.md
│   ├── 03-execution-engine
│   │   └── README.md
│   ├── 04-model-adapters
│   │   └── README.md
│   ├── 05-tool-agent-protocols
│   │   └── README.md
│   ├── 06-observability-evaluation
│   │   └── README.md
│   ├── 07-security-permissions
│   │   └── README.md
│   ├── 08-desktop-runtime
│   │   └── README.md
│   ├── 09-competitors
│   │   └── README.md
│   └── 10-feasibility-experiments
│       └── README.md
├── planning
│   ├── project-charter-draft.md
│   ├── module-boundaries-draft.md
│   ├── open-decisions.md
│   └── p0-01-delivery-report.md
└── decisions
    └── README.md
```

共18份Markdown文件、13个子目录；没有空研究分类。每个研究分类只建一份笔记，避免重复拆文档。planning包含三份要求的草案及本报告，decisions只保留记录规则。

## 资料数量及证据范围

[资料总索引](../research/sources.md)共**48条记录：46条已核实文档内容，2条正文访问失败**。统计单位是可独立追溯的资料记录，不是软件产品、URL数量或打开次数。每条均列名称、分类、官方URL、核验日期、版本/适用范围、核实事实、关联/复用理由、未验证内容及实验。

失败记录为S47 Anthropic旧Messages入口（正文过大）和S48 Dify自部署索引（工具不可访问）。参数结论另据可访问的Claude版本页；Dify使用官方产品页与历史调试文章，保留当前版别未核验限制。Flowise API曾在浏览工具失败，后以只读HTTP请求成功获取元数据，成功及失败途径均记录。

**没有运行任何候选软件，也没有通过E01–E07。** 一手文档支持不等于目标Windows环境兼容、性能、安全或恢复已证明。

## 重要技术事实与实际含义

1. Vue Flow提供节点、端口与图导出等交互能力，不能据此认定调度、恢复与权限已经解决。[S01–S03](../research/sources.md#s01)
2. LangGraph暂停恢复会重跑所在节点，暂停前副作用需幂等；持久化不自动保证外部操作只执行一次。[S18/S19](../research/sources.md#s18)
3. Temporal已有事件历史与重放机制，但Service/Worker及确定性约束必须计入本地复用成本；尚不能判定优于或劣于自主层。[S20](../research/sources.md#s20)
4. 统一模型SDK仍存在供应商差异。Claude API 2026-10-21明确移除采样参数，能力需按模型、端点和API版本记录。[S22–S27](../research/sources.md#s22)
5. MCP本地stdio和远端Streamable HTTP有不同生命周期与安全要求；Agent任务需要另保留任务状态与产物语义。[S28–S30](../research/sources.md#s28)、[S44/S45](../research/sources.md#s44)
6. SQLite WAL同机读写可并行，但仍单写者，也不替代业务恢复协议。[S21](../research/sources.md#s21)
7. Tauri权限约束主要面对WebView的IPC暴露；独立进程/Job Objects不自动形成文件与网络沙箱。[S36–S38](../research/sources.md#s36)
8. 单步调试、人工介入、版本和恢复在成熟产品中已有实现，不能宣称为本项目独有创新。n8n完整历史有版别条件。[S09–S12](../research/sources.md#s09)、[S43](../research/sources.md#s43)
9. Flowise官方最新发布元数据为flowise@3.1.4，published_at=2026-07-29T15:51:25Z；可确认存在近期发布活动，不能写成停止维护，也不构成长期维护承诺。[S42](../research/sources.md#s42)

## 无法确认、存在版本差异或证据不足

- AI SDK滚动文档页面标示v7、Langflow标示1.13.x、Vue Flow标示1.48.2；它们是查阅快照，未选定安装版本。包/API兼容和依赖许可须在实验前锁定复核。
- LiteLLM旧模型参数表仍有temperature支持，Claude新API版本删除该参数；应按模型与版本区分，不构造统一支持结论。
- A2A latest页含1.0与0.3兼容描述；未固定规范tag与SDK，不能保证互操作。
- Dify产品声明、1.5.0历史文章与当前自部署版不能简单等同；失败索引未被当作已查阅正文。
- Node-RED Projects页含历史0.18预览措辞，不能据此判断当前默认开关。
- vLLM原生Windows运行、模型硬件资源、不同框架的并行/恢复语义、真实隔离效果、完整token费用核对、离线安装均未实测。
- AppContainer等隔离路线、第三方再分发许可、独立Agent互操作仍有资料缺口；已列入后续研究。

## 初步模块职责和依赖

[模块草案](./module-boundaries-draft.md)暂分10个逻辑职责：A1画布操作、A2检查评估、B1定义校验、C1运行控制、D1模型/D2工具/D3 Agent适配、E1存储产物、E2策略审批、E3桌面与系统能力。

主要路径为A1→B1校验→C1调度→E2授权→D适配/E3受控执行→C1经E1保存→A2展示。C1唯一拥有业务状态转换，E2唯一决定授权，B1唯一解释定义。E1不调度、E3不重试业务、A2不更新run状态。逻辑职责不等于十个独立服务或固定进程。

## 下一阶段验证建议

优先顺序为：**E01 → E07最小探针 → E02/E03 → E04 → E06 → E05 → E07完整分发复核**。先确保图/契约和Windows宿主可行，再验证真实接口、调度、授权与崩溃窗口。每项[实验设计](../research/10-feasibility-experiments/README.md)含目标、输入、步骤、通过标准、失败条件、风险和来源。

最需原型回答的问题：能否复用成熟运行时而保持自定图语义；状态权威放在哪个进程；未知外部副作用如何恢复；审批是否在每条执行路径强制；真实参数/费用能否完整解释；Windows干净环境的依赖和进程清理是否可靠。

## 需要用户后续决定的输入

本轮无需等待用户决定。下一阶段需确认：优先使用场景、Windows版本/架构和安装方式、两家供应商及实验预算、初版插件信任范围、是否必须纳入独立Agent/A2A。详细选项及影响见[开放决策](./open-decisions.md)。不要求在实验前确定Rust或TS。

## 质量检查

文件级检查已完成：18份Markdown、13个子目录；171处内部相对链接（包括显式来源锚点）全部可解析；48个来源编号与46条文档核实/2条正文未核验统计一致。全部R01–R10目录有内容，索引均可导航。

对跨文档完全相同且不少于100字符的长段落进行扫描，重复数为0；人工复核了定义/调度/授权职责、关键结论的来源与假设标记。该扫描不声称消除所有语义相近表述；必要交叉引用保留。

外部链接核验依据本轮实际读取的一手正文及访问失败结果；没有把HTTP可达、首页可读或搜索摘要单独当作完整能力证明。滚动版本和无法访问项已单列，所有性能/恢复/隔离实验仍为未执行。

目录中非Markdown文件数为0；没有Git元数据、依赖目录、工程清单、数据库、模型或第三方代码。PFT和同步sources未被本轮变更；本报告前述审计边界保持不变。

## 范围结束

本轮只创建Markdown笔记与草案；没有模型、依赖、第三方仓库、语言工程、数据库或Git元数据；没有提交、推送、重置或清理。交付后停止，不自动进入P0-02。

