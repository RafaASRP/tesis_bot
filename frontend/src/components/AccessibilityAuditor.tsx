"use client";

import React, { useEffect } from 'react';

export default function AccessibilityAuditor() {
  useEffect(() => {
    // Aislamiento estricto: el motor de auditoría solo se ejecuta en entorno de desarrollo local
    if (process.env.NODE_ENV !== 'production' && typeof window !== 'undefined') {
      import('@axe-core/react').then((axe) => {
        import('react-dom').then((ReactDOM) => {
          axe.default(React, ReactDOM, 1000, {
            rules: [
              { id: 'color-contrast', enabled: true },
              { id: 'target-size', enabled: true }
            ]
          }).then(() => {
            console.info("Auditoría heurística WCAG 2.1 AA (axe-core) inicializada en el DOM.");
          });
        });
      });
    }
  }, []);

  return null;
}
