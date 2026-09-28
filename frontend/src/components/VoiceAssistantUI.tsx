"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';
import { sendChatMessage } from '../lib/api';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
}

export default function VoiceAssistantUI() {
  const [isInitialized, setIsInitialized] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showHitlModal, setShowHitlModal] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [textInput, setTextInput] = useState("");
  
  const lastProcessedRef = useRef("");
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const { startListening, stopListening, isListening, transcript, supported: sttSupported } = useSpeechRecognition();
  const { speak, stop: stopSpeaking, isSpeaking } = useSpeechSynthesis();

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const applyTheme = (dark: boolean) => {
      setIsDarkMode(dark);
      document.body.style.backgroundColor = dark ? '#0f172a' : '#f8fafc';
      document.body.style.color = dark ? '#f8fafc' : '#0f172a';
    };
    
    applyTheme(mediaQuery.matches);
    const handler = (e: MediaQueryListEvent) => applyTheme(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  const toggleTheme = () => {
    setIsDarkMode((prev) => {
      const next = !prev;
      document.body.style.backgroundColor = next ? '#0f172a' : '#f8fafc';
      document.body.style.color = next ? '#f8fafc' : '#0f172a';
      return next;
    });
  };

  const handleSystemStart = () => {
    setIsInitialized(true);
    const greeting = "Hola. Soy GovAssist, tu asistente virtual de trámites de identidad y seguridad social. Actualmente solo puedo ayudarte con cinco trámites activos: CURP, Acta de Nacimiento, Semanas Cotizadas del IMSS, Pasaporte y Cédula Profesional. ¿En cuál de estos te puedo ayudar hoy?";
    setMessages([{ id: '1', text: greeting, sender: 'bot' }]);
    speak(greeting);
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, transcript, isProcessing]);

  useEffect(() => {
    if (isListening && transcript) {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = setTimeout(() => {
        const currentText = transcript.trim();
        if (currentText.length > 0 && currentText !== lastProcessedRef.current && !isProcessing) {
          stopListening();
          procesarPeticionBackend(currentText);
        }
      }, 2500);
    }
    return () => {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    };
  }, [transcript, isListening, isProcessing, stopListening]);

  const procesarPeticionBackend = async (texto: string) => {
    if (!texto.trim()) return;
    
    setIsProcessing(true);
    lastProcessedRef.current = texto;
    stopSpeaking();
    
    setMessages(prev => [...prev, { id: Date.now().toString(), text: texto, sender: 'user' }]);

    try {
      const response = await sendChatMessage({ message: texto });
      
      if (response.reply.includes("CAPTCHA") || response.reply.includes("intervención")) {
        setShowHitlModal(true);
        speak("Por favor, resuelve este control de seguridad del gobierno para continuar.");
        setMessages(prev => [...prev, { id: Date.now().toString(), text: "Intervención manual requerida (CAPTCHA).", sender: 'bot' }]);
      } else {
        setMessages(prev => [...prev, { id: Date.now().toString(), text: response.reply, sender: 'bot' }]);
        speak(response.reply);
      }
    } catch (error) {
      const errorMsg = "Tuve un problema de conexión con el servidor. Asegúrate de tener activo el backend de Python con FastAPI.";
      setMessages(prev => [...prev, { id: Date.now().toString(), text: errorMsg, sender: 'bot' }]);
      speak(errorMsg);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleMicToggle = () => {
    if (isSpeaking) stopSpeaking();
    if (isListening) {
      stopListening(); 
    } else {
      lastProcessedRef.current = ""; 
      startListening();
    }
  };

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (textInput.trim() && !isProcessing) {
      procesarPeticionBackend(textInput);
      setTextInput("");
    }
  };

  if (!isInitialized) {
    return (
      <div 
        onClick={handleSystemStart}
        className={`fixed inset-0 z-50 flex flex-col items-center justify-center transition-colors duration-500 cursor-pointer p-4
        ${isDarkMode ? 'bg-slate-900' : 'bg-slate-50'}`}
      >
        <div className={`p-8 md:p-12 rounded-[3rem] shadow-2xl flex flex-col items-center text-center max-w-xl border w-full
          ${isDarkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'}`}>
          <div className="w-28 h-28 bg-gradient-to-br from-[#8A1538] to-[#5a0c24] rounded-[2rem] flex items-center justify-center shadow-lg shadow-[#8A1538]/40 mb-8 animate-[bounce_2s_infinite]">
            <svg className="w-16 h-16 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </div>
          <h1 className={`text-4xl font-extrabold mb-4 tracking-tight ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>GovAssist Core</h1>
          <p className={`text-xl font-medium mb-10 leading-relaxed ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>
            Asistente virtual de Trámites de Identidad y Seguridad Social.
          </p>
          <div className="w-full py-6 bg-[#003B5C] text-white rounded-2xl font-bold text-2xl shadow-xl shadow-[#003B5C]/30 hover:bg-[#002a42] transition-colors">
            Tocar la pantalla para Iniciar
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`w-full flex flex-col gap-6 font-sans transition-colors duration-500 ${isDarkMode ? 'text-slate-100' : 'text-slate-900'} pb-6 min-h-screen lg:min-h-0`}>
      
      <div className="w-full flex justify-end px-4 md:px-0 pt-4 lg:pt-0">
        <button 
          onClick={toggleTheme}
          aria-label={isDarkMode ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
          className={`p-3 rounded-2xl shadow-md border hover:scale-105 transition-all focus:outline-none focus:ring-4 focus:ring-[#8A1538]/50 
            ${isDarkMode ? 'bg-[#171717] border-gray-700 text-yellow-400' : 'bg-white border-slate-200 text-slate-600'}`}
        >
          {isDarkMode ? (
            <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
          ) : (
            <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" /></svg>
          )}
        </button>
      </div>

      <div className="w-full flex flex-col lg:grid lg:grid-cols-12 gap-8 lg:h-[75vh] px-4 md:px-0">
        
        {/* PANEL DE HISTORIAL: Ocupa el último lugar en móviles (order-last) y el primero en escritorio (lg:order-first) */}
        <div className={`order-last lg:order-first lg:col-span-8 rounded-[2rem] shadow-xl border flex flex-col overflow-hidden transition-colors duration-500 h-[60vh] lg:h-full
          ${isDarkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'}`}>
          
          <div className={`p-5 border-b flex justify-between items-center ${isDarkMode ? 'bg-slate-900/50 border-slate-700' : 'bg-slate-50 border-slate-200'}`}>
            <h2 className={`font-bold text-lg md:text-xl flex items-center gap-4 tracking-wide ${isDarkMode ? 'text-white' : 'text-slate-800'}`}>
              <span className="flex h-4 w-4 relative">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isProcessing ? 'bg-[#003B5C]' : isListening ? 'bg-red-500' : 'bg-[#8A1538]'}`}></span>
                <span className={`relative inline-flex rounded-full h-4 w-4 ${isProcessing ? 'bg-[#003B5C]' : isListening ? 'bg-red-500' : 'bg-[#8A1538]'}`}></span>
              </span>
              Transcurso del Trámite
            </h2>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6" role="log" aria-live="polite">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[95%] md:max-w-[85%] p-5 md:p-6 rounded-[2rem] text-lg md:text-xl font-medium leading-relaxed shadow-sm transition-colors duration-300
                  ${msg.sender === 'user' 
                    ? 'bg-gradient-to-br from-[#003B5C] to-[#001f30] text-white rounded-br-none border border-[#003B5C]/50' 
                    : isDarkMode 
                      ? 'bg-slate-700 text-slate-100 border border-slate-600 rounded-bl-none' 
                      : 'bg-slate-100 text-slate-900 border border-slate-200 rounded-bl-none'}`}>
                  {msg.text}
                </div>
              </div>
            ))}
            
            {isListening && transcript && (
              <div className="flex justify-end opacity-95">
                <div className="max-w-[95%] md:max-w-[85%] p-5 md:p-6 rounded-[2rem] text-lg md:text-xl font-medium leading-relaxed bg-[#8A1538] text-white rounded-br-none italic shadow-md border border-[#5a0c24]">
                  {transcript}
                  <span className="inline-block w-2.5 h-5 ml-2 align-middle bg-amber-400 animate-pulse rounded-full"></span>
                </div>
              </div>
            )}
            
            {isProcessing && (
              <div className="flex justify-start">
                <div className={`p-5 md:p-6 rounded-[2rem] text-lg md:text-xl font-medium border rounded-bl-none flex items-center gap-4 
                  ${isDarkMode ? 'bg-slate-700 border-slate-600 text-slate-300' : 'bg-slate-50 border-slate-200 text-slate-600'}`}>
                  <svg className="w-8 h-8 animate-spin text-[#8A1538] flex-shrink-0" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  Procesando en gob.mx...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} className="h-6" />
          </div>
        </div>

        {/* PANEL DE INTERACCIÓN: Ocupa los primeros lugares en móviles */}
        <div className="order-first lg:order-last lg:col-span-4 flex flex-col gap-6 w-full">
          
          <div className={`w-full py-8 md:py-0 md:min-h-[200px] rounded-[2rem] shadow-xl border flex flex-col items-center justify-center relative overflow-hidden transition-colors duration-500 
            ${isDarkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'}`}>
            
            <div className={`absolute top-4 md:top-6 px-5 py-1.5 rounded-full text-xs md:text-sm font-black uppercase tracking-widest z-20
              ${isListening 
                ? isDarkMode ? 'bg-red-900/50 text-red-300 border border-red-800' : 'bg-red-100 text-red-700 border border-red-200' 
                : isProcessing 
                  ? isDarkMode ? 'bg-blue-900/50 text-blue-300 border border-blue-800' : 'bg-blue-100 text-[#003B5C] border border-blue-200' 
                  : isDarkMode ? 'bg-slate-900 text-slate-400 border border-slate-700' : 'bg-slate-100 text-slate-600 border border-slate-200'}`}>
              {isListening ? "Escuchando..." : isProcessing ? "Trabajando" : "Asistente Activo"}
            </div>
            
            <div className={`relative w-40 h-40 md:w-44 md:h-44 transition-transform duration-700 mt-8 md:mt-10 ${isSpeaking ? 'scale-105' : 'scale-100 animate-[bounce_4s_infinite]'}`}>
              <div className={`absolute inset-0 rounded-full border-[6px] transition-all duration-300 z-0
                ${isListening ? 'border-red-500 scale-110 animate-ping opacity-40' : 
                  isProcessing ? 'border-[#003B5C] scale-105 animate-spin opacity-50' : 'border-transparent'}`}></div>
              
              <svg viewBox="0 0 200 200" className="w-full h-full drop-shadow-xl z-10 relative overflow-visible" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <clipPath id="avatar-clip"><circle cx="100" cy="100" r="95" /></clipPath>
                  <linearGradient id="bg-grad" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor={isDarkMode ? "#334155" : "#ffffff"} />
                    <stop offset="100%" stopColor={isDarkMode ? "#0f172a" : "#f1f5f9"} />
                  </linearGradient>
                </defs>
                <circle cx="100" cy="100" r="95" fill="url(#bg-grad)" stroke={isDarkMode ? "#475569" : "#e2e8f0"} strokeWidth="6"/>
                <g clipPath="url(#avatar-clip)">
                  <path d="M 130 220 C 130 140 140 100 100 65" fill="none" stroke="#8A1538" strokeWidth="36" strokeLinecap="round"/>
                  <circle cx="100" cy="65" r="28" fill="#8A1538"/>
                  <path d="M 120 45 Q 150 40 145 75" fill="none" stroke="#8A1538" strokeWidth="8" strokeLinecap="round"/>
                  <path d="M 80 55 L 10 65 L 80 70 Z" fill="#D4AF37" style={{ transformOrigin: '80px 65px', transform: isSpeaking ? 'rotate(-6deg)' : 'rotate(0deg)' }}/>
                  <path d="M 80 70 L 20 78 L 80 82 Z" fill="#D4AF37" style={{ transformOrigin: '80px 70px', transform: isSpeaking ? 'rotate(12deg)' : 'rotate(0deg)' }}/>
                  <circle cx="90" cy="58" r="7" fill="#FFFFFF"/>
                  <circle cx="88" cy="58" r="3.5" fill={isProcessing ? "#D4AF37" : "#000000"} className={isProcessing ? "animate-pulse" : ""}/>
                </g>
              </svg>
            </div>
          </div>

          <div className={`w-full rounded-[2rem] shadow-xl border p-6 flex flex-col items-center justify-center transition-all duration-500 
            ${isDarkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'}`}>
            
            {sttSupported ? (
              <button
                onClick={handleMicToggle}
                disabled={isProcessing}
                aria-label={isListening ? "Detener grabación" : "Hablar con el asistente"}
                className={`group relative h-24 w-24 md:h-28 md:w-28 rounded-full flex items-center justify-center transition-all duration-300 focus:outline-none focus:ring-8 shadow-2xl mb-6 flex-shrink-0
                  ${isListening 
                    ? 'bg-red-600 text-white scale-110 shadow-red-600/50 focus:ring-red-500/50 animate-pulse border-4 border-red-300' 
                    : isProcessing 
                      ? isDarkMode ? 'bg-slate-700 text-slate-500 cursor-not-allowed border border-slate-600' : 'bg-slate-200 text-slate-400 cursor-not-allowed border border-slate-300'
                      : 'bg-[#003B5C] text-white hover:bg-[#002a42] hover:scale-105 hover:shadow-[#003B5C]/50 focus:ring-[#003B5C]/50'}`}
              >
                <svg className="w-10 h-10 md:w-12 md:h-12 relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </button>
            ) : (
              <p className={`font-bold text-center text-sm p-4 mb-6 rounded-xl ${isDarkMode ? 'bg-red-900/40 text-red-300 border border-red-800' : 'bg-red-50 text-red-600 border border-red-200'}`}>Micrófono no compatible.</p>
            )}

            <form onSubmit={handleTextSubmit} className="w-full flex flex-col sm:flex-row gap-3">
              <input 
                type="text" 
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="O escribe tu trámite..." 
                disabled={isProcessing || isListening}
                className={`flex-1 p-4 rounded-2xl text-base md:text-lg font-medium border focus:outline-none focus:ring-2 transition-all w-full
                  ${isDarkMode 
                    ? 'bg-slate-900 border-slate-700 text-white placeholder-slate-500 focus:ring-[#8A1538]/50 focus:border-[#8A1538]' 
                    : 'bg-slate-50 border-slate-300 text-slate-900 placeholder-slate-500 focus:ring-[#8A1538]/50 focus:border-[#8A1538]'}`}
              />
              <button 
                type="submit" 
                disabled={!textInput.trim() || isProcessing || isListening}
                className={`px-6 py-4 rounded-2xl font-bold text-base md:text-lg transition-all focus:outline-none focus:ring-4 w-full sm:w-auto
                  ${!textInput.trim() || isProcessing || isListening
                    ? isDarkMode ? 'bg-slate-900 text-slate-600 border border-slate-700' : 'bg-slate-100 text-slate-400 border border-slate-200'
                    : 'bg-[#8A1538] text-white hover:bg-[#5a0c24] hover:scale-105 shadow-lg focus:ring-[#8A1538]/50'}`}
              >
                Enviar
              </button>
            </form>
          </div>
        </div>
      </div>

      {showHitlModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-lg p-4 md:p-6 animate-in fade-in duration-300">
          <div className={`p-8 md:p-14 rounded-[2rem] md:rounded-[3rem] shadow-2xl flex flex-col items-center text-center max-w-3xl border w-full
            ${isDarkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'}`}>
            <div className={`w-20 h-20 md:w-28 md:h-28 rounded-2xl md:rounded-[2rem] flex items-center justify-center mb-8 md:mb-10 rotate-6 hover:rotate-0 transition-transform border
              ${isDarkMode ? 'bg-yellow-900/40 border-yellow-800/50' : 'bg-yellow-50 border-yellow-200'}`}>
              <svg className="w-10 h-10 md:w-14 md:h-14 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
            </div>
            <h3 className={`text-3xl md:text-4xl font-black mb-4 md:mb-6 ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>Control de Seguridad</h3>
            <p className={`text-lg md:text-2xl mb-8 md:mb-12 leading-relaxed font-medium ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}`}>
              El portal oficial <span className={`font-black ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>gob.mx</span> solicita validar que eres humano. Resuelve el reto visual en la siguiente ventana para continuar.
            </p>
            <button onClick={() => setShowHitlModal(false)} className="w-full py-5 md:py-6 bg-gradient-to-r from-[#003B5C] to-[#001f30] text-white rounded-2xl font-black text-xl md:text-2xl hover:scale-[1.02] transition-transform shadow-2xl shadow-[#003B5C]/50">
              Completar Validación Manual
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
