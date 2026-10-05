'use client';

import React, { useState } from 'react';

export type ModalState = 'connecting' | 'captcha' | 'error' | 'success';

interface ProcedureModalProps {
  isOpen: boolean;
  onClose: () => void;
  procedureTitle?: string;
  onRetry?: () => void;
  onCaptchaSolved?: () => void;
}

export const ProcedureModal: React.FC<ProcedureModalProps> = ({
  isOpen,
  onClose,
  procedureTitle = 'Consulta de CURP',
  onRetry,
  onCaptchaSolved,
}) => {
  const [currentState, setCurrentState] = useState<ModalState>('connecting');
  const [captchaChecked, setCaptchaChecked] = useState(false);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
    >
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl ring-2 ring-gray-900/10 md:p-8">
        {/* Encabezado accesible */}
        <div className="border-b border-gray-200 pb-4 text-center">
          <span className="inline-block rounded-full bg-blue-100 px-3 py-1 text-sm font-semibold text-blue-800">
            Trámite Oficial gob.mx
          </span>
          <h2 id="modal-title" className="mt-2 text-2xl font-bold text-gray-900">
            {procedureTitle}
          </h2>
        </div>

        {/* 1. Estado: Conectando con gob.mx */}
        {currentState === 'connecting' && (
          <div className="my-8 flex flex-col items-center text-center">
            <div className="h-16 w-16 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
            <h3 className="mt-6 text-xl font-bold text-gray-900">
              Conectando con el portal oficial...
            </h3>
            <p className="mt-2 text-base text-gray-600">
              Estamos ingresando de forma segura a gob.mx con tus datos. Por favor, no cierres esta ventana.
            </p>
            {/* Botón de prueba para simular evento de CAPTCHA */}
            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={() => setCurrentState('captcha')}
                className="text-xs text-blue-600 underline"
              >
                (Simular reto CAPTCHA)
              </button>
              <button
                type="button"
                onClick={() => setCurrentState('error')}
                className="text-xs text-red-600 underline"
              >
                (Simular error de conexión)
              </button>
            </div>
          </div>
        )}

        {/* 2. Estado: Error de Conexión */}
        {currentState === 'error' && (
          <div className="my-6 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
              <span className="text-3xl font-bold text-red-600">!</span>
            </div>
            <h3 className="mt-4 text-xl font-bold text-gray-900">
              Problema de conexión con gob.mx
            </h3>
            <p className="mt-2 text-base text-gray-600">
              El portal oficial tardó demasiado en responder o tiene intermitencias temporales.
            </p>
            <div className="mt-6 flex flex-col gap-3">
              <button
                type="button"
                onClick={() => {
                  setCurrentState('connecting');
                  if (onRetry) onRetry();
                }}
                className="flex min-h-[48px] w-full items-center justify-center rounded-xl bg-blue-700 px-6 text-lg font-bold text-white shadow-md transition hover:bg-blue-800"
              >
                Reintentar conexión
              </button>
              <button
                type="button"
                onClick={onClose}
                className="flex min-h-[48px] w-full items-center justify-center rounded-xl border-2 border-gray-300 bg-white px-6 text-base font-semibold text-gray-700 hover:bg-gray-50"
              >
                Cerrar y volver al chat
              </button>
            </div>
          </div>
        )}

        {/* 3. Estado: Reto de Seguridad CAPTCHA (Human-in-the-Loop) */}
        {currentState === 'captcha' && (
          <div className="my-6 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-100">
              <span className="text-2xl">🛡️</span>
            </div>
            <h3 className="mt-3 text-xl font-bold text-gray-900">
              Verificación de Seguridad
            </h3>
            <p className="mt-2 text-base text-gray-700">
              El portal de gob.mx solicita verificar que eres un ciudadano real. Por favor marca la casilla:
            </p>

            {/* Recuadro accesible para resolución manual del reto */}
            <div className="mx-auto my-6 flex max-w-xs items-center justify-between rounded-lg border-2 border-gray-300 bg-gray-50 p-4 shadow-inner">
              <label className="flex cursor-pointer items-center gap-3">
                <input
                  type="checkbox"
                  checked={captchaChecked}
                  onChange={(e) => setCaptchaChecked(e.target.checked)}
                  className="h-8 w-8 cursor-pointer rounded border-gray-400 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-base font-medium text-gray-900">
                  No soy un robot
                </span>
              </label>
              <span className="text-xs font-semibold text-gray-400">reCAPTCHA</span>
            </div>

            <button
              type="button"
              disabled={!captchaChecked}
              onClick={() => {
                if (onCaptchaSolved) onCaptchaSolved();
                setCurrentState('connecting');
              }}
              className={`flex min-h-[48px] w-full items-center justify-center rounded-xl px-6 text-lg font-bold shadow-md transition ${
                captchaChecked
                  ? 'bg-green-700 text-white hover:bg-green-800'
                  : 'cursor-not-allowed bg-gray-300 text-gray-500'
              }`}
            >
              Continuar con la consulta
            </button>
          </div>
        )}

        {/* 4. Estado: Éxito en la consulta */}
        {currentState === 'success' && (
          <div className="my-6 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
              <span className="text-3xl">✓</span>
            </div>
            <h3 className="mt-4 text-2xl font-bold text-gray-900">
              ¡CURP Encontrada con Éxito!
            </h3>
            <p className="mt-2 text-base text-gray-600">
              Tu documento oficial ha sido generado y certificado por RENAPO.
            </p>
            <div className="mt-6 flex flex-col gap-3">
              <button
                type="button"
                onClick={onClose}
                className="flex min-h-[48px] w-full items-center justify-center rounded-xl bg-blue-700 px-6 text-lg font-bold text-white shadow-md hover:bg-blue-800"
              >
                Descargar Documento PDF
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
