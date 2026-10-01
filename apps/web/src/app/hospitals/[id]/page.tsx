import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { FacilityDetailContent } from "../../../features/eye-map/facility-detail-content";
import { parseUuid, ValidationError } from "../../../lib/public-api/validation";
import { getPublicFacilityRepository } from "../../../lib/public-api/repository";
import { formatFacilityCategory } from "../../../features/eye-map/facility-presentation";

type PageProps = { params: Promise<{ id: string }> };

async function findPublishedFacility(id: string) {
  try {
    return await getPublicFacilityRepository().getById(parseUuid(id));
  } catch (error) {
    if (error instanceof ValidationError) return null;
    throw error;
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const facility = await findPublishedFacility(id);
  if (!facility) return {};
  const description = [facility.name, formatFacilityCategory(facility.category), facility.address, facility.region.name]
    .filter(Boolean)
    .join(" · ");
  return {
    title: `${facility.name}｜全国眼科医疗资源地图`,
    description,
  };
}

export default async function HospitalDetailPage({ params }: PageProps) {
  const { id } = await params;
  const facility = await findPublishedFacility(id);
  if (!facility) notFound();
  return <main className="eye-map-page eye-map__public-detail">
    <header className="eye-map__header">
      <div>
        <p className="eye-map__eyebrow">公开医疗资源详情</p>
        <h1>{facility.name}</h1>
      </div>
    </header>
    <article className="eye-map__public-detail-card" aria-label={`${facility.name}公开信息`}>
      <FacilityDetailContent facility={facility} mapLink />
    </article>
  </main>;
}
