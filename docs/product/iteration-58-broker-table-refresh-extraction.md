# 迭代 58：交易执行页表格刷新抽离

## 本轮目标

- 继续把交易执行页的展示层从主窗口里拆出去。
- 将持仓表、订单建议表、提交记录表的填充逻辑统一收口到刷新层。

## 本轮改动

- 更新 [ui_refresh.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_refresh.py)
  - 新增 `fill_holdings_table(...)`
  - 新增 `fill_order_intents_table(...)`
  - 新增 `refresh_submission_table(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_fill_holdings()` 改为委托刷新层
  - `_fill_orders()` 改为委托刷新层
  - `_refresh_submission_table()` 改为委托刷新层
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 补充上述刷新入口导入校验

## 当前收益

- 交易执行页的状态卡、摘要区、三张核心表格都开始走统一刷新层。
- 主窗口进一步回归编排层，后续改交易页布局时更容易局部调整。
