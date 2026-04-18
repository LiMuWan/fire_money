# 夜间持续优化日志

## 说明

这份日志用于记录夜间持续优化期间的实际工作轨迹，重点覆盖：

- 高频刷新性能
- Qt 表格重绘成本
- 状态透明度
- 推荐到交易链路体验
- 商业化终端界面表达

## 2026-04-12 00:00 左右

- 建立夜间持续优化自动任务，并逐步把执行频率提高到分钟级。
- 明确后续优化优先级：先性能，再状态透明度，再终端化表达。

## 2026-04-12 00:10 左右

- 为主界面补充统一的专业终端头部与全局状态 chips。
- 将当前页面、行情通道、自动刷新、运行状态持续暴露在顶部，增强主控台感和状态透明度。
- 扫描链路改为真正后台任务，避免盘中自动刷新阻塞主线程。

## 2026-04-12 00:20 左右

- 为自动刷新加入 in-flight guard。
- 当上一轮市场刷新或扫描仍在执行时，当前轮次会跳过，避免重入和状态抖动。
- 盘中监控摘要改为快照覆盖，避免 QTextEdit 内容越刷越大。

## 2026-04-12 00:30 左右

- 提交记录表改为轻量 item 渲染，不再依赖 cell widget 承载身份块和状态 badge。
- 抽出表格轻量 helper，为后续委托建议表和其它高频表格复用做准备。

## 2026-04-12 00:40 左右

- 为持仓表补充批量更新包裹，减少全表重绘时的闪动和无效刷新。
- 为自动刷新跳过场景补充更明确的状态文案，避免用户误以为系统停工。

## 2026-04-12 01:00 左右

- 为委托建议表补充批量更新包裹，先降低高频刷新时的整表重绘抖动。
- 当前经纪模块三张表里，提交记录表已轻量化，持仓表与委托建议表已进入批量更新模式。
- 下一步继续处理推荐池和市场池两张更重的表，并考虑进一步减少委托建议表中的 cell widget 数量。

## 2026-04-12 01:10 左右

- 为推荐池和市场池补充批量更新包裹，减少高频筛选和刷新时的闪动与无效重绘。
- 市场池的行内符号数据同步收口到轻量 role 写入，后续继续为去 widget 化做准备。
- 下一步继续选择一张高频表做更进一步的轻量渲染，优先仍然看委托建议表和市场池。

## 2026-04-12 01:20 左右

- 推荐池动作列从 badge widget 改为轻量 item 渲染，减少一列 cell widget 重建。
- 市场池的资金标签列、策略/题材/信号列改为紧凑 item 渲染，减少两列 cell widget 重建。
- 下一步继续评估是否把市场池身份列或推荐池题材列进一步轻量化，同时保持当前终端观感不明显退化。

## 2026-04-12 01:30 左右

- 推荐池的主线/角色列改为紧凑 item 渲染，再减少一列 cell widget 重建。
- 当前策略保持为：优先移除展示增强列的 widget，最后再处理信息主干的身份列。
- 下一步优先评估市场池身份列是否能在不明显损伤可读性的前提下轻量化。

## 2026-04-12 01:40 左右

- 市场池身份列从 stock identity widget 改为轻量 item 渲染，补齐 tooltip 与 UserRole，进一步减少高频筛选时的重建成本。
- 当前市场池已基本去除主要展示列上的 cell widget，只剩更少量的重型渲染点。
- 下一步继续看推荐池身份列是否值得按同样方式处理，并同步补强状态透明度与主控台体验。

## 2026-04-12 01:50 左右

- 推荐池身份列从 stock identity widget 改为轻量 item 渲染，保留执行状态、symbol、热度等关键信息。
- 当前推荐池与市场池都已经完成主要展示列的轻量化，后续可把重点切回状态透明度与主控台体验。
- 下一步优先补一轮“系统正在工作/后台正在推进”的显性表达，降低用户对线程停工的感知风险。

## 当前状态

- 已完成多轮性能与状态可见性优化。
- 当前下一步重点：继续处理委托建议表刷新，再推进推荐池和市场池两张更重的表。

## 2026-04-12 02:10 左右

- 在主界面头部新增常驻“系统脉搏条”，把后台任务状态、推荐到交易链路进度、风险灯和最近时间戳集中展示。
- 当行情刷新、扫描任务、推荐池、交易计划、待审委托在不同阶段切换时，顶部会给出不同的显性文案，减少“界面看起来像没在工作”的感知。
- 下一步继续强化交易执行页的可见状态，把“推荐 -> 计划 -> 委托 -> 提交”链路压缩成更直接的中控表达。

## 2026-04-12 02:20 左右

- 给自动刷新链路上的高频状态标签增加“文本相同则跳过 setText”短路，减少顶部状态条、刷新时间和跳过提示的重复重绘。
- 这一步优先覆盖最容易高频触发的总览自动刷新和扫描自动刷新状态文案，属于低风险的流畅度优化。
- 下一步继续处理交易执行区，把待审委托和阻塞项表达得更像真正的中控终端。

## 2026-04-12 02:30 左右

- 重写交易执行页顶部状态横幅，用“风险灯 + 待审/已提交 + 下一步动作”的格式表达交易链路，而不是只显示数量。
- 同步把几处空状态标签接入文本去重 helper，减少重复写入，也让交易页的状态更新节奏更稳。
- 下一步继续看委托表本身，优先处理剩余较重的渲染点或重复刷新链路。

## 2026-04-12 02:45 左右

- 委托建议表继续轻量化：身份列和动作列不再逐行创建 widget，改为更轻的 item 渲染，降低表格重建成本。
- 同时给委托表补了选中保持逻辑，刷新后会优先回到用户刚才查看的那只票，减少焦点跳回默认行的割裂感。
- 本轮变更后继续通过 Qt 烟雾测试和全量 86 项单元测试，当前可以继续向其它高频表格和重复刷新链路推进。

## 2026-04-12 03:00 左右

- 应用层旧版 `_fill_holdings` 和 `_fill_orders` 已切换到统一的优化刷新实现，避免新旧两套 broker 表格渲染路径并存。
- 这样持仓表和委托表都会走同一套轻量化、批量化、带状态联动的刷新链路，后续继续做性能和焦点优化时不会出现“只优化了一半”的问题。
- 本轮再次完成编译校验、Qt 烟雾测试和全量 86 项测试，当前基线稳定。

## 2026-04-12 03:15 左右

- 给扫描表、回测汇总表、盘中监控表补了按 symbol 保留选中项的逻辑，刷新后不再默认跳回首行。
- 给执行记录表补了按时间戳保留焦点的逻辑，用户在复盘某条提交回执时，新结果写入不会立刻打断当前阅读。
- 本轮变更后继续通过编译校验、Qt 烟雾测试和全量 86 项测试，当前可以继续向市场池和总览联动链路推进。

## 2026-04-12 03:25 左右

- 给总览市场池补了按 symbol 保留选中项的逻辑，筛选和刷新后优先回到当前关注票，而不是一律跳回第一行。
- 这一步进一步改善了总览右侧联动的稳定感，减少用户在盯某只票时被刷新打断的体感。
- 本轮变更后继续通过编译校验、Qt 烟雾测试和全量 86 项测试，当前基线保持稳定。

## 2026-04-12 03:35 左右

- 给明细区信号表、交易记录表以及打板候选/打板监控两张表补了焦点保持逻辑，重算或刷新后优先回到用户刚才查看的记录。
- 这样切换标的、运行回测、刷新打板模式时，面板不会频繁把用户拉回首行，整体更像可持续盯盘的工作台。
- 本轮变更后继续通过编译校验、Qt 烟雾测试和全量 86 项测试，当前可以继续转向重复状态刷新和右侧文本区去重。

## 2026-04-12 03:50 左右

- 把“内容未变化则不重写”的策略扩到总览右侧和 broker 中控的高频文本面板，包括主题摘要、新闻广度、数据源状态、交易回放、风控摘要、执行摘要等区域。
- 这样在自动刷新命中但内容实际没变时，界面会减少无效文本重绘，滚动和盯盘体感更稳。
- 本轮变更后继续通过编译校验、Qt 烟雾测试和全量 86 项测试，当前可以继续清理推荐区与扫描区剩余高频标签。

## 2026-04-12 04:05 左右

- 把“内容未变化则不重写”的策略继续铺到推荐区和扫描区核心路径，包括扫描焦点状态、扫描摘要卡、推荐分发摘要、单票审查、待审队列、主线前排/观察/风险三块内容。
- 同时把“正在生成推荐池”“扫描后台刷新中”“扫描自动跳过”“总览正在筛选候选”等入口状态也切到去重写入，进一步降低高频自动刷新时的无效 UI 更新。
- 本轮变更后继续通过编译校验、Qt 烟雾测试和全量 86 项测试，当前基线稳定。

## 2026-04-12 04:15 左右

- 继续把去重写入扩到总览仪表卡、市场详情头部和扫描联动摘要，让切换标的和自动刷新时的顶部/侧边标签减少无效重绘。
- 现在候选数、买入数、平均热度、主线主题这类总览指标，以及市场标题、副标题、行情摘要、监控摘要都会在内容变化时才更新。
- 本轮变更后继续通过编译校验、Qt 烟雾测试和全量 86 项测试，当前可以继续转入更偏商业化表达和细节 polish 的优化。

## 2026-04-12 04:25 左右

- 补强了 `statusBanner`、`workspaceToolPanel`、`focusStateLabel`、`emptyStateMeta`、`emptyActionBar` 的视觉样式，把状态横幅、工具面板和空状态做出更清晰的商业化层级。
- 同时把关键状态横幅打开自动换行，长文案和窄窗口下的可读性更稳，避免信息被截断后显得像内部调试界面。
- 本轮变更后继续通过编译校验、Qt 烟雾测试和全量 86 项测试，当前基线稳定。
## 2026-04-12 08:20 宸﹀彸

- 閲嶅缓 `quant_hunter/ui_cards.py` 锛屼慨澶嶅崱鐗囧眰鏈畬鎴愯ˉ涓佸甫鏉ョ殑鍙橀噺鏈畾涔夈€佸瓧绗︿覆鎴柇鍜岀紪璇戞晠闅滐紝鍚屾椂瀹屾垚鍗￠潰绾у晢涓氬寲 polish銆?
- `InsightCardBase` 鏀逛负鏇存湁缁堢鎰熺殑娓愬彉鑳屾櫙 + 閫忔槑鏂囨湰灞傦紝骞朵负 `ActionFlowCard`銆乢ompactSummaryCard`銆乤lertSignalCard` 鍜?`StrategyWorkbenchCard` 琛ュ叆 accent strip锛屾彁鍗囦富鎺у彴鐨勫晢涓氬寲灞傜骇銆?
- `AlertSignalCard` 鍜?`CompactSummaryCard` 琛ュ己鎹㈣涓庣┖鐘舵€佽〃杈撅紝璁╅暱鏂囨鍜岀姸鎬佹枃瀛楀湪灏忓崱鐗囬噷鏇村彲璇汇€?
- 缁欑洏涓洃鎺ц〃鍔犱笂鈥滃揩鐓х鍚嶁€濓細褰撳叧娉ㄨ偂绁ㄥ垪琛ㄣ€佸姩浣滀俊鍙枫€佸垎鏁板拰琛岄鏈彉鏃讹紝鐩存帴璺宠繃 `monitor_table` 鏁磋〃閲嶇粯锛屽噺灏戦珮棰戠洏涓埛鏂版椂鐨勯棯鍔ㄥ拰鏃犳晥 item 閲嶅缓銆?
- 缁欐寔浠撹〃鍔犱笂鍚屾牱鐨勫揩鐓х鍚嶈烦杩囬€昏緫锛屾寔浠撳唴瀹规病鏈夊彉鍖栨椂涓嶅啀鍙嶅閲嶅缓琛ㄦ牸锛屼絾浠嶄繚鎸?broker 鍖轰腑鎺х姸鎬佹甯稿悓姝ャ€?
- 鏈疆鍙樻洿鍚庡凡缁忛€氳繃缂栬瘧鏍￠獙銆丵t 鐑熼浘娴嬭瘯鍜屽叏閲?86 椤瑰崟鍏冩祴璇曪紝褰撳墠鍩虹嚎淇濇寔绋冲畾銆?
## 2026-04-12 08:34 宸﹀彸

