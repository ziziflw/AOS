# P0-08 SDK 对照与采用依据

日期：2026-10-29。遵循 [Reuse First](reuse-first-policy.md)。本轮已获离线实现授权；保留原评估的历史范围，不替换 C1。

| 路线 | 依据 / 版本 / 许可证 | 实际对照与成本 | 结论 |
|---|---|---|---|
| 官方 Python SDK | openai **3.41.0**、anthropic **2.3.0**，本轮 wheel 均为 Apache-2.0；上游 [openai-python](https://github.com/openai/openai-python)、[anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python) | 两者实际调用自有 HTTP，文本/JSON、429、超时、取消和 usage。直接复用 Python 执行进程，无额外服务。供应商差异由 D1 薄映射承担 | **本轮主路线**。两种官方客户端是互补协议实现，不是统一覆盖全部厂商的承诺 |
| LiteLLM / core | 观察 1.106.6，核心 MIT；完整依赖较重。官方 [10月23日安全事件报告](https://docs.litellm.ai/blog/security-incident-oct-21-2026-attack-chain)确认 1.107.0 被污染 | 仅文档、元数据和许可审查；**未安装、未导入、未执行**。既有评估还发现其 openai<3 约束与官方新 major 不同，不能直接混装 | 暂缓；不将旧版或 PyPI latest 自动视为安全，不安装受污染版本。以后独立环境重验供应链及收益 |
| Vercel AI SDK | 观察 ai7.0.156、@ai-sdk/openai4.0.104、@ai-sdk/anthropic4.0.91，Apache-2.0，Node>=22；[官方设置](https://ai-sdk.dev/docs/ai-sdk-core/settings) | 本轮仅文档/锁定候选元数据审查，**未执行其 SDK**。可在可信 JS 运行时使用，不强制 Next.js。接当前 Python 需要额外 JS 边界、取消/秘密/预算协调 | 保留可信 TS 对照候选；当前两协议不值得为统一 API 新增执行进程，不能据此永久排除 TS |

本轮实际比较的是两种官方 SDK 在相同 C1/HTTP 夹具下的行为；没有宣称三套候选都实测。最小复现入口：`experiments/p0-08/test_models.py` T01/T03/T05/T08。原始失败证据揭示 Anthropic 的 URL 拼接规则与 OpenAI 不同，修正 base URL 后两协议通过。

官方 [OpenAI Python 文档](https://developers.openai.com/api/reference/python)与 [Anthropic Python 文档](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python)用于确认 async 客户端、异常和重试入口；本轮将 SDK 自动重试设为 0，使用有界超时，并关闭环境代理与重定向。对确切行为的结论来自安装版本和本机请求事实，不把在线文档等同固定制品。

SDK提供 HTTP/序列化/响应对象及供应商异常；AOS没有自写两套供应商 HTTP 客户端。JSON Schema校验继续复用 jsonschema，图和状态仍复用 C1。结构化输出的请求字段由 SDK 发送；业务输出 Schema仍由 C1独立验证，不将“能返回 JSON 文本”当成 schema 合格。

新依赖隔离在 P0-08 `.venv`。openai/anthropic 当前版本依赖 **httpx2 2.16.0 / httpcore2 2.16.0**，与原 MCP/A2A 的 httpx0.28.1 并存；没有升级 P0-06 环境。完整闭包、精确哈希和全部 wheel 许可见 [依赖审查](../experiments/p0-08/evidence/dependency-review.json)及 [锁文件](../experiments/p0-08/sdk-requirements.lock)。jiter、pydantic-core、pywin32 等含 Windows 原生构件，不能把本机 venv 直接当跨平台包。`pip check`通过只证明声明依赖一致，不代表无漏洞或打包完成。

总成本判断：本轮两协议直接 SDK 集成最小；供应商增多后须重新比较映射维护量与成熟聚合组件的安全/升级成本。未冻结 SDK 组合或正式产品技术栈。
