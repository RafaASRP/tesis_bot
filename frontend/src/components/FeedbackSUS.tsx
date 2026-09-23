"use client";

import React, { useState } from 'react';

// Cuestionario estandarizado SUS (Brooke, 1996) traducido y adaptado para lectura fluida
const SUS_QUESTIONS = [
  "1. Creo que me gustaría utilizar este sistema con frecuencia.",
  "2. Encontré el sistema innecesariamente complejo.",
  "3. Pensé que el sistema era fácil de usar.",
  "4. Creo que necesitaría el apoyo de una persona técnica para poder utilizar este sistema.",
  "5. Encontré que las diversas funciones de este sistema estaban bien integradas.",
  "6. Pensé que había demasiada inconsistencia en este sistema.",
  "7. Imagino que la mayoría de las personas aprenderían a utilizar este sistema muy rápidamente.",
  "8. Encontré que el sistema era muy engorroso de utilizar.",
  "9. Me sentí muy confiado/a utilizando el sistema.",
  "10. Necesitaba aprender muchas cosas antes de poder empezar a utilizar este sistema."
];

interface FeedbackSUSProps {
  onSubmit: (scores: number[]) => Promise<void>;
  onCancel: () => void;
}

export default function FeedbackSUS({ onSubmit, onCancel }: FeedbackSUSProps) {
  const [answers, setAnswers] = useState<number[]>(Array(10).fill(0));
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSelect = (value: number) => {
    const newAnswers = [...answers];
    newAnswers[currentQuestion] = value;
    setAnswers(newAnswers);
  };

  const handleNext = () => {
    if (currentQuestion < 9) {
      setCurrentQuestion(prev => prev + 1);
    }
  };

  const handlePrevious = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(prev => prev - 1);
    }
  };

  const handleSubmit = async () => {
    // Validar que todas las preguntas hayan sido respondidas (valor > 0)
    if (answers.includes(0)) {
      alert("Por favor, responda todas las preguntas antes de finalizar.");
      return;
    }
    setIsSubmitting(true);
    try {
      await onSubmit(answers);
    } catch (error) {
      console.error("Error al enviar la evaluación SUS", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const progressPercentage = ((currentQuestion + 1) / 10) * 100;
  const currentAnswer = answers[currentQuestion];

  return (
    <div className="w-full max-w-3xl bg-gov-surface shadow-xl rounded-2xl flex flex-col border-2 border-gov-border overflow-hidden">
      
      {/* Barra de Progreso Accesible */}
      <div className="w-full bg-gray-200 h-4">
        <div 
          className="bg-gov-focus h-4 transition-all duration-300 ease-in-out" 
          style={{ width: `${progressPercentage}%` }}
          role="progressbar" 
          aria-valuenow={Math.round(progressPercentage)} 
          aria-valuemin={0} 
          aria-valuemax={100}
        />
      </div>

      <div className="p-6 md:p-8 flex-1 flex flex-col">
        <h3 className="text-2xl font-bold text-gov-primary mb-2">Evaluación de Usabilidad</h3>
        <p className="text-gov-muted mb-8 text-lg">
          Pregunta {currentQuestion + 1} de 10. Seleccione la opción que mejor describa su experiencia.
        </p>

        {/* Contenedor de la Pregunta */}
        <div className="bg-gov-background p-6 rounded-xl border border-gov-border mb-8 min-h-[8rem] flex items-center justify-center">
          <p className="text-xl md:text-2xl text-center font-medium text-gov-text leading-relaxed">
            {SUS_QUESTIONS[currentQuestion]}
          </p>
        </div>

        {/* Opciones Likert (Botones táctiles amplios > 48px) */}
        <div className="flex flex-col md:flex-row justify-between items-center gap-4 mb-10">
          <span className="hidden md:block text-gov-muted font-bold w-24 text-center">Totalmente en desacuerdo</span>
          
          <div className="flex w-full md:w-auto justify-between gap-2 md:gap-4">
            {[1, 2, 3, 4, 5].map((value) => (
              <button
                key={value}
                onClick={() => handleSelect(value)}
                className={`h-16 w-16 md:h-20 md:w-20 rounded-full border-4 flex items-center justify-center text-xl font-bold transition-all focus-visible:ring-4 focus-visible:ring-gov-focus shadow-sm
                  ${currentAnswer === value 
                    ? 'bg-gov-focus border-gov-focus text-white scale-110' 
                    : 'bg-white border-gov-border text-gov-text hover:border-gov-focus hover:bg-gray-50'
                  }`}
                aria-label={`Valor ${value}`}
                aria-pressed={currentAnswer === value}
              >
                {value}
              </button>
            ))}
          </div>
          
          <span className="hidden md:block text-gov-muted font-bold w-24 text-center">Totalmente de acuerdo</span>
          
          {/* Etiquetas móviles */}
          <div className="flex md:hidden w-full justify-between mt-2 px-2">
            <span className="text-sm text-gov-muted font-bold">En desacuerdo</span>
            <span className="text-sm text-gov-muted font-bold">De acuerdo</span>
          </div>
        </div>

        {/* Controles de Navegación */}
        <div className="flex justify-between items-center mt-auto pt-4 border-t-2 border-gray-100">
          <button
            onClick={onCancel}
            className="h-12 px-6 rounded-xl border-2 border-gov-border text-gov-text font-bold text-lg hover:bg-gray-50 transition-colors focus-visible:ring-4 focus-visible:ring-gov-focus"
          >
            Cancelar
          </button>
          
          <div className="flex gap-4">
            <button
              onClick={handlePrevious}
              disabled={currentQuestion === 0}
              className="h-12 px-6 rounded-xl bg-gray-200 text-gov-text font-bold text-lg disabled:opacity-50 transition-opacity focus-visible:ring-4 focus-visible:ring-gov-focus"
            >
              Anterior
            </button>
            
            {currentQuestion < 9 ? (
              <button
                onClick={handleNext}
                disabled={currentAnswer === 0}
                className="h-12 px-8 rounded-xl bg-gov-primary text-white font-bold text-lg disabled:opacity-50 transition-opacity focus-visible:ring-4 focus-visible:ring-gov-focus shadow-md"
              >
                Siguiente
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={currentAnswer === 0 || isSubmitting}
                className="h-12 px-8 rounded-xl bg-gov-accent text-white font-bold text-lg disabled:opacity-50 transition-opacity focus-visible:ring-4 focus-visible:ring-gov-focus shadow-md flex items-center justify-center min-w-[140px]"
              >
                {isSubmitting ? 'Enviando...' : 'Finalizar'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
