"use client";

import { useState } from "react";

export type UserLocation = { longitude: number; latitude: number };
type LocationStatus = "idle" | "requesting" | "granted" | "denied" | "unavailable" | "timeout" | "error" | "unsupported";

type Props = { onLocated: (location: UserLocation) => void };

const messages: Record<Exclude<LocationStatus, "idle" | "requesting" | "granted" | "denied">, string> = {
  unavailable: "当前设备无法提供位置",
  timeout: "定位超时，请重试",
  error: "定位失败，请重试",
  unsupported: "当前浏览器不支持定位",
};

export function LocationControl({ onLocated }: Props) {
  const [status, setStatus] = useState<LocationStatus>("idle");

  const requestLocation = () => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setStatus("unsupported");
      return;
    }
    setStatus("requesting");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setStatus("granted");
        onLocated({ longitude: position.coords.longitude, latitude: position.coords.latitude });
      },
      (error) => {
        if (error.code === 1) setStatus("denied");
        else if (error.code === 2) setStatus("unavailable");
        else if (error.code === 3) setStatus("timeout");
        else setStatus("error");
      },
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 300_000 },
    );
  };

  const label = status === "idle" ? "定位到我"
    : status === "requesting" ? "正在获取位置…"
      : status === "granted" ? "已定位"
        : status === "denied" ? "无法获取位置，可手动浏览地图"
          : messages[status];
  const failed = status !== "idle" && status !== "requesting" && status !== "granted";

  return (
    <div className="eye-map__location-control" aria-live="polite">
      <button className="eye-map__location" type="button" disabled={status === "requesting"} onClick={requestLocation}>
        {label}
      </button>
      {status === "denied" && <p role="status">定位权限未开启，你仍可以搜索或手动浏览地图。</p>}
      {failed && <p className="eye-map__location-fallback">可通过地区筛选或拖动地图继续浏览</p>}
      {status === "denied" && <button className="eye-map__location-retry" type="button" onClick={requestLocation}>重新尝试定位</button>}
    </div>
  );
}
