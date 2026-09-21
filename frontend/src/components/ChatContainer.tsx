"use client";

import React, { useState, useRef, useEffect } from "react";
import { sendChatMessage, MessageItem } from "@/lib/api";
import VoiceController from "@/components/VoiceController";

export default function ChatContainer() {
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      role: "assistant",
      content: "¡Hola! Soy GovAssist, su asistente para trámites de gob.mx. ¿En qué le puedo ayudar hoy? Puede escribir su duda o presionar el botón de hablar."
    }
  ]);
  const [inputText, setInputText] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendMessage = async (textToSend?: string) => {
    const textContent = textToSend || inputText;
    if (!textContent.trim() || isLoading) return;

    const newUserMessage: MessageItem = { role: "user", content: textContent };
    const updatedMessages = [...messages, newUserMessage];
    
    setMessages(updatedMessages);
    if (!textToSend) setInputText("");
    setIsLoading(true);

    try {
      const response = await sendChatMessage(updatedMessages, "session_web_01");
      const assistantMessage: MessageItem = { role: "assistant", content: response.reply };
      setMessages([...updatedMessages, assistantMessage]);
    } catch (error) {
      console.error("Error al enviar mensaje:", error);
      setMessages([
        ...updatedMessages,
        { role: "assistant", content: "Disculpe, ocurrió un error de conexión. Intente de nuevo por favor." }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const lastAssistantMsg = messages.filter(m => m.role === "assistant").pop()?.content;

  return (
    <main className="flex flex-col h-screen max-w-2xl mx-auto bg-gov-bg text-gov-text font-sans">
      {/* Cabecera institucional accesible */}
      <header className="bg-gov-burgundy text-white p-4 shadow-md flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">GovAssist Core</h1>
          <p className="text-sm opacity-90">Asistente de Trámites Federales (gob.mx)</p>
        </div>
        <div className="bg-white/10 px-3 py-1 rounded-full text-xs font-semibold">
          Versión Accesible (50+)
        </div>
      </header>

      {/* Historial del Chat con alto contraste */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] p-4 rounded-2xl text-lg shadow-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-gov-accent text-white rounded-br-none"
                  : "bg-white border-2 border-gray-200 text-gov-text rounded-bl-none"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white border-2 border-gray-200 p-4 rounded-2xl text-lg text-gray-500 animate-pulse">
              GovAssist está pensando su respuesta...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Sugerencias rápidas pre-cargadas para evitar frustración al escribir */}
      <div className="px-4 py-2 bg-white border-t border-gray-100 flex gap-2 overflow-x-auto">
        <button
          onClick={() => handleSendMessage("Quiero consultar mi CURP")}
          className="whitespace-nowrap px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gov-text text-base font-medium rounded-full border border-gray-300 transition-all active:scale-95"
        >
          🔍 Consultar CURP
        </button>
        <button
          onClick={() => handleSendMessage("¿Cómo tramito mi acta de nacimiento?")}
          className="whitespace-nowrap px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gov-text text-base font-medium rounded-full border border-gray-300 transition-all active:scale-95"
        >
          📄 Acta de Nacimiento
        </button>
      </div>

      {/* Barra de Entrada de Texto y Enlace con Voz */}
      <div className="p-4 bg-white border-t border-gray-200 flex gap-2">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
          placeholder="Escriba su duda aquí..."
          className="flex-1 px-4 py-3 text-lg border-2 border-gray-300 rounded-xl focus:border-gov-accent focus:outline-none bg-gov-bg text-gov-text"
          aria-label="Escriba su mensaje"
        />
        <button
          onClick={() => handleSendMessage()}
          disabled={isLoading || !inputText.trim()}
          className="bg-gov-burgundy text-white font-bold px-6 py-3 rounded-xl hover:bg-opacity-90 disabled:opacity-50 transition-all text-lg min-h-[52px]"
          aria-label="Enviar mensaje"
        >
          Enviar
        </button>
      </div>

      {/* Controlador de Voz (STT y TTS) */}
      <VoiceController
        onTranscript={(text) => handleSendMessage(text)}
        lastAssistantMessage={lastAssistantMsg}
      />
    </main>
  );
}
