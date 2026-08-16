import "./globals.css";

export const metadata = { title: "Umiya Screener", description: "NSE quantitative momentum screener" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
