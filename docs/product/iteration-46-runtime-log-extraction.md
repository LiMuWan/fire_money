# 迭代 46 - 运行日志追加抽离

## 目标
- 继续清理主窗口中的运行维护代码。
- 优先抽离最高频调用的日志追加入口。
- 保持重构过程中应用可启动、可运行、可测试。

## 本次变更
- 在 [ui_runtime.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_runtime.py) 新增 `append_runtime_log(...)`。
- [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中 `_append_runtime_log()` 已改为委托 runtime 模块。

## 价值
- 运行维护链进一步集中到同一模块。
- 后续如果要统一日志格式、日志裁剪策略或日志落盘策略，不需要再回主窗口改动。
- 主窗口的运行支线再次收窄。

## 验收
- 运行日志仍能正常显示在面板中。
- Qt 主窗口可正常启动。
- 编译检查、启动冒烟测试、全量测试全部通过。

## 下一步
- 继续评估自动导出与运行维护是否适合继续迁入 runtime / controller。
- 继续清理主窗口里零散的状态汇总代码。
