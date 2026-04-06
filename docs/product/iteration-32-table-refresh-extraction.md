# 迭代 32 - 核心表格刷新抽离

## 目标
- 继续将首页与推荐页中最核心的表格填充逻辑从主窗口抽离。
- 让 `ui_refresh.py` 更接近真正的展示层 binder。

## 用户价值
- 首页算法池表格和推荐池表格后续继续调整字段、排序展示和样式时，改动位置更集中。
- 主窗口里的筛选与刷新逻辑边界更清晰，后续继续重构风险更低。

## 本次范围
- 在 [ui_refresh.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_refresh.py) 中新增：
  - `populate_filtered_daily_pool_table(...)`
  - `apply_market_filters(...)`
- 在 [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中将对应窗口方法改为委托调用。

## 实现方案
- `populate_filtered_daily_pool_table(...)` 负责推荐池按题材筛选后的表格落地。
- `apply_market_filters(...)` 负责首页算法池的筛选、表格填充、标签条渲染与后续联动触发。
- 主窗口仍保留筛选状态和业务入口，只迁移表格刷新实现。

## 验收标准
- `app_qt.py`、`ui_refresh.py`、`tests/test_core.py` 编译通过。
- 入口测试可导入 `apply_market_filters`。
- 全量单元测试继续通过。
- 首页算法池表格与推荐池表格仍能正常筛选、填充和联动刷新。

## 风险
- 首页算法池表格刷新仍依赖窗口中的颜色规则和 badge 构造方法，后续若继续下沉需要先抽统一表格渲染 helper。
- 如果继续抽更多表格逻辑，需要控制展示层和业务规则层的边界。

## 下一步
- 继续评估扫描页与回测摘要表格的填充逻辑抽离。
- 开始整理 `overview / recommend / scanner` 的刷新入口，把它们往更明确的 binder/controller 结构推进。
