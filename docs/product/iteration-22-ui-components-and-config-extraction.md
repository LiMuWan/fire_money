# 迭代 22 - UI 组件与配置抽离

## 目标
- 继续降低 `app_qt.py` 的体量和耦合度。
- 先把最稳定、最独立的 UI 组件层和 UI 配置层拆出去。
- 为后续拆分 overview / recommend / broker workspace builder 做准备。

## 本轮完成

### 1. 抽离 UI 卡片组件
- 新增 [ui_cards.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_cards.py)
- 从 [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中移出：
  - `InsightCardBase`
  - `LeaderboardCard`
  - `StrategyWorkbenchCard`
  - `ActionFlowCard`
  - `CompactSummaryCard`
  - `AlertSignalCard`

收益：
- 主窗口文件不再同时承担“业务编排 + 卡片组件定义”两层职责。
- 后续新增卡片时可以直接在组件模块扩展。
- UI 组件可以更容易复用到其他工作区。

### 2. 抽离 UI 常量与路由配置
- 新增 [ui_config.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_config.py)
- 从主文件集中迁出：
  - `THEME_OPTIONS`
  - `DISPLAY_TEXT`
  - `WORKSPACE_TAB_LABELS`
  - `WORKSPACE_TAB_ORDER`
  - `WORKSPACE_LABEL_BY_KEY`
  - `OVERVIEW_QUICK_ROUTE_SPECS`
  - `STRATEGY_FILTER_LABELS`
  - `STRATEGY_SCORE_FIELDS`
  - `STRATEGY_WORKBENCH_SPECS`

收益：
- 解决了主文件顶部重复常量和损坏文本并存的问题。
- 页面标题、快捷入口、战法映射有了单一权威来源。
- 后续更换命名、重排工作区或新增战法时改动更集中。

### 3. 主窗口改为只做编排
- [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 现在通过 import 使用组件和配置模块。
- 现有测试对 `app_qt` 的导入兼容性保持不变，外部仍可从 `app_qt` 访问这些类名。

## 结构收益
- `app_qt.py` 更接近“主控制器”角色。
- `ui_cards.py` 更接近“视图组件库”角色。
- `ui_config.py` 更接近“UI 元数据中心”角色。

这三层拆开后，下一步再拆 workspace builder 的风险会明显下降。

## 下一步建议
1. 把 overview / recommend / broker 的构建函数继续拆成独立 builder。
2. 把表格联动、页面跳转、状态栏更新抽成共享 controller。
3. 开始逐页核查功能完成度，补齐仍偏展示型的页面逻辑。

## 验收
- `app_qt.py`、`ui_cards.py`、`ui_config.py` 均可通过 `py_compile`
- 全量单元测试通过
- 原有首页、推荐页、提醒面板、榜单卡片不回退
