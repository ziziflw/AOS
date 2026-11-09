# P0-02离线静态检查

日期：2026-10-24。结果：[static-check-results.json](./static-check-results.json)；脚本：[validate_contracts.py](./validate_contracts.py)。

## 实际环境与结果

现有Python 3.12.14、PowerShell 7.6.5，主机报告Microsoft Windows 10.0.22631/AMD64。使用内置Test-Json（底层JsonSchema.NET）校验Draft 2020-12对象；Python标准库仅组织夹具、有限语义检查和结果记录。Python的jsonschema和已探测Node Ajv未发现，**没有安装任何新依赖**。Python用于检查不代表选择最终执行语言。

共117项预期检查通过、0项失败。这里的“通过”含正例被接受和负例按预期拒绝，不能理解为117项产品功能已实现。根文档9份（1份catalog、3份workflow、3份run-request、2份环境模板）均结构合法；另对实际节点config/能力配置、输入输出与Envelope负载及nullable分层检查。

## 覆盖与明确未覆盖

- Schema：必填版本、字段/数值、参数差别、输出类型、文件引用、namespaced扩展、未知节点结构。
- 有限语义：节点/端口/版本、通道/方向/类型/nullable/基数、必填、汇合顺序、直接环、子图引用、disabled来源和危险重试。
- 有限声明预检：环境模板中的OS/arch、service/connection/credential引用、target漂移。模板均有未绑定凭据；即使标configured仍保留PRE_RUNTIME_UNVERIFIED。
- 保留：Python JSON值级往返保留未知节点、未知核心字段和扩展；**不是产品导入保存器实测，也不保留字节格式**。
- 影响与职责：样例后继闭包、设计中提出的模块导入依赖DAG；**没有应用代码可扫描真实模块依赖**。
- 秘密：已知敏感字段名拒绝检查；不能证明任意prompt/自由文本不藏秘密。

未测试：模型调用、MCP连接、Agent任务、并行调度、条件/skip传播、循环执行、人工审批、OS权限/沙箱、真实密钥访问、文件挂载读取、持久恢复、产品迁移器、Linux/macOS环境。结果文件将这些真实运行计数明确记录为0。

## 复现

在现有Python环境执行：

```powershell
& 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'D:\AIOrchestrationStudio\research\10-feasibility-experiments\validation\validate_contracts.py'
```

脚本要求PATH可找到已有pwsh/Test-Json，不自行安装。会用临时文件批量传递测试夹具，结束后清理；只将最终结果写回本validation目录。未运行任何业务节点或外部网络请求。结果保留Schema/catalog/各输入与检查脚本的SHA-256，便于确认验证对应的文件。

Schema编译和有限正负样例不构成完整官方一致性套件。子图I/O映射、任意Schema可赋值推理、迁移正确性、恶意Schema资源耗尽等仍需专项验证；不能为增加通过数而放宽这些要求。

