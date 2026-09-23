"use client";

import React, { useState, useEffect, useRef } from "react";

interface VoiceControllerProps {
  onResult: (text: string) => void;
  disabled?: boolean;
}

export default function VoiceController({ onResult, disabled = false }: VoiceControllerProps) {
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = false;
        recognitionRef.current.interimResults = false;
        recognitionRef.current.lang = "es-MX";

        recognitionRef.current.onresult = (event: any) => {
          const transcript = event.results[0][0].transcript;
          onResult(transcript);
          setIsListening(false);
        };

        recognitionRef.current.onerror = (event: any) => {
          console.error("Error Web Speech API:", event.error);
          setIsListening(false);
        };

        recognitionRef.current.onend = () => {
          setIsListening(false);
        };
      }
    }
  }, [onResult]);

  const toggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      recognitionRef.current?.start();
      setIsListening(true);
    }
  };

  return (
    <button
      onClick={toggleListening}
      disabled={disabled}
      type="button"
      className={`min-h-[48px] min-w-[48px] rounded-lg px-4 font-bold text-lg transition-colors flex items-center justify-center ${
        isListening ? "bg-red-600 text-white animate-pulse" : "bg-[#0B231E] text-white"
      } disabled:opacity-50`}
      aria-label={isListening ? "Detener grabación de voz" : "Iniciar dictado por voz"}
      title="Dictar por voz"
    >
      {isListening ? "🎙️..." : "🎤"}
    </button>
  );
}
