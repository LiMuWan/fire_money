# 迭代 65：首页指标卡 Snapshot 抽离

## 本轮目标

- 将首页指标卡文案和数值摘要从主窗口里抽成独立 snapshot helper。
- 清理该区域遗留的历史坏文案，并让首页壳层刷新时一并更新指标卡。

## 本轮改动

- 更新 [ui_refresh.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_refresh.py)
  - 新增 `build_dashboard_metrics_snapshot(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_update_dashboard_metrics()` 改为委托 snapshot helper
  - `shell/header` 刷新时会同步更新首页指标卡
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增 `build_dashboard_metrics_snapshot` 入口导入校验

## 当前收益

- 首页第一屏指标卡不再依赖主窗口内嵌拼装逻辑。
- 该区域的坏文案已经恢复正常。
- 后续继续做首页主控台优化时，可以围绕 snapshot helper 扩展而不是回到主窗口里堆逻辑。
