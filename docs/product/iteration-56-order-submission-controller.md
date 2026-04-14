# 迭代 56：真实提交链 Controller 化

## 本轮目标

- 将 `confirm_and_submit_orders()` 从主窗口进一步收敛成单一委托入口。
- 保持确认弹窗、SDK 提交、失败回退、成功写回行为不变。

## 本轮改动

- 更新 [ui_controllers.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_controllers.py)
  - 新增 `confirm_and_submit_orders_controller(...)`
  - 复用前一轮已经抽出的提交前准备、失败回退、成功写回入口
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `confirm_and_submit_orders()` 改为单一 controller 委托
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 增加 `confirm_and_submit_orders_controller` 导入校验

## 当前收益

- 主窗口里的真实提交链入口进一步变薄
- 交易执行主链现在和推荐链、市场链、扫描链一样，有更清晰的 controller 落点
- 后续若接券商适配、多账户模式或风控前置钩子，controller 层更容易扩展
