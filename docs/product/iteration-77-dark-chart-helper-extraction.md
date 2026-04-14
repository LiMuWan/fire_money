# 迭代 77：深色图表样式 Helper 抽离

## 本轮目标

- 继续把首页和推荐页图表共用的纯样式逻辑从主窗口中抽离。
- 保持分时图、日线图、主力资金图、动能图的视觉表现不变。

## 本轮改动

- 更新 [ui_helpers.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_helpers.py)
  - 新增 `style_dark_chart(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_style_dark_chart()` 改为委托 `ui_helpers.py`
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增图表样式 helper 的导入校验

## 当前收益

- 深色图表标题、背景、绘图区底色、图例隐藏等规则从主窗口中移出。
- `app_qt.py` 继续减少纯显示代码，更接近编排层。
- 后续若统一主题或新增图表，只需复用同一个 helper。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py quant_hunter\ui_helpers.py quant_hunter\decision.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
