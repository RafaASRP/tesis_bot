'use client';

import React, { useState, useEffect, useRef } from 'react';
import { ProcedureModal } from './ProcedureModal';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export const ChatContainer: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        'Hola. Soy GovAssist, tu asistente virtual de trámites de identidad y seguridad social. Actualmente solo puedo ayudarte con cinco trámites activos: CURP, Acta de Nacimiento, Semanas Cotizadas del IMSS, Pasaporte y Cédula Profesional. ¿En cuál de estos te puedo ayudar hoy?',
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isListening, setIsListening] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Detector del evento de conexión para desplegar la ventana emergente
  useEffect(() => {
    const lastMsg = messages[messages.length - 1];
    if (
      lastMsg &&
      lastMsg.role === 'assistant' &&
      lastMsg.content.includes('Estamos conectando con el portal oficial de gob.mx')
    ) {
      setIsModalOpen(true);
    }
  }, [messages]);

  const sendMessage = async (textToSend: string) => {
    const trimmed = textToSend.trim();
    if (!trimmed || isLoading) return;

    const newMessages: Message[] = [...messages, { role: 'user', content: trimmed }];
    setMessages(newMessages);
    setInputText('');
    setIsLoading(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://tesis-bot.onrender.com';
      const response = await fetch(`${apiUrl}/api/v1/chat/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: trimmed }],
          session_id: 'prod_user_session',
        }),
      });

      if (!response.ok) {
        throw new Error('Error al conectar con el servidor.');
      }

      const data = await response.json();
      const botReply = data.response || data.reply || 'Disculpa, no pude procesar la respuesta.';
      setMessages((prev) => [...prev, { role: 'assistant', content: botReply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Tuve un problema de comunicación con el servidor. Por favor intenta de nuevo.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      sendMessage(inputText);
    }
  };

  // Reconocimiento de voz nativo (Web Speech API)
  const toggleListening = () => {
    const SpeechRecognition =
      (window as unknown as { SpeechRecognition?: any; webkitSpeechRecognition?: any })
        .SpeechRecognition ||
      (window as unknown as { SpeechRecognition?: any; webkitSpeechRecognition?: any })
        .webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert('Tu navegador no soporta entrada de voz. Te recomendamos usar Google Chrome.');
      return;
    }

    if (isListening) {
      setIsListening(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'es-MX';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onerror = () => setIsListening(false);
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      if (transcript) {
        sendMessage(transcript);
      }
    };

    recognition.start();
  };

  return (
    <>
      <div className="flex flex-col lg:flex-row gap-6 w-full max-w-6xl mx-auto">
        {/* Columna Izquierda: Conversación del Trámite */}
        <section className="flex-1 bg-white rounded-[2.5rem] border border-slate-200 shadow-xl p-6 md:p-8 flex flex-col h-[700px]">
          <div className="flex items-center gap-3 border-b border-slate-100 pb-4 mb-4">
            <span className="h-3 w-3 rounded-full bg-[#8A1538] animate-pulse" />
            <h2 className="text-xl font-black text-slate-800">Transcurso del Trámite</h2>
          </div>

          {/* Historial de Mensajes */}
          <div className="flex-1 overflow-y-auto space-y-4 pr-2">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-3xl p-5 text-base md:text-lg font-medium leading-relaxed shadow-sm whitespace-pre-line ${
                    msg.role === 'user'
                      ? 'bg-[#8A1538] text-white rounded-br-sm'
                      : 'bg-slate-100 text-slate-900 border border-slate-200/80 rounded-bl-sm'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-slate-100 rounded-3xl p-4 border border-slate-200 text-slate-600 font-medium flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-[#8A1538] animate-bounce" />
                  <span className="h-2 w-2 rounded-full bg-[#8A1538] animate-bounce [animation-delay:0.2s]" />
                  <span className="h-2 w-2 rounded-full bg-[#8A1538] animate-bounce [animation-delay:0.4s]" />
                  <span>GovAssist está respondiendo...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </section>

        {/* Columna Derecha: Asistente Activo y Controles de Voz/Texto */}
        <aside className="w-full lg:w-96 flex flex-col gap-6">
          {/* Card del Asistente */}
          <div className="bg-white rounded-[2.5rem] border border-slate-200 shadow-xl p-6 text-center flex flex-col items-center">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">
              Asistente Activo
            </span>
            <div className="w-32 h-32 rounded-full bg-slate-50 border-2 border-slate-200 flex items-center justify-center p-2 shadow-inner">
              <svg viewBox="0 0 100 100" className="w-24 h-24">
                <path d="M70,30 Q65,15 50,20 Q35,25 35,45 Q35,65 50,70 Q65,75 70,60 Z" fill="#8A1538" />
                <path d="M50,35 Q30,35 15,45 Q30,55 50,55 Z" fill="#D97706" />
                <circle cx="55" cy="35" r="4" fill="white" />
                <circle cx="56" cy="35" r="2" fill="black" />
              </svg>
            </div>
            <h3 className="mt-4 text-lg font-bold text-slate-900">GovAssist Core</h3>
            <p className="text-sm text-slate-500">Apoyo digital para trámites de gob.mx</p>
          </div>

          {/* Controles de Interacción */}
          <div className="bg-white rounded-[2.5rem] border border-slate-200 shadow-xl p-6 flex flex-col items-center gap-4">
            {/* Botón de Micrófono (Accesibilidad 48x48px+) */}
            <button
              type="button"
              onClick={toggleListening}
              aria-label={isListening ? 'Detener dictado de voz' : 'Iniciar dictado de voz'}
              className={`w-24 h-24 rounded-full flex items-center justify-center shadow-lg transition-all active:scale-95 ${
                isListening
                  ? 'bg-red-600 animate-pulse text-white ring-4 ring-red-300'
                  : 'bg-[#1E3A8A] hover:bg-[#172554] text-white hover:scale-105'
              }`}
            >
              <svg className="w-10 h-10" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
              </svg>
            </button>
            <span className="text-sm font-semibold text-slate-600">
              {isListening ? 'Escuchando tu voz...' : 'Toca el micrófono para hablar'}
            </span>

            {/* Entrada de Texto y Envío */}
            <div className="w-full flex flex-col sm:flex-row gap-2 mt-2">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="O escribe tu respuesta..."
                className="flex-1 p-4 rounded-2xl text-base font-medium border border-slate-300 bg-slate-50 text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#8A1538] focus:border-transparent transition"
              />
              <button
                type="button"
                onClick={() => sendMessage(inputText)}
                disabled={!inputText.trim() || isLoading}
                className="px-6 py-4 rounded-2xl font-bold text-base text-white bg-[#8A1538] hover:bg-[#5a0c24] disabled:bg-slate-300 disabled:cursor-not-allowed shadow-md transition-all"
              >
                Enviar
              </button>
            </div>
          </div>
        </aside>
      </div>

      {/* Ventana Emergente Oficial */}
      <ProcedureModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        procedureTitle="Consulta Oficial de CURP"
      />
    </>
  );
};
