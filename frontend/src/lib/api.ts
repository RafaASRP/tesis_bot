const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://tesis-bot-ou04.onrender.com/api/v1";

interface ChatRequest {
  message: string;
}

interface ChatResponse {
  reply: string;
  session_id?: string;
}

export async function sendChatMessage(data: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error('Error al comunicarse con el servidor de GovAssist Core.');
  }

  return response.json();
}
