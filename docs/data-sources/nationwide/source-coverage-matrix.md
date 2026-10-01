# P6-A 全国数据来源与覆盖盘点

盘点日期：2026-10-01。此文件是来源发现和覆盖规划记录，不构成数据许可、采集授权或全国覆盖声明。来源状态 `UNKNOWN` 必须 fail closed。只记录已能从官方来源页核实的信息；空白/“未核实”表示没有完成核查，不代表字段不存在。

## 状态定义

- 来源准入状态仅使用 `APPROVED`、`MANUAL_ONLY`、`UNKNOWN`、`REJECTED`、`STALE`。`APPROVED`/`MANUAL_ONLY` 仅适用于既有 P5 评审结论，不能从“网页可访问”推导。
- 描述分组仅使用 `STRUCTURED_OFFICIAL`、`OFFICIAL_UNSTRUCTURED`、`OFFICIAL_QUERY_ONLY`、`REGISTERED_DOWNLOAD`、`NO_USABLE_SOURCE`、`REQUIRES_FURTHER_REVIEW`。
- 覆盖粒度仅为 `province_wide`、`city_only`、`district_only`；直辖市完整市域可记作其省级规划单元，但需明确其来源实际覆盖范围。
- “官方数据平台显示无条件开放”只描述平台元数据，不自动证明长期存储、应用展示、原始数据转移/再分发的权利。

## 省级地区覆盖表

