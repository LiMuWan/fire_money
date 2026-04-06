# 迭代 33 - 扫描页表格刷新抽离

## 目标
- 将扫描页中最基础的两张表格填充逻辑从主窗口抽离。
- 继续把 `app_qt.py` 往“状态 + 调度”结构收敛。

## 用户价值
- 扫描结果表和回测摘要表后续继续调整列展示或样式时，改动位置更集中。
- 扫描页与推荐页、首页的展示层结构开始趋同，后面更容易统一维护。

## 本次范围
- 在 [ui_refresh.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_refresh.py) 中新增：
  - `fill_scan_rows(...)`
  - `fill_backtest_summaries(...)`
- 在 [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中将 `_fill_scan_rows()`、`_fill_backtest_summaries()` 改为委托调用。

## 实现方案
- 扫描页表格仍由主窗口维护状态数据源。
- `ui_refresh.py` 负责把状态数据落到 `QTableWidget`。
- 先迁移表格填充本身，不调整扫描流程、监控逻辑和状态更新时机。

## 验收标准
- `app_qt.py`、`ui_refresh.py`、`tests/test_core.py` 编译通过。
- 入口测试可导入 `fill_scan_rows`。
- 全量单元测试继续通过。
- 扫描结果表和回测摘要表仍能正常刷新。

## 风险
- 扫描页的盘中监控和观察池联动尚未抽离，后续重构仍需要注意调用链顺序。
- 若继续抽离监控刷新逻辑，需要区分“纯展示”与“告警状态变更”两类责任。

## 下一步
- 继续评估扫描页监控摘要与观察池刷新是否适合抽到 `ui_refresh.py`。
- 开始考虑把首页、推荐页、扫描页的刷新入口整理成更明确的 binder/controller。
