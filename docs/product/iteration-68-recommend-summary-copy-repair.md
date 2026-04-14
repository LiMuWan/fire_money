# 迭代 68：推荐页摘要卡文案修复

## 本轮目标

- 修复推荐页顶部摘要卡仍残留的占位符文案。
- 保持推荐页摘要逻辑继续留在 `ui_refresh.py`，不回退到主窗口中。

## 本轮改动

- 更新 [ui_refresh.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_refresh.py)
  - 修正 `refresh_recommend_summary_cards(...)` 的摘要文案
  - 补齐 `推荐逻辑 / 盘前计划 / 市场情绪 / 持仓建议` 4 张卡片的正常中文描述

## 当前收益

- 推荐页第一屏现在不再显示 `????` 和占位符，而是正常展示主策略、题材、决策分、待复核数量、已提交数量和市场风险信息。
- 这部分逻辑继续保持在 refresh helper 层，主窗口没有重新变重。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
