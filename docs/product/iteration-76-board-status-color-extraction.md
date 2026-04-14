# 迭代 76：打板监控颜色规则状态模块抽离

## 本轮目标

- 继续把打板监控页里留在主窗口中的纯显示规则下沉到状态模块。
- 保持打板候选表和盘中监控表的颜色表现不变。

## 本轮改动

- 更新 [ui_status.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_status.py)
  - 新增 `board_risk_colors(...)`
  - 新增 `board_monitor_colors(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_board_risk_colors()` 改为委托 `ui_status.py`
  - `_board_monitor_colors()` 改为委托 `ui_status.py`
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增两个打板显示 helper 的导入校验

## 当前收益

- 打板页颜色规则与首页、推荐页、交易页的状态显示规则进一步统一到同一模块中。
- `app_qt.py` 再减少两段纯显示逻辑。
- 后续如果统一配色体系或扩展更多状态，只需要维护一个状态模块。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py quant_hunter\ui_helpers.py quant_hunter\decision.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
