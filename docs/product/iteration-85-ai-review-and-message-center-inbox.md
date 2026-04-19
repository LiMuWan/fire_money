# 迭代 85：AI 评测与统一消息中心 Inbox 收口

## 目标

- 把推荐页里的 AI 评测从“单次调用”推进到“可配置、可流式、可自动重评”的研究辅助能力。
- 把消息、AI、交易回执统一收敛到同一个消息中心，并补齐 inbox 级别的消费动作。
- 为后续人工验收和桌面 smoke 留下更清晰的产品口径。

## 本轮完成

### 1. GPT-5.4 单票评测接入

- 新增 OpenAI 请求模块：
  - `quant_hunter/ai_review.py`
- 支持：
  - `Responses API`
  - `gpt-5.4`
  - 流式输出
  - 本地配置保存
  - 结构化上下文拼装

### 2. AI 评测配置页

- 在配置页新增 AI 配置区：
  - Base URL
  - API Key
  - 模型
  - 推理强度
  - 超时
  - 最大输出
- 支持自动重评开关：
  - 推荐链路变化后自动重评当前焦点
  - 消息源载入后自动触发
  - 推荐池刷新后自动触发

### 3. 推荐页 AI 评测面板

- 推荐页新增 `AI评测当前焦点` 按钮。
- 推荐页新增 `AI评测` 面板。
- 支持：
  - 手动触发
  - 流式展示
  - 成功/失败回填
  - 结果本地缓存

### 4. 统一消息中心

- 推荐页新增 `统一消息中心` 面板。
- 汇总事件来源：
  - AI 评测开始/完成/失败
  - 消息源载入成功/失败
  - 推荐池刷新
  - 交易提交成功/失败
- 支持：
  - 分类筛选
  - 状态详情
  - 事件表格
  - 颜色优先级
  - 顶部弹条提醒

### 5. Inbox 能力

- 事件状态：
  - 未读 / 已读
  - 未处理 / 已处理
- 交互动作：
  - 标已读
  - 标已处理
  - 全标已读
  - 清已处理
  - 只看未处理
- 路由动作：
  - 定位股票
  - 打开关联页
  - 建议动作文案

### 6. 状态持久化

- `AppState` 已保存：
  - AI 配置
  - AI 自动重评开关
  - 消息中心事件历史
  - 消息中心筛选偏好
  - 只看未处理偏好
- 敏感字段继续复用 DPAPI：
  - `ai_review_api_key`

## 当前推荐页工作流

1. 载入消息源或刷新推荐池。
2. 当前焦点发生变化时，按配置决定是否自动触发 AI 评测。
3. AI 评测结果流式显示在推荐页。
4. AI / 消息 / 交易事件同步进入统一消息中心。
5. 用户在消息中心中：
   - 查看详情
   - 跳到关联股票或页面
   - 标记已读/已处理
   - 用 `只看未处理` 聚焦剩余待办

## 当前交付口径

- 这套能力已经不只是“信息展示”，而是：
  - 能自动生成研究辅助结论
  - 能把关键事件汇总成 inbox
  - 能给出下一步建议动作
  - 能在桌面端保持历史上下文

## 已做验证

- `py_compile`
- 相关单测与 UI 辅助测试：
  - `tests/test_ai_review.py`
  - `tests/test_message_center.py`
- 运行命令：

```powershell
python -m unittest -v tests.test_ai_review tests.test_message_center tests.test_core.StrategyWorkflowTests.test_app_state_persists_news_source_settings tests.test_core.StrategyWorkflowTests.test_app_state_persists_strategy_and_license_settings tests.test_core.StrategyWorkflowTests.test_app_state_encrypts_sensitive_broker_credentials tests.test_core.StrategyWorkflowTests.test_save_strategy_preferences_controller_persists_risk_profile tests.test_core.StrategyWorkflowTests.test_switch_strategy_risk_profile_controller_switches_and_saves
```

## 已知边界

- 这轮还没有做完整的桌面 GUI 自动点击验收，当前以单测 + 轻量 Qt smoke 为主。
- `python -m unittest discover -s tests -v` 整套测试仍然较重，未在本轮作为交付口径强制通过。
- AI 评测仍定位为研究辅助，不替代人工最终交易决策。

## 下一步建议

- 做一轮真实桌面 smoke：
  - 载入消息源
  - 刷新推荐池
  - 触发 AI 评测
  - 检查消息中心未读/待处理计数
  - 标已读、标已处理、全标已读、清已处理
- 如果要继续产品化，可以再补：
  - 排序切换
  - 事件来源统计卡片
  - 更细的优先级规则
