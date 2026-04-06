# 迭代 30 - 刷新面板与榜单渲染抽离

## 目标
- 继续把首页和推荐页中的纯展示型刷新逻辑从主窗口抽离。
- 让 `ui_refresh.py` 开始承接更多卡片、榜单和摘要面板更新。

## 用户价值
- 后续继续调优 `掘龙榜`、`战法明细`、`市场快照摘要` 时，改动位置更集中。
- 首页与推荐页的展示层会更容易统一风格和做组件化演进。

## 本次范围
- 在 [ui_refresh.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_refresh.py) 中新增：
  - `refresh_strategy_focus_detail(...)`
  - `populate_market_depth_texts(...)`
  - `render_leaderboard_cards(...)`
- 在 [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中将对应窗口方法改为委托调用。

## 实现方案
- `战法明细` 继续保留主窗口入口，但实际字符串拼装迁到 `ui_refresh.py`。
- `市场快照摘要` 中的左侧文本面板更新迁到 `ui_refresh.py`。
- `掘龙榜` 卡片展示也由 `ui_refresh.py` 统一渲染。

## 验收标准
- `app_qt.py`、`ui_refresh.py`、`tests/test_core.py` 编译通过。
- 入口测试可导入 `render_leaderboard_cards`。
- 全量单元测试继续通过。
- 推荐页战法明细、首页左侧摘要、右侧榜单卡片仍能正常刷新。

## 风险
- 当前 `ui_refresh.py` 仍以 `window` 为依赖入口，后续需要进一步收窄接口。
- 若继续抽表格填充逻辑，需要注意不要把颜色规则和业务判断混进同一层。

## 下一步
- 继续评估抽离表格填充逻辑，例如首页算法池、题材榜、龙头榜。
- 开始考虑为 `overview / recommend / board` 引入更明确的 binder/controller 模式。
