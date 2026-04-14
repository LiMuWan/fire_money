# 迭代 64：首页命令面板 Snapshot 抽离

## 本轮目标

- 将首页命令面板与执行面板的摘要拼装逻辑从主窗口里抽成 snapshot helper。
- 同时清理该区域遗留的历史坏文案。

## 本轮改动

- 更新 [ui_refresh.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_refresh.py)
  - 新增 `build_overview_command_snapshot(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_refresh_overview_command_deck()` 改为委托 snapshot helper
  - 清理不再需要的旧状态统计 import
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 补充 `build_overview_command_snapshot` 入口导入校验

## 当前收益

- 首页命令面板与执行面板摘要不再堆在主窗口里。
- 该区域的历史乱码文案已经恢复为正常中文。
- 后续若继续做首页摘要卡、命令面板或晨会视图，可以继续围绕 snapshot helper 扩展。
