# 迭代 42 - 通用后台任务 Controller 抽离

## 目标
- 把主窗口中的通用异步任务调度逻辑再往 controller 层收一层。
- 为后续更多页面共用统一后台执行框架打基础。
- 在重构过程中持续保证应用可启动。

## 本次变更
- 在 [ui_controllers.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_controllers.py) 新增 `run_background_job_controller(...)`。
- [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中 `_run_background_job()` 已改为委托 controller。

## 当前 controller 覆盖范围
- `refresh_daily_pool_controller(...)`
- `refresh_remote_market_controller(...)`
- `run_background_job_controller(...)`

## 价值
- 主窗口不再直接持有通用异步调度的长逻辑。
- 后续要扩展扫描、优化、回测、导出等后台任务时，可以复用同一 controller 模式。
- 项目结构更接近：
  - builder
  - refresh
  - binder
  - controller
  - orchestrator

## 验收
- 异步任务仍能正常更新运行日志与状态。
- Qt 主窗口可正常启动。
- 编译检查、启动冒烟测试、全量测试全部通过。

## 下一步
- 继续补齐扫描 controller。
- 评估是否需要把运行时诊断面板也拆成独立 controller / service。
