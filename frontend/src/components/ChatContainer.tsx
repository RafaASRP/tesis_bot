"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useSpeechRecognition } from '@/hooks/useSpeechRecognition';
import { useSpeechSynthesis } from '@/hooks/useSpeechSynthesis';
import { sendChatMessage } from '@/lib/api';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
}

export default function ChatContainer() {
  const [messages, setMessages] = useState<Message[]>([
    { 
      id: 'welcome', 
      text: 'Hola. Soy GovAssist, tu asistente virtual. Puedo ayudarte con tu CURP, Acta de Nacimiento, Semanas Cotizadas, Pasaporte o Cédula Profesional. Toca el micrófono para hablar o escribe tu duda.', 
      sender: 'bot' 
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { startListening, stopListening, isListening, transcript, supported: sttSupported } = useSpeechRecognition();
  const { speak, stop: stopSpeaking } = useSpeechSynthesis();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (transcript) setInput(transcript);
  }, [transcript]);

  const handleSend = async (textToSend: string) => {
    if (!textToSend.trim()) return;

    const userMsg: Message = { id: Date.now().toString(), text: textToSend, sender: 'user' };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);
    stopSpeaking(); // Detener TTS si el usuario interrumpe

    try {
      const response = await sendChatMessage({ message: textToSend });
      const botMsg: Message = { id: (Date.now() + 1).toString(), text: response.reply, sender: 'bot' };
      setMessages(prev => [...prev, botMsg]);
      speak(response.reply); // Lectura automática modulada a 0.85x
    } catch (error) {
      const errorMsg: Message = { id: (Date.now() + 1).toString(), text: 'Lo siento, tuve un problema de red. ¿Podrías intentar de nuevo?', sender: 'bot' };
      setMessages(prev => [...prev, errorMsg]);
      speak(errorMsg.text);
    } finally {
      setIsLoading(false);
      stopListening(); 
    }
  };

  const toggleMic = () => {
    if (isListening) stopListening();
    else startListening();
  };

  return (
    <div className="w-full max-w-3xl bg-gov-surface shadow-xl rounded-2xl flex flex-col h-[70vh] border-2 border-gov-border">
      {/* Historial de conversación accesible */}
      <div className="flex-1 p-6 overflow-y-auto space-y-6" role="log" aria-live="polite">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`p-4 max-w-[85%] rounded-2xl text-lg shadow-sm ${msg.sender === 'user' ? 'bg-gov-focus text-white rounded-br-none' : 'bg-gov-background text-gov-text border border-gov-border rounded-bl-none'}`}>
              {msg.text}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="p-4 bg-gov-background border border-gov-border rounded-2xl text-gov-muted animate-pulse text-lg rounded-bl-none">
              Procesando tu solicitud...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Controles táctiles (Áreas mínimas de 48x48 px - WCAG 2.1 AA) */}
      <div className="p-4 border-t-2 border-gov-border bg-gov-background rounded-b-2xl flex items-end gap-3">
        {sttSupported && (
          <button
            type="button"
            onClick={toggleMic}
            aria-label={isListening ? "Detener micrófono" : "Iniciar micrófono"}
            className={`h-12 w-12 flex-shrink-0 rounded-full flex items-center justify-center transition-colors focus-visible:ring-4 focus-visible:ring-gov-focus shadow-md ${isListening ? 'bg-gov-error text-white animate-pulse' : 'bg-gov-accent text-white hover:bg-opacity-90'}`}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" /></svg>
          </button>
        )}
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend(input)}
          placeholder="Escribe tu mensaje aquí..."
          className="flex-1 min-h-[3rem] p-3 border-2 border-gov-border rounded-xl text-lg text-gov-text focus:outline-none focus:border-gov-focus bg-white shadow-inner"
          aria-label="Caja de texto para mensaje"
        />
        <button
          onClick={() => handleSend(input)}
          disabled={isLoading || !input.trim()}
          aria-label="Enviar mensaje"
          className="h-12 px-6 rounded-xl bg-gov-primary text-white font-bold text-lg disabled:opacity-50 transition-opacity focus-visible:ring-4 focus-visible:ring-gov-focus shadow-md flex items-center justify-center"
        >
          Enviar
        </button>
      </div>
    </div>
  );
}
