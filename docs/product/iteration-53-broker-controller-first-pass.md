# 迭代 53：交易执行 Controller 第一轮抽离

## 本轮目标

- 在不影响实际交易执行链稳定性的前提下，先抽离交易执行页中风险较低的入口。
- 让主窗口减少直接处理账户保存、模板生成、订单建议生成和委托计划导出的细节。

## 本轮改动

- 更新 [ui_controllers.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_controllers.py)
  - 新增 `save_broker_profile_controller(...)`
  - 新增 `create_broker_templates_controller(...)`
  - 新增 `generate_order_suggestions_controller(...)`
  - 新增 `export_order_plan_controller(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `save_profile()` 改为委托 controller
  - `create_broker_templates()` 改为委托 controller
  - `generate_order_suggestions()` 改为委托 controller
  - `export_order_plan()` 改为委托 controller
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 增加上述 controller 入口导入校验

## 为什么先抽这四个

- 都属于单向动作，失败边界清晰。
- 不直接改动最敏感的真实提交链和 SDK 下单确认链。
- 能快速减少主窗口里交易执行页的流程细节堆积。

## 当前收益

- 主窗口进一步回归编排层。
- 交易执行链开始形成和推荐链、扫描链一致的 controller 风格。
- 后续继续抽 `导出执行结果 / SDK 同步 / 生成实盘脚本 / 确认提交` 时有了统一落点。

## 风险控制

- 本轮不修改订单意图生成规则。
- 本轮不调整真实下单确认和失败回退流程。
- 保持编译检查、Qt 启动冒烟、全量单测三层验证。
