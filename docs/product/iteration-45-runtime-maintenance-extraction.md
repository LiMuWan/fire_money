# 迭代 45 - 运行维护能力继续抽离

## 目标
- 继续把运行维护相关逻辑从主窗口中迁出。
- 优先处理缓存清理和任务结果记录这两块高频维护代码。
- 保持应用在重构过程中持续可启动。

## 本次变更
- 在 [ui_runtime.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_runtime.py) 新增：
  - `clear_market_cache(...)`
  - `record_job_result(...)`
- [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中：
  - `clear_market_cache()` 已改为委托 runtime 模块
  - `_record_job_result()` 已改为委托 runtime 模块

## 价值
- 运行维护链路进一步脱离主窗口。
- 缓存清理、任务结果统计、运行面板刷新开始汇聚到同一条 runtime 支线。
- 后续再做运行诊断增强时，不需要再回到主窗口中修改长逻辑。

## 验收
- 缓存清理后运行面板仍可正确刷新。
- 后台任务成功/失败后运行状态仍可正常更新。
- Qt 主窗口可正常启动。
- 编译检查、启动冒烟测试、全量测试全部通过。

## 下一步
- 继续评估运行诊断和缓存维护是否适合形成更完整的 runtime service。
- 再回头处理仍留在主窗口中的零散状态汇总代码。
