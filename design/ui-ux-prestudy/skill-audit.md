# Skill安装与可选补充审查

日期2026-10-27。安装只落在AOS项目的`.agents/skills`，没有修改全局Codex配置、PFT或执行代码。

## 先检查，再安装

使用本机Codex app-server的**只读skills/list**查询真实已启用目录，未创建thread、turn或模型请求：[安装前](./evidence/before-skills.json)、[安装后](./evidence/after-skills.json)。安装前根目录列出13个技能，含技能安装/创建、OpenAI Docs、文档/PDF/演示/表格、可视化等，没有frontend-design或ui-ux-pro-max。磁盘plugin cache不被当成“已启用”证明。

前端设计技能安装后根目录出现第14个技能：name=frontend-design、scope=repo、enabled=true、path指向本项目；errors为空。元数据默认提示包含`$frontend-design`。本轮已读取已安装SKILL.md并按其工作流完成方向选择、真实浏览器渲染、截图审查与修正；没有为“调用测试”启动额外模型会话或改全局技能根。

[OpenAI官方技能文档](https://learn.chatgpt.com/docs/build-skills)说明项目级`.agents/skills`与显式`$技能名`方式；[App Server文档](https://learn.chatgpt.com/docs/app-server)提供skills/list及cwd作用域。实际查询还发现本项目不是Git仓库，从design子目录不一定向上发现根Skill；因此使用时应在**D:\AIOrchestrationStudio根目录**打开项目。当前ChatGPT镜像目录不属于该作用域。若选择器未刷新，下一轮重新打开/重启Codex；不需要复制一份到全局。

## frontend-design（已安装）

- 用户指定仓库：[dobromirdikov/codex-frontend-design-skill](https://github.com/dobromirdikov/codex-frontend-design-skill)。个人公开仓库，非OpenAI官方技能，不以作者自述代替官方背书。
- 固定提交：`983119775a936d123df9fbfbc3821bdee5bb58fd`，由git ls-remote确认后审查该提交归档。[归档清单/摘要](./references/frontend-repository.json)、[安装逐文件摘要](./evidence/skill-install-manifest.json)。
- 上游说明为Anthropic frontend-design的Codex移植；Apache-2.0。SKILL内保留来源说明，项目技能目录增加原仓库LICENSE副本。
- 技能包仅SKILL.md与agents/openai.yaml；没有脚本、二进制、依赖安装、外部服务、提权或后台钩子。完整阅读其工作流、反模式、资产/排版/浏览器QA要求，未发现要求外传项目或执行未知命令的内容。
- 通过已审查的**系统内置skill-installer**，指定`--dest D:\AIOrchestrationStudio\.agents\skills --method git --ref <固定提交>`安装；只复制目标技能目录。安装没有执行仓库脚本；上游两文件与审查副本字节一致。
- 首次Git检出受Windows换行影响，内容一致但字节摘要不同；[初始记录](./evidence/skill-install-initial.json)保留。逐文件确认仅换行差异后，用已审查归档的原字节对齐，两份指令/元数据没有语义修改，也没有改动全局Git配置。
- 适配原则：用户只要设计预研，不因技能中的“production-grade/implement”措辞扩张为正式GUI；保留桌面密度、本机字体、无装饰动效，不套营销页hero规则。

网络审查过程遇到GitHub API公共限流和Python codeload证书校验错误，改用git读远端与Windows curl正常证书验证下载；没有关闭TLS验证、提交凭据或运行npx安装器。

## UI/UX Pro Max（未安装）

来源：[nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)，固定审查提交`28b3b8dee8c976df4fa3e94aed4e092ad43fcb03`。MIT；[归档清单](./references/optional-repository.json)及SKILL/README/部分搜索源码只保存在references，**不属于已安装技能目录**。

审查了技能主体、搜索入口/core/design-system源码及CLI包清单，没有执行其中Python、npm/npx、build、persist或安装脚本。归档还包含brand/slides等多个技能，本轮一个也没有自动安装。没有把整个8MB级归档装入自动技能目录。

| 项目 | 价值 | AOS适配风险 |
| --- | --- | --- |
| 可搜索规则/颜色/字体/控件数据库 | 后续聚焦无障碍、字段错误、键盘导航时可补充 | 搜索结果是启发，不是密集图编辑器的用户验证 |
| 默认44px触控目标、16px正文、mobile-first | 适合触屏/网页 | 不能机械套在Windows鼠标工作台，否则空间和密度失衡 |
| design-system生成/persist | 可复用查询与结构化输出 | 会写新文件，必须锁定输出位置；不能覆盖已选Tokens |
| GSAP/landing/chart等广覆盖 | 其他项目可能有用 | 本轮多余，可能误导到营销/仪表盘或装饰动效 |
| CLI及多技能资源 | 跨编辑器分发便利 | 扩大依赖/审查面；本轮没有必要运行整个CLI |

建议**暂缓安装**。若后续确有重复的无障碍或Schema表单检索需求，再审查对应模块、引用/数据闭包与Codex本地路径适配，最小安装；不要把“79种风格”等自述计数当设计质量证据，也不以本轮有限静态检查宣称完整供应链安全。
