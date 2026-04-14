# 迭代 55：真实提交链外壳抽离

## 本轮目标

- 在不改变真实提交行为的前提下，先把下单主链外壳从主窗口里收薄。
- 将提交前准备、失败回退、成功写回抽成独立 controller 入口。

## 本轮改动

- 更新 [ui_controllers.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_controllers.py)
  - 新增 `prepare_order_submission_controller(...)`
  - 新增 `handle_order_submission_failure_controller(...)`
  - 新增 `handle_order_submission_success_controller(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `confirm_and_submit_orders()` 改成由主窗口编排、controller 承接外围逻辑
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增上述 controller 入口导入校验

## 本轮边界

- 保留真实 SDK 提交调用位置不变
- 保留确认弹窗行为不变
- 保留失败后回退导出 CSV 的行为不变
- 保留成功后同步 SDK 账户和写入执行日志的行为不变

## 当前收益

- `confirm_and_submit_orders()` 明显变短，主窗口更接近编排层
- 后续若要接入更多券商适配器，可以复用失败/成功写回逻辑
- 下一步可以继续把真实提交动作本身抽成更明确的 broker execution service

## 稳定性补充

- 更新 [storage.py](C:/Users/18335/Documents/New%20project/quant_hunter/storage.py)
  - `load_app_state(...)` 现在会在状态文件为空或 JSON 损坏时自动回退默认状态
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增损坏状态文件回退测试，避免启动因本地状态文件异常而失败
