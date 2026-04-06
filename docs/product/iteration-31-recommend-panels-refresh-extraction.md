# 迭代 31 - 推荐页面板刷新抽离

## 目标
- 继续将推荐页中的展示型刷新逻辑从主窗口中抽离。
- 为推荐页后续形成更清晰的 binder/controller 打下基础。

## 用户价值
- 题材热度榜、龙头股榜、五大战法工作台的展示刷新集中到同一模块，后续继续优化更容易。
- 推荐页联动复杂度下降，页面维护成本更低。

## 本次范围
- 在 [ui_refresh.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_refresh.py) 中新增：
  - `refresh_theme_heat_panels(...)`
  - `refresh_strategy_pack_panels(...)`
- 在 [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中将对应窗口方法改为委托调用。

## 实现方案
- `refresh_theme_heat_panels(...)` 负责刷新题材热度榜与龙头股榜。
- `refresh_strategy_pack_panels(...)` 负责刷新五大战法工作台卡片。
- 现有的事件入口与调用顺序保持不变，只迁移具体展示实现。

## 验收标准
- `app_qt.py`、`ui_refresh.py`、`tests/test_core.py` 编译通过。
- 入口测试可导入 `refresh_theme_heat_panels`。
- 全量单元测试继续通过。
- 推荐页题材榜、龙头榜、五大战法工作台仍能正常刷新。

## 风险
- 推荐页仍有部分表格填充和筛选逻辑留在主窗口，后续继续抽离时需要保持调用链稳定。
- 若继续下沉更多逻辑，应注意不要把业务排序规则误放进 UI 模块。

## 下一步
- 继续评估首页算法池表格与推荐页股票池表格的填充逻辑抽离。
- 开始整理 overview / recommend 的刷新入口与状态依赖，逐步形成 binder/controller。
