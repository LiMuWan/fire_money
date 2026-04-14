# 迭代 83：运行配置读取 Helper 抽离

## 本轮目标

- 继续把主窗口里用于读取策略运行配置和盘前模板配置的小工具函数下沉到 runtime 模块。
- 保持配置页读取结果与盘前/盘后导出行为不变。

## 本轮改动

- 更新 [ui_runtime.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_runtime.py)
  - 新增 `current_strategy_runtime_config(...)`
  - 新增 `current_report_template_config(...)`
  - 新增 `parse_focus_themes_text(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_current_strategy_runtime_config()` 改为委托 `ui_runtime.py`
  - `_current_report_template_config()` 改为委托 `ui_runtime.py`
  - `_parse_focus_themes()` 改为委托 `ui_runtime.py`
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增三个 runtime helper 的导入校验

## 当前收益

- 配置页和导出链之间的参数读取逻辑开始向 runtime 模块集中。
- 主窗口继续减少“读输入框 -> 兜底 state -> 裁剪结果”这类辅助代码。
- 这一轮不改变现有配置语义，只做结构收敛。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py quant_hunter\ui_helpers.py quant_hunter\ui_config.py quant_hunter\decision.py quant_hunter\broker.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
