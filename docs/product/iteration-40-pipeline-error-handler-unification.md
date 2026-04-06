# 迭代 40 - 主链错误入口统一

## 目标
- 把推荐失败、扫描失败也从主窗口中迁出。
- 让推荐链、扫描链、市场链都拥有成对的成功入口与失败入口。
- 在持续重构的同时，保证应用仍能正常启动。

## 本次变更
- 在 [ui_binders.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_binders.py) 新增：
  - `handle_daily_pool_error(...)`
  - `handle_scan_error(...)`
- [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中：
  - `_handle_daily_pool_error()` 已改为委托 binder
  - `_handle_scan_error()` 已改为委托 binder

## 当前主链结构
- 推荐链：
  - 成功：`apply_daily_pool_rows(...)`
  - 失败：`handle_daily_pool_error(...)`
- 扫描链：
  - 成功：`apply_scan_universe_result(...)`
  - 失败：`handle_scan_error(...)`
- 市场链：
  - 成功：`apply_market_screen_result(...)`
  - 失败：`handle_market_refresh_error(...)`

## 价值
- 主窗口进一步回到“调度层”角色。
- 三条核心业务链的成功/失败入口已经成体系，后续拆 controller 更容易。
- 错误处理逻辑集中后，后面做统一诊断和日志策略会更快。

## 验收
- 推荐失败、扫描失败、市场失败都能继续正确显示状态与日志。
- Qt 主窗口可正常启动。
- 编译检查、启动冒烟测试、全量测试全部通过。

## 下一步
- 继续清理 `app_qt.py` 中剩余直接状态写回逻辑。
- 评估是否开始抽 `controller` 层，而不再只停留在 binder / refresh / builder。
