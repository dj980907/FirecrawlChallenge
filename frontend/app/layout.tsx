import ThemeRegistry from "@/components/providers/ThemeRegistry";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Firecrawl Challenge",
  description: "72-hour Firecrawl interview challenge",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <ThemeRegistry>{children}</ThemeRegistry>
      </body>
    </html>
  );
}
