# 迭代 61：交易执行摘要 Service 抽离

## 本轮目标

- 将交易执行页和确认弹窗共用的执行摘要计算抽成独立 service。
- 删除主窗口里已经失去复用价值的孤立摘要包装方法。

## 本轮改动

- 新增 [broker_status.py](C:/Users/18335/Documents/New%20project/quant_hunter/broker_status.py)
  - 提供 `build_broker_execution_summary(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - 确认弹窗改为使用新的摘要 service
  - 删除 `_broker_execution_summary()` 孤立包装方法
- 更新 [ui_refresh.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_refresh.py)
  - 交易执行页状态刷新改为复用新的摘要 service
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增 `broker_status` 入口导入校验

## 当前收益

- 确认弹窗和交易执行页状态卡使用同一份摘要计算逻辑。
- 主窗口继续减薄。
- 后续若扩展不同券商适配器的环境诊断和执行摘要，可优先从 service 层扩展。
