# 磁盘占用与首次源码基线 · 2026-11-10

## 扫描口径

范围为 D:\AIOrchestrationStudio。建库前递归统计到 219,302 个文件，文件长度合计 14,578,827,490 字节（13.58 GiB）。没有读取失败或跳过的重解析点。统计基于逻辑文件大小；NTFS 簇、压缩和硬链接会影响卷上的实际分配量。本报告不包括用户 AppData、Cargo 全局缓存及临时目录。各行按路径互斥归类。

|内容|MiB|占比|
|---|---:|---:|
|四个宿主的 Cargo target|10,805.52|77.72%|
|dist 与 demo/dist 的发行目录和归档|1,154.98|8.31%|
|其余 runs / evidence 目录中的运行记录、测试证据|573.88|4.13%|
|五份工作树 node_modules|571.21|4.11%|
|P0-11 的 .runtime 和工作台 .desktop-preview|354.58|2.55%|
|P0-04、05、06、08 的 .venv|340.18|2.45%|
|其余文件，包括源码、研究、素材及其他构建/测试文件|103.09|0.74%|

## 多版本与重复项

四个 target 分别是 experiments/p0-07/host（2,983.6 MiB）、demo/build/host（2,864.4 MiB）、experiments/p0-06/host（2,534.1 MiB）、experiments/p0-08/host（2,423.5 MiB）。实际文件包括 Rust 的 .rlib、调试符号 .pdb 与增量编译产物。同名的四份约 120 MiB libwindows-c9c024e80cf6b92f.rlib 的 SHA256 各异；尺寸相近不能据以判定字节相同。

dist 共 682.2 MiB，含 v0.1.0 至 v0.1.3 四套解压目录及四份 ZIP。四份 ZIP 的实际 SHA256 均与各自 .sha256 一致。逐项读取 ZIP 的未压缩字节，按包内相对路径、长度及 SHA256 比对，发现跨版本超出首份的相同条目 30,139 个，未压缩字节合计 328,123,072。该数字描述归档内容重复程度，不等同可释放的卷空间。demo/dist 另有三个较早构建目录，分别为 155.2、158.8、158.8 MiB。

实际源码也有继承和分叉。对 experiments/p0-07 与 p0-08 的 frontend/src 同相对路径做 SHA256 对照，1 个文件相同、3 个不同；host/src 的 3 个共有文件均不同。demo/build/frontend/src 与 demo/studio/frontend/src 有 3 个相同文件、1 个不同，后者另有 14 个文件。demo/build_host.py 从 P0-08 复制并加工前端与宿主，demo/studio/build.py 也将 Cargo 输出指向 demo/build/host/target。当前集成视图位于 demo/studio/frontend/src/integration，共享 Vue 控制逻辑，独立启动入口在 apps/aos-workbench。旧实验源码与当前入口均保留。

## Git 边界与后续开发

审计前，项目及父目录未被识别为 Git 工作树，整个项目内无嵌套 .git 文件或目录。此前没有分支、HEAD、暂存区、标签、远程或正在进行的合并/rebase。此次在项目根建立 main 本地基线。提交源码、契约、锁文件、构建脚本、许可证、标准模板、研究报告及选定的合成运行证据。根 .gitignore 排除已构建程序、依赖树、Python 环境、编译缓存、浏览器用户配置、数据库、归档和原始旧会话目录。保留 P0-06 手写的 host/ui 和各阶段源代码。根 .gitattributes 保留基线文件原始换行，避免跨平台 checkout 改写被契约锁或恢复身份哈希覆盖的字节。

当前工作目录可继续按 [START_HERE](../START_HERE.md) 启动。P0-11 的集成 EXE、node_modules、私有 Python 环境和 v0.1.3 解压目录仍在本机原处；Git 只记录源代码和构建输入。新克隆需要按锁文件恢复依赖、准备 Rust 工具链及所需缓存、按启动文档构建开发宿主。首次初始化 P0-11 运行时还需从已有受信任的 v0.1.3 归档恢复 dist/AOS-Demo-v0.1.3-win-x64/app；历史验收报告中指向本机缓存、旧会话或上游下载快照的链接可能仅在原工作目录有效。本次没有删除项目文件、打包、打标签或推送。
