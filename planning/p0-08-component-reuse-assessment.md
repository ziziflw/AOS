# P0-08 组件复用复核

延续 [组件总评估](component-reuse-assessment.md)，本轮由文档比较进入限定实测。

| 模块 | 直接复用 | AOS必要适配 / 成本与风险 |
|---|---|---|
| 模型D1 | openai3.41.0 / anthropic2.3.0 async SDK | 固定能力Schema、消息/usage/错误映射、安全边界；未复制或改SDK协议内部源码。更多厂商意味着更多能力测试，未承诺全覆盖 |
| 画布/检查器 | Vue3.5.44、VueFlow1.48.2、background1.3.2；P0-07原交互 | 添加模型类型/受检场景、预算控件与权威用量显示；不重做几何、连线、表单框架或主题 |
| 状态/预算/审批 | 原C1、SQLite、jsonschema4.26.0、原ControllerLock | 一个默认不变的usage钩子，加可信子类准入/结算；不引入独立结算数据库或第二调度器。未知预留/费用字段仍需正式契约收敛 |
| 宿主/IPC | Tauri2.12.5、Rust原Job/权限/定长帧、原P0-07编辑接口 | 隔离宿主副本只切换固定P0-08执行进程；不开放任意URL、路径、脚本或命令。宿主自有胶水副本未来可提取公共包，当前保留回归基线 |
| MCP/A2A | 官方mcp1.30.0、a2a-sdk1.2.3及原D2/D3 | 不修改协议，P0-08额外实际调用MCP，A2A跑原完整回归；没有新增A2A GUI或把模型调用当Agent委托 |
| 凭据 | 既有pywin32 312 / Windows Credential Manager | 自有假凭据目标与受限别名映射；无自研密码学，真实用户凭据入口待授权设计 |
| 追踪 | 既有opentelemetry-api1.45.1保留 | 本轮未安装SDK/exporter或建立遥测服务；SQLite事件是既有恢复证据，不宣称OTel追踪完成 |

第三方 wheel 未本地修改。完整版本/传递依赖/许可证/原生构件与哈希在 [dependency-review.json](../experiments/p0-08/evidence/dependency-review.json)；许可和NOTICE原文保留于 [third-party](../experiments/p0-08/third-party)。Vue/Tauri依赖沿用本轮独立 package-lock / Cargo.lock，实际包内许可仍在本地依赖分发中；正式打包还须自动汇总完整声明。

闭包中的aiologic/culsans轮子缺独立许可文件，已依据相同发行版的PyPI源归档补齐ISC及文档CC-BY-4.0原文；归档只读未执行，来源/sha256见 supplemental-source-licenses.json，不能把metadata classifier当完整许可原文。55个锁定运行发行版、加venv自带pip共56份元数据，统计不冒充55项新依赖。

本轮未复制限制性许可证代码。LiteLLM受安全门禁暂缓，Vercel AI SDK仅文档候选，原因和未测范围见 [SDK比较](p0-08-sdk-comparison.md)。SDK升级首先影响D1调用/能力/usage/异常及原生依赖，需重跑两协议、预算、未知状态和窗口回归；禁止在旧实验环境原位升级。

Windows新venv实际约**114.1MiB**，包含既有MCP/A2A及新SDK闭包，**不含基础Python分发**、npm/Rust构建缓存和安装包。venv引用本机基础Python，不能复制文件夹就宣称发行完成。生产包还要解决Python运行时、jiter/pydantic-core/pywin32架构、证书、WebView2、DLL许可、干净机器安装和升级。Linux/macOS需各自构建并替换凭据/进程适配，未验证。

LangGraph/Temporal仍是未来独立对照候选；持久化/interrupt与C1的authority、未知副作用、取消和审批必须逐条对照后提出迁移/回滚，经用户确认再替换。本轮不换执行引擎。ComfyUI未来应从官方服务API接入，不复制其执行内核、插件或模型。本轮保留P0-03～07全部代码及证据作回归基线，没有因复用原则而大规模推翻已验证模块。
