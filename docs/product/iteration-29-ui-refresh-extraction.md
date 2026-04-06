# 迭代 29 - UI 刷新链第一批抽离

## 目标
- 开始将首页与推荐页中的纯 UI 刷新逻辑从主窗口抽离。
- 为后续整理 `overview / recommend / board` 的 binder 或 controller 做准备。

## 用户价值
- 后续继续调整卡片内容、优先级面板和路径推演时，改动会更集中。
- 主窗口中与业务无关的卡片刷新代码减少，定位问题更快。

## 本次范围
- 新增 [ui_refresh.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_refresh.py)。
- 将以下方法改为委托调用：
  - `推荐摘要卡刷新`
  - `动作流程卡刷新`
  - `优先级卡刷新`
  - `主线推演路径刷新`
  - `首页盘前优先级卡刷新`

## 实现方案
- `ui_refresh.py` 先承接纯展示型刷新，不触碰推荐生成、题材计算、决策引擎等业务逻辑。
- `app_qt.py` 中同名方法保留，以委托形式兼容现有调用点。
- 通过这种“保留窗口入口、迁出实现”的方式，逐步降低重构风险。

## 验收标准
- `app_qt.py`、`ui_refresh.py`、`tests/test_core.py` 编译通过。
- 入口测试可导入 `refresh_priority_cards`。
- 全量单元测试继续通过。
- 首页和推荐页的摘要卡、动作流程卡、优先级卡、路径面板仍能正常刷新。

## 风险
- 当前 `ui_refresh.py` 仍通过 `window` 访问控件和显示方法，后续需要进一步收敛接口。
- 如果继续抽离更多刷新逻辑，应避免把过多业务判断也迁入 UI 模块。

## 下一步
- 优先继续整理 `overview / recommend / board` 的面板刷新与表格填充逻辑。
- 评估将首页与推荐页的刷新链拆成更明确的 binder/controller。
