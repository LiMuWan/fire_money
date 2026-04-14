# 迭代 63：推荐执行状态 Helper 抽离

## 本轮目标

- 将推荐页和首页共用的执行状态摘要逻辑从主窗口里抽成独立 helper。
- 进一步减少主窗口对状态统计细节的直接依赖。

## 本轮改动

- 新增 [recommend_status.py](C:/Users/18335/Documents/New%20project/quant_hunter/recommend_status.py)
  - `execution_status_for_symbol(...)`
  - `recommend_execution_summary(...)`
  - `execution_summary_for_rows(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_execution_status_for_symbol()` 改为委托 helper
  - `_recommend_execution_summary()` 改为委托 helper
  - 首页命令面板执行摘要改为复用 `execution_summary_for_rows(...)`
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增 `recommend_status` 入口导入校验

## 当前收益

- 首页和推荐页对执行状态的统计口径更统一。
- 主窗口继续向编排层收缩。
