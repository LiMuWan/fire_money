# 迭代 49 - 配置状态链首批抽离

## 目标
- 不只把配置页页面装配抽出去，还要开始拆配置页的状态链。
- 优先处理最核心的两段：保存配置、授权状态刷新。
- 保持重构过程中应用持续可启动。

## 本次变更
- 在 [ui_binders.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_binders.py) 新增 `refresh_license_status_view(...)`。
- 在 [ui_controllers.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_controllers.py) 新增 `save_strategy_preferences_controller(...)`。
- [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中：
  - `save_strategy_preferences()` 已改为委托 controller
  - `_refresh_license_status_view()` 已改为委托 binder

## 价值
- 配置页开始形成和其他业务链一致的结构：
  - builder
  - binder
  - controller
- 主窗口里的配置状态写回再次减少。
- 后续如果继续处理授权切换、模板约束、版本能力刷新，会更容易沿这条线继续抽离。

## 验收
- 保存配置后，授权状态、推荐池和监控摘要仍能联动刷新。
- Qt 主窗口可正常启动。
- 编译检查、启动冒烟测试、全量测试全部通过。

## 下一步
- 继续评估 `activate_professional_plan / reset_trial_plan / activate_enterprise_plan` 是否适合一并迁入 controller。
- 继续清理配置页与运行维护页相邻的零散状态逻辑。
