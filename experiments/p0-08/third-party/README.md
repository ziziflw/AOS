# 第三方来源与许可材料

精确发行版、PyPI轮子哈希、传递依赖、包声明的许可证、原生文件、钩子见 `../evidence/dependency-review.json`；`../sdk-requirements.lock`固定55项运行发行版。pip是venv自带的第56项元数据，不是模型SDK新增运行依赖。

各包目录保留 wheel 内实际提供的 LICENSE / NOTICE / COPYING 原文。没有本地修改第三方Python包；模型SDK、MCP/A2A、校验库仍使用上游发行版。AOS新代码是实验适配、C1准入与界面胶水。

aiologic0.17.1及culsans0.11.0的wheel没有附带独立许可文件；代码SPDX头/metadata classifier声明ISC，文档使用CC-BY-4.0。已从PyPI取得**相同精确发行版**的源归档，只作为数据读取（未运行setup/build脚本），校验注册表sha256，补齐各自 `sdist/LICENSES/` 原文及文档说明。来源/归档哈希见 `../evidence/supplemental-source-licenses.json`。猜测GitHub tag路径的404记录保留，不将失败路径当许可依据。完整源归档保留在 `../source-archives/`，其中版权/SPDX说明未改。

OpenAI3.41.0、Anthropic2.3.0 wheel声明Apache-2.0，SDK自身及其附属NOTICE完整保留。全部审查和依赖一致不等于完整漏洞/供应链审计。

Vue/Vue Flow/Tauri等前端和Rust依赖继续沿用独立 package-lock/Cargo.lock；上游许可在本机依赖分发中。宿主、前端、图标复用P0-07自有实验代码，保持隔离，不复制成熟组件内部实现。正式发行仍需对最终打包制品自动汇总许可、NOTICE及原生依赖，不以本材料代替发行法务审查。
