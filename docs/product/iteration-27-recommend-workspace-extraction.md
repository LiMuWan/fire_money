# 迭代 27 - 每日推荐 Workspace Builder 拆分

## 目标
- 将 `每日推荐` 的页面构建逻辑从主窗口中抽离，进一步降低 `app_qt.py` 的页面复杂度。
- 保持推荐刷新、题材热度、龙头联动、战法工作台和交易计划逻辑不变，只拆布局与控件装配。

## 用户价值
- 推荐页后续继续扩充战法细节、提醒面板和交易计划联动时，改动范围更可控。
- 工作台结构更清晰，后续做界面整理、组件替换或样式统一会更顺。

## 本次范围
- 在 [workspace_builders.py](C:\Users\18335\Documents\New%20project\quant_hunter\workspace_builders.py) 中新增 `build_recommend_workspace(...)`。
- 在 [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中将 `_build_recommend_tab()` 改为委托调用。
- 将推荐页的导入按钮区、题材榜、龙头榜、每日股票池、五大战法工作台、提醒面板、摘要卡、交易计划区统一迁入 builder。

## 实现方案
- `build_recommend_workspace(...)` 接收表格构建函数、卡片类、战法配置常量。
- 主窗口继续保留推荐池刷新、题材联动、决策生成和提示链逻辑。
- 先拆“UI 装配层”，后续再评估是否继续抽推荐页的 binder/controller。

## 验收标准
- `app_qt.py` 与 `workspace_builders.py` 编译通过。
- 入口测试可导入 `build_recommend_workspace`。
- 全量单元测试继续通过。
- 推荐页原有表格、卡片、提醒区和联动控件仍可正常初始化。

## 风险
- 推荐页仍有较多刷新和联动方法留在主窗口，后续进一步抽象时需要注意事件耦合。
- 若后面继续拆推荐页逻辑，建议优先把“题材/龙头/交易计划刷新”抽成单独 binder，而不是直接把业务塞进 builder。

## 下一步
- 评估是否拆分 `打板监控` 的 builder。
- 继续整理首页与推荐页的刷新链，逐步把页面状态联动从主窗口中抽离。
