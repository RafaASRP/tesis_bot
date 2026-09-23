import ChatContainer from "@/components/ChatContainer";

export default function Home() {
  return (
    <div className="w-full flex flex-col items-center justify-center space-y-6">
      <section className="text-center max-w-2xl px-4">
        <h2 className="text-3xl font-bold text-gov-primary mb-3">Asistencia de Trámites por Voz</h2>
        <p className="text-gov-muted text-lg leading-relaxed">
          Presione el ícono del micrófono rojo para hablar, o escriba su duda en la caja inferior. 
          GovAssist leerá las respuestas en voz alta para usted.
        </p>
      </section>
      <ChatContainer />
    </div>
  );
}