- 缁欐帹鑽愬伐浣滃彴鐨?`theme_heat_table` 鍜?`leader_table` 琛ュ叆鎵归噺鏇存柊鍖呰９锛岄伩鍏嶆瘡杞暣琛?setItem 閲嶇粯鏃剁殑闂姩銆?
- 涓轰富绾跨儹搴﹁〃鎸?`theme_name`銆侀緳澶磋〃鎸?`stock_id` 淇濈暀閫変腑椤癸紝鎺ㄨ崘姹犻噸绠楀悗浼樺厛鍥炲埌鐢ㄦ埛鍒氭墠鍏虫敞鐨勪富绾挎垨鏍囩殑锛屽噺灏戦潰鏉块噸缁樺悗鐨勭劍鐐逛涪澶便€?
- 缁欎笂杩颁袱寮犺〃鍔犱笂鍐呭蹇収绛惧悕锛屽綋涓婚鐑害鏁版嵁鎴栭緳澶存帓鍚嶆病鏈夊彉鍖栨椂锛岀洿鎺ヨ烦杩囨暣琛ㄩ噸缁橈紝缁х画淇濇寔鎺ㄨ崘閾捐矾鐨勬祦鐣呭害銆?
- `strategy_detail_text` 鏀逛负鈥滄枃鏈唴瀹规湭鍙樺寲鍒欎笉閲嶅啓鈥濓紝褰撳墠鐒︾偣鍜屾垬娉?Top 3 娌℃湁鍙樺寲鏃讹紝涓嶅啀鍙嶅 `setPlainText`锛岄檷浣庢帹鑽愮劍鐐硅鎯呴潰鏉跨殑鏃犳晥閲嶆帓銆?
- 鏈疆鍙樻洿鍚庡凡缁忛€氳繃缂栬瘧鏍￠獙銆丵t 鐑熼浘娴嬭瘯鍜屽叏閲?86 椤瑰崟鍏冩祴璇曪紝褰撳墠鍩虹嚎缁х画淇濇寔绋冲畾銆?

## 2026-04-12 08:40 宸﹀彸

- 缁欎氦鏄撲腑鎺у尯鐨?focus button 鎸夐挳鐘舵€侀€昏緫琛ュ叆 helper锛岀幇鍦?`setEnabled` 鍜?`setToolTip` 涔熶細鍍忔枃鏈浛鎹㈤偅鏍凤紝鍦ㄧ姸鎬佹病鏈夊彉鍖栨椂鐩存帴璺宠繃銆?
- 杩欏逛氦鏄撻摼璺壒鍒湁鐢細褰撳墠 broker 椋庢帶銆侀樆濉炪€侀珮浼樺厛绁ㄧ殑鍒ゆ柇娌℃湁鍙樺寲鏃讹紝涓嶅啀姣忚疆閮芥妸鈥滄煡鐪嬮樆濉?鍜?鈥滃畾浣嶄紭鍏堢鈥濈殑鎸夐挳鐘舵€佸拰鎻愮ず閲嶅啓涓€閬嶃€?
- 鏈疆鍙樻洿鍚庡啀娆￠€氳繃缂栬瘧鏍￠獙銆丵t 鐑熼浘娴嬭瘯鍜屽叏閲?86 椤瑰崟鍏冩祴璇曪紝褰撳墠鍩虹嚎缁х画淇濇寔绋冲畾銆?

## 2026-04-12 22:45 宸﹀彸

- 瀹為檯杩愯 `app_qt.py` 鍋氫簡鐪熸満鍚姩楠岃瘉锛屼富绐楀彛鑳芥甯歌捣鏉ワ紝涓斿凡鐪嬪埌杩愯涓殑绐楀彛鏍囬鈥?閲忓寲鐚庢墜 Pro v2.2鈥濓紝璇存槑褰撳墠涓嶆槸鍙祴璇曡兘杩囷紝鑰屾槸鐪熺殑鑳藉惎鍔ㄣ€?
- 鍚姩楠岃瘉鍚庯紝椤轰究鎶婅瘯璺戞椂鐣欎笅鐨勭嫭绔?Python 杩涚▼鍥炴敹浜嗭紝閬垮厤褰卞搷鍚庣画鍒锋柊銆佹祴璇曞拰鑷富浼樺寲鑺傚銆?
- 缁欐帹鑽愬伐浣滃彴鐨勯緳澶存鍗?`LeaderboardCard` 琛ュ叆鈥滃崱鐗囩鍚嶁€濓紝褰撶一浜屼笁寮犳鍗曞唴瀹规病鏈夊彉鍖栨椂锛屼笉鍐嶅弽澶?`set_row` 閲嶇粯銆?
- 缁欐垬娉曟鍗?`StrategyWorkbenchCard` 琛ュ叆鈥滄憳瑕佺鍚嶁€濓紝褰撳ご鍙峰€欓€夈€佽瘎鍒嗐€乀op 3 鍜岄€昏緫鎽樿閮芥病鍙樺寲鏃讹紝涓嶅啀姣忚疆閮介噸鍐?`set_strategy_summary`锛屾帹鑽愬伐浣滃彴浼氭洿绋炽€?
- 鍚屾椂缁欏競鍦烘繁搴﹀尯鐨勪拱鐐广€佸崠鐐广€佹秷鎭潰涓夊潡鏂囨湰鎺ュ叆鈥滃唴瀹规湭鍙樺寲鍒欎笉閲嶅啓鈥濓紝杩涗竴姝ラ檷浣庤嚜鍔ㄥ埛鏂版椂鐨勫彸渚ц鎯呴棯鍔ㄣ€?
- 鏈疆鍙樻洿鍚庡凡缁忛€氳繃缂栬瘧鏍￠獙銆丵t 鐑熼浘娴嬭瘯鍜屽叏閲?87 椤瑰崟鍏冩祴璇曪紝褰撳墠鍩虹嚎缁х画淇濇寔绋冲畾銆?

## 2026-04-12 22:55 宸﹀彸

- 鎶婂崱鐗囩粍浠剁殑鍐欏叆鍏ュ彛鏈韩鍋氭垚幂瓑绛夋洿鏂帮細`ActionFlowCard`銆乢ompactSummaryCard`銆乤lertSignalCard` 浠ュ強 `StrategyWorkbenchCard` 鐜板湪閮戒細鍦ㄦ枃鏈湡姝ｅ彉鍖栨椂鎵嶆墽琛?`setText`銆?
- 杩欐牱鏀剁泭涓嶆槸鍗曠偣鐨勶紝鑰屾槸鏁翠釜鎺ㄨ崘銆佹€昏銆佺洏涓彁閱掋€佷腑鎺ф憳瑕佺瓑澶氬鍏卞悓鍙楃泭锛屽彲浠ュ噺灏戞秷鎭崱鐗囧拰鎽樿鍗＄殑鏃犳晥閲嶆帓銆?
- `refresh_recommend_bucket_panels()` 鍚屾椂鎺ュ叆鈥滃唴瀹规湭鍙樺寲鍒欎笉閲嶅啓鈥濓紝褰撴牳蹇冩墽琛屻€佽瀵熻窡韪拰椋庨櫓鍥為伩涓夊潡姒傝娌℃湁鍙樺寲鏃讹紝涓嶅啀鍙嶅鍒锋柊涓夊潡 QTextEdit銆?
- 鏈疆鍙樻洿鍚庡啀娆￠€氳繃缂栬瘧鏍￠獙銆丵t 鐑熼浘娴嬭瘯鍜屽叏閲?87 椤瑰崟鍏冩祴璇曪紝褰撳墠鍩虹嚎缁х画淇濇寔绋冲畾銆?

## 2026-04-12 23:05 宸﹀彸

