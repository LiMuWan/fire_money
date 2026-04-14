# 迭代 79：Splitter 与滚动 Helper 抽离

## 本轮目标

- 继续把主窗口里通用的界面小工具函数下沉到公共 helper 模块。
- 保持分栏布局比例和滚动手感不变。

## 本轮改动

- 更新 [ui_helpers.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_helpers.py)
  - 新增 `configure_splitter(...)`
  - 新增 `enable_smooth_scroll(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_configure_splitter()` 改为委托 `ui_helpers.py`
  - `_enable_smooth_scroll()` 改为委托 `ui_helpers.py`
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增两个通用 UI helper 的导入校验

## 当前收益

- workspace builder 和主窗口共用的 splitter 调整逻辑不再留在主窗口内部。
- 滚动区域的单步滚动设置也集中到了 helper 层。
- `app_qt.py` 继续朝“编排器”方向收敛。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py quant_hunter\ui_helpers.py quant_hunter\decision.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
