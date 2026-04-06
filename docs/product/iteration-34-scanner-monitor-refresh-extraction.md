# 迭代 34 - 扫描页监控刷新抽离

## 目标
- 将扫描页中观察池刷新与盘中监控刷新逻辑从主窗口继续抽离。
- 让扫描页开始具备更明确的展示层刷新模块边界。

## 用户价值
- 观察池、盘中监控表和监控摘要后续继续优化时，改动位置更集中。
- 扫描页的结构更接近首页与推荐页，后面统一做 binder/controller 会更顺。

## 本次范围
- 在 [ui_refresh.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_refresh.py) 中新增：
  - `refresh_watchlist(...)`
  - `refresh_intraday_monitor(...)`
- 在 [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中将 `_refresh_watchlist()`、`_refresh_intraday_monitor()` 改为委托调用。

## 实现方案
- `refresh_watchlist(...)` 负责观察池列表控件刷新，并联动盘中监控刷新。
- `refresh_intraday_monitor(...)` 负责监控表填充、题材掉队提醒摘要和声音提示触发。
- 仍保留主窗口中的业务状态与入口，先迁移展示与监控刷新实现。

## 验收标准
- `app_qt.py`、`ui_refresh.py`、`tests/test_core.py` 编译通过。
- 入口测试可导入 `refresh_intraday_monitor`。
- 全量单元测试继续通过。
- 观察池刷新、盘中监控表刷新、监控摘要与提示音逻辑继续可用。

## 风险
- 盘中监控刷新不再只是纯表格展示，已经包含部分提醒状态变更，需要谨慎继续下沉。
- 若后续继续抽离扫描页逻辑，建议把“监控状态计算”和“监控 UI 渲染”再分两层。

## 下一步
- 评估是否正式引入 `scanner / overview / recommend` 的 binder/controller 模块。
- 继续清理主窗口中剩余的大块刷新逻辑，尤其是首页侧边摘要与市场文本面板。
