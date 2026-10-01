# P8 全国眼科医疗资源地图界面

## 页面与组件

- 路由：`/resources/eye-hospitals`
- 页面容器：`EyeHospitalsClient`
- 组件：`SearchAndFilters`、`MapCanvas`、`FacilityList`、`FacilityDetailPanel`、`LocationControl`
- 桌面端为左侧搜索/过滤/列表、右侧地图；窄屏将地图放在上方，搜索、筛选和列表留在下方。列表项是可键盘操作的原生按钮，详情提供可聚焦关闭按钮。

页面显示免责声明：“信息供查询，实际门诊与服务请以医院官方信息为准。”列表和详情只显示公开 UI 字段，不渲染设施内部 ID、原始来源对象、法人信息或证据计数。来源外链仅允许 HTTPS，并使用 `target="_blank" rel="noopener noreferrer"`；来源内容作为文本显示，不解析 HTML。

## API 与视窗请求

- `GET /api/meta/categories`：加载唯一的分类 ID/中文标签映射，并从只读 `publishedFacilityCount` 元数据读取已发布数量；`unknown` 使用弱化的“待核验”样式。
- `GET /api/facilities?bbox=west,south,east,north&zoom=...&limit=...`：地图初次 load 和 moveend 更新视窗时请求；类别和地区代码作为可选筛选参数。
- `GET /api/search?q=...&match=prefix&limit=20`：搜索输入停止 300ms 后请求；结果展示名称、地址和地区。选择结果后飞到其坐标并请求详情。
- `GET /api/facilities/{id}`：选择点位或列表项目时读取详情。

视窗和搜索均使用 300ms debounce、`AbortController` 和 effect 清理。更换视窗、缩放或筛选会终止前序请求，并通过活动请求标志阻止迟到响应写入状态。视窗变化时不沿用旧 cursor。设施分页每页最多 500 条；客户端最多累计 1,200 条。若达到上限时服务端仍提供 `nextCursor`，页面丢弃该不完整集合并提示“当前区域机构较多，请继续放大地图”。

P7 的 `MIN_FACILITY_DETAIL_ZOOM=7` 是唯一缩放阈值。低于 7 时页面清空点位且不请求 `/api/facilities`，显示“放大地图查看附近眼科医疗资源”。API 返回 `VIEWPORT_TOO_LARGE` 时页面显示放大提示，不用部分点位做 cluster。当前视窗没有记录时显示空状态；API 错误提供重试入口。MapLibre 初始化失败会显示底图错误，同时保留可用的搜索与列表区域。

## 地图与聚合

`MapCanvas` 将公开设施经纬度作为 WGS84 位置交给 MapLibre，并使用本地 GeoJSON source：`cluster=true`、`clusterMaxZoom=17`、`clusterRadius=48`。点图层用于单个机构，cluster 圆和数量图层用于当前已完整加载的局部视窗。点击 cluster 会读取 expansion zoom 并缩放；点击点位选中同一列表项并打开详情；点击列表飞到地图坐标并选中；空白地图清除选中状态。

图层依赖 P7 API 的局部 viewport 结果。页面不在全国/低 zoom 明细上创建伪聚合，也未新增 server-side cluster API。

## 底图配置与上线边界

`src/lib/basemap/types.ts` 定义 `BasemapConfig`（`styleObject`、`attribution`、`coordinateSystem` 和环境标记）；`config.ts` 当前提供只有 background layer 的本地 MapLibre style。地图右上角标记“开发占位底图”，角落署名“开发占位底图 · 无在线瓦片”。配置坐标声明为 WGS84；不做坐标转换，不含任何第三方瓦片、地图样式或生产 provider URL。

生产底图接入前，需单独确认供应商许可、服务地区、坐标体系、token 配置、署名要求和适用的互联网地图合规要求，再通过 `BasemapConfig` 替换本地 style。当前占位地图可验证点位、聚合、交互和无数据页面，不提供道路、行政区或地名底图，因此不应作为生产地图发布。

## 空状态与范围

- 低 zoom：提示放大；不取设施明细。
- `VIEWPORT_TOO_LARGE`：提示缩小视窗范围/继续放大。
- 全库计数为 0：显示“当前暂无已发布机构数据”。全库计数大于 0 且当前查询为空：显示“当前视窗内暂无已发布机构”，不据此推断其他地区的数据覆盖状态。
- 请求失败：显示 API 错误与重试；已取消请求不显示错误。
- 搜索零结果：显示“没有找到匹配的机构”。
- 详情 404：显示“该机构详情暂不可用”。
- 底图失败：显示地图画布错误，列表和搜索仍可使用。

## P8 范围外

当前没有浏览器定位、附近半径 API、导航、行政区树、后台、真实数据导入、新地理编码或全国抓取。`LocationControl` 仅展示 P9 占位文案。

## 测试

UI 组件测试在 jsdom 中运行并 mock 地图适配器，不建立真实 MapLibre WebGL 或网络瓦片请求。覆盖空状态、低 zoom 请求抑制、viewport success、过大 viewport、筛选重查、取消旧请求、列表/地图联动、详情成功与 404、来源链接安全属性、分类和搜索，以及内部字段不展示。构建检查还会验证 App Router 页面和 MapLibre 浏览器端动态载入。