| 地区 | 代码 | 当前发现与官方核查入口 | 覆盖/分组 | 来源状态 | 备注 |
|---|---:|---|---|---|---|
| 北京 | 110000 | P5 北京市公共数据开放平台“定点医疗机构信息” | province_wide（P5 受控样本，不代表已全量导入）/ STRUCTURED_OFFICIAL | APPROVED | 仅按既有来源评审结论；已导入 50 条并 QA。不得推称北京全量覆盖。 |
| 天津 | 120000 | [三级医疗机构基本信息](https://open.data.tj.gov.cn/sjj/1be22c6e54be4f3e85989bc60ae28bd8.htm) | province_wide（直辖市）/ STRUCTURED_OFFICIAL | UNKNOWN | 页面标注 XLS、名称/地址/邮编/区县、年度、无条件开放；可见 2026-08 文件。存储/展示/再分发权、实际记录数及精确字段待审。 |
| 河北 | 130000 | [京津冀公共数据协同目录](https://data.beijing.gov.cn/jjjxtsjkfzt/index.htm) 列出河北省医保局“定点医疗机构信息表” | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 目录列出省级提供方和下载入口，但未核实原始发布平台、实际覆盖、schema、记录数、更新日及协议；聚合目录不能替代源平台权利审查。 |
| 山西 | 140000 | [国家医保服务平台](https://fuwu.nhsa.gov.cn/)地方服务入口；省级卫健/医保开放目录待检 | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 目前仅确认查询入口，不确认完整名录下载/API 或再利用许可。 |
| 内蒙古 | 150000 | [自治区卫健委医卫机构查询](https://wjw.nmg.gov.cn/dataservice/wjw/index.action) | unknown / OFFICIAL_QUERY_ONLY | UNKNOWN | 查询类入口，不视为可批量获取或可复用数据集；导出和条款未核实。 |
| 辽宁 | 210000 | [国家医保服务平台](https://fuwu.nhsa.gov.cn/)地方服务入口；省级公开目录待检 | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 尚未核实可复现的官方机构名录文件/API。 |
| 吉林 | 220000 | [吉林省政府公开信息](https://www.jl.gov.cn/szfzt/szjl/gzcg/202309/t20230904_2511189.html)曾列二级以上公立医院等 | city/province 范围未核实 / OFFICIAL_UNSTRUCTURED | STALE | 公开页面为 2023 年清单，不能作为当前完整名录。需查现行平台/数据集。 |
| 黑龙江 | 230000 | 省级开放平台及卫健/医保名录待检 | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 未确认可用的官方结构化来源。 |
| 上海 | 310000 | [上海市公共数据开放平台](https://data.sh.gov.cn/)；2025 操作指南仅发现养老机构设置医疗机构等关联数据 | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 已发现医疗相关数据产品，但尚未验证全市医院目录、完整性及复用协议。 |
| 江苏 | 320000 | [江苏省医保局](https://ybj.jiangsu.gov.cn/)定点机构查询入口；南京有官方医疗机构目录 | city_only（南京）/ OFFICIAL_QUERY_ONLY | UNKNOWN | 南京市级目录不代表江苏全省；省级导出和权利待核实。 |
| 浙江 | 330000 | [浙江·数据开放](https://data.zjzwfw.gov.cn/dopServer/index.html)精选“二级及以上医疗机构基本信息” | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 平台有省级资源，但未核实该数据集具体地域范围；条目显示“数据使用申请”；[受限开放协议](https://data.zjzwfw.gov.cn/dopServer/static/agreement/%E6%B5%99%E6%B1%9F%E7%9C%81%E6%95%B0%E6%8D%AE%E5%BC%80%E6%94%BE%E5%B9%B3%E5%8F%B0%E5%8F%97%E9%99%90%E5%BC%80%E6%94%BE%E5%8D%8F%E8%AE%AE.pdf)要求具体申请/约束用途；尚未取得批准。 |
| 安徽 | 340000 | [国家医保服务平台](https://fuwu.nhsa.gov.cn/)地方服务入口；省级开放目录待检 | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 未核实医院目录的数据集与许可。 |
| 福建 | 350000 | 省级政务数据开放平台/卫健委数据公开目录待检 | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 未确认结构化医疗机构目录。 |
| 江西 | 360000 | 省级数据开放目录、卫健/医保入口待检 | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 未确认完整目录或授权方式。 |
| 山东 | 370000 | [山东省公共数据开放平台](https://data.sd.gov.cn/)；省数据条例区分无条件/有条件开放 | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 已找到地区级执业许可信息线索，但不能据此推断省级覆盖；逐数据集审查必要。 |
| 河南 | 410000 | [河南省医保公共服务平台](https://ggfw.ylbz.henan.gov.cn/tps-local/) | unknown / OFFICIAL_QUERY_ONLY | UNKNOWN | 公开查询服务不等同于可再利用的省级文件/API。 |
| 湖北 | 420000 | [湖北省卫健委数据开放](https://wjw.hubei.gov.cn/sjkf/) | province_wide（公开许可/统计目录；机构主目录未证实）/ OFFICIAL_UNSTRUCTURED | UNKNOWN | 有 2026 年医疗机构设置与执业登记行政许可公示，属公告流，不等价当前有效机构快照。 |
| 湖南 | 430000 | 省级数据开放平台及卫健/医保名录待检 | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 未确认可复现、可保留的机构目录。 |
| 广东 | 440000 | P5 深圳市开放平台“宝安区-医院基本信息” | district_only / STRUCTURED_OFFICIAL | APPROVED | 既有批准仅限宝安区 27 条来源；不代表广东省或深圳全市覆盖。 |
| 广西 | 450000 | 省级开放平台及卫健/医保名录待检 | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 未确认结构化全区目录。 |
| 海南 | 460000 | 省级政务数据开放平台、卫健/医保入口待检 | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 未确认来源许可和全省覆盖。 |
| 重庆 | 500000 | 市级开放平台及卫健/医保目录待检 | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 直辖市按省级规划单位处理；具体来源尚未核实。 |
| 四川 | 510000 | [四川省卫健委信息公开目录](https://wsjkw.sc.gov.cn/scwsjkw/xxgkml/zfxxgkmlgl.shtml) | unknown / OFFICIAL_UNSTRUCTURED | UNKNOWN | 目录入口不是医疗机构完整结构化名录；需继续检索数据集。 |
| 贵州 | 520000 | [贵州医保公共服务平台](https://fuwu.pubs.ylbzj.guizhou.gov.cn/hsa-pass-hallEnter/) | unknown / OFFICIAL_QUERY_ONLY | UNKNOWN | 查询/便民服务入口；数据下载与再利用权未核实。 |
| 云南 | 530000 | [云南省医保局](https://ylbz.yn.gov.cn/)异地联网定点医药机构查询 | unknown / OFFICIAL_QUERY_ONLY | UNKNOWN | 查询服务不等于可批量采集或可再分发。 |
| 西藏 | 540000 | 自治区卫健/医保及数据开放入口待检 | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 尚无已核实来源；需关注低频更新和行政区代码版本。 |
| 陕西 | 610000 | 省级公共数据开放平台及卫健/医保目录待检 | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 未核实可复现结构化名录。 |
| 甘肃 | 620000 | 省卫健/医保与公共数据开放目录待检 | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 医疗信息化/共享平台存在不代表公共再利用授权。 |
| 青海 | 630000 | [青海政务服务网定点医疗机构查询](https://www.qhzwfw.gov.cn/query_result_ydjy.html) | unknown / OFFICIAL_QUERY_ONLY | UNKNOWN | 可查询机构名称、等级、地址；导出/API、范围完整性和用途权限待核实。 |
| 宁夏 | 640000 | 省级数据开放目录及卫健/医保入口待检 | unknown / REQUIRES_FURTHER_REVIEW | UNKNOWN | 尚无已核实结构化公开来源。 |
| 新疆 | 650000 | [国家卫健委政务服务平台机构查询](https://zwfw.nhc.gov.cn/cxx/ywjgcx/cqzdjsyljg/)等；自治区目录待检 | unknown / OFFICIAL_QUERY_ONLY | UNKNOWN | 国家查询页覆盖的机构类别有限，不是新疆完整目录；兵团需另行识别边界和来源。 |

港澳台：`OUT_OF_SCOPE_PENDING_POLICY_REVIEW`。本阶段不推断法域、授权或地域代码的适用方式。

## 候选来源资格字段

| region / region_code | platform / provider / dataset | dataset page | coverage_level | records / updated | format / API / registration | access_policy / data_use / reuse / app display / raw transfer / redistribution / attribution / retention / automated / manual | ophthalmology / address / admin code / registration id / coordinates / coordinate system | source_status / group / notes |
|---|---|---|---|---|---|---|---|---|
| 天津 / 120000 | 天津市信息资源统一开放平台 / 市卫生健康委 / 三级医疗机构基本信息 | [官方数据集页](https://open.data.tj.gov.cn/sjj/1be22c6e54be4f3e85989bc60ae28bd8.htm) | province_wide（直辖市；范围仍需文件核验） | 页面展示 2026-08-20 文件；数量未核实 | XLS；页面有登录/注册入口，下载是否要求注册未核实 | 页面元数据显示“无条件开放”；存储、再使用、应用展示、原始转移/再分发、归属、保留期、自动访问、手动下载逐项均待协议审核 | 明确名称/地址/邮编/区县；眼科字段/区划码/注册号/坐标/坐标系待检查文件 | UNKNOWN / STRUCTURED_OFFICIAL / 每年；只可人工获取官方文件，禁止自动下载直至批准 |
| 河北 / 130000 | 京津冀协同目录展示 / 河北省医疗保障局 / 定点医疗机构信息表 | [官方协同目录](https://data.beijing.gov.cn/jjjxtsjkfzt/index.htm)（非源平台） | unknown（目录称省级；待源平台确认） | 未核实 | 页面有下载入口；实际格式、是否需注册未知 | 开放属性和服务条款未知；所有再利用、展示、存储、归因、保留、访问政策未知 | 全部字段待源页面/文件确认；名称地址可能性不能当作已核实 | UNKNOWN / REQUIRES_FURTHER_REVIEW / 必须找到河北源平台并核实条款、字段、下载复现性 |
| 浙江 / 330000 | 浙江·数据开放 / 省级平台 / 二级及以上医疗机构基本信息 | [官方平台](https://data.zjzwfw.gov.cn/dopServer/index.html)（搜索精选项） | unknown（具体数据地域范围待元数据确认） | 条目日期 2025-01-03；数量未见 | 条目为“数据使用申请”；格式/API/注册状态待核实 | 受限开放协议存在，必须获得数据主体批准；存储、产品展示、原始传递、再分发、归因、保留与后续撤回需在具体协议中逐项确认 | schema 未验证；不能推定有眼科、地址、行政码、注册号或坐标 | UNKNOWN / REQUIRES_FURTHER_REVIEW / 未取得申请批准前禁止导入 |
| 国家 / N/A | 国家卫健委政务服务平台 / 主管部门 / 分类医疗机构查询 | [医卫机构查询](https://zwfw.nhc.gov.cn/cxx/ywjgcx/cqzdjsyljg/) | 多省但仅特定资质类别 | 页面查询可见结果数；非机构总量 | 在线查询；API/导出及注册要求未核实 | 查询页面不授予抓取、长期存储、转移或再分发权；全部待审 | 页面含机构名、地址、主营科室、地区；仅限定类别，不能做主名录；坐标系无 | UNKNOWN / OFFICIAL_QUERY_ONLY / 仅作为核验线索 |

## 盘点结论与证据限制

已找到明确官方结构化名录页面的候选数有限；对其余地区，本次记录的是官方核查入口或待查状态，不宣称“没有数据源”。国家卫健委查询、医保定点查询、行政许可公示和公开目录分别有类别/状态/时效边界，不能直接合并成全国完整医院清单。

可直接支持具体事实的官方页面：天津数据集元数据明确 XLS、无条件开放、字段和更新频率；浙江平台明确省级资源与医疗机构条目及使用申请；河北协同目录明确数据提供方和资源名；湖北数据开放页列出行政许可公示；国家卫健委提供分类机构查询。上述信息不等于权利批准。

## 下一轮核查优先级

1. 对天津、河北、浙江取到官方元数据/协议样本，由数据提供部门逐项确认保存、内部处理、产品展示、原始转移和撤回后的保留义务。
2. 逐个省级公共数据开放平台搜索“医疗机构/医院名录/执业登记/定点医疗机构”，保存具体数据集页面、字段字典、授权协议、更新时间与下载方式。
3. 对任何有条件开放、登录、验证码、付费、403 或平台限制的来源停止自动访问，不尝试绕过；可申请正式人工下载授权。
4. 任何文件下载后先检查 provenance、hash、region、schema 与小样本 QA；来源变化或撤回时停止导入并按已评审 retention workflow 处理。
