# 迭代 69：市场代理走势 Helper 抽离

## 本轮目标

- 继续把首页市场主控区中的纯计算逻辑从主窗口里抽离。
- 保持首页图表行为不变，同时进一步压缩 `app_qt.py`。

## 本轮改动

- 更新 [ui_refresh.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_refresh.py)
  - 新增 `build_market_proxy_points(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_build_market_proxy_points()` 改为委托 `ui_refresh.py`
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 补充 `build_market_proxy_points` 入口导入校验

## 当前收益

- 首页“市场代理走势”这部分的点位生成逻辑已经不再直接堆在主窗口里。
- 市场图表链继续向 `refresh/helper` 层收口，便于后续继续拆首页图表和市场快照逻辑。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
