import Link from "next/link";
import type { PublicFacility } from "../../lib/public-api/types";
import { formatFacilityCategory, formatVerifiedDate, safeSourceUrl } from "./facility-presentation";

type Props = { facility: PublicFacility; labels?: Map<string, string>; mapLink?: boolean; detailLink?: boolean };

function FacilitySources({ facility }: { facility: PublicFacility }) {
  if (!facility.attribution.length) return <>公开来源信息暂缺</>;
  return <ul>{facility.attribution.map((source, index) => {
    const href = safeSourceUrl(source.url);
    return <li key={`${source.name}-${index}`}>
      {href ? <a href={href} target="_blank" rel="noopener noreferrer">{source.name}</a> : <span>{source.name}</span>}
      {source.updatedAt && <span>（更新于 {formatVerifiedDate(source.updatedAt)}）</span>}
    </li>;
  })}</ul>;
}

export function FacilityDetailContent({ facility, labels = new Map(), mapLink = false, detailLink = false }: Props) {
  return <>
    <dl>
      <dt>机构类型</dt><dd>{formatFacilityCategory(facility.category, labels)}</dd>
      <dt>地址</dt><dd>{facility.address}</dd>
      <dt>地区</dt><dd>{facility.region.name}</dd>
      {facility.hospitalLevel && <><dt>医院级别</dt><dd>{facility.hospitalLevel}</dd></>}
      {facility.hospitalGrade && <><dt>医院等级</dt><dd>{facility.hospitalGrade}</dd></>}
      <dt>眼科信息</dt><dd>{facility.ophthalmology.status === "verified" ? "已核验眼科信息" : "眼科信息待核验"}</dd>
      <dt>最近核验</dt><dd>{formatVerifiedDate(facility.lastVerifiedAt)}</dd>
      <dt>来源</dt><dd><FacilitySources facility={facility} /></dd>
    </dl>
    <p className="eye-map__disclaimer">信息供查询，实际门诊与服务请以医院官方信息为准。</p>
    {detailLink && <p><Link href={`/hospitals/${facility.id}`}>查看完整详情</Link></p>}
    {mapLink && <p><Link href={`/resources/eye-hospitals?facility=${encodeURIComponent(facility.id)}`}>在地图中查看</Link></p>}
  </>;
}
