"use client";

import type { PublicFacility } from "../../lib/public-api/types";
import type { Ref } from "react";
import { FacilityDetailContent } from "./facility-detail-content";

type Props = { facility: PublicFacility | null; loading: boolean; error: string | null; labels: Map<string, string>; onClose: () => void; headingRef: Ref<HTMLHeadingElement> };

export function FacilityDetailPanel({ facility, loading, error, labels, onClose, headingRef }: Props) {
  if (!facility && !loading && !error) return null;
  const title = facility?.name ?? "机构详情";
  return (
    <section className="eye-map__detail" role="dialog" aria-modal="false" aria-label={`${title}详情`} aria-labelledby="facility-detail-title">
      <button className="eye-map__detail-close" type="button" aria-label="关闭详情" onClick={onClose}>关闭</button>
      <h2 ref={headingRef} id="facility-detail-title" tabIndex={-1}>{title}</h2>
      {loading && <p role="status">正在加载机构详情…</p>}
      {error && <p role="alert">{error}</p>}
      {facility && <FacilityDetailContent facility={facility} labels={labels} detailLink />}
    </section>
  );
}
