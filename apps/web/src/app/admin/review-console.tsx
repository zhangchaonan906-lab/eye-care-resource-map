"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type QueueType = "candidates" | "duplicates" | "locations" | "facilities" | "imports" | "audit" | "syncPolicies" | "syncTasks" | "syncAlerts";
type Row = Record<string, unknown> & { id: string };
const TABS: Array<{ key: QueueType; label: string }> = [
  { key: "candidates", label: "候选审核" }, { key: "duplicates", label: "重复冲突" },
  { key: "locations", label: "坐标审核" }, { key: "facilities", label: "发布审核" },
  { key: "imports", label: "运行记录" }, { key: "audit", label: "审计记录" },
  { key: "syncPolicies", label: "同步来源" }, { key: "syncTasks", label: "同步任务" }, { key: "syncAlerts", label: "同步告警" },
];
const STATUS_OPTIONS: Record<QueueType, Array<[string, string]>> = {
  candidates: [["", "全部状态"], ["unmatched", "未匹配"], ["needs_review", "待复核"], ["matched", "已匹配"], ["rejected", "已拒绝"]],
  duplicates: [["", "全部状态"], ["pending", "待处理"], ["merge", "已合并"], ["separate", "已拆分"], ["reject", "已拒绝"]],
  locations: [["", "全部状态"], ["needs_review", "待复核"], ["verified", "已核验"], ["rejected", "已拒绝"]],
  facilities: [["", "全部状态"], ["in_review", "待核验"], ["verified", "待发布"], ["published", "已发布"], ["withdrawn", "已撤回"]],
  imports: [["", "全部状态"], ["running", "运行中"], ["succeeded", "成功"], ["failed", "失败"]],
  audit: [["", "全部动作"], ["PUBLISH", "发布"], ["WITHDRAW", "撤回"], ["MERGE", "合并"]],
  syncPolicies: [["", "全部来源"], ["approved", "已批准"], ["pending", "待审核"], ["suspended", "已暂停"]],
  syncTasks: [["", "全部状态"], ["queued", "排队中"], ["running", "运行中"], ["retry_wait", "等待重试"], ["succeeded", "成功"], ["dead_letter", "死信"]],
  syncAlerts: [["", "全部级别"], ["warning", "警告"], ["error", "错误"], ["critical", "严重"]],
};
const STATUS_COLUMN: Record<QueueType, string> = { candidates: "match_status", duplicates: "resolution", locations: "validation_status", facilities: "verification_status", imports: "status", audit: "action", syncPolicies: "source_status", syncTasks: "status", syncAlerts: "severity" };

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

