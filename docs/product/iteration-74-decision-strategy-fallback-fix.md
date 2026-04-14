# 迭代 74：决策引擎战法缺省映射修复

## 本轮目标

- 修复决策引擎在 `stock_pool` 缺失时，无法根据 `primary_strategy` 生成正确止损止盈的问题。
- 保证这类修复不会影响现有已经带 `stock_pool` 的推荐链结果。

## 本轮改动

- 更新 [decision.py](C:/Users/18335/Documents/New%20project/quant_hunter/decision.py)
  - `_pool_trade_plan(...)` 新增“仅在 `stock_pool` 为空时生效”的战法缺省映射
  - 新增 `_strategy_trade_plan_override(...)`
  - 新增 `_infer_stock_pool_from_strategy(...)`

## 修复内容

- `擒龙打板` 在缺少 `stock_pool` 时，会按打板策略生成更合理的止损/目标位。
- `价值低吸` 在缺少 `stock_pool` 时，会按低吸策略生成更合理的止损/目标位。
- 如果推荐链已经明确写入 `stock_pool`，仍然优先沿用原有股票池逻辑，不改变现有行为。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_decision_engine_uses_strategy_specific_targets -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
