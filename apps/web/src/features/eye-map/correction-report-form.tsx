"use client";

import { useId, useState } from "react";
import { CORRECTION_TYPES, type CorrectionType } from "../../lib/corrections/validation";

const labels: Record<CorrectionType, string> = {
  institution_info: "机构信息有误", moved: "机构已搬迁", closed: "机构已停业",
  ophthalmology_services: "眼科服务有变化", coordinates: "地图位置有误", source_issue: "来源信息有问题",
};

export function CorrectionReportForm({ facilityId, compact = false }: { facilityId?: string; compact?: boolean }) {
  const privacyId = useId();
  const [type, setType] = useState<CorrectionType>("institution_info");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setStatus(null);
    try {
      const response = await fetch("/api/corrections", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...(facilityId ? { facilityId } : {}), type, description }),
        cache: "no-store",
      });
      if (!response.ok) throw new Error("提交失败，请稍后重试");
      setDescription("");
      setStatus("已提交，内容将由工作人员审核；不会自动修改机构信息。");
    } catch (error) { setStatus(error instanceof Error ? error.message : "提交失败，请稍后重试"); }
    finally { setBusy(false); }
  }
  return <details className="eye-map__correction">
    <summary>{compact ? "报告此机构信息问题" : "报告机构信息问题"}</summary>
    <form onSubmit={submit}>
      <label>问题类型<select value={type} onChange={(event) => setType(event.target.value as CorrectionType)}>{CORRECTION_TYPES.map((item) => <option key={item} value={item}>{labels[item]}</option>)}</select></label>
      <label>说明<textarea required minLength={10} maxLength={1000} value={description} onChange={(event) => setDescription(event.target.value)} aria-describedby={privacyId} /></label>
      <p id={privacyId}>请勿填写个人信息、病情或精确当前位置。提交内容仅进入人工审核队列，不会直接修改公开数据。</p>
      <button type="submit" disabled={busy || description.trim().length < 10}>{busy ? "正在提交…" : "提交审核"}</button>
      {status && <p role="status">{status}</p>}
    </form>
  </details>;
}
