# 场景C · 多Agent执行、验证与人工审批

状态：设计与离线检查完成；真实Agent、审批、取消/恢复和循环调度未执行。关联E04/E05/E06；[主图与修复子图JSON](../02-node-contracts/examples/scenario-c.workflow.json)、[运行输入](../02-node-contracts/examples/scenario-c.run-request.json)。

## 用户需要与节点连接

用户希望多个具有独立任务身份的Agent协作产出结果，失败后有界修复，同时能控制高影响任务提交和最终发布，避免取消不明或重复写入。

```text
goal → planner → executor[提交前审批] → validate → branch(valid?)
                                               ├─pass────────────┐
                                               └─fail→repairLoop ┤
                                                     最多2轮      ↓
                                                   merge(exclusive)
                                                         ↓
                                               approval[发布批准] → output
repair-body: feedback → repairAgent[每轮提交前审批] → validateRepair → bodyOutput
```

主图9节点、9边，修复子图4节点、3边。未选路径标记skipped并传播；merge恰好接一条active路径。修复耗尽且仍invalid则抛LoopLimitExceeded，不能将其作为正常有效结果发布。

## 完整输入输出与作用域映射

| 节点 | 输入 | 数据输出 |
| --- | --- | --- |
| goal | inputs.goal:Goal{objective:string,allowedScope:string[]} | out:Goal |
| planner | in:Goal；config.skill=plan | out:Plan{steps:非空string[],scope:string[]} |
| executor | in:Plan；skill=execute | out:ExecutionResult{artifact:FileReference,operationId:string,effectState:confirmed或unknown} |
| validate | in:ExecutionResult | out:Validation{valid:boolean,issues:string[],result:ExecutionResult} |
| branch | in:Validation；/valid==true | pass:Validation或fail:Validation，只激活一个 |
| repairLoop | in:Validation | out:达到valid条件的Validation；失败走Error而非输出无效终值 |
| feedback | 子图inputs.feedback:Validation（循环控制器包装上一轮反馈） | out:Validation |
| repairAgent | in:Validation；skill=repair | out:ExecutionResult |
| validateRepair | in:ExecutionResult | out:Validation |
| bodyOutput | in:Validation | 每轮返回Validation给循环控制器 |
| merge | items:Validation many；pass.order=0、repair.order=1 | out:恰好一份active Validation |
| approval | in:Validation，config绑定release-artifact操作及参数 | approved:原Validation；rejected:Error，不能继续发布 |
| output | in:Validation | 工作流最终Validation |

所有节点使用统一ready/done/Error端口。Validation校验器必须真实检查内容与产物、确认副作用；effectState=unknown时不能认定valid。Agent任务的taskId、contextId、原始状态与消息在D3/C1运行记录中保存，不塞回Plan或workflow文件。远端FileReference先授权传输并由E1登记本地产物，不能信任任意远端路径。

## 环境与预计真实外部接口

固定候选A2A规范tag v1.0.1、线协议1.0、Python SDK 1.2.3；先使用两个独立的无副作用A2A测试服务作为规划/执行端，经Agent Card发现与SendMessage/GetTask/CancelTask验证真实协议。修复可复用执行端的独立skill。此类服务后续才建立，本轮没有连接；对真实第三方Agent产品的兼容尚待用户指定可调用端点。

MCP可作为Agent内部受控工具，但不把MCP工具调用冒充独立Agent任务。没有可调用接口的桌面软件不纳入通用自动化。

## 两道审批与远端信任

executor和每轮repairAgent在提交前由E2按goal/plan作用域、目标Agent、参数摘要、权限和成本批准；最终approval仅授权发布已验证产物，不追溯批准此前副作用。计划扩大scope必须再次批准，不能让模型自行授权。

本地E2无法拦截不合作远端Agent内部每次工具操作。必须使用可约束/可审计的服务或可信外部系统；若接口无法满足该信任条件，应拒绝高影响Agent实验或缩减为无副作用任务。此限制不能靠Prompt或最终确认框消除。

## 后续故障步骤与标准

1. 固定goal、Agent Card/skill/规范与SDK版本，按审批完成一次任务，保存taskId与产物。
2. 让首次结果invalid，走修复；覆盖第1轮成功、第2轮成功、两轮均失败及人类拒绝。
3. 在提交后未知响应、等待审批、等待远端结果、产物已完成四处中断并重启。
4. 取消运行中的Agent任务；确认远端canceled后才报告cancelled；无法确认则unknown并停止新派发。
5. 同一逻辑任务重连优先GetTask；不确定时禁止盲目SendMessage。真实写操作须服务支持幂等键/查询，按其规范验证。

通过：独立taskId和状态可恢复；无批准零高影响提交；旧批准不适用于修改后的plan；每轮有独立iterationPath、操作身份和审批；最多2轮；重复响应/重连不产生重复已确认操作；分支/汇合不死等；取消与未知结果可解释。
失败：用一次字符串响应假称Agent生命周期；循环无限；取消请求发送后立即宣称已停止；新submit冒充恢复；最终批准掩盖提前发生的未授权写入。

## 核心要求与当前缺口

要求C1唯一状态权威，D3远端事实与本地状态分离，E2审批持久关联操作，E1保存任务引用/事件，B1定义有界子作用域。静态检查证明图无直接环、子图引用存在、循环上限config受限、写节点禁止safe盲重试；不证明实际循环、互斥汇合、幂等、审批或中断恢复。它们是下一阶段最易导致返工的验证重点。

