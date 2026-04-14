# 迭代 59：交易执行写回 Binder 抽离

## 本轮目标

- 把交易执行页中“写日志 / 写提交记录 / 联动刷新”的状态写回逻辑从主窗口里抽离。
- 继续保持真实提交行为不变。

## 本轮改动

- 更新 [ui_binders.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_binders.py)
  - 新增 `append_order_result_entry(...)`
  - 新增 `append_submission_record_entry(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_append_order_result()` 改为委托 binder
  - `_append_submission_record()` 改为委托 binder
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 补充上述 binder 入口导入校验

## 当前收益

- 交易执行链里的“结果写回 + 推动界面联动”不再堆在主窗口里。
- 主窗口继续向编排层收敛。
- 后续若扩展多账户提交、批次号记录、审计日志落库，可在 binder / service 层继续扩展。
