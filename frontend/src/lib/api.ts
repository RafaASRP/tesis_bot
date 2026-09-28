const getApiBaseUrl = (): string => {
  const envUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:10000';
  const cleanBase = envUrl.replace(/\/+$/, '');
  if (cleanBase.endsWith('/api/v1')) {
    return cleanBase;
  }
  return `${cleanBase}/api/v1`;
};

export interface ChatRequest {
  message: string;
  session_id?: string;
}

export interface ChatResponse {
  reply: string;
  sources?: string[];
}

export async function sendChatMessage(data: ChatRequest): Promise<ChatResponse> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/chat/query`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      messages: [
        {
          role: 'user',
          content: data.message,
        }
      ],
      session_id: data.session_id || 'default_session',
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}
