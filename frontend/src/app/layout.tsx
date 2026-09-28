import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import dynamic from 'next/dynamic';

const inter = Inter({ subsets: ["latin"] });

// Carga dinámica del auditor para evitar que afecte el bundle en producción
const AccessibilityAuditor = dynamic(() => import('@/components/AccessibilityAuditor'), { ssr: false });

export const viewport: Viewport = {
  themeColor: "#0B231E",
  width: "device-width",
  initialScale: 1,
  // maximumScale eliminado estrictamente para cumplir con WCAG 2.1 AA (Zooming enabled)
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
        
        {/* Header de alto contraste WCAG 2.1 AA */}
        <header className="bg-gov-primary text-white p-4 shadow-md text-center border-b-4 border-gov-accent" role="banner">
          <h1 className="text-xl font-bold tracking-wide">GovAssist Core</h1>
          <p className="text-sm opacity-90">Accesibilidad y Trámites Simples en gob.mx</p>
        </header>
        
        {/* Contenedor principal con compensación visual para 50+ años */}
        <main className="flex-grow container mx-auto px-4 py-6 flex flex-col items-center" role="main">
          {children}
        </main>
      </body>
    </html>
  );
}
