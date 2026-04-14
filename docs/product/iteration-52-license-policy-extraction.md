# 迭代 52：授权能力策略抽离

## 本轮目标

- 把授权版本能力规则从主窗口中抽离出来。
- 保持 `TRIAL / PRO / ENTERPRISE` 现有行为不变。
- 在不影响页面功能的前提下，为后续商业化能力限制预留独立 policy 层。

## 本轮改动

- 新增 [license_policy.py](C:/Users/18335/Documents/New%20project/quant_hunter/license_policy.py)
  - 提供 `license_capabilities(plan)` 统一返回授权能力配置。
- 更新 [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py)
  - `_license_capabilities()` 改为委托 `license_capabilities(...)`。
- 更新 [test_core.py](C:/Users/18335/Documents/New%20project/tests/test_core.py)
  - Qt 入口导入测试新增 `quant_hunter.license_policy` 校验。

## 当前收益

- 主窗口少了一段硬编码授权规则。
- 后续增加套餐能力、灰度开关、授权服务接入时，只需要改 policy 层。
- 配置页、推荐页、报告导出页都能共用同一份授权能力定义。

## 风险控制

- 本轮只抽规则，不改 UI 行为。
- 继续保留编译检查、Qt 启动冒烟、全量单测三层验证。
