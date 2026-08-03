"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ 
  icon: Icon, 
  title, 
  description, 
  actionLabel, 
  onAction 
}) => {
  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="flex flex-col items-center justify-center p-12 text-center max-w-md mx-auto"
    >
      <div className="h-20 w-20 bg-primary/10 rounded-3xl flex items-center justify-center mb-6 border border-primary/20 shadow-inner">
        <Icon className="h-10 w-10 text-primary" />
      </div>
      <h3 className="text-2xl font-bold tracking-tight mb-2">{title}</h3>
      <p className="text-muted-foreground mb-8 leading-relaxed">
        {description}
      </p>
      {actionLabel && onAction && (
        <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
          <Button onClick={onAction} size="lg" className="rounded-full shadow-lg hover:shadow-primary/25 transition-all">
            {actionLabel}
          </Button>
        </motion.div>
      )}
    </motion.div>
  );
};
