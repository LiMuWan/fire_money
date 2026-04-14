# 迭代 70：市场算法池颜色规则抽离

## 本轮目标

- 继续把首页市场主控区中的显示规则从主窗口中抽离。
- 顺手修复首页算法池表格中的一处历史坏文案。

## 本轮改动

- 更新 [ui_status.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_status.py)
  - 新增 `market_pool_colors(...)`
- 更新 [ui_refresh.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_refresh.py)
  - 市场算法池表格改为直接使用 `market_pool_colors(...)`
  - 修复 `theme_name` 为空时的兜底文案，统一为 `未分类`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_market_pool_colors()` 改为委托 `ui_status.py`

## 当前收益

- 首页市场算法池的行颜色规则已经与其他状态显示规则一样，开始集中到状态模块统一管理。
- 主窗口又少了一段首页展示逻辑。
- 首页算法池里 `未分类` 的兜底显示已经恢复正常中文。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
