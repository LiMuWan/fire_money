# 迭代 62：显示 Helper 统一收口

## 本轮目标

- 把动作、模式、龙头级别等显示文案统一收口到状态显示模块。
- 顺手修复一个历史编码污染导致的动作文案坏码问题。

## 本轮改动

- 更新 [ui_status.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_status.py)
  - 新增 `display_action(...)`
  - 新增 `display_label(...)`
  - 新增 `display_mode(...)`
  - 新增 `display_leader_level(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_display_action()`、`_display_label()`、`_display_mode()`、`_display_leader_level()` 改为轻量委托
  - 修复 `_display_action()` 中历史坏码文案
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 补充上述显示 helper 入口导入校验

## 当前收益

- 全局显示口径进一步统一。
- 后续若做多语言、版本词汇统一或配色联动，可继续围绕 `ui_status` 扩展。
