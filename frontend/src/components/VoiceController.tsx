"use client";

import React, { useEffect } from "react";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { useSpeechSynthesis } from "@/hooks/useSpeechSynthesis";

interface VoiceControllerProps {
  onTranscript: (text: string) => void;
  lastAssistantMessage?: string;
}

export default function VoiceController({ onTranscript, lastAssistantMessage }: VoiceControllerProps) {
  const { transcript, isListening, hasSupport: hasMicSupport, startListening, stopListening } = useSpeechRecognition();
  const { isSpeaking, hasSupport: hasTtsSupport, speak, stop: stopSpeaking } = useSpeechSynthesis();

  // Cada vez que cambia el texto reconocido por voz, lo mandamos al contenedor principal
  useEffect(() => {
    if (transcript) {
      onTranscript(transcript);
    }
  }, [transcript, onTranscript]);

  // Cada vez que el asistente responde con un nuevo mensaje, sintetizamos la voz automáticamente
  useEffect(() => {
    if (lastAssistantMessage && hasTtsSupport) {
      speak(lastAssistantMessage);
    }
  }, [lastAssistantMessage, hasTtsSupport, speak]);

  if (!hasMicSupport && !hasTtsSupport) {
    return null;
  }

  return (
    <div className="flex items-center gap-4 p-4 bg-white border-t border-gray-200 shadow-md rounded-t-2xl">
      {/* Botón de Micrófono / Hablar */}
      {hasMicSupport && (
        <button
          onClick={isListening ? stopListening : startListening}
          className={`flex-1 flex items-center justify-center gap-2 py-4 px-6 rounded-xl font-bold text-lg transition-all min-h-[56px] shadow-sm ${
            isListening
              ? "bg-red-600 text-white animate-pulse"
              : "bg-gov-burgundy text-white hover:bg-opacity-90 active:scale-95"
          }`}
          aria-label={isListening ? "Detener grabación de voz" : "Hablar con el asistente"}
        >
          <span className="text-2xl" role="img" aria-hidden="true">
            {isListening ? "🛑" : "🎙️"}
          </span>
          <span>{isListening ? "Escuchando... (Toque para terminar)" : "Tocar para hablar"}</span>
        </button>
      )}

      {/* Botón de Silenciar / Detener Voz del Asistente */}
      {hasTtsSupport && isSpeaking && (
        <button
          onClick={stopSpeaking}
          className="py-4 px-5 bg-gray-200 text-gray-800 rounded-xl font-semibold hover:bg-gray-300 transition-all min-h-[56px]"
          aria-label="Silenciar asistente"
        >
          🔇 Silenciar voz
        </button>
      )}
    </div>
  );
}
