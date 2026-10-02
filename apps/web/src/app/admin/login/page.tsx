"use client";

import { useState } from "react";

export default function AdminLoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const challenge = await fetch("/api/admin/session", { cache: "no-store" }).then((response) => response.json());
      if (!challenge.data?.csrfToken) throw new Error("登录校验暂不可用");
      const response = await fetch("/api/admin/session", {
        method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": challenge.data.csrfToken },
        body: JSON.stringify({ username, password }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error?.message ?? "登录失败");
      window.location.replace("/admin");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "登录失败");
    } finally { setBusy(false); setPassword(""); }
  }

  return <main className="admin-login"><form onSubmit={submit} className="admin-login__card">
    <p className="admin-eyebrow">EYE CARE RESOURCE MAP</p><h1>管理员登录</h1>
    <label>用户名<input autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} /></label>
    <label>密码<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
    {error && <p role="alert" className="admin-error">{error}</p>}
    <button disabled={busy}>{busy ? "正在验证…" : "登录审核台"}</button>
    <p className="admin-muted">仅限授权审核员使用。操作会记录在审计日志中。</p>
  </form></main>;
}
