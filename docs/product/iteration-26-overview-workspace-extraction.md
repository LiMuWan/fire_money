# 迭代 26 - 首页总览 Workspace Builder 拆分

## 目标
- 将 `首页总览` 的页面构建逻辑从主窗口中抽离，继续收敛 `app_qt.py` 的体量。
- 在不改动刷新链路和业务联动的前提下，把首页布局与控件装配统一转入 builder 模式。

## 用户价值
- 首页后续继续调整布局、放大图表、压缩说明区时，改动会更集中。
- 首页主控台的按钮、图表、榜单、摘要卡和参数区更容易独立优化，不容易误伤其它页面。

## 本次范围
- 在 [workspace_builders.py](C:\Users\18335\Documents\New%20project\quant_hunter\workspace_builders.py) 中新增 `build_overview_workspace(...)`。
- 在 [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中将 `_build_overview_tab()` 改为委托调用。
- 将首页的快捷按钮区、搜索筛选区、指标卡、优先级卡、三栏主控台、参数区统一迁入 builder。

## 实现方案
- `build_overview_workspace(...)` 接收表格构建函数、参数对象工厂和卡片类依赖。
- 页面状态字段仍挂在 `QuantHunterWindow` 上，保留既有刷新方法和联动逻辑。
- 先拆“页面装配”，不拆“页面刷新”，以降低回归风险。

## 验收标准
- `app_qt.py` 与 `workspace_builders.py` 编译通过。
- 入口测试可导入 `build_overview_workspace`。
- 全量单元测试继续通过。
- 首页原有按钮、图表、榜单、摘要卡和参数输入区仍能正常初始化。

## 风险
- 首页仍有较多刷新与联动方法留在主窗口中，后续继续拆分时需要进一步抽出 overview controller / binder。
- 由于历史编码问题，主窗口仍存在少量旧文本残留，后续应逐步统一成干净 UTF-8 文案。

## 下一步
- 优先评估拆分 `每日推荐` 的 builder。
- 继续整理首页刷新链，把侧边摘要、图表刷新和数据源状态联动逐步从主窗口剥离。
