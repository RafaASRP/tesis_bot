import VoiceAssistantUI from "@/components/VoiceAssistantUI";

export default function Home() {
  return (
    <div className="w-full flex flex-col items-center justify-center space-y-10 py-10">
      <section className="text-center max-w-3xl px-4">
        <h2 className="text-4xl font-bold text-gov-primary mb-4">GovAssist Core</h2>
        <p className="text-gov-muted text-xl leading-relaxed">
          Asistente virtual de trámites federales por voz. 
        </p>
      </section>
      <VoiceAssistantUI />
    </div>
  );
}
