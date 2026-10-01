"use client";

export type CategoryOption = { id: string; label: string };
type Props = {
  categories: CategoryOption[];
  category: string;
  region: string;
  search: string;
  onCategoryChange: (value: string) => void;
  onRegionChange: (value: string) => void;
  onSearchChange: (value: string) => void;
};

export function SearchAndFilters(props: Props) {
  return (
    <div className="eye-map__controls">
      <label className="eye-map__field">
        <span>搜索医院</span>
        <input aria-label="搜索医院" type="search" value={props.search} onChange={(event) => props.onSearchChange(event.target.value)} placeholder="输入机构名称" />
      </label>
      <label className="eye-map__field">
        <span>机构类型</span>
        <select aria-label="机构类型" value={props.category} onChange={(event) => props.onCategoryChange(event.target.value)}>
          <option value="">全部类型</option>
          {props.categories.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select>
      </label>
      <label className="eye-map__field">
        <span>地区代码</span>
        <input aria-label="地区代码" inputMode="numeric" value={props.region} onChange={(event) => props.onRegionChange(event.target.value)} placeholder="如 110000" maxLength={6} />
      </label>
    </div>
  );
}
