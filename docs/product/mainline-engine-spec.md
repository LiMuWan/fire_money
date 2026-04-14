# Quant Hunter 主线引擎专项方案

## 1. 目标

把当前项目里的“题材热度 + 龙头识别 + 推荐池联动”升级成真正的主线引擎。

主线引擎要回答 4 个问题：

1. 今天主线是谁。
2. 这条主线还能不能做。
3. 主线里哪些股票最值得做。
4. 主线何时开始分歧、退潮、切换。

这套能力将成为整个产品的第一核心，其他模块都围绕主线服务。

## 2. 当前基础

项目里已经具备主线引擎的基础零件：

- `quant_hunter/theme.py`
  - 已有 `ThemeHeatEngine`
  - 已有 `ThemeHeatRow`
  - 已有 `LeaderCandidate`
  - 已有 `theme_rank`、`theme_score`、`leader_level`

- `quant_hunter/recommend.py`
  - 已有 `infer_theme_name`
  - 已有推荐池构建
  - 已有五大战法打分
  - 已有 `last_theme_rows` 和 `last_leader_rows`

- `quant_hunter/decision.py`
  - 已有 `top_theme_limit`
  - 已有“非主线降权”逻辑
  - 已有市场情绪和仓位控制

结论：

你们不是缺主线能力，而是主线能力还停留在“题材热度排序”阶段，尚未升级成“主线决策引擎”。

## 3. 当前主线模块的主要问题

### 3.1 现在更多是在算“热度”，还没真正算“主线”

目前 `ThemeHeatEngine` 更偏题材聚合排序，但真正的主线不只是热度高，还要具备：

- 市场承载力
- 持续性
- 龙头集中度
- 扩散能力
- 失败成本

### 3.2 主题与个股关系还不够精细

虽然已有 `leader_level`，但目前层次还偏粗。

主线内至少应分为：

- 核心龙头
- 前排换手龙
- 助攻前排
- 中位跟风
- 后排杂毛
- 淘汰风险票

### 3.3 缺“主线退潮”和“主线切换”判断

现在更容易告诉用户“哪个题材靠前”，但不够容易告诉用户：

- 这条主线是不是要弱了
- 是否开始从 A 主线切到 B 主线
- 主线内是强分歧还是彻底退潮

### 3.4 产品表达还没完全主线化

目前推荐、明细、交易页都已有题材字段，但表达方式还没有做到全链路围绕主线展开。

## 4. 主线引擎最终结构

建议把主线引擎拆成 4 层。

### 4.1 主线识别层

目标：识别谁是今天的主线、次主线、观察方向。

输出：

- `mainline_tag`
- `mainline_rank`
- `mainline_strength_score`
- `mainline_continuation_score`
- `mainline_switch_risk`

### 4.2 主线分层层

目标：把主线里的股票按交易价值分层。

输出：

- `mainline_role`
- `mainline_role_score`
- `leader_position_score`
- `follow_quality_score`

建议角色：

- `CORE`
- `FRONT`
- `ASSIST`
- `FOLLOW`
- `NOISE`
- `ELIMINATED`

### 4.3 主线交易层

目标：主线里哪些票可以做，哪些只能看，哪些该放弃。

输出：

- `mainline_action_bias`
- `execution_readiness`
- `mainline_window_score`
- `mainline_risk_flag`

### 4.4 主线风险层

目标：识别主线是否进入分歧、退潮或切换。

输出：

- `theme_failure_risk`
- `theme_divergence_score`
- `theme_rotation_score`
- `mainline_exit_signal`

## 5. 核心分数设计

主线引擎最关键的是下面 6 个分数。

### 5.1 `theme_strength_score`

含义：这条题材今天有多强。

建议来源：

- 题材内高分股数量
- 买入候选占比
- 平均总分
- 平均技术分
- 平均消息分
- 热点扩散数量

### 5.2 `theme_continuation_score`

含义：这条题材是否具备延续能力。

建议来源：

- 平均持续性分
- 过去若干日热度斜率
- 龙头稳定度
- 前排是否持续强于后排

### 5.3 `leader_position_score`

含义：这只股票在主线中的站位有多靠前。

建议来源：

- 在同题材中的综合排名
- 龙头属性
- 技术强度
- 资金关注度
- 新闻催化强度

### 5.4 `theme_divergence_score`

含义：主线当前是否开始分歧。

建议来源：

- 高位股炸板风险
- 前排和后排强弱差扩大
- 题材内部得分离散度升高
- 强势股次日承接下降

### 5.5 `theme_failure_risk`

含义：主线是否接近退潮。

建议来源：

- 题材强度下降速度
- 持续性评分下滑
- 买入候选急剧减少
- 龙头票风险标签增加

### 5.6 `theme_rotation_score`

含义：市场是否正在切换到新方向。

建议来源：

- 新题材热度上升速度
- 老主线热度回落速度
- 推荐池主题集中度变化
- 资金是否从旧方向迁移到新方向

## 6. 个股主线分层设计

每只股票建议新增 4 个主线维度字段。

### 6.1 `mainline_tag`

这只股票属于哪条主线。

### 6.2 `mainline_rank`

