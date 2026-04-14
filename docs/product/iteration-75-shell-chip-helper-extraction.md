# 迭代 75：顶部状态 Chip Helper 抽离

## 本轮目标

- 继续把应用壳层顶部状态栏中的纯组件拼装逻辑从主窗口中抽离。
- 保持顶部工作台状态、市场状态、执行进度、运行状态这几张 chip 的行为不变。

## 本轮改动

- 更新 [ui_helpers.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_helpers.py)
  - 新增 `create_shell_chip(...)`
  - 新增 `set_shell_chip(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_create_shell_chip()` 改为委托 `ui_helpers.py`
  - `_set_shell_chip()` 改为委托 `ui_helpers.py`
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增两个 shell chip helper 的导入校验

## 当前收益

- 顶部壳层状态 chip 的构建与赋值逻辑脱离主窗口。
- `app_qt.py` 继续减少纯 UI 组件代码，更接近编排层。
- 后续如果要统一顶栏视觉样式或扩展更多 chip，可以集中在 helper 层处理。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py quant_hunter\ui_helpers.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
