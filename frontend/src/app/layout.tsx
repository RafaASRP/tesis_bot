import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import dynamic from 'next/dynamic';

const inter = Inter({ subsets: ["latin"] });

// Carga dinámica con ruta relativa para asegurar compilación en Vercel
const AccessibilityAuditor = dynamic(() => import('../components/AccessibilityAuditor'), { ssr: false });

export const viewport: Viewport = {
  themeColor: "#0B231E",
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  title: "GovAssist Core",
  description: "Asistente virtual accesible para trámites federales (CURP, Acta, IMSS, Pasaporte, Cédula)",
  manifest: "/manifest.json",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className={`${inter.className} min-h-screen flex flex-col`}>
        {process.env.NODE_ENV !== 'production' && <AccessibilityAuditor />}
        
        <header className="bg-gov-primary text-white p-4 shadow-md text-center border-b-4 border-gov-accent" role="banner">
          <h1 className="text-xl font-bold tracking-wide">GovAssist Core</h1>
          <p className="text-sm opacity-90">Accesibilidad y Trámites Simples en gob.mx</p>
        </header>
        
        <main className="flex-grow container mx-auto px-4 py-6 flex flex-col items-center" role="main">
          {children}
        </main>
      </body>
    </html>
  );
}
