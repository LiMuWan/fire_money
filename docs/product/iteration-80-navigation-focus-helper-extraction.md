# 迭代 80：导航与焦点 Helper 抽离

## 本轮目标

- 继续把主窗口里用于页面导航和焦点处理的通用小工具函数下沉到公共模块。
- 保持工作区切换、首行自动选中、焦点回填这些行为不变。

## 本轮改动

- 更新 [ui_config.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_config.py)
  - 新增 `workspace_name_for_index(...)`
- 更新 [ui_helpers.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_helpers.py)
  - 新增 `select_first_row(...)`
  - 新增 `focus_widget_later(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_workspace_name_for_index()` 改为委托 `ui_config.py`
  - `_select_first_row()` 改为委托 `ui_helpers.py`
  - `_focus_widget_later()` 改为委托 `ui_helpers.py`
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增相关 helper 的导入校验

## 当前收益

- 工作区名称映射不再留在主窗口里。
- 页面跳转时的首行选中和焦点回填逻辑下沉到了公共 helper 层。
- `app_qt.py` 继续往编排器结构收敛。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py quant_hunter\ui_helpers.py quant_hunter\ui_config.py quant_hunter\decision.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
