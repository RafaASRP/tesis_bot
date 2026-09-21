"init strict";
"use client";

import React, { useState } from "react";

interface FeedbackSUSProps {
  sessionId: string;
  evaluationStage: "pre_test" | "post_test";
  onComplete: (score: number) => void;
}

const SUS_QUESTIONS = [
  "1. Creo que me gustaría utilizar este sistema con frecuencia.",
  "2. Encontré el sistema innecesariamente complejo.",
  "3. Pensé que el sistema fue fácil de usar.",
  "4. Creo que necesitaría el apoyo de un técnico para poder usar este sistema.",
  "5. Encontré que las diversas funciones del sistema estaban bien integradas.",
  "6. Pensé que había demasiada inconsistencia en este sistema.",
  "7. Imaginaría que la mayoría de la gente aprendería a usar este sistema muy rápidamente.",
  "8. Encontré el sistema muy engorroso de usar.",
  "9. Me sentí muy seguro al usar el sistema.",
  "10. Necesitaba aprender muchas cosas antes de poder seguir adelante con este sistema."
];

const LIKERT_OPTIONS = [
  { label: "Totalmente en desacuerdo", value: 0 },
  { label: "En desacuerdo", value: 1 },
  { label: "Neutral", value: 2 },
  { label: "De acuerdo", value: 3 },
  { label: "Totalmente de acuerdo", value: 4 },
];

export default function FeedbackSUS({ sessionId, evaluationStage, onComplete }: FeedbackSUSProps) {
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitted, setSubmitted] = useState<boolean>(false);

  const handleSelect = (questionIndex: number, value: number) => {
    setAnswers({ ...answers, [questionIndex]: value });
  };

  const isComplete = Object.keys(answers).length === SUS_QUESTIONS.length;

  const calculateAndSubmit = async () => {
    if (!isComplete || isSubmitting) return;
    setIsSubmitting(true);

    // Cálculo del puntaje SUS global (0 a 100)
    let sumOdd = 0;
    let sumEven = 0;

    SUS_QUESTIONS.forEach((_, idx) => {
      const val = answers[idx] || 0;
      if (idx % 2 === 0) {
        // Preguntas impares (1, 3, 5, 7, 9 -> índice 0, 2, 4, 6, 8): contribución es val
        sumOdd += val;
      } else {
        // Preguntas pares (2, 4, 6, 8, 10 -> índice 1, 3, 5, 7, 9): contribución es 4 - val
        sumEven += (4 - val);
      }
    });

    const rawScore = (sumOdd + sumEven) * 2.5;

    try {
      const response = await fetch("http://127.0.0.1:8000/api/v1/telemetry/sus", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          evaluation_stage: evaluationStage,
          q1: answers[0],
          q2: answers[1],
          q3: answers[2],
          q4: answers[3],
          q5: answers[4],
          q6: answers[5],
          q7: answers[6],
          q8: answers[7],
          q9: answers[8],
          q10: answers[9],
          total_sus_score: rawScore
        })
      });

      if (response.ok) {
        setSubmitted(true);
        onComplete(rawScore);
      } else {
        console.error("Error al registrar telemetría SUS en backend.");
      }
    } catch (error) {
      console.error("Fallo de red al enviar cuestionario SUS:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="p-6 bg-white rounded-2xl shadow-md text-center max-w-xl mx-auto my-8 border-2 border-green-600">
        <h2 className="text-2xl font-bold text-green-800 mb-2">¡Muchas gracias por su opinión!</h2>
        <p className="text-lg text-gray-700">Sus respuestas han sido registradas exitosamente para mejorar la accesibilidad de GovAssist Core.</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-2xl shadow-lg my-8 text-gov-text font-sans border border-gray-200">
      <h2 className="text-2xl font-bold text-gov-burgundy mb-2">Cuestionario de Experiencia de Uso (SUS)</h2>
      <p className="text-base text-gray-600 mb-6">
        Por favor, indique qué tan de acuerdo está con cada una de las siguientes afirmaciones respecto a su experiencia con el asistente.
      </p>

      <div className="space-y-8">
        {SUS_QUESTIONS.map((question, qIdx) => (
          <div key={qIdx} className="p-4 bg-gov-bg rounded-xl border border-gray-200">
            <p className="text-lg font-semibold text-gov-text mb-3">{question}</p>
            <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
              {LIKERT_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => handleSelect(qIdx, opt.value)}
                  className={`py-3 px-2 rounded-lg text-sm font-medium border transition-all min-h-[48px] flex items-center justify-center text-center ${
                    answers[qIdx] === opt.value
                      ? "bg-gov-accent text-white border-gov-accent shadow-md"
                      : "bg-white text-gray-700 border-gray-300 hover:bg-gray-100"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8">
        <button
          type="button"
          disabled={!isComplete || isSubmitting}
          onClick={calculateAndSubmit}
          className={`w-full py-4 rounded-xl font-bold text-lg shadow-md transition-all min-h-[56px] ${
            isComplete && !isSubmitting
              ? "bg-gov-burgundy text-white hover:bg-opacity-90 active:scale-95"
              : "bg-gray-300 text-gray-500 cursor-not-allowed"
          }`}
        >
          {isSubmitting ? "Enviando respuestas..." : "Enviar Evaluación"}
        </button>
        {!isComplete && (
          <p className="text-center text-sm text-red-600 mt-2">
            Por favor responda todas las preguntas para continuar.
          </p>
        )}
      </div>
    </div>
  );
}
