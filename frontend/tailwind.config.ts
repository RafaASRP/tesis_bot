import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Paleta de alto contraste optimizada para WCAG 2.1 AA (Adultos Mayores)
        gov: {
          primary: "#0B231E",    // Verde institucional oscuro / Guinda institucional
          burgundy: "#6A1B29",   // Guinda gob.mx
          accent: "#1D4ED8",     // Azul interactivo de alto contraste
          bg: "#F9FAFB",         // Fondo claro legible
          card: "#FFFFFF",       // Superficie de tarjetas limpia
          text: "#111827",       // Texto principal casi negro para máxima legibilidad
          muted: "#4B5563",      // Texto secundario contrastado
        }
      },
      fontSize: {
        // Tamaños de fuente aumentados para accesibilidad cognitiva y visual
        base: ["1.125rem", { lineHeight: "1.75rem" }], // 18px base
        lg: ["1.25rem", { lineHeight: "1.75rem" }],
        xl: ["1.5rem", { lineHeight: "2rem" }],
        "2xl": ["1.875rem", { lineHeight: "2.25rem" }],
      }
    },
  },
  plugins: [],
}
export default config
