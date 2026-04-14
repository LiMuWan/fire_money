# 迭代 66：市场主控台快照抽离与交易页启动修复

## 本轮目标

- 继续把首页市场主控台的展示逻辑从主窗口中抽离，降低 `app_qt.py` 复杂度。
- 修复重构过程中暴露出的交易执行页启动回归，保证应用可正常打开。

## 本轮改动

- 更新 [ui_refresh.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_refresh.py)
  - 新增 `build_market_dashboard_snapshot(...)`
  - 新增 `build_market_text_snapshot(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_render_market_dashboard()` 改为委托市场主控台快照 helper
  - `_update_market_text_panels()` 改为委托市场文字面板快照 helper
  - 修正首页图表标题与动能柱状图标签的历史坏文案
- 更新 [workspace_builders.py](C:/Users/18335/Documents/New%20project/quant_hunter/workspace_builders.py)
  - 修复 `build_broker_workspace(...)` 中未定义的 `current_mode` 启动错误
  - 同步补齐交易执行页账户配置区的按钮和字段文案

## 当前收益

- 首页市场快照、资金画像、交易决策这条链开始走统一 snapshot helper，后续继续调整首页盘面时更安全。
- 交易执行页的 builder 启动回归已修复，Qt 主窗口可正常启动。
- 这一轮不仅通过了业务测试，还通过了带 Qt 的真实启动冒烟。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
