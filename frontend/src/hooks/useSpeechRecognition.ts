import { useState, useEffect, useCallback } from 'react';

// Declaración de tipos para la Web Speech API nativa del navegador
interface IWindow extends Window {
  SpeechRecognition?: any;
  webkitSpeechRecognition?: any;
}

export function useSpeechRecognition() {
  const [transcript, setTranscript] = useState<string>("");
  const [isListening, setIsListening] = useState<boolean>(false);
  const [hasSupport, setHasSupport] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  let recognition: any = null;

  useEffect(() => {
    if (typeof window !== "undefined") {
      const browserWindow = window as IWindow;
      const SpeechRecognitionAPI = browserWindow.SpeechRecognition || browserWindow.webkitSpeechRecognition;
      
      if (SpeechRecognitionAPI) {
        setHasSupport(true);
      } else {
        setHasSupport(false);
      }
    }
  }, []);

  const startListening = useCallback(() => {
    if (typeof window === "undefined") return;
    const browserWindow = window as IWindow;
    const SpeechRecognitionAPI = browserWindow.SpeechRecognition || browserWindow.webkitSpeechRecognition;

    if (!SpeechRecognitionAPI) {
      setError("El reconocimiento de voz no es compatible con este navegador.");
      return;
    }

    try {
      recognition = new SpeechRecognitionAPI();
      recognition.lang = "es-MX"; // Español de México para modulación local correcta
      recognition.continuous = false;
      recognition.interimResults = true;

      recognition.onstart = () => {
        setIsListening(true);
        setError(null);
      };

      recognition.onresult = (event: any) => {
        const current = event.resultIndex;
        const text = event.results[current][0].transcript;
        setTranscript(text);
      };

      recognition.onerror = (event: any) => {
        setError(`Error en reconocimiento: ${event.error}`);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognition.start();
    } catch (err: any) {
      setError(`No se pudo iniciar el micrófono: ${err.message}`);
      setIsListening(false);
    }
  }, []);

  const stopListening = useCallback(() => {
    if (recognition) {
      recognition.stop();
    }
    setIsListening(false);
  }, []);

  const resetTranscript = useCallback(() => {
    setTranscript("");
  }, []);

  return {
    transcript,
    isListening,
    hasSupport,
    error,
    startListening,
    stopListening,
    resetTranscript,
  };
}
