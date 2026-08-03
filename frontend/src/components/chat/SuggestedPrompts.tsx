import React from 'react';
import { motion } from 'framer-motion';
import { Code, Mail, Calendar, FileText } from 'lucide-react';

interface SuggestedPromptsProps {
  onSelect: (prompt: string) => void;
}

const PROMPTS = [
  {
    title: 'Analyze my GitHub',
    subtitle: 'Summarize recent PRs',
    icon: <Code className="h-5 w-5" />,
    prompt: 'Summarize the recent pull requests in my primary GitHub repository.'
  },
  {
    title: 'Smart Email',
    subtitle: 'Draft a reply',
    icon: <Mail className="h-5 w-5" />,
    prompt: 'Fetch my unread emails, summarize them, and draft a reply to the most urgent one.'
  },
  {
    title: 'Daily Briefing',
    subtitle: 'What is on my plate?',
    icon: <Calendar className="h-5 w-5" />,
    prompt: 'Give me a daily briefing of my schedule and pending tasks.'
  },
  {
    title: 'Document Analysis',
    subtitle: 'Summarize uploaded file',
    icon: <FileText className="h-5 w-5" />,
    prompt: 'Analyze the attached document and provide a key takeaways summary.'
  }
];

export const SuggestedPrompts: React.FC<SuggestedPromptsProps> = ({ onSelect }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-3xl mx-auto my-8">
      {PROMPTS.map((item, idx) => (
        <motion.div
          key={idx}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: idx * 0.1 }}
          whileHover={{ y: -2, scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => onSelect(item.prompt)}
          className="flex flex-col gap-2 p-4 rounded-xl border bg-card/40 backdrop-blur-sm cursor-pointer hover:bg-card/80 hover:border-primary/50 transition-colors shadow-sm"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 text-primary rounded-lg">
              {item.icon}
            </div>
            <div className="font-semibold text-sm">{item.title}</div>
          </div>
          <div className="text-xs text-muted-foreground ml-11">
            {item.subtitle}
          </div>
        </motion.div>
      ))}
    </div>
  );
};
