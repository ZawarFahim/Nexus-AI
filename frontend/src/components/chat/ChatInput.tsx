import React, { useRef, useEffect, useState } from 'react';
import { Send, Paperclip, Mic, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { motion } from 'framer-motion';

interface ChatInputProps {
  onSend: (message: string, options?: { synthesizeResponse?: boolean }) => void;
  onAudioSend?: (audioBlob: Blob) => Promise<string | undefined>;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, onAudioSend, disabled }) => {
  const [value, setValue] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
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

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        if (onAudioSend) {
          const text = await onAudioSend(audioBlob);
          if (text) {
            onSend(text, { synthesizeResponse: true });
          }
        }
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Error accessing microphone:", err);
      alert("Microphone access denied. Please allow microphone permissions in your browser settings to use voice commands.");
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
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
        placeholder={isRecording ? "Listening..." : "Message Nexus AI..."}
        className={`min-h-[44px] max-h-[200px] border-0 focus-visible:ring-0 resize-none bg-transparent shadow-none py-3 px-3 text-sm flex-1 ${isRecording ? 'text-red-500 animate-pulse' : ''}`}
        rows={1}
        disabled={disabled || isRecording}
      />
      
      {value.trim() ? (
        <motion.div whileTap={{ scale: 0.95 }}>
          <Button 
            onClick={handleSend}
            disabled={disabled}
            size="icon" 
            className="shrink-0 rounded-full h-10 w-10 ml-2"
          >
            <Send className="h-4 w-4" />
          </Button>
        </motion.div>
      ) : (
        <motion.div whileTap={{ scale: 0.95 }}>
          <Button 
            onClick={isRecording ? stopRecording : startRecording}
            disabled={disabled}
            size="icon" 
            variant={isRecording ? "destructive" : "default"}
            className={`shrink-0 rounded-full h-10 w-10 ml-2 ${isRecording ? 'animate-pulse' : ''}`}
          >
            {isRecording ? <Square className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
          </Button>
        </motion.div>
      )}
    </div>
  );
};
