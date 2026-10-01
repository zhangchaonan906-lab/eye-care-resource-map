"use client";

import type { PublicFacility } from "../../lib/public-api/types";
import { FacilityDetailContent } from "./facility-detail-content";

type Props = { facility: PublicFacility | null; loading: boolean; error: string | null; labels: Map<string, string>; onClose: () => void };

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
        <FacilityDetailContent facility={facility} labels={labels} detailLink />
      </>}
    </section>
  );
}
