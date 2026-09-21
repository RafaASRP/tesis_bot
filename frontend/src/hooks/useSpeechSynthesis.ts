import { useState, useEffect, useCallback } from 'react';

export function useSpeechSynthesis() {
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [hasSupport, setHasSupport] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      setHasSupport(true);
    }
  }, []);

  const speak = useCallback((text: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;

    const synth = window.speechSynthesis;

    // Detener cualquier locución previa en curso
    if (synth.speaking) {
      synth.cancel();
    }

    if (!text.trim()) return;

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "es-MX";
    utterance.rate = 0.85; // Velocidad reducida a 0.85x para accesibilidad cognitiva de adultos mayores
    utterance.pitch = 1.0;

    utterance.onstart = () => {
      setIsSpeaking(true);
    };

    utterance.onend = () => {
      setIsSpeaking(false);
    };

    utterance.onerror = (event) => {
      console.error("Error en síntesis de voz (TTS):", event);
      setIsSpeaking(false);
    };

    synth.speak(utterance);
  }, []);

  const stop = useCallback(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    const synth = window.speechSynthesis;
    if (synth.speaking) {
      synth.cancel();
      setIsSpeaking(false);
    }
  }, []);

  return {
    isSpeaking,
    hasSupport,
    speak,
    stop,
  };
}
