import React from 'react';
import { Bot, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

export const DashboardHeader = () => {
  const hour = new Date().getHours();
  let greeting = 'Good evening';
  if (hour < 12) greeting = 'Good morning';
  else if (hour < 18) greeting = 'Good afternoon';

  return (
    <motion.div 
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col md:flex-row items-start md:items-center justify-between mb-10 gap-6"
    >
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Sparkles className="h-5 w-5 text-primary animate-pulse" />
          <h1 className="text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70">
            {greeting}, User!
          </h1>
        </div>
        <p className="text-muted-foreground text-lg ml-7">
          Here is what is happening across your integrated platforms today.
        </p>
      </div>
      <motion.div 
        whileHover={{ scale: 1.05 }}
        className="flex items-center gap-3 px-5 py-3 bg-primary/10 rounded-full border border-primary/20 shadow-[0_0_15px_rgba(var(--primary),0.2)] backdrop-blur-md cursor-default"
      >
        <Bot className="h-5 w-5 text-primary" />
        <span className="text-sm font-semibold text-primary tracking-wide">Nexus Agent Active</span>
      </motion.div>
    </motion.div>
  );
};
