# P4 坐标与地理编码设计

## 来源与边界

本设计落实项目基线中的 P4 Coordinate / Geocoding Pipeline。P4 只处理已有 `candidate_records`，不调用真实地图 API，不开展北京/广东试点，不修改或发布 `facilities`，不写正式 `facility_locations`。坐标使用单独的 `candidate_locations` 暂存表；只有 provider policy 明确允许持久化时才保存返回坐标。CI 和本地集成测试仅使用 FixtureGeocoder。

## 组件

- `eye_collector.geocoding.models`：provider policy、provider-independent result、error/precision/status 枚举及统计类型。
- `providers`：`GeocodeProvider` 协议和完全离线的 `FixtureGeocoder`。Fixture adapter 使用已有 `HttpClient`，复用 timeout、429/5xx/transport retry、rate limit 和响应大小限制。Provider 返回类型化结果，不访问数据库。
- `coordinates`：WGS84/GCJ02 转换边界。WGS84 原样返回；GCJ02 使用单独可测试的逆转换后标记存储 WGS84；未知系统拒绝写入可验证坐标。
- `validation`：检查世界和中国坐标范围、null island、区域代码祖先/后代关系以及 rooftop/building 精度。区域一致性以 `regions.parent_id` 链为准，不比较地区中文名或 adcode 前缀。
- `pipeline`/`repository`：用地址及显式行政区查询候选；地址指纹覆盖 normalized address、行政区、provider 和 provider version；同候选同 provider/version/address 的请求幂等，地址变化产生可追溯新行。provider policy 不允许持久化时，不调用 provider，仅写无响应内容的 `POLICY_BLOCKED` 记录。dry-run 执行请求与校验但不插入记录。
- CLI `geocode`：限定 provider 为 fixture，支持 limit、candidate-id 和 dry-run，输出稳定 JSON 统计。

## 数据库与访问控制

Migration 006 增加 `candidate_locations`，复合外键回链 candidate 与其 `source_record`，保存 provider/version/result ID、规范地址和行政区指纹、返回地址/行政区、原始和存储坐标系、WGS84 坐标、精度、验证结论/原因、结果类型、来源元数据、请求/返回/创建/核验时间。唯一键由 candidate、provider、provider version、地址指纹和 provider-result 指纹构成；地址变化或 provider 结果变化产生可追溯新行。`verified` 只允许 WGS84、合法中国坐标、父子行政区一致且精度 rooftop/building。

单独的 `eye_geocode` NOLOGIN 角色可读候选、地区、必要来源证据及已有位置，并仅能插入/读取 `candidate_locations`。不授予 source_records、facilities、facility_locations、发布视图或来源审批写权限。另建 `etl_source_dispositions` 保存 P3 对确定性终止跳过（当前 missing_name）的处理结果；按 source_record + pipeline version 唯一，不触碰原始快照。

## P3 匹配查询优化

替换每个候选读取全部 facility targets 的路径为一个数据库过滤查询：可信登记号精确条件，或规范名称 + 显式行政区精确条件；只有筛选后的目标传给原 matcher。原 P3 matcher 的优先级、院区处理、状态与 reason 保持不变。查询由候选的可信登记号/名称区划组合缩小，并为 name-region 查询增加组合索引；数据库测试检查该索引存在。

## 失败与重试

错误分类为 `NO_RESULT`、`AMBIGUOUS_RESULT`、`REGION_MISMATCH`、`LOW_PRECISION`、`INVALID_COORDINATE`、`RATE_LIMITED`、`PROVIDER_ERROR`、`POLICY_BLOCKED`。只有 P2 HTTP 层识别的 429、5xx 和 timeout/transport error 重试；语义结果不重试。许可不允许持久化时不得调用 provider 或记录任何返回坐标；只记录无坐标的 `POLICY_BLOCKED` 审计结果。verified 要求 rooftop/building、accuracy 0–100m、有效中国范围坐标及可验证行政区层级。语义失败均进入 needs_review/rejected 暂存状态，不能进入可发布坐标。

## 验证

测试涵盖地址+行政区请求、WGS84 与 GCJ02 转换、区域层级关系、坐标范围/null island、中国范围、精度、全部错误分类、P2 retry、许可拦截、dry-run、地址/结果指纹幂等、P3 terminal skip、facility 查询候选集等价、DB 外键/唯一/最小权限和无正式位置/发布写入。迁移和 P1/P2/P3 测试均通过临时 PostGIS 执行。CI 仅走 fixture transport，不访问公网。
