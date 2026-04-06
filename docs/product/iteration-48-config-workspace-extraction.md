# 迭代 48 - 配置页 Workspace Builder 抽离

## 目标
- 把刚修复的配置页也纳入 workspace builder 体系。
- 继续压缩主窗口中的页面装配代码。
- 保持应用在重构过程中持续可启动。

## 本次变更
- 在 [workspace_builders.py](C:\Users\18335\Documents\New%20project\quant_hunter\workspace_builders.py) 新增 `build_config_workspace(...)`。
- [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中 `_build_config_tab()` 已改为委托 builder。
- 当前配置页 builder 已覆盖：
  - 策略参数区
  - 授权状态区
  - 版本切换按钮
  - 保存配置入口
  - 配置说明区

## 价值
- 配置页不再是主窗口中的大块页面装配逻辑。
- 现在 `overview / recommend / board / auth / detail / broker / config` 都已进入 builder 体系。
- 后续继续拆配置页内部逻辑时，会更清晰。

## 验收
- 配置页仍可正常打开与保存。
- Qt 主窗口可正常启动。
- 编译检查、启动冒烟测试、全量测试全部通过。

## 下一步
- 继续清理配置页与运行维护周边的零散状态逻辑。
- 视情况开始收缩主窗口中的配置状态刷新分支。
