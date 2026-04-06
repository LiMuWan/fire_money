# 迭代 28 - 打板监控 Workspace Builder 拆分

## 目标
- 将 `打板监控` 的页面构建逻辑从主窗口中抽离，继续收敛 `app_qt.py` 的页面装配职责。
- 保持打板候选、回封监控、导出计划与复盘的业务逻辑不变，只迁移布局和控件初始化。

## 用户价值
- 打板页后续继续增强炸板提醒、回封观察和盘后复盘时，改动会更集中。
- 页面结构更清晰，便于继续放大表格区、压缩说明区和统一样式。

## 本次范围
- 在 [workspace_builders.py](C:\Users\18335\Documents\New%20project\quant_hunter\workspace_builders.py) 中新增 `build_board_workspace(...)`。
- 在 [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 中将 `_build_board_tab()` 改为委托调用。
- 将打板监控页的 hero、操作按钮区、候选池表格、监控表格和说明区统一迁入 builder。

## 实现方案
- `build_board_workspace(window, build_table, header_view_cls)` 负责布局和控件装配。
- 主窗口继续持有 `_refresh_board_mode()`、计划导出、复盘导出等行为逻辑。
- 先拆 UI 层，后续如果继续优化，再评估是否抽出 board binder/controller。

## 验收标准
- `app_qt.py` 与 `workspace_builders.py` 编译通过。
- 入口测试可导入 `build_board_workspace`。
- 全量单元测试继续通过。
- 打板监控页原有按钮、表格与文本区仍可正常初始化。

## 风险
- 打板页虽然比推荐页简单，但依然依赖主窗口中的刷新状态和导出能力，继续拆分时要注意接口边界。
- 仍存在少量历史乱码文案，后续应继续统一清洗为稳定 UTF-8 文本。

## 下一步
- 开始整理首页 / 推荐页 / 打板页的刷新链与联动状态。
- 评估是否把 overview / recommend / board 的刷新逻辑抽成独立 binder。
