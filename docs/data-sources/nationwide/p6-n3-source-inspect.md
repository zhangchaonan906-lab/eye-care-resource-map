# P6-N3 全国第二批医疗机构登记来源快速验证

检查日期：2026-10-02
分支：`p6-n3-registration-source-inspect`

本阶段仅使用政府/卫健委公开页面和官网直接附件。没有登录、绕验证码、枚举隐藏接口、导入生产数据或修改来源准入状态。每个候选均按快速验证处理；遇到无法通过普通页面操作的环节即停止。

## 来源结果

### 1. 广州市医疗机构执业许可信息

- Status：`NOT_CONFIRMED`（只找到 2025 年度市级公共数据开放计划中的数据集条目，未确认现行详情页）
- Official Provider：广州市卫生健康委员会
- Official URL：[2025 年度广州市本级公共数据开放计划（PDF）](https://zsj.gz.gov.cn/attachment/7/7926/7926428/10526524.pdf)
- Open Status：无条件开放（计划条目）
- Updated At / Record Count：计划未提供当前更新日期或记录数
- Formats：JSON、XML、CSV、XLS、XLSX、RDF（计划条目）
- Download Available / Login Required / Application Required：当前详情页和附件下载流程均未确认
- Coverage：计划名称为广州市；不能据此确认完整覆盖范围
- Fields explicitly listed：机构名称、行政区划、地址、邮政编码、机构级别、登记号、诊疗科目名称、机构类别等
- Eye-evidence capable：YES（计划字段含诊疗科目名称）
- Result：`GUANGZHOU_CURRENT_FILE_NOT_CONFIRMED`

### 2. 广州市中医医疗机构执业登记信息

- Status：`NOT_CONFIRMED`（只找到 2025 年度开放计划条目，未确认当前独立数据集详情页）
- Official Provider：广州市卫生健康委员会
- Official URL：[2025 年度广州市本级公共数据开放计划（PDF）](https://zsj.gz.gov.cn/attachment/7/7926/7926428/10526524.pdf)
- Open Status：无条件开放（计划条目）；Update Frequency：每半年
- Updated At / Record Count：计划未提供当前更新日期或记录数
- Formats：JSON、XML、CSV、XLS、XLSX、RDF（计划条目）
- Download Available / Login Required / Application Required：当前详情页和附件下载流程均未确认
- Coverage：计划名称为广州市；不能据此确认完整覆盖范围
- Fields explicitly listed：机构名称、机构第二名称、机构地址、诊疗科目名称、机构类别、登记号、机构级别等
- Eye-evidence capable：YES（计划字段含诊疗科目名称）

#### 关联但独立的广州卫健委公开附件（已下载，不等同于上述两个计划数据集）

- Dataset：广州市内广东省中医药局发证的医疗机构信息（数据截至 2026-07-13）
- Provider：广州市卫生健康委员会官网发布；页面标题说明为广东省中医药局发证机构
- Official Page：[广州卫健委附件发布页](https://wjw.gz.gov.cn/xxgk/zdlyxx/ylwsxx1/content/post_10908062.html)
- Official Attachment：[官网 XLSX 附件](https://wjw.gz.gov.cn/attachment/8/8050/8050361/10908062.xlsx)
- Acquisition Method：从官方发布页公开附件 href 直接下载（不要求登录；未调用 API）
- Downloaded At：2026-10-02 00:44:56 China Standard Time（本地文件时间戳）
- Original Filename：`广州市内广东省中医药局发证的医疗机构信息（数据截至2026年7月13日）.xlsx`
- Full Path：`C:\Users\72343\AppData\Local\EyeCareResourceMap\P6Downloads\Guangzhou\广州市内广东省中医药局发证的医疗机构信息（数据截至2026年7月13日）.xlsx`
- File Size：14,478 bytes
- SHA-256：`001C36E76D3656849D1858E69A987B98B9FDF7079EDF09FF621D89B8ADDA1DFD`
- Format / Integrity：XLSX ZIP package；archive integrity check passed；未发现 VBA macro part
- Sheets：3（`Sheet1`, `Sheet2`, `Sheet3`；仅 `Sheet1` 有数据）
- Header Row：2
- Rows / Columns：7 data rows / 14 columns
- Exact Headers：`序号`、`机构名称`、`登记号`、`机构第二名称`、`机构地址`、`法人姓名`、`负责人姓名`、`行政区划`、`机构类别`、`机构级别`、`经营性质`、`床位数`、`牙椅数`、`诊疗科目名称`
- Empty Names / Empty Addresses：0 / 0
- Duplicate Names / Duplicate Registration IDs：0 / 0
- Name + Address + Specialties：YES
- Eye Evidence：7 rows / 7 distinct names；只从 `诊疗科目名称` 中包含“眼科”的值提取
- Coordinates：无经纬度字段
- Data Scope：标题限定为“广州市内广东省中医药局发证的医疗机构”；不称为广州全部医疗机构
- Raw file remains outside the repository. No row dump or personal-name values are included here.
- Source Status：`UNKNOWN`；未写数据库，也没有变更准入状态

### 3. 夷陵区医院信息

- Status：`FOUND`（官方宜昌数据平台目录检索摘要列出该独立数据集；独立详情 URL 未能确认）
- Official Provider：宜昌市夷陵区卫生健康局
- Official Portal：[宜昌市公共数据开放平台](https://data.yichang.gov.cn/)
- Official Search Evidence：[官方平台目录结果页](https://data.yichang.gov.cn/kf/open/table/detail/1001440)列出“夷陵区医院信息”及其摘要
- Description fields：医院名称、医院类型、等级、诊疗科目、地址、电话
- Open Status / Updated At / Formats / Record Count：未从该数据集独立详情页核实
- Download Available / Login Required / Application Required：未验证
- Coverage：标题指向夷陵区；未推断区级数据覆盖完整性
- Eye-evidence capable：YES（官方目录摘要明确列出诊疗科目）
- File：未取得；没有从 SPA 页面推导接口或下载地址

### 4. 夷陵区诊所信息

- Status：`FOUND`（官方宜昌数据平台目录检索摘要列出该独立数据集；独立详情 URL 未能确认）
- Official Provider：宜昌市夷陵区卫生健康局
- Official Portal：[宜昌市公共数据开放平台](https://data.yichang.gov.cn/)
- Official Search Evidence：[官方平台目录结果页](https://data.yichang.gov.cn/kf/open/table/detail/1001440)列出“夷陵区诊所信息”及其摘要
- Description fields：诊所名称、地址、诊疗科目、联系电话
- Open Status / Updated At / Formats / Record Count：未从该数据集独立详情页核实
- Download Available / Login Required / Application Required：未验证
- Coverage：标题指向夷陵区；未推断区级数据覆盖完整性
- Eye-evidence capable：YES（官方目录摘要明确列出诊疗科目）
- File：未取得；没有从 SPA 页面推导接口或下载地址

### 5. 宜昌市医院信息（夷陵来源的 fallback）

- Status：`FOUND`（官方详情页）
- Dataset：宜昌市医院信息
- Provider：宜昌市卫生健康委员会
- Official URL：[官方数据集详情页](https://data.yichang.gov.cn/kf/open/table/detail/1001691)
- Open Status：无条件开放；数据分级：完全公开
- Coverage：官方页面标为全市
- Updated At：2026-07-10；Published At：2024-03-19
- Record Count：332
- Format：页面显示电子表格 XLSX，并列有 XLS、CSV、XML、JSON、RDF 下载格式
- Description fields：医院名称、人员信息、所在地区、级别等级、地址、联系电话、监督电话、是否医保定点医院、医院性质、医院简介等
- Specialty Field：没有在页面摘要中列出；不得产生 ophthalmology evidence
- Download Available：页面提供文件下载入口；本次没有完成普通 UI 点击
- Login Required：UNKNOWN（平台展示登录/注册入口；本次未验证直接下载是否需要登录）
- Application Required：页面元数据显示无条件开放
- Local File / Read-only Inspect：NO

## 官方下载操作记录

广州附件从广州卫健委公开页面直接链接下载成功。宜昌平台详情页由 SPA 渲染；当前会话的浏览器 UI 初始化返回 `failed to write kernel assets: 系统找不到指定的路径`。因此没有点击任何宜昌下载控件，也没有尝试读取页面内部接口或构造请求。该工具限制不等于来源或平台阻止下载。

广州规划中的两个精确数据集未找到当前详情页；关联的广州卫健委附件作为独立文件记录，不替代精确数据集的状态。夷陵医院/诊所只确认目录摘要，未确认其独立详情 URL。

## 只读 P3 内存预览

对上述广州卫健委附件按实际表头映射 `机构名称`、`机构地址`、`登记号`、`诊疗科目名称`，调用现有 P3 `parse_snapshot`、`normalize_record`、`extract_ophthalmology_evidence` 变换。没有调用数据库或持久化层；未提供行政区代码推断，也没有运行正式 entity matching。

| Metric | Result |
|---|---:|
| Raw Rows | 7 |
| Parsed | 7 |
| Skipped | 0 |
| Normalized Candidate Groups | 7 |
| Duplicate Normalized Name Groups | 0 |
| Eye Evidence Rows | 7 |
| Distinct Eye Candidate Names | 7 |
| Production / Persistent DB Writes | 0 |

该内存预览只证明当前附件能够进入 P3 的纯函数解析、文本标准化和明确科目证据提取步骤；不代表来源获批，也不等于创建或发布正式医院实体。

## 阶段边界与结果

- Production database writes：NO
- Persistent imports / `source_records` / `candidate_records`：NO
- Geocoder calls：0
- Facilities published：NO
- Source status changes：NO；所有新增来源仍为 `UNKNOWN`
- Production code changes：NONE
- Nationwide / bulk production crawling：NO；只下载一份官方公开附件作为本地只读样本

```text
P6-N3 STATUS: PARTIAL
Sources Attempted: 5
Real Official Files Obtained: 1 (related Guangzhou Health Commission attachment)
Files With Name + Address + Specialties: 1
Eye Evidence Capable Sources: Guangzhou planned license datasets, Guangzhou related attachment, Yiling hospital listing, Yiling clinic listing
In-memory P3 Preview: YES (7 parsed, 7 explicit eye evidence rows)
Production DB Writes: NO
Geocoder Calls: NO
Facilities Published: NO
Source Status Changes: NO
```

## Recommended Next Step

请在普通浏览器中打开夷陵区医院信息、夷陵区诊所信息和宜昌市医院信息的官方详情页，检查公开下载入口是否可直接使用；如从常规页面下载成功，将原始文件放到仓库外并提交给只读 inspect。另请确认广州卫健委官网的关联附件是否可作为独立辅助来源，避免将其误认为开放计划中的同名登记数据集。
