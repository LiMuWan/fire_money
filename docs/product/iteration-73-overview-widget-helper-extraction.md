# 迭代 73：首页组件 Helper 抽离

## 本轮目标

- 继续把首页主控台中残留在主窗口里的纯组件拼装逻辑下沉到公共 helper 模块。
- 保持首页可见布局与交互不变，只降低 `app_qt.py` 的 UI 负担。

## 本轮改动

- 更新 [ui_helpers.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_helpers.py)
  - 新增 `build_stock_identity_cell(...)`
  - 新增 `create_metric_card(...)`
  - 新增 `build_badge_strip(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_build_stock_identity_cell()` 改为委托 `ui_helpers.py`
  - `_create_metric_card()` 改为委托 `ui_helpers.py`
  - `_build_badge_strip()` 改为委托 `ui_helpers.py`
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增三个组件 helper 的导入校验

## 当前收益

- 首页龙头个股身份块、指标卡和标签条的组件拼装已经脱离主窗口。
- `app_qt.py` 又减少了一批纯 UI 构建代码，更接近编排层。
- 这些组件后续如果要统一视觉风格，也更容易集中调整。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py quant_hunter\ui_helpers.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
