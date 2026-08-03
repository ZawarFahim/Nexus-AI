import { useState, useRef, useEffect } from 'react';

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

  const sendMessage = async (content: string) => {
    if (!content.trim()) return;

    const token = localStorage.getItem('access_token');
    if (!token) {
      console.error("No access token found");
      return;
    }

    // Optimistically add user message
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content };
    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);

    // Initialize AI message placeholder
    const aiMessageId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, { id: aiMessageId, role: 'assistant', content: '' }]);

    try {
      const response = await fetch('http://localhost:8000/api/v1/chat/stream', {
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

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        const chunkValue = decoder.decode(value, { stream: true });

        // SSE chunks are separated by double newlines
        const events = chunkValue.split('\n\n');
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
                // Update the AI message with new chunk
                setMessages(prev => 
                  prev.map(msg => 
                    msg.id === aiMessageId 
                      ? { ...msg, content: msg.content + data.chunk }
                      : msg
                  )
                );
              }
            } catch (e) {
              // Sometimes chunks get split exactly at the JSON boundary, handling partial JSON is complex.
              // For simplicity in this demo, we assume chunks contain complete JSON objects.
              console.warn("Failed to parse SSE chunk:", e);
            }
          }
        }
      }
    } catch (error) {
      console.error("Error sending message:", error);
    } finally {
      setIsTyping(false);
    }
  };

  return {
    messages,
    isTyping,
    sendMessage,
    scrollRef
  };
}
