# 迭代 51 - UI 文案修复与稳定性验证

## 背景

在最近几轮 builder / binder / controller / runtime 拆分后，部分新抽离模块里出现了可见文案损坏，主要表现为：

- 配置页出现 `????`
- 推荐页多处标题、表头、说明文本乱码
- 运行面板和缓存清理提示存在历史编码串
- 交易执行页少量表头仍未修复

这些问题虽然不直接影响核心算法，但已经影响产品可用性和专业感，因此本轮优先级从“继续抽象”切回“先修可见质量，再保运行”。

## 本轮调整

### 1. 修复配置页文案

已修复：

- 策略配置 / 商业化 Hero 区
- 策略参数分组
- 授权与状态分组
- 说明区
- 保存按钮与版本切换按钮

### 2. 修复推荐页文案

已修复：

- 页头 Hero 文案
- 导入 / 刷新按钮
- 题材筛选 / 战法筛选 / 动作筛选
- 题材热度榜、龙头股榜、每日推荐股票池
- 五大战法工作台
- 战法明细联动
- 决策流程总览
- 优先级排序面板
- 盘中提醒面板
- 主线推演路径
- 决策摘要卡
- 推荐逻辑说明 / 交易计划 / 市场情绪 / 持仓建议

### 3. 修复运行时面板文案

已修复：

- 运行概览
- 最近任务状态
- 日志导出说明
- 缓存清理反馈

### 4. 修复交易执行页尾部表头

已修复：

- 执行指标
- 委托建议
- 订单建议表头

## 设计原则

这轮没有继续做大范围结构调整，而是遵循以下原则：

- 先修用户已经能看到的问题
- 只改可见文案和轻量状态提示
- 尽量不改动业务逻辑
- 每轮修改后都执行启动冒烟验证

## 验证

本轮完成后已执行：

```powershell
C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_refresh.py quant_hunter\workspace_builders.py quant_hunter\ui_binders.py quant_hunter\ui_controllers.py quant_hunter\ui_runtime.py
C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest tests.test_core.StrategyWorkflowTests.test_qt_window_smoke_boot -v
C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v
```

结果：

- Qt 主窗口启动正常
- 推荐页 / 配置页 / 运行页装配链正常
- 当前测试总数 35 项，全部通过

## 下一步

下一轮建议继续两条线并行推进：

1. 继续清理其他 workspace builder 中残余的历史乱码文本。
2. 在保证界面稳定的前提下，继续把配置页和交易页状态链往 binder / controller / policy 方向收。
