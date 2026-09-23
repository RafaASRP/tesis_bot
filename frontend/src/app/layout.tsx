import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GovAssist Core - UATx",
  description: "Asistente inclusivo de automatización para trámites federales dirigido a adultos mayores.",
  manifest: "/manifest.json",
  themeColor: "#0B231E",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className="bg-[#0B231E] text-white antialiased min-h-screen text-lg">
        {children}
      </body>
    </html>
  );
}
