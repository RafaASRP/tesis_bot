"use client";

import React, { useState, useRef, useEffect } from 'react';
import { sendChatMessage } from '../lib/api';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
}

export default function ChatContainer() {
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', text: 'Hola, soy GovAssist Core. ¿En qué trámite federal te puedo ayudar hoy (CURP, Acta, IMSS, Pasaporte, Cédula)?', sender: 'bot' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg: Message = { id: Date.now().toString(), text: input, sender: 'user' };
    setMessages(prev => [...prev, userMsg]);
    const currentInput = input;
    setInput('');
    setLoading(true);

    try {
      const res = await sendChatMessage({ message: currentInput });
      const botMsg: Message = { id: (Date.now() + 1).toString(), text: res.reply, sender: 'bot' };
      setMessages(prev => [...prev, botMsg]);
    } catch {
      const errorMsg: Message = { id: (Date.now() + 1).toString(), text: 'Error de comunicación con el servidor backend.', sender: 'bot' };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[75vh] w-full max-w-4xl mx-auto bg-white dark:bg-slate-800 rounded-3xl shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      <div className="bg-[#003B5C] text-white p-4 font-bold text-lg flex items-center justify-between">
        <span>GovAssist Core — Asistente de Trámites</span>
        <span className="text-xs bg-emerald-600 px-3 py-1 rounded-full">WCAG 2.1 AA</span>
      </div>
      
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] p-4 rounded-2xl text-lg font-medium shadow-sm ${
              m.sender === 'user' 
                ? 'bg-[#003B5C] text-white rounded-br-none' 
                : 'bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-bl-none border border-slate-200 dark:border-slate-600'
            }`}>
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="p-4 rounded-2xl bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 animate-pulse">
              Consultando gob.mx...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="p-4 bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700 flex gap-3">
        <input 
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Escribe tu consulta aquí..."
          className="flex-1 p-4 rounded-2xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#8A1538]"
        />
        <button 
          type="submit"
          disabled={loading || !input.trim()}
          className="px-8 py-4 bg-[#8A1538] text-white font-bold rounded-2xl hover:bg-[#5a0c24] transition-colors disabled:opacity-50"
        >
          Enviar
        </button>
      </form>
    </div>
  );
}
