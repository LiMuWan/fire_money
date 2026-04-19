# 迭代 86：统一消息中心看板化与排序增强

## 目标

- 把推荐页里的统一消息中心从“事件列表”推进到“轻量看板”。
- 给消息中心补齐排序切换、统计卡片和更稳定的使用偏好持久化。
- 继续保持 inbox 流程不变：可读、可筛、可跳、可处理。

## 本轮完成

### 1. 排序切换

- 新增排序模式：
  - 最新优先
  - 未读优先
  - 待处理优先
  - 异常优先
- 排序会直接影响推荐页消息中心列表的显示顺序。
- 排序偏好已持久化，重启后仍保留。
- 当前支持：
  - 最新优先
  - 未读优先
  - 待处理优先
  - 异常优先

### 2. 来源 / 状态统计卡片

- 推荐页消息中心新增统计卡片：
  - 未读
  - 待处理
  - AI 事件
  - 消息事件
  - 交易事件
- 用于快速判断当前事件态势，而不必先翻表格。
- 卡片已接入点击联动：
  - `未读` 卡点击后切到未读优先排序
  - `待处理` 卡点击后切到只看未处理
  - `AI / 消息 / 交易` 卡点击后直接切换到对应分类

### 3. 偏好持久化补齐

- 已持久化：
  - 消息中心分类筛选
  - 只看未处理
  - 排序模式
- 这些偏好已加入 `AppState`。

### 4. 现有 inbox 能力保持

- 标已读
- 标已处理
- 全标已读
- 清已处理
- 只看未处理
- 顶部弹条提醒
- 推荐页 Tab 未读 / 待处理计数
- 推荐页内徽标

## 当前产品口径

统一消息中心现在已经具备三层能力：

1. **提醒层**
   - 顶部弹条
   - 推荐页 Tab 计数

2. **Inbox 层**
   - 已读 / 未读
   - 已处理 / 未处理
   - 筛选与清理动作

3. **看板层**
   - 排序切换
   - 统计卡片
   - 详情与建议动作
   - 卡片点击联动筛选

## 已做验证

- `py_compile`
- 相关单测
- 轻量 Qt UI smoke

推荐命令：

```powershell
python -m unittest -v tests.test_message_center tests.test_ai_review tests.test_core.StrategyWorkflowTests.test_app_state_persists_news_source_settings tests.test_core.StrategyWorkflowTests.test_app_state_persists_strategy_and_license_settings tests.test_core.StrategyWorkflowTests.test_app_state_encrypts_sensitive_broker_credentials tests.test_core.StrategyWorkflowTests.test_save_strategy_preferences_controller_persists_risk_profile tests.test_core.StrategyWorkflowTests.test_switch_strategy_risk_profile_controller_switches_and_saves
```

## 下一步建议

- 如果继续做产品层增强，可以考虑：
  - 按事件来源导出摘要
  - 盘中时间窗内更细的提醒策略
