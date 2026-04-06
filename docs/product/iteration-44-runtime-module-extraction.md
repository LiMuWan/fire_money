# 迭代 44 - 运行时模块抽离

## 目标
- 把运行概览、运行面板刷新、运行日志导出从主窗口中抽离。
- 让主窗口进一步回归到编排层，而不是承载运行诊断细节。
- 保持重构过程中应用持续可启动。

## 本次变更
- 新增 [ui_runtime.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_runtime.py)。
- 当前已抽出的运行能力包括：
  - `build_runtime_overview_text(...)`
  - `refresh_runtime_panel(...)`
  - `runtime_export_dir(...)`
  - `export_runtime_log(...)`
- [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中：
  - `_runtime_overview_text()`
  - `refresh_runtime_panel()`
  - `_runtime_export_dir()`
  - `export_runtime_log()`
  都已改为委托运行模块。

## 价值
- 运行诊断链路开始脱离主窗口。
- 后续继续扩展任务监控、运行状态面板、日志导出格式时，不需要再回到主窗口长文件中修改。
- 项目结构进一步清晰：
  - builder
  - refresh
  - binder
  - controller
  - runtime
  - orchestrator

## 验收
- 运行面板仍可正常刷新。
- 运行日志仍可正常导出。
- Qt 主窗口可正常启动。
- 编译检查、启动冒烟测试、全量测试全部通过。

## 下一步
- 继续评估缓存清理与运行时维护是否也适合进入 runtime / service 层。
- 继续收缩主窗口中的剩余诊断与状态汇总代码。
