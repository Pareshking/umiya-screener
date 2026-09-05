import "./globals.css";

export const metadata = {
  title: "Umiya Screener — NSE momentum research",
  description: "Ranked NSE 750 momentum research on a calendar-period quantitative engine.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* Inter for text, JetBrains Mono for every number in the product.
            Preconnect so the numeric face is not the last thing to paint. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;550;600;650;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
