"use client";

import { useState, useEffect, useCallback } from 'react';

interface IWindow extends Window {
  SpeechRecognition?: new () => ISpeechRecognition;
  webkitSpeechRecognition?: new () => ISpeechRecognition;
}

interface ISpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  onresult: (event: ISpeechRecognitionEvent) => void;
  onerror: () => void;
  onend: () => void;
}

interface ISpeechRecognitionEvent {
  results: {
    [index: number]: {
      [index: number]: {
        transcript: string;
      };
    };
  };
}

export function useSpeechRecognition() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [supported, setSupported] = useState(false);
  const [recognitionInstance, setRecognitionInstance] = useState<ISpeechRecognition | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const clientWindow = window as unknown as IWindow;
      const SpeechRecognitionAPI = clientWindow.SpeechRecognition || clientWindow.webkitSpeechRecognition;
      if (SpeechRecognitionAPI) {
        setSupported(true);
        const recognition = new SpeechRecognitionAPI();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'es-MX';

        recognition.onresult = (event: ISpeechRecognitionEvent) => {
          let currentTranscript = '';
          for (let i = 0; i < Object.keys(event.results).length; i++) {
            currentTranscript += event.results[i][0].transcript;
          }
          setTranscript(currentTranscript);
        };

        recognition.onerror = () => {
          setIsListening(false);
        };

        recognition.onend = () => {
          setIsListening(false);
        };

        setRecognitionInstance(recognition);
      }
    }
  }, []);

  const startListening = useCallback(() => {
    if (recognitionInstance && !isListening) {
      setTranscript('');
      try {
        recognitionInstance.start();
        setIsListening(true);
      } catch {
        // Manejo defensivo
      }
    }
  }, [recognitionInstance, isListening]);

  const stopListening = useCallback(() => {
    if (recognitionInstance && isListening) {
      try {
        recognitionInstance.stop();
      } catch {
        // Manejo defensivo
      }
      setIsListening(false);
    }
  }, [recognitionInstance, isListening]);

  return {
    startListening,
    stopListening,
    isListening,
    transcript,
    supported,
  };
}
