# 迭代 23 - UI Helper 抽离

## 目标
- 继续缩小 [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 的职责范围。
- 把最基础、复用最高的 UI Helper 从主窗口类中抽离出去。
- 为后续拆分 workspace builder 提前铺好通用 UI 底座。

## 本轮完成

### 1. 新增共享 UI Helper 模块
- 新增 [ui_helpers.py](C:\Users\18335\Documents\New%20project\quant_hunter\ui_helpers.py)

当前已迁出的通用能力：
- `build_workspace_badge()`
- `build_workspace_hero()`
- `set_button_role()`
- `style_terminal_panel()`
- `style_terminal_console()`

### 2. 主窗口改为调用 Helper
- [app_qt.py](C:\Users\18335\Documents\New%20project\app_qt.py) 里的以下方法现在已退化为轻量 wrapper：
  - `_build_workspace_hero()`
  - `_build_workspace_badge()`
  - `_set_button_role()`
  - `_style_terminal_panel()`
  - `_style_terminal_console()`

收益：
- 后续拆分各个 workspace 页面时，不必再把这些基础 UI 工具绑在主窗口类里。
- 如果以后想做统一风格升级，可以优先改 helper 层。

### 3. 测试覆盖扩展
- 更新 [test_core.py](C:\Users\18335\Documents\New%20project\tests\test_core.py)
- 入口导入测试现在会额外校验：
  - `quant_hunter.ui_cards`
  - `quant_hunter.ui_config`
  - `quant_hunter.ui_helpers`

## 当前结构状态
- `ui_cards.py`：卡片组件
- `ui_config.py`：UI 常量 / 映射 / 路由配置
- `ui_helpers.py`：通用 UI 构建与样式 helper
- `app_qt.py`：主窗口编排层

这说明 UI 基础层已经开始从“单文件巨石”过渡到“可扩展模块”。

## 下一步建议
1. 开始把 overview / recommend / broker 的构建函数拆成独立 workspace builder。
2. 把表格联动、跳转聚焦、状态栏联动抽成共享 controller。
3. 继续清理仍然存在的死代码和旧输出分支。

## 验收
- `app_qt.py`、`ui_helpers.py`、`tests/test_core.py` 通过 `py_compile`
- 全量单元测试通过
- 现有按钮样式、Hero 区和终端样式行为不回退
