import React, { useRef, useEffect } from 'react';
import { Send, Paperclip } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { motion } from 'framer-motion';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled }) => {
  const [value, setValue] = React.useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [value]);

  const handleSend = () => {
    if (value.trim() && !disabled) {
      onSend(value.trim());
      setValue('');
      if (textareaRef.current) textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="relative flex items-end w-full max-w-4xl mx-auto bg-background/80 backdrop-blur-xl border rounded-2xl p-2 shadow-sm focus-within:ring-1 focus-within:ring-primary transition-all">
      <Button variant="ghost" size="icon" className="shrink-0 rounded-full text-muted-foreground hover:text-foreground">
        <Paperclip className="h-5 w-5" />
      </Button>
      
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Message Nexus AI..."
        className="min-h-[44px] max-h-[200px] border-0 focus-visible:ring-0 resize-none bg-transparent shadow-none py-3 px-3 text-sm flex-1"
        rows={1}
        disabled={disabled}
      />
      
      <motion.div whileTap={{ scale: 0.95 }}>
        <Button 
          onClick={handleSend}
          disabled={!value.trim() || disabled}
          size="icon" 
          className="shrink-0 rounded-full h-10 w-10 ml-2"
        >
          <Send className="h-4 w-4" />
        </Button>
      </motion.div>
    </div>
  );
};
