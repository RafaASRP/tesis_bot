'use client';

import React, { useState, useEffect } from 'react';

export type ModalState = 'connecting' | 'captcha' | 'error' | 'success';

interface ProcedureModalProps {
  isOpen: boolean;
  onClose: () => void;
  procedureTitle?: string;
}

export const ProcedureModal: React.FC<ProcedureModalProps> = ({
  isOpen,
  onClose,
  procedureTitle = 'Consulta Oficial de CURP',
}) => {
  const [currentState, setCurrentState] = useState<ModalState>('connecting');
  const [captchaChecked, setCaptchaChecked] = useState(false);
  const [isProcessingCaptcha, setIsProcessingCaptcha] = useState(false);

  // Temporizador para simular la llegada del portal gob.mx al reto CAPTCHA
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isOpen && currentState === 'connecting') {
      timer = setTimeout(() => {
        setCurrentState('captcha');
      }, 3500);
    }
    return () => clearTimeout(timer);
  }, [isOpen, currentState]);

  if (!isOpen) return null;

  const handleSolveCaptcha = () => {
    setIsProcessingCaptcha(true);
    setTimeout(() => {
      setIsProcessingCaptcha(false);
      setCurrentState('success');
    }, 2000);
  };

  const handleRetry = () => {
    setCaptchaChecked(false);
    setCurrentState('connecting');
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-status-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-md animate-fadeIn"
    >
      <div className="w-full max-w-lg rounded-3xl bg-white p-6 md:p-8 shadow-2xl border border-slate-200">
        {/* Cabecera Institucional */}
        <div className="border-b border-slate-200 pb-4 text-center">
          <span className="inline-block rounded-full bg-[#8A1538]/10 px-4 py-1 text-xs font-bold text-[#8A1538] uppercase tracking-wider">
            Ventanilla Digital gob.mx
          </span>
          <h2 id="modal-status-title" className="mt-2 text-2xl font-black text-slate-900">
            {procedureTitle}
          </h2>
        </div>

        {/* 1. Estado: Conectando con gob.mx */}
        {currentState === 'connecting' && (
          <div className="my-8 flex flex-col items-center text-center">
            <div className="relative flex h-20 w-20 items-center justify-center">
              <div className="absolute h-full w-full animate-ping rounded-full bg-[#8A1538]/20" />
              <div className="h-16 w-16 animate-spin rounded-full border-4 border-[#8A1538] border-t-transparent" />
            </div>
            <h3 className="mt-6 text-xl font-bold text-slate-900">
              Conectando con el portal de gob.mx...
            </h3>
            <p className="mt-2 text-base text-slate-600 max-w-sm">
              Estamos ingresando tus datos validados en los servidores federales. Por favor, mantén esta ventana abierta.
            </p>
            {/* Disparador de emergencia para simular error de red si se desea probar */}
            <button
              type="button"
              onClick={() => setCurrentState('error')}
              className="mt-6 text-xs text-slate-400 hover:text-red-600 underline"
            >
              (Probar pantalla de error de conexión)
            </button>
          </div>
        )}

        {/* 2. Estado: Reto de Seguridad CAPTCHA (Human-in-the-Loop) */}
        {currentState === 'captcha' && (
          <div className="my-6 text-center animate-fadeIn">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-100 text-amber-800">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <h3 className="mt-3 text-xl font-bold text-slate-900">
              Validación de Seguridad Ciudadana
            </h3>
            <p className="mt-2 text-base text-slate-700">
              El portal oficial solicita confirmar que eres una persona real antes de emitir tu documento.
            </p>

            {/* Recuadro Accesible tipo reCAPTCHA */}
            <div className="mx-auto my-6 flex max-w-xs items-center justify-between rounded-xl border-2 border-slate-300 bg-slate-50 p-4 shadow-sm hover:border-slate-400 transition">
              <label className="flex cursor-pointer items-center gap-3">
                <input
                  type="checkbox"
                  checked={captchaChecked}
                  onChange={(e) => setCaptchaChecked(e.target.checked)}
                  className="h-7 w-7 cursor-pointer rounded border-slate-400 text-[#8A1538] focus:ring-[#8A1538]"
                />
                <span className="text-base font-semibold text-slate-800">
                  No soy un robot
                </span>
              </label>
              <span className="text-xs font-bold text-slate-400 tracking-wider">reCAPTCHA</span>
            </div>

            <button
              type="button"
              disabled={!captchaChecked || isProcessingCaptcha}
              onClick={handleSolveCaptcha}
              className={`flex min-h-[50px] w-full items-center justify-center rounded-2xl px-6 text-lg font-bold shadow-lg transition-all ${
                captchaChecked && !isProcessingCaptcha
                  ? 'bg-[#8A1538] text-white hover:bg-[#5a0c24] active:scale-95'
                  : 'cursor-not-allowed bg-slate-300 text-slate-500'
              }`}
            >
              {isProcessingCaptcha ? 'Validando con RENAPO...' : 'Continuar con el trámite'}
            </button>
          </div>
        )}

        {/* 3. Estado: Error de Conexión */}
        {currentState === 'error' && (
          <div className="my-6 text-center animate-fadeIn">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-red-100 text-red-700">
              <svg className="w-9 h-9" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="mt-4 text-xl font-bold text-slate-900">
              Intermitencia en el portal oficial
            </h3>
            <p className="mt-2 text-base text-slate-600">
              El servicio de gob.mx no respondió en el tiempo esperado. Por favor reintenta la conexión.
            </p>
            <div className="mt-6 flex flex-col gap-3">
              <button
                type="button"
                onClick={handleRetry}
                className="flex min-h-[48px] w-full items-center justify-center rounded-2xl bg-[#8A1538] px-6 text-base font-bold text-white shadow-md hover:bg-[#5a0c24]"
              >
                Reintentar conexión
              </button>
              <button
                type="button"
                onClick={onClose}
                className="flex min-h-[48px] w-full items-center justify-center rounded-2xl border border-slate-300 bg-white px-6 text-base font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cerrar ventana
              </button>
            </div>
          </div>
        )}

        {/* 4. Estado: Éxito y Consulta Concluida */}
        {currentState === 'success' && (
          <div className="my-6 text-center animate-fadeIn">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700">
              <svg className="w-9 h-9" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h3 className="mt-4 text-2xl font-black text-slate-900">
              ¡CURP Localizada con Éxito!
            </h3>
            <p className="mt-2 text-base text-slate-600">
              Tu constancia oficial ha sido verificada en el Registro Nacional de Población.
            </p>
            <div className="mt-6 flex flex-col gap-3">
              <button
                type="button"
                onClick={onClose}
                className="flex min-h-[50px] w-full items-center justify-center rounded-2xl bg-[#8A1538] px-6 text-lg font-bold text-white shadow-lg hover:bg-[#5a0c24] active:scale-95 transition"
              >
                Descargar Documento Oficial (PDF)
              </button>
              <button
                type="button"
                onClick={onClose}
                className="text-sm font-semibold text-slate-500 hover:text-slate-800"
              >
                Finalizar trámite
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
