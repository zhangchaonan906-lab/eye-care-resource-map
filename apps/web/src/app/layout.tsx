import type { Metadata } from "next";
import { validatedSiteUrl } from "@/lib/release/security";
import "./globals.css";

const siteUrl = validatedSiteUrl(process.env.SITE_URL);

export const metadata: Metadata = {
  title: "全国眼科医疗资源地图",
  description: "浏览已发布的眼科医疗资源及其公开来源信息。",
  ...(siteUrl ? { metadataBase: siteUrl } : {}),
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
