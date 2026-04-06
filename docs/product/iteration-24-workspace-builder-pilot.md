# 迭代 24 - Workspace Builder 试点拆分

## 目标
- 将 `统一登录` 与 `明细复盘` 两个工作区从主窗口中拆出，验证页面 builder 模式可行。
- 降低 `app_qt.py` 的页面构建复杂度，为后续拆分 `首页 / 每日推荐 / 交易执行` 做准备。

## 用户价值
- 页面结构更稳定，后续新增功能时不容易误伤其它工作区。
- 登录页和复盘页的文案、控件、联动逻辑更集中，便于持续优化。

## 本次范围
- 新增 [workspace_builders.py](C:\Users\18335\Documents\New%20project\quant_hunter\workspace_builders.py)。
- 在 [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中将 `_build_auth_tab()`、`_build_detail_tab()` 改为委托调用。
- 清理 builder 中遗留的乱码文案与不完整字符串。

## 实现方案
- `build_auth_workspace(window)` 负责统一登录页的 hero、账户表单、渠道状态区。
- `build_detail_workspace(window, build_table)` 负责明细复盘页的 hero、单票操作区、策略摘要、信号表、交易表。
- 主窗口只保留页面路由与状态编排，不再直接承载这两个页面的控件装配细节。

## 验收标准
- `app_qt.py` 可以成功编译。
- Qt 入口模块导入测试继续通过。
- 全量单元测试继续通过。
- 登录页与复盘页打开后，控件结构和既有交互不回退。

## 风险
- `app_qt.py` 历史上存在乱码文本和旧实现残留，继续拆分时需要优先采用边界明确的页面。
- builder 之间若过早互相依赖，可能把主窗口复杂度转移到模块间耦合，需要控制接口粒度。

## 下一步
- 优先拆分 `交易执行` 或 `首页总览` 的 builder。
- 继续把页面内摘要卡、联动方法和右侧面板抽成更清晰的编排层接口。