export default function AdminConsole({ username }: { username: string }) {
  const [tab, setTab] = useState<QueueType>("candidates");
  const [status, setStatus] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const [selected, setSelected] = useState<Row | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reason, setReason] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [csrf, setCsrf] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [regionFilter, setRegionFilter] = useState("");

  const load = useCallback(async (type: QueueType, selectedStatus: string, currentCursor?: string | null, selectedSource?: string, selectedRegion?: string) => {
    try {
      const syncType = type === "syncPolicies" ? "policies" : type === "syncTasks" ? "tasks" : type === "syncAlerts" ? "alerts" : null;
      const params = new URLSearchParams({ type: syncType ?? type, limit: "25" });
      if (selectedStatus) params.set("status", selectedStatus);
      if (currentCursor) params.set("cursor", currentCursor);
      if (selectedSource) params.set("source", selectedSource);
      if (selectedRegion) params.set("region", selectedRegion);
      const response = await fetch(`${syncType ? "/api/admin/sync" : "/api/admin/review"}?${params}`, { cache: "no-store" });
      setBusy(true); setError("");
      const result = await response.json();
      if (response.status === 401) { window.location.replace("/admin/login"); return; }
      if (!response.ok) throw new Error(result.error?.message ?? "审核队列加载失败");
      setRows(result.data ?? []); setNextCursor(result.meta?.nextCursor ?? null); setSelected(null);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "审核队列加载失败"); }
    finally { setBusy(false); }
  }, []);

  useEffect(() => { void Promise.resolve().then(() => load(tab, status, cursor, sourceFilter, regionFilter)); }, [tab, status, cursor, sourceFilter, regionFilter, load]);
  useEffect(() => { void fetch("/api/admin/session", { cache: "no-store" }).then((response) => response.json()).then((result) => setCsrf(result.data?.csrfToken ?? "")); }, []);

  const detailKeys = useMemo(() => selected ? Object.keys(selected).filter((key) => key !== "id") : [], [selected]);

  async function decide(action: string, payload: Record<string, unknown> = {}, confirmation = false) {
    if (!selected || reason.trim().length < 5) { setActionMessage("请填写至少 5 个字符的审核理由。"); return; }
    if (confirmation && !window.confirm(`即将执行“${action}”。请确认该操作及其影响。`)) return;
    setBusy(true); setActionMessage("");
    const body = { action, reason: reason.trim(), ...payload };
    try {
      const isSync = tab.startsWith("sync");
      const target = isSync ? `/api/admin/sync/${String(selected.source_id ?? "")}/decision` : `/api/admin/${tab}/${selected.id}/decision`;
      const response = await fetch(target, {
        method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf, "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify(body),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error?.message ?? "审核操作失败");
      setReason(""); setActionMessage("操作已完成并写入审计记录。");
      await load(tab, status, cursor, sourceFilter, regionFilter);
    } catch (cause) { setActionMessage(cause instanceof Error ? cause.message : "审核操作失败"); }
    finally { setBusy(false); }
  }

  async function logout() {
    await fetch("/api/admin/session", { method: "DELETE", headers: { "X-CSRF-Token": csrf } });
    window.location.replace("/admin/login");
  }

  function actionButtons() {
    if (!selected) return null;
    if (tab === "syncPolicies") return <div className="admin-actions">
      <button disabled={busy || selected.access_policy !== "automated_access_allowed" || selected.source_status !== "approved"} onClick={() => void decide("RUN_NOW")}>立即运行</button>
      <button disabled={busy} onClick={() => void decide("PAUSE_SYNC", {}, true)}>暂停同步</button>
      <button disabled={busy} onClick={() => void decide("RESUME_SYNC", {}, true)}>恢复同步</button>
    </div>;
    if (tab === "candidates") return <div className="admin-actions">
      <details><summary>建立审核中机构</summary><div className="admin-form-grid">
        <input aria-label="机构名称" placeholder="机构名称（需审核员确认）" id="candidate-name" />
        <input aria-label="机构地址" placeholder="机构地址（需审核员确认）" id="candidate-address" />
        <input aria-label="行政区代码" placeholder="6 位行政区代码" id="candidate-region" defaultValue={String(selected.administrative_code ?? "")} />
        <select aria-label="机构类别" id="candidate-category"><option value="unknown">待分类</option><option value="eye_specialty_hospital">眼科专科医院</option><option value="general_hospital_ophthalmology">综合医院眼科</option><option value="ophthalmology_center">眼科中心</option><option value="eye_clinic">眼科诊所</option></select>
        <button disabled={busy} onClick={() => void decide("CREATE_FACILITY", { name: (document.getElementById("candidate-name") as HTMLInputElement).value, address: (document.getElementById("candidate-address") as HTMLInputElement).value, regionCode: (document.getElementById("candidate-region") as HTMLInputElement).value, category: (document.getElementById("candidate-category") as HTMLSelectElement).value })}>建立并进入审核</button>
      </div></details>
      <details><summary>匹配现有机构</summary><div className="admin-form-grid"><input id="target-facility" placeholder="目标 facility UUID" /><button disabled={busy} onClick={() => void decide("MATCH_EXISTING_FACILITY", { targetFacilityId: (document.getElementById("target-facility") as HTMLInputElement).value })}>匹配机构</button></div></details>
      <button className="admin-button--danger" disabled={busy} onClick={() => void decide("REJECT_CANDIDATE", {}, true)}>拒绝候选</button>
    </div>;
    if (tab === "duplicates") return <div className="admin-actions">
      <details><summary>合并候选</summary><div className="admin-form-grid"><input id="duplicate-target" placeholder="目标 facility UUID；新建请留空" /><input id="duplicate-primary" placeholder="新建时主 candidate UUID" /><input id="duplicate-name" placeholder="新机构名称" /><input id="duplicate-address" placeholder="新机构地址" /><input id="duplicate-region" placeholder="6 位行政区代码" /><select id="duplicate-category"><option value="unknown">待分类</option><option value="eye_specialty_hospital">眼科专科医院</option><option value="general_hospital_ophthalmology">综合医院眼科</option></select><button disabled={busy} onClick={() => void decide("MERGE", { targetFacilityId: (document.getElementById("duplicate-target") as HTMLInputElement).value || null, primaryCandidateId: (document.getElementById("duplicate-primary") as HTMLInputElement).value, name: (document.getElementById("duplicate-name") as HTMLInputElement).value, address: (document.getElementById("duplicate-address") as HTMLInputElement).value, regionCode: (document.getElementById("duplicate-region") as HTMLInputElement).value, category: (document.getElementById("duplicate-category") as HTMLSelectElement).value }, true)}>合并候选</button></div></details>
      <button disabled={busy} onClick={() => void decide("SEPARATE", {}, true)}>拆分为不同机构</button><button className="admin-button--danger" disabled={busy} onClick={() => void decide("REJECT_DUPLICATE", {}, true)}>拒绝重复关系</button>
      {String(selected.resolution) !== "pending" && <button disabled={busy} onClick={() => void decide("REOPEN_DUPLICATE_CASE", {}, true)}>重新打开冲突</button>}
    </div>;
    if (tab === "locations") return <div className="admin-actions"><button disabled={busy} onClick={() => void decide("VERIFY_LOCATION", {}, true)}>核验坐标</button><button className="admin-button--danger" disabled={busy} onClick={() => void decide("REJECT_LOCATION", {}, true)}>拒绝坐标</button><button disabled={busy} onClick={() => void decide("PROMOTE_LOCATION", { replaceVerified: window.confirm("若已有已核验位置，此操作会替换。确认允许替换？") }, true)}>提升为机构位置</button></div>;
    if (tab === "facilities") return <div className="admin-actions">
      <button disabled={busy || String(selected.verification_status) !== "in_review"} onClick={() => void decide("VERIFY_FACILITY", {}, true)}>核验机构</button>
      <button disabled={busy || String(selected.verification_status) !== "verified" || (Array.isArray((selected.publication_checklist as { blockers?: unknown[] })?.blockers) && ((selected.publication_checklist as { blockers: unknown[] }).blockers.length > 0))} onClick={() => void decide("PUBLISH", {}, true)}>发布</button>
      <button disabled={busy} onClick={() => void decide("RETURN_TO_REVIEW", {}, true)}>退回审核</button><button className="admin-button--danger" disabled={busy || String(selected.verification_status) !== "published"} onClick={() => void decide("WITHDRAW", {}, true)}>撤回发布</button>
    </div>;
    return null;
  }

  return <main className="admin-shell">
    <aside className="admin-sidebar"><div><p className="admin-eyebrow">EYE CARE RESOURCE MAP</p><h1>审核控制台</h1><p className="admin-muted">管理员：{username}</p></div>
      <nav aria-label="审核队列">{TABS.map((item) => <button key={item.key} className={tab === item.key ? "is-active" : ""} onClick={() => { setTab(item.key); setStatus(""); setCursor(null); }}>{item.label}</button>)}</nav>
      <button className="admin-logout" onClick={() => void logout()}>退出登录</button>
    </aside>
    <section className="admin-workspace"><header className="admin-toolbar"><div><p className="admin-eyebrow">P11 · REVIEW & PUBLICATION</p><h2>{TABS.find((item) => item.key === tab)?.label}</h2></div>
      <div className="admin-toolbar__filters">{tab === "candidates" && <><label>来源 UUID<input value={sourceFilter} onChange={(event) => { setCursor(null); setSourceFilter(event.target.value); }} placeholder="按来源筛选" /></label><label>行政区代码<input value={regionFilter} onChange={(event) => { setCursor(null); setRegionFilter(event.target.value); }} placeholder="2–6 位前缀" /></label></>}
      {tab !== "audit" && <label>状态筛选<select value={status} onChange={(event) => { setCursor(null); setStatus(event.target.value); }}>{STATUS_OPTIONS[tab].map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label>}</div>
    </header>
    <div className="admin-review-grid"><section className="admin-queue" aria-label="审核列表">
      {error && <p className="admin-error" role="alert">{error}</p>}{busy && <p className="admin-muted">正在加载…</p>}
      {!busy && !error && rows.length === 0 && <p className="admin-empty">当前筛选没有待处理记录。</p>}
      <ul>{rows.map((row) => <li key={row.id}><button className={selected?.id === row.id ? "is-selected" : ""} onClick={() => setSelected(row)}>
        <strong>{display(row.name ?? row.parsed_name ?? row.candidate_name ?? row.source_name ?? row.entity ?? row.id)}</strong>
        <span>{display(row.address ?? row.parsed_address ?? row.query_address ?? row.reason ?? row.action)}</span>
        <small>{display(row[STATUS_COLUMN[tab]])} · {row.id}</small>
      </button></li>)}</ul>
      {nextCursor && <button className="admin-next" disabled={busy} onClick={() => setCursor(nextCursor)}>加载下一页</button>}
    </section>
    <section className="admin-detail" aria-label="审核详情">
      {!selected ? <div className="admin-empty">选择左侧记录查看审核信息。</div> : <>
        <div className="admin-detail__heading"><div><p className="admin-eyebrow">REVIEW RECORD</p><h3>{display(selected.name ?? selected.parsed_name ?? selected.candidate_name ?? selected.id)}</h3></div><code>{selected.id}</code></div>
        {tab === "facilities" && <div className="admin-checklist"><h4>发布检查清单</h4>{Object.entries((selected.publication_checklist as Record<string, unknown>) ?? {}).filter(([key]) => key !== "blockers" && key !== "exists").map(([key,value]) => <p key={key} className={value ? "is-pass" : "is-fail"}>{value ? "✓" : "✗"} {key}</p>)}{Array.isArray((selected.publication_checklist as { blockers?: unknown[] })?.blockers) && <p className="admin-error">阻塞项：{display((selected.publication_checklist as { blockers: unknown[] }).blockers)}</p>}</div>}
        <dl>{detailKeys.map((key) => <div key={key}><dt>{key}</dt><dd>{display(selected[key])}</dd></div>)}</dl>
        {TABS.find((item) => item.key === tab)?.key && !["audit", "imports", "syncTasks", "syncAlerts"].includes(tab) && <div className="admin-decision"><label>操作理由（5–500 字）<textarea minLength={5} maxLength={500} value={reason} onChange={(event) => setReason(event.target.value)} /></label>{actionButtons()}</div>}
      </>}
      {actionMessage && <p role="status" className="admin-status">{actionMessage}</p>}
    </section></div>
    <footer className="admin-footnote">来源审批仍由人工管理。同步操作仅排队、暂停或恢复已批准的自动化来源；不会触发地理编码或设施发布。</footer>
  </section></main>;
}
