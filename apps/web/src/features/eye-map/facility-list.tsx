"use client";

import type { PublicFacility } from "../../lib/public-api/types";

type ListedFacility = PublicFacility & { distanceMeters?: number };
type Props = { facilities: ListedFacility[]; selectedId: string | null; labels: Map<string, string>; onSelect: (facility: PublicFacility) => void; title?: string };

export function formatDistance(distanceMeters: number): string {
  if (distanceMeters < 1000) return `${Math.round(distanceMeters)} m`;
  return `${(distanceMeters / 1000).toFixed(1)} km`;
}

export function FacilityList({ facilities, selectedId, labels, onSelect, title = "当前视窗机构" }: Props) {
  if (!facilities.length) return null;
  return (
    <section className="eye-map__list" aria-label={title}>
      <h2>{title} <span>{facilities.length}</span></h2>
      <ul>
        {facilities.map((facility) => {
          const subdued = facility.category === "unknown";
          return (
            <li key={facility.id}>
              <button className={`eye-map__facility${selectedId === facility.id ? " is-selected" : ""}${subdued ? " is-unknown" : ""}`} type="button" aria-pressed={selectedId === facility.id} onClick={() => onSelect(facility)}>
                <span className="eye-map__facility-name">{facility.name}</span>
                <span className="eye-map__facility-category">{labels.get(facility.category) ?? (subdued ? "待核验" : "医疗机构")}</span>
                <span className="eye-map__facility-address">{facility.address}</span>
                <span className="eye-map__facility-address">{facility.region.name}</span>
                {facility.distanceMeters !== undefined && <span className="eye-map__facility-distance">{formatDistance(facility.distanceMeters)}</span>}
                {(facility.hospitalLevel || facility.hospitalGrade) && <span className="eye-map__facility-address">{[facility.hospitalLevel, facility.hospitalGrade].filter(Boolean).join(" · ")}</span>}
                <span className="eye-map__verified">已核验眼科信息</span>
                <time className="eye-map__facility-date" dateTime={facility.lastVerifiedAt}>最近核验：{new Date(facility.lastVerifiedAt).toLocaleDateString("zh-CN")}</time>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
