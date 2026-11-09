# AOS 标准工作流

在 P0-11 工作台点击左侧「文件」再选示例。每个示例的 workflow.json 采用 P0-02 原生定义；layout.json 只记录坐标。内置入口将两者组合为工作台文档。文件导入入口接受含 workflow 和 layout 的组合 JSON。批准、状态和输出来自 C1。

|示例|节点、输入和环境|独立验收条件与结果|
|---|---|---|
|WF-01 文本信息提取|文本输入 → 追加 JSON 要求 → LM Studio → aos.validate-tasks → 受审批的输出。需配置并加载 Gemma；无需 MCP。输入为小林整理清单、小陈更新说明的合成会议记录。|一次生成，Schema 校验通过，输出前等待批准。实际得到两项任务，负责人为小林和小陈，期限为“周五前”和 null。非法 JSON / 缺字段停在校验节点。[记录](../../experiments/p0-11/evidence/WF-01-1794200917789/WF-01.json)|
|WF-02 本地工具协作|文本输入“核对模拟订单 A-17” → 追加“ / 已整理” → 封装参数 → 自有 MCP stdio echo_text → 解包 → 输出。需私有 Python/MCP，无需模型或人工批准。|最终文本逐字等于“核对模拟订单 A-17 / 已整理”。真实工具节点一个 attempt，模型用量为零。端口类型不匹配将拒绝连接。[记录](../../experiments/p0-11/evidence/portability-1794201236758/WF-02.json)|
|WF-03 人工审批|同一输入 → 确定性生成“ / 建议登记核查” → 封装参数 → 受控 MCP simulated_effect → 解包 → 输出。仅写入本次运行的合成账本，不需要模型。|未批准时工具 attempt 为零，错误指纹被拒，恢复后仍须批准；点击批准后工具执行一次。取消时工具未执行。[记录](../../experiments/p0-11/evidence/WF-03-1794201245104/WF-03.json)|

模板来自既有 AOS 提取模板与 P0-07 的 echo / effect 场景，移除后两个场景不必要的合成模型节点。加载 WF-01 时检查目标服务和已配置模型；故障保留可编辑的图，运行时仍复核连接。工具能力在 C1 校验和实际 SDK 调用时验证。

组织方式参考 [n8n AI 模板](https://n8n.io/workflows/categories/ai)、[人工复核示例](https://n8n.io/workflows/13847-production-ai-playbook-human-oversight-exercise-1/) 与 [ComfyUI 模板目录](https://github.com/Comfy-Org/workflow_templates)。分步处理和分支职责参照 [Dify Workflow](https://dify.ai/zh/workflows)，画布交互、IPC 与本机模型发现分别查阅 [Vue Flow](https://vueflow.dev/examples/)、[Tauri](https://v2.tauri.app/develop/calling-rust/) 和 [LM Studio](https://lmstudio.ai/docs/developer/rest)。移植内容仅使用 AOS 原有节点与定义。
