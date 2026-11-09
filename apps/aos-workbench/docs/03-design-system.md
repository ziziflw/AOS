# 工作台布局基线 · 2026-11-09

当前设计以用户提供的两张 Langflow Desktop 截图为准。白色窄顶栏显示项目与流程名。左侧图标切换组件、草稿或节点属性，同一时间只展开一块侧栏。收起后只保留图标和画布。节点名称与配置值是业务数据。右上方为草稿保存和更多操作，下方仅保留缩放与适配画布。

今后新增控件优先用操作名称和可访问标签。保持右侧和底部画布空间，避免常驻说明、悬浮提示框、欢迎卡、辅助徽章和装饰小字。实际失败在对应操作处反馈。双击节点在左侧编辑属性。

图的交互沿用 React Flow。订单变量、条件与脚本图标直接取自 [FlowGram 官方自由布局示例素材](https://github.com/bytedance/flowgram.ai/tree/7f568bb2515bcaae561df9b8494af8c744027ebc/apps/demo-free-layout/src/assets)，固定提交 7f568bb2515bcaae561df9b8494af8c744027ebc；MIT 许可证保存在 licenses/flowgram.txt。其他图标来自 Lucide。布局依据用户截图，未嵌入 Langflow 或其品牌资产。

「打开新版工作台.cmd」现已指向 P0-11 集成开发构建。React 前端预览可用 npm run dev。下列证据为原草稿预览阶段，集成实测另见[交付报告](../../../planning/p0-11-integration-report.md)。预览实测见 evidence/langflow-desktop.json、evidence/langflow-open.png、evidence/langflow-canvas.png。旧 Dockview 样式的截图仅为历史记录。

