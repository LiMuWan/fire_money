# 迭代 50 - 授权切换 Controller 抽离

## 目标
- 把配置页中的授权切换入口也纳入 controller 层。
- 让配置页的版本切换链路进一步完整。
- 保持重构过程中应用持续可启动。

## 本次变更
- 在 [ui_controllers.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_controllers.py) 新增 `switch_license_plan_controller(...)`。
- [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中：
  - `activate_professional_plan()`
  - `reset_trial_plan()`
  - `activate_enterprise_plan()`
  已全部改为委托 controller。

## 价值
- 配置页的“保存配置”和“切换授权”都开始统一进入 controller 层。
- 主窗口中的配置状态操作继续减少。
- 后续如果接入真实授权服务，controller 会是更自然的接入点。

## 验收
- 试用版 / 专业版 / 企业版切换后，状态面板仍能正常刷新。
- Qt 主窗口可正常启动。
- 编译检查、启动冒烟测试、全量测试全部通过。

## 下一步
- 继续评估配置页其余零散状态入口，尽量把配置链路收完整。
- 开始考虑是否把授权能力规则本身再往 service 层抽。
