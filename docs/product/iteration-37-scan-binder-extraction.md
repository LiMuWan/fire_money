# 迭代 37 - 扫描结果 Binder 首批抽离

## 目标
- 把本地扫描完成后的结果写回链路从主窗口中抽离。
- 让扫描页、推荐页、回测摘要、盘中监控的联动有独立入口。
- 在重构过程中继续保证应用可启动、可运行、可测试。

## 本次变更
- 在 [ui_binders.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_binders.py) 新增 `apply_scan_universe_result(window, folder, payload)`。
- [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中 `_apply_scan_universe_result()` 改为委托 binder 执行。
- Binder 统一负责：
  - 写入扫描结果、K 线缓存、分析结果、回测摘要
  - 刷新扫描页表格与回测摘要
  - 刷新盘中监控
  - 触发每日推荐刷新
  - 处理选中股票恢复与状态保存

## 价值
- 扫描主链从主窗口中退出来，后续更适合继续拆成 `scan controller / scan binder / scan refresh`。
- 扫描与推荐的联动边界更清晰，后面排查刷新问题更快。
- 主窗口继续向“调度层”收敛。

## 验收
- 本地扫描完成后，扫描表、回测摘要、盘中监控、每日推荐仍能联动刷新。
- Qt 主窗口可正常启动。
- 编译检查、启动冒烟测试、全量单元测试全部通过。

## 下一步
- 继续把首页市场刷新链抽成 binder/controller 入口。
- 评估是否将 `market screen result` 写回逻辑也迁出主窗口。
