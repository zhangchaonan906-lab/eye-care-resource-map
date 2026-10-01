export const FACILITY_CATEGORIES = [
  "eye_specialty_hospital",
  "general_hospital_ophthalmology",
  "ophthalmology_center",
  "eye_clinic",
  "unknown",
] as const;

export const MIN_FACILITY_DETAIL_ZOOM = 7;
export const MAX_MAP_ZOOM = 24;

export type FacilityCategory = (typeof FACILITY_CATEGORIES)[number];

export type PublicFacility = {
  id: string;
  name: string;
  category: FacilityCategory;
  address: string;
  region: { adcode: string; name: string };
  hospitalLevel: string | null;
  hospitalGrade: string | null;
  longitude: number;
  latitude: number;
  ophthalmology: { status: "verified"; evidenceCount: number };
  attribution: Array<{ name: string; url: string; updatedAt: string | null }>;
  lastVerifiedAt: string;
};

export type Page<T> = { items: T[]; nextCursor: string | null };
export type FacilityListInput = {
  bbox: [number, number, number, number];
  zoom: number;
  category?: FacilityCategory;
  region?: string;
  limit: number;
  cursor?: string;
};
export type SearchInput = {
  q: string;
  match: "exact" | "prefix";
  category?: FacilityCategory;
  region?: string;
  limit: number;
  cursor?: { name: string; id: string };
};

export interface PublicFacilityRepository {
  list(input: FacilityListInput): Promise<Page<PublicFacility>>;
  getById(id: string): Promise<PublicFacility | null>;
  search(input: SearchInput): Promise<Page<PublicFacility>>;
  countPublished(): Promise<number>;
}
