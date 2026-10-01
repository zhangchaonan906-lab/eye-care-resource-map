"use client";

import type { PublicFacility } from "../../lib/public-api/types";

type Props = { facilities: PublicFacility[]; selectedId: string | null; labels: Map<string, string>; onSelect: (facility: PublicFacility) => void };

export function FacilityList({ facilities, selectedId, labels, onSelect }: Props) {
  if (!facilities.length) return null;
  return (
    <section className="eye-map__list" aria-label="当前地图视窗内的医疗机构">
      <h2>当前视窗机构 <span>{facilities.length}</span></h2>
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
