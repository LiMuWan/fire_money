# 迭代 36 - 每日推荐 Binder 首批抽离

## 目标
- 把“每日推荐结果写回界面”的主链从主窗口中抽离一层。
- 为后续拆分 `recommend controller / binder` 打基础。
- 保持应用在重构过程中持续可启动、可刷新、可测试。

## 本次变更
- 新增 [ui_binders.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_binders.py)。
- 抽出 `apply_daily_pool_rows(window, rows, summarize_themes_fn)`，统一负责：
  - 写入 `daily_pool_rows`
  - 汇总题材热度与龙头候选
  - 刷新推荐页题材筛选
  - 刷新每日股票池表格
  - 刷新题材热度榜与龙头股榜
  - 刷新推荐摘要文本
  - 刷新交易计划与打板监控
- [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中 `_apply_daily_pool_rows()` 改为委托调用 binder。

## 价值
- 主窗口进一步收敛成“调度 + 状态”角色。
- 每日推荐主链有了明确边界，后续更适合继续拆成 `binder + controller + refresh`。
- 推荐页、交易计划、打板页之间的联动入口更加集中，后续修问题更快。

## 验收
- 应用窗口可正常启动。
- 每日推荐生成后，推荐池、题材榜、龙头榜、交易计划、打板监控仍然同步刷新。
- 单元测试与 Qt 启动冒烟测试全部通过。

## 下一步
- 继续抽离扫描结果写回链路。
- 评估是否引入 `recommend binder` 与 `scan binder` 两个明确入口。