该主线在全市场中的排名。

### 6.3 `mainline_role`

该股在主线里的角色。

建议值：

- `CORE`
- `FRONT`
- `ASSIST`
- `FOLLOW`
- `NOISE`
- `ELIMINATED`

### 6.4 `mainline_window_score`

当前是不是适合出手的窗口。

这个分数比单纯推荐动作更重要，因为它直接决定用户是否应该“现在动手”。

## 7. 主线表达如何落到页面

### 7.1 总览页

总览页应该改成“今日主线驾驶舱”。

第一屏最重要的内容应变成：

- 今日第一主线
- 今日第二主线
- 主线可信度
- 主线分歧风险
- 主线窗口状态

建议新增卡片：

- `主线等级`
- `主线窗口`
- `主线风险`
- `主线切换信号`

### 7.2 推荐页

推荐页应围绕主线池做分层。

建议展示四层池子：

- 主线核心池
- 主线前排池
- 主线观察池
- 非主线淘汰池

推荐表格建议新增列：

- 主线
- 主线排名
- 主线角色
- 窗口分
- 主线风险

### 7.3 明细页

明细页最重要的是解释个股和主线的关系。

每只股票固定输出：

- 它是不是主线票
- 它在主线里站什么位置
- 现在是否属于主线出手窗口
- 主线失效时这只票会先怎么坏

### 7.4 交易页

交易前必须增加主线审查。

新增检查项建议：

- 是否主线前 3 题材
- 是否主线前排
- 是否仍处于主线窗口
- 是否存在主线退潮风险

## 8. 数据结构建议

建议优先扩展 `RecommendationRow`，不要新造太多中间对象。

建议新增字段：

- `mainline_tag: str = ""`
- `mainline_rank: int = 0`
- `mainline_role: str = ""`
- `mainline_strength_score: float = 0.0`
- `mainline_continuation_score: float = 0.0`
- `leader_position_score: float = 0.0`
- `mainline_window_score: float = 0.0`
- `theme_divergence_score: float = 0.0`
- `theme_failure_risk: float = 0.0`
- `theme_rotation_score: float = 0.0`
- `mainline_risk_flag: str = ""`

建议新增主线聚合结构：

- `MainlineSnapshot`

建议字段：

- `theme_name`
- `rank`
- `strength_score`
- `continuation_score`
- `divergence_score`
- `failure_risk`
- `rotation_score`
- `window_score`
- `is_primary`

## 9. 代码改造顺序

### 9.1 第一步：升级 `theme.py`

这是主线引擎的核心入口。

需要做的事：

- 把 `ThemeHeatEngine` 升级为主线评分器
- 增加主线强度、持续性、分歧、退潮、切换计算
- 把当前粗粒度 `leader_level` 升级成更细的 `mainline_role`

### 9.2 第二步：升级 `models.py`

需要做的事：

- 扩展 `RecommendationRow`
- 必要时新增 `MainlineSnapshot`

### 9.3 第三步：升级 `recommend.py`

需要做的事：

- 把推荐池排序从“总分优先”升级成“主线优先 + 主线内排序”
- 引入主线窗口和主线风险
- 给每条推荐补齐主线解释

### 9.4 第四步：升级 `decision.py`

需要做的事：

- 市场计划不再只说情绪，还要说主线状态
- 非主线票进一步降权
- 主线退潮时减少新仓数量
- 主线切换时给出“观察等待”而不是强行推荐

### 9.5 第五步：升级工作台展示

重点文件：

- `quant_hunter/workspace_builders.py`
- `quant_hunter/ui_refresh.py`
- `quant_hunter/ui_helpers.py`

需要做的事：

- 总览页主线驾驶舱
- 推荐页主线分层表格
- 明细页主线解释模块
- 交易页主线审查卡片

## 10. 推荐的开发阶段

### P0：先把主线识别做对

范围：

- `theme_strength_score`
- `theme_continuation_score`
- `leader_position_score`
- `mainline_role`

目标：

- 用户先能看清今天主线是谁，哪些票在主线上。

### P1：再把主线交易做强

范围：

- `mainline_window_score`
- `execution_readiness`
- 主线前排池
- 非主线淘汰池

目标：

- 用户知道哪些主线票现在能做，哪些只能看。

### P2：最后把主线风险做深

范围：

- `theme_divergence_score`
- `theme_failure_risk`
- `theme_rotation_score`
- 主线切换提示

目标：

- 用户能更早看到主线退潮和风格切换。

## 11. 推荐的第一批开发任务

如果下一步直接进入代码，建议先做这 5 项：

1. 给 `RecommendationRow` 增加主线相关字段。
2. 在 `theme.py` 里补主线角色和主线窗口评分。
3. 在 `recommend.py` 里改成主线优先排序。
4. 在推荐页表格增加“主线 / 角色 / 窗口 / 风险”列。
5. 在总览页增加“今日主线卡片”。

## 12. 一句话产品判断

主线是这个项目最应该打透的壁垒。

只要主线识别、主线分层、主线窗口、主线退潮这四件事做得比别的产品更稳，你们的产品就不再只是“量化工具”，而会变成真正有竞争力的“主线决策终端”。
