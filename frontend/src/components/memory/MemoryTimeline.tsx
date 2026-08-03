"use client";

import React from 'react';
import { MemoryData, MemoryCard } from './MemoryCard';
import { Skeleton } from '@/components/ui/skeleton';
import { motion } from 'framer-motion';
import { EmptyState } from '@/components/ui/empty-state';
import { BrainCircuit } from 'lucide-react';

interface MemoryTimelineProps {
  memories: MemoryData[];
  onDelete: (id: string) => void;
  onEdit: (id: string) => void;
  loading?: boolean;
}

export const MemoryTimeline: React.FC<MemoryTimelineProps> = ({ memories, onDelete, onEdit, loading }) => {
  if (loading) {
    return (
      <div className="relative pl-6 md:pl-8 border-l border-primary/20 space-y-8 mt-8 pb-12">
        {[1, 2, 3].map((i) => (
          <div key={i} className="relative">
            <div className="absolute -left-[37px] md:-left-[45px] top-4 h-5 w-5 rounded-full border-4 border-background bg-muted shadow-sm animate-pulse" />
            <div className="w-full bg-card/20 backdrop-blur-sm border rounded-xl p-4 shadow-sm space-y-4">
              <div className="flex justify-between items-center">
                <Skeleton className="h-5 w-24 rounded-full" />
                <Skeleton className="h-2 w-16 rounded-full" />
              </div>
              <Skeleton className="h-16 w-full rounded" />
              <Skeleton className="h-3 w-32 rounded" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (memories.length === 0) {
    return (
      <div className="mt-20">
        <EmptyState 
          icon={BrainCircuit}
          title="Blank Slate"
          description="Nexus AI hasn't learned any facts matching this filter yet. Chat with the AI and explicitly tell it to remember something."
        />
      </div>
    );
  }

  return (
    <div className="relative pl-6 md:pl-8 border-l border-primary/20 space-y-8 mt-8 pb-12">
      {memories.map((memory, index) => (
        <motion.div 
          key={memory.id} 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.1, duration: 0.4, type: "spring" }}
          className="relative"
        >
          {/* Timeline Dot */}
          <div className="absolute -left-[37px] md:-left-[45px] top-5 h-5 w-5 rounded-full border-4 border-background bg-primary shadow-[0_0_10px_rgba(var(--primary),0.5)]" />
          
          <MemoryCard 
            memory={memory} 
            onDelete={onDelete} 
            onEdit={onEdit} 
          />
        </motion.div>
      ))}
    </div>
  );
};
