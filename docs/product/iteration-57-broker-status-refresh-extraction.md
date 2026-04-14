# 迭代 57：交易执行页状态刷新抽离

## 本轮目标

- 将交易执行页中偏展示层的状态刷新从主窗口中抽离。
- 不改变真实下单、SDK 同步、订单导出等行为。

## 本轮改动

- 更新 [ui_refresh.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_refresh.py)
  - 新增 `refresh_trade_recap(...)`
  - 新增 `refresh_broker_execution_panel(...)`
  - 新增 `refresh_broker_status(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_refresh_trade_recap()` 改为委托刷新模块
  - `_refresh_broker_execution_panel()` 改为委托刷新模块
  - `_refresh_broker_status()` 改为委托刷新模块
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 补充上述刷新入口导入校验

## 当前收益

- 主窗口再次减薄，交易执行页展示逻辑开始和推荐页、扫描页采用同类刷新层结构。
- 后续若新增更多账户状态卡、执行摘要卡、券商环境诊断视图，可继续在刷新层扩展。
