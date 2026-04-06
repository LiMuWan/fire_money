# 迭代 25 - 交易执行 Workspace Builder 拆分

## 目标
- 将 `交易执行` 工作区从主窗口中抽离，验证复杂页面也可以稳定迁移到 builder 模式。
- 让 `app_qt.py` 进一步回归为编排层，而不是继续承载大块 UI 装配细节。

## 用户价值
- 交易执行页后续增加风控、授权、日志和下单联动时，改动会更集中。
- 页面结构更清晰，减少在主窗口大文件里定位和修改控件的成本。

## 本次范围
- 在 [workspace_builders.py](C:\Users\18335\Documents\New%20project\quant_hunter\workspace_builders.py) 中新增 `build_broker_workspace(...)`。
- 在 [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中将 `_build_broker_tab()` 改为委托调用。
- 将交易执行页的 hero、账户表单、执行按钮区、状态日志区、持仓表、委托表、下单结果区收敛到同一 builder。

## 实现方案
- `build_broker_workspace(window, build_table, adapter_factory, project_root)` 负责布局和控件装配。
- 主窗口仅传入依赖：表格构建函数、券商适配器工厂、项目根目录。
- 页面内的业务动作仍由 `QuantHunterWindow` 现有方法处理，先不改业务链路。

## 验收标准
- `app_qt.py` 与 `workspace_builders.py` 编译通过。
- 入口测试可以导入 `build_broker_workspace`。
- 全量单元测试继续通过。
- 交易执行页原有按钮、表格、日志区仍可正常初始化。

## 风险
- 交易执行页依赖较多窗口状态字段，后续继续拆分时需要控制 builder 与窗口状态的耦合。
- 若继续抽离更深层逻辑，应逐步把页面状态对象化，而不是在 builder 中直接堆更多字段。

## 下一步
- 优先拆 `首页总览` 或 `每日推荐` 的 builder。
- 继续把页面里的摘要卡、提醒链和联动表格从主窗口中收敛出去。
