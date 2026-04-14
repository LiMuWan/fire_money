# 迭代 54：交易执行 Controller 第二轮抽离

## 本轮目标

- 继续收拢交易执行页外围流程。
- 在不动真实下单主链的前提下，把结果导出、SDK 同步和脚本生成迁入 controller。

## 本轮改动

- 更新 [ui_controllers.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_controllers.py)
  - 新增 `export_order_result_log_controller(...)`
  - 新增 `sync_broker_via_sdk_controller(...)`
  - 新增 `generate_sdk_strategy_script_controller(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `export_order_result_log()` 改为委托 controller
  - `sync_broker_via_sdk()` 改为委托 controller
  - `generate_sdk_strategy_script()` 改为委托 controller
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 增加上述 controller 入口导入校验

## 当前收益

- 交易执行页外围动作基本都不再直接堆在主窗口里。
- 主窗口保留更少的分支细节，更接近编排层。
- 后续只剩 `confirm_and_submit_orders()` 这条最敏感的真实提交链还在主窗口主干里。

## 风险控制

- 本轮不改真实下单确认弹窗。
- 本轮不改提交失败后的回退导出逻辑。
- 保持编译检查、Qt 启动冒烟、全量单测三层验证。

## 兼容修复

- 在 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py) 中补回了旧 builder 仍依赖的轻量 wrapper：
  - `_build_workspace_hero(...)`
  - `_style_terminal_panel(...)`
  - `_style_terminal_console(...)`
  - `_set_button_role(...)`
  - `_configure_splitter(...)`
  - `_enable_smooth_scroll(...)`
  - `_scan_universe(...)`
- 同时修复了顶部工作区页签标题显示，避免出现 `??`。
