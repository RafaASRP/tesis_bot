"use client";

import React, { useEffect } from 'react';

interface ProcedureModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  message: string;
  pdfUrl?: string;
}

export default function ProcedureModal({ isOpen, onClose, title, message, pdfUrl }: ProcedureModalProps) {
  // Manejo accesible para cerrar con la tecla Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-70 backdrop-blur-sm p-4" 
      role="dialog" 
      aria-modal="true" 
      aria-labelledby="modal-title"
    >
      <div className="bg-gov-surface w-full max-w-2xl rounded-2xl shadow-2xl border-4 border-gov-accent overflow-hidden flex flex-col animate-in fade-in zoom-in duration-300">
        
        {/* Cabecera de alto contraste */}
        <div className="bg-gov-primary p-5 text-white flex justify-between items-center border-b-4 border-gov-accent">
          <h2 id="modal-title" className="text-2xl font-bold tracking-wide">{title}</h2>
          <button
            onClick={onClose}
            aria-label="Cerrar ventana"
            className="h-12 w-12 flex-shrink-0 flex items-center justify-center rounded-full hover:bg-gov-secondary transition-colors focus-visible:ring-4 focus-visible:ring-gov-focus"
          >
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        {/* Cuerpo del Modal */}
        <div className="p-6 flex-1 overflow-y-auto flex flex-col items-center">
          <p className="text-xl text-gov-text mb-8 text-center leading-relaxed">
            {message}
          </p>
          
          {pdfUrl && (
            <div className="w-full bg-gov-background border-2 border-gov-border rounded-xl p-6 flex flex-col items-center justify-center space-y-5">
              <div className="p-4 bg-gov-accent bg-opacity-10 rounded-full">
                <svg className="w-16 h-16 text-gov-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <p className="text-gov-muted text-center font-medium text-lg max-w-md">
                Tu documento oficial está listo. La copia en nuestros servidores será purgada inmediatamente para proteger tu privacidad.
              </p>
              <a
                href={pdfUrl}
                download
                target="_blank"
                rel="noopener noreferrer"
                className="h-14 px-10 bg-gov-accent text-white rounded-xl font-bold text-xl flex items-center justify-center shadow-md hover:bg-opacity-90 focus-visible:ring-4 focus-visible:ring-gov-focus transition-all w-full md:w-auto mt-4"
              >
                Descargar PDF
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
