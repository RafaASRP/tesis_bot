import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Paleta de Alto Contraste (WCAG 2.1 AA) para adultos 50+
        gov: {
          primary: "#0B231E", // Verde oscuro institucional
          secondary: "#13322B", 
          accent: "#9D2449", // Guinda institucional (Botones de acción primaria)
          background: "#FAFAFA", // Fondo claro cálido para evitar fatiga visual
          surface: "#FFFFFF",
          text: "#1A1A1A", // Texto casi negro para máximo contraste (ratio > 4.5:1)
          muted: "#4A4A4A", // Texto secundario
          border: "#CCCCCC",
          focus: "#005EB8", // Azul eléctrico para anillos de enfoque accesibles
          error: "#D32F2F", // Rojo para alertas
        }
      },
      spacing: {
        '12': '3rem', // Garantiza áreas táctiles mínimas de 48x48 px (12 * 0.25rem = 3rem = 48px)
      },
      fontSize: {
        'base': '1.125rem', // 18px base para mejor legibilidad en adultos mayores
        'lg': '1.25rem',    // 20px
        'xl': '1.5rem',     // 24px
        '2xl': '1.875rem',  // 30px
      }
    },
  },
  plugins: [],
};
export default config;
