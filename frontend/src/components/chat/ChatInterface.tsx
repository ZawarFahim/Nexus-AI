'use client';

import React from 'react';
import { useChatStream } from '@/hooks/useChatStream';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { SuggestedPrompts } from './SuggestedPrompts';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Bot } from 'lucide-react';
import { motion } from 'framer-motion';

export const ChatInterface = () => {
  const { messages, isTyping, sendMessage, sendAudioMessage, scrollRef } = useChatStream();
  
  const handleSend = (text: string) => {
    sendMessage(text);
  };

  return (
    <div className="flex flex-col h-full w-full max-w-5xl mx-auto px-4 py-6 relative">
      <div className="flex items-center gap-2 mb-6 ml-2">
        <Bot className="h-6 w-6 text-primary" />
        <h1 className="text-xl font-semibold tracking-tight">Nexus AI</h1>
      </div>

      <ScrollArea className="flex-1 pr-4 rounded-md" ref={scrollRef}>
        <div className="flex flex-col pb-4 min-h-full justify-end">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center my-auto pt-20 pb-10">
              <motion.div 
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.4 }}
                className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mb-6"
              >
                <Bot className="h-8 w-8 text-primary" />
              </motion.div>
              <h2 className="text-2xl font-semibold mb-2">How can I help you today?</h2>
              <p className="text-muted-foreground text-sm mb-12 text-center max-w-md">
                I can orchestrate your calendar, write your code, summarize your inbox, and execute complex workflows.
              </p>
              <SuggestedPrompts onSelect={handleSend} />
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} role={msg.role} content={msg.content} />
              ))}
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="pt-4 sticky bottom-0 bg-background/80 backdrop-blur-xl">
        <ChatInput onSend={handleSend} onAudioSend={sendAudioMessage} disabled={isTyping} />
        <div className="text-center mt-2 text-xs text-muted-foreground">
          AI generated content may be inaccurate.
        </div>
      </div>
    </div>
  );
};
