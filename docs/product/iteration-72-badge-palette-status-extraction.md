# 迭代 72：徽章配色规则状态模块抽离

## 本轮目标

- 继续把首页和推荐页中仍留在主窗口里的纯展示规则下沉到状态模块。
- 保持界面配色与交互不变，只降低 `app_qt.py` 的维护复杂度。

## 本轮改动

- 更新 [ui_status.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_status.py)
  - 新增 `fund_badge_palette(...)`
  - 新增 `strategy_badge_palette(...)`
  - 新增 `signal_badge_palette(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_fund_badge_palette()` 改为委托 `ui_status.py`
  - `_strategy_badge_palette()` 改为委托 `ui_status.py`
  - `_signal_badge_palette()` 改为委托 `ui_status.py`
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增三个配色 helper 的导入校验

## 当前收益

- 首页和推荐页里用于资金标签、战法标签、信号标签的配色规则进一步集中。
- `app_qt.py` 又减少了一批纯 UI 映射代码，更接近编排层。
- 这类规则后续如果要统一全局视觉风格，只需要改一处。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py quant_hunter\ui_helpers.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
