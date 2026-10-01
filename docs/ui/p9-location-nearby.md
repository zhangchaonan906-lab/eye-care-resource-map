# P9 Browser Location and Nearby Facilities

## Location lifecycle

The page calls `navigator.geolocation.getCurrentPosition` only after the user activates “定位到我”. It does not start location access on page load and does not use `watchPosition`. Options are `enableHighAccuracy: false`, a 10-second timeout, and a 5-minute maximum age. The location provider returns WGS84 coordinates, which are used directly without a coordinate-system conversion.

The control presents `idle`, `requesting`, `granted`, `denied`, `unavailable`, `timeout`, `error`, and unsupported-browser states. A denied permission displays “定位权限未开启，你仍可以搜索或手动浏览地图。” and provides an explicit retry button; it never retries automatically. Browsers without Geolocation show “当前浏览器不支持定位”. Geolocation requires HTTPS in production; localhost is suitable for development.

Location coordinates are held in React state and the map adapter only for the current page session. The page does not write them to PostgreSQL, local storage, session storage, cookies, analytics, or application logs. Accuracy is not sent. A page refresh clears the location and marker.

## Map and nearby list

The MapLibre adapter keeps the current-location GeoJSON source separate from the clustered facility source. It renders a blue dot with a contrasting outer ring and uses no external image. On location success the camera moves to at least zoom 13. The existing viewport query continues independently; nearby results are kept as their own list and merged with viewport facilities only for map display.

The nearby list defaults to 10 km and supports 3, 5, 10, 20, and 50 km. Radius and existing category changes trigger a fresh query. Each new request aborts the previous request, and an aborted or stale response cannot replace current results. Results use the API's distance order and display meters below 1 km or kilometers with one decimal place above that threshold. Selecting a result uses the existing facility selection, detail panel, and map camera flow.

## Fallback and result states

Location denial or failure leaves name search, category, region-code filtering, and manual map dragging available. The page explains “可通过地区筛选或拖动地图继续浏览”. A complete national city metadata set is not available, so the city selector is deferred rather than populated with a partial hardcoded list.

An empty nearby response says “附近 N 公里暂无已发布眼科医疗机构”, which describes the published dataset and does not claim that no eye-care provider exists. An API failure only replaces nearby content with “附近机构加载失败，请稍后重试”; viewport facilities, search, and manual browsing remain usable. If the API reports more results than the UI limit, the page says “附近机构较多，可缩小搜索半径”.

## Scope boundary

P9 does not persist locations, import real data, call a geocoder or external map provider, write production coordinates, publish facilities, or provide navigation. The existing development placeholder basemap remains in use.
