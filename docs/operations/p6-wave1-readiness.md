# P6 Wave 1 来源资格与就绪状态

审查日期：2026-10-01。此表区分 `source_status`（来源资格）与 `access_policy`（获取方式）。`UNKNOWN` 不得升级为批准。三个候选目前均 `Ready For Pilot: NO`。

## Wave 1 汇总

| Region | Source | Source Status | Access Policy | Coverage | Official Provider | Rights Reviewed | Storage Allowed | App Display Allowed | Raw Redistribution | Attribution | Retention | Acquisition | File Obtained | Schema Inspected | Ready For Pilot | Blocking Issues |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 天津 | 三级医疗机构基本信息 | UNKNOWN | manual_only | 天津市级地域、仅三级机构子集；实际地理完整性待文件验证 | 天津市卫健委（官方数据集元数据） | PARTIAL：平台网站声明已核，项目关键权利未闭合 | UNKNOWN | UNKNOWN（平台应用成果审核；项目站外展示未明确） | YES（平台一般条款允许无条件开放资源传播/分享，受法律约束） | YES；“天津市信息资源统一开放平台” | UNKNOWN | 仅人工；数据页显示登录/注册，是否必需未核 | NO | NO | NO | 长期存储、站外 app 展示、商用和撤回后的既有副本处置未明确；需官方确认。 |
| 河北 | 定点医疗机构信息表 | UNKNOWN | unknown | unknown；医保定点不等于全体医疗机构 | 协同目录列河北省医保局；源平台提供主体未独立核实 | NO（仅来源线索/政策背景；无数据集许可） | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | authoritative dataset page 未找到；不得由协同目录下载替代 | NO | NO | NO | 河北原始平台页面、数据集条款、schema、覆盖及实际下载方式未核实；官方开放网首页本次返回 502。 |
| 浙江 | 二级及以上医疗机构基本信息 | UNKNOWN | application_required | 地域待数据集元数据/申请确认；仅二级及以上类别 | 省级平台精选项；具体数据提供主体待确认 | PARTIAL：审查通用受限开放协议，未获本项目具体批准 | UNKNOWN；期限须在具体协议填写 | NO（尚无指定 app/service 授权） | NO（未获授权不得向第三方提供原始数据） | YES when used/referenced；具体文本待确认 | 由具体协议设定；终止后需按约销毁 | 先提交真实项目申请并获批，之后才可按授权取得 | NO | NO | NO | 无申请批准；数据范围、处理、存储、app、期限、原始数据访问和撤回后销毁义务尚未具体约定。 |

## 天津详细结论

- **Source:** 天津市信息资源统一开放平台“三级医疗机构基本信息”。[数据集页](https://open.data.tj.gov.cn/sjj/1be22c6e54be4f3e85989bc60ae28bd8.htm)
- **Source Status:** `UNKNOWN`
- **Access Policy:** `manual_only`；当前页面支持 XLS 下载但是否需注册未核实，不运行自动获取。
- **Coverage:** 天津市级地域中的三级医疗机构子集；不能描述为天津所有医院或全部眼科资源。实际覆盖地区/完整性需 inspect 经许可取得的文件。
- **Official Provider:** 市卫生健康委。
- **Rights Reviewed:** 平台[网站声明](https://open.data.tj.gov.cn/xgxx/wzsm/index.htm)允许无条件开放资源自由利用、传播分享并要求平台来源署名；平台可以审核在平台发布的数据应用成果。它没有明确本项目站外 app 展示、长期存储期限、商用条件或数据下架后的副本义务。
- **File:** 未取得；**Schema:** 未 inspect。仅官方页面确认 XLS、名称/地址/邮编/区县字段摘要、每年更新；页面附件最新条目时间 2026-08-20，非数据统计时点证明。
- **Ready For Pilot:** NO。逐项结论见[天津来源审查](../data-sources/nationwide/reviews/tianjin-tertiary-medical-institutions.md)。

## 河北详细结论

- **Source:** 京津冀官方协同目录出现河北省医保局“定点医疗机构信息表”；[目录页](https://data.beijing.gov.cn/jjjxtsjkfzt/index.htm)。目录链接到河北开放网 `http://hebdata.hebyun.gov.cn/home`，本次对公开首页请求收到 HTTP 502。
- **Source Status:** `UNKNOWN`
- **Access Policy:** `unknown`
- **Authoritative Source Found:** NO（尚未取得河北原始数据集详情页/条款）；北京协同目录不能替代源平台资格审查。
- **Rights/Coverage/File/Schema:** 未核实。候选名录若属实也仅表示医保定点类别，不表示所有医疗机构。
- **Ready For Pilot:** NO。逐项结论见[河北来源审查](../data-sources/nationwide/reviews/hebei-designated-medical-institutions.md)。

## 浙江详细结论

- **Source:** 浙江·数据开放精选项“二级及以上医疗机构基本信息”；[官方平台](https://data.zjzwfw.gov.cn/dopServer/index.html)。平台显示“数据使用申请”。
- **Source Status:** `UNKNOWN`
- **Access Policy:** `application_required`
- **Application Approved:** NO；没有提交申请，也没有自动申请。
- **Rights:** [受限开放协议](https://data.zjzwfw.gov.cn/dopServer/static/agreement/%E6%B5%99%E6%B1%9F%E7%9C%81%E6%95%B0%E6%8D%AE%E5%BC%80%E6%94%BE%E5%B9%B3%E5%8F%B0%E5%8F%97%E9%99%90%E5%BC%80%E6%94%BE%E5%8D%8F%E8%AE%AE.pdf)要求申请表/需求清单明确数据，并绑定主体、用途和具体 app/service；未授权不得向第三方提供原始数据；引用需署名；期限、终止后销毁时间是项目协议字段。
- **Coverage:** 地域待核实；“二级及以上”不含所有级别医疗机构。
- **File/Schema:** 均未取得/检查。
- **Ready For Pilot:** NO。逐项结论见[浙江来源审查](../data-sources/nationwide/reviews/zhejiang-secondary-plus-medical-institutions.md)。

## 下一步准入闸门

1. 天津：先取得平台关于长期保存、外部地图展示/商用及来源下架后存量副本处理的书面确认；再人工取文件并登记 provenance，才做 inspect。
2. 河北：先找到能访问的河北官方原始数据集页，核实是否为社会公开、具体提供主体/字段/范围/协议和下载流程。不得从北京协同目录下载代替。
3. 浙江：由合法项目主体使用真实项目名称和真实用途申请，获得批准/签署项目协议后，按已批准范围取得文件；需把存储期、指定 app、署名、原始数据访问、终止后销毁等逐项写入协议。
4. 任一来源完成审查之后仍须另行执行官方文件 provenance、inspect、dry-run 和人工审阅；当前 PR 不执行 P6-C。

## 全局限制

- 本阶段没有真实文件、真实数据导入、真实地理编码或设施发布。
- `source_status` 只取 `APPROVED`、`UNKNOWN`、`REJECTED`、`STALE`；`access_policy` 只取 `automated_access_allowed`、`manual_only`、`application_required`、`query_only`、`unknown`。
- 无来源记录或文件数据不会自动转成 `pilot_ready`；必须按地区+来源+import run+QA 样本分别记录状态。
