# 场景A · 多模型协作与结果比较

状态：设计与离线契约检查完成，真实模型/并行调度未验证。相关E01/E02/E04；[工作流JSON](../02-node-contracts/examples/scenario-a.workflow.json)、[独立运行输入](../02-node-contracts/examples/scenario-a.run-request.json)、[类型与参数catalog](../02-node-contracts/examples/fixture-catalog.json)。

## 用户需要与节点关系

用户希望同一任务由不同供应商独立生成，再由审查模型比较；必须看到有效参数、不同输出、调用失败和费用，避免只比较漂亮结果。

```text
task → task-to-text → modelA ─┐
                    modelB ─┴→ join(all, edge-order) → review → package → output
                                      └─ candidates ──────────┘
join.done --control--> review.ready
```

task对应core.input.task，prompt对应core.task-to-text；modelA/modelB为model.generate；join为core.join-candidates；review为model.review；package为core.package-comparison；output为core.output.comparison。共8节点、10边。

## 完整输入输出

精确字段/required/additionalProperties约束以catalog.types和workflow.inputSchema/outputSchema为准，不由示例文字替代。

| 节点 | 输入 | 数据输出 |
| --- | --- | --- |
| task | RunRequest.inputs.task = Task{objective:string,context:string[]} | out:Task |
| prompt | in:Task | out:Text；只使用显式context，映射固定 |
| modelA/modelB | prompt:Text | out:Candidate{answer:string,provider:string,usage:Usage} |
| join | items:Candidate many；modelA.order=0/modelB.order=1 | out:CandidateSet{candidates:恰好2份Candidate} |
| review | in:CandidateSet；可选ready控制依赖 | out:Review{conclusion:string,findings:string[]} |
| package | review:Review与candidates:CandidateSet | out:Comparison{review:Review,candidates:CandidateSet} |
| output | in:Comparison | 工作流最终Comparison |

每节点另有可选ready控制输入、done控制输出、Error错误输出；error按当前policy.stop结束依赖分支。Usage精确字段为availability(reported/estimated/unknown)、inputTokens/outputTokens/costMinor（整数或null）、currency/priceSnapshot（字符串或null）。D1填真实usage，不让模型生成计费数字；审查模型本身的usage经运行事件进入A2总账，最终Comparison内的Candidate usage不等于整次run费用总额。

## 环境与预计真实接口

需要两家供应商的已锁模型/API/能力、一个审查模型服务、网络权限与三项secretRef绑定。后续真实接口候选为Claude Messages API 2026-10-21（[S27](../sources.md#s27)）及Gemini generateContent v1beta（[S56](../sources.md#s56)）。精确modelId、额度、SDK待实验前决定，不能直接用fixture名称调用。

JSON中fixture.model.a/b只用于证明参数差别；A不支持temperature、B支持0–1。切到真实供应商必须替换已核验catalog、能力/环境目标并新建workflow修订，禁止静默重绑定改变参数含义。环境模板当前缺凭据且指向.invalid，因此设计上阻断执行。

## 后续步骤、通过与失败

1. 固定输入与两份真实能力快照，分别验证普通/流式/结构化调用和usage；实验前规定费用/请求上限。
2. 用事件时间证明两生成节点执行区间重叠，反序完成不改变Candidate顺序。
3. 审查只在两份validated终值齐备后运行；任一结构错误不得进入review。
4. 用相同workflow、不同显式参数形成新修订和新run；对比有效参数、质量、延迟、重试及全部模型费用。

通过：两家真实端点都成功；无静默丢参数；并行有时间证据；all汇合恰好一次；字段结构通过输出Schema；usage缺失可见，review费用也纳入总账；修改modelA只影响其后继闭包，modelB历史结果不被误判失效。
失败：只画并列但串行；按返回顺序接错数据；某支失败却伪造两份成功结果；用LLM自报token；取消后费用归零；把fixture静态通过当真实兼容。

## 核心要求与未验证

要求B1固定修订/参数Schema、C1管理并行与顺序/预算、D1保留差异与原始usage、A2比较运行来源。当前只证明结构/config/夹具能力及样例I/O合法；真实供应商参数、流取消、成本、并行、质量和跨OS执行均未验证。

