"use client";

import type { PublicFacility } from "../../lib/public-api/types";

type Props = { facility: PublicFacility | null; loading: boolean; error: string | null; labels: Map<string, string>; onClose: () => void };

function safeSourceUrl(value: string): string | null {
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

export function FacilityDetailPanel({ facility, loading, error, labels, onClose }: Props) {
  if (!facility && !loading && !error) return null;
  const title = facility?.name ?? "机构详情";
  return (
    <section className="eye-map__detail" role="dialog" aria-modal="false" aria-label={`${title}详情`} aria-labelledby="facility-detail-title">
      <button className="eye-map__detail-close" type="button" aria-label="关闭详情" onClick={onClose}>关闭</button>
      {loading && <p role="status">正在加载机构详情…</p>}
      {error && <p role="alert">{error}</p>}
      {facility && <>
        <h2 id="facility-detail-title" tabIndex={-1}>{facility.name}</h2>
        <dl>
          <dt>机构类型</dt><dd>{labels.get(facility.category) ?? (facility.category === "unknown" ? "待核验" : "医疗机构")}</dd>
          <dt>地址</dt><dd>{facility.address}</dd>
          <dt>地区</dt><dd>{facility.region.name}</dd>
          {facility.hospitalLevel && <><dt>医院级别</dt><dd>{facility.hospitalLevel}</dd></>}
          {facility.hospitalGrade && <><dt>医院等级</dt><dd>{facility.hospitalGrade}</dd></>}
          <dt>眼科信息</dt><dd>已核验眼科信息</dd>
          <dt>最近核验</dt><dd>{new Date(facility.lastVerifiedAt).toLocaleDateString("zh-CN")}</dd>
          <dt>来源</dt><dd>{facility.attribution.length ? <ul>{facility.attribution.map((source, index) => {
            const href = safeSourceUrl(source.url);
            return <li key={`${source.name}-${index}`}>{href ? <a href={href} target="_blank" rel="noopener noreferrer">{source.name}</a> : source.name}</li>;
          })}</ul> : "来源信息暂缺"}</dd>
        </dl>
      </>}
    </section>
  );
}
