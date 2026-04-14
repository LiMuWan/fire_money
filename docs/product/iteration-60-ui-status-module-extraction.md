# 迭代 60：状态显示规则模块抽离

## 本轮目标

- 将交易执行页和刷新层共用的状态显示规则从主窗口中抽出。
- 降低 `ui_refresh` 对主窗口包装方法的依赖。

## 本轮改动

- 新增 [ui_status.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_status.py)
  - `signal_colors(...)`
  - `submission_colors(...)`
  - `display_order_status(...)`
  - `display_fill_status(...)`
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_signal_colors()`、`_submission_colors()`、`_display_order_status()`、`_display_fill_status()` 改为轻量委托
- 更新 [ui_refresh.py](C:/Users/18335/Documents/New%20project/quant_hunter/ui_refresh.py)
  - 直接使用状态模块，而不是依赖主窗口里的颜色/状态包装方法
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - 新增 `ui_status` 入口导入校验

## 当前收益

- 刷新层与主窗口解耦更进一步。
- 后续若统一全局状态色、委托状态色、交易动作文案，可以只改一处。
