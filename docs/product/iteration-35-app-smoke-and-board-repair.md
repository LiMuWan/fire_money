# 迭代 35 - 应用启动冒烟验证与打板页面修复

## 目标
- 为重构过程补上一条真正的“应用可启动”保险线。
- 修复打板监控页因重构遗漏导致的窗口启动失败问题。

## 用户价值
- 以后每次重构后，不只是单元测试通过，还能确认窗口本身可以正常构建。
- 打板监控页不会再因为缺失刷新入口而在启动阶段直接报错。

## 本次范围
- 在 [tests/test_core.py](C:\Users\18335\Documents\New%20project\tests\test_core.py) 中新增 `test_qt_window_smoke_boot`。
- 在 [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中补回 `_refresh_board_mode()`。
- 让打板监控页的候选表、监控表、说明区能在窗口构建后正常刷新。

## 实现方案
- 冒烟测试使用 `QApplication` 创建主窗口并执行 `processEvents()`，确认工作区标签页至少能完成构建。
- `_refresh_board_mode()` 使用现有 [BoardModeEngine](C:\Users\18335\Documents\New%20project\quant_hunter\board.py) 生成候选与监控结果，再填充 UI。
- 保持现有页面入口与导出逻辑不变，仅补齐缺失刷新实现。

## 验收标准
- `app_qt.py`、`tests/test_core.py` 编译通过。
- `test_qt_window_smoke_boot` 单独执行通过。
- 全量单元测试继续通过。
- 应用窗口可正常构建，打板监控页不再阻断启动。

## 风险
- 当前冒烟测试验证的是“窗口能构建”，还不是完整交互回归；后续如果需要更强保障，可以继续补工作区级 smoke。
- 打板页刷新逻辑目前已经恢复，但后续若继续抽离 binder，仍需再次核对页面入口是否齐全。

## 下一步
- 在继续重构前，默认先保留并运行这条冒烟测试。
- 后续若继续拆 `overview / recommend / scanner` binder，可再补更多页面级 smoke 检查。
