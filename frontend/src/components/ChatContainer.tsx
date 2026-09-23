"use client";

import React, { useState, useRef, useEffect } from "react";
import { chatApi, ChatMessage } from "@/lib/api";
import VoiceController from "@/components/VoiceController";

export default function ChatContainer() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: 'Hola, soy tu asistente virtual de GovAssist. ¿En qué trámite federal te puedo ayudar hoy?' }
  ]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;
    
    const newUserMsg: ChatMessage = { role: 'user', content: text };
    const newMessages = [...messages, newUserMsg];
    setMessages(newMessages);
    setInputText("");
    setIsLoading(true);

    try {
      const response = await chatApi.query(newMessages, "session_50plus_prod");
      
      const newAssistantMsg: ChatMessage = { role: 'assistant', content: response.reply };
      setMessages(prev => [...prev, newAssistantMsg]);
    } catch (error) {
      console.error(error);
      const fallbackMsg: ChatMessage = { 
        role: 'assistant', 
        content: 'Lo siento, tuve un problema de conexión. ¿Podrías repetir tu consulta por favor?' 
      };
      setMessages(prev => [...prev, fallbackMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[80vh] max-w-3xl mx-auto bg-white text-black rounded-lg shadow-lg overflow-hidden border-4 border-[#0B231E]">
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50" role="log" aria-live="polite">
        {messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`p-4 rounded-xl max-w-[85%] text-lg ${msg.role === 'user' ? 'bg-[#0B231E] text-white' : 'bg-gray-200 text-black border-2 border-gray-300'}`}>
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="p-4 rounded-xl bg-gray-200 text-black border-2 border-gray-300 text-lg" aria-label="El asistente está escribiendo">
              Procesando solicitud...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="p-4 bg-white border-t-2 border-gray-300 flex items-center space-x-2">
        <VoiceController onResult={handleSendMessage} disabled={isLoading} />
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSendMessage(inputText)}
          placeholder="Escribe o dicta tu consulta..."
          className="flex-1 min-h-[48px] p-3 border-2 border-gray-400 rounded-lg text-lg focus:outline-none focus:border-[#0B231E]"
          aria-label="Campo de texto para consulta"
          disabled={isLoading}
        />
        <button
          onClick={() => handleSendMessage(inputText)}
          disabled={isLoading}
          className="min-h-[48px] min-w-[48px] bg-[#0B231E] text-white rounded-lg px-6 font-bold text-lg disabled:opacity-50"
          aria-label="Enviar mensaje"
        >
          Enviar
        </button>
      </div>
    </div>
  );
}
