# 迭代 81：导出目录 Runtime Helper 抽离

## 本轮目标

- 继续把报表导出链中留在主窗口里的目录 helper 下沉到运行维护模块。
- 保持收盘复盘导出和盘前计划导出的路径行为不变。

## 本轮改动

- 更新 [ui_runtime.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_runtime.py)
  - 新增 `review_output_dir(...)`
  - 新增 `daily_plan_output_dir(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_review_output_dir()` 改为委托 `ui_runtime.py`
  - `_daily_plan_output_dir()` 改为委托 `ui_runtime.py`
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增两个导出目录 helper 的导入校验

## 当前收益

- 运行日志、缓存维护、运行面板之外，导出路径规则也开始纳入同一条 runtime 模块链。
- 主窗口进一步减少与导出目录相关的辅助逻辑。
- 本轮保持了既有目录语义，不引入行为变化。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py quant_hunter\ui_helpers.py quant_hunter\ui_config.py quant_hunter\decision.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
