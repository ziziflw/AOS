# 场景B · 数据转换与外部工具协作

状态：设计与离线检查完成，MCP/HTTP/权限执行未实测。相关E03/E06；[工作流](../02-node-contracts/examples/scenario-b.workflow.json)、[运行输入](../02-node-contracts/examples/scenario-b.run-request.json)。

## 用户需要与节点关系

用户把输入任务和受控本地资料交给工具检索，能定位参数错误、超时和未确定副作用；同一业务I/O可分别绑定本地MCP与远端HTTP实现。本场景选确定数据转换作为前处理，模型前处理可在新修订中替换，不能暗中增加模型调用。

```text
request → map(query-and-source-v1) → tool.query → check → output
```

共5节点、4条数据边。节点类型分别为core.input.tool-request、core.map-tool-args、tool.query、core.check-tool-result、core.output.tool-result。

## 完整输入输出

| 节点 | 输入 | 数据输出 |
| --- | --- | --- |
| request | inputs.request:ToolRequest{query:string,source:FileReference} | out:ToolRequest |
| map | in:ToolRequest | out:ToolArgs{query:string,source:FileReference} |
| tool | args:ToolArgs；config.operation=query | out:ToolResult{items:Item[],operationState:confirmed或unknown} |
| check | in:ToolResult | out:同一ToolResult；unknown操作状态须阻断或转人工，不假称已确认 |
| output | in:ToolResult | 工作流最终ToolResult |

Item精确为{text:string,source:FileReference}；FileReference为{resourceUri,mediaType,sizeBytes,可选sha256}。实例引用workspace:source/sample.txt，实际路径由本机挂载解析。标准ready/done/Error端口同统一契约；工具isError/协议错误/类型错误进入Error，不能作为普通items伪装成功。

MCP工具输入Schema与工具输出Schema须与ToolArgs/ToolResult的适配投影一致；如果远端只有非结构化文本，必须新增显式解析/验证步骤，不能声称已满足结构化输出。

## 环境依赖与真实接口候选

本地方式：以后续任务按官方候选SDK创建/配置无副作用query测试服务，通过MCP 2025-11-25 initialize、tools/list、tools/call接入，stdio启动程序按受控路径配置。此测试服务目前尚不存在；真实协议实验不等于支持任意第三方工具。

远端方式：使用用户授权的HTTP测试服务，约定query输入及ToolResult返回；本轮没有现成第三方URL、未猜测可用服务。HTTP请求方法、路径、鉴权、Schema/幂等语义在实验前固定。样例中tool.query的adapter为fixture.tool.mcp；HTTP变体改成fixture.tool.http并同步requirement/环境绑定和workflow修订，仍验证相同业务I/O。

远程工具不能自动读取本机workspace路径。需显式授权上传产物到远端可访问的受控存储，或选择本地代理；传输输出仍是受限引用/摘要，禁止自动外传。是否允许上传是E2决策，属于HTTP变体实验输入。

## 后续通过与失败条件

1. 发现并锁定工具描述；成功调用后验证结构化结果与文件引用。
2. 缺query、错类型、畸形outputSchema或描述变化时检查执行前/运行时拒绝。
3. 测本地程序缺失、stdout污染、远端401/403/429、超时后结果查询；核对副作用状态。
4. 拒绝资源和网络权限，确认没有发生目标操作；再批准精确请求。
5. 切换HTTP变体，重新评估数据外发与资源解析。

通过：发现/版本/Schema可追溯；非法参数在目标操作前被拦；类型错误隔离；本地与远程凭据、资源和网络约束可诊断；无凭据时零调用；工具超时不被当作“没发生”；仅有受信任只读证据时按有限次数重试。
失败：依赖模型自判参数；把工具自报readOnly当强制权限；把本机绝对路径发送给远端当可用文件；副作用未知时盲重试；用UI确认代替后端拦截。

## 核心要求与未验证

D2发现/映射/校验并申请授权；E2决定权限；E3落实本地进程/网络与文件约束；C1独占重试和状态；E1管理产物。静态fixture只证明接口形状和安全重试分支规则，真实工具发现、IO、网络上传、超时结果和OS隔离全部待实验。

