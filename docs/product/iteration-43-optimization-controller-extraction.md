# 迭代 43 - 参数优化 Controller 抽离

## 目标
- 把独立业务流程也开始迁入 controller 层，而不只是刷新链路。
- 优先选择参数优化这个边界清晰、风险较低的功能入口。
- 保证重构过程中应用持续可启动。

## 本次变更
- 在 [ui_controllers.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_controllers.py) 新增 `run_parameter_optimization_controller(...)`。
- [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中 `run_parameter_optimization()` 已改为委托 controller。

## 这一层负责什么
- 判定是否具备优化前置数据
- 准备优化参数与样本
- 启动后台任务
- 处理成功结果写回与失败提示
- 维护运行日志

## 价值
- controller 层开始从“刷新调度”扩展到“业务流程调度”。
- 后续优化、导出、复盘等流程可以沿用同样的抽离路径。
- 主窗口继续退回到编排角色。

## 验收
- 参数优化入口可正常运行。
- Qt 主窗口可正常启动。
- 编译检查、启动冒烟测试、全量测试全部通过。

## 下一步
- 继续评估导出链、运行时诊断链是否也适合迁入 controller。
- 再回头处理扫描入口的真实使用路径，而不是盲目增加未接线的 controller。
