import { useState, useRef, useEffect } from 'react';
import { API_BASE_URL } from '@/lib/api';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export function useChatStream() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const synthesizeAndPlay = async (text: string, token: string) => {
    try {
      // Clean up markdown formatting for TTS
      const cleanText = text.replace(/[*#`]/g, '').trim();
      if (!cleanText) return;
      
      const response = await fetch(`${API_BASE_URL}/voice/synthesize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ text: cleanText })
      });
      
      if (!response.ok) throw new Error("TTS failed");
      
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play();
      
      audio.onended = () => {
        URL.revokeObjectURL(url);
      };
    } catch (e) {
      console.error("Failed to synthesize speech:", e);
    }
  };

  const sendMessage = async (content: string, options?: { synthesizeResponse?: boolean }) => {
    if (!content.trim()) return;

    const token = localStorage.getItem('access_token');
    if (!token) {
      console.error("No access token found");
      return;
    }

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content };
    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);

    const aiMessageId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, { id: aiMessageId, role: 'assistant', content: '' }]);

    let fullAiContent = "";

    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: content,
          conversation_id: conversationId
        })
      });

      if (!response.body) throw new Error("ReadableStream not supported in this browser.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let done = false;
      let buffer = "";

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split('\n\n');
        buffer = events.pop() || ""; // keep the last incomplete chunk in the buffer

        for (const event of events) {
          if (event.startsWith('data: ')) {
            const dataStr = event.substring(6);
            try {
              const data = JSON.parse(dataStr);
              
              if (data.error) {
                console.error("Chat Error:", data.error);
                break;
              }
              
              if (data.event === 'start') {
                if (!conversationId) setConversationId(data.conversation_id);
                continue;
              }
              
              if (data.event === 'end') {
                break;
              }

              if (data.chunk) {
                fullAiContent += data.chunk;
                setMessages(prev => 
                  prev.map(msg => 
                    msg.id === aiMessageId 
                      ? { ...msg, content: msg.content + data.chunk }
                      : msg
                  )
                );
              }
            } catch (e) {
              console.warn("Failed to parse SSE chunk:", e, "Data string:", dataStr);
            }
          }
        }
      }
      
      // If voice mode is active, read the response out loud
      if (options?.synthesizeResponse && fullAiContent.trim()) {
        await synthesizeAndPlay(fullAiContent, token);
      }
      
    } catch (error) {
      console.error("Error sending message:", error);
    } finally {
      setIsTyping(false);
    }
  };

  const sendAudioMessage = async (audioBlob: Blob): Promise<string | undefined> => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
      setIsTyping(true); // show typing while transcribing
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      const response = await fetch(`${API_BASE_URL}/voice/transcribe`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (!response.ok) throw new Error("Transcription failed");
      
      const data = await response.json();
      setIsTyping(false);
      return data.text;
    } catch (error) {
      console.error("Failed to transcribe audio:", error);
      setIsTyping(false);
      return undefined;
    }
  };

  return {
    messages,
    isTyping,
    sendMessage,
    sendAudioMessage,
    scrollRef
  };
}
