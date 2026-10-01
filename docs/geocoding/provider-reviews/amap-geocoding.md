# 高德地理编码：P5 Provider 评审

| 字段 | 审查记录 |
| --- | --- |
| provider | AMap / 高德开放平台 Web 服务地理编码 |
| API | Web 服务地理编码 API；本试点不调用 |
| coordinate system | 需以产品官方 API 文档明确声明为准；P5 未核实，因此 UNKNOWN |
| allowed fields | 查询结果字段许可及独立展示范围需按适用协议和具体产品确认 |
| persistent storage terms | 当前开放平台服务协议限制未经书面许可直接存储、缓存、抓取或用于数据库的相关服务内容；未取得本项目特定书面许可 |
| caching terms | 未取得适用于本项目的明确许可 |
| redistribution terms | 协议限制未经书面许可的传播/再分发；未取得本项目特定书面许可 |
| commercial-use requirements | 取决于运营主体与用途；需适用的许可/商用条款确认 |
| quota | 账户与 API 配额未配置、未核实 |
| rate limit | 产品及账户级限制未核实 |
| attribution | 适用服务的署名要求未核实 |
| reviewed_at | 2026-10-01 |
| decision | BLOCKED for persistent coordinate storage |

本项目 P0 基线决定在取得明确授权前不得持久化高德返回的地理编码、坐标或地址结果。此评审不主张高德服务不能在任何许可下使用；它只记录当前项目没有证明所需的持久化权利。P5 只允许本地 `FixtureGeocoder` 做合成离线测试，不能用它生成或冒充真实医院坐标。

依据：[高德地图开放平台服务协议](https://developer.amap.com/pages/terms/)将地理编码、坐标经纬度等列入“相关内容”，并限制未经书面许可的存储、缓存、抓取和数据库衍生使用（4.12、7.3）。调用产品前还须核对账号适用版本、具体 API 文档、商用许可和坐标系声明。