- 缁欐帹鑽愬鐩樺拰鍒嗗彂閾捐矾鍐嶆敹涓€杞?direct text write锛?`recommend_review_text`銆乺ecommend_next_day_text`銆乺ecommend_dispatch_text`銆乺ecommend_focus_review_text` 浠ュ強 `recommend_queue_text` 鐜板湪閮芥敼涓衡€滃唴瀹规湭鍙樺寲鍒欎笉閲嶅啓鈥濄€?
- 杩欐牱鍦ㄦ帹鑽愭睜娌℃湁瀹炶川鍙樺寲浣嗙郴缁熶粛鍦ㄨ疆璇㈠埛鏂扮殑鏃跺€欙紝澶嶇洏銆佹鏃ラ妗堛€侀€佸/鎻愪氦鍒嗗彂鎽樿涓嶅啀鍙嶅闂姩锛屾暣浣撴洿鍍忕ǔ瀹氱殑涓帶缁堢銆?
- 鏈疆鍙樻洿鍚庡凡缁忓啀娆￠€氳繃缂栬瘧鏍￠獙銆丵t 鐑熼浘娴嬭瘯鍜屽叏閲?87 椤瑰崟鍏冩祴璇曪紝褰撳墠鍩虹嚎缁х画淇濇寔绋冲畾銆?

## 2026-04-12 23:12 宸﹀彸

- 涓绘帹婕旇矾寰?`strategy_path_text` 鏈€鍚庝篃鎺ュ叆鈥滃唴瀹规湭鍙樺寲鍒欎笉閲嶅啓鈥濓紝鐜板湪鎺ㄨ崘宸ヤ綔鍙颁富瑕佹枃鏈憳瑕佸尯宸茬粡鍩烘湰鍋氬埌缁熶竴鍘婚噸鍒锋柊銆?
- 鍚屾椂鍐嶆鐢?`rg` 妫€鏌?`quant_hunter/ui_refresh.py`锛屽綋鍓?`setPlainText` 鍙墿 helper 鑷韩锛屼笉鍐嶆湁涓氬姟鍒锋柊鍑芥暟鐩存帴纭啓 QTextEdit锛岃繖瑙嗕负杩欎竴杞?UI 鏂囨湰鍘婚噸鏀堕棬銆?
- 鏈疆鍙樻洿鍚庡凡缁忓啀娆￠€氳繃缂栬瘧鏍￠獙銆丵t 鐑熼浘娴嬭瘯鍜屽叏閲?87 椤瑰崟鍏冩祴璇曪紝褰撳墠鍩虹嚎缁х画淇濇寔绋冲畾銆?

## 2026-04-12 23:30 Commercial Card Polish
- `quant_hunter/ui_cards.py` 为 `LeaderboardCard` 增加显式状态位和 `Why now` 理由文案，让龙头卡更像商业终端里的精选机会卡。
- `InsightCardBase` 新增样式幂等写入，减少高频刷新时重复 `setStyleSheet` 带来的卡片抖动。
- `LeaderboardCard` 新增 `status_label`、`reason_label`，并将部分文本更新切到按需写入，进一步降低无效重绘。
- 验证通过：`py_compile app_qt.py quant_hunter/ui_refresh.py quant_hunter/ui_cards.py`、Qt smoke、全量 `87` 项 unittest。

## 2026-04-12 23:45 Refresh Signature Pass
- `quant_hunter/ui_refresh.py` 为 `daily_pool_table` 增加签名短路与选中态保持；当推荐池内容未变化时，跳过整表重建。
- `quant_hunter/ui_refresh.py` 为 `orders_table` 增加签名短路；当委托建议内容未变化时，直接保留当前焦点并刷新状态链路，减少 broker 工作区抖动。
- `quant_hunter/ui_refresh.py` 为 `execution_table` 增加签名短路与选中态保持；提交流水未变化时不再重复 `setRowCount + setItem`。
- 验证通过：`py_compile app_qt.py quant_hunter/ui_refresh.py quant_hunter/ui_cards.py`、Qt smoke、全量 `87` 项 unittest。

## 2026-04-13 00:05 Market Pool And Status Dedupe
- `quant_hunter/ui_refresh.py` 为 `market_pool_table` 增加签名短路；筛选条件和行内容未变化时，跳过整表重建，仅保留选择态并刷新侧边摘要。
- `app_qt.py` 将顶部 `shell pulse` 的 hint/meta，以及四组 live summary 面板切到 `_set_label_text_if_changed`，减少无变化文本反复写入造成的闪烁感。
- 这一批改动优先提升“正在持续工作”的观感，让总览层和顶部状态层更稳、更像商业终端。
- 验证通过：`py_compile app_qt.py quant_hunter/ui_refresh.py quant_hunter/ui_cards.py`、Qt smoke、全量 `87` 项 unittest。

## 2026-04-13 00:18 Shell Status Bus Upgrade
- `app_qt.py` 顶部 `shell header` 继续升级，把状态表达从简单计数提升到链路阶段表达：`市场同步`、`推荐生成`、`计划就绪`、`委托待审`、`风控阻塞`。
- `shell_pulse_hint` 现在直接给出当前最重要的下一步动作，不再只是静态指标拼接，更接近商业终端里的运行指挥条。
- `shell_pulse_meta` 统一显示阶段、风险灯、已提交数、市场时间戳和任务时间戳，增强“系统正在持续推进”的透明度。
- 验证通过：`py_compile app_qt.py quant_hunter/ui_refresh.py quant_hunter/ui_cards.py`、Qt smoke、全量 `87` 项 unittest。

## 2026-04-13 00:30 Product Copy Unification
- `app_qt.py` 统一了推荐页与交易页的一批高频状态文案，把默认表达从“功能提示”升级成更像商业终端的“状态结论 + 下一步动作”。
- 推荐空态升级为“机会池等待生成”，并补充了“综合机会池与执行优先级”的结果导向表述。
- 交易 banner 统一为 `红灯阻塞 / 黄灯复核 / 绿灯待审` 的阶段语言，让风险状态和推进动作更直观。
- 默认按钮文案进一步统一为 `载入样例数据`、`生成委托链路`、`确认并提交委托`，强化完整链路感。
- 验证通过：`py_compile app_qt.py quant_hunter/ui_refresh.py quant_hunter/ui_cards.py`、Qt smoke、全量 `87` 项 unittest。

## 2026-04-13 00:42 Focus Copy Tightening
- `app_qt.py` 进一步统一了推荐焦点、计划焦点、委托焦点和推荐故事面板的默认文案，减少“等待刷新”式弱表达，改成更结果导向的状态语言。
- 推荐故事默认面板升级为 `等待机会池生成 / 等待主线确认`，并明确下一步动作：先刷新市场，再生成机会池与主线判断。
- 推荐与交易页默认焦点文案收紧为 `推荐焦点：高优先 / 观察 / 风险 / 执行链路`、`计划焦点：等待交易计划生成`、`委托焦点：等待委托链路生成`。
- 验证通过：`py_compile app_qt.py quant_hunter/ui_refresh.py quant_hunter/ui_cards.py`、Qt smoke、全量 `87` 项 unittest。

## 2026-04-13 00:55 Card Summary Compression
- `app_qt.py` 继续压缩了总览卡片、推荐摘要卡片、优先级卡片与提醒卡片的文案，把更多空间留给结论、风险和动作，而不是解释性表述。
- 总览卡片现在更接近交易摘要：`催化/风险`、`窗口/总分`、`下一步` 等表达更短更直接。
- 推荐摘要与优先级卡片统一压缩了催化、风险和执行提示长度，让卡片在高密度界面里更像专业终端的决策摘要块。
- 验证通过：`py_compile app_qt.py quant_hunter/ui_refresh.py quant_hunter/ui_cards.py`、Qt smoke、全量 `87` 项 unittest。

## 2026-04-13 16:32 Action And Alert Chain Polish
- `app_qt.py` 继续收紧推荐页动作卡文案，把 `BUY / WATCH / REDUCE / SELL` 统一成更像交易台动作摘要的短句，强化从推荐到送审、减仓、止盈止损的推进感。
- `alert_cards` 同步压缩为更标准的终端表达：主线卡改成 `主线 | 信号`，策略卡改成 `动作 | 催化`，动作卡改成 `下一步 ...`，让链路判断更直接。
- 这一轮保持低风险小补丁，只调整 copy，不动刷新架构，继续沿用前面已经验证稳定的幂等更新策略。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 16:40 Shell Status Transparency Pass
- `app_qt.py` 继续增强顶部状态总线，把 `推荐 / 计划 / 待审 / 已提交 / 当前任务 / 最近完成时间` 聚合到同一条 meta 信息里，强化“系统正在持续推进”的可见性。
- 这一步不改业务逻辑，只补强状态透明度，方便用户快速判断当前链路卡在市场同步、推荐生成、计划就绪还是委托待审。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 17:05 Terminal Language And Refresh Stability Pass
- `app_qt.py` 把顶部 `shell_pulse_hint`、交易台 banner、计划焦点、委托焦点继续压成更像交易席位的短句，强化“下一动作 / 待送审 / 等回执 / 阻塞中”的链路语义。
- `app_qt.py` 将详情页三块长文本面板切到 `_set_plain_text_if_changed`，减少跨页面联动和焦点切换时的长文本重复重写。
- `quant_hunter/ui_refresh.py` 为 `scan_table`、`summary_table`、`watchlist_widget` 增加轻量签名短路和选中态保持，降低整表重建与观察池闪动。
- `quant_hunter/ui_cards.py` 将 `LeaderboardCard` 的状态和原因文案切成中文终端表达，减少中英文混搭带来的成品感割裂。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 17:18 Board Focus Render Cost Pass
- `app_qt.py` 将打板焦点面板 `board_text / board_monitor_text` 切到 `_set_plain_text_if_changed`，减少扫描页、推荐页、打板页联动时的长文本重复重写。
- 这一轮继续优先做低风险去抖动处理，不改业务判断，只减少无变化内容带来的重绘和闪动。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 17:28 Overview Status Dedupe Pass
- `app_qt.py` 将总览页 `market_status_label` 的一组高频状态更新切到 `_set_label_text_if_changed`，覆盖页面切换、快捷视图切换、总览聚焦、历史窗口切换和视窗偏移等场景。
- 同步把收盘复盘自动导出后的 `last_refresh_label` 更新切到幂等写入，进一步减少“状态没变但仍重复刷新”的闪动感。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 17:36 Scanner Default State Dedupe
- `app_qt.py` 将扫描页默认状态初始化里的 `scan_summary_label / last_refresh_label / universe_label / monitor_summary_text` 切到按需写入，减少切页和初始化时的重复写入。
- 总览页 `overview_command_text` 的“当前视图”提示，以及一组总览状态追加逻辑，也统一走幂等更新，继续压低界面闪动。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 17:44 Trade Plan Text Dedupe
- `app_qt.py` 将交易计划页的 `trade_plan_text / market_pulse_text / position_advice_text` 切到 `_set_plain_text_if_changed`，降低计划刷新、持仓建议更新时的长文本重写成本。
- 这一轮继续只做低风险去抖动处理，不改决策逻辑，只减少刷新时的无效写入和视觉闪动。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 17:52 Status Tail Cleanup
- `app_qt.py` 继续清理残留的高频直接写入点：策略过滤后的 `market_status_label`、盘中监控摘要初始文案、总览默认状态文案都统一切到按需写入。
- 这一轮属于尾部去抖动清扫，目的是继续降低切页、切过滤条件和初始化阶段的重复刷新感。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 18:00 Overview Command Dedupe
- `app_qt.py` 将总览命令区 `overview_command_text` 的动态刷新与空态初始化统一切到 `_set_plain_text_if_changed`，减少总览焦点切换时的大段文本重写。
- 扫描页默认监控摘要和扫描状态默认文案也同步切到幂等更新，继续收紧初始化与切页阶段的无效刷新。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 18:08 Overview Insight Text Dedupe
- `app_qt.py` 将总览页 `overview_execution_text / market_capital_text / market_decision_text` 切到 `_set_plain_text_if_changed`，减少总览焦点变更和市场快照更新时的长文本重写。
- 同步补上扫描监控默认摘要的一处残留旧写法，继续统一到幂等更新路径。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 18:16 Empty State Tail Cleanup
- `app_qt.py` 将总览页 `market_leaderboard_text` 的空态初始化切到 `_set_plain_text_if_changed`，减少首页初始加载时的榜单摘要重写。
- 同步清理扫描页更早一版 `_normalize_scanner_workspace_texts()` 里的 `scan_summary_label / last_refresh_label / monitor_summary_text` 直接写入，继续统一幂等更新路径。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 18:24 Home Empty Insight Consistency
- `app_qt.py` 将首页剩余几块空态摘要 `market_theme_brief_text / market_source_status_text / daily_pool_text` 统一切到 `_set_plain_text_if_changed`，让首页洞察区在初始化和切页时保持一致的幂等更新行为。
- 这一轮继续只收首页空态尾巴，不改业务逻辑，只减少无变化时的大段文本重写。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 18:34 Plan Table Signature Pass
- `app_qt.py` 为 `trade_plan_table` 和 `position_advice_table` 增加轻量签名短路；当计划决策行和持仓建议行内容未变化时，直接跳过整表 `setRowCount + setItem` 重建。
- 这一步继续沿用前面高频表优化策略，把交易计划链路里的表格刷新也纳入稳定路径，减少联动刷新时的布局抖动。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 18:42 Detail Table Signature Pass
- `app_qt.py` 为 `signal_table` 和 `trades_table` 增加轻量签名短路；当信号记录和回测成交记录内容未变化时，跳过整表重建，只保留当前选中行恢复。
- 这一轮继续沿着“明细联动去抖动”推进，减少选股、回测、复盘切换时的表格刷新成本。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 18:50 Backtest And Home Empty Dedupe
- `app_qt.py` 将回测结果摘要 `metrics_text` 切到 `_set_plain_text_if_changed`，减少重复回测或同标的回放时的长文本重写。
- 同步把首页空态的 `market_buy_text / market_sell_text / market_breadth_text` 统一到幂等更新路径，让首页洞察卡在初始化时保持一致的稳定刷新行为。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 18:58 Auth And Config Text Dedupe
- `app_qt.py` 将登录说明 `login_status_text`、授权状态 `license_status_text`、配置说明 `config_notes_text` 统一切到 `_set_plain_text_if_changed`，减少配置页、登录页切换和参数变更时的长文本重写。
- 同步补上登录状态更新 helper 路径的一处残留直接写入，继续把说明类长文本收敛到同一套幂等更新模式。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 19:06 Recommend Story Dedupe
- `app_qt.py` 将推荐页 `daily_pool_text / strategy_path_text` 的空态与动态刷新统一切到 `_set_plain_text_if_changed`，减少推荐页选中联动与机会池刷新时的大段文本重写。
- 这一轮继续收推荐页的说明型长文本，让推荐、总览、交易三条链路的文本刷新行为更一致。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 19:14 Recommend Panel Defaults Dedupe
- `app_qt.py` 将推荐页默认说明面板 `recommend_dispatch_text / recommend_focus_review_text / recommend_queue_text / strategy_path_text` 统一切到 `_set_plain_text_if_changed`。
- 这一步把推荐页“空态说明 / 默认说明 / 动态说明”三种文本刷新路径进一步收敛到同一套幂等更新模式，减少切页和初始化时的整段重写。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 19:22 Legacy Path Cleanup
- `app_qt.py` 将推荐故事面板较早一版刷新路径里的 `daily_pool_text / strategy_path_text` 也切到 `_set_plain_text_if_changed`，避免历史重复定义里残留直接写入。
- 同步把登录、授权、配置说明在“乱码修复/兜底初始化”分支里的残留 `setPlainText` 统一到幂等更新，进一步收敛旧路径。
- 待验证：`py_compile`、Qt smoke、全量 unittest。

## 2026-04-13 19:30 Empty Workspace Text Unification
- `app_qt.py` 将空工作区注水逻辑里的 `trade_plan_text / position_advice_text / board_text / board_monitor_text / metrics_text` 统一切到 `_set_plain_text_if_changed`。
- 这一步让空态与动态态的长文本刷新行为进一步一致，减少首次加载、切页和空面板回填时的整段重写。
- 待验证：`py_compile`、Qt smoke、全量 unittest。
## 2026-04-13 19:38 Broker Replay Dedupe Pass
- `app_qt.py` 将最后生效的 `_qh_refresh_submission_focus()` 里 `order_result_text / broker_recap_text` 的预演态、空态和真实提交回放统一切到 `_set_plain_text_if_changed`，减少委托选择变化和提交记录切换时的长文本重复写入。
- `app_qt.py` 同步把 `_qh_refresh_broker_auxiliary_panels()` 里的 `broker_mainline_review_text / broker_execution_text` 切到按需写入，让主线审查与执行链路面板在高频联动下保持更稳的刷新节奏。
- 这轮继续只做低风险刷新层优化，不改交易判断逻辑，优先提升“持续在工作”的稳定观感和券商工作台的响应质感。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 19:46 Broker Metrics And Board Focus Dedupe
- `app_qt.py` 将 `_qh_refresh_broker_status()` 里的 `broker_status_text` 以及四组 `broker_metric_labels / broker_metric_accents` 统一切到按需写入，减少账户状态、预算和准备度反复刷新时的无效重绘。
- `app_qt.py` 同步把 `_qh_refresh_board_focus_cards()` 里的打板焦点指标标签统一改成 `_set_label_text_if_changed`，降低扫描联动、候选切换和盘中监控回写时的标签抖动。
- 这一轮仍然只动显示层，不动风控或交易逻辑，继续沿着“高频刷新性能 + 状态透明度”的优先级推进。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 19:54 Detail Review And Recommend Defaults Dedupe
- `app_qt.py` 将最后生效的 `_refresh_detail_workspace_panels()` 中 `detail_decision_text / detail_execution_text / detail_conclusion_text` 统一切到 `_set_plain_text_if_changed`，减少详情联动、信号切换和成交回看时的长文本重复重写。
- `app_qt.py` 同步把 `_qh_prime_recommend_workspace_defaults_v2()` 里的 `recommend_status_label / recommend_empty_title / recommend_empty_meta / last_refresh_label` 切到按需写入，让推荐页默认态在初始化与回填时更稳定。
- 这轮继续坚持低风险 UI 性能优化，不改推荐和交易逻辑，只压缩无效重绘和默认态闪动。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 20:02 Board Default Panels And Focus Metrics Dedupe
- `app_qt.py` 将 `_qh_normalize_board_workspace_texts_v2()` 里的 `board_text / board_monitor_text` 以及 `auto_review_export_checkbox` 文案统一改成按需写入，减少打板专项页初始化与回填时的重复重绘。
- `app_qt.py` 同步把推荐页焦点卡默认指标 `recommend_focus_metric_labels / recommend_focus_metric_accents` 切到 `_set_label_text_if_changed`，降低推荐页进入时和默认态重置时的标签抖动。
- 这一轮继续只打磨显示层稳定性和商业终端观感，不动任何交易、推荐或风控判断。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 20:10 Auxiliary Defaults Unification
- `app_qt.py` 将 `_qh_normalize_aux_workspace_texts_v2()` 中一组默认标签与按钮文案的批量回填统一切到 `_set_label_text_if_changed`，减少工作台初始化、文案修复和异常回填时的重复写入。
- `app_qt.py` 同步把 `_qh_hydrate_empty_workspace_panels_v2()` 里的空态 `QTextEdit` 批量回填切到 `_set_plain_text_if_changed`，让总览、详情与推荐等空面板走同一套幂等更新路径。
- 这轮属于“全局尾部统一化”，继续压低零散默认态刷新带来的闪动和不一致感。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 20:18 Overview Builder Label Dedupe
- `app_qt.py` 将 `_qh_repair_runtime_widget_texts_v2()` 里的运行时文案修复批量 `widget.setText(...)` 统一切到 `_set_label_text_if_changed`，减少页面修复阶段对按钮、勾选框和标签的重复写入。
- `app_qt.py` 同步把 `_qh_normalize_overview_builder_texts_v2()` 里的总览页按钮、页头标签和按钮组标题统一改成按需写入，降低切视图、重建按钮映射和工作台初始化时的标签抖动。
- 这轮继续只优化显示层和交互稳定感，不改总览策略逻辑与数据流。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 20:24 Refresh Toggle Copy Consistency
- `app_qt.py` 将后段布局收口逻辑里 `dashboard_auto_refresh_checkbox` 的文案重写统一成“盘中自动刷新”，并走 `_set_label_text_if_changed`，避免总览页前后出现“自动刷新 / 盘中自动刷新”两套表达来回切换。
- 这是一处很小但直接影响成品感的文案一致性修补，继续提升商业终端界面的稳定与专业感。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 20:31 Focus Card Title And Action Copy Dedupe
- `app_qt.py` 将推荐页默认按钮 `recommend_empty_sample_button / recommend_empty_refresh_button` 切到 `_set_label_text_if_changed`，减少空态回填时的无效重写。
- `app_qt.py` 同步把 `_qh_normalize_action_row_texts_v2()` 中动作行按钮文案归一化，以及 `_qh_apply_focus_dashboard_v7()` 里的推荐焦点卡、委托焦点卡标题更新，统一改成按需写入。
- 这轮继续打磨小而密的界面表达细节，让焦点区和动作区在运行时修复、初始化和视图切换时更稳、更像成品终端。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 20:39 Legacy Recommend Default Path Cleanup
- `app_qt.py` 将较早版本的 `_prime_recommend_workspace_defaults()` 也统一切到 `_set_label_text_if_changed`，覆盖推荐状态、空态文案、默认按钮、最近刷新标签和推荐焦点默认指标，避免历史初始化路径把新文案与幂等更新策略覆盖回旧写法。
- `app_qt.py` 同步把一条较早的动作行按钮归一化分支也切到按需写入，继续减少旧路径带来的文案回跳与重复重绘。
- 这一轮属于“兼容旧分支收尾”，继续保证不同初始化入口下的界面表达尽量一致。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 20:47 Scanner And Recommend Legacy Repair Unification
- `app_qt.py` 将较早版本的 `_normalize_scanner_workspace_texts()` 里的 `scan_summary_label / last_refresh_label / universe_label` 修复逻辑统一切到 `_set_label_text_if_changed`，减少扫描页默认态在历史入口下的重复回填。
- `app_qt.py` 同步把另一段较早的 `_prime_recommend_workspace_defaults()` 中推荐状态、空态按钮、最近刷新和推荐焦点默认指标也统一切到按需写入，继续压低旧路径覆盖新文案的概率。
- 这轮继续做兼容尾部统一化，不动业务逻辑，只提升多入口初始化时的一致性和稳定感。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 20:52 Early Recommend Branch Alignment
- `app_qt.py` 继续补齐另一段更早的推荐页默认态分支，把 `universe_label` 以及推荐状态、空态按钮的直写也统一切到 `_set_label_text_if_changed`，减少同类逻辑分散残留。
- 这一轮是尾部扫漏，目标是尽量让推荐页默认态无论走到哪个历史入口，都保持一致的文案和幂等更新行为。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 20:59 Legacy Broker Default Panels Dedupe
- `app_qt.py` 将较早版本的推荐页说明面板 `recommend_dispatch_text / recommend_focus_review_text / recommend_queue_text / strategy_path_text` 统一切到 `_set_plain_text_if_changed`，减少历史初始化入口下的大段说明文案重复写入。
- `app_qt.py` 同步把较早版本的券商默认态 `_prime_broker_workspace_defaults()` 里的四组指标标签和三块提交回顾面板，统一切到 `_set_label_text_if_changed` / `_set_plain_text_if_changed`。
- 这轮继续只清理旧入口下的显示层残留，不改交易和推荐逻辑，目标是把历史路径也收进同一套稳定刷新模型。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 21:06 Legacy Overview And Aux Copy Unification
- `app_qt.py` 将较早版本的 `_normalize_overview_builder_texts()` 里的总览状态、页头标签、行情说明和按钮组标题，统一切到 `_set_label_text_if_changed`，减少旧总览入口下的文案重复写入。
- `app_qt.py` 同步把 `_normalize_aux_workspace_texts()` 里的默认标签与按钮文案回填，也统一切到幂等写入，继续降低辅助工作台初始化时的文案回跳。
- 这一轮继续清理旧版 UI 文案分支，让多入口下的终端表达更一致、更像同一套产品。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 21:13 Login And Early Broker Label Cleanup
- `app_qt.py` 将辅助工作台另一段更早的默认标签/按钮批量回填，也统一切到 `_set_label_text_if_changed`，继续压缩零散旧分支。
- `app_qt.py` 同步把登录页默认标签与按钮回填，以及一版更早的券商默认指标标签更新，统一切到按需写入，减少初始化时的标签回跳。
- 这轮继续只做显示层收尾，让配置、登录和交易入口在不同历史路径下保持更一致的表达。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 21:20 Login Status And Broker Order Metric Dedupe
- `app_qt.py` 将登录页说明面板 `login_status_text` 切到 `_set_plain_text_if_changed`，减少登录配置初始化和回填时的大段文本重复写入。
- `app_qt.py` 同步把一版更早的券商委托焦点默认指标 `broker_order_metric_labels / broker_order_metric_accents` 也统一切到 `_set_label_text_if_changed`。
- 这一轮继续补齐最后几处高可见默认态残留，让登录、券商和工作台三条入口的显示层行为更一致。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 21:27 Detail Panel And Top Badge Dedupe
- `app_qt.py` 将一版较早的详情联动面板 `detail_decision_text / detail_execution_text / detail_conclusion_text` 也统一切到 `_set_plain_text_if_changed`，减少旧明细入口下的长文本重写。
- `app_qt.py` 同步把两处旧版 `_refresh_workspace_status_labels()` 里的 `top_badge` 更新切到 `_set_label_text_if_changed`，降低工作台切页和状态刷新时顶部徽标的重复重绘。
- 这一轮继续收高可见区域的历史残留，让“系统一直在推进”的顶部状态表达更稳。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 21:35 Legacy Submission And Recommend/Broker Copy Unification
- `app_qt.py` 将一版较早的 `_refresh_submission_focus()` 也统一切到 `_set_plain_text_if_changed`，覆盖 `order_result_text / broker_recap_text` 的空态和真实回放，减少旧交易执行入口下的长文本重写。
- `app_qt.py` 同步把一版较早的推荐说明面板 `recommend_dispatch_text / recommend_focus_review_text / recommend_queue_text / strategy_path_text`，以及券商默认态里的指标标签和三块委托回顾面板，统一切到幂等更新。
- 这一轮把一整片旧版推荐到交易链路的默认显示路径收进同一套刷新模型，继续提升多入口下的一致性和商业终端稳定感。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 21:42 Empty Panel Hydration Tail Cleanup
- `app_qt.py` 将登录页按钮文案标准化分支里的 `button.setText(...)` 统一切到 `_set_label_text_if_changed`，减少登录入口修复时的按钮文案回跳。
- `app_qt.py` 同步把 `_hydrate_empty_workspace_panels()` 里的空面板批量回填 `widget.setPlainText(text)` 统一切到 `_set_plain_text_if_changed`，继续收紧默认说明面板的多入口刷新路径。
- 这一轮属于默认态尾部清扫，目标是让空面板、登录和推荐交易链路在旧入口下保持同一套稳定刷新行为。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 21:49 Chart Title And Group Header Dedupe
- `app_qt.py` 将一版较早的总览图表标题更新改成“仅在标题变化时才写入”，覆盖市场代理走势、主图、资金和动能四张图，减少切换周期窗口时的无效标题重绘。
- `app_qt.py` 同步把认证页分组标题标准化改成按需更新，继续收口高可见分组标题的历史残留。
- 这一轮继续打磨高可见但低风险的终端表达细节，让图表区和设置区的成品感更稳定。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 21:56 Tab Header Tail Cleanup
- `app_qt.py` 将一版较早的辅助工作台页签标题归一化 `tabs / recommend_stage_tabs / right_intel_tabs` 改成“仅在标签变化时才更新”，减少切页和多入口初始化时的重复页签重绘。
- `app_qt.py` 同步把认证页与配置页分组标题的历史标准化分支也改成按需更新，继续收紧设置入口的标题一致性。
- 这轮继续处理高可见但低风险的标题层残留，让整个工作台更像一套统一、克制的商业终端界面。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 22:02 Final Tab Text Dedupe Sweep
- `app_qt.py` 将另一版较早的 `_normalize_aux_workspace_texts()` 里的 `tabs / recommend_stage_tabs / right_intel_tabs` 页签文字标准化，也统一切到“只有文字变化时才更新”的路径。
- 这一轮属于标题层最后一遍扫尾，目的就是把多入口下的页签表达全部收进同一套克制的刷新行为，避免旧分支残留反复重绘。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 22:08 Broker Default Panel Tail Cleanup
- `app_qt.py` 将另一版较早的券商默认态三块长文面板 `broker_order_focus_text / order_result_text / broker_recap_text` 也统一切到 `_set_plain_text_if_changed`。
- 这一轮继续扫旧券商入口的最后几处长文本残留，减少交易执行页默认态在历史初始化路径下的整段重写。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 22:15 Final Active Path Title And Broker Default Sweep
- `app_qt.py` 将当前生效的 `_qh_prime_broker_workspace_defaults()` 里四块默认说明面板 `broker_order_focus_text / order_result_text / broker_recap_text / broker_status_text` 统一切到 `_set_plain_text_if_changed`，减少交易执行页默认态在现行路径下的无效重写。
- `app_qt.py` 同步把当前生效的 `right_intel_tabs`、`market_news_group` 和 `_qh_normalize_aux_workspace_texts_v2()` 里的主工作台页签标题改成“仅在标题变化时才更新”。
- 这轮相当于把“当前活跃路径”的标题层和券商默认态也做了最终收口，让现行主路径和历史兼容路径都回到同一套稳定刷新模型。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 22:22 Active Tab And Header Closure
- `app_qt.py` 将当前活跃路径里的 `recommend_stage_tabs` 页签标题，以及全局 `QTabWidget / QGroupBox` 文案修复分支，也统一改成“只有文本真的变化时才更新”。
- 这一轮相当于把标题层最后几个仍会无条件写入的分支也收口，进一步减少全局文案修复时的无效页签与分组标题重绘。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 22:29 Action Button Alias Tail Cleanup
- `app_qt.py` 将最后一处动作按钮旧别名映射分支 `button.setText(...)` 统一切到 `_set_label_text_if_changed`，覆盖“只看主线前排 / 导出运行日志”等历史按钮文案修正入口。
- 同轮复查后，剩余命中的 `item.setText(...)` 属于表格内容真实变化，`_qh_set_label_text_v7()` 的 `widget.setText(...)` 属于 helper 兜底路径，暂不为“归零命中数”而增加额外改动风险。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 22:36 Helper Fallback Dedupe
- `app_qt.py` 将 `_qh_set_label_text_v7()` 的 fallback `widget.setText(...)` 也补成“先比较再写入”，让少量仍走 helper 兜底的历史标签路径也具备幂等更新行为。
- 这一轮属于极小收尾，不改业务逻辑，只把最后一个仍可能无条件写标签的兜底点补齐。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 22:43 Overview Table Cell Tail Dedupe
- `app_qt.py` 将总览焦点表格里动作摘要列的 `item.setText(brief)` 改成“仅在文本变化时才写入”，避免同一状态色和同一摘要反复刷回单元格。
- 到这一轮为止，当前活跃路径里能稳定拿收益的同值重复写入点已经基本收完，剩余命中更多属于真实数据变化或 helper 内部正常实现。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 22:51 Group Header Tail Dedupe
- `app_qt.py` 将两处分组标题 `parent.setTitle(title)` 和一处“推荐焦点”分组标题更新，也统一改成“只有标题变化时才更新”。
- 这一轮继续补齐标题层最后几个高可见、低风险的无条件写入点，让推荐页和打板页的分组标题在多入口修复时更稳。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 23:04 Active Status And Broker Focus Dedupe
- `app_qt.py` 灏嗗綋鍓嶇敓鏁堢殑 `_on_workspace_tab_changed()` 涓?`top_badge` 鍜?`_on_market_history_date_changed()` 閲岀殑 `market_status_label` 鏀规垚鈥滃厛姣旇緝鍐嶆洿鏂扳€濓紝缁х画鍘嬩綆鍒囬〉銆佸巻鍙叉棩鏈熷垏鎹㈠拰椤堕儴鐘舵€佹爣绛剧殑鏃犳晥鍐欏叆銆?
- `app_qt.py` 鍚屾鎶婂綋鍓嶇敓鏁堢殑 `_refresh_broker_order_focus()` 閲岀殑 `broker_order_focus_text / orders_focus_label / broker_order_metric_labels / broker_order_metric_accents` 缁熶竴鍒囧埌 `_set_plain_text_if_changed` / `_set_label_text_if_changed`锛屽噺灏戝鎵樼劍鐐瑰垏鎹㈠拰鏃犻€夋椂鐨勭┖鎬佸弽澶嶅洖鍐欍€?
- 杩欎竴杞户缁攣瀹氬綋鍓嶆椿璺冭矾寰勯噷鐨勯珮鍙鍒锋柊鐐癸紝璁╁伐浣滃彴鐘舵€佸拰鍒稿晢濮旀墭鐒︾偣鍦ㄨ繛缁繍琛屾椂鏇寸ǔ銆?
- 寰呴獙璇侊細`py_compile`銆丵t smoke銆佸叏閲?`unittest`銆?
## 2026-04-13 23:18 Shell Copy Premium Pass
- `app_qt.py` 灏嗛《閮?shell header` 鐨勭溂鐪夋爣璇€佸壇鏍囬銆乸ulse bar` 榛樿鎻愮ず浠ュ強 `top_badge` 鍒囨崲鎴愭洿鍟嗕笟鍖栥€佹洿鍍忔満鏋勭粓绔殑榛樿琛ㄨ揪锛屾彁鍗囬灞忕殑鎴愬搧鎰熴€?
- `app_qt.py` 鍚屾鎶婃€昏鍚姩鐘舵€佹枃妗堜粠鈥滄鍦ㄥ噯澶囧競鍦烘暟鎹€濆崌绾ф垚鈥滄鍦ㄥ缓绔嬪競鍦哄揩鐓р€濓紝璁╃敤鎴疯兘鏇寸洿瑙夊湴鐞嗚В绯荤粺鍦ㄥ共浠€涔堛€?
- 杩欎竴杞富鎵撳晢涓氬寲缁堢琛ㄨ揪鍜岀姸鎬侀€忔槑搴︼紝涓嶅姩绠楁硶銆侀鎺ф垨浜ゆ槗閫昏緫锛屽睘浜庝綆椋庨櫓楂樻劅鐭ュ崌绾с€?
- 寰呴獙璇侊細`py_compile`銆丵t smoke銆佸叏閲?`unittest`銆?
## 2026-04-13 23:31 Trade Plan Table Signature Guard
- `app_qt.py` 鍦ㄥ綋鍓嶇敓鏁堢殑 `_refresh_trade_plan()` 閲屼负 `trade_plan_table` 澧炲姞浜嗚鍐呭绛惧悕鐭矾锛岃鍒掑唴瀹规病鍙樻椂涓嶅啀鏁磋〃 `setRowCount + setItem` 閲嶅缓锛屽噺灏戞帹鑽愩€佷氦鏄撹鍒掕仈鍔ㄦ椂鐨勮〃鏍奸噸缁樻垚鏈銆?
- 鍚屾鎶?`trade_plan_focus_label / trade_plan_empty_hint / trade_plan_text` 鍒囧埌鎸夐渶鍐欏叆锛岃璁″垝鏈《閮ㄧ劍鐐逛笌鍙充晶闀挎枃鏈湪鐩稿悓鍐呭涓嬩笉鍐嶅弽澶嶅洖鍐欍€?
- 杩欎竴杞槸浠ュ綋鍓嶆椿璺冭矾寰勭殑楂橀琛ㄦ牸鍒锋柊涓轰紭鍏堢骇鐨勪竴姝ワ紝缁х画鍦ㄤ笉鍔ㄤ氦鏄撳喅绛栫殑鍓嶆彁涓嬫彁鍗囩晫闈㈡祦鐣呭害銆?
- 寰呴獙璇侊細`py_compile`銆丵t smoke銆佸叏閲?`unittest`銆?
## 2026-04-13 23:42 Intraday Monitor Row Diff Update
- `quant_hunter/ui_refresh.py` 在 `refresh_intraday_monitor()` 中新增按行签名比对：仅当某行签名变化时才重绘该行，避免任何一条监控行变化时整表重建所有单元格。
- 这一改动保持现有签名机制不变，只减少重复 `setItem` 与重建 badge/identity cell 的成本，盘中监控刷新更稳更省。
- 待验证：`py_compile`、Qt smoke、全量 `unittest`。
## 2026-04-13 23:49 Scan And Backtest Row Diff Update
- `quant_hunter/ui_refresh.py` 将 `fill_scan_rows()` 和 `fill_backtest_summaries()` 从“签名变化就整表重建”升级成“只重绘变化行”，同时包进 `_batched_table_update(...)`，减少高频扫描与回测摘要刷新时的无效 `setItem`。
- 选中态、整表签名短路和现有 badge/identity cell 结构保持不变，只在有变化的行上重建复合单元格，尽量压低重绘成本。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-13 23:57 Daily Pool Row Diff Update
- `quant_hunter/ui_refresh.py` 将 `populate_filtered_daily_pool_table()` 从“签名变化就整表重刷”推进到“仅重绘变化行”，推荐池表中 20+ 列普通单元格与复合 badge cell 只在该行数据变化时更新。
- 同轮顺手移除了函数尾部一处未定义的 `orders_signature` 写入，避免推荐池刷新路径潜在触发 `NameError`。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 00:08 Recommend And Broker Terminal Copy Pass
- `app_qt.py` 将当前生效的推荐链路标题统一成更明确的阶段语言：`待送审 / 焦点复核 / 已提交与失败`，同时升级三块默认说明文案，让推荐到交易的流水线表达更清楚。
- 同轮将交易执行区默认文案进一步收口成 `主线闸门 / 为什么` 与 `最近执行` 视角，强化“能不能下单、为什么、最近发生了什么”的 operator console 感。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 00:18 Recommend Summary Language Alignment
- `quant_hunter/ui_refresh.py` 将推荐摘要卡 `logic / plan / pulse / holding` 的详情文案统一成更接近交易链路的终端语言，例如 `主线 / 待复核 / 风险灯 / 持仓处理建议`，提升推荐页与交易页之间的表达连续性。
- `app_qt.py` 同步将当前生效的推荐焦点摘要卡文案收口成 `风险灯 / 送审准备 / 主线窗口 / 链路下一步` 这一套口径，让焦点卡、顶部状态和执行面板更像同一套产品语言。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 00:27 Alert And Default Copy Closure
- `app_qt.py` 将告警卡 fallback 文案统一成更贴近终端状态的表达，例如 `主线强度 / 位次 / 风险灯 / 链路阶段`，避免无数据时退回到偏开发态的提示口吻。
- 同轮将推荐摘要卡默认态文案收口成 `主线、位次、风险灯、送审优先级、主线窗口` 这套统一语言，让空态、默认态和实时态读起来像同一套终端产品。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 00:36 Scanner Monitor Copy Closure
- `app_qt.py` 将扫描与监控焦点卡的默认提示从 `待刷新 / 等待盘中监控 / 等待盘中联动` 收口成更统一的终端表达，例如 `待联动 / 等待监控链路 / 等待扫描链路`。
- 同轮把扫描页默认状态文案里的“生成观察池与盘中监控焦点”压缩成更干净的“同步观察池与监控焦点”，让扫描页空态、焦点卡和顶部状态语气更一致。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 00:45 Overview Empty State Polish
- `app_qt.py` 将总览侧边面板空态从笼统的“等待刷新”升级成更明确的终端语义，例如 `等待主线同步 / 等待候选同步 / 等待推演同步`，让空态也能解释系统当前缺的是什么。
- `quant_hunter/ui_refresh.py` 同步把总览指标卡的空态提示收口成 `等待候选同步 / 等待热度同步 / 等待主线同步`，避免高可见区域残留工具化提示。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 00:54 Legacy Scanner Copy Sweep
- `app_qt.py` 清扫了两段历史扫描页实现里仍会露出的默认提示，将 `等待刷新 / 待刷新 / 等待盘中监控 / 等待盘中联动` 统一收口成 `等待扫描链路同步 / 待联动 / 等待监控链路`。
- 同轮把旧分支里的扫描页空态文案也改成“同步观察池与监控焦点”，避免不同入口下出现两套扫描页语言。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 01:14 Premium Empty-State And Shell Pulse Pass
- `app_qt.py` 收口了当前生效推荐工作区默认态里的高可见文案，把 `最近刷新` 从“等待市场数据同步”升级成“等待市场快照建立”，同时把推荐摘要卡 fallback 从泛化的“等待刷新”收成“等待链路同步”，让空态更像交易终端而不是开发态提示。
- `quant_hunter/ui_refresh.py` 同步升级了主线推演、战法详情、排行榜和策略卡的空态表达，统一成 `等待候选同步 / 等待机会池同步后更新` 这一组更贴近推荐链路的口径，并保持现有幂等签名逻辑不变。
- `app_qt.py` 继续打磨顶部 shell pulse 的待启动文案，把系统当前等待的对象明确成“市场快照、候选优先级与交易链路”，同时把下一动作改成更清楚的终端操作提示，提升页面静止时的工作感与状态透明度。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 01:28 Board Monitor And Overview Focus Copy Pass
- `app_qt.py` 收口了打板监控摘要、盘中监控摘要和总览主题焦点卡里仍然残留的旧空态文案，把 `等待刷新 / 等待打板监控刷新 / 等待盘中监控刷新` 统一升级成 `等待监控链路同步 / 等待候选同步 / 等待扫描链路同步`，让扫描、监控、打板和总览四个入口的口径继续对齐。
- `app_qt.py` 同步把打板焦点卡的标签更新切成 `_set_label_text_if_changed(...)`，并把默认态从 `待刷新 / 等待盘中监控` 收口成更明确的 `待联动 / 等待监控链路`，在不改业务判断的前提下减少高频重复写标签。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 01:42 Detail Panels And Overview Console Dedupe
- `app_qt.py` 继续把当前生效路径里的高频文本面板切到按需更新，覆盖了总览指挥区里的 `overview_command_text / overview_execution_text / market_capital_text / market_decision_text`，以及推荐链路中的 `trade_plan_text / market_pulse_text / daily_pool_text`，减少重复 `setPlainText(...)` 带来的无效重写。
- `app_qt.py` 同步补齐了详情页与执行页的一批高可见文本区，包括 `broker_execution_text / detail_decision_text / detail_execution_text / detail_conclusion_text` 及一处历史兼容入口，让多入口切换时也尽量保持幂等刷新。
- 这一轮没有改动任何交易决策、风控判断或数据结构，只收口显示层的刷新方式与默认态表现。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 02:06 Order Feedback Panel Dedupe
- `app_qt.py` 把交易执行链路里 `order_result_text / broker_recap_text / broker_order_focus_text` 的默认态与执行回放收口为按需更新，并统一 `_refresh_submission_focus` 两个入口都走 `_set_plain_text_if_changed(...)`，减少提交记录刷新时的重复重写。
- `app_qt.py` 同步收口 `_append_order_result(...)` 的追加路径，避免提交日志滚动时高频 `setPlainText(...)` 反复写入。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 02:26 Portfolio And Broker Panel Dedupe
- `app_qt.py` 收口了 `license_status_text / position_advice_text / broker_status_text` 等高可见文本区的直接 `setPlainText(...)`，改为 `_set_plain_text_if_changed(...)`，降低刷新负担并保持文案一致。
- `app_qt.py` 同步收口打板页的默认提示文本（多处入口），确保主路径和兼容入口统一走幂等写入，减少多入口切换时的重复刷新。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 02:42 Terminal Panel Dedupe Pass
- `app_qt.py` 继续收口高频文本区的 `setPlainText(...)`：登录状态、工作台报告、参数优化、持仓处置说明、打板页默认提示和模拟盘回放等，统一改为 `_set_plain_text_if_changed(...)`。
- `app_qt.py` 同步把默认面板填充逻辑里的 `QTextEdit` 赋值也走幂等写入，减少启动和切换路径下的重复文本重绘。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 03:02 Final PlainText Dedupe Sweep
- `app_qt.py` 把登录状态、工作台报告、参数优化提示、模拟盘回放与面板默认填充的 `setPlainText(...)` 统一改为 `_set_plain_text_if_changed(...)`，把高频文本写入全面收口到幂等路径。
- `app_qt.py` 将题材词典编辑器初始化也切到幂等写入，避免打开弹窗时重复覆盖文本。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 03:18 Order Table Batch Update
- `app_qt.py` 对 `_refresh_submission_table()` 增加了 `setUpdatesEnabled(False)` 与 `blockSignals(True)` 包裹，避免委托提交记录刷新时的闪烁与多次重绘。
- 这一轮依旧不改业务逻辑，仅优化 UI 刷新节奏与用户感知稳定性。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 03:36 Board Table Batch Update
- `app_qt.py` 对打板候选表与打板监控表的刷新增加 `setUpdatesEnabled(False)` 和 `blockSignals(True)` 包裹，减少高频刷表时的闪烁和信号抖动。
- 这次依旧只动显示层刷新节奏，不触及打板评分或候选逻辑。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 03:52 Signal And Trade Table Batch Update
- `app_qt.py` 对信号表与成交记录表的刷新增加 `setUpdatesEnabled(False)` 与 `blockSignals(True)` 包裹，减少高频行更新时的抖动和闪烁。
- 依旧不改业务逻辑，仅优化显示层刷新成本。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 04:04 Paper Trading Table Batch Update
- `app_qt.py` 对模拟盘的 `paper_positions_table / paper_ledger_table / paper_strategy_table / paper_patrol_table` 增加批量刷新包裹（`setUpdatesEnabled(False)` + `blockSignals(True)`），减少高频巡航刷新时的表格闪烁与信号抖动。
- 依旧不改变任何交易逻辑，仅优化 UI 刷新成本。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 04:24 Trade Plan And Position Table Batch Update
- `app_qt.py` 对交易计划表与持仓处置表的刷新增加批量更新包裹（`setUpdatesEnabled(False)` + `blockSignals(True)`），减少刷新计划/持仓时的表格闪烁。
- 逻辑不变，仅优化 UI 更新节奏。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 04:44 Order Dialog Batch Update
- `app_qt.py` 对下单确认弹窗的 `order_table` 刷新增加 `setUpdatesEnabled(False)` 与 `blockSignals(True)` 包裹，减少确认界面加载时的闪烁。
- 仍不改变任何下单或确认逻辑，仅优化显示刷新。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 05:06 Trade Plan Detail Batch Update
- `app_qt.py` 对多个 trade plan / position advice 的兼容入口表格刷新增加批量更新包裹，避免重复刷表时的闪烁。
- 依旧不改业务逻辑，仅优化显示层刷新节奏。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 05:28 Execution Table Signature Guard
- `app_qt.py` 为执行记录表 `_refresh_submission_table()` 增加签名缓存，内容未变时跳过整表重建，只保留焦点刷新。
- 依旧不动业务逻辑，仅减少无效表格重绘。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 05:50 Trade Plan Signature Guard
- `app_qt.py` 为主线交易计划表和持仓处置表增加签名缓存，内容未变时直接跳过整表重绘。
- 继续保持只优化显示层刷新成本，不触及业务逻辑。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 06:18 Market Channel Copy Pass
- `app_qt.py` 将顶部行情通道的默认状态从“待同步”升级为“等待行情接入”，与整体终端语气保持一致。
- 逻辑不变，仅优化可见文案一致性。
- 待验证：`py_compile`、全量 `unittest`。
## 2026-04-14 07:20 Focus Sync Copy Closure
- `app_qt.py` 缁画娓呯悊鎺ㄨ崘/鎬昏/澶/澶嶇洏涓渶鍚庡嚑澶勫皢鈥滃緟鍚屾鈥濆洖閫€鐨勬枃妗堬紝缁熶竴鎴愭洿绗﹀悎缁堢琛ㄨ揪鐨勨€滅瓑寰呰鎯呮帴鍏ュ拰绛夊緟淇″彿/绛外緟绛栫暐鍚屾鈥濓紝閬垮厤鍦ㄧ┖鎬佹椂鏈a���t?  
## 2026-04-14 07:22 Focus Sync Copy Closure (clean)
- `app_qt.py` Harmonized remaining "待同步" copy to terminal-grade "等待行情接入/等待策略同步/等待信号同步/等待标的同步/等待行情同步".
- `app_qt.py` Routed legacy recommend focus metric defaults through `_set_label_text_if_changed` to avoid redundant repaints.
- Verification: `py_compile` and `unittest` pending.
## 2026-04-14 16:57 Broker Execution First-Screen Summary
- `app_qt.py` adds a pure broker execution summary helper to classify submitted records into pending/failure/filled tracking stages and generate concrete next-step guidance.
- Active `_qh_refresh_submission_focus_v26` now upgrades `order_result_text`, `broker_recap_text`, `broker_execution_text`, `broker_workbench_banner`, and `broker_status_banner` when an execution record is selected, so the trade workspace lands on a clearer terminal-style verdict instead of only raw status fields.
- Added a second pure helper that translates execution stage into concrete route guidance such as staying on the trade page, returning to recommend, or switching to review, improving recommend-to-trade-to-review continuity.
- Added a third pure helper that translates common failure reasons into practical repair actions such as shrinking size, fixing risk parameters, or checking the broker channel, then surfaces that guidance in the mainline review and order-focus areas.
- Added stage-driven visual tone mapping so the broker status banner, workbench banner, stage label, order-focus label, execution table, and execution text panels shift to buy/watch/risk hierarchy based on the currently selected execution stage.
- Added recommend-context carry-through so the broker execution first screen now repeats the current price plan and latest catalyst/source lines from the recommend workspace, reducing bounce-back between tabs before users decide whether to hold, retry, or review.
- Added execution-vs-plan parameter comparison so the broker first screen now tells users whether the actual委托价 is still贴合买点, already偏高, 接近目标位, or should be treated as防守/兑现 handling, with concrete checkpoints on whether to改价格、改仓位 or回推荐页复核.
- Added a final resolution-entry helper so the broker first screen now clearly tells users the next handling入口 should be账户配置、推荐页、委托参数区、执行回执区 or复盘页, and reuses that guidance in collapsed detail status plus submit/regenerate button tooltips.
- Added a compact terminal-brief helper so the visible broker banners and focus labels are now shorter, denser, and more desk-terminal-like, while detailed reasoning stays in tooltips and text panels.
- Added a panel-conclusion helper so each broker execution text panel now starts with a single-line conclusion in terminal format before expanding into detailed reasoning.
- `tests/test_core.py` adds narrow helper coverage for pending, filled, failed, route-followup, repair-hint, stage-tone, recommend-context, parameter-alignment, resolution-entry, compact-brief, and panel-conclusion execution summaries.
- Verification: `py_compile` and `unittest` passed.
## 2026-04-14 10:58 Recommend Default-State Consistency And Builder Helper
- `quant_hunter/ui_config.py` adds shared recommend empty-state title/button constants, so the recommend workspace now has one source of truth for empty-title, guidance CTA, focus copy, and broker/recommend default banners.
- `app_qt.py` routes more empty/default/focus branches onto those shared constants, including recommend focus fallback, order-focus fallback, and trade-plan empty fallback, reducing copy drift across runtime compatibility paths.
- `quant_hunter/workspace_builders.py` now builds the recommend daily-pool table through a dedicated helper, keeping the commercial table shape, scroll policy, row height, and selection wiring centralized for future polish.
- Verification: `py_compile` passed, `python -m unittest discover -s tests -v` passed (`130` tests), and `app_qt.py` launched for a live smoke run within the observation window.
## 2026-04-14 11:12 Recommend Interaction Transparency Pass
- `quant_hunter/ui_config.py` adds a shared recommend empty-state hint so the empty panel copy now matches the actual CTA buttons (`载入样例数据 / 重算机会池`) instead of older phrasing.
- `quant_hunter/workspace_builders.py` uses a small helper to configure recommend-side focus actions, reducing duplicated role/disabled/tooltip/click wiring and keeping future CTA polish safer.
- `quant_hunter/workspace_builders.py` and `app_qt.py` both upgrade the recommend auxiliary-stage toggle/status area with clearer tooltips, so users can better understand when to stay focused on成交核心区块 and when to unfold deeper战法/复盘洞察.
- Verification: `py_compile` passed and `python -m unittest discover -s tests -v` passed (`132` tests).
## 2026-04-14 11:24 Recommend CTA Chain Clarification
- `app_qt.py` connects the active recommend decision-summary refresh path to the existing CTA label helper, so the three primary buttons now surface clearer state-driven copy such as `暂不送审 / 查看送审中 / 查看已提交 / 暂不进交易 / 查看交易链路`.
- The same path now updates CTA tooltips with symbol, verdict, execution hint, and next-step wording, making the recommend-to-review-to-trade chain easier to scan without extra clicks.
- `tests/test_core.py` adds an empty-focus regression test to pin the default CTA text and disabled state when no focus stock is selected, reducing the risk of legacy compatibility patches drifting this workflow.
- Verification: `py_compile` passed and `python -m unittest discover -s tests -v` passed (`136` tests).
## 2026-04-14 11:36 Recommend-To-Broker Status Transparency
- `app_qt.py` adds a dedicated recommend-to-broker link-copy helper so cross-page jump feedback now distinguishes `已送审 / 已提交 / 提交失败 / 已同步记录 / 等待生成委托建议` instead of flattening everything into the same “已联动” copy.
- The active broker-focus jump path now applies that helper to both the top trading banner and the order-focus label, keeping the first-screen feedback aligned when users jump from推荐页 directly into交易执行.
- `tests/test_core.py` adds a regression test for the new broker link-copy helper, pinning the wording for review, submitted, and failed states.
- Verification: `py_compile` passed and `python -m unittest discover -s tests -v` passed (`137` tests).
## 2026-04-14 11:48 Recommend-To-Broker Landing Target Polish
- `app_qt.py` adds a small broker landing-target helper so recommend-side jumps now choose the first visible focus area based on real execution state: `已提交 / 提交失败` prefer the submission-record table, while `已送审 / 待执行` stay anchored on the order-intent table.
- This keeps the initial broker landing aligned with the user’s next likely action: track回执 when the order is already in flight, or continue复核/送审 when it is not.
- `tests/test_core.py` adds a regression test for the landing-target helper to pin the expected routing for submitted, failed, and reviewing states.
- Verification: `py_compile` passed and `python -m unittest discover -s tests -v` passed (`138` tests).
## 2026-04-14 09:12 Daily Pool Header Stabilization
- `quant_hunter/workspace_builders.py` re-applied clean daily pool headers (23 columns) to ensure "买卖价" is always visible even if legacy garbled labels appear.
- Verification: `py_compile` and `unittest` pending.
## 2026-04-14 09:36 Price Ladder Readability Pass
- `quant_hunter/ui_refresh.py` adds a shared price snapshot helper for the daily pool, includes stop price in the refresh signature, and surfaces price-space text in tooltips.
- `quant_hunter/ui_refresh.py` upgrades the "买卖价" column to a color-coded compact badge, so entry/target prices scan faster in dense terminal tables.
- `app_qt.py` links recommendation live summary and detail panels with the same price ladder brief, upside/risk ratio, hype logic, and recent catalyst lines.
- `quant_hunter/ui_cards.py` adds leaderboard status tooltips so users can hover the badge and immediately see action, strategy, mainline, and why-now context.
- Verification: `py_compile` and `unittest` passed.
## 2026-04-14 09:58 Daily Pool Header Unification
- `quant_hunter/ui_config.py` extracts shared `DAILY_POOL_TABLE_HEADERS`, giving the recommend workspace a single source of truth for the 23-column opportunity-pool schema.
- `app_qt.py` switches the main identity-header refresh paths to the shared header constant, reducing future column drift when the daily pool evolves.
- `quant_hunter/workspace_builders.py` now reapplies the shared daily-pool headers at the end of workspace construction, so runtime always lands on the clean commercial header set even if legacy builder code still exists earlier in the file.
- `quant_hunter/ui_refresh.py` sets the final "买卖价" badge item to right-aligned numeric layout so the price ladder remains scan-friendly after badge replacement.
- Verification: `py_compile` and `unittest` passed.
## 2026-04-14 10:09 Recommend-To-Trade Summary Transparency
- `app_qt.py` upgrades the recommend decision summary card with unified price plan text, logic/theme explanation, upside-vs-defense space, and recent catalyst lines.
- This makes the "送审前最后一眼" panel closer to a commercial terminal summary, reducing the need to bounce between recommend, detail, and broker tabs just to confirm one symbol.
- Verification: `py_compile` and `unittest` passed.
## 2026-04-14 10:22 Action Tooltip Transparency Pass
- `app_qt.py` enriches recommend-side action button tooltips with verdict, price plan, and next-step guidance, so users can judge whether to送审/去交易页 before clicking.
- `app_qt.py` upgrades `orders_focus_label` and `recommend_status_label` tooltips with symbol, mainline, price plan, risk lamp, and catalyst context while keeping the visible text compatible with existing workflows and tests.
- Verification: `py_compile` and `unittest` passed.
## 2026-04-14 10:31 Recommend Builder Default-State Polish
- `quant_hunter/workspace_builders.py` makes the active recommend-workspace build path reapply the shared daily-pool header schema and adds default tooltips for "送审这只 / 去复盘 / 看交易计划" buttons.
- Cleaned a duplicated shared-header reapply in the legacy builder branch so the fallback construction path stays deterministic.
- Verification: `py_compile` and `unittest` passed.
## 2026-04-14 10:46 Default Copy Consolidation Pass
- Ran the desktop product entry (`app_qt.py`) for a live startup check; the window launched within the observation window without startup errors.
- `quant_hunter/ui_config.py` now owns shared default copy for recommend status, empty-state guidance, recommend focus, trade-plan focus, order focus, and broker status.
- `app_qt.py` switches scattered default labels and normalization paths onto those shared constants, reducing future drift across recommend and broker workspaces.
- Verification: `py_compile` and `unittest` passed.
## 2026-04-14 07:32 Board Table Signature Guard
- `app_qt.py` Added signature guards for board candidates and monitor tables to skip rebuilds when data unchanged.
- `app_qt.py` Keeps selection and focus refresh intact while reducing table redraw cost.
- Verification: `py_compile` and `unittest` pending.
## 2026-04-14 07:45 Recommend Defaults Consistency
- `app_qt.py` unified legacy recommend focus metric defaults and summary card defaults to the latest terminal copy (waiting for mainline/plan/pulse/holding) to avoid mixed language across entry points.
- Verification: `py_compile` and `unittest` pending.
## 2026-04-14 07:58 Trade Plan And Refresh Copy Alignment
- `app_qt.py` unified trade plan focus defaults to "等待生成今日交易计划" across legacy entry points.
- `app_qt.py` aligned scanner refresh defaults to "等待市场快照建立" for consistent terminal wording.
- Verification: `py_compile` and `unittest` pending.
## 2026-04-14 08:24 Selected Stock Logic + News
- Added per-stock hype logic/theme/news support: recommendation rationale/profile notes/scan reason feed into detail panels and summary badges.
- News catalysts now accept optional source/url columns and tooltips/news summaries render source + time when available.
- Verification: `py_compile` and `unittest` passed.
## 2026-04-14 08:42 Entry/Exit Price Tagging
- `daily_pool_table` adds a “买卖价” column showing suggested entry/target prices for each candidate.
- Layout specs updated so the new column has a stable width and scroll behavior.
- Verification: `py_compile` and `unittest` passed.
## 2026-04-14 08:55 Risk/Reward Tooltip Boost
- Daily pool tooltip now shows entry/stop/target plus calculated risk-reward ratio when available.
- Helps users quickly judge “收益最大化” potential without opening detail panels.
- Verification: `py_compile` and `unittest` pending.
## 2026-04-14 18:14 Broker Execution Deck Alignment
- `app_qt.py` adds `_qh_broker_execution_deck_v50` and plugs it into the active submission-focus refresh path, so the broker middle metrics and the execution text panel now share one compact terminal summary language.
- The execution focus card now aligns `股票 / 闸门 / 风险 / 去向` with the actual submission record, making the middle strip read more like an institutional terminal status deck instead of four unrelated labels.
- `tests/test_core.py` adds a focused regression test for the execution deck mapping to pin the headline, accents, and route copy for the broker execution state.
- Verification: `py_compile` passed and `python -m unittest discover -s tests -v` passed (`164` tests).

## 2026-04-14 20:31 Broker Action Strip Rhythm
- `app_qt.py` adds `_qh_broker_action_strip_labels_v52`, so the broker middle quick actions now switch visible labels with the execution stage: blockers surface as `处理阻塞`, in-flight orders shift to `跟前排单`, and post-fill follow-up shifts to `看前排复盘`.
- This keeps the middle action row aligned with the execution copy and makes the workbench feel more like a live terminal strip instead of four static utility buttons.
- `app_qt.py` also resets the broker action strip back to stable default labels in empty-state / non-focus paths, so users do not see stale execution-stage wording after leaving a submission record.
- `app_qt.py` adds `_qh_broker_primary_cta_labels_v53` and `_qh_broker_primary_cta_tooltips_v54`, so the two primary CTAs now also follow the live execution state: initial state shows `生成委托链路 / 确认并提交委托`, normal ready state shifts to `重算委托链路 / 核对后提交`, and blocker state shifts to `按阻塞重生成 / 修正后提交`.
- The CTA tooltips now explain the current action reason in the same terminal language instead of staying on static generic hints, which tightens the recommend-to-trade chain and reduces “为什么现在是这个按钮”的疑惑感。
- `app_qt.py` restores lightweight compatibility hooks for recommend focus-card refresh and relaxes a few recommend-focus helpers to better tolerate test and fallback window stubs.
- `tests/test_core.py` adds focused regression coverage for the stage-based action-strip labels, the stage-aware CTA texts/tooltips, and the empty-state reset path.
- Verification: `py_compile` passed and `python -m unittest discover -s tests -v` passed (`172` tests).

## 2026-04-18 20:35 Regression Baseline Recovery + Market Transparency
- `quant_hunter/ui_window_broker_patches.py` fixes the broker execution-detail toggle so the detail status label no longer gets overwritten by setup-drawer copy; folded and expanded states now stay semantically correct.
- `app_qt.py` restores recommendation-aware market panels: the execution panel again surfaces catalyst-driven price-plan context, the capital panel now exposes `消息层级 / 来源 / 摘要`, and the decision panel explicitly shows `炒作逻辑`.
- `app_qt.py` upgrades `market_breadth_text` with a visible `焦点` marker while preserving the recommended next-workspace guidance, improving recommend-to-trade continuity from market news cards.
- `app_qt.py` tightens compact overview geometry by capping `right_intel_tabs` height in short windows, removing redundant overflow without reducing information density.
- `app_qt.py` hardens `_apply_readability_override_v29` to always append its overview contrast selectors into the live stylesheet, restoring the expected compact-info tab contrast in runtime and tests.
- Verification:
- `python -m py_compile app_qt.py tests\test_core.py quant_hunter\ui_window_broker_patches.py`
- `python -m unittest discover -s tests -v` passed (`376` tests)
- Next: continue on high-frequency refresh cost, focusing on overview/market side-panel signature guards and avoiding redundant Qt text/table repaints during repeated intraday refresh.

## 2026-04-18 20:52 Overview / Market Refresh Signature Guards
- `app_qt.py` adds `_market_depth_signature_v6`, so repeated intraday calls to `_qh_populate_market_depth_texts_v5` now skip all three QTextEdit updates when rows and linked catalyst context are unchanged.
- `app_qt.py` adds `_overview_side_signature_v6`, so `_qh_refresh_overview_side_panels_v5` no longer rewrites the overview side-rail text blocks on identical market inputs; it still refreshes the source-status panel so runtime state remains visible.
- `tests/test_core.py` adds focused regression coverage for both signature guards and confirms the existing market-breadth guidance path still renders correctly.
- Verification:
- `python -m py_compile app_qt.py tests\test_core.py`
- targeted `unittest` cases passed for the new signature guards and existing market-breadth coverage.
- Next: continue on `_qh_update_market_text_panels_v5` and adjacent overview focus-card refreshes, aiming to skip repeated recommendation/snapshot text rebuilds during high-frequency polling.

## 2026-04-18 21:18 Market Panel / Focus Card Signature Guards
- `app_qt.py` adds `_market_text_panel_signature_v6`, so repeated calls to `_qh_update_market_text_panels_v5` now skip four overview/market text panel rewrites when recommendation, snapshot, and linked news context are unchanged.
- `app_qt.py` adds `_overview_focus_card_signature_v5`, so `_qh_refresh_overview_focus_cards_v4` no longer repeats the same summary-card `set_data` work for identical recommend / snapshot / empty states.
- `app_qt.py` adds `_market_source_status_signature_v2`, reducing redundant source-status text and summary-card refreshes during repeated overview polling while still updating when cache state, pool count, mode, or error context changes.
- `tests/test_core.py` adds focused regression coverage for all three guards and keeps the existing news-tier / recommend-focus / source-status scenarios green.
- Verification:
- `python -m py_compile app_qt.py tests\test_core.py`
- `python -m unittest discover -s tests -v` passed (`381` tests)
- Next: continue into `market_pool_table` and adjacent binder paths to check whether the overview table refresh is still doing avoidable full-row rebuilds.

## 2026-04-18 21:34 Scanner Focus / Summary Card Guards
- `app_qt.py` adds `_scanner_focus_cards_signature_v1`, so repeated scanner-focus card refreshes now skip the four metric-label updates when the target symbol, signal, recommendation linkage, and board snapshot are unchanged.
- `app_qt.py` adds `_scanner_summary_cards_signature_v1`, so repeated scanner summary-card refreshes no longer rewrite scan/watch/summary/monitor counters and accents when the linked symbol context has not changed.
- `app_qt.py` also switches `_populate_existing_views_from_market` to `_set_label_text_if_changed` for recommend status and recommend focus labels, trimming two remaining direct label rewrites in the market-result landing path.
- `tests/test_core.py` adds focused regression coverage for both scanner guards and also makes the existing scan-warning status test self-sufficient by creating its own `QApplication`, so it can run standalone.
- Verification:
- `python -m py_compile app_qt.py tests\test_core.py`
- targeted `unittest` cases passed for scanner focus cards, scanner summary cards, and scan-warning status.
- Next: continue checking whether market-result binder paths still have any direct label rewrites or avoidable cross-workspace cascades after the existing table signatures.

## 2026-04-18 21:53 Theme Combo Guards + Tooltip Write Dedup
- `app_qt.py` adds `_recommend_theme_option_signature_v1` and `_market_theme_option_signature_v1`, so the recommend / overview theme filter combos no longer `clear + addItem` on every identical refresh.
- `app_qt.py` resets the market-theme signature in the empty/normalize paths that manually clear the combo, preventing stale-signature false positives after builder/compact resets.
- `app_qt.py` upgrades `_qh_set_tooltip_v7` to write only when tooltip text actually changes, reducing repeated tooltip churn across recommend-focus status and related helper flows.
- `tests/test_core.py` adds focused regression coverage for both theme-combo guards and the tooltip helper dedup behavior.
- Verification:
- `python -m py_compile app_qt.py tests\test_core.py`
- `python -m unittest discover -s tests -v` passed (`388` tests)
- Next: continue from the market-result landing path into recommend-focus and cross-workspace post-processing, looking for any remaining repeated summary rebuilds that are still outside existing signature guards.

## 2026-04-18 22:07 Recommend Focus Post-Processing Guard
- `app_qt.py` adds `_recommend_focus_panel_signature_v39`, so `_qh_refresh_recommendation_focus_panels_v38` now skips repeated hype-logic/news-line rebuilds, news-button refreshes, and focus-label re-rendering when the same recommendation + news context is revisited.
- `tests/test_core.py` adds focused regression coverage for the new recommend-focus post-processing guard and keeps the existing recommend focus panel rendering scenario green.
- Verification:
- `python -m py_compile app_qt.py tests\test_core.py`
- targeted `unittest` cases passed for the new recommend-focus guard and the existing recommend-focus rendering path.
- Next: continue checking cross-workspace post-processing around recommend / scanner / overview focus chains, prioritizing places where identical symbol context still triggers repeated summary rebuilds.

## 2026-04-18 22:26 Focus Context Reuse In Banner / Shell Helpers
- `app_qt.py` lets `_qh_workspace_focus_capsule_v40`, `_qh_workspace_focus_capsule_html_v44`, `_qh_shell_focus_chip_html_v46`, and `_qh_update_shell_focus_hover_card_v49` accept precomputed focus context, so a single banner/header refresh no longer repeatedly resolves the same symbol / recommendation / execution context.
- `app_qt.py` updates `_qh_refresh_workspace_focus_banners_v40` and `_refresh_shell_header` to pass one shared focus-context snapshot through those helpers, trimming repeated focus resolution during high-frequency status refresh.
- `tests/test_core.py` makes the existing workspace-focus-banner test self-sufficient by creating its own `QApplication`, keeping the banner/shell verification path reliable when run standalone.
- Verification:
- `python -m py_compile app_qt.py tests\test_core.py`
- targeted `unittest` cases passed for workspace focus banners and shell header focus chip sync.
- Next: continue down the cross-workspace focus chain, especially places where repeated status refresh still re-enters detail/recommend/scanner summary helpers for the same active symbol.

## 2026-04-18 22:43 Monitor Summary Signature Guard
- `app_qt.py` adds `_monitor_summary_signature_v2`, so `_refresh_monitor_summary` now skips repeated intraday summary rebuilds and avoids re-triggering downstream scanner focus/summary refreshes when the same symbol context, scan signal, recommend context, and board linkage are unchanged.
- `tests/test_core.py` adds focused regression coverage for the new monitor-summary guard while preserving the scanner focus-card / summary-card guard coverage around it.
- Verification:
- `python -m py_compile app_qt.py tests\test_core.py`
- `python -m unittest discover -s tests -v` passed (`396` tests)
- Next: continue checking same-symbol status chains, especially recommend / detail summary refreshes that still rebuild text after identical active-symbol transitions.

## 2026-04-18 22:57 Detail Workspace Signature Guard
- `app_qt.py` adds `_detail_workspace_signature_v2`, so `_qh_refresh_detail_workspace_panels` now skips repeated detail-summary metric updates and decision/execution/conclusion text rebuilds when the same symbol, recommendation, execution row, selected signal/trade, and strategy-history context are unchanged.
- `tests/test_core.py` adds focused regression coverage for the new detail-workspace guard and keeps the existing order-focus-symbol detail refresh scenario green.
- Verification:
- `python -m py_compile app_qt.py tests\test_core.py`
- `python -m unittest discover -s tests -v` passed (`397` tests)
- Next: continue on the remaining same-symbol status chain, prioritizing recommend-status / decision-summary style post-processing where identical focus context may still trigger secondary UI work.
