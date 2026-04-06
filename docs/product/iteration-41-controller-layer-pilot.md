# 迭代 41 - Controller 层试点抽离

## 目标
- 不只抽 UI builder / refresh / binder，再向上抽一层轻量 controller。
- 先从风险最低的两条入口开始：每日推荐刷新、市场刷新。
- 保持应用在重构过程中持续可启动。

## 本次变更
- 新增 [ui_controllers.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_controllers.py)。
- 当前已落地两个 controller：
  - `refresh_daily_pool_controller(...)`
  - `refresh_remote_market_controller(...)`
- [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中：
  - `refresh_daily_pool()` 已改为委托 controller
  - `refresh_remote_market()` 已改为委托 controller

## 这一层负责什么
- 组装刷新所需参数
- 决定同步 / 异步执行路径
- 调用后台任务提交入口
- 串联成功回调与失败回调

## 价值
- 主窗口进一步脱离“业务流程脚本”的角色。
- 后续继续扩展 `scan controller / broker controller / runtime controller` 会更自然。
- 业务层次现在已逐步形成：
  - workspace builder
  - refresh
  - binder
  - controller
  - main window orchestrator

## 验收
- 每日推荐刷新正常。
- 市场刷新正常。
- Qt 主窗口可正常启动。
- 编译检查、启动冒烟测试、全量测试全部通过。

## 下一步
- 继续寻找扫描入口，补齐 `scan controller`。
- 开始评估是否需要抽统一的任务调度 controller。
