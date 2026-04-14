# 迭代 71：首页按钮样式 Helper 抽离

## 本轮目标

- 继续把首页主控台中的纯样式逻辑从主窗口里抽离出去。
- 保持首页按钮外观和交互完全不变，只降低 `app_qt.py` 的维护压力。

## 本轮改动

- 更新 [ui_helpers.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_helpers.py)
  - 新增 `build_overview_outline_style(...)`
  - 新增 `build_overview_filled_style(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_overview_outline_style()` 改为委托 `ui_helpers.py`
  - `_overview_filled_style()` 改为委托 `ui_helpers.py`
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增对两个样式 helper 的导入校验

## 当前收益

- 首页顶部按钮、过滤按钮和周期按钮使用的样式拼装进一步从主窗口下沉。
- `app_qt.py` 又减少了一段纯 UI 字符串逻辑，更接近编排层。
- 本轮不触碰业务主链，属于低风险重构。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py quant_hunter\ui_helpers.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
