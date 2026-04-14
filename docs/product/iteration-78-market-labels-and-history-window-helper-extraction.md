# 迭代 78：市场模式文案与历史窗口 Helper 抽离

## 本轮目标

- 继续把首页市场主控台中的纯文案映射和图表窗口限制逻辑从主窗口里抽离。
- 保持市场来源显示、模式显示和图表窗口行为不变。

## 本轮改动

- 更新 [ui_status.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_status.py)
  - 新增 `market_mode_label(...)`
  - 新增 `market_source_mode_label(...)`
- 更新 [ui_refresh.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_refresh.py)
  - 新增 `history_window_limit(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_market_mode_label()` 改为委托 `ui_status.py`
  - `_market_source_mode_label()` 改为委托 `ui_status.py`
  - `_history_window_limit()` 改为委托 `ui_refresh.py`
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增相关 helper 的导入校验

## 当前收益

- 首页数据源状态面板的模式/来源文案映射不再留在主窗口中。
- 市场图表“近3月 / 近1年 / 近3年 / 全部”的窗口限制逻辑也从主窗口中抽离。
- `app_qt.py` 继续往“编排层”收敛。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py quant_hunter\ui_helpers.py quant_hunter\decision.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
