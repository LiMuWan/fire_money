# 迭代 67：交易执行页文案修复与 Builder 回归修复

## 本轮目标

- 清理交易执行页中仍然直接暴露给用户的 `????` 文案。
- 保持 `workspace builder` 重构继续推进，同时修复过程中引入的启动回归。

## 本轮改动

- 更新 [workspace_builders.py](C:/Users/18335/Documents/New%20project/quant_hunter/workspace_builders.py)
  - 重写 `build_broker_workspace(...)` 的文案层
  - 修复账户配置、交易动作、执行指标、运行维护、当前持仓、委托建议、提交记录、成交回顾等分组标题
  - 修复委托表、执行表、按钮、字段标签等用户可见文字
  - 修复 builder 错误创建 tab 的问题，恢复为与其他 workspace 一致的挂载方式
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - 修正首页市场主控区图表标题与动能标签的历史坏文案

## 当前收益

- 交易执行页现在从顶部 Hero 到中部表格、底部日志的主要文案都恢复成正常中文。
- Qt 启动冒烟再次证明交易执行页 builder 没有因为重写而破坏应用启动。
- 这一轮在“修可见问题”的同时，没有回退前面的分层重构成果。

## 验证

- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py quant_hunter\license_policy.py quant_hunter\ui_status.py quant_hunter\broker_status.py quant_hunter\recommend_status.py`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v`
- `C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v`
