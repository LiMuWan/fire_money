# Quant Hunter

这是一个面向 Windows 的本地桌面应用原型，用来把“反收割”研究流程做成可以持续迭代的产品。

当前桌面层已经迁移到 `PySide6`，不再依赖这台机器上有问题的 `Tkinter/Tcl` 环境。

## 当前能力

- `PySide6` 桌面界面
- 多标的 CSV 股票池扫描
- 观察池管理
- 单标的信号详情和回测面板
- 参数优化与报告导出
- 工作台报告导出
- 东方财富持仓 / 资金 CSV 导入
- 东方财富委托建议 CSV 导出
- GM 实盘脚本生成
- 盘中自动刷新
- 一键下单二次确认
- 下单结果日志
- 本地状态持久化

## 关键文件

- [app_qt.py](C:/Users/18335/Documents/New%20project/app_qt.py): Qt 桌面应用入口
- [app.py](C:/Users/18335/Documents/New%20project/app.py): 旧 Tk 版本入口，当前不再作为默认启动项
- [quant_hunter/strategy.py](C:/Users/18335/Documents/New%20project/quant_hunter/strategy.py): 策略逻辑
- [quant_hunter/scanner.py](C:/Users/18335/Documents/New%20project/quant_hunter/scanner.py): 股票池扫描
- [quant_hunter/backtest.py](C:/Users/18335/Documents/New%20project/quant_hunter/backtest.py): 回测引擎
- [quant_hunter/optimizer.py](C:/Users/18335/Documents/New%20project/quant_hunter/optimizer.py): 参数优化
- [quant_hunter/reports.py](C:/Users/18335/Documents/New%20project/quant_hunter/reports.py): 报表导出
- [quant_hunter/broker.py](C:/Users/18335/Documents/New%20project/quant_hunter/broker.py): 东方财富 / GM 桥接
- [quant_hunter/sdk_bridge.py](C:/Users/18335/Documents/New%20project/quant_hunter/sdk_bridge.py): Python 3.12 GM 子进程桥接脚本
- [build_exe.bat](C:/Users/18335/Documents/New%20project/build_exe.bat): Windows EXE 打包脚本
- [quant_hunter.spec](C:/Users/18335/Documents/New%20project/quant_hunter.spec): PyInstaller 配置

## 本地运行

```powershell
C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe .\app_qt.py
```

也可以直接双击 [run_app.bat](C:/Users/18335/Documents/New%20project/run_app.bat)。

## EXE 打包

当前默认使用本机的 `Python 3.13 + PySide6` 打包桌面程序，并把 `sdk_bridge.py` 一起打进发布目录。

先确认依赖已装好：

```powershell
C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m pip install PySide6 pyinstaller
```

再执行：

```powershell
.\build_exe.bat
```

打包产物位于：

```text
dist\quant_hunter
```

主程序：

```text
dist\quant_hunter\quant_hunter.exe
```

## 东方财富 / GM SDK 说明

当前实现分两层：

1. 半自动层：扫描后生成委托建议 CSV，由你在东方财富终端再次确认。
2. SDK 层：通过 `gm.api` 尝试同步账户和提交订单。

你当前机器上的已知环境是：

- 主界面运行环境：`Python 3.13`
- GM SDK 运行环境：`Python 3.12`
- 已安装 GM 包版本：`gm 3.0.183`

因此当前推荐方式是：

- 桌面界面运行在 `Python 3.13`
- GM 同步 / 下单通过 `Python 3.12 + gm` 子进程桥接执行

在界面里需要至少填写：

- `account_id`
- `token`
- `strategy_id`
- `sdk_module`
- `Bridge Python`

默认桥接解释器会优先指向：

```text
C:\Users\18335\AppData\Local\Programs\Python\Python312\python.exe
```

## 盘中自动刷新与一键下单

当前 Qt 版桌面程序已经支持：

- 设定盘中自动刷新间隔
- 在交易时段自动重扫股票池
- `sdk` 模式下自动同步账户
- 一键下单前弹出二次确认窗口
- 显示账户、策略、桥接 Python 和待提交订单表
- 提交失败时自动导出兜底 CSV
- 在界面中记录每次下单结果

## 测试

```powershell
C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe -m unittest discover -s tests -v
```

## 合规边界

程序化交易属于强监管场景，这个项目默认按“研究、筛选、风控、半自动执行”来设计，不鼓励任何扰乱交易秩序的做法。
