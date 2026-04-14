# 迭代 82：股票资料查询 Helper 抽离

## 本轮目标

- 继续把主窗口里用于查询股票资料的小工具函数下沉到公共 helper 模块。
- 保持股票名称、股票代码、资料兜底显示行为不变。

## 本轮改动

- 更新 [ui_helpers.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_helpers.py)
  - 新增 `stock_profile_for_symbol(...)`
  - 新增 `stock_name_for_symbol(...)`
  - 新增 `stock_id_for_symbol(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_stock_profile_for_symbol()` 改为委托 `ui_helpers.py`
  - `_stock_name_for_symbol()` 改为委托 `ui_helpers.py`
  - `_stock_id_for_symbol()` 改为委托 `ui_helpers.py`
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增三个股票资料 helper 的导入校验

## 当前收益

- 主窗口里又减少了一组重复出现的资料查询薄包装。
- 后续如果推荐页、交易页、复盘页要统一资料兜底逻辑，可以直接复用这组 helper。
- 这一轮不触碰业务决策，只收辅助查询层。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py quant_hunter\ui_helpers.py quant_hunter\ui_config.py quant_hunter\decision.py quant_hunter\broker.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
